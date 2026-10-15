# Early companion review (not final approval)

Inspected companion SHA256 `4a39e0ef63f1783a5c0389c7d9fd8b152171fcbaf8ba52d6cf4a139cff8210a6` while owner tests/receipts/export are unfinished.

The bounded replay design matches the agreed correction: identity uses query/display_order/URL rather than shifted candidate_order; original events remain read-only; prior blocked Q14 routes and same-state Q03 slot resolve without retrieval; Q05 is the only permitted catch-up acquisition; selected() for subsequent quotas comes from the logical replay; future queries require the corrected-prefix checkpoint. It labels the cohort protocol-deviation corrected and does not claim restored physical order.

One material issue to fix before final approval: register(q,p), currently lines163–167, checks direct_basis metadata before calling frozen.register. The frozen registration path is what persists exact raw record bytes and appends the retained/held receipt. A repeat metadata-converter error therefore raises before preservation/held evidence, recreating the failed-search audit gap just fixed. Persist the raw search response through frozen.preserve_search_response first, then run metadata validation; on failure append an exact-hash query_response_held event and leave the one-shot intent unresolved. Do not overwrite or silently correct the input record. The normal frozen.register call can reuse the already preserved exact bytes. Primary-hash-bound resolution remains the escape hatch for the same single response.

Final approval still requires stable tests/receipts/code hashes and the authoritative logical-view export verifier. No new source access is approved by this early review. No implementation files changed by this child.
