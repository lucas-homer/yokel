# 0002. Single monorepo with pnpm workspaces

- Status: Accepted
- Date: 2026-06-14

## Context

The architecture is a shared **substrate** (DocketClock) with **vertical wedges** (Watershed Watch)
that rent it via a contract: OCD-IDs, the `ParticipationWindow` schema, and the REST/webhook surface.
The Watershed Watch standalone contingency is explicitly "fork the deployment, never the schema."

## Decision

One monorepo, pnpm workspaces only (no Turborepo/nx yet). Layout: `packages/contracts` (the shared
seam), `apps/docketclock`, `apps/watershed-watch`, `spikes/`, `docs/`. Heavy generated artifacts live
in `docs/research/` and are deliberately not referenced by any `CLAUDE.md` so agents don't auto-load
them. TypeScript + Node 24.

## Consequences

- The shared contract lives in exactly one place; a vertical can be built without forking the core,
  and the standalone contingency forks only deployment.
- Single issue tracker, single history, easy machine-to-machine transport via git.
- No build-graph tooling overhead until there's a measured need (revisit if builds get slow).
- Alternatives rejected: two separate repos (tempts a schema fork; splits issues/history).
