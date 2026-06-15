# 0009. GitOps + IaC toolchain: Argo CD, Helm, External Secrets + Vault, Terraform/k3d

- Status: Accepted
- Date: 2026-06-14
- Builds on: ADR 0008 (Kubernetes is the platform; self-hosted Postgres via CloudNativePG).

## Context

ADR 0008 made Kubernetes the platform but didn't specify _how_ it is provisioned and operated. The
requirement: the dev environment closely matches production, everything is defined as code, and changes
are applied via GitOps (declarative, git-as-source-of-truth) rather than imperative commands.

## Decision

- **GitOps engine: Argo CD** (app-of-apps). Argo reconciles desired state from git; its UI gives a
  solo operator visibility into sync/health/drift.
- **Packaging: Helm everywhere.** Vendored components (CloudNativePG, ESO, Vault) are Argo Applications
  sourced from upstream Helm repos; our app is a first-party chart `charts/docketclock` with
  `values-local.yaml` / `values-cloud.yaml` overlays.
- **Secrets: External Secrets Operator backed by self-hosted HashiCorp Vault.** Vault runs HA-raft and
  **auto-unseals in every environment** — locally via a Transit seal from a tiny in-cluster `vault-transit`
  (the local stand-in for cloud KMS), in prod via cloud KMS (`gcpckms`/`awskms`). Same shape; only the
  seal backend + replica count differ by overlay. CloudNativePG manages Postgres creds itself — ESO only
  handles external-origin secrets (Regs.gov key, Anthropic key, webhook HMAC).
- **Provisioning: Terraform for cloud (structure now, provider deferred); a k3d config for local.**
  `infra/terraform` holds provider-agnostic module interfaces (no resources yet) so the cloud provider
  stays deferred to Phase 3. Local is a committed `k3d` config.
- **Runner: go-task.** `cd infra && task dev-up` is the one codified entrypoint (colima → k3d → Argo CD
  → platform → app). The only imperative seam is installing Argo CD; Argo does the rest.
- **Dev environment: full in-cluster** on k3d/colima on the Mini. Tilt is the app inner-loop (Phase 1).
- **Parity principle:** identical across envs = API objects, chart versions, app image, reconciliation
  mechanism, **and Vault's shape (HA-raft + auto-unseal + recovery-key init)**. Differ via overlays only
  = replica/HA topology, StorageClass, ingress/LB, TLS issuer, CNPG backup target, **Vault seal backend
  (transit ↔ KMS)**. "Same shapes, different scale and seams."

## Consequences

- A clean `task dev-up` reproducibly brings up the whole stack; verified end-to-end with a placeholder
  app (Argo Synced/Healthy, Vault→ESO secret flow, CNPG Postgres healthy, app reachable via ingress).
- The platform Applications source from upstream Helm repos, so they sync without pushing this repo;
  our app chart is Argo-managed from git once pushed (offline local uses `task app-local`).
- Vendored-chart **versions are pinned** in `infra/argocd/apps/*` (argo-cd 9.5.21, cloudnative-pg
  0.28.3, external-secrets 2.6.0, vault 0.33.0); bump deliberately.
- On a Tailscale host, colima must start with explicit public DNS (`--dns 1.1.1.1 --dns 8.8.8.8`) or
  the lima forwarder breaks image pulls inside the k3d nodes — baked into `task cluster-up`.
- Cloud specifics (provider, backups object storage, ingress/TLS, the Vault **KMS seal** + replica
  bump + Kubernetes auth method) remain deferred to Phase 3; only the Terraform _structure_ exists now.
- Local trade-off: `vault-transit` runs dev-mode (in-memory), so if **that** pod restarts the autounseal
  key is lost and the main Vault can't unseal — recover with `task dev-down && task dev-up`. Accepted for
  a solo dev box; prod has no such edge (KMS is a managed, always-available service).
