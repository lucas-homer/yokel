# Completed-run routing diagnosis

The frozen runtime reached zero Jev calls because every proposed candidate hit a deterministic hard condition gate. This run therefore tests extraction/routing and OCR acquisition, not Jev's ability to verify these notices. No changes or new provider calls were made for this diagnosis.

Observed final artifact: `execution/run/completed.json` (SHA-256 in `facts.json`), all 12 scheduled documents terminal. The retained input scopes are five full_notice, five unknown and two slice. There are 16 native plus seven fallback candidate rows; all 23 are review/not_attempted, and all 23 have `condition_scope_requires_semantic_verification` in their actual deterministic blockers. Five OCR operations acquired 14 pages. Seven other notices routed to source_review. These are row counts, not distinct source facts or source-verified recall.

The dispatch explanation is explicit in `runtime/run_pipeline.py`: `SOFT_ISSUES` includes only submission-role and written-comment-role uncertainty. Condition and competing-temporal-role signals are HARD_ISSUES; `local_gate` returns before constructing a provider operation when any hard issue is present. The proposer’s original broader soft-issue list does not control this live gate. Runtime reservations/accounted usage remain in `facts.json`; no inference about independently billed actual cost is made here.

## Exact examples from acquired text

`evidence.json` records unchanged UTF-8 artifact hashes, zero-based half-open Unicode spans and exact quotes. These are parser-text observations; original PDFs were not visually audited and independent source labels were not read.

| Example | Exact native text span | Observed mechanism |
| --- | --- | --- |
| Arkansas, doc-7035335ec6ae | `[193,216)` “following proposed rule”; `[1500,1546)` “following email address: ORP@dhs.arkansas.gov.” | Generic QUALIFIER matches `following` used to point to text/addresses. Entire qualifying paragraphs become candidate conditions, which the runtime hard-blocks. |
| Arkansas explicit close | `[1547,1620)` “All public comments … no later than April 12, 2026.” | Date and email are extracted correctly as literals from this paragraph. Both native and OCR proposals still have the same hard condition issue. This is not proof of original-source correctness or unconditional legal applicability. |
| South Carolina, doc-6de1104bdc54 | `[5041,5104)` “The language in the regulation was superseded by state statute.” | LIFECYCLE scans the whole notice. A statement about regulation text adds lifecycle_scope_unresolved to a submission-email candidate in a different paragraph. It does not explicitly state that the participation window was superseded. |
| South Carolina date | `[2941,2983)` “on or before 5:00 PM on February 23, 2026.” | The absolute date is visible, but CLOSE lacks `before`. No DATE proposal is generated in either channel. The clock must remain raw; this diagnosis does not calculate a cutoff/timezone. |
| New Hampshire, doc-cc8a5c237cc2 | `[5618,5778)` form “Deadline for submission of materials in writing … Thursday, November 12, 2026”; `[5796,5830)` “X Email piera.y.siegert@agr.nh.gov” | Comment-only lexical role matching does not connect the form header, separate date paragraph and selected email option. Two repeated email strings are proposed with role-unverified; no DATE proposal appears after OCR either. Associating these form fields with the supported comment role still needs source audit. |
| Numeric date, doc-27f924e9b9d3 | See `numeric-date-unsupported` in evidence.json | `7/16/2021` is found but normalized to null under the frozen slash-date policy. Its retained scope is also not full_notice. This is a grammar/scope stop, not evidence of OCR failure. |

Exact source locations: `sources/documents/<document_id>/native.txt`; proposal and blocking records: `execution/run/documents/<document_id>/{native,fallback}/pipeline-record.json`, `results.json` and per-case JSON. For Arkansas the native date blocker is directly recorded in `native/case-224365d5ae776867.json`; its sole blocker is condition_scope_requires_semantic_verification. `facts.json` retains every candidate case ID and actual deterministic blocker list.

## Genuine conditions and role uncertainty must remain visible

Hawaii doc-03fab2becee5 contains real relative testimony timing at `[12885,12933)` (“at least twenty-four hours prior to the hearing”) and a participation-extension possibility at `[13875,14005)`. Those are genuine supported-scope limitations, not merely incidental word matches. The same notice also contains subject-matter “withdrawal of signatures” at `[6727,6775)`, and the whole-text rule/chapter detector counts authority Chapter 91 and wrapped Chapter 3-171 alongside proposed rules. Removing every lifecycle/condition/multi-rule signal would lose material participation evidence and would not establish a single unambiguous participation window.

South Carolina’s hearing-cancellation condition at `[2561,2673)` is also real acquired evidence, even though it is not automatically a condition on the separate written-comment receipt clause. Role-specific association is the unresolved task.

Idaho doc-09c6b865024f has `[833,893)` “To participate, responses must be received by July 31, 2023.” The role is negotiated-rulemaking participation response; treating it as written-comment close automatically would broaden this experiment’s scope. Native and OCR text both describe communication “by email” but contain no extracted literal email address. A missing field candidate does not prove source absence, and OCR must not invent an address.

## What the OCR route could not repair in this run

`ocr-outcomes.json` records all five acquisition decisions and paired channels. Every native/fallback candidate-value multiset and route list is identical: Hawaii 2→2, Idaho 0→0, South Carolina 1→1, Arkansas 2→2, New Hampshire 2→2. Candidate issues are also unchanged for those records. Thus no observed candidate-recovery or dispatch improvement followed acquisition in these cases; this is not a general comparison of parser fidelity.

None of the five OCR decisions was triggered by the frozen low-text/image-sparse thresholds. Embedded nonspace counts ranged from 962 to 2,749 per page; one New Hampshire page had an image object but its text count was 1,619, above the image-sparse threshold. Reasons were missing candidate signals, structural review or native_candidate_not_text_supported—the latter includes deterministic not_attempted review, not a failed semantic model judgment.

Faithful OCR cannot resolve policy stops that persist in faithful text: a deictic word classified as a hard condition, unsupported relative timing, a non-comment participation role, an absent literal destination, or a lifecycle/scope association requiring reasoning. It can sometimes change formatting/paragraph boundaries; that could change heuristics, but was not observed here and must not be mistaken for semantic repair. Scope slice/unknown remains a source-boundary problem; the router correctly did not acquire OCR for those seven inputs.

Six candidate rows additionally hit case_overlimit. Full-notice input plus copied qualifying paragraphs can exceed claim/condition limits even when source text fits its own limit. Removing one issue would not make candidates with additional hard blockers reachable; no counterfactual pass count is claimed.

## Next bounded experiment — proposed, not tested

Use this completed set only as development evidence now. Freeze a separate native-only routing experiment before any new evaluation. First require an offline reachability report: candidate counts, exact hard blocker categories, and whether a proposed OCR acquisition has a mechanically plausible parser deficit it could fix. Keep source scope unknown/slice, ambiguous/relative dates, unsupported clocks/timezones and true participation lifecycle conflicts as review states.

Test a narrow explicit-date lane: generic `on or before` close language; form-header/date association as a proposal rather than accepted truth; and distinguishing demonstrative “following [rule/address]” or regulation-subject lifecycle words from participation conditions. Retain the full notice for verification and all source spans. Positive controls should be paired with real hearing-request conditions, relative deadlines, actual deadline extensions, incidental contact emails, neighboring windows and unsupported numeric dates. Scope/condition changes must pass independent review; do not simply turn every hard condition into a soft model override.

Measure native source-candidate recall and the fraction of eligible proposals reaching semantic verification before buying OCR. Independently source-audit all eventual terminal acceptance. A later fresh set is needed to evaluate revised rules; this report neither implements them nor predicts their safety/coverage. No frozen proposer, router, evaluator, labels or final run artifacts were edited.
