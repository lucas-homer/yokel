# Terraform — cloud provisioning (Phase 3 stub)

Provisions the **production** Kubernetes cluster + the object storage for CloudNativePG PITR backups,
then bootstraps Argo CD (after which GitOps reconciles everything from git). See ADR 0008 / 0009.

**Status: structure only.** The modules are provider-agnostic interfaces with no resources yet, so the
cloud provider stays deferred. `terraform init && terraform validate` works offline today.

```
modules/
  k8s-cluster/    # interface for the managed-control-plane cluster (vars in, kubeconfig/endpoint out)
  cnpg-backups/   # interface for the PITR backup bucket
envs/
  cloud/          # root module wiring the two; provider block intentionally unfilled
```

## At Phase 3 (choosing the provider)

1. Pick the provider (GKE / EKS / DOKS / Civo / Hetzner-class).
2. Add `required_providers` + a `provider` block in `envs/cloud/versions.tf`.
3. Implement `modules/k8s-cluster` and `modules/cnpg-backups` with that provider's resources, keeping
   the existing variables + outputs (so `envs/cloud` is unchanged).
4. `terraform apply`, then use the `kubeconfig` output to install Argo CD and apply
   `infra/bootstrap/root-app-cloud.yaml`. GitOps takes over from there.
