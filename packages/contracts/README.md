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
- `AccuracyRecord` (+ `AccuracyBasis`/`AccuracyVerdict`/`AccuracyHorizon`) — the post-close
  verification verdict (append-only trust primitive; never correctness-by-default, misses name
  their contradicting observations).
- `HumanReviewVerdict` (+ `HumanReviewVerdictKind`) — the typed `raw` payload for
  `source: human_review` observations (Slice R): a resolution is an observation, never a mutation,
  and it is honored only while no source observation is newer (supersedence lands in reconcile-v2).

**Rule:** never fork this schema — only fork the deployment. The Watershed Watch standalone
contingency still emits OCD-Event-shaped records so it can rejoin DocketClock later.

Status: **built and in active use** (see `package.json` for the current version; changes go
through the contract-keeper flow with a version bump). The `AccuracyRecord` shape landed at
0.9.0 with the post-close verification slice (V, PR-V1); the `human_review` source +
`HumanReviewVerdict` + `human_resolved` flag landed at 0.10.0 with the review/resolve slice (R, PR-R1).
