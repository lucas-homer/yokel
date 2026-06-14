# @yokel/contracts

The **shared seam** between the DocketClock substrate and vertical wedges (Watershed Watch).

This is the single most important package for long-term maintainability: it holds the schemas and
types both sides agree on so a vertical can be built without forking the core.

- `ParticipationWindow` — the canonical unit of trust (a derived, versioned projection over the
  Observation log).
- Stable **OCD-IDs** — the cross-system join key. Verticals join on these, **never** internal UUIDs.
- `Confidence`, `ConflictFlag`, `WindowType`, `WindowStatus` enums.

**Rule:** never fork this schema — only fork the deployment. The Watershed Watch standalone
contingency still emits OCD-Event-shaped records so it can rejoin DocketClock later.

Status: **stub**, pinned to `docs/architecture/docketclock.md`. Validation refinements and the
Observation/ConflictRecord/AccuracyRecord shapes are TODO (land when DocketClock is built).
