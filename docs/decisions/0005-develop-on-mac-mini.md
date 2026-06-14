# 0005. Author on the Air, build on the Mac Mini; GitHub is the bridge

- Status: Accepted
- Date: 2026-06-14

## Context

Planning/organizing currently happens on a MacBook Air, but the local dev environment and builds are
intended to live on a Mac Mini. We need the project to move cleanly between machines.

## Decision

- The Air is for **authoring text** (docs, configs, stubs) and **git**. No `pnpm install`, no
  `node_modules`, no local Postgres, no `.env` on the Air.
- The Mac Mini is for **all installs, local env (Postgres/PostGIS), and builds.** Bootstrap is in
  `SETUP.md`.
- **GitHub is the transport.** Push from the Air, `git clone` on the Mini.

## Consequences

- Everything that matters travels as text via git; the repo stays light and reproducible.
- `SETUP.md` is the canonical Mini bootstrap; `AGENTS.md` encodes the two-machine convention so
  agents don't try to install/build on the Air.
- Secrets never live in the repo (`.env` gitignored; `.env.example` is the template).
