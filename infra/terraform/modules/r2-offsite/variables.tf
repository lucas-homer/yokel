variable "account_id" {
  type        = string
  description = "Cloudflare account ID (dash → R2 → account details, or `wrangler whoami`)."
}

variable "bucket_name" {
  type        = string
  default     = "yokel-backups"
  description = "R2 bucket for the offsite backup mirror (the backups phase's fixed name)."
}

variable "location" {
  type        = string
  default     = "wnam"
  description = "R2 location hint (wnam/enam/weur/eeur/apac). wnam = US-west-ish, closest to the Mini."
}
