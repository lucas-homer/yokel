# Cloud root module — STUB (Phase 3). Wires the cluster + backup-bucket modules into a production
# environment. No provider block yet — fill it (and credentials) when the provider is chosen.
# `terraform init && terraform validate` works offline today because no providers are required.

module "cluster" {
  source             = "../../modules/k8s-cluster"
  cluster_name       = var.cluster_name
  region             = var.region
  node_count         = 3
  kubernetes_version = "1.31"
}

module "backups" {
  source      = "../../modules/cnpg-backups"
  bucket_name = "${var.cluster_name}-cnpg-backups"
  region      = var.region
}

output "kubeconfig" {
  description = "Kubeconfig for the provisioned cluster (used to bootstrap Argo CD, then GitOps takes over)."
  value       = module.cluster.kubeconfig
  sensitive   = true
}
