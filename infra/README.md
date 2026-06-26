# infra — DocketClock platform (IaC + GitOps)

Kubernetes is the platform (ADR 0008). This dir defines it as code: a local **k3d** dev cluster that
closely matches a future cloud cluster, reconciled by **Argo CD** (GitOps), with **CloudNativePG**
(Postgres), **External Secrets Operator + self-hosted Vault** (secrets), and our **Helm** app chart.
Toolchain rationale: ADR 0009.

## Layout

```
Taskfile.yml          # the runbook — `task dev-up`, `task dev-down`, `task status`, …
k3d/yokel.yaml        # local cluster definition (codifies what was once `k3d cluster create …`)
bootstrap/            # Argo CD Helm values + the app-of-apps root Applications (local + cloud stub)
argocd/apps/          # one Argo Application per component (CNPG, ESO, Vault) + the app (from git)
scripts/vault-seed.sh # seed dev Vault + wire ESO token auth (idempotent)
terraform/            # cloud provisioning — structure only, provider deferred (see its README)
../charts/docketclock # our first-party Helm chart (CNPG Cluster, ESO wiring, app)
```

## Local bring-up (on the Mini)

```bash
cd infra
task dev-up        # colima → k3d → Argo CD → platform (CNPG/ESO/Vault) → vault-seed → app
task status        # Argo Applications + key pods
task argocd-ui     # Argo dashboard at https://localhost:8081 (user: admin; pw: `task argocd-password`)
task dev-down      # delete the cluster (colima keeps running)
```

The only imperative step is installing Argo CD; Argo reconciles the rest. The platform Applications
source straight from upstream Helm repos, so they sync without pushing this repo. Our app chart is
`helm`-installed locally by `task app-local` and is managed by Argo from git (`app-docketclock.yaml`)
once the repo is pushed — that's the GitOps path. The Tilt inner-loop (`../Tiltfile`) lands in Phase 1.

## Secrets

Vault runs **HA-raft (1 replica, persistent) and auto-unseals via a Transit seal** — the same shape as
prod, which auto-unseals via cloud KMS. Two Vaults locally:

- `vault-transit` — a tiny **persistent** (standalone + PVC) Vault whose only job is to hold the
  `autounseal` transit key. It is the **local stand-in for cloud KMS**. `vault-transit-init` inits it
  once (stashing the unseal key + root token in the `vault-transit-keys` Secret) and enables its transit
  engine + key; because it persists, the key **survives pod restarts** (the old dev-mode Vault lost it in
  memory on every restart, which bricked the main Vault). It starts sealed, so `task cluster-restart`
  re-unseals it (via `vault-transit-unseal`) after a colima/Docker restart. The main Vault's seal reads
  that root token from `VAULT_TOKEN`, injected from the `vault-transit-keys` Secret.
- `vault` (main) — raft storage, `seal "transit"` pointing at `vault-transit`. `vault-seed` runs
  `operator init` once (recovery keys — there are no Shamir unseal keys under auto-unseal), stashes the
  root token + recovery keys in the `vault/vault-root-token` Secret (dev convenience), then writes the
  placeholder external secrets (Regs.gov / Anthropic keys, webhook HMAC) to `secret/docketclock/external`.

ESO syncs those into the `docketclock-external` K8s Secret. Postgres credentials are **not** here —
CloudNativePG generates and rotates those itself. Prod differs only by overlay: the `seal "transit"`
stanza becomes `seal "gcpckms"`/`"awskms"` (no static token — workload identity), replicas → 3, and ESO
auth switches from the dev root token to the kubernetes auth method (see `platform-vault.yaml` comments
and `charts/docketclock/values-cloud.yaml`). There is **no** `vault-transit` in cloud.

## Observability

Logs-first stack (Slice A / PR-A2), three platform Argo Applications in the `observability`
namespace, all pinned lean for the 12 GiB colima budget:

- **Loki** (`platform-loki.yaml`, chart `grafana/loki`) — SingleBinary mode, filesystem storage, 72h
  retention. The store; reachable in-cluster at `http://loki.observability.svc.cluster.local:3100`.
  The chart's gateway / memcached caches / canary / self-monitoring / test pods are all disabled.
- **Alloy** (`platform-alloy.yaml`, chart `grafana/alloy`) — single-replica Deployment log shipper.
  Discovers pods via the Kubernetes API, relabels to `namespace` / `pod` / `container` / `app`, drops its
  own noise, and pushes to Loki. (Promtail is EOL; Alloy is the supported agent.) It's a Deployment, not
  a DaemonSet, because the API-based source reads cluster-wide — a DaemonSet would tail every pod once
  per node and duplicate every line.
- **Grafana** (`platform-grafana.yaml`, chart `grafana-community/grafana`) — Loki pre-provisioned as the
  default datasource. Ephemeral (no PVC); ClusterIP service, reached via port-forward. (Uses the
  `grafana-community` chart — the old `grafana/grafana` chart is deprecated upstream.)

### Vault seed

Grafana's admin credentials come from Vault via ESO (never inline) — the `grafana-admin`
`ExternalSecret` ships inside `platform-grafana.yaml` and reads `secret/observability/grafana` through
the existing `vault-backend` ClusterSecretStore. **`task vault-seed` seeds this automatically** (defaults
`admin`/`admin`; override with `GRAFANA_ADMIN_USER` / `GRAFANA_ADMIN_PASSWORD` in your shell env before
running it). ESO then materializes the `grafana-admin` Secret (keys `admin_user` / `admin_password`).

To change the password later without a full reseed:

```bash
kubectl -n vault exec -it vault-0 -- vault kv put secret/observability/grafana \
  admin_user=admin admin_password='<choose-a-strong-password>'
```

If the path is missing entirely the Grafana sync stays unhealthy until it's seeded (ESO is
all-or-nothing, same as `secret/docketclock/external`).

### Use it

```bash
task grafana   # port-forward svc/grafana :80 → localhost:3000 (log in with the seeded admin creds)
```

Then **Explore → Loki**. Example query for the structured adjudicator cycle events:

```logql
{namespace="docketclock"} |= "chain adjudicate cycle"
```

## Troubleshooting

- **Image pulls fail inside k3d nodes (`EAI_AGAIN` / `lookup registry-1.docker.io: Try again`).** On a
  Tailscale host the lima DNS forwarder (`192.168.5.2`) is unreliable. Fix: restart colima with public
  DNS — `colima restart --dns 1.1.1.1 --dns 8.8.8.8` — then `task dev-down && task dev-up`. (Baked into
  `task cluster-up` for fresh starts.)
- **Main Vault stuck sealed / `vault` Application never goes Healthy.** The transit seal: the
  `vault-transit` pod restarted and is sealed (it persists its key but starts sealed), so the main Vault
  can't reach `transit/encrypt/autounseal` (`404 route entry not found`) and crashloops. In-place fix:
  `task vault-transit-unseal` then `kubectl -n vault delete pod vault-0` (both are folded into
  `task cluster-restart`). No re-bootstrap needed — the key persists on the transit PVC. (Only a _lost_
  transit PVC, or the legacy dev-mode Vault, makes the main Vault's raft data unrecoverable.)
- **`vault-transit` Application stuck `OutOfSync`/Degraded after upgrading to the persistent transit Vault.**
  Switching `vault-transit` from dev-mode to standalone adds a `volumeClaimTemplate` — an immutable
  StatefulSet field — so Argo can't sync it over the old dev-mode StatefulSet. ONE-TIME fix (dev-mode held
  no data worth keeping): `kubectl -n vault delete statefulset vault-transit --cascade=orphan`, then let
  Argo recreate it (or `task vault-transit-init`). A clean `task dev-up` on a fresh cluster doesn't hit this.
- **`wait-platform` hangs.** Argo syncs asynchronously; check `task status` and the Argo UI
  (`task argocd-ui`). A platform Application stuck `OutOfSync` usually means a pinned chart version or
  values key drifted — see `infra/argocd/apps/`.
