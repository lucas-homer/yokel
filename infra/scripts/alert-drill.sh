#!/usr/bin/env bash
set -euo pipefail
# alert-drill.sh — the alerting fire drill (Slice V / PR-V3, plans/verification-accuracy.md).
# Cadence: QUARTERLY. An alert path is untested until it has actually paged someone, so this drill
# manufactures a REAL failure and requires a human to confirm the phone buzzed. Two modes:
#
# `alert-drill.sh stall` (default) — the *Poller stalled* heartbeat rule:
#   1. pause docketclock's Argo auto-sync IF Argo manages it — git pins the poller at replicas:1,
#      so selfHeal would quietly "fix" the outage we're staging. (Locally the app is a plain Helm
#      release / Tilt — nothing to pause, and the guard degrades to a WARN.)
#   2. scale the poller to 0 and wait for the rule to fire with its REAL thresholds, not a lowered
#      test copy. Timing (first-run finding, 2026-07-11): scale-to-0 fires in ~13m, not 45m+10m —
#      the dead pod's heartbeat series goes stale and the rule's `or vector(0)` fallback treats the
#      ABSENT metric as infinitely stale (by design: pod-gone pages faster). Only a hung-but-still-
#      running poller takes the full ~55-60m aging path.
#   3. you confirm the ntfy notification REACHED YOUR PHONE
#   4. restore (scale back, re-enable auto-sync), wait for resolve, confirm the resolve notification
#
# `alert-drill.sh ingest` — the *Poll pass failing* single-source-blindness rule (#91), by staging
#   the REAL 2026-07 incident: an invalid regs.gov key. The fault is injected at the SOURCE (Vault,
#   via seed-docketclock-secrets.sh) so the whole delivery chain is exercised (Vault → ESO → Secret →
#   poller env) and the Deployment spec never drifts — nothing for Argo selfHeal or Tilt to fight,
#   no auto-sync pause needed. The regs pass then throws every 15m cycle while the heartbeat stays
#   green (the exact incident signature). Expect FIRING ~t+36m (failures at ~t+1/16/31m cross the
#   3-in-1h threshold at the third, + for:5m) and RESOLVE ~30-60m after restore (the [1h] window has
#   to age the outage-era increments out). Restore re-seeds the real key from the repo-root .env —
#   checked BEFORE staging: never inject a fault you can't roll back.
#
# The dead-man half (healthchecks.io paging on ping ABSENCE) is a manual step printed at the end of
# the stall drill — its wait is period+grace (~2h) and needs no babysitting.
#
# Cleanup is trap'd: the outage is rolled back even on ^C/failure (stall: re-scale + re-enable
# auto-sync; ingest: re-seed the real key).

NS_APP=docketclock
POLLER=docketclock-poller
GRAFANA_NS=observability
PF_PORT="${PF_PORT:-3999}"
FIRE_TIMEOUT_MIN="${FIRE_TIMEOUT_MIN:-80}"

MODE="${1:-stall}"
case "$MODE" in
  stall) ALERTNAME="Poller stalled"; RESOLVE_TIMEOUT_MIN="${RESOLVE_TIMEOUT_MIN:-30}" ;;
  ingest) ALERTNAME="Poll pass failing"; RESOLVE_TIMEOUT_MIN="${RESOLVE_TIMEOUT_MIN:-70}" ;;
  *) echo "usage: $0 [stall|ingest]" >&2; exit 2 ;;
esac
export ALERTNAME

HERE=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd "$HERE/../.." && pwd)

# ── ingest-mode preflight: the RESTORE path must exist before we break anything ─────────────────
if [ "$MODE" = "ingest" ]; then
  REAL_KEY=$(grep '^REGS_API_KEY=' "$REPO_ROOT/.env" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r\n')
  if [ -z "$REAL_KEY" ]; then
    echo "ABORT: REGS_API_KEY not found in $REPO_ROOT/.env — the drill breaks the in-cluster key and"
    echo "restores it from there. Refusing to stage a fault with no rollback."
    exit 1
  fi
  unset REAL_KEY # only proving it exists; the restore re-reads it (value never held/printed)
fi

# ── preflight: refuse to drill a receiver that can't receive ────────────────────────────────────
NTFY_URL=$(kubectl -n "$GRAFANA_NS" get secret grafana-alerting -o jsonpath='{.data.ALERTING_NTFY_URL}' 2>/dev/null | base64 -d || true)
case "$NTFY_URL" in
  *127.0.0.1*|"")
    echo "ABORT: the ntfy contact point still points at the local-noop placeholder — a drill would"
    echo "prove nothing. Run scripts/seed-alerting-secrets.sh (and subscribe on your phone) first."
    exit 1;;
esac
unset NTFY_URL

# ── restore + cleanup (trap'd) ───────────────────────────────────────────────────────────────────
AUTOMATION_PAUSED=0
FAULT_STAGED=0
PF_PID=""
restore_outage() {
  if [ "$MODE" = "ingest" ]; then
    echo "restoring: re-seeding the real regs key from $REPO_ROOT/.env (never printed)..."
    REGS_API_KEY=$(grep '^REGS_API_KEY=' "$REPO_ROOT/.env" | head -1 | cut -d= -f2- | tr -d '\r\n') \
      bash "$HERE/seed-docketclock-secrets.sh" || \
      echo "WARN: restore failed — re-seed by hand: task -d infra regs-key"
  else
    echo "restoring: poller replicas -> 1..."
    kubectl -n "$NS_APP" scale deploy "$POLLER" --replicas=1 >/dev/null || true
  fi
}
cleanup() {
  code=$?
  # kill + wait so the shell reaps the port-forward quietly (else bash prints "Terminated: 15").
  if [ -n "$PF_PID" ]; then kill "$PF_PID" >/dev/null 2>&1 || true; wait "$PF_PID" 2>/dev/null || true; fi
  [ "$FAULT_STAGED" = "1" ] && restore_outage
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
pf_ok=0
for _ in $(seq 1 20); do
  curl -fsS -m 2 "http://127.0.0.1:$PF_PORT/api/health" >/dev/null 2>&1 && { pf_ok=1; break; }
  sleep 1
done
if [ "$pf_ok" != "1" ]; then
  echo "ABORT: Grafana never answered /api/health via the port-forward (port $PF_PORT busy? pod not"
  echo "Ready?) — fix that before drilling. Override the local port with PF_PORT=<n>."
  exit 1
fi

# Returns the current state of the drilled alert ($ALERTNAME), NORMALIZED to: Alerting / Pending /
# Normal / api-error. The alerts endpoint only lists ACTIVE (pending/firing) instances — absence
# means Normal — and Grafana versions vary between its own capitalized enum ("Alerting") and
# Prometheus-style lowercase ("firing"), so both vocabularies are folded in here (review catch
# on #86: a casing mismatch would spin the drill through the full timeout with the alert visibly
# firing).
alert_state() {
  curl -fsS -m 10 -u "$GF_USER:$GF_PASS" \
    "http://127.0.0.1:$PF_PORT/api/prometheus/grafana/api/v1/alerts" 2>/dev/null | python3 -c '
import sys, json, os
try:
    alerts = json.load(sys.stdin)["data"]["alerts"]
except Exception:
    print("api-error"); sys.exit(0)
states = [str(a.get("state", "")).lower() for a in alerts
          if a.get("labels", {}).get("alertname") == os.environ["ALERTNAME"]]
if any(s in ("alerting", "firing") for s in states):
    print("Alerting")
elif any(s == "pending" for s in states):
    print("Pending")
else:
    print("Normal")'
}

state=$(alert_state)
if [ "$state" != "Normal" ]; then
  echo "ABORT: '$ALERTNAME' is already $state — the cluster is not in a clean baseline state."
  exit 1
fi

# ── 1. pause auto-sync (stall only), 2. stage the outage ────────────────────────────────────────
if [ "$MODE" = "ingest" ]; then
  echo "=== Alert fire drill [$MODE]: staging an invalid regs.gov key (expect ~35-40m to fire; see header) ==="
  # Inject at the source: patch Vault with a syntactically-plausible-but-invalid key. The seed
  # script force-syncs ESO and rolls the poller, so the regs pass starts 403ing on its next cycle.
  # No Deployment drift → no auto-sync pause needed.
  FAULT_STAGED=1
  REGS_API_KEY="drill-invalid-key-do-not-use-0000000000" bash "$HERE/seed-docketclock-secrets.sh"
  echo "invalid key seeded at $(date '+%H:%M:%S'). Waiting for '$ALERTNAME' to fire..."
else
  echo "=== Alert fire drill [$MODE]: staging a real poller outage (expect ~10-15m to fire; see header) ==="
  # 2>/dev/null: on a cluster where docketclock is Helm/Tilt-managed the Argo app doesn't exist —
  # that's the same "nothing to pause" case as auto-sync being off, not an error.
  if [ -n "$(kubectl -n argocd get application docketclock -o jsonpath='{.spec.syncPolicy.automated}' 2>/dev/null)" ]; then
    kubectl -n argocd patch application docketclock --type=json \
      -p '[{"op":"remove","path":"/spec/syncPolicy/automated"}]' >/dev/null
    AUTOMATION_PAUSED=1
    echo "docketclock auto-sync paused (selfHeal would revert the outage)."
  else
    echo "no Argo-managed docketclock auto-sync to pause (Helm/Tilt-managed, or already off) — proceeding."
  fi
  FAULT_STAGED=1
  kubectl -n "$NS_APP" scale deploy "$POLLER" --replicas=0 >/dev/null
  echo "poller scaled to 0 at $(date '+%H:%M:%S'). Waiting for '$ALERTNAME' to fire..."
fi

# ── wait for FIRING ──────────────────────────────────────────────────────────────────────────────
if [ "$MODE" = "ingest" ]; then
  FIRE_HINT="3 failed 15m cycles + for:5m fires ~t+36m"
  RESOLVE_HINT="the [1h] window ages the failures out — expect ~30-60m"
else
  FIRE_HINT="scale-to-0 fires ~t+13m; hung-poller path would be ~t+55-60m"
  RESOLVE_HINT="first settled cycle + eval"
fi
fired=0
for i in $(seq 1 $((FIRE_TIMEOUT_MIN))); do
  sleep 60
  state=$(alert_state)
  if [ "$state" = "Alerting" ]; then fired=1; break; fi
  [ $((i % 5)) -eq 0 ] && echo "  t+${i}m: alert state = $state ($FIRE_HINT)"
done
if [ "$fired" != "1" ]; then
  echo "FAIL: '$ALERTNAME' did not fire within ${FIRE_TIMEOUT_MIN}m — rule or datasource broken."
  exit 1
fi
echo "🔥 '$ALERTNAME' is FIRING at $(date '+%H:%M:%S')."

read -r -p "Did the ntfy notification arrive ON YOUR PHONE? [y/N] " got_page

# ── restore + wait for RESOLVE (the trap also restores on ^C/failure; do it now, visibly) ───────
restore_outage
FAULT_STAGED=0
echo "outage restored. Waiting for the alert to resolve ($RESOLVE_HINT)..."
resolved=0
for i in $(seq 1 $((RESOLVE_TIMEOUT_MIN))); do
  sleep 60
  state=$(alert_state)
  if [ "$state" = "Normal" ]; then resolved=1; break; fi
  [ $((i % 5)) -eq 0 ] && echo "  t+${i}m: alert state = $state"
done
if [ "$resolved" != "1" ]; then
  echo "FAIL: alert did not resolve within ${RESOLVE_TIMEOUT_MIN}m of restore — investigate before trusting the path."
  exit 1
fi
echo "✅ alert resolved at $(date '+%H:%M:%S')."

read -r -p "Did the RESOLVED notification arrive on your phone? [y/N] " got_resolve

if [ "$MODE" = "stall" ]; then
  echo
  echo "=== Dead-man half (manual — the wait is ~2h of ping absence) ==="
  echo "  1. pause the deadman app's auto-sync, then suspend the CronJob:"
  echo "       kubectl -n argocd patch application deadman --type=json -p '[{\"op\":\"remove\",\"path\":\"/spec/syncPolicy/automated\"}]'"
  echo "       kubectl -n observability patch cronjob deadman-ping -p '{\"spec\":{\"suspend\":true}}'"
  echo "  2. wait for the healthchecks.io ABSENCE page (check period 1h + grace 1h)"
  echo "  3. restore: unsuspend + re-enable — or simply: task -d infra platform (git is truth)"
  echo
fi

case "$got_page" in y|Y) :;; *) echo "=== Drill: FAILED (firing page never reached the phone) ==="; exit 1;; esac
case "$got_resolve" in y|Y) :;; *) echo "=== Drill: FAILED (resolve notification never reached the phone) ==="; exit 1;; esac
echo "=== Drill: PASSED — the alert path has now actually paged a human. Log the date in infra/README.md's cadence note. ==="
