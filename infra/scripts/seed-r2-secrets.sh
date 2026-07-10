#!/usr/bin/env bash
set -euo pipefail
# Push the Terraform-managed R2 credentials (infra/terraform/envs/backups outputs) into Vault at
# secret/backups/r2, replacing the placeholders vault-seed.sh stubbed. Run AFTER `terraform apply`
# in envs/backups. Idempotent; safe to re-run after a token rotation (taint + re-apply in TF).
#
# SECRET HYGIENE: values flow terraform → python (in-process) → stdin of `vault kv put -` (which
# reads ALL fields as JSON from stdin) — never argv, never echoed, never on disk.

TF_DIR="$(cd "$(dirname "$0")/../terraform/envs/backups" && pwd)"

echo "⏳ reading terraform outputs from $TF_DIR..."
TF_JSON=$(terraform -chdir="$TF_DIR" output -json)
for key in endpoint access_key_id secret_access_key; do
  printf '%s' "$TF_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['$key']['value'], '$key empty'" \
    || { echo "✗ terraform output '$key' missing/empty — did 'terraform apply' run?"; exit 1; }
done

echo "🔑 fetching the Vault root token (dev convenience Secret)..."
ROOT_TOKEN=$(kubectl -n vault get secret vault-root-token -o jsonpath='{.data.token}' | base64 -d)

echo "🌱 writing secret/backups/r2 (endpoint + bucket-scoped S3 keypair; values via stdin only)..."
printf '%s' "$TF_JSON" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(json.dumps({k: d[k]['value'] for k in ('endpoint', 'access_key_id', 'secret_access_key')}))
" | kubectl -n vault exec -i vault-0 -- sh -c \
  "export VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=$ROOT_TOKEN; vault kv put secret/backups/r2 -" \
  >/dev/null # suppress vault's written-metadata echo

echo "🔄 force-syncing the r2-creds ExternalSecret (skips the ~1h refreshInterval)..."
kubectl -n backups annotate externalsecret r2-creds "force-sync=$(date +%s)" --overwrite >/dev/null

echo "✅ R2 creds seeded. The hourly r2-mirror CronJob picks them up at its next tick (CronJob pods"
echo "   re-read Secrets per run — no restart needed). Trigger one now to verify:"
echo "   kubectl -n backups create job --from=cronjob/r2-mirror r2-mirror-manual-\$(date +%s)"
