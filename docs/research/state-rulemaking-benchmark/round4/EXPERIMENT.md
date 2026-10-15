# Automated date/email pipeline — round four

Status: completed October 7, 2026. All 12 inputs reached terminal output; the progression gate was not met. See README.md for results and limitations.

This experiment connects automatic candidate discovery and context selection to deterministic checks and Jev. The bounded fields are explicit absolute written-comment deadline dates and submission emails. It preserves date precision: no invented time, timezone, missing year, or deadline arithmetic. Research outputs do not enter DocketClock production.

The target fresh cohort is 12 complete notices from at least six states, including four real publisher scans or degraded originals. Collection starts only after implementation and policy are frozen. Source-only labels are independently prepared and frozen before running the pipeline on fresh notices. Search order, failures, family overlap and any quota shortfall remain visible.

The runtime starts with native text. Mechanical quality and missing/ambiguous evidence can request Mistral OCR fallback; the route is recorded before fallback output is acquired. Jev judges semantic support/role/conditions/conflicts; code owns exact destination matching, date validity, offsets and schema checks. An accepted text claim remains distinct from original-source fidelity and completeness of the notice.

Bounds: 12 documents, at most 120 Jev case requests and 60 OCR input pages, at most $1 nominal estimated provider cost, no automatic retry of uncertain POST outcomes. Development uses old notices and synthetic cases. Fresh outcomes cannot justify changing the frozen pipeline; later fixes require a new version and fresh evaluation.

Frozen research progression gate: zero source-incorrect accepted critical claims, zero accepted unresolved conflicts, and at least 25 percent of source-resolvable in-scope fields correctly shadow-accepted. This is permission to learn from a larger shadow experiment, not proof of production safety. All scheduled notices, omissions, absent/inapplicable fields, fallback decisions, provider failures, and costs must be reported.
