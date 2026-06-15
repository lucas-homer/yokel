output "bucket_name" {
  description = "Backup bucket name."
  value       = var.bucket_name
}

output "backup_endpoint" {
  description = "S3-compatible endpoint for CNPG barman-cloud (filled by the provider implementation)."
  value       = null
}
