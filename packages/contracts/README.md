# @yokel/contracts

The **shared seam** between the DocketClock substrate and vertical wedges (Watershed Watch).

This is the single most important package for long-term maintainability: it holds the schemas and
types both sides agree on so a vertical can be built without forking the core.

- `ParticipationWindow` — the canonical unit of trust (a derived, versioned projection over the
  Observation log).
- Stable **OCD-IDs** — the cross-system join key. Verticals join on these, **never** internal UUIDs.
- `Confidence`, `ConflictFlag`, `WindowType`, `WindowStatus` enums.
- `Observation` and `ConflictRecord` (incl. the cross-window `conflict_scope` extension), the
  RuleBox rules-as-data shapes, the adjudication verdict types, and the REST response envelope.

**Rule:** never fork this schema — only fork the deployment. The Watershed Watch standalone
contingency still emits OCD-Event-shaped records so it can rejoin DocketClock later.

Status: **built and in active use** (see `package.json` for the current version; changes go
through the contract-keeper flow with a version bump). Still TODO: the `AccuracyRecord` shape,
which lands with the post-close verification phase.
