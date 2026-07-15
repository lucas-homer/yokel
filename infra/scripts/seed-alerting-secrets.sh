#!/usr/bin/env bash
set -euo pipefail
# Patch secret/observability/alerting with REAL alert-receiver values (Slice V / PR-V3), replacing
# the placeholders vault-seed.sh stubbed. Two consumers:
#   ntfy_url              -> Grafana's ntfy contact point (via the grafana-alerting ExternalSecret +
#                            envFromSecret; Grafana reads env at POD START, so we roll the Deployment)
#   healthchecks_ping_url -> the deadman-ping CronJob (per-run secretKeyRef; next tick picks it up)
#
# Inputs (all optional, all preserve-unless-overridden — a bare re-run never clobbers a real value):
#   NTFY_TOPIC             ntfy topic to publish alerts to. If unset and Vault still holds the
#                          placeholder, a random topic is GENERATED and printed (you must subscribe
#                          to it on your phone — treat it like a password: whoever knows the topic
#                          can read and spoof your alerts).
#   NTFY_SERVER            defaults to https://ntfy.sh
#   HEALTHCHECKS_PING_URL  the https://hc-ping.com/<uuid> URL of your healthchecks.io check
#                          (create it by hand: period 1h, grace 1h — pages within ~2h of silence).
#
# SECRET HYGIENE: values flow env/Vault → python (in-process) → stdin of `vault kv put -` — never
# argv on the pod side, never echoed (the generated topic is deliberately printed ONCE, see above).

ROOT_TOKEN=$(kubectl -n vault get secret vault-root-token -o jsonpath='{.data.token}' | base64 -d)
vault_exec() { # $1: pod-side command. The root token rides stdin LINE 1 (never argv — #75: exec
  # command strings land in apiserver audit logs and in-container `ps`); any `kv put -` payload
  # follows on the function's own stdin. Call sites with NO payload MUST redirect `</dev/null`
  # so `cat` sees EOF instead of waiting on the terminal.
  { printf '%s\n' "$ROOT_TOKEN"; cat; } | kubectl -n vault exec -i vault-0 -- sh -c \
    "export VAULT_ADDR=http://127.0.0.1:8200; IFS= read -r VAULT_TOKEN; export VAULT_TOKEN; $1"
}

echo "⏳ reading current secret/observability/alerting (preserve-unless-overridden)..."
EXISTING_JSON=$(vault_exec "vault kv get -format=json secret/observability/alerting" </dev/null 2>/dev/null || echo '{}')

# Remember the pre-write Secret value so we can wait for ESO to propagate the change below.
PRE=$(kubectl -n observability get secret grafana-alerting -o jsonpath='{.data.ALERTING_NTFY_URL}' 2>/dev/null || true)

echo "🌱 writing secret/observability/alerting (values via stdin only)..."
printf '%s' "$EXISTING_JSON" | NTFY_TOPIC="${NTFY_TOPIC:-}" NTFY_SERVER="${NTFY_SERVER:-https://ntfy.sh}" \
  HEALTHCHECKS_PING_URL="${HEALTHCHECKS_PING_URL:-}" python3 -c '
import json, os, secrets, sys

try:
    existing = json.load(sys.stdin)["data"]["data"]
except Exception:
    existing = {}

def is_placeholder(v):
    return not v or "PLACEHOLDER" in v or "127.0.0.1" in v

# ntfy: env topic wins; else keep a real existing URL; else generate a topic.
server = os.environ["NTFY_SERVER"].rstrip("/")
topic = os.environ["NTFY_TOPIC"]
if topic:
    ntfy_url = f"{server}/{topic}?template=grafana"
elif not is_placeholder(existing.get("ntfy_url")):
    ntfy_url = existing["ntfy_url"]
else:
    topic = "yokel-alerts-" + secrets.token_hex(6)
    ntfy_url = f"{server}/{topic}?template=grafana"
    print(f"🔔 generated ntfy topic: {topic}", file=sys.stderr)
    print(f"   SUBSCRIBE NOW in the ntfy app (or {server}/{topic}) — and note it somewhere safe;", file=sys.stderr)
    print(f"   it is printed only this once.", file=sys.stderr)

# healthchecks: env wins; else keep whatever is there (real or placeholder).
ping = os.environ["HEALTHCHECKS_PING_URL"] or existing.get("healthchecks_ping_url") or "PLACEHOLDER-run-seed-alerting-secrets"
if "PLACEHOLDER" in ping:
    print("⚠️  healthchecks_ping_url still a placeholder — deadman CronJob stays disarmed.", file=sys.stderr)
    print("   Create a check at healthchecks.io (period 1h, grace 1h), then re-run with", file=sys.stderr)
    print("   HEALTHCHECKS_PING_URL=https://hc-ping.com/<uuid> — the ntfy value will be preserved.", file=sys.stderr)

json.dump({"ntfy_url": ntfy_url, "healthchecks_ping_url": ping}, sys.stdout)
' | vault_exec "vault kv put secret/observability/alerting -" >/dev/null

echo "🔄 force-syncing the ExternalSecrets (skips the ~1h refreshInterval)..."
for es in grafana-alerting deadman-ping; do
  kubectl -n observability annotate externalsecret "$es" "force-sync=$(date +%s)" --overwrite >/dev/null 2>&1 \
    || echo "  ↳ externalsecret/$es not found yet (run 'task platform' first) — Argo will sync it with the new value"
done

# ESO propagates asynchronously; wait for the Secret to actually change before restarting Grafana,
# or the new pod boots with the OLD env. A timeout here usually just means a no-op re-run (value
# unchanged) — restarting is harmless either way.
if kubectl -n observability get secret grafana-alerting >/dev/null 2>&1; then
  for _ in $(seq 1 12); do
    POST=$(kubectl -n observability get secret grafana-alerting -o jsonpath='{.data.ALERTING_NTFY_URL}' 2>/dev/null || true)
    [ -n "$POST" ] && [ "$POST" != "$PRE" ] && break
    sleep 5
  done
  echo "🔁 restarting Grafana (contact-point env is read at pod start)..."
  kubectl -n observability rollout restart deploy/grafana >/dev/null
  kubectl -n observability rollout status deploy/grafana --timeout=180s >/dev/null
fi

echo "✅ alerting secrets seeded. Grafana alerts now publish to your ntfy topic; the deadman"
echo "   CronJob picks up its URL at the next hourly tick (per-run secretKeyRef, no restart)."
echo "   Prove the path end-to-end with: task -d infra alert-drill"
