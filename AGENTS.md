# AGENTS.md — working notes for agents

Read this first. It's the map and the conventions. Keep it small and high-signal.
Provider-agnostic on purpose (Claude + other models/harnesses). Follows the
[AGENTS.md](https://agents.md) convention.

## What this project is

Yokel is a civic-tech monorepo helping **busy non-experts** monitor public-comment periods / rules /
hearings and take meaningful action. Architecture is a layered "house":

- **DocketClock** (`apps/docketclock`) — the federal comment-deadline **substrate**. Built FIRST.
  Net-new value = reconciliation + confidence + provenance, NOT discovery. Append-only Observation
  log is primary; `ParticipationWindow` is a derived, versioned projection. Federal-only is a hard
  rule until a paying customer funds a jurisdiction tranche.
- **Watershed Watch** (`apps/watershed-watch`) — the first **vertical wedge**. Rents DocketClock
  (partial build-on); OWNS EPA EIS ingestion, HUC geo-recall, and the action/receipt loop.
- **`packages/contracts`** — the shared seam both consume (schemas, OCD-IDs, confidence enums).
  Verticals join on **stable OCD-IDs**, never internal UUIDs. Never fork the schema, only the deployment.

Full designs: `docs/architecture/docketclock.md` and `docs/architecture/watershed-watch.md`
(canonical, generated from `arch-foundry-result.json` via `tools/gen_arch_md.py` — regenerate, don't hand-edit).

## Where things live

- **Decisions / the "why":** `docs/decisions/` (ADRs). Add an ADR for any consequential call.
- **Plans:** `docs/plans/` — the immediate work is `week1-validation-spikes.md`.
- **Heavy reference:** `docs/research/` (100KB+ HTML reports, foundry JSON). **Do NOT read these
  routinely** — they're large and burn context. The markdown in `docs/architecture/` is the
  distilled, canonical form. Reach into `docs/research/` only when explicitly needed.

## Conventions

- **Two machines.** Authoring/organizing/git happens on the **MacBook Air**. **All installs, local
  env, Postgres, and builds happen on the Mac Mini** (see `SETUP.md`). Do NOT run `pnpm install`,
  start databases, or create `node_modules`/`.env` on the Air. GitHub is the transport.
- **Validate before building.** Don't write DocketClock pipeline code until the Week-1 spikes pass —
  especially D1 (frDocNum join hit-rate) and W3 (in-basin value density). A measured "no" is a win.
- **Don't publish fake certainty.** This is the product's core principle AND a working norm: surface
  unknown/conflicting states honestly; never assert an API field/endpoint exists without verifying.
- **Stack:** TypeScript (Node 24), pnpm workspaces, Fastify + Zod, Postgres 16 (+ PostGIS for
  Watershed). No Turborepo/OpenSearch/Temporal until a measured bottleneck justifies them.
- ADRs use the lightweight format in `docs/decisions/0001-record-architecture-decisions.md`.

## Naming

`yokel` is a codename; the public umbrella brand is parked (ADR 0006). Product names (DocketClock,
Watershed Watch) are settled.
