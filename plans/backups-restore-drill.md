# Backups + Restore Drill — CNPG PITR, offsite copy, Vault snapshots, drills

> Status: **Ready to build** — decisions locked, awaiting go on PR-1.
> Target: local k3d (colima 12 GiB, ~5–6 GiB safe headroom — every component pinned lean).
> Why now: the append-only observation log is the irreplaceable asset (current state is re-pollable;
> the historical observation chains + adjudication history are not), and today there are **zero
> backups** — every PVC lives on the colima VM disk. This phase also folds into verification:
> a restore drill that has never run is not a backup system.

## Decisions locked

- **Backup target: in-cluster MinIO** (single-node, small PVC) as the S3-compatible barman target.
  Prod-parity shape: cloud cutover later swaps endpoint + credentials in `values-cloud.yaml` /
  the `cnpg-backups` Terraform module — same shapes, different seams.
- **Offsite replica: Cloudflare R2**, mirrored by an in-cluster rclone CronJob (MinIO → R2).
  MinIO alone is NOT a backup — its PVC sits on the same VM disk as Postgres. R2 survives the
  VM, the cluster, and the Mini itself; zero egress fees; free tier covers our ~GiB scale; and it
  is a live candidate for the production PITR bucket at cloud cutover (the Terraform stub already
  speaks S3-compatible barman-cloud).
- **Engine: Barman Cloud Plugin (CNPG-I)** — in-tree `barmanObjectStore` is deprecated since CNPG
  1.26 and we run operator ~1.27 (chart 0.28.3); the Terraform stub already names the plugin.
  Fallback if the plugin misbehaves on k3d: in-tree stanza (still functional), noted in PR-2.
- **Volume snapshots rejected**: k3d's local-path provisioner has no CSI snapshot support.
- **Scope: BOTH CNPG clusters** — `docketclock-pg` (chart) and the Langfuse Postgres (manifests;
  traces + eval datasets are re-derivable only partially). Deliberately NOT backed up: Loki (72h
  retention, ephemeral by design), Prometheus (7d, same), Grafana (fully provisioned from git),
  all k8s state (GitOps recreates it from `main`).
- **Vault is tier-2**: contents are re-seedable (`vault-seed.sh` + `seed-docketclock-secrets.sh`
  from upstream key sources), so Vault DR = cheap raft-snapshot insurance, not a hard dependency.
  BUT a raft snapshot is useless without the seal chain, so the `vault-root-token` +
  `vault-transit-keys` Secrets get a one-time **age-encrypted** export to R2 (key stored off-machine).
- **Belt-and-suspenders logical dumps**: nightly `pg_dump -Fc` alongside physical PITR. At ~1 GiB
  it costs nothing and restores anywhere (a laptop Postgres, no CNPG needed) — the "everything
  else failed" tier.
- **Offsite encryption**: R2's default server-side encryption at rest is the accepted baseline for
  the DB backups/WAL/dumps. docketclock's content is public-source regulatory data (FR/regs.gov
  observations + adjudications derived from them — no PII, no customer data); Langfuse traces
  (prompts/LLM output) are a step more sensitive but derive from the same public pipeline. Revisit
  (barman-cloud client-side encryption, or age on the dumps) the moment tenant or customer data
  enters either DB. The Vault seal-chain export (above) is the exception — always age-encrypted.
- **Retention**: 14 days of base backups + WAL (barman `retentionPolicy`), 14 nightly dumps,
  14 daily Vault snapshots. R2 mirrors MinIO 1:1 via `rclone sync` (retention enforced once, at
  the source). RPO targets: ≤5 min local (continuous WAL), ≤1 h offsite (hourly sync). RTO
  targets: ≤30 min scratch PITR, ≤half a day cold rebuild from R2.
- **Drills are in-phase acceptance criteria**, not a follow-up: the phase is DONE when both
  drills below have passed at least once and the runbook exists.

## PR-1 — MinIO platform app + secret seams

Raw manifests in `infra/argocd/manifests/minio/` (the Langfuse pattern — no heavyweight
operator/chart), one `platform-minio.yaml` Application, platform sync-wave.

1. Single-node MinIO: StatefulSet (or Deployment + PVC), 10Gi, ~256Mi memory limit, namespace
   `backups`. Root creds from Vault via ESO (`secret/backups/minio`).
2. Bucket-init Job (`mc mb --ignore-existing`): `cnpg-docketclock`, `cnpg-langfuse`, `pgdump`,
   `vault-snapshots`.
3. `vault-seed.sh`: seed `secret/backups/minio` (generated creds) + `secret/backups/r2`
   (placeholders — real values patched later like the docketclock keys).
4. Taskfile: `task minio` port-forward for the console; README Observability-style section.
5. **Verify:** app `Synced/Healthy`; `mc ls` shows the four buckets; `kubectl top nodes` headroom.

## PR-2 — CNPG WAL archiving + scheduled backups (both clusters)

1. Deploy the Barman Cloud Plugin (own platform Argo app, `cnpg-system`). Confirm operator/plugin
   version compatibility here; if flaky on k3d, fall back to the in-tree `barmanObjectStore`
   stanza and record the swap as a TODO tied to the operator upgrade.
2. docketclock chart: `postgres.backup.*` values (enabled, endpoint, bucket, retention `14d`,
   schedule) templating an `ObjectStore` CR + nightly `ScheduledBackup` (~08:00 UTC) + the plugin
   stanza on the Cluster. `values-local.yaml` points at MinIO; `values-cloud.yaml` gets the
   real-bucket TODO filled with the R2/endpoint seam.
3. Same additions to the Langfuse Postgres manifests.
4. Heads-up: enabling the plugin rolls the single-instance clusters once (brief DB downtime; the
   poller's next cycle + API restarts absorb it — do it off-peak, note in the PR).
5. **Verify:** `kubectl get backup` shows `completed`; WAL objects accumulating in MinIO; Cluster
   status reports a `firstRecoverabilityPoint`; no deprecation warnings in operator logs.

## PR-3 — Offsite mirror to R2 + logical dumps

1. Create the R2 bucket (`yokel-backups`) + a bucket-scoped API token in the Cloudflare dashboard
   (documented step; Terraform can absorb it in Phase 3). Patch real creds into Vault
   (`secret/backups/r2`) via the seed-secrets pattern.
2. rclone CronJob (namespace `backups`, hourly): `rclone sync` each MinIO bucket → R2 prefix.
   One-way, source-wins — retention decisions happen in MinIO only.
3. Nightly `pg_dump -Fc` CronJob for both databases → `pgdump` bucket (URI from the CNPG app
   Secrets), pruned to 14.
4. One-time `scripts/backup-vault-keys.sh`: age-encrypt `vault-root-token` +
   `vault-transit-keys` Secret manifests → R2. The age identity lives OFF the Mini (password
   manager / printed) — documented in the runbook.
5. **Verify:** objects visible in R2; `rclone check` clean; a dump ACTUALLY restores into a
   scratch local Postgres at least once this phase (a full `pg_restore`, not just `--list` — the
   TOC listing won't catch a corrupt dump body; `--list` stays as the cheap repeatable check).

## PR-4 — Vault raft snapshots

1. Daily CronJob in `vault`: `vault operator raft snapshot save` against `vault-0` authenticated
   with the `vault-root-token` Secret (dev-acceptable; the prod path is k8s-auth + a snapshot
   policy — tracked as issue #75 so it survives this phase being marked done), upload to MinIO
   `vault-snapshots`, keep 14. Mirrored to R2 by PR-3's sync.
2. **Verify:** snapshot object lands; size sane; job green two consecutive days.

## PR-5 — Backup observability

1. Grafana alert rules (provisioned like the existing set, same contact-point caveat — routes to
   `local-noop` until a real receiver lands, which stays a separate task): last base backup
   age > 26 h per cluster (CNPG collector metrics), WAL archiving failing (last-failed newer than
   last-archived), and CronJob staleness for rclone/pg_dump/vault-snapshot via kube-state-metrics
   `kube_cronjob_status_last_successful_time`.
2. `task backup-status`: one-shot report — newest base backup per cluster, newest WAL, newest
   dump, newest Vault snapshot, newest R2 sync time.
3. `validate-argocd-apps.py` keeps passing (extend if the new rules trip its consistency checks).
4. **Verify:** pause a ScheduledBackup (or lower a threshold) → alert goes Pending/Firing in
   Grafana; restore → resolves.

## PR-6 — Restore drills (runbooks + automation) — the acceptance gate

1. **Drill A, scratch PITR (automated, repeatable, non-destructive)** — `task drill-pitr`:
   spins a `docketclock-pg-drill` Cluster (namespace `dr`, 256Mi) bootstrapping `recovery` from
   the ObjectStore at `targetTime = now - 5m`, then a verify script asserts: row counts for
   `observations` / `participation_windows` / adjudications within tolerance of live, the
   append-only trigger still rejects an UPDATE, `max(observed_at)` consistent with the target
   time. Tears itself down. Checks colima headroom before starting.
2. **Drill B, cold restore from R2 (the "Mini died" scenario)** — runbook
   `docs/runbooks/restore-from-offsite.md`: fresh cluster (scratch k3d name, e.g. `yokel-dr` —
   never the live one) → restore MinIO from R2 (reverse rclone) → Vault re-seed (or raft-snapshot
   restore path) → CNPG `recovery` bootstrap as the main cluster → app up → poller sanity: the
   restored `poll_cursor` means differential polling resumes where it left off, and the 6 h cursor
   overlap + payload-hash idempotent ingest absorb the gap without duplicate observations.
   Executed once for real in this phase; it doubles as the cloud-cutover rehearsal later.
3. **Drill C (stretch)** — restore a Vault raft snapshot into a scratch Vault; skippable since
   re-seeding is the primary Vault DR path.
4. Cadence, documented in the runbook: Drill A monthly (it's one task invocation), Drill B
   semi-annually and before cloud cutover.
5. **Verify / phase exit:** Drill A green from a clean run; Drill B executed once end-to-end with
   timings recorded in the runbook; `task backup-status` clean; alerts proven in PR-5.

## Out of scope

- Real alert delivery (Slack/email contact point + external dead-man's-switch heartbeat) — its own
  small task, prerequisite for trusting any of PR-5 unattended.
- Terraform-managed R2 (folds into the Phase 3 `cnpg-backups` module, which now has a concrete
  provider candidate).
- Long-term Loki/Prometheus retention; Langfuse object exports.

## Rollback

- PR-1/PR-4: delete the Argo app / CronJob — nothing else references them.
- PR-2: set `backup.enabled=false` → ObjectStore/ScheduledBackup prune; the Cluster keeps running
  (one more rolling restart to drop the plugin stanza). Existing backup objects stay in MinIO.
- PR-3: delete the CronJobs; R2 bucket retains the last mirror (harmless, cheap).
- PR-5/PR-6: provisioned rules and task targets revert with the merge; drills leave no state
  (scratch namespaces/clusters are torn down).
