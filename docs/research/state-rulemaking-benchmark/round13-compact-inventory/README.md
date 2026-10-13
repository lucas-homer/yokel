# Round 13: compact source inventory pilot

The compact representation completed successfully on the previously exposed Washington notice. It produced **91 inventory units in 5,728 completion tokens**, below the unchanged 8,192-token limit, with exact evidence reconstruction. Independent semantic review found useful source discovery and remaining uncertainty/normalization gaps. This is an engineering feasibility result, not production readiness or a representative accuracy estimate.

| Observation | R12 source-only attempt | R13 compact source-only attempt |
| --- | ---: | ---: |
| Completion status | Truncated; invalid JSON | Complete; validated |
| Completion tokens, including reasoning | 8,192 | 5,728 |
| Reported reasoning tokens | 63 | 87 |
| Output UTF-8 bytes | 30,283 unfinished | 17,827 complete |
| Validated inventory units | None | 91 |
| Provider-reported cost | $0.086531 | $0.066281 |

The two attempts used the same 3,876-byte notice, model and output cap, with different representations/prompts. R13 had 2,464 unused completion tokens, approximately 30% of the cap. One failed attempt followed by one outcome-exposed diagnostic cannot establish a causal effect, general performance, or a direct-versus-staged accuracy comparison.

## What changed

The host partitions the exact source into 37 deterministic line spans and places each stable evidence ID beside its full text in the request. The model emits compact named fields and selects those IDs instead of repeatedly generating quotations. Expansion restores exact quotations, Unicode offsets and occurrences. Source and table hashes, explicit uncertainty, conditions, prerequisites and separate relationship members are validated. Multiple atomic assertions can cite the same line; shared evidence does not merge contact purposes.

The full guarded request is 15,692 bytes, below the unchanged 40,000 limit. One signed, no-retry source-only request ran through the existing unattended service account without a new desktop authorization. No scope-classification, candidate-mapping or direct-verification call was made. The ledger retains the full $0.20 reservation, bringing conservative cumulative debit to **$1.705990718** and remaining headroom to **$0.294009282** within the existing $2 ceiling. Reported actual cost is $0.066281, not invoice-verified. Input usage again fits the observed cache-write premium; the nominal routing price cap is not treated as an all-in billing guarantee.

## Semantic findings

The independent reviewer assessed all 91 units and mapped them many-to-many against the frozen AI reference. Those bookkeeping counts are not accuracy denominators.

- **Useful preservation:** separate drafting, implementation and enforcement contact purposes; principal participation dates/routes; proposed adjudication distinguished from current public comments; 20/14-day triggers, qualifications, proof-of-service requirements and deleted/proposed wording. Discovering these source facts is not detecting errors in a candidate record—no candidate was mapped.
- **Deadline uncertainty needs work:** units 29 and 35 preserve dates but do not explicitly retain missing cutoff clocks/timezones or comment receipt/postmark semantics. No fabricated timestamp was observed; the gap is failure to represent those unknowns.
- **Amendment identity is only partly explicit:** unit 65 says the section amends a historical WSR filing. The affected WAC rule is linked through unit 4 but should be an explicit transition target.
- **Some facts remain bundled:** agency/notice/phase, date/clock, city/state and exemption components sometimes share a unit, making later field-level matching harder.
- **Some force labels are disputed:** advisory versus conditionally mandatory readings need a clearer contract. An AI reference's stronger label alone does not settle legal force.

The assessment also identified reference/input limits. A signature date is interpretive, and a reference label for newly inserted text depends on HTML underline markup absent from the model's plain-text input. That absent insertion label cannot fairly count as a model omission. All original labels and artifacts remain unchanged. Broad source-span coverage and valid JSON do not prove entailment or completeness.

## Verification and recommendation

13 protocol tests and 18 runtime tests passed and were reproduced by the primary. Independent reviews passed 197 protocol checks, 92 runtime checks and 89 operational checks. The published signature, all 8,704 release pins, 6,981 historical baseline files and completion/ledger receipts verify. The runtime ledger timing bug discovered during review was fixed before release: charges and outcome receipts are separate. All prior experiments remain immutable.

Keep the compact representation. The next refinement should be offline generic examples and checks for date-only deadline uncertainty, affected-rule versus historical-filing identity, independently lossy fact boundaries, and ambiguous directive strength. Preserve source markup where change status depends on it. A future semantic test should use a prospectively selected fresh notice; this case is now outcome-exposed. There is no demonstrated need here to increase the output cap or add chunking. No additional paid call is released by this report.

Evidence: [protocol](protocol/SPEC.md), [runtime](runtime/README.md), [frozen execution](execution/READY.json), [operational audit](review/postrun/REVIEW.md), [semantic assessment](evaluation/postrun/REPORT.md), [per-unit verdicts](evaluation/postrun/unit-verdicts.json).

The user requested GPT/OpenAI-only work. All R13 protocol, implementation and evaluations used OpenAI models. The advisory chat initially began under a Claude OpenRouter model before that correction; it was switched to Sol, and its final report documents the limited pre-change provenance under the historical `claude-design-review` directory. No further Claude route was used after the correction. No commits, pushes, PRs or production changes were made.
