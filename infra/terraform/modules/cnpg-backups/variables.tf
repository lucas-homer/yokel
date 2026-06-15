variable "bucket_name" {
  type        = string
  description = "Object-storage bucket for CloudNativePG PITR backups (barman-cloud)."
}

variable "region" {
  type        = string
  description = "Cloud region for the backup bucket."
}
