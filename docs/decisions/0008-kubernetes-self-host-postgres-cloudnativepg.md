# 0008. Self-host Postgres on Kubernetes via CloudNativePG; K8s is the platform

- Status: Accepted
- Date: 2026-06-14
- Supersedes: the "No Kubernetes/Lambda" hosting stance and the "Render/Fly.io + managed Postgres"
  sketch in `docs/architecture/docketclock.md` (the architecture doc is generated from the foundry
  output and is left as-is; this ADR is the human override).

## Context

The architecture (`docs/architecture/docketclock.md`) deliberately chose a ruthless anti-ops MVP:
Postgres-as-everything (append-only observation log, outbox queue, FTS), hosted on a zero-ops PaaS
(Render/Fly) with **managed** Postgres, explicitly "No Kubernetes/Lambda." That stance assumed
Kubernetes is a net *cost* — true for a team that would have to learn it.

That assumption does not hold here. The operator is already fluent in Kubernetes, has the tooling on
the Mac Mini (`kubectl`, `helm`, `kind`, `k3d`, `colima`), and intends K8s to be the long-term
platform. For a K8s-fluent operator, self-hosting on K8s is *lower* friction than learning a managed
DB platform's quirks and lock-in — and it keeps the app tier and the database on one substrate.

The one project-specific constraint that any host must satisfy: the observation log is an
**append-only, DB-trigger-enforced, role-locked-down** trust primitive (legal defensibility). This
requires real Postgres with full role control — which self-hosting via an operator provides directly.

## Decision

- **Database:** self-host **Postgres 16** via the **CloudNativePG** operator (CNCF de-facto standard:
  declarative clusters, automated failover, PITR/backups to object storage, in-place minor upgrades,
  built-in connection pooling). Chosen over the Zalando and Crunchy (CPGO) operators for a greenfield
  start; revisit only on a concrete need.
- **App tier:** the Fastify API + the poller/outbox workers run **in-cluster** as well (decided
  together with the DB), so dev and prod share one substrate.
- **Dev environment:** **full in-cluster locally** — a throwaway **k3d** cluster on **colima** on the
  Mini (colima gives a headless, SSH-friendly container runtime; Docker Desktop's GUI daemon is
  avoided). The app and a CNPG-managed Postgres run in-cluster; the inner loop redeploys into it.
- **Production:** a **managed-control-plane** Kubernetes cluster in a cloud provider (the provider —
  GKE / EKS / DOKS / Civo / Hetzner-class — is chosen at the Phase 3 deploy, not now). We self-host
  Postgres-via-CNPG and our workloads on top; we do **not** run the control plane.
- **Portability:** manifests are **provider-agnostic** (Kustomize base + `local`/`cloud` overlays).
  The only environment-specific seams are isolated in overlays: **StorageClass** (`local-path` →
  cloud CSI), **ingress/LoadBalancer** (local Traefik/port-forward → cloud LB), and **CNPG backup
  object storage** (local MinIO/none → S3/GCS). The same base YAML runs on the Mini and in the cloud.

## Consequences

- **We own Postgres ops** — backups, PITR, failover, major-version upgrades, monitoring — instead of a
  vendor. CloudNativePG automates most of this declaratively, but the responsibility is ours; that is
  the accepted cost of this decision.
- This **front-loads infrastructure** (cluster, operator, manifests, secrets, ingress/TLS,
  image build + CI-to-cluster) ahead of product code, and slows the local inner loop vs. running the
  app on the host. Accepted in exchange for dev/prod parity and the operator's existing K8s leverage.
- **No application lock-in:** the app talks to Postgres by connection string only. If self-hosting
  ever stops paying off, migrating to a managed Postgres (Neon/Crunchy Bridge/RDS) is a connection-
  string change, and the cloud cluster choice stays open until deploy time.
- `docs/architecture/docketclock.md` now diverges from reality on hosting; this ADR is the source of
  truth for infra. The Postgres-as-everything data decisions (outbox queue, FTS, no
  OpenSearch/Temporal/BullMQ) are **unchanged** — only *where/how Postgres and the app run* changed.
- `SETUP.md` (Mini bootstrap) and `AGENTS.md` must point here so future agents target the cluster, not
  a bare local Postgres.
