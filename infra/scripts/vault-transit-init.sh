#!/usr/bin/env bash
set -euo pipefail
# Initialize + unseal the PERSISTENT local seal-provider Vault (`vault-transit`) and create the
# `autounseal` transit key the main Vault seals against. Idempotent. DEV ONLY — vault-transit is the local
# stand-in for cloud KMS (in cloud the main Vault seals against a real KMS, so this step doesn't run).
#
# vault-transit is now standalone + PVC (NOT dev-mode), so unlike before:
#   • it starts SEALED + uninitialized → we `operator init` it ONCE (1 key-share; Shamir, since the seal
#     provider itself has nothing to auto-unseal against) and stash the unseal key + root token in the
#     `vault-transit-keys` Secret so restarts can re-unseal it (vault-transit-unseal.sh);
#   • the `autounseal` transit key now PERSISTS on the PVC, so the main Vault's data stays decryptable
#     across restarts — no more "lost key → unrecoverable Vault" re-bootstrap.
# The stored root token is ALSO injected into the main Vault as VAULT_TOKEN for its transit-seal auth
# (see platform-vault.yaml). Run this FIRST (before vault-seed.sh).

VAULT_ADDR_IN_POD="http://127.0.0.1:8200"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "⏳ waiting for the transit Vault API (standalone starts sealed + uninitialized)..."
until kubectl -n vault get pod vault-transit-0 >/dev/null 2>&1; do sleep 2; done
attempts=0
while :; do
  status_json=$(kubectl -n vault exec vault-transit-0 -- sh -c \
    "export VAULT_ADDR=$VAULT_ADDR_IN_POD; vault status -format=json 2>/dev/null" 2>/dev/null || true)
  printf '%s' "$status_json" | grep -q '"sealed"' && break
  attempts=$((attempts + 1))
  if [ "$attempts" -ge 80 ]; then echo "✗ transit Vault API never responded (240s)"; exit 1; fi
  sleep 3
done

if kubectl -n vault get secret vault-transit-keys >/dev/null 2>&1; then
  echo "↩︎  transit Vault already initialized; reusing the stored keys."
  ROOT_TOKEN=$(kubectl -n vault get secret vault-transit-keys -o jsonpath='{.data.root_token}' | base64 -d)
else
  echo "🔓 initializing the transit Vault (1 unseal key-share; stashing keys for restart-unseal)..."
  INIT_JSON=$(kubectl -n vault exec vault-transit-0 -- sh -c \
    "export VAULT_ADDR=$VAULT_ADDR_IN_POD; vault operator init -key-shares=1 -key-threshold=1 -format=json")
  ROOT_TOKEN=$(printf '%s' "$INIT_JSON" | python3 -c 'import sys,json; print(json.load(sys.stdin)["root_token"])')
  UNSEAL_KEY=$(printf '%s' "$INIT_JSON" | python3 -c 'import sys,json; print(json.load(sys.stdin)["unseal_keys_b64"][0])')
  # Stash unseal key + root token (+ full init output) — dev recovery aid; never do this in prod.
  kubectl -n vault create secret generic vault-transit-keys \
    --from-literal=unseal_key="$UNSEAL_KEY" \
    --from-literal=root_token="$ROOT_TOKEN" \
    --from-literal=init.json="$INIT_JSON" \
    --dry-run=client -o yaml | kubectl apply -f -
fi

# Unseal (idempotent) so the transit engine is reachable for the writes below + the main Vault's seal.
bash "$SCRIPT_DIR/vault-transit-unseal.sh"

echo "🔐 enabling the transit engine + 'autounseal' key (idempotent)..."
kubectl -n vault exec vault-transit-0 -- sh -c "
  export VAULT_ADDR=$VAULT_ADDR_IN_POD VAULT_TOKEN=$ROOT_TOKEN
  vault secrets enable transit 2>/dev/null || true        # no-op if already enabled
  vault write -f transit/keys/autounseal 2>/dev/null || true   # no-op if the key already exists
"

# Bounce the main Vault so it re-evaluates its VAULT_TOKEN env NOW. On first bring-up `platform` applies
# the main Vault BEFORE this script creates the vault-transit-keys Secret, so vault-0 sits in
# CreateContainerConfigError until kubelet's slow resync notices the Secret — which can outlast vault-seed's
# 240s poll on a slow box. Deleting the pod forces an immediate re-create that mounts the now-present token
# and auto-unseals against the transit key we just provisioned. No-op if vault-0 doesn't exist yet.
kubectl -n vault delete pod vault-0 --ignore-not-found >/dev/null 2>&1 || true

echo "✅ transit seal ready (persistent — the autounseal key survives restarts)."
