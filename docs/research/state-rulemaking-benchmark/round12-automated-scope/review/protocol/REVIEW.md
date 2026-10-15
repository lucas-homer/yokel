# Round 12 initial generic protocol review

**TARGETED BLOCKER — do not freeze this protocol for implementation or provider dispatch.** The discovery, isolation and scope contracts are acceptable in principle, but the preregistered full C object transport makes B predictably exceed the fixed request guard at modest inventory sizes. Primary has commissioned a codec revision; this report is historical evidence against the initial frozen protocol, not a review of that revision.

Reviewed generic READY SHA256: `7ea413bff36444990db5b53a8942a6e24cf148c64bf80d1b8f710500fd63fb57`. Source binding SHA256: `9dbccc70a7687eebb148b80c40e0c46264509052c39c7df29a58687510fe2940`. Candidate file SHA256: `934c3c999c203f44756416b103519e36d73a9b807b8ca0a104a67f1820b9c1a7`. Source SHA256: `7cf8d7a924724d7fc80c80e5b4337c2114585668feef5edb14f49a75aec4d437`.

## Blocking finding: full scope transport

SPEC requires complete unchanged C JSON, with all reasons and quotations, in B alongside the complete candidate and losslessly encoded A. On the actual frozen 3,876-byte source and candidate, the complete operative projection is 11,462 canonical bytes. Independent request assembly uses canonical UTF-8 JSON, nested user-message JSON escaping, complete instantiated response schemas, original prompts/settings and the 1,024-byte safety allowance. It uses the existing request envelope and descriptive response-format names; the final runtime must measure its exact bodies independently.

| Probe | Units | C guarded bytes | B guarded bytes | B fits 40,000 |
|---|---:|---:|---:|---|
| Modest | 24 | 16,324 | 37,819 | yes |
| Modest | 32 | 18,268 | 42,551 | no |
| Modest | 40 | 20,212 | 47,289 | no |
| Modest | 46 | 21,670 | 50,851 | no |
| Modest | 48 | 22,156 | 52,033 | no |
| Modest | 64 | 26,044 | 61,481 | no |

Modest means 90-character assertion, 30-character applicability, 100-character scope reason, one 94-character exact source quote, no dependencies and no uncertainty explanation. Earlier round10 actually produced 46 units, with assertion median 90, applicability mean 29.9 and quote median 94. These prior dimensions motivate a sensitivity probe; they do not predict round12 unit count or C verbosity. All units in the probe use required scope; this changes byte lengths slightly compared with other categories and does not assert that real units have that scope.

Even the concise profile (70/20/50/60 characters respectively) overflows at 40 units (42,699 bytes) and 48 units (46,523 bytes). A and D fixed requests fit at 10,205 and 28,441 guarded bytes. No guard increase, semantic deletion, candidate repair, post-spend codec switch or favorable truncation is acceptable.

**Required resolution:** prospectively define and review bounded lossless C transport (including exact source evidence selectors, every ID, category, basis, reason and full-output hash), then repeat complete serialized-size sensitivity on the frozen candidate and show a plausible complete-case envelope. Preserve raw C and require exact round-trip canonical equality. Do not insist that all maximal 64-unit schema combinations fit; retain the actual per-call stop gate. The runtime must still stop before B if actual A/C do not fit. This review does not prescribe an unmeasured codec as sufficient.

Synthetic filler strings and source slices are dimensional probes only: not atomic claims, scope judgments, model truth, source-completeness evidence or a runnable verifier. No independent reference/gold contents were read.

## Contracts reviewed without another blocker

- D enumerates its own source assertions, including claims absent from the candidate; the schedule is an array of source units with shared A/C/B definitions. Missing mappings permit zero pointers. It is not constrained to candidate IDs or A IDs.
- C's exact input allowlist is source and immutable A only. It has neither candidate nor assessment access. C and B schedules must be instantiated from every frozen A ID, without extras, deletion, mutation or discovery repair. D output is not shared with A/C/B. This is a contract-level conclusion; builder and process isolation remain to be tested.
- Classification uses actor, proceeding and function. Proposed regulated/adjudicatory duties can be background even when their kind is timing or instruction. Current notice comment, hearing and assistance obligations remain required. All kinds permit all categories structurally; the category/basis bijection remains mandatory. Misclassification of natural language therefore needs independent semantic review, not a host kind rule.
- The four current-versus-future controls are sensible synthetic semantic controls. They do not demonstrate model classification. The other runtime fixtures are explicitly specified but unexecuted. Primary source-informed design exposure is disclosed; neither this review nor the protocol establishes blind design.
- Raw known missing/mismatched loss survives effective uncertainty. Unresolved scope/required recovery blocks completeness. The separate reverse audit binds source, original candidate and full operative projection and covers unsupported additions. No production/action readiness or whole-source completeness follows from inventoried coverage.
- Four calls maximum, order D/A/C/B, same model/settings, OpenAI-only routing, no fallback, price caps 2/10, 8,192 output-token cap, no retry/repair/clipping, actual request guards, dependent-stage stops and retained failed-attempt accounting are explicit. Budget arithmetic is correct: 1,182,150,718 prior + 647,680,000 four-call reserve = 1,829,830,718 nanodollars, leaving 170,169,282 under the 2,000,000,000 ceiling. Each actual admission must still recalculate debit.
- Source/archive and candidate pins verified. Parser definitions independently reproduced archived body text and five anchors without executing source-write statements; the full body and browser model source have equal whitespace-token sequences. This verifies the local archive relationship, not a new network fetch or legal interpretation.

## Small corrections and remaining release gates

The evaluation sentence “four calls versus one” should say three-stage source-first arm versus one-stage direct arm, four calls total. This is a reporting correction, not a second implementation blocker.

Source READY refers to FRAME.json without pinning its bytes. This review pins the frame in its input closure and verifies ascending unique selection and first eligible candidate. Carry that pin into the final immutable release dependency closure; do not silently treat the source READY hash as a frame-content pin.

Runtime review still needs strict JSON/ref/schema rejection, all mutation and isolation tests, exact inventory/C round trips, full candidate pointer enumeration and original/projection witnesses, stale audit rejection, budget accounting, dependent-stage stop tests and actual body guards. No runtime, provider compatibility, dispatch or semantic outcome is approved here.

## Evidence

`checks.py` produced `check-results.json`: **99/99 independent checks passed**, including the reproduced **54/54 author static checks**. Passing checks establish facts and reproduce the size blocker; they are not an overall protocol approval. Input hashes were checked again at the end of the run. Only review/protocol artifacts were written. No provider calls, credentials, signer/runner actions or changes to owner/prior/signed artifacts occurred. All measured profiles and input hashes are preserved in the result.
