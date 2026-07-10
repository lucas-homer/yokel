# Runbook: cold restore from offsite (R2) — "the Mini died"

**Scenario**: the Mac Mini (or its colima VM / disk) is gone. Everything in-cluster is lost —
Postgres, MinIO, Vault, the k3d cluster itself. What survives: this git repo (GitHub), the
Cloudflare R2 bucket `yokel-backups` (hourly mirror of every MinIO backup bucket), and the
out-of-band credentials listed below.

This is **Drill B** of the backups phase (`plans/backups-restore-drill.md`, PR-6). It is executed
for real once in this phase, and it doubles as the cloud-cutover rehearsal: the recovery seam it
exercises (`postgres.recovery.*` chart values) is the same one a MinIO→R2 provider swap uses.

**Cadence** (phase decision): **Drill A monthly** (`task drill-pitr` — automated scratch PITR,
~10 minutes, non-destructive), **Drill B semi-annually and before cloud cutover** (this runbook,
~half a day, needs operator judgment at several steps). Drill C (Vault raft-snapshot restore into a
scratch Vault) is a stretch goal — re-seeding is the primary Vault DR path and is what this runbook
uses.

## What you must have OFF the Mini (check these NOW, not during the incident)

| Item                                                                                                      | Where it lives                                | Used for                                                                      |
| --------------------------------------------------------------------------------------------------------- | --------------------------------------------- | ----------------------------------------------------------------------------- |
| Git repo                                                                                                  | GitHub (`lucas-homer/yokel`)                  | everything                                                                    |
| Cloudflare account id + a bootstrap API token (or the ability to mint one: dash login)                    | password manager                              | recreating the R2 credential via Terraform                                    |
| age IDENTITY (secret key) for the seal-chain backups                                                      | password manager / paper — **never** the Mini | only needed for the raft-snapshot path (Drill C); re-seed path doesn't use it |
| App secrets seed material (LLM API keys etc. consumed by `vault-seed.sh` / `seed-docketclock-secrets.sh`) | password manager                              | re-seeding Vault                                                              |

> **Terraform state is on the dead Mini** (`infra/terraform/envs/backups`, local + gitignored — a
> deliberate PR-3 decision). The R2 _bucket_ outlives the state. Recovery: fresh checkout,
> `terraform import` the bucket, `apply` mints a NEW scoped token:
>
> ```sh
> export CLOUDFLARE_API_TOKEN=<bootstrap token>
> cd infra/terraform/envs/backups
> terraform init
> terraform import module.r2_offsite.cloudflare_r2_bucket.offsite '<account_id>/yokel-backups'
> terraform apply   # recreates the account token; outputs = fresh S3 keypair
> ```

## Step 0 — decide where the replacement cluster runs

- **Same Mini, disk survived**: `colima start` + `task cluster-restart` may be all you need — that
  is the boot-recovery path (#54), not this runbook. Use this runbook when the k3d volumes are gone.
- **Same Mini, fresh VM**: the 12 GiB budget only fits ONE cluster. If any old cluster half-exists:
  `k3d cluster delete yokel` first.
- **New hardware**: follow `SETUP.md` prerequisites (colima, k3d, kubectl, task, helm), then
  continue here.

Name the replacement cluster `yokel-dr` while drilling (never touch a live `yokel`); at a real
incident on fresh hardware you may name it `yokel` directly.

## Step 1 — cluster + platform bring-up (the normal bootstrap, minus the app)

All commands in this runbook run from the **repo root** (`task` invocations use `-d infra`).

```sh
k3d cluster create yokel-dr --k3s-arg "--disable=traefik@server:0"   # match k3d-default.yaml sizing
task -d infra argocd     # install Argo CD
task -d infra platform   # apply all platform-*.yaml Applications
bash infra/scripts/vault-transit-init.sh
task -d infra vault-seed # re-seed Vault: NEW random MinIO root creds, app secrets from your vault
```

Wait for the platform tier: `kubectl get applications -n argocd` — everything Synced/Healthy except
the CNPG clusters' backups (empty MinIO) and langfuse (restored below). `vault-seed` regenerating
MinIO root creds is fine — the fresh MinIO initializes with them; R2 does not care who reads it.

## Step 2 — ⚠️ SUSPEND THE MIRROR BEFORE ANYTHING ELSE TOUCHES MINIO ⚠️

```sh
kubectl -n backups patch cronjob r2-mirror -p '{"spec":{"suspend":true}}'
```

**Why this is step 2 and not step 6**: `rclone sync` makes the destination match the source —
including deletions. If the hourly mirror fires while MinIO is empty/partially restored, it will
**delete the offsite copy you are restoring from**. Suspend first, verify `SUSPEND=True` in
`kubectl -n backups get cronjob`, only then proceed. Re-enable in step 7.

## Step 3 — seed the R2 read credentials + reverse-mirror into MinIO

```sh
bash infra/scripts/seed-r2-secrets.sh    # terraform outputs → Vault → r2-creds ExternalSecret
```

Then run the reverse sync (R2 → MinIO) as an in-cluster one-off Job. It is the mirror CronJob with
source and destination swapped:

```sh
kubectl -n backups get cronjob r2-mirror -o json | python3 -c "
import json,sys
cj=json.load(sys.stdin)
job={'apiVersion':'batch/v1','kind':'Job',
     'metadata':{'name':'r2-restore','namespace':'backups'},
     'spec':cj['spec']['jobTemplate']['spec']}
job['spec']['backoffLimit']=0
c=job['spec']['template']['spec']['containers'][0]
c['command']=['sh','-c','''fail=0
for b in cnpg-docketclock cnpg-langfuse pgdump vault-snapshots; do
  echo \"--- restoring \$b\"
  rclone sync \"r2:yokel-backups/\$b\" \"minio:\$b\" --fast-list --stats-one-line || fail=1
done
exit \$fail''']
print(json.dumps(job))" | kubectl apply -f -
kubectl -n backups wait --for=condition=complete job/r2-restore --timeout=1800s
kubectl -n backups logs job/r2-restore
```

Sanity: `task -d infra backup-status` — the ObjectStore section will still be empty (no clusters yet), but
MinIO now holds the base backups + WAL. Optionally verify a bucket listing via the MinIO console
(`task -d infra minio`).

## Step 4 — recover the DocketClock Postgres (the recovery seam)

Deploy the chart with the DR values — identical to the normal local install plus the
`postgres.recovery.*` block:

```sh
helm upgrade --install docketclock charts/docketclock -n docketclock --create-namespace \
  -f charts/docketclock/values.yaml -f charts/docketclock/values-local.yaml \
  --set postgres.recovery.enabled=true \
  --set postgres.recovery.sourceServerName=docketclock-pg
  # optionally: --set postgres.recovery.targetTime="<RFC3339>" for PITR; omit = newest WAL
```

CNPG bootstraps `docketclock-pg` by `recovery` from the restored MinIO store, then the migrate Job
(idempotent) and the api/poller deployments come up against it. Watch:

```sh
kubectl -n docketclock get cluster docketclock-pg -w    # → "Cluster in healthy state"
kubectl -n docketclock get pods
```

**Post-recovery archiving**: the recovered cluster keeps `backup.enabled=true` from values-local,
so it resumes WAL-archiving into `s3://cnpg-docketclock/` under the SAME serverName on the restored
store — continuity is intentional (barman handles the timeline switch). The nightly ScheduledBackup
takes a fresh base backup at 08:00 UTC (`immediate: true` fires one on land).

**Argo handoff (real incident, after the dust settles)**: `task platform` + applying
`app-docketclock.yaml` puts Argo back in charge. Argo's rendered manifest says `bootstrap: initdb`
while the live cluster was born from `recovery` — CNPG treats `bootstrap` as creation-only so
nothing re-runs, but Argo will show a persistent diff on the field. Options: add an
`ignoreDifferences` for `.spec.bootstrap` (+ `.spec.externalClusters`) to `app-docketclock.yaml`,
or accept the OutOfSync until the next planned cluster rebuild. During a drill, skip the handoff.

Langfuse: same shape by hand if you care to restore it during a drill (its manifests live in
`infra/argocd/manifests/langfuse/`; add a `bootstrap.recovery` + `externalClusters` stanza pointing
at `langfuse-db-store`/`serverName: langfuse-db`). At a real incident it is not on the critical
path — the observation log is.

## Step 5 — poller sanity (the resume-from-cursor guarantee)

The restored `poll_cursor` means the poller resumes differential polling where the backup left off:

```sh
PRIMARY=$(kubectl -n docketclock get cluster docketclock-pg -o jsonpath='{.status.currentPrimary}')
kubectl -n docketclock exec "$PRIMARY" -c postgres -- psql -U postgres -d docketclock -Atc \
  "SELECT source, last_polled_at FROM poll_cursor"
```

Let the poller run one cycle (≤15 min), then assert the gap was absorbed WITHOUT duplicate
observations — the 6h cursor overlap re-fetches the tail and the payload-hash dedupe drops
everything already in the log:

```sh
kubectl -n docketclock exec "$PRIMARY" -c postgres -- psql -U postgres -d docketclock -Atc \
  "SELECT count(*) - count(DISTINCT (source, coalesce(fr_document_number,''), payload_hash))
   FROM observations"    # MUST be 0 — payload-hash dedupe held through the restore
kubectl -n docketclock exec "$PRIMARY" -c postgres -- psql -U postgres -d docketclock -Atc \
  "SELECT max(fetched_at) FROM observations"   # advances past the restore point after a cycle
```

Also check `/readyz` through the api Service and that `docketclock_poller_last_heartbeat_seconds`
is fresh in Prometheus (or just watch the Grafana poller-stalled rule stay Normal).

## Step 6 — verify the backup pipeline is whole again

`task -d infra backup-status`: recovery window present for `docketclock-pg`, WAL archiving current, dump +
snapshot CronJobs will populate at the next 08:xx window. The `Backups` Grafana alerts (PR-5) go
Normal as each leg reports.

## Step 7 — re-enable the mirror (LAST)

Only after MinIO again holds everything the offsite copy should reflect:

```sh
kubectl -n backups patch cronjob r2-mirror -p '{"spec":{"suspend":false}}'
kubectl -n backups create job --from=cronjob/r2-mirror r2-mirror-postdrill
kubectl -n backups logs -f job/r2-mirror-postdrill   # clean sync, no mass deletions
```

## Step 8 — drill teardown (drill only)

```sh
k3d cluster delete yokel-dr
# if the live cluster was stopped for headroom: k3d cluster start yokel, then task -d infra cluster-restart
```

At a REAL incident there is no teardown — instead: rotate anything the incident may have exposed,
run `terraform apply` drift-check, and schedule the next Drill A within a week to confirm the new
store recovers too.

## Exit criteria (phase gate, PR-6)

- [ ] Drill A green from a clean run (`task drill-pitr`)
- [ ] Drill B executed once end-to-end: app up on the recovered log, poller resumed from the
      restored cursor with zero duplicate observations, mirror re-enabled with a clean sync
- [ ] This runbook corrected wherever reality disagreed with it during the execution
