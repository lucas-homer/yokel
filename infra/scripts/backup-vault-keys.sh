#!/usr/bin/env bash
set -euo pipefail
# ONE-TIME (backups PR-3): export the Vault seal chain — the vault-root-token and vault-transit-keys
# Secrets — age-ENCRYPTED, straight to R2. A raft snapshot (PR-4) is useless without these; with them,
# a total Mini loss can rebuild Vault (transit unseal key + root token + recovery keys).
#
# The plaintext NEVER touches disk or argv: kubectl → age (encrypt) → rclone rcat (stream upload).
# Decryption needs the age IDENTITY, which must live OFF the Mini (password manager / printed copy) —
# that identity is the root of this whole recovery path; treat it like the asset it protects.
#
# Prereqs: brew install age rclone;  terraform apply'd envs/backups;  AGE_RECIPIENT set:
#   age-keygen -o vault-backup-identity.txt   # DO THIS OFF-MINI (or move + delete after); the
#   export AGE_RECIPIENT=age1...              # public "recipient" line is what this script needs
#
# Re-run whenever the seal chain changes (re-init, transit key rotation) — uploads are date-stamped.

: "${AGE_RECIPIENT:?set AGE_RECIPIENT to the age public key (age1...) whose identity lives OFF this machine}"
command -v age >/dev/null || { echo "✗ age not installed (brew install age)"; exit 1; }
command -v rclone >/dev/null || { echo "✗ rclone not installed (brew install rclone)"; exit 1; }

TF_DIR="$(cd "$(dirname "$0")/../terraform/envs/backups" && pwd)"
TF_JSON=$(terraform -chdir="$TF_DIR" output -json)
r2() { printf '%s' "$TF_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['$1']['value'])"; }

# rclone remote defined entirely via env — no config file, no creds on disk.
export RCLONE_CONFIG_R2_TYPE=s3
export RCLONE_CONFIG_R2_PROVIDER=Cloudflare
export RCLONE_CONFIG_R2_ENDPOINT="$(r2 endpoint)"
export RCLONE_CONFIG_R2_ACCESS_KEY_ID="$(r2 access_key_id)"
export RCLONE_CONFIG_R2_SECRET_ACCESS_KEY="$(r2 secret_access_key)"
BUCKET="$(r2 bucket_name)"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)

for s in vault-root-token vault-transit-keys; do
  echo "🔐 $s → age → r2:$BUCKET/vault-seal-chain/$s-$STAMP.yaml.age"
  kubectl -n vault get secret "$s" -o yaml \
    | age -r "$AGE_RECIPIENT" \
    | rclone rcat "r2:$BUCKET/vault-seal-chain/$s-$STAMP.yaml.age"
done

echo "✅ seal chain exported (encrypted). Verify listing:"
rclone ls "r2:$BUCKET/vault-seal-chain/"
echo "REMINDER: the age identity (private key) must live OFF the Mini — without it these blobs are noise;"
echo "with it alone an attacker holds your Vault. Password manager or printed copy, documented in the runbook."
