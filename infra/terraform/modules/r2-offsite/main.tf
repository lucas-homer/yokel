# Cloudflare R2 offsite backup target — backups PR-3 (plans/backups-restore-drill.md). IaC-not-clickops:
# the bucket AND its scoped credential are Terraform-managed; the only hand-held credential is the
# bootstrap CLOUDFLARE_API_TOKEN in the operator's env (see envs/backups/README notes).
#
# The in-cluster rclone CronJob mirrors MinIO → this bucket hourly; retention is enforced at the
# MinIO source (barman retentionPolicy + ILM rules) and the mirror inherits it. This module is also
# the concrete provider candidate for the phase-3 cnpg-backups stub (same S3-compatible seam).

terraform {
  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.0"
    }
  }
}

resource "cloudflare_r2_bucket" "offsite" {
  account_id = var.account_id
  name       = var.bucket_name
  location   = var.location
}

# Look the R2 permission-group IDs up by name instead of hardcoding magic IDs — they differ per
# Cloudflare deployment era and the data source is the stable seam.
data "cloudflare_account_api_token_permission_groups" "all" {
  account_id = var.account_id
}

locals {
  r2_item_read = one([
    for g in data.cloudflare_account_api_token_permission_groups.all.permission_groups :
    g.id if g.name == "Workers R2 Storage Bucket Item Read"
  ])
  r2_item_write = one([
    for g in data.cloudflare_account_api_token_permission_groups.all.permission_groups :
    g.id if g.name == "Workers R2 Storage Bucket Item Write"
  ])
  # R2 bucket resource id in token policies: <account>_<jurisdiction>_<bucket>; ours is default-jurisdiction.
  bucket_resource = "com.cloudflare.edge.r2.bucket.${var.account_id}_default_${cloudflare_r2_bucket.offsite.name}"
}

# Account-owned API token scoped to ONLY this bucket, read+write objects — the credential the
# in-cluster mirror uses. Its S3-compatible keypair is derived in outputs.tf (Cloudflare convention:
# access key = token id, secret key = SHA-256 of the token value).
resource "cloudflare_account_token" "r2_backups" {
  account_id = var.account_id
  name       = "${var.bucket_name}-mirror-rw"
  policies = [{
    effect = "allow"
    permission_groups = [
      { id = local.r2_item_read },
      { id = local.r2_item_write },
    ]
    resources = jsonencode({ (local.bucket_resource) = "*" })
  }]
}
