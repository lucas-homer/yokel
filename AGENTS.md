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
  **Shelved** at the W3 value-density gate (stub only) — revival paths in the go/no-go memo.
- **`packages/contracts`** — the shared seam both consume (schemas, OCD-IDs, confidence enums).
  Verticals join on **stable OCD-IDs**, never internal UUIDs. Never fork the schema, only the deployment.

Full designs: `docs/architecture/docketclock.md` and `docs/architecture/watershed-watch.md`
(canonical, generated from `arch-foundry-result.json` via `tools/gen_arch_md.py` — regenerate, don't hand-edit).

## Where things live

- **Decisions / the "why":** `docs/decisions/` (ADRs). Add an ADR for any consequential call.
- **Plans:** `docs/plans/` — the Week-1 spikes are **done**; outcomes in `week1-go-no-go-memo.md`.
  Phase plans (observability slices, rename) live in `plans/` at the repo root. How we build with
  agent teams (roles, phases, gating): `docs/plans/agent-orchestration.md`; the team lives in `.claude/agents/`.
- **Heavy reference:** `docs/research/` (100KB+ HTML reports, foundry JSON). **Do NOT read these
  routinely** — they're large and burn context. The markdown in `docs/architecture/` is the
  distilled, canonical form. Reach into `docs/research/` only when explicitly needed.

## Conventions

- **Two machines.** Authoring/organizing/git happens on the **MacBook Air**. **All installs, local
  env, Postgres, and builds happen on the Mac Mini** (see `SETUP.md`). Do NOT run `pnpm install`,
  start databases, or create `node_modules`/`.env` on the Air. GitHub is the transport.
- **Validate before building.** The Week-1 gates are decided (D1 join hit-rate passed → DocketClock
  BUILD; W3 value density → Watershed Watch shelved), but the norm stands: measure before building —
  e.g. run a value-density spike before any new wedge gets code. A measured "no" is a win.
- **Don't publish fake certainty.** This is the product's core principle AND a working norm: surface
  unknown/conflicting states honestly; never assert an API field/endpoint exists without verifying.
- **Stack:** TypeScript (Node 24), pnpm workspaces, Fastify + Zod, Postgres 18 (+ PostGIS for
  Watershed). No Turborepo/OpenSearch/Temporal until a measured bottleneck justifies them.
- **Infrastructure (ADR 0008 + 0009):** Kubernetes is the platform, GitOps-managed by **Argo CD**.
  Postgres 18 is **self-hosted via CloudNativePG** (chart `postgres.imageName` is PINNED, and CI's test
  Postgres matches it — keep them in lockstep; a 16/18 skew once let a PG18-only SQL parse error past CI);
  the app tier runs in-cluster. Packaging is **Helm**
  (vendored operators + our `charts/docketclock` with `values-local.yaml` / `values-cloud.yaml`);
  secrets via **External Secrets Operator + self-hosted Vault**; cloud provisioning via **Terraform**
  (structure now, provider deferred). Dev is **full in-cluster** on **k3d/colima** on the Mini — bring
  it up with `cd infra && task dev-up` (the codified runbook is `infra/`). Deploys land via **git →
  Argo reconciles**, not imperative `kubectl`. This **overrides** the architecture doc's "No Kubernetes
  / managed-Postgres" hosting line. The Postgres-as-everything data choices (outbox queue, FTS) are
  unchanged.
- ADRs use the lightweight format in `docs/decisions/0001-record-architecture-decisions.md`.

## Naming

`yokel` is a codename; the public umbrella brand is parked (ADR 0006). Product names (DocketClock,
Watershed Watch) are settled.
