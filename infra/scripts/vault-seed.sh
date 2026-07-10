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

echo "🌱 seeding secret/docketclock/external (regs_api_key, docketclock_api_keys, gemini_api_key, webhook_hmac_secret)..."
# These four keys MUST match charts/.../values.yaml externalSecret.keys — ESO is all-or-nothing, so a
# missing key (previously docketclock_api_keys) fails the whole sync. Real values flow from the HOST
# shell env (REGS_API_KEY etc.) with dev-* fallbacks so `task dev-up` stays reproducible. gemini_api_key
# defaults to EMPTY: ESO still finds the key (sync goes green) but the poller sees an empty GEMINI_API_KEY
# and runs null:abstain — dormant until a real key is seeded.
#
# SHELL-QUOTING CONSTRAINT: the host string below is DOUBLE-quoted, so ${VAR:-default} expands on the
# HOST before kubectl ships it; the single-quotes then wrap each value for the pod's `sh`. Correct ONLY
# if values contain no single-quote (') char — fine for API keys / dev placeholders.
kubectl -n vault exec vault-0 -- sh -c "
  export VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=$ROOT_TOKEN
  vault kv put secret/docketclock/external \
    regs_api_key='${REGS_API_KEY:-dev-regs-key}' \
    docketclock_api_keys='${DOCKETCLOCK_API_KEYS:-dev-docketclock-key}' \
    gemini_api_key='${GEMINI_API_KEY:-}' \
    webhook_hmac_secret='${WEBHOOK_HMAC_SECRET:-dev-hmac-secret}'
"

echo "🌱 seeding secret/observability/grafana (admin_user, admin_password) for the Grafana ESO secret..."
# Grafana's grafana-admin ExternalSecret (infra/argocd/apps/platform-grafana.yaml) reads these two keys;
# without them the Grafana pod stalls in CreateContainerConfigError and its Argo app reports Degraded.
# Seeded here (symmetry with the docketclock block) so the observability stack comes up healthy with no
# manual step. Local-dev default is admin/admin (Grafana forces a password change on first login);
# override via GRAFANA_ADMIN_USER / GRAFANA_ADMIN_PASSWORD. Same host-side ${VAR:-default} expansion +
# single-quote wrapping as the docketclock block above.
kubectl -n vault exec vault-0 -- sh -c "
  export VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=$ROOT_TOKEN
  vault kv put secret/observability/grafana \
    admin_user='${GRAFANA_ADMIN_USER:-admin}' \
    admin_password='${GRAFANA_ADMIN_PASSWORD:-admin}'
"

echo "🌱 seeding secret/langfuse/config (Langfuse v2 server crypto + headless-init keypair)..."
# Langfuse's langfuse-secrets ExternalSecret (infra/argocd/manifests/langfuse/externalsecret.yaml) reads
# these six keys; missing any one fails the whole ESO sync (all-or-nothing). DEV DEFAULTS are FIXED (not
# randomized) on purpose: re-running vault-seed must NOT rotate encryption_key, or Langfuse can no longer
# decrypt previously-stored data. encryption_key MUST be exactly 64 hex chars (ENCRYPTION_KEY contract).
# The init_project_*_key pair is pinned here so the SAME keypair flows to BOTH Langfuse (LANGFUSE_INIT_*)
# and the poller (PR-C2) with no manual UI step. Override any of them via the LANGFUSE_* host env.
kubectl -n vault exec vault-0 -- sh -c "
  export VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=$ROOT_TOKEN
  vault kv put secret/langfuse/config \
    nextauth_secret='${LANGFUSE_NEXTAUTH_SECRET:-dev-langfuse-nextauth-secret}' \
    salt='${LANGFUSE_SALT:-dev-langfuse-salt}' \
    encryption_key='${LANGFUSE_ENCRYPTION_KEY:-0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef}' \
    init_project_public_key='${LANGFUSE_PUBLIC_KEY:-pk-lf-dev-docketclock}' \
    init_project_secret_key='${LANGFUSE_SECRET_KEY:-sk-lf-dev-docketclock}' \
    init_user_password='${LANGFUSE_USER_PASSWORD:-docketclock-dev}'
"

echo "🌱 seeding secret/backups/minio + secret/backups/r2 (backup seams — backups PR-1)..."
# UNLIKE the fixed-default blocks above, these two are seeded ONCE and then left alone on re-runs:
#  - backups/minio: the root password is GENERATED (host-side openssl, never printed). The MinIO
#    StatefulSet, the CNPG ObjectStores (PR-2), and the rclone/pg_dump/vault-snapshot CronJobs (PR-3/4)
#    all read these creds — a re-seed that rotated them would strand every consumer at once.
#  - backups/r2: placeholders now; the REAL Cloudflare R2 token is patched in at PR-3 via the
#    seed-docketclock-secrets.sh pattern — an unguarded re-seed would clobber the patched values.
kv_missing() { # true iff the kv path has no live version yet (so we only ever seed it once)
  ! kubectl -n vault exec vault-0 -- sh -c \
    "export VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=$ROOT_TOKEN; vault kv get $1" >/dev/null 2>&1
}
if kv_missing secret/backups/minio; then
  MINIO_PW="${MINIO_ROOT_PASSWORD:-$(openssl rand -hex 24)}"
  kubectl -n vault exec vault-0 -- sh -c "
    export VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=$ROOT_TOKEN
    vault kv put secret/backups/minio \
      root_user='${MINIO_ROOT_USER:-minio-root}' \
      root_password='$MINIO_PW'
  " >/dev/null # suppress vault's echo of written metadata (never print secret material)
  unset MINIO_PW
  echo "  ↳ seeded secret/backups/minio (generated root credentials)."
else
  echo "  ↳ secret/backups/minio already seeded — leaving as-is (no rotation on re-run)."
fi
if kv_missing secret/backups/r2; then
  kubectl -n vault exec vault-0 -- sh -c "
    export VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=$ROOT_TOKEN
    vault kv put secret/backups/r2 \
      access_key_id='placeholder' \
      secret_access_key='placeholder' \
      endpoint='https://PLACEHOLDER-ACCOUNT-ID.r2.cloudflarestorage.com'
  " >/dev/null
  echo "  ↳ seeded secret/backups/r2 (placeholders — patch real values at PR-3)."
else
  echo "  ↳ secret/backups/r2 already seeded — leaving as-is (patched values preserved)."
fi

echo "🔑 wiring ESO → Vault token auth (external-secrets/vault-token)..."
kubectl create namespace external-secrets --dry-run=client -o yaml | kubectl apply -f -
kubectl -n external-secrets create secret generic vault-token \
  --from-literal=token="$ROOT_TOKEN" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "✅ vault-seed complete."
