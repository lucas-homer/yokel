#!/usr/bin/env bash
set -euo pipefail
# Enable the transit engine + autounseal key on the LOCAL seal-provider Vault (`vault-transit`).
# This is the local stand-in for cloud KMS: the main Vault's `seal "transit"` stanza unseals against
# the `autounseal` key created here. Idempotent. DEV ONLY (transit Vault is dev-mode, token "transit-root").
# In cloud there is no transit Vault — the main Vault seals against a real KMS, so this step doesn't run.

echo "⏳ waiting for transit Vault (the seal provider)..."
until kubectl -n vault get pod vault-transit-0 >/dev/null 2>&1; do sleep 2; done
kubectl -n vault wait --for=condition=Ready pod/vault-transit-0 --timeout=240s

echo "🔐 enabling transit engine + 'autounseal' key (idempotent)..."
kubectl -n vault exec vault-transit-0 -- sh -c '
  export VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=transit-root
  vault secrets enable transit 2>/dev/null || true        # no-op if already enabled
  vault write -f transit/keys/autounseal 2>/dev/null || true   # no-op if the key already exists
'
echo "✅ transit seal ready (vault-transit holds the autounseal key)."
