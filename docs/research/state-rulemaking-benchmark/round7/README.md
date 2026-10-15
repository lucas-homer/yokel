# State notice normalization fixes

The reviewed specification is implemented as a new offline research version. Correct weekday-prefixed dates, source-evidenced multipart routes, and purpose-scoped contact alternatives are now representable without weakening exact evidence checks. Runtime and evaluator reporting distinguish pipeline rejection from an uncalled verifier or a completed judgment.

The [specification](SPEC.md) was approved in [independent spec review](review/SPEC-REVIEW.md). Its original proposed-status text is retained with the reviewed hash; the approval record and coordination status establish the later implementation decision. Implementation review found and resolved prompt guidance, observation consistency, page-cap and numeric-cost defects. [Final code review](review/FINAL-REVIEW.md) records approval.

| Change | Behavior |
| --- | --- |
| Complete dates with weekdays | Validate the printed weekday against the date; preserve raw evidence and reject conflicts without inferring years or timezones. |
| Multipart routes | Preserve exact components with individual evidence and IDs. Descriptions remain semantic claims and cannot substitute for an endpoint. |
| Contact alternatives | Explicit purpose, membership, event scope and qualifications; ancillary contacts are not promoted to submission routes. |
| Disclosure and coverage prompts | Explicit consideration-policy and ancillary-contact guidance; completeness remains independently audited. |
| Admission and observations | Preserve existing caps; reject oversized inputs before dispatch; distinguish called and uncalled arms; reject statuses that contradict retained judgments. |

The owner suite and independent tests validate public behavior, including negative controls. The development replay keeps the original R6 inventories unchanged and reproduces all 18 historical assembly errors. Separately authored R7 examples assemble and fit the internal limits for both verifier request bodies. They retain their review reasons and are not improved real-model extraction results. Kentucky remains size-rejected, with no clipping or cap increase.

No provider calls, credential changes or production deployment were made. Improved extraction recall and comparative verifier quality remain unmeasured. A future fresh-sample run must use the new reviewed version and its own frozen protocol and execution authorization; the old R6 job is not silently reused.

Run the integrated offline checks from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 docs/research/state-rulemaking-benchmark/round7/development/replay.py
```

Implementation: [pipeline interface](pipeline/INTERFACE.md), [development results](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round7/development/results.json), [independent verification](verification/), and [primary verification receipt](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round7/primary-verification.json).
