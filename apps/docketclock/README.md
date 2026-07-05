# DocketClock

The reconciled federal comment-deadline **substrate** — built first, now running.

> Net-new value = reconciliation + confidence + provenance, NOT discovery. The append-only
> Observation log is primary; `ParticipationWindow` is a derived, versioned projection. Federal-only
> until a paying customer funds a jurisdiction tranche.

**Full design:** [`docs/architecture/docketclock.md`](../../docs/architecture/docketclock.md)
**Build gate (passed):** [`docs/plans/week1-go-no-go-memo.md`](../../docs/plans/week1-go-no-go-memo.md)
— D1 frDocNum join hit 78.7% → **BUILD**, frDocNum-primary join strategy.

Three non-negotiables (see the design for why):

1. Conflict detection compares dates normalized to **America/New_York**, not UTC.
2. Confidence drop **suppresses the alert AND fires a conflict notification** — suppression is never silence.
3. Never publish fake certainty — unknown/conflicting states surface honestly, with provenance.

## What's here

- `src/sources/` — Federal Register (keyless) + Regulations.gov v4 adapters; differential polling
- `src/ingest/` — append-only observation log (mutation-rejecting triggers)
- `src/reconcile/` + `src/rulebox/` — window projection, cross-window chain links, deterministic
  rules-as-data classification
- `src/adjudicator/` — provider-agnostic LLM port (Gemini adapter) for borderline chain links,
  verdict cache, Langfuse tracing, gold-corpus evals
- `src/poll/` — single-writer poll loop (FR → Regs → chain reconcile), dead-lettering, heartbeat
- `src/api/` — Fastify delivery API (`/v1/windows`, `/v1/conflicts`, `/openapi.json`), fail-closed
  `x-api-key` auth
- `migrations/` — Postgres migrations (run by the chart's migrate Job)

Entrypoints: the Helm chart runs `src/api/run.ts` (API), `src/poll/run.ts` (poller), and
`src/db/migrate.ts` (migrate Job) from one image — `src/index.ts` is a legacy placeholder.

## Common commands

```bash
pnpm --filter @yokel/docketclock test          # full suite (incl. adversarial variants)
pnpm --filter @yokel/docketclock eval:chain    # adjudicator gold-corpus eval
pnpm --filter @yokel/docketclock smoke:fr      # live Federal Register smoke
pnpm --filter @yokel/docketclock smoke:regs    # live Regulations.gov smoke (needs REGS_API_KEY)
```

Local deploy/inner loop: see the [root README](../../README.md) (`task dev-up`, then `tilt up`).
