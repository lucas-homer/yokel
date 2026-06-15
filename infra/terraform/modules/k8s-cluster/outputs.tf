output "kubeconfig" {
  description = "Raw kubeconfig for the provisioned cluster (filled by the provider implementation)."
  value       = null
}

output "cluster_endpoint" {
  description = "Kubernetes API endpoint (filled by the provider implementation)."
  value       = null
}
