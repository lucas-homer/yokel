#!/usr/bin/env bash
set -euo pipefail
# Unseal the PERSISTENT transit Vault (vault-transit) from its stored unseal key. Idempotent: a no-op if
# already unsealed. The transit Vault is standalone+PVC (NOT dev-mode), so it starts SEALED on every pod
# start; until it is unsealed the main Vault cannot auto-unseal against it. Called by:
#   • vault-transit-init.sh  — right after init, to bring the freshly-initialized transit Vault online;
#   • task cluster-restart   — after a colima/Docker restart, to re-unseal before the main Vault retries.
# Requires the `vault-transit-keys` Secret (created by vault-transit-init.sh) — fails loudly if absent.

VAULT_ADDR_IN_POD="http://127.0.0.1:8200"

echo "⏳ waiting for the transit Vault API to respond..."
until kubectl -n vault get pod vault-transit-0 >/dev/null 2>&1; do sleep 2; done
# Poll the API, NOT pod-Ready: a sealed Vault is never Ready. `vault status` prints JSON (with a "sealed"
# field) and exits 2 when sealed — capture to a var first so pipefail doesn't poison the loop (mirrors the
# pattern in vault-seed.sh).
attempts=0
while :; do
  status_json=$(kubectl -n vault exec vault-transit-0 -- sh -c \
    "export VAULT_ADDR=$VAULT_ADDR_IN_POD; vault status -format=json 2>/dev/null" 2>/dev/null || true)
  printf '%s' "$status_json" | grep -q '"sealed"' && break
  attempts=$((attempts + 1))
  if [ "$attempts" -ge 60 ]; then echo "✗ transit Vault API never responded (120s)"; exit 1; fi
  sleep 2
done

if ! kubectl -n vault get secret vault-transit-keys >/dev/null 2>&1; then
  echo "✗ vault-transit-keys Secret not found — run vault-transit-init.sh first." >&2
  exit 1
fi

SEALED=$(printf '%s' "$status_json" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["sealed"])' 2>/dev/null || echo unknown)

if [ "$SEALED" = "False" ]; then
  echo "↩︎  transit Vault already unsealed."
  exit 0
fi

UNSEAL_KEY=$(kubectl -n vault get secret vault-transit-keys -o jsonpath='{.data.unseal_key}' | base64 -d)
echo "🔓 unsealing transit Vault..."
# Single-quote the key for the pod's sh — unseal keys are base64 (no single-quote char), so this is safe.
kubectl -n vault exec vault-transit-0 -- sh -c \
  "export VAULT_ADDR=$VAULT_ADDR_IN_POD; vault operator unseal '$UNSEAL_KEY'" >/dev/null
echo "✅ transit Vault unsealed."
