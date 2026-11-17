# 0019: Host DocketClock on Cloudflare Containers + Neon, declared with Alchemy

- Status: proposed
- Date: 2026-11-17

## Context

DocketClock runs on a k3d cluster on a Mac mini. Lucas wants it in the cloud cheaply. He already pays for
Cloudflare Workers, and is learning Alchemy and Effect. Running a managed Kubernetes cluster is the costly
option we're avoiding. The fallback is Hetzner CAX with k3s.

## Decision

- Run the **existing Docker image** in Cloudflare Containers:
  - The **poller** runs one cycle per Cron Trigger (`--once`), then exits.
  - The **API** runs in a container that sleeps when idle, fronted by a Worker.
- Use **Neon** Postgres 18. It keeps plain Postgres, so `pg_dump`/`pg_restore` carries the history over and no SQL is rewritten. D1 was ruled out: it has a 10 GB cap and would need a rewrite.
- Declare everything in **Alchemy v2** (`infra/cloudflare/alchemy.run.ts`), with state in `Cloudflare.state()`.
- Enforce **one poll cycle at a time** with a Postgres session advisory lock (`src/poll/cycle-lock.ts`), on
  Neon's **direct** endpoint. The pooled endpoint uses pgbouncer in transaction mode, which would break a session lock.

## Consequences

- The ingest/reconcile single-writer assumption now holds across processes, whatever starts a cycle.
- Alchemy v2 is beta and pinned exactly (`2.0.0-beta.87`). Expect breaking changes on upgrade.
- The cron stays off until cutover. The Mac mini remains the writer until then.
- Not done yet:
  - porting the poller to Workflows and the API to a native Worker (planned with the Effect migration);
  - embeddings in Vectorize;
  - raw documents in R2.
