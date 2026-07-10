# Backups env — LIVE TODAY (unlike envs/cloud, the phase-3 stub): provisions the Cloudflare R2
# offsite mirror target for the backups phase (plans/backups-restore-drill.md, PR-3).
#
# Operator loop (one-time + on drift):
#   export CLOUDFLARE_API_TOKEN=...            # bootstrap credential, env only
#   cp terraform.tfvars.example terraform.tfvars   # fill the account id
#   terraform init && terraform apply
#   bash ../../../scripts/seed-r2-secrets.sh   # pushes the outputs into Vault (secret/backups/r2)

module "r2_offsite" {
  source     = "../../modules/r2-offsite"
  account_id = var.cloudflare_account_id
}

output "bucket_name" {
  value = module.r2_offsite.bucket_name
}

output "endpoint" {
  value = module.r2_offsite.endpoint
}

output "access_key_id" {
  value = module.r2_offsite.access_key_id
}

output "secret_access_key" {
  value     = module.r2_offsite.secret_access_key
  sensitive = true
}
