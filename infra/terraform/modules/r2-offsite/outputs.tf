output "bucket_name" {
  description = "The offsite mirror bucket."
  value       = cloudflare_r2_bucket.offsite.name
}

output "endpoint" {
  description = "S3-compatible R2 endpoint for this account."
  value       = "https://${var.account_id}.r2.cloudflarestorage.com"
}

output "access_key_id" {
  description = "S3 access key id for the bucket-scoped token (= the token's id)."
  value       = cloudflare_account_token.r2_backups.id
}

output "secret_access_key" {
  description = "S3 secret access key (= SHA-256 of the token value, per Cloudflare's R2 convention)."
  value       = sha256(cloudflare_account_token.r2_backups.value)
  sensitive   = true
}
