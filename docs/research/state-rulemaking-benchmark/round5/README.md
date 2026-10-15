# Round 5 — native extraction and Jev verification

Completed October 7, 2026. Research only; no application, production ingestion, or deployment changes.

**The experiment completed, but the pipeline fails the progression gate.** Cheap native text contains the needed evidence in this sample; routing and qualification preservation are the main measured problems. Jev is inexpensive and reachable, but the current candidate-plus-verifier design cannot be trusted to approve normalized facts on its own.

Eight notices from six states, comprising 22 pages, produced 22 candidate rows and nine successful `jev-1.13.0` requests. Six rows were accepted in shadow mode, representing five distinct claims. Independent source review judged only two claims fully correct: South Dakota's written-comment date and submission email. Three accepted claims omitted applicable filing qualifications; one also had unresolved notice identity. All outputs remained not action-ready.

## Results and denominators

| Measure | Result |
| --- | ---: |
| Scheduled / completed inputs | 8 / 8 |
| Independently verified complete notices | 7 / 8 |
| States / physical pages | 6 / 22 |
| Candidate rows | 22 |
| Rows stopped before Jev | 13 |
| Successful Jev requests | 9 |
| Terminal accepted rows / distinct claims | 6 / 5 |
| Correct distinct accepted claims | 2 |
| Unsafe distinct accepted claims under the frozen audit contract | 3 / 5 |
| Complete-subset DATE recovery | 1 / 5 (20%) |
| Complete-subset EMAIL recovery | 1 / 6 (16.7%) |
| Complete-subset pooled recovery | 2 / 11 (18.2%) |
| Whole-cohort recovery rate | Undefined: one notice has unresolved scope |
| OCR calls / recorded POST retries | 0 / 0 |

The three unsafe claims are not three fabricated values. Their date/email literals and local roles are supported, but the normalized claims fail qualification preservation; the New Mexico claim additionally lacks verified whole-notice scope. The strict frozen contract counts these as failures. We did not weaken that contract after seeing results.

The whole cohort has 14 known eligible facts (seven DATE, seven EMAIL), but not an established complete denominator. The complete seven-notice subset is descriptive and cannot replace the prespecified eight-notice cohort. The full-cohort 25% gate cannot be evaluated as passed; the descriptive subset also falls below it. The zero-unsafe-acceptance gate fails, and the eight-complete-notice requirement is unmet. No production or larger-study readiness claim follows.

## Where the facts were lost

In the seven complete notices, all 11 eligible local facts and their qualification text are faithfully present in native extraction, and all 11 have matching value/role/scope candidates. A matching candidate does not imply that all its qualifications were carried forward.

| Outcome for these 11 facts | DATE | EMAIL | Total |
| --- | ---: | ---: | ---: |
| Deterministic block before Jev | 2 | 4 | 6 |
| Completed verifier nonacceptance | 1 | 0 | 1 |
| Accepted by runtime, rejected by source audit | 1 | 1 | 2 |
| Correct audited acceptance | 1 | 1 | 2 |

Across all 14 known local facts, native text preserves their local evidence. The uncertain New Mexico notice contributes a separate response-date discovery omission: a line break in “no later than” defeats the proposer. Its other two candidate mappings retain unresolved scope, so exact whole-cohort candidate recall remains undefined. These are field-level audits, not a claim of perfect whole-document parsing or recall of every possible rulemaking fact. The frozen stage vocabulary lacked an unsafe-acceptance category; those records retain `loss_stage=unmeasured` with a separate explicit `terminal_source_audit_rejection` attribution, rather than altering the frozen taxonomy.

## Concrete failures

| Source | Observation | Implication |
| --- | --- | --- |
| Kentucky | Hearing-intent timing blocks an independently stated written-comment date. Two valid alternative email routes exceed the conservative request limit. | Attach conditions to the event they qualify. Multiple valid routes need a set representation; their actual observed block here was size, not competition. |
| Ohio, August notice | A wrapped body sentence beginning “proposed rulemaking” is treated as a second notice heading. | Notice boundaries need structural evidence, not a line-start phrase alone. |
| Ohio, October notice | Candidate misses later close-of-business and discretionary late-comment qualifications. Jev rejects preservation. It also incorrectly calls a hearing-registration email a matched submission role, though another failed dimension prevents acceptance. | Some verifier rejections are useful, but a favorable role classification alone is insufficient. |
| Michigan | Date and email are accepted with empty conditions, omitting the instruction to refer to ADM File No. 2021-29. Email also omits the public-posting statement. Jev says conditions are preserved. | A verifier evaluating proposed facts can miss instructions that the proposer omitted. Correct literal values are insufficient. |
| New Mexico PRC | Initial and response windows are separate phases. Posting latency causes a false date block; the response date is omitted. Accepted email loses PDF-format and docket-reference instructions. Heading and footer identify different dockets. | Preserve phase, format, identity and cross-page discrepancies separately. A classifier cannot resolve publisher inconsistency merely by returning “no conflict.” |
| New Mexico cannabis | Hearing-bound date correctly stays unresolved; explicit email cannot reach Jev because of request size. | Timing uncertainty need not erase the independently supported route, but route qualifications must accompany it. |
| Connecticut | Extension language creates real date uncertainty. Global lifecycle blocking also stops the separately stated email. | Uncertainty should attach to the affected fact and remain visible to downstream users. |
| South Dakota | Date and email pass independent review. Duplicate email mentions represent one fact. | A simple native path works for this notice, but it does not establish national reliability. |

## Costs and execution integrity

Nine requests used 26,638 reported input tokens and 1,547 output tokens. At the pinned rate, **usage-based estimated API cost was $0.001118796**. Conservative reserved budget charge was **$0.005140464**, against a $0.10 cap. Neither is a verified invoice. The estimated API cost per independently correct distinct field was $0.000559398, charging all nine requests to the two correct fields. These figures exclude source discovery, labeling, review, orchestration and engineering.

Summed retained POST latency was 1.9372 seconds; mean 0.2152 seconds. This excludes authentication and the much longer end-to-end research workflow. An initial 1Password authorization attempt timed out before run creation; the retriggered authorization completed the run.

Mechanical preflight passed 1,826 checks. Independent execution audit passed 2,130 checks, reconciling requests, raw responses, model IDs, usage, terminal outcomes and freeze bindings. All 104 frozen execution files are unchanged. The ledger records nine single-attempt HTTP 200 operations, zero OCR, no stops and no provider/model fallback. Provider-internal transport behavior is not independently observable.

## What this changes in the solution design

The evidence supports keeping a cheap native path, but not treating a cheap classifier as an acceptance authority. This round does not compare parser products or establish that one expensive tool would fix the failures. No OCR was used, and all measured local evidence survived native extraction.

The next bounded development step should be a **source-grounded representation of participation events and requirements**:

1. Preserve source identity, document/page/span hashes and unresolved identity conflicts independently of model judgments.
2. Represent initial comments, response comments, hearings and hearing-intent deadlines as different events. Bind dates and relative/conditional timing to those events.
3. Represent submission routes as alternatives, with exact addresses, required references, formats and applicable instructions. Keep publication disclosures distinct from deadline conditions without dropping either.
4. Inventory requirements from the source before approving candidates. Verify both directions: every proposed claim has support, and every relevant source requirement is represented or explicitly unresolved. A candidate-only verifier cannot reliably detect everything never proposed.
5. Keep deterministic literal/calendar/provenance checks. Route semantic ambiguity to deeper extraction or independent verification; route corrupt/missing text or difficult layout to document/OCR tools. A genuinely inconsistent source needs review, not confident repair.
6. Handle request limits explicitly. Evaluate supported token accounting or complete, provenance-preserving document decomposition before sending oversize inputs. Do not silently clip context or choose only the decisive-looking paragraph.

Jev remains a candidate for bounded classifications and triage, with calibrated tests for each task. Its current four-question acceptance role failed this sample. A future comparison could hold a richer candidate bundle fixed and compare Jev with a stronger independent verifier; separately test source requirement discovery so neither verifier gets credit for an incomplete candidate set. These are recommendations, not unperformed results or authorization for another paid experiment.

Use this round's failures as development regressions, then freeze a new design and test on fresh notices. Do not retune and advertise accuracy on these same eight. Continue reporting DATE and EMAIL separately, unsafe acceptance, qualified-fact coverage, source uncertainty, and total operating cost. Production remains federal-only.

## Methods and limitations

Implementation, prompts, routing rules and selection protocol were frozen before collection. Original source files were frozen before independent image-only labeling; all 22 pages were viewed. Labels were frozen before native proposals or live outputs. The unchanged round-four evaluator scored terminal outcomes with a new independent acceptance audit. Separate visible Codex child tasks handled pipeline, runtime, collection and review; the primary executed live calls and integrated findings.

This is a small, purposive diagnostic set, not representative accuracy across 50 states. It contains historical notices and a Michigan judicial-rule proposal; it does not claim these comment periods are currently open. Selection excludes unusable native text and oversize sources, so it measures neither scan-only performance nor discovery coverage, currentness or ongoing change tracking. No fresh Firecrawl/LlamaParse/Mistral comparison occurred in this round.

Disclosed collection deviations remain in the artifacts: Q01–Q03 omitted the planned PDF search filter, with an append-only correction; one initially retained oversized Kentucky notice was removed under the preexisting size rule before source/label/output freeze, with its files and correction preserved. Collection stopped at Q12 candidate 3 after 36 candidate decisions. Quota/state-feasibility clarifications are recorded. One PRC document failed independent completeness review and was retained rather than replaced.

Freeze A accidentally included the initially empty, append-authorized access ledger. Exactly 181 of 182 files retain their original hashes; the sole ledger difference is documented in a separate exception receipt, and completed ledger bytes are pinned by Freeze S. No code/prompt change is concealed by that exception. Freeze S (230 files), Freeze B (seven files) and Freeze E (104 files) match exactly. Hashes and chronology support the recorded procedure, but do not prove process isolation.

## Evidence

- [Frozen protocol](protocol/PROTOCOL.md)
- [Source collection and retained originals](https://github.com/lucas-homer/yokel/tree/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round5/sources)
- [Image-only source labels and rationale](protocol/source-labels/README.md)
- [Terminal evaluation](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round5/protocol/postrun-audit/evaluation-report.json)
- [Complete-notice subset](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round5/protocol/postrun-audit/complete-notice-subset.json)
- [Claim-by-claim acceptance audit](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round5/protocol/postrun-audit/audits.json)
- [Source-to-output stage audit](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round5/protocol/postrun-audit/stage-audit.json)
- [Routing diagnosis and exact source spans](execution/routing-diagnosis/README.md)
- [Execution integrity and cost audit](execution/postrun-integrity/REPORT.md)
- [Frozen live outputs](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round5/execution/run/completed.json)
