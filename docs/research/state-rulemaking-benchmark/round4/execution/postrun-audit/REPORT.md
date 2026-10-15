# Round 4 completed execution audit

All **285/285 checks passed**. All 12 scheduled documents reached terminal output. The audit made no provider calls, ran no proposer, read no source labels, and verified that all 125 execution artifacts stayed unchanged during inspection. Frozen implementation, Freeze A, and source PDF/text hashes matched their pins; authorization hash and attestations matched the run.

## Operations and accounting

The ledger contains **five OCR operations over 14 pages, zero Jev operations**, five completed HTTP 200 responses, and no stop records or unknown-cost operations. Each operation has its pinned request, immutable intent, retained raw response, parsed result, and matching response/decision hashes. No duplicate operation IDs or recorded retry attempts occurred. OCR starts were spaced at least 22 seconds apart; provider fallback and automatic retry were disabled in retained requests. This establishes ledger integrity, not an independent reconstruction of provider-internal transport behavior.

| Cost measure | USD |
| --- | ---: |
| OpenRouter response-reported cost | 0.02865504 |
| Jev usage/rate estimate | 0.00000000 |
| Conservative accounted cost before reserves | 0.05665504 |
| Nominal operation reserves | 0.15300000 |
| Conservative budget charge | 0.15300000 |

The accounted figure adds $0.002 per OCR page to the OpenRouter reported cost. This may double count page fees already included in the reported figure. The budget charge takes the greater of reserve and accounted cost per operation; all five reserves were larger. These are separate accounting measures, not a verified final invoice. The charge is below the $1 authorization.

## Routing and model exposure

Five `full_notice` documents acquired Mistral OCR annotations; seven documents with slice/unknown scope routed to source review. OCR source text exactly matched the retained annotation text joined by the frozen separator, rather than the wrapper completion. The exact Mistral backend version remains unavailable; wrapper model and engine alias were pinned.

There were **16 native candidates and seven OCR fallback candidates**. Every candidate was held by deterministic gates before Jev: conditional scope was a blocking issue on all 16 native and all seven fallback cases. Overlapping blockers included case size, multiple notice/rule scopes, lifecycle uncertainty, competing temporal roles, unresolved date structure, source corruption, and incomplete scope. Three documents produced no candidates in either available channel. The evidence supports conservative abstention, not a measured Jev success or failure.

All **23 terminal observations were `review`**, with zero `text_supported` observations. Every document remained research-only, not action-ready, with completeness requiring independent source audit and source fidelity unverified. No source-truth accuracy or completeness score was computed here. Empty observations are not evidence of complete extraction; empty disagreement arrays are not evidence of channel agreement when neither channel produced supported claims.

## Artifacts

- `audit.json`: counts, costs, per-document routes, and aggregate blockers.
- `checks.json`: all 285 check results.
- `execution-hashes.json`: immutable execution snapshot.
- `audit.py`: reproducible read-only audit, writing only this report directory.
