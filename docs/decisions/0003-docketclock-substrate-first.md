# 0003. Build DocketClock (the substrate) first

- Status: Accepted
- Date: 2026-06-14

## Context

Both our idea foundry and a parallel "Codex" run independently converged on the
comment-deadline-as-trustworthy-object as the reusable primitive everything else needs. Our own
foundry initially under-rated it by scoring it as a consumer app; reframed as substrate it's the
correct first build. Full design: `docs/architecture/docketclock.md`.

## Decision

Build DocketClock first as a federal-only B2B picks-and-shovels API/webhook. Net-new value is
reconciliation + confidence + provenance, not discovery. Three non-negotiables:

1. Append-only **Observation log is primary**; `ParticipationWindow` is a derived, versioned projection.
2. Conflict detection compares dates normalized to **America/New_York**, not UTC.
3. Confidence drop **suppresses the alert AND fires a conflict notification** (suppression ≠ silence).

Federal-only is a hard rule until a paying customer funds a specific jurisdiction tranche.

## Consequences

- The substrate is honest, auditable, and rentable by verticals via OCD-IDs + a tag/enrichment contract.
- It is an honest pivot from the original "busy citizen" thesis at the substrate layer; the civic
  mission returns through the vertical wedges (see [0004](0004-watershed-watch-partial-build-on.md)).
- Build is gated behind the Week-1 spikes (`docs/plans/week1-validation-spikes.md`), esp. D1.
