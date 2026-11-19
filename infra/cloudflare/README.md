# DocketClock on Cloudflare + Neon

Phase 1 of the move off the Mac mini ([ADR 0019](../../docs/decisions/0019-cloudflare-neon-hosting.md)).
This package is an [Alchemy v2](https://alchemy.run) program, `alchemy.run.ts`, that declares the following resources.

| Resource                            | What it is                                                                                                                       |
| ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `Db`: Neon project `docketclock`    | Postgres 18 in `aws-us-west-2`, with database and role `docketclock`                                                             |
| `Poller` Worker + `PollerContainer` | A Cron Trigger starts one container that runs one poll cycle (`src/poll/run.ts --once`) and exits. Pending migrations run first. |
| `Api` Worker + `ApiContainer`       | Every request is forwarded to the Fastify API in a container. The container sleeps after 10 idle minutes.                        |
| Alchemy state store                 | A Worker that Alchemy creates on the account to hold deploy state (`Cloudflare.state()`)                                         |

Both containers run the **existing** image (`apps/docketclock/Dockerfile`), so the app code doesn't change.

## Safe by default

- **The poll cron is OFF** unless `DOCKETCLOCK_POLL_CRON` is set. Deploying this next to the Mac mini adds
  no second writer. Even with both running, the poll-cycle advisory lock (`apps/docketclock/src/poll/cycle-lock.ts`)
  skips any cycle that overlaps another one.
- **The API is on `workers.dev`** until `DOCKETCLOCK_API_DOMAIN` is set. That needs the `docketclock.app` zone
  on the account and the token's second policy: Specified Domains, with Zone Read, DNS Edit and Workers Routes Edit.
- **Nothing deploys automatically.** The `Cloud deploy` workflow runs only when you start it by hand.

## Settings it reads

| Name                     | Where                                            | Required                                                    |
| ------------------------ | ------------------------------------------------ | ----------------------------------------------------------- |
| `CLOUDFLARE_API_TOKEN`   | GitHub secret, or your Alchemy profile locally   | yes                                                         |
| `CLOUDFLARE_ACCOUNT_ID`  | GitHub variable, or your Alchemy profile locally | yes                                                         |
| `NEON_API_KEY`           | GitHub secret; repo-root `.env` locally          | yes                                                         |
| `REGS_API_KEY`           | GitHub secret; repo-root `.env` locally          | yes (the poller)                                            |
| `CLOUDFLARE_AI_TOKEN`    | GitHub secret; repo-root `.env` locally          | yes (the poller)                                            |
| `DOCKETCLOCK_API_KEYS`   | GitHub secret; repo-root `.env` locally          | yes (the API)                                               |
| `DOCKETCLOCK_POLL_CRON`  | GitHub variable / `.env`                         | no (unset means the cron is off; `*/15 * * * *` at cutover) |
| `DOCKETCLOCK_API_DOMAIN` | GitHub variable / `.env`                         | no (for example `api.docketclock.app`)                      |
| `HEALTHCHECKS_PING_KEY`  | GitHub secret / `.env`                           | no (unset means no alerts; see [Alerts](#alerts))           |
| `NTFY_URL`               | GitHub secret / `.env`                           | no (unset means no daily review nag)                        |

LLM adjudication goes through Cloudflare AI Gateway. The live model is not a setting: it is
`ADJUDICATOR_MODEL` in `apps/docketclock/src/adjudicator/model.ts`, so changing models is a reviewed
one-line diff. `CLOUDFLARE_AI_TOKEN` is an account API token with Account > Workers AI > Read.

`REGS_API_KEY`, `CLOUDFLARE_AI_TOKEN` and `DOCKETCLOCK_API_KEYS` are GitHub secrets. Use the values the
cluster uses today. Alchemy binds each one as a Worker secret, and the Durable Object hands it to its
container as an environment variable.

## Alerts

The Mini's Grafana alerts, ported. The rules live in `apps/docketclock/src/alerts/` and the poller checks
them at the end of every cycle, then pings [healthchecks.io](https://healthchecks.io), which pages through
the project's ntfy integration.

| Check                  | Pages when                                                                                                   |
| ---------------------- | ------------------------------------------------------------------------------------------------------------ |
| `docketclock-poller`   | no cycle has finished for 45 minutes (Cloudflare, the container or Neon is down), or a cycle failed outright |
| `docketclock-api`      | the API's `/readyz` is not 200 (checked hourly by the poller)                                                |
| `docketclock-passes`   | one pass failed in 3 or more cycles in the last hour                                                         |
| `docketclock-llm`      | more than 3 AI Gateway calls failed in one cycle                                                             |
| `docketclock-accuracy` | HIGH-confidence deadlines were right less than 95% of the time over 90 days (sample of 20 or more)           |

Escalations waiting on a human, and conflicts older than 7 days, go to ntfy directly once a day at
16:00 UTC (8 AM Pacific), since healthchecks.io only notifies on a change.

Setup, once:

1. In the healthchecks.io project, add an ntfy integration (Integrations → ntfy) for your topic.
2. In project Settings, create a ping key and a read-write API key.
3. Add GitHub secrets `HEALTHCHECKS_PING_KEY`, `HEALTHCHECKS_API_KEY` and `NTFY_URL` (the topic URL).
4. Run **Alerts sync** from the Actions tab. It creates the checks from `checks.ts` and keeps them in step
   whenever that file changes on main.
5. Run **Cloud deploy** so the poller gets the ping key.

## Run it

From GitHub, open Actions, choose **Cloud deploy**, then **Run workflow**. Pick `plan` first, then `deploy`.

To run it locally from `infra/cloudflare`:

```sh
pnpm plan     # alchemy plan --stage prod --env-file ../../.env
pnpm deploy   # alchemy deploy --stage prod --env-file ../../.env
pnpm logs     # tail Worker logs
```

A local deploy needs Docker running, because it builds the image.

## Cutover from the Mac mini

Order matters: stop the Mini's poller **before** the dump, so nothing is written to the Mini database
after the copy. Every command below runs on the Mac mini, with `kubectl` pointed at the k3d cluster.
Postgres tools run inside the CNPG pod (same 18.x version as Neon), so nothing else needs installing.

### 1. Stop the Mini poller

The Mini runs the chart with Helm (`task app-local`) or Tilt, not Argo. Scale the poller to zero. Neither
Helm nor Tilt restores replicas on its own, but if `tilt up` is running on the Mini, stop that process
with Ctrl-C. **Never run `tilt down` here**: it deletes everything Tilt deployed, including the
`docketclock-pg` Cluster and its volume.

```sh
kubectl -n docketclock scale deploy/docketclock-poller --replicas=0
```

Check that it is gone. This must show no `Running` pod (old `Completed` pods do not matter):

```sh
kubectl -n docketclock get pods -l app.kubernetes.io/component=poller
```

To keep it off across a later `task app-local`, pass `--set poller.enabled=false`. (The Argo app in
`infra/argocd/apps/app-docketclock.yaml` already sets that, for a cluster where Argo runs the chart.)

Grafana's **Poller stalled** alert fires once the heartbeat goes stale. Silence it, or ignore it.

### 2. Dump the Mini database

```sh
PG_POD=$(kubectl -n docketclock get pod -l cnpg.io/cluster=docketclock-pg,cnpg.io/instanceRole=primary -o name)
kubectl -n docketclock exec "$PG_POD" -c postgres -- pg_dump -Fc -d docketclock > ~/docketclock-cutover.dump
ls -lh ~/docketclock-cutover.dump
```

Keep this file until the cloud poller has run cleanly for a few days.

### 3. Get the Neon connection string

In the Neon console, open project **docketclock**, then click **Connect**. Choose branch `main`,
database `docketclock` and role `docketclock`, and turn **Connection pooling** off (the poller's advisory
lock needs a direct connection). Copy the string, then paste it at this hidden prompt so it stays out of
your shell history:

```sh
read -rs NEON_URL; echo
```

Confirm Neon is still empty. This must print `Did not find any relations.`:

```sh
kubectl -n docketclock exec "$PG_POD" -c postgres -- psql "$NEON_URL" -c '\dt'
```

### 4. Restore into Neon

`--single-transaction` means a failure leaves Neon empty, so a retry starts clean.

```sh
kubectl -n docketclock exec -i "$PG_POD" -c postgres -- \
  pg_restore --no-owner --no-acl --single-transaction --exit-on-error -d "$NEON_URL" \
  < ~/docketclock-cutover.dump
```

### 5. Compare row counts

```sh
Q="select 'schema_migrations' t, count(*) from schema_migrations
union all select 'observations', count(*) from observations
union all select 'observation_targets', count(*) from observation_targets
union all select 'participation_windows', count(*) from participation_windows
union all select 'conflict_records', count(*) from conflict_records
union all select 'adjudications', count(*) from adjudications
union all select 'accuracy_records', count(*) from accuracy_records
union all select 'poll_cursor', count(*) from poll_cursor
union all select 'poll_dead_letter', count(*) from poll_dead_letter
union all select 'regs_poll_watch', count(*) from regs_poll_watch
union all select 'verification_watch', count(*) from verification_watch order by 1"
kubectl -n docketclock exec "$PG_POD" -c postgres -- psql -d docketclock -c "$Q"   # Mini
kubectl -n docketclock exec "$PG_POD" -c postgres -- psql "$NEON_URL" -c "$Q"     # Neon
```

The two tables must match exactly. Then note where the poll cursor stands:

```sh
kubectl -n docketclock exec "$PG_POD" -c postgres -- psql "$NEON_URL" -c 'select * from poll_cursor'
```

### 6. Turn on the cloud cron

In GitHub, open **Settings**, then **Secrets and variables**, then **Actions**, then the **Variables** tab.
Add a repository variable `DOCKETCLOCK_POLL_CRON` with the value `*/15 * * * *`. Run **Cloud deploy** with
`plan` (it should show only the Poller Worker changing), then `deploy`.

### 7. Check the first cycles

After 15 to 30 minutes, run the `poll_cursor` query from step 5 again: `last_polled_at` should be recent.
`pnpm logs` (from `infra/cloudflare`) shows "poll cron fired" and each container's exit code.

### Rolling back

Delete the `DOCKETCLOCK_POLL_CRON` variable and deploy, which turns the cron off. Then revert the
`poller.enabled` parameter in `app-docketclock.yaml`, and the Mini poller resumes on the Mini database.
Anything the cloud poller wrote to Neon in the meantime is not copied back.
