# Post-run adapter audit

The favorable-label pattern is present in the provider's raw outputs. No local adapter/interface defect explains Nano's broad acceptance. All 30 response bodies replay exactly into stored results, all 15 request pairs contain byte-identical serialized semantic state, and the same explicit four-axis rubrics were delivered. This establishes a failure of the tested model/prompt/structured-output configuration on these cases; it does not isolate a model-weights cause or establish a general ranking of providers.

Audit scope: read-only investigation of the existing live artifacts, followed by this sole new report. No provider calls, credential access, code/contract changes, score edits, response repair, or threshold tuning. Checked against the frozen staged engine, not a revised implementation. Existing artifacts were fingerprinted before and after writing; all existing round-three files remained unchanged.

## Boundary checks

| Check | Result |
| --- | --- |
| Scheduled input records identical between arms and staged runtime | 16/16 |
| Deterministic preblock identical, no provider request | C007, candidate.value null |
| Actual saved request equals frozen build_request output | 30/30 |
| Provider semantic state identical, full source and actual structured values preserved | 15/15 pairs |
| Rubrics and scoped-target policy identical in meaning and content | 15/15 pairs |
| Exact request SHA matches durable intent | 30/30 |
| Exact response SHA matches status metadata | 30/30 |
| Frozen parse_response reproduces complete stored result after case/field provenance | 30/30 |
| HTTP completion / valid usage | 30/30, HTTP 200 |
| Returned Jev model | jev-1.13.0, 15/15 |
| Returned OpenRouter model/provider | openai/gpt-4.1-nano / OpenAI, 15/15 |
| Nano finish reason | stop, 15/15 |
| Nano completion tokens | 21–25, versus 512 cap |
| Nano input tokens | 776–2920 |
| Jev input/output tokens | 1611–3925 / 171–180 |

The runtime whitelist permits only source_text, candidate, evidence and optional metadata; model state excludes case IDs and metadata. Evaluator files are not opened by the runtime. Every retained request reconstructs from its frozen runtime case with no reviewer labels, parser scores, hidden fallback text, or gold spans added. This is evidence of no local label leakage; historical training-data contamination cannot be assessed from saved requests.

Nano's schema permits all three labels on each axis. There are no default labels or response-healing plugins, no automatic retry or model fallback, no local label replacement, and no manufactured probabilities. The raw JSON content contains exactly the labels subsequently evaluated. C014 and C015 use non-favorable schema labels, demonstrating that the schema did not force the favorable tuple. Native model confidence is preserved separately for Jev and does not alter the frozen categorical gate. Nano supplies no probability distribution.

The requests use different native interfaces: Jev gets four independent Choice questions, while Nano gets one structured completion containing four answers. The same state/rubrics do not make those execution interfaces identical. The audit reaches the retained API request/response boundary; it cannot independently prove the provider's internal prompt forwarding or decoder behavior.

## Concrete failure evidence

**C002 exact email typo.** The actual supplied source/evidence says `DNRAdministrativeRulesComments@wisconsin.gov`; candidate.value and claim both say `DNRAministrativeRulesComments@wisconsin.gov`, missing the d after A. Both strings are visible in each saved request. Both providers returned all four favorable labels. Jev's raw support Choice is supported at probability 0.95, confidence 0.93, with insufficient 0.03 and contradicted 0.02. Nano's raw content is `{"condition":"preserved","conflict":"absent","role":"matched","support":"supported"}`. The adapter copied those judgments faithfully.

This also exposes a **known deterministic coverage limitation**, separate from response parsing: the exact-quote check verifies the quoted source, while value_claim_consistency checks whether the candidate value appears in the candidate claim. The typo appears consistently in both candidate fields, so it passes that consistency check. The code does not enforce exact source correspondence for routing strings. Thus this experiment delegated the source/value spelling comparison to the models, and both missed it. A passing citation check was never proof of the candidate destination. C003 is different: its supplied source itself contains the corrupted email, so text-only agreement is an explicitly predeclared source-fidelity blind spot.

**C009 actual versus anticipated.** The source explicitly says the September 8 date is anticipated and `NOT the effective date`. The candidate claims actual effectiveness. Nano nevertheless returns all favorable labels; Jev returns contradicted/mismatched/omitted_or_changed/present. The contradiction is present in the saved source, not lost by the adapter.

**C011 conditional hearing.** Source text repeatedly conditions the hearing on at least 25 requests and explicitly describes cancellation below that count. The candidate says it will occur regardless of the number of requests and has empty conditions. Nano returns all favorable labels; Jev rejects. The source was retained in full in both arms.

**C006, C008 and C013 role/precision.** Nano accepts an official filing-stamp claim from a submit-date field and an empty official-stamp region; a closing-date claim from an ambiguous hearing-or-comment-period label; and an actual OAL submission from an anticipated on-or-after date. The actual structured roles/values and source wording were delivered unchanged. Jev produces non-favorable judgments on all three.

**C005 malformed range.** Nano accepts `July 2223, 2026` although the source clearly says July 22–23 with a separate possible extension. There is no text normalization or downstream repair creating that result.

**C014 and C015 conflict detection.** Nano does reject these two cases through support/condition judgments, but labels conflict absent in both despite visible competing years/day bases. These are gate catches, not exact per-dimension correctness. Jev marks conflict present in both. Conversely Jev sometimes reports conflict present for a false candidate even when distinct source events do not themselves conflict; do not equate 8/9 gate detection with 8/9 perfect four-axis labels.

**C004 control.** Jev's non-acceptance comes directly from condition=omitted_or_changed, while the frozen field scope treats the announced initial dates separately from the possible extension. This is a model/rubric scope error at the condition axis, not an interface error or a newly revised control label.

## Raw label accounting

Label order below is support / role / condition / conflict. This is a transcription of retained outputs, not rescoring or a changed decision rule.

| Case | Jev raw-derived labels | Nano raw labels |
| --- | --- | --- |
| C001 | supported/matched/preserved/absent | supported/matched/preserved/absent |
| C002 | supported/matched/preserved/absent | supported/matched/preserved/absent |
| C003 | supported/matched/preserved/absent | supported/matched/preserved/absent |
| C004 | supported/matched/omitted_or_changed/absent | supported/matched/preserved/absent |
| C005 | contradicted/matched/omitted_or_changed/present | supported/matched/preserved/absent |
| C006 | insufficient/mismatched/omitted_or_changed/insufficient | supported/matched/preserved/absent |
| C008 | insufficient/insufficient/omitted_or_changed/insufficient | supported/matched/preserved/absent |
| C009 | contradicted/mismatched/omitted_or_changed/present | supported/matched/preserved/absent |
| C010 | supported/matched/preserved/absent | supported/matched/preserved/absent |
| C011 | contradicted/mismatched/omitted_or_changed/present | supported/matched/preserved/absent |
| C012 | supported/matched/preserved/absent | supported/matched/preserved/absent |
| C013 | insufficient/mismatched/omitted_or_changed/insufficient | supported/matched/preserved/absent |
| C014 | supported/matched/omitted_or_changed/present | contradicted/matched/omitted_or_changed/absent |
| C015 | insufficient/matched/omitted_or_changed/present | insufficient/matched/insufficient/absent |
| C016 | supported/matched/preserved/absent | supported/matched/preserved/absent |

Jev returned the all-favorable tuple 6/15 times; Nano 13/15. These include C016, excluded from primary resolved-gate metrics, and C003, the declared source-fidelity blind spot. C007 was a deterministic preblock with no provider response. Frozen primary summaries remain: model-eligible detectable errors caught Jev 8/9 versus Nano 2/9; correct controls accepted Jev 3/4 versus Nano 4/4. Including C007 gives 9/10 versus 3/10 composite detections. No scores were changed by this audit.

## Provenance discrepancy and limits

11/12 frozen paths match their recorded SHA. The sole mismatch is `protocol/challenge-label-review.json`: frozen `b26055f47c2ba9c487ad839c66528d1a97ce3ffb9554623ea4925ab9ce56d27a` versus current `6cd05c984f003f61c8a590b32f9b5b084fa9f8ba397f1efea02109d5be6c3dc6`. Its current final_resolution records timestamp 2026-10-07T04:49:02.385199+00:00, just after the freeze timestamp 2026-10-07T04:49:01.641271+00:00, and before the first durable POST intent 2026-10-07T04:49:16.232740+00:00. The final_resolution references evaluator SHA `3d334a924bff14e54964de6e976f0ab0905a12ba08dbdecbe2034d528f1972ad`, which matches the frozen and current evaluator file. The runtime inputs, staged engine, evaluator, challenge contract, source dependencies and execution wrappers still match freeze. The review-note hash discrepancy should be retained as a provenance annotation; it does not explain Nano's responses or establish an output-driven label change. The prior version's exact content is unavailable in the freeze record, so this audit cannot reconstruct that note's complete diff.

Favorable labels are the first enum entries in Nano's schema. Ordering/structured-decoder anchoring is a plausible untested explanation, not an established cause; the present audit cannot distinguish it from the model's semantic weakness, prompt formulation, or joint-answer behavior. No reordered prompt or additional provider call was made. The data therefore supports rejecting this tested Nano configuration as an adequate verifier for these failure modes, while preserving uncertainty about causal mechanisms and generalization. Jev's exact-string miss and control rejection also remain material.

Audit completed using the systematic-debugging investigation workflow. All existing artifacts retained their pre-audit SHA-256 values; frozen outputs and scores are unchanged.
