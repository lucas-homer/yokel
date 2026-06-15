# STUB (Phase 3) — provider-agnostic interface for the managed-control-plane Kubernetes cluster.
# At deploy time, swap in a provider implementation (GKE / EKS / DOKS / Civo) that satisfies the same
# variables + outputs, so callers (envs/cloud) don't change. No resources yet, so this validates
# offline (no provider download on `terraform init`). See ADR 0008.
