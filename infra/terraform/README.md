# Terraform — cloud provisioning

Two environments with very different maturity:

- **`envs/backups` — LIVE (backups PR-3).** The Cloudflare R2 offsite-mirror bucket + a
  bucket-scoped API token, IaC-not-clickops. Operator loop is documented in its `main.tf` header:
  `terraform apply` with a bootstrap `CLOUDFLARE_API_TOKEN` in env, then
  `../../scripts/seed-r2-secrets.sh` feeds the outputs into Vault. State is local + gitignored and
  contains the derived S3 secret — treat the state file like a credential.
- **`envs/cloud` — Phase 3 stub.** The **production** Kubernetes cluster + PITR object storage,
  then Argo CD bootstrap (after which GitOps reconciles everything from git). See ADR 0008 / 0009.
  The modules are provider-agnostic interfaces with no resources yet; `terraform init && terraform
validate` works offline today. Note the `r2-offsite` module doubles as the concrete candidate for
  the `cnpg-backups` interface (R2 already speaks the S3-compatible barman seam).

```
modules/
  k8s-cluster/    # interface for the managed-control-plane cluster (vars in, kubeconfig/endpoint out)
  cnpg-backups/   # interface for the PITR backup bucket (stub)
  r2-offsite/     # IMPLEMENTED: Cloudflare R2 bucket + scoped token (backups PR-3)
envs/
  cloud/          # phase-3 root module; provider block intentionally unfilled
  backups/        # LIVE root module for the R2 offsite target (cloudflare provider)
```

## At Phase 3 (choosing the provider)

1. Pick the provider (GKE / EKS / DOKS / Civo / Hetzner-class).
2. Add `required_providers` + a `provider` block in `envs/cloud/versions.tf`.
3. Implement `modules/k8s-cluster` and `modules/cnpg-backups` with that provider's resources, keeping
   the existing variables + outputs (so `envs/cloud` is unchanged).
4. `terraform apply`, then use the `kubeconfig` output to install Argo CD and apply
   `infra/bootstrap/root-app-cloud.yaml`. GitOps takes over from there.
