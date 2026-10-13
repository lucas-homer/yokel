# Round 8 — fresh-source development experiment

Status: the authorized native job ran once and stopped on an incomplete extraction response. One provider call occurred; no valid inventory, normalized record or verifier result was produced. Independent postrun audit and primary scoring verification are complete.

The reviewed R7 normalization changes are unchanged. This round tests new notices with the same source-only extraction and paired Jev/stronger verification policy. It is research only; no production records or state connectors are deployed.

## Actual cohort

| State | Pages | Sampling category |
| --- | ---: | --- |
| Wisconsin | 2 | General |
| Illinois | 1 | Conditional control |
| Massachusetts | 2 | General |
| Kentucky | 9 | Conditional control |
| Georgia | 3 | General |

Collection exhausted the 24 fixed queries: 413 displayed results, 71 corrected bounded candidate slots, five retained and 66 excluded. Exclusion reasons can overlap. The target of eight notices, at least six states, six general notices and two controls was not met. This is a **protocol-deviation corrected development cohort**, not a pristine preregistered validation sample or a population-accuracy estimate.

Candidate metadata initially missed direct-document routes in Illinois, Massachusetts and Ohio. The original responses and access history are preserved. Independently reviewed companion code replayed the original selection criteria in logical order, with bounded Massachusetts catch-up. Later guards caught an Indiana row-classification error and a replay bug reopening a definitive size exclusion. Both were resolved with retained evidence; no query rerun or duplicate download occurred. Physical access order cannot be restored and is explicitly disclosed.

## Readiness evidence

- Runtime review: 23 tests pass, plus independent budget-stop, preflight and receipt-tamper checks. Completed paid results are preserved when a reported charge triggers the stop guard.
- Final source audit: 374 checks pass. All source/code freeze hashes, promoted manifests, image hashes and five native-text replays match.
- Four exact inventory requests fit the frozen internal request cap. Kentucky's request does not fit in preflight; it remains in the schedule without clipping or replacement. The live run stopped before reaching it, so its observed state is not_started, not a live size rejection. This is an internal admission limit, not a measured provider context limit.
- Independent references contain 178 source units from all 17 page images, authored without native text, collector conclusions or provider outputs. The frozen truth validator and image/ledger linkage checks pass. These are AI references, not human-adjudicated gold.
- The $2 nominal reservation/stop guard and maximum 24 attempted provider operations remain fixed. No retries, fallback or paid repair are authorized. The guard is not an invoice guarantee.

## Execution outcome

After the user authorized the exact v3 binary, noninteractive identity and credential-injection smoke checks passed. The fixed native job verified all frozen inputs and sent one Wisconsin extraction request. OpenRouter returned HTTP 200 after about 80 seconds, but the response reached the 6,144 completion-token cap (`finish_reason=length`, native `max_output_tokens`) and ended inside an unterminated JSON string. The frozen parser rejected it; the global stop prevented further calls. No automatic retry or partial-response repair occurred.

The retained response reports $0.0688185, not invoice-verified. The intent reserves $0.100166 conservatively. No Jev or stronger verifier calls occurred, and the remaining four scheduled notices are not_started. This attempt cannot establish extraction quality, comparative verifier accuracy, safety from zero accepted records, or cost per successful record.

All 178 frozen image-reference units remain in the scheduled denominator. Source/reference/code freezes and all 3,519 prior-round baseline files remain unchanged. Raw outputs and service receipts are pinned in [Freeze E](execution/freeze-E.json). See [primary postrun checks](execution/primary-postrun-checks.json) and [post-authorization checks](execution/service-account/post-authorization-validation.json).

See [protocol](protocol/PROTOCOL.md), [runtime review](review/FINAL-REVIEW.md), [source audit](verification/final-source/REVIEW.md), [actual schedule](execution/schedule.json), and [inventory admission](execution/preflight-audit/inventory-admission.json). See the [independent audit](execution/postrun-audit/README.md), [failure diagnosis](execution/failure-analysis/DIAGNOSIS.md), [primary scoring verification](execution/primary-scoring-verification.json), and [reviewed next-step recommendation](execution/postrun-audit/NEXT-AMENDMENT-REVIEW.md). Frozen outputs remain intact.

## Next-step recommendation

The primary agrees with the independent reviewer: use the same Wisconsin source for one separately versioned development probe, changing only the inventory output cap to 12,288 tokens. Allow at most one inventory call and one call per verifier, conditional on assembly and both exact request bodies fitting the unchanged input caps. Keep the old $0.100166 conservative debit; the proposed combined worst-case nominal reservation is $0.406694 under the existing $2 envelope. This is a reviewed specification, not an implemented or executed job. No second paid attempt occurred. More output headroom may expose assembly or verifier-size limits; it does not guarantee quality or completion. Reused-source results must remain distinct from unseen validation.
