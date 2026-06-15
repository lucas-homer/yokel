#!/usr/bin/env bash
set -euo pipefail
# Initialize the main Vault (auto-unsealed via the transit seal), seed DocketClock's external-origin
# secrets, and wire ESO token auth. Idempotent: safe to re-run.
#
# DEV ONLY. The main Vault is HA-raft with a transit auto-unseal seal (see platform-vault.yaml), so on
# first run it is UNINITIALIZED — we `operator init` it (recovery keys, since unseal is automatic) and
# stash the root token + recovery keys in the `vault/vault-root-token` Secret so re-runs reuse them.
# That stored root token is a dev convenience; prod uses the Kubernetes auth method, not a root token
# in a Secret (see charts/docketclock/values-cloud.yaml). Run vault-transit-init.sh FIRST.

echo "⏳ waiting for the main Vault API to respond..."
# Poll the API, NOT pod phase/Ready: an uninitialized Vault never becomes Ready (we init it below), and
# pod-phase=Running can flip before the `vault` container is execable (→ "container not found"). Once
# `vault status` prints (even "Initialized false"), the container is up and the API is listening.
# Capture to a var first: `vault status` exits 2 when sealed/uninitialized, which would poison an
# `exec | grep` pipe under `set -o pipefail` and loop forever even though grep matched.
attempts=0
while :; do
  status_out=$(kubectl -n vault exec vault-0 -- sh -c 'export VAULT_ADDR=http://127.0.0.1:8200; vault status 2>&1' 2>/dev/null || true)
  printf '%s' "$status_out" | grep -q 'Initialized' && break
  attempts=$((attempts + 1))
  if [ "$attempts" -ge 80 ]; then echo "✗ Vault API never responded (240s)"; exit 1; fi
  sleep 3
done

if kubectl -n vault get secret vault-root-token >/dev/null 2>&1; then
  echo "↩︎  Vault already initialized; reusing the stored root token."
  ROOT_TOKEN=$(kubectl -n vault get secret vault-root-token -o jsonpath='{.data.token}' | base64 -d)
else
  echo "🔓 initializing Vault (auto-unseals via the transit seal; capturing recovery keys)..."
  INIT_JSON=$(kubectl -n vault exec vault-0 -- sh -c \
    'export VAULT_ADDR=http://127.0.0.1:8200; vault operator init -recovery-shares=1 -recovery-threshold=1 -format=json')
  ROOT_TOKEN=$(printf '%s' "$INIT_JSON" | python3 -c 'import sys,json; print(json.load(sys.stdin)["root_token"])')
  # Stash root token + full init output (recovery keys) — dev recovery aid; never do this in prod.
  kubectl -n vault create secret generic vault-root-token \
    --from-literal=token="$ROOT_TOKEN" \
    --from-literal=init.json="$INIT_JSON" \
    --dry-run=client -o yaml | kubectl apply -f -
fi

echo "⏳ waiting for Vault to finish auto-unsealing..."
kubectl -n vault wait --for=condition=Ready pod/vault-0 --timeout=180s

echo "🗄  ensuring kv-v2 engine at secret/ (dev mode auto-mounts this; HA-raft does not)..."
kubectl -n vault exec vault-0 -- sh -c "
  export VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=$ROOT_TOKEN
  vault secrets enable -version=2 -path=secret kv 2>/dev/null || true   # no-op if already mounted
"

echo "🌱 seeding secret/docketclock/external (dev placeholder values)..."
kubectl -n vault exec vault-0 -- sh -c "
  export VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=$ROOT_TOKEN
  vault kv put secret/docketclock/external \
    regs_api_key='dev-regs-key' \
    anthropic_api_key='dev-anthropic-key' \
    webhook_hmac_secret='dev-hmac-secret'
"

echo "🔑 wiring ESO → Vault token auth (external-secrets/vault-token)..."
kubectl create namespace external-secrets --dry-run=client -o yaml | kubectl apply -f -
kubectl -n external-secrets create secret generic vault-token \
  --from-literal=token="$ROOT_TOKEN" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "✅ vault-seed complete."
