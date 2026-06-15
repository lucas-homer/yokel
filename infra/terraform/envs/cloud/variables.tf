variable "cluster_name" {
  type        = string
  default     = "yokel-prod"
  description = "Name of the production cluster."
}

variable "region" {
  type        = string
  default     = ""
  description = "Cloud region (set when the provider is chosen at Phase 3)."
}
