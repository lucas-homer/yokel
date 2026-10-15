# Evaluator executable review — bounded blockers

All published inventory hashes match and all 19 synthetic tests pass. No fresh sources, runtime outputs or provider calls were used. Frozen protocol files remain unchanged.

Three additional synthetic cases show protocol/metric mismatches:

1. **E01 — runtime readiness uses gold absence.** With both fields `not_stated`, no runtime observations and `action_ready=true`, false readiness is reported as 0/1. Gold completeness must not supply an absence-verification capability the frozen runtime does not have.
2. **E02 — unsupported abstention is field-wide.** A correct in-scope DATE acceptance suppresses abstention credit for an unrelated unsupported DATE. Score the source group using independent audit mappings; preserve conservative handling for unmapped claims and no-terminal work.
3. **E03 — acceptance grouping is unchecked.** Two different accepted dates mapped to different source facts collapse into one claim if the audits share a `claim_group`. Reject materially inconsistent groups; retain valid native/fallback duplicate grouping and unsafe-group tainting.

Exact reproduction outcomes, root causes and bounded regressions are in `executable-review-v1.json`. These are the complete remaining focused scoring fixes from this review. Existing value/role/condition audits, source-conflict handling, literal checks and scheduled/missing-work accounting are otherwise consistent with the requested adapter. Final source-stage recall and cost audits remain outside this terminal-only scaffold and must be reported unmeasured unless separately assessed.
