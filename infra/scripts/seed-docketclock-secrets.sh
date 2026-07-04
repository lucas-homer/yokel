#!/usr/bin/env bash
# seed-docketclock-secrets.sh — patch one or more docketclock-external keys into Vault (local k3d),
# re-sync ESO, and restart whichever workload reads them. A convenience wrapper around the same
# secret/docketclock/external path that infra/scripts/vault-seed.sh seeds at bring-up.
#
# Supply values via ENV VARS (never hardcoded, never printed). Only the ones you set are touched —
# `kv patch` leaves the other fields intact:
#
#   REGS_API_KEY          -> regs_api_key          (poller: regulations.gov polling)
#   GEMINI_API_KEY        -> gemini_api_key         (poller: chain-seam LLM adjudicator)
#   DOCKETCLOCK_API_KEYS  -> docketclock_api_keys   (API: X-Api-Key auth; comma-separated)
#   WEBHOOK_HMAC_SECRET   -> webhook_hmac_secret    (delivery webhook signing)
#
# Both the Vault root token and each value are passed to the pod via STDIN (never argv), so nothing
# sensitive shows up in `ps` on the host or in the pod. Values are never echoed — only their length.
#
# Usage:
#   REGS_API_KEY=xxxx bash infra/scripts/seed-docketclock-secrets.sh
#   GEMINI_API_KEY=xxxx REGS_API_KEY=yyyy bash infra/scripts/seed-docketclock-secrets.sh
set -euo pipefail

NS_VAULT=vault
NS_APP=docketclock

# env-var name -> vault field name. (kept parallel so the loop maps host env → stored key)
FIELDS="REGS_API_KEY:regs_api_key GEMINI_API_KEY:gemini_api_key DOCKETCLOCK_API_KEYS:docketclock_api_keys WEBHOOK_HMAC_SECRET:webhook_hmac_secret"

# --- Preflight: gather which keys were provided --------------------------------------------------------
provided=""
restart_poller=false
restart_api=false
for pair in $FIELDS; do
  env_name=${pair%%:*}; field=${pair##*:}
  # indirect expansion: value of the env var whose NAME is in $env_name
  val=${!env_name:-}
  [ -z "$val" ] && continue
  provided="$provided $pair"
  case "$field" in
    regs_api_key | gemini_api_key) restart_poller=true ;;
    docketclock_api_keys) restart_api=true ;;
  esac
done
if [ -z "$provided" ]; then
  echo "✗ No key env vars set. Set at least one of REGS_API_KEY / GEMINI_API_KEY /" >&2
  echo "  DOCKETCLOCK_API_KEYS / WEBHOOK_HMAC_SECRET, e.g.:" >&2
  echo "    REGS_API_KEY=your-key bash $0" >&2
  exit 1
fi
if ! kubectl -n "$NS_VAULT" get secret vault-root-token >/dev/null 2>&1; then
  echo "✗ vault-root-token Secret not found — is the cluster up and Vault seeded? (task status)" >&2
  exit 1
fi
ROOT_TOKEN=$(kubectl -n "$NS_VAULT" get secret vault-root-token -o jsonpath='{.data.token}' | base64 -d)

# --- 1. Patch each provided key (root token + value both via stdin; value piped to vault via `=-`) -----
for pair in $provided; do
  env_name=${pair%%:*}; field=${pair##*:}
  val=${!env_name}
  echo "🌱 patching $field into secret/docketclock/external (value not shown)…"
  kubectl -n "$NS_VAULT" exec -i vault-0 -- sh -c '
    set -e
    export VAULT_ADDR=http://127.0.0.1:8200
    IFS= read -r VAULT_TOKEN; export VAULT_TOKEN
    IFS= read -r FIELD
    IFS= read -r VALUE
    printf "%s" "$VALUE" | vault kv patch secret/docketclock/external "$FIELD=-" >/dev/null
    n=$(vault kv get -field="$FIELD" secret/docketclock/external | wc -c | tr -d " ")
    echo "  ✓ stored ($FIELD length: $n)"
  ' <<EOF
$ROOT_TOKEN
$field
$val
EOF
done

# --- 2. Force ESO to re-sync the materialized Secret --------------------------------------------------
echo "🔄 forcing ESO re-sync of docketclock-external…"
kubectl -n "$NS_APP" annotate externalsecret docketclock-external "force-sync=$(date +%s)" --overwrite >/dev/null
kubectl -n "$NS_APP" wait --for=condition=Ready externalsecret/docketclock-external --timeout=60s >/dev/null
sleep 3

# --- 3. Restart whichever workload reads the changed keys (secretKeyRef env is read at pod start) ------
if $restart_poller; then
  echo "♻️  restarting the poller…"
  kubectl -n "$NS_APP" rollout restart deploy/docketclock-poller >/dev/null
  kubectl -n "$NS_APP" rollout status deploy/docketclock-poller --timeout=120s
fi
if $restart_api; then
  echo "♻️  restarting the API…"
  kubectl -n "$NS_APP" rollout restart deploy/docketclock >/dev/null
  kubectl -n "$NS_APP" rollout status deploy/docketclock --timeout=120s
fi

echo
echo "✅ Done. Verify a poll cycle picked up the change:"
echo "   kubectl -n docketclock logs deploy/docketclock-poller --tail=40 | grep -iE 'regs poll cycle|regs poll failed'"
