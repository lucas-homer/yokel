#!/usr/bin/env bash
set -euo pipefail
# alert-drill.sh — the alerting fire drill (Slice V / PR-V3, plans/verification-accuracy.md).
# Cadence: QUARTERLY. An alert path is untested until it has actually paged someone, so this drill
# manufactures a REAL failure and requires a human to confirm the phone buzzed:
#
#   1. pause docketclock's Argo auto-sync — git pins the poller at replicas:1, so selfHeal would
#      quietly "fix" the outage we're staging
#   2. scale the poller to 0 and wait for the *Poller stalled* rule to fire
#      (heartbeat age >45m + for:10m — the wait is ~55-60m; that latency IS the drill: it proves
#      the real rule fires with its real thresholds, not a lowered test copy)
#   3. you confirm the ntfy notification REACHED YOUR PHONE
#   4. restore (scale back, re-enable auto-sync), wait for resolve, confirm the resolve notification
#
# The dead-man half (healthchecks.io paging on ping ABSENCE) is a manual step printed at the end —
# its wait is period+grace (~2h) and needs no babysitting.
#
# Cleanup is trap'd: auto-sync is re-enabled and the poller re-scaled even on ^C/failure.

NS_APP=docketclock
POLLER=docketclock-poller
GRAFANA_NS=observability
PF_PORT="${PF_PORT:-3999}"
FIRE_TIMEOUT_MIN="${FIRE_TIMEOUT_MIN:-80}"
RESOLVE_TIMEOUT_MIN="${RESOLVE_TIMEOUT_MIN:-30}"

# ── preflight: refuse to drill a receiver that can't receive ────────────────────────────────────
NTFY_URL=$(kubectl -n "$GRAFANA_NS" get secret grafana-alerting -o jsonpath='{.data.ALERTING_NTFY_URL}' 2>/dev/null | base64 -d || true)
case "$NTFY_URL" in
  *127.0.0.1*|"")
    echo "ABORT: the ntfy contact point still points at the local-noop placeholder — a drill would"
    echo "prove nothing. Run scripts/seed-alerting-secrets.sh (and subscribe on your phone) first."
    exit 1;;
esac
unset NTFY_URL

# ── cleanup (trap'd) ─────────────────────────────────────────────────────────────────────────────
AUTOMATION_PAUSED=0
PF_PID=""
cleanup() {
  code=$?
  [ -n "$PF_PID" ] && kill "$PF_PID" >/dev/null 2>&1 || true
  echo "restoring: poller replicas -> 1..."
  kubectl -n "$NS_APP" scale deploy "$POLLER" --replicas=1 >/dev/null || true
  if [ "$AUTOMATION_PAUSED" = "1" ]; then
    echo "restoring: docketclock auto-sync (prune + selfHeal)..."
    kubectl -n argocd patch application docketclock --type=merge \
      -p '{"spec":{"syncPolicy":{"automated":{"prune":true,"selfHeal":true}}}}' >/dev/null || \
      echo "WARN: could not re-enable auto-sync — restore by hand: task -d infra platform"
  fi
  exit $code
}
trap cleanup EXIT

# ── grafana API access (port-forward + admin creds; never echoed) ────────────────────────────────
GF_USER=$(kubectl -n "$GRAFANA_NS" get secret grafana-admin -o jsonpath='{.data.admin_user}' | base64 -d)
GF_PASS=$(kubectl -n "$GRAFANA_NS" get secret grafana-admin -o jsonpath='{.data.admin_password}' | base64 -d)
kubectl -n "$GRAFANA_NS" port-forward svc/grafana "$PF_PORT:80" >/dev/null 2>&1 &
PF_PID=$!
for _ in $(seq 1 20); do
  curl -fsS -m 2 "http://127.0.0.1:$PF_PORT/api/health" >/dev/null 2>&1 && break
  sleep 1
done

# Returns the current state of the "Poller stalled" alert: Alerting / Pending / Normal.
# The alerts endpoint only lists ACTIVE (pending/firing) instances — absence means Normal.
poller_alert_state() {
  curl -fsS -m 10 -u "$GF_USER:$GF_PASS" \
    "http://127.0.0.1:$PF_PORT/api/prometheus/grafana/api/v1/alerts" 2>/dev/null | python3 -c '
import sys, json
try:
    alerts = json.load(sys.stdin)["data"]["alerts"]
except Exception:
    print("api-error"); sys.exit(0)
states = [a.get("state", "?") for a in alerts if a.get("labels", {}).get("alertname") == "Poller stalled"]
print(states[0] if states else "Normal")'
}

state=$(poller_alert_state)
if [ "$state" != "Normal" ]; then
  echo "ABORT: 'Poller stalled' is already $state — the cluster is not in a clean baseline state."
  exit 1
fi

echo "=== Alert fire drill: staging a real poller outage (expect ~55-60m to fire) ==="

# ── 1. pause auto-sync, 2. stage the outage ─────────────────────────────────────────────────────
if [ -n "$(kubectl -n argocd get application docketclock -o jsonpath='{.spec.syncPolicy.automated}')" ]; then
  kubectl -n argocd patch application docketclock --type=json \
    -p '[{"op":"remove","path":"/spec/syncPolicy/automated"}]' >/dev/null
  AUTOMATION_PAUSED=1
  echo "docketclock auto-sync paused (selfHeal would revert the outage)."
else
  echo "WARN: docketclock auto-sync already disabled — leaving it as found."
fi
kubectl -n "$NS_APP" scale deploy "$POLLER" --replicas=0 >/dev/null
echo "poller scaled to 0 at $(date '+%H:%M:%S'). Waiting for 'Poller stalled' to fire..."

# ── wait for FIRING ──────────────────────────────────────────────────────────────────────────────
fired=0
for i in $(seq 1 $((FIRE_TIMEOUT_MIN))); do
  sleep 60
  state=$(poller_alert_state)
  if [ "$state" = "Alerting" ]; then fired=1; break; fi
  [ $((i % 5)) -eq 0 ] && echo "  t+${i}m: alert state = $state (fires around t+55-60m)"
done
if [ "$fired" != "1" ]; then
  echo "FAIL: 'Poller stalled' did not fire within ${FIRE_TIMEOUT_MIN}m — rule or datasource broken."
  exit 1
fi
echo "🔥 'Poller stalled' is FIRING at $(date '+%H:%M:%S')."

read -r -p "Did the ntfy notification arrive ON YOUR PHONE? [y/N] " got_page

# ── restore + wait for RESOLVE (cleanup trap re-scales + re-enables sync; do it now, visibly) ───
kubectl -n "$NS_APP" scale deploy "$POLLER" --replicas=1 >/dev/null
echo "poller scaled back to 1. Waiting for the alert to resolve (first settled cycle + eval)..."
resolved=0
for i in $(seq 1 $((RESOLVE_TIMEOUT_MIN))); do
  sleep 60
  state=$(poller_alert_state)
  if [ "$state" = "Normal" ]; then resolved=1; break; fi
  [ $((i % 5)) -eq 0 ] && echo "  t+${i}m: alert state = $state"
done
if [ "$resolved" != "1" ]; then
  echo "FAIL: alert did not resolve within ${RESOLVE_TIMEOUT_MIN}m of restore — investigate before trusting the path."
  exit 1
fi
echo "✅ alert resolved at $(date '+%H:%M:%S')."

read -r -p "Did the RESOLVED notification arrive on your phone? [y/N] " got_resolve

echo
echo "=== Dead-man half (manual — the wait is ~2h of ping absence) ==="
echo "  1. pause the deadman app's auto-sync, then suspend the CronJob:"
echo "       kubectl -n argocd patch application deadman --type=json -p '[{\"op\":\"remove\",\"path\":\"/spec/syncPolicy/automated\"}]'"
echo "       kubectl -n observability patch cronjob deadman-ping -p '{\"spec\":{\"suspend\":true}}'"
echo "  2. wait for the healthchecks.io ABSENCE page (check period 1h + grace 1h)"
echo "  3. restore: unsuspend + re-enable — or simply: task -d infra platform (git is truth)"
echo

case "$got_page" in y|Y) :;; *) echo "=== Drill: FAILED (firing page never reached the phone) ==="; exit 1;; esac
case "$got_resolve" in y|Y) :;; *) echo "=== Drill: FAILED (resolve notification never reached the phone) ==="; exit 1;; esac
echo "=== Drill: PASSED — the alert path has now actually paged a human. Log the date in infra/README.md's cadence note. ==="
