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
| `GEMINI_API_KEY`         | GitHub secret; repo-root `.env` locally          | yes (the poller)                                            |
| `DOCKETCLOCK_API_KEYS`   | GitHub secret; repo-root `.env` locally          | yes (the API)                                               |
| `ADJUDICATOR`            | `.env` / environment                             | no (defaults to `gemini`)                                   |
| `DOCKETCLOCK_POLL_CRON`  | GitHub variable / `.env`                         | no (unset means the cron is off; `*/15 * * * *` at cutover) |
| `DOCKETCLOCK_API_DOMAIN` | GitHub variable / `.env`                         | no (for example `api.docketclock.app`)                      |

`REGS_API_KEY`, `GEMINI_API_KEY` and `DOCKETCLOCK_API_KEYS` are new GitHub secrets. Use the values the
cluster uses today. Alchemy binds each one as a Worker secret, and the Durable Object hands it to its
container as an environment variable.

## Run it

From GitHub, open Actions, choose **Cloud deploy**, then **Run workflow**. Pick `plan` first, then `deploy`.

To run it locally from `infra/cloudflare`:

```sh
pnpm plan     # alchemy plan --stage prod --env-file ../../.env
pnpm deploy   # alchemy deploy --stage prod --env-file ../../.env
pnpm logs     # tail Worker logs
```

A local deploy needs Docker running, because it builds the image.

## Cutover (phase 2, not in this PR)

1. Deploy with the cron off. Copy the data over with `pg_dump` from the Mac mini cluster and
   `pg_restore --no-owner --role=docketclock` into Neon.
2. Stop the Mac mini poller, then set `DOCKETCLOCK_POLL_CRON=*/15 * * * *` and deploy.
3. Watch a few cycles with `pnpm logs`. Each cycle logs "poll cron fired", then the container's exit code.
