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
~2h wall clock as drilled — ~1h happy path; needs operator judgment at several steps). Drill C (Vault raft-snapshot restore into a
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
# Match the LIVE cluster's shape (infra/k3d/yokel.yaml): KEEP traefik (it's the chart's ingress
# class), same k3s image; skip the Tilt registry + host-port mappings a DR cluster doesn't need.
k3d cluster create yokel-dr --servers 1 --agents 1 --image rancher/k3s:v1.31.5-k3s1 --wait
k3d image import docketclock:local -c yokel-dr   # the app image is LOCAL-built, never in a registry
task -d infra bootstrap-argocd   # install Argo CD
task -d infra platform           # apply all platform-*.yaml Applications
bash infra/scripts/vault-transit-init.sh
task -d infra vault-seed # re-seed Vault: NEW random MinIO root creds, app secrets from your host env
```

(2026-07-11 drill: on a brand-new machine, build the image first — `docker build -t docketclock:local
apps/docketclock` — or point `image.repository` at a real registry; without the import every app pod
is `ImagePullBackOff`.)

Wait for the platform tier: `kubectl get applications -n argocd` — everything Synced/Healthy except
the CNPG clusters' backups (empty MinIO) and langfuse (restored below). `vault-seed` regenerating
MinIO root creds is fine — the fresh MinIO initializes with them; R2 does not care who reads it.

> **Apps stuck `SyncError` after vault-seed (2026-07-11 drill)**: apps whose ExternalSecrets need
> Vault (minio, vault-snapshot, langfuse) burn their 5 sync retries BEFORE the seed and then stop
> retrying. Re-trigger them — the minio app matters most (it owns the `r2-mirror` CronJob and the
> `r2-creds` ExternalSecret the next steps need):
>
> ```sh
> for app in minio vault-snapshot langfuse; do
>   kubectl -n argocd patch application $app --type merge -p '{"operation":{"sync":{"prune":true}}}'
> done
> ```

**If you are NOT restoring langfuse during this run, remove its app NOW, before step 3:**

```sh
kubectl -n argocd delete application langfuse
kubectl delete namespace langfuse --ignore-not-found
```

(2026-07-11 drill: the platform tier auto-creates a FRESH, empty `langfuse-db`, whose empty-archive
check passes because MinIO is still empty — it then starts archiving into `s3://cnpg-langfuse/`
under the original serverName, and step 3's reverse-mirror lands the OLD archive into the same
prefix: two histories mixed in one archive, unusable for recovery until re-mirrored from a good
source. Restore langfuse properly later, or re-create its app after step 3 with the same
new-serverName discipline as step 4.)

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

Deploy the chart with the DR values in **two steps** — both corrections are 2026-07-11 drill
findings:

1. **Migrations must be OFF for the cold install.** The migrate Job is a helm `pre-install` hook:
   on a cold install helm runs it BEFORE the Cluster manifest applies, the Job waits forever on the
   not-yet-existing `docketclock-pg-app` Secret, the hook times out (5m) and the release lands
   `failed` with NOTHING installed. (It never bites day-to-day because the live release predates the
   hook — `pre-upgrade` always has a running DB.)
2. **The recovered cluster must archive under a NEW serverName.** Barman's pre-restore check
   demands an EMPTY archive for the archiving server (`ERROR: WAL archive check failed for server
docketclock-pg: Expected empty archive`) — same-name "continuity" into the store you are reading
   from is refused by design. Bump a generation suffix: first recovery archives as
   `docketclock-pg-r1` (reading `docketclock-pg`); a later recovery archives `-r2` reading `-r1`.

```sh
# Step A — recover, migrations off:
helm upgrade --install docketclock charts/docketclock -n docketclock --create-namespace \
  -f charts/docketclock/values.yaml -f charts/docketclock/values-local.yaml \
  --set postgres.recovery.enabled=true \
  --set postgres.recovery.sourceServerName=docketclock-pg \
  --set postgres.backup.serverName=docketclock-pg-r1 \
  --set migrations.enabled=false
  # optionally: --set postgres.recovery.targetTime="<RFC3339>" for PITR; omit = newest WAL

kubectl -n docketclock get cluster docketclock-pg -w    # → "Cluster in healthy state" (~2m)

# Step B — same command, migrations back on (drop ONLY the migrations flag). The pre-upgrade hook
# now runs against the live recovered DB and proves itself idempotent ("schema up to date"):
helm upgrade docketclock charts/docketclock -n docketclock \
  -f charts/docketclock/values.yaml -f charts/docketclock/values-local.yaml \
  --set postgres.recovery.enabled=true \
  --set postgres.recovery.sourceServerName=docketclock-pg \
  --set postgres.backup.serverName=docketclock-pg-r1
```

Troubleshooting (all hit on 2026-07-11):

- **Recovery pod `Pending`, "persistentvolumeclaim … not found"**: you reinstalled while the
  previous release's PVC was still terminating. Fully drain first:
  `kubectl -n docketclock delete cluster docketclock-pg --wait && kubectl -n docketclock get pvc`
  (must be empty), then re-apply via `helm upgrade`.
- **api `503` on `/readyz` / poller `ECONNREFUSED` after the Cluster was deleted + recreated**: the
  pods hold the OLD generation's service IP and `docketclock-pg-app` password in env (read at pod
  start). `kubectl -n docketclock rollout restart deploy/docketclock deploy/docketclock-poller`.
  (Not needed on a clean single-pass install — pods retry into the same generation fine.)

**Post-recovery archiving**: with `backup.enabled=true` (values-local) + the bumped
`postgres.backup.serverName`, the recovered cluster WAL-archives into the same bucket under the NEW
server prefix on its recovery timeline, and the ScheduledBackup (`immediate: true`) fires a base
backup on land — `task -d infra backup-status` shows a fresh recovery window for
`docketclock-pg-r1` within minutes. The OLD prefix (`docketclock-pg/`) is now an unmanaged archive:
nothing writes it and NOTHING PRUNES IT (retention is enforced by the archiving cluster, which now
targets the new name). Keep it through a confidence window (≥14d), then delete it from the store by
hand; until then it remains a second recovery source. **Record the new generation** — the next
restore must use `--set postgres.recovery.sourceServerName=docketclock-pg-r1`.

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

- [x] Drill A green from a clean run (`task drill-pitr`) — 2026-07-10, all assertions exact
- [x] Drill B executed once end-to-end — **2026-07-11**: recovery byte-perfect against the pre-drill
      fingerprint (7830/4214/67/9 rows, identical cursors, append-only trigger intact), poller
      resumed from the restored cursor and absorbed the gap (+227 observations) with **zero
      duplicates**, archiving live under `docketclock-pg-r1` with a fresh base backup, mirror
      re-enabled with a clean sync. Deviation: Terraform state survived (same Mini), so the
      `terraform import` block above was not exercised live — the existing outputs fed
      `seed-r2-secrets.sh` directly; import remains the real-incident path.
- [x] This runbook corrected wherever reality disagreed with it during the execution — 9 findings
      folded in above (cluster-create flags, image import, task name, post-seed sync retries,
      langfuse pre-restore removal, two-step install, new-generation serverName, PVC drain race,
      post-recreate deployment restart)
