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
argocd/apps/          # one Argo Application per component (CNPG, ESO, Vault, observability) + the app
argocd/manifests/     # raw manifests for git-sourced apps (e.g. the vault-backend ClusterSecretStore)
scripts/vault-seed.sh # seed dev Vault + wire ESO token auth (idempotent)
scripts/seed-docketclock-secrets.sh # patch individual docketclock-external keys (regs/gemini/…) + roll
scripts/seed-r2-secrets.sh # push terraform R2 outputs → Vault secret/backups/r2 (after terraform apply)
scripts/backup-vault-keys.sh # one-time age-encrypted Vault seal-chain export → R2 (identity OFF the Mini)
terraform/            # envs/backups: LIVE Cloudflare R2 (backups PR-3); envs/cloud: phase-3 stub
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
once the repo is pushed — that's the GitOps path. For active development the Tilt inner-loop
(`../Tiltfile`) is the day-to-day path: `tilt up` builds the image, deploys the chart with local
values, and live-updates the running container on source changes (Argo keeps managing the platform +
the committed app; Tilt overrides the app workload while it's running).

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

Logs + metrics stack (Slice A / PR-A2 for logs, Slice B / PR-B2 for metrics), platform Argo
Applications in the `observability` namespace, all pinned lean for the 12 GiB colima budget:

- **Loki** (`platform-loki.yaml`, chart `grafana/loki`) — SingleBinary mode, filesystem storage, 72h
  retention. The log store; reachable in-cluster at `http://loki.observability.svc.cluster.local:3100`.
  The chart's gateway / memcached caches / canary / self-monitoring / test pods are all disabled.
- **Alloy** (`platform-alloy.yaml`, chart `grafana/alloy`) — single-replica Deployment log shipper.
  Discovers pods via the Kubernetes API, relabels to `namespace` / `pod` / `container` / `app`, drops its
  own noise, and pushes to Loki. (Promtail is EOL; Alloy is the supported agent.) It's a Deployment, not
  a DaemonSet, because the API-based source reads cluster-wide — a DaemonSet would tail every pod once
  per node and duplicate every line.
- **Prometheus** (`platform-prometheus.yaml`, chart `prometheus-community/prometheus`) — the metrics
  store: server (5Gi PVC, 7d retention) + kube-state-metrics + node-exporter; alertmanager + pushgateway
  disabled (alerting is Grafana-managed). Scraping is **annotation-based** (no operator): the bundled
  `kubernetes-pods` job scrapes any pod with `prometheus.io/scrape: "true"` — the docketclock API (:8080)
  and poller (:9464) carry those. Reachable at `http://prometheus-server.observability.svc.cluster.local`.
- **Grafana** (`platform-grafana.yaml`, chart `grafana-community/grafana`) — Prometheus pre-provisioned as
  the **default** datasource (metrics), Loki alongside it (logs). Ephemeral (no PVC); ClusterIP service,
  reached via port-forward. (Uses the `grafana-community` chart — the old `grafana/grafana` chart is
  deprecated upstream.)

### Vault seed

Grafana's admin credentials come from Vault via ESO (never inline) — the `grafana-admin`
`ExternalSecret` ships inside `platform-grafana.yaml` and reads `secret/observability/grafana` through
the existing `vault-backend` ClusterSecretStore. **`task vault-seed` seeds this automatically** (defaults
`admin`/`admin`; override with `GRAFANA_ADMIN_USER` / `GRAFANA_ADMIN_PASSWORD` in your shell env before
running it). ESO then materializes the `grafana-admin` Secret (keys `admin_user` / `admin_password`).

To change the password later without a full reseed:

```bash
# VAULT_ADDR + VAULT_TOKEN are required inside the pod — Vault listens on http (not the CLI's https
# default) and the put needs the root token (stashed by vault-seed in the vault/vault-root-token Secret).
ROOT_TOKEN=$(kubectl -n vault get secret vault-root-token -o jsonpath='{.data.token}' | base64 -d)
kubectl -n vault exec -it vault-0 -- sh -c "
  export VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=$ROOT_TOKEN
  vault kv put secret/observability/grafana admin_user=admin admin_password='<choose-a-strong-password>'
"
```

If the path is missing entirely the Grafana sync stays unhealthy until it's seeded (ESO is
all-or-nothing, same as `secret/docketclock/external`).

### Use it

```bash
task grafana      # port-forward svc/grafana :80 → localhost:3000 (log in with the seeded admin creds)
task prometheus   # port-forward svc/prometheus-server :80 → localhost:9090 (raw Targets/Graph UI)
```

Grafana is the day-to-day view (**Explore → Prometheus** for metrics, **→ Loki** for logs); `task
prometheus` opens the raw store — its **/targets** page is the quickest way to confirm the docketclock
API/poller pods are `UP` and kube-state-metrics/node-exporter are scraping.

**Dashboards + alerts (Slice B / PR-B3)** are provisioned into Grafana from `platform-grafana.yaml`
(no manual import). Under **Dashboards** you'll find _DocketClock — App_ (poll/chain cycles, adjudicator
LLM latency/tokens/verdicts/cache-hit, HTTP p95/5xx, `db_up`) and _Cluster — Overview_ (node
CPU/mem/disk, plus pod restarts/memory by namespace). Under **Alerting → Alert rules**: _Poller stalled_
(heartbeat age > 3× interval), _LLM adjudicator error spike_, and _API readiness down_ (`db_up == 0`).
Each rule scopes by `app_kubernetes_io_component` so the cross-process gauge leaks (`db_up=0` on the
poller, `heartbeat=0` on the API) never false-fire.

**Alert delivery (Slice V / PR-V3)** — every rule (the three above + the `Backups` folder) routes to
the **ntfy** contact point: a hosted-push topic your phone subscribes to via the ntfy app, formatted by
ntfy's built-in `?template=grafana`. The topic URL is a _secret_ (whoever knows the topic can read and
spoof alerts): it lives at Vault `secret/observability/alerting`, flows ESO → the `grafana-alerting`
Secret → pod env (`envFromSecret`) → `${ALERTING_NTFY_URL}` interpolation in the provisioned contact
point — never git. Arm it with `scripts/seed-alerting-secrets.sh` (generates + prints a topic if you
don't pass `NTFY_TOPIC`; subscribe on the phone, then keep the topic somewhere safe). Until then the
Vault placeholder is the old `local-noop` URL, so delivery no-ops; `local-noop` also stays defined as
the one-line rollback (flip `policies.yaml`'s `receiver` back). Grafana reads env at pod start — the
seed script rolls the Deployment for you after a rotation.

**Dead-man's switch (`platform-deadman.yaml`)** — all of the above lives _inside_ the cluster; if
colima/k3d/the Mini dies outright, Grafana can't page anyone. The `deadman-ping` CronJob
(`observability` ns, hourly at :11) curls a [healthchecks.io](https://healthchecks.io) check that pages
on ping _absence_ (configure the check by hand: period 1h, grace 1h → a total outage pages within
~2h). The ping URL rides the same Vault path (`healthchecks_ping_url`, seeded via
`HEALTHCHECKS_PING_URL=... scripts/seed-alerting-secrets.sh`); while it's still the placeholder the
CronJob exits 0 without pinging, so nothing fails and nothing pages.

**Fire drill — `task alert-drill` (quarterly, ~90m).** An alert path is untested until it has paged
someone: the drill pauses docketclock's auto-sync (git pins the poller at `replicas: 1`; selfHeal would
revert the outage), scales the poller to 0, waits for _Poller stalled_ to fire **with its real
thresholds** (~55–60m), asks you to confirm the page reached your phone, restores, and confirms the
resolve notification too. It then prints the manual dead-man half (suspend the CronJob once, wait for
the absence page, restore). Drill log: <!-- add PASS dates here --> not yet run.

Then **Explore → Loki**. Start with a generic stream selector to confirm logs are flowing (works
before docketclock is even running) — the labels Alloy sets are `namespace` / `pod` / `container` / `app`:

```logql
{namespace="observability"}          # platform logs — Loki/Alloy/Grafana themselves
{namespace="docketclock"}            # the app, once it's deployed
```

A more specific query for the structured adjudicator cycle events:

```logql
{namespace="docketclock"} |= "chain adjudicate cycle"
```

### LLM observability (Langfuse)

Per-call traces of the chain-seam adjudicator's LLM calls — input/output, model, latency, tokens — and
the seed for an eval dataset (Slice C; `plans/observability-llm.md`). **Langfuse v2** (Postgres-only) runs
as a platform Argo app (`platform-langfuse.yaml`) in the `langfuse` namespace: a single
`langfuse/langfuse:2` container backed by a dedicated CloudNativePG `langfuse-db`. v2 is the deliberate
lean choice — v3 (ClickHouse/Redis/S3) would blow the colima budget; v2 is security-EOL upstream but this
is a local, non-internet-exposed dev tool. Secrets (server crypto + the pinned API keypair) come from
Vault via ESO; **`task vault-seed` seeds `secret/langfuse/config`** (dev defaults; override via `LANGFUSE_*`
env). DB migrations run on container startup, and `LANGFUSE_INIT_*` headlessly creates the org/project/
user — no manual UI bootstrap.

```bash
task langfuse   # port-forward svc/langfuse :3000 → localhost:3001 (login admin@docketclock.local)
```

The poller sends adjudicator traces (PR-C2): with `ADJUDICATOR=gemini`, a `GEMINI_API_KEY`, and the three
`LANGFUSE_*` vars set, each chain-adjudicate cycle opens a trace with a `generation` per real LLM call
(model, input/output, token usage, latency). `pnpm --filter @yokel/docketclock smoke:langfuse` lands one
trace on demand (synthetic ambiguous pair) to prove the wiring.

**Eval-dataset seed (PR-C3).** Seed a Langfuse dataset of representative adjudication inputs from the
`adjudications` cache, each historical verdict attached as a _provisional_ expected-output for human
labeling in Slice D:

```bash
# DATABASE_URL → the docketclock Postgres (port-forward svc/docketclock-pg-rw locally); LANGFUSE_* from .env
pnpm --filter @yokel/docketclock seed:langfuse-dataset --dry-run   # print the stratification plan
pnpm --filter @yokel/docketclock seed:langfuse-dataset            # upsert into "docketclock-adjudications"
```

Stratifies by `kind × classification`, caps `SEED_CAP` (default 25) per stratum, dedupes by `content_hash`
(= the item id, so re-runs upsert — no duplicates), and selects oldest-first so the seeded corpus is stable
and reproducible across cache growth. Read-only on Postgres; writes only to Langfuse.

## Backups

The in-cluster half of the backups + restore-drill phase (`plans/backups-restore-drill.md`; all six
PRs landed). **MinIO** (`platform-minio.yaml`, raw manifests in `argocd/manifests/minio/` — the
langfuse pattern) runs single-node in the `backups` namespace as the S3-compatible target that CNPG
barman PITR (PR-2), nightly `pg_dump`s + the Cloudflare R2 offsite mirror (PR-3), and Vault raft
snapshots (PR-4) land in. MinIO alone is NOT a backup — its 10Gi PVC lives on the same colima VM disk
as Postgres; R2 is the copy that survives the VM/Mini. A bucket-init sync-hook Job creates the four
fixed buckets: `cnpg-docketclock`, `cnpg-langfuse`, `pgdump`, `vault-snapshots`.

**Offsite (PR-3)** is **Cloudflare R2, Terraform-managed — no dashboard clickops**
(`terraform/envs/backups`: the bucket + a bucket-scoped API token whose S3 keypair is derived in
outputs; run `terraform apply` with a bootstrap `CLOUDFLARE_API_TOKEN` in env, then
`scripts/seed-r2-secrets.sh` pushes the outputs into Vault, stdin-only). An hourly `r2-mirror`
CronJob (`argocd/manifests/minio/`) rclone-syncs every MinIO bucket to R2 1:1 — retention decisions
happen ONLY in MinIO (barman `retentionPolicy` for the `cnpg-*` buckets, 14d ILM rules for
`pgdump`/`vault-snapshots`) and the mirror inherits them. Nightly `pg_dump -Fc` CronJobs (08:30/08:40
UTC, version-matched to the server image) drop restore-anywhere logical dumps into `pgdump` — the
"everything else failed" tier. One-time `scripts/backup-vault-keys.sh` streams the Vault seal-chain
Secrets age-ENCRYPTED to R2 (the age identity lives OFF the Mini — password manager or paper).

**PITR (PR-2)** runs through the **Barman Cloud Plugin** (`platform-barman-plugin.yaml`, a vendored
upstream release manifest in `argocd/manifests/barman-cloud-plugin/` — in-tree `barmanObjectStore` is
deprecated since CNPG 1.26), which requires **cert-manager** (`platform-cert-manager.yaml`, pinned
lean) for its TLS chain. Both CNPG Clusters archive WAL continuously (RPO ≤5 min) and take a nightly
base backup (08:00/08:10 UTC, `immediate: true` on first land) with a 14d recovery window enforced at
the source store: the docketclock chart templates an `ObjectStore` + `ScheduledBackup` from
`postgres.backup.*` values (local → MinIO, cloud → the R2 seam), and the langfuse app inlines the same
shapes (`langfuse/backup.yaml`). Enabling/disabling the plugin stanza rolls a Cluster ONCE (sidecar
injection). Check `kubectl get backup -A` and each Cluster's `firstRecoverabilityPoint` for state.

**Vault raft snapshots (PR-4)** (`platform-vault-snapshot.yaml`, raw manifests in
`argocd/manifests/vault-snapshot/`): a daily CronJob (08:20 UTC, staggered inside the nightly
window) saves a raft snapshot from the leader (`vault-active`) and uploads it to the
`vault-snapshots` bucket — 14d ILM retention, mirrored to R2 hourly like everything else. It
authenticates with the root token for now; the k8s-auth + snapshot-policy hardening is issue #75
(hard requirement at cloud cutover). A snapshot restore needs the seal chain from
`backup-vault-keys.sh` — re-seeding (`vault-seed.sh`) stays the primary local Vault DR path.

**Observability (PR-5)**: `task backup-status` prints a one-shot freshness report (PITR windows,
newest WAL, dump/snapshot/mirror CronJobs). Grafana alerts (folder `Backups`, delivered via the
ntfy contact point since Slice V's PR-V3): base-backup age >26h, WAL archiving
failing, nightly CronJobs stale >26h, r2-mirror stale >3h. Metric plumbing lives in
`platform-prometheus.yaml`: a `cnpg-pods` scrape job (the DB pods' :9187 exporters carry no
`prometheus.io` annotations) and kube-state-metrics `customResourceState` over the barman
**ObjectStore CR** — with plugin backups the Cluster-status backup fields stay empty, so
recoverability truth is `.status.serverRecoveryWindow` (exported as `cnpg_objectstore_*`).

**Drills (PR-6)** — backups you haven't restored are a hypothesis, not a capability. `task
drill-pitr` (Drill A, **monthly**) spins a scratch `docketclock-pg-drill` Cluster in namespace `dr`
recovering from the live store at `now-5m`, asserts row-count tolerance / the append-only trigger /
the PITR target, and tears itself down — non-destructive by construction (the drill Cluster never
archives). Drill B (**semi-annually + before cloud cutover**) is the full "Mini died" cold restore
from R2: `docs/runbooks/restore-from-offsite.md`, using the chart's `postgres.recovery.*` seam —
read its step-2 warning about suspending `r2-mirror` before touching an empty MinIO.

Root creds come from Vault via ESO (`secret/backups/minio`); **`task vault-seed` seeds them** —
GENERATED on first seed and never rotated by a re-run (every backup producer reads them; see the
comments in `vault-seed.sh`). The seed also stubs `secret/backups/r2` with placeholders; the real
bucket-scoped R2 token is patched in at PR-3 (create the bucket + token in the Cloudflare dashboard
first — the one manual step of the phase).

```bash
task minio   # port-forward the MinIO console :9001 → localhost:9001 (creds from the minio-root Secret)
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
- **Langfuse login redirects fail / "callback" auth errors.** Langfuse's `NEXTAUTH_URL` is pinned to
  `http://localhost:3001` to match the `task langfuse` port-forward. Reaching the UI any other way (a LAN
  IP, or an ingress host you added without updating the env) breaks the OAuth callback. Access it via the
  port-forward, or update `NEXTAUTH_URL` in `infra/argocd/manifests/langfuse/deployment.yaml` to the real
  URL.

## Surviving a reboot (auto-recovery)

The Mini reboots occasionally (power blips, or macOS updates if you leave auto-install on). A reboot stops
colima and leaves the cluster broken: k3d nodes down, stale kubelet certs, sealed transit Vault. Two pieces
make a reboot self-heal unattended:

1. **colima auto-starts** — `brew services start colima` registers it as a launchd agent (one-time).
   Combined with the Mini's auto-login, colima comes back on every boot.
2. **`task install-boot-recovery`** — installs the `cc.rostr.yokel.boot-recovery` LaunchAgent, which on
   each login waits for colima/docker to be ready and then runs `task cluster-restart`
   (`infra/scripts/boot-cluster-restart.sh`). Output → `~/Library/Logs/yokel-boot-recovery.log`. Remove with
   `task uninstall-boot-recovery`. Note: installing it runs `cluster-restart` once immediately (RunAtLoad).

tmux sessions do **not** survive a reboot (they're in RAM) — so the real win is not rebooting unnecessarily:
keep macOS auto-install off and update on your own schedule. Between reboots, tmux survives SSH disconnects
fine — close the laptop, reopen, `ssh mini`, `tmux attach`, and the cluster is still running.
