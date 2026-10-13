# Round 8 bounded reconciliation companion

Status: preparation complete; fresh source access held. No amendment release exists.

The companion imports the unchanged frozen collector's mechanical acquisition, native PDF checks, rendering, retention, quota and one-shot query functions. It maps candidate identity by query, displayed rank and URL, reuses original observations, and maintains an append-only corrected logical ledger. Original artifacts remain unchanged. The original physical access order cannot be restored; the final cohort is explicitly classified as **protocol-deviation corrected**.

Corrected bounds are Q03 display 2/5/6, Q05 display 2/4/6, and Q14 display 1/2/3. Q03 display 13 remains preserved outside the corrected cohort. Only the missing Q05 Massachusetts routes need catch-up acquisition; Q03 display 5 is excluded by state spread without acquisition, and the missing Q14 routes are blocked by frozen prior URLs. Kentucky remains provisional until Massachusetts is resolved in logical order. A retained Massachusetts general notice of up to 28 pages permits Kentucky; 29–37 pages displaces Kentucky by aggregate page cap. A Massachusetts control fills the second control slot. A first Massachusetts candidate exceeding the aggregate cap leaves the next Massachusetts candidate pending.

## Release gate

Primary approval must create `amendment-release.json` with `authorized_reconciliation: true`, `authorized_future_queries` (explicit boolean), `primary_approval_message`, `timestamp_utc`, `companion_preparation_sha256`, `original_ledger_sha256`, and `plan_amendment_sha256`. Preparation authorization alone permits no acquisition. The receipt binds `preparation.READY.json` and its static file hashes. Future queries additionally require the immutable completed Q01–Q14 `logical-replay.READY.json` checkpoint.

Use the bundled Python with `-B`. Commands are `companion.py view`, `acquire Q05 1`, `review-pages Q05 1`, `retain Q05 1 REVIEW_NOTE`, `exclude Q05 1 REASON`, and `checkpoint`. Candidate ranks are corrected ranks, not original physical ranks. Always inspect the earliest pending identity from `view`; no independent advance is allowed. Future `query-request Q15` through Q24 and `register-search QUERY RECORD` use the unchanged fixed query strings, one-shot intent and preserved exact raw responses. Every future result row requires explicit source-only title/URL/metadata route review; known route patterns are minimum detection, not an exhaustive endpoint definition. Invalid classification is preserved and held without rerun or HTML expansion.

After the authorized collection reaches target or resolves Q24, `export_bundle.py` writes only inside this directory. Runtime and blind-image paths are relative to the **sources root**. The primary must promote the manifest, blind inventory and metadata byte-identically to new canonical top-level sources paths before invoking the fixed runtime adapter; do not pass a nested manifest directly to it.

## Offline validation

`test_companion.py` runs seven bounded controls with network and native subprocess dispatch prohibited. They cover corrected rank reuse, Massachusetts quota/page branches, absent-release refusal, cohort/manifest equality, preserved held raw responses, explicit document routes outside minimum patterns, and all 503 original source plus 69 Freeze A byte pins. `prepare_companion.py` is a completed one-time preparation utility and must not be rerun. Mutable access/correction ledgers start empty and are excluded from static preparation pins.
