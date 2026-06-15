variable "cluster_name" {
  type        = string
  description = "Name of the managed Kubernetes cluster."
}

variable "region" {
  type        = string
  description = "Cloud region for the cluster."
}

variable "node_count" {
  type        = number
  default     = 3
  description = "Worker node count."
}

variable "kubernetes_version" {
  type        = string
  default     = "1.31"
  description = "Kubernetes control-plane version."
}
