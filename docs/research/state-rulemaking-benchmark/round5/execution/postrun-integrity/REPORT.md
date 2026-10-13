# Round 5 completed execution integrity audit

**2,130/2,130 checks passed.** All eight scheduled documents (22 input pages) have completed terminal output. The 22 candidates reconcile to nine successful Jev POST operations plus 13 deterministic reviews. There are zero OCR operations, no stop records, no uncertain/temporary operation artifacts, and no duplicate operation IDs. Every operation has a durable identity/request/intent, HTTP 200 status/latency, exact raw response hash and parsed usage/judgments.

Request and response model IDs are `jev-1.13.0`; all four Choice questions exactly match the pinned rubrics and full-notice projection policy. Full request source text hashes match the original frozen native bytes. Case/request hashes, provider dimensions/probabilities/confidence, categorical acceptance, conservative competitor resolution and terminal projections all reconcile. Completed receipt documents and cost totals match individual retained artifacts. All 104 execution files remained unchanged during audit and match Freeze E.

## Costs and timing

| Measure | Result |
| --- | ---: |
| Reported Jev input tokens | 26,638 |
| Reported Jev output tokens | 1,547 |
| Usage × pinned rate estimate | $0.001118796 |
| Nominal reservations | $0.005140464 |
| Conservative budget charge | $0.005140464 |
| Authorized cap | $0.10 |
| Retained POST latency sum | 1.9372 s |
| Mean POST latency | 0.2152 s |
| POST latency range | 0.1198–0.4012 s |

Cost is an estimate from provider-returned token usage at $0.042/M input tokens, output free. No provider-reported charge or final invoice is verified. Conservative accounting sums the greater of reservation and estimated cost per operation. POST latency excludes 1Password authorization, collection, labeling and the full workflow.

## Freezes and labels-before-output evidence

Freeze A has 181/182 exact original matches. The sole exception is the primary's explicitly append-authorized access ledger: originally empty, now 9,593 bytes, matching the exception receipt and Freeze S. Freeze A was not rewritten. All 230 Freeze S files, all seven Freeze B files and all 104 Freeze E files match exactly. Label files were hashed only as opaque bytes; no label contents were parsed or evaluated.

The six-key authorization, immutable run pins and pre-output binding all reference Freeze B SHA `657a6c89696cd3c8f64d8372f74dc8373964193c17b405aa033cdd66c85cf839`. Labels were frozen at 11:10:17 a.m. PDT October 7, 2026; the primary's absent-run binding followed immediately. First retained POST intent is 11:45:21 a.m. PDT. This is consistent with labels-before-output chronology. The absent-run fact remains a primary attestation; hashes and retained timestamps do not independently establish OS isolation or trusted wall-clock authority.

## Outcomes and limits

Terminal observations are six `text_supported` and 16 `review`. All documents remain research-only, not action-ready, source fidelity unverified and completeness requiring independent audit. These statuses are implementation outcomes; this audit does not score correctness, extraction fidelity or source coverage.

The retained ledger shows nine single-attempt successful calls with no recorded retransmission, fallback or model mismatch. Provider-internal transport history is not independently observable. The primary reports an earlier 1Password timeout before run creation and before any calls; the successful ledger cannot independently prove that negative event.

No provider calls, runtime/proposer imports, source/image content inspection or label-content reads by this audit. Only this new postrun-integrity directory was written. Edits stop with this report.
