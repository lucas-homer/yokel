# State notice normalization experiment results

The service-account runner completed its first real research job without interactive Keychain approval. The normalization experiment produced no usable records: one of four notices exceeded the frozen request-size limit, and three returned inventories that failed deterministic assembly. Neither Jev nor the stronger verifier was called. This round establishes an execution success and an extraction-to-schema failure; it supplies no comparative verifier accuracy result.

The four notices cover Kentucky, Ohio and New Hampshire, with 14 PDF pages. They fall short of the planned eight notices across at least six states. Sources, independent AI image-reference labels, code and outputs remain frozen. The reference is not human-adjudicated gold, and the sample cannot establish national accuracy.

| Outcome | Count |
| --- | ---: |
| Scheduled notices | 4 |
| Request-size review before extraction | 1 |
| Successful inventory responses | 3 |
| Assembly review after extraction | 3 |
| Normalized records produced | 0 |
| Jev calls / stronger verifier calls | 0 / 0 |
| Provider service errors | 0 |

Provider responses report **$0.1377235** total cost. A simple usage-rate calculation gives $0.142018; the conservative budget ledger charged $0.279674 against the $2 cap. Cache accounting explains why the simple rate estimate differs from the reported cost. These amounts are not invoice verified. No automatic retries or paid repair calls occurred. Cost per correct accepted record is undefined because no records were accepted.

The pipeline diagnosis reproduced 18 assembly errors. Four arise because complete printed dates begin with a weekday, which the current parser rejects. Six arise because the model joins address or meeting components, or uses a descriptive activity label, in a field that requires an exact contiguous source literal. Eight arise because alternative groups are restricted to submission routes, excluding hearing-access and ancillary-contact alternatives. All 102 evidence selectors resolved exactly, but exact quote resolution alone does not establish semantic correctness or completeness.

The next version should support weekday-prefixed complete dates under an explicit consistency rule; distinguish exact source components from normalized display values; and represent alternatives according to their function without promoting help contacts to submission routes. Keep strict evidence checks. Use these observed failures as development regressions, then freeze a new version and test a fresh sample. Do not repair these outputs and count them as successful results from this round. The Kentucky size rejection also needs an explicit future routing decision, rather than silent clipping.

The installed v2 runner is restricted to this fixed initial job and refuses to rerun an existing execution. Identity, two-key injection and live execution passed in the logged-in Mini agent context with Keychain interaction disabled. The current desktop lock state was not independently established, and logout/reboot operation remains untested. Future jobs require their own reviewed policy; this run does not enable arbitrary unattended commands.

Evidence: [completed run](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round6/execution/run/completed.json), [cost and integrity audit](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round6/execution/postrun-audit/audit.json), [failure diagnosis](execution/failure-analysis/ALL-THREE.md), [v2 validation](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round6/execution/service-account/primary-validation-v2.json), and [output freeze](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round6/execution/freeze-E.json). The [independent matching audit](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round6/protocol/postrun-audit/matching-audit.json) and [evaluation report](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round6/protocol/postrun-audit/evaluation-report.json) provide the semantic findings below.


The independent AI audit matched 82 of 120 frozen source units across the scheduled cohort. The size-rejected Kentucky notice accounts for 31 unextracted units. Among the three returned inventories, 82 of 89 units matched: Ohio notice one 27/28, Ohio notice two 25/28, and New Hampshire 30/33. These are clustered descriptive counts, not independent trials or population accuracy estimates. No inventory was complete under the frozen contract.

Of 96 enumerated semantic claims, 90 were judged correct, five incorrect and one unknown. The incorrect claims comprise two disclosure-classification errors and three unsupported claims of completeness; they are not five fabricated dates or contacts. The unknown claim concerns a mixed-level hearing-route grouping. Seven audited date literals and five email literals were correct. The audit separately identified an omitted Ohio office address and omitted New Hampshire local-number link and publisher office. Correct scalar values therefore do not establish complete participation records. Composite values can also preserve true components while violating the exact contiguous-literal transport contract.

All normalized records are absent, giving zero useful accepted records from four scheduled notices. Neither verifier has an observed quality result; zero unsafe acceptances with zero acceptances is not evidence of safety. The frozen evaluator was independently reproduced by the primary. Its fixed phrase “Eight-notice pilot” is stale for this four-notice run. Its missing-audit counts reflect absent artifacts (one inventory and four records), not unfinished matching of existing artifacts.

The operational audit retains four pre-verifier review outcomes. The evaluator requires record and payload hashes for an arm-level review, so its derived observation file correctly represents both uncalled verifier arms as `not_started`, preserving the original gate reasons and input hash in a separate adapter receipt. This changes no frozen evidence and introduces no provider-failure claim.
