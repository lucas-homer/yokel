# Exact assessment IDs in a live completeness check

The revised response contract worked on the retained Wisconsin notice: the provider returned exactly 70 keyed assessments, and the unchanged host checks accepted the structure. The model also identified a source-supported loss in the question-submission instruction. It still missed the two previously documented completeness gaps, so this result supports the response format but does not establish reliable completeness detection.

| Question | Result |
|---|---|
| Does the provider accept the compact keyed schema? | Yes in this call: HTTP 200, normal completion, 70 required IDs, no extras or validation errors. |
| Does the model detect repeal/recreation missing from operative record fields? | No. It incorrectly says the event description retains that context; the wording exists only in source/evidence. |
| Does it detect the missing full Zoom/phone alternative relationship? | No. It approves the phone subgroup and describes alternatives as represented. |
| Does it detect another source-supported issue? | Yes. The source says questions “should be submitted” to the contact; the question item reduces this to informational directory text. |
| Does it preserve the earlier modality concern? | No. It calls the comment-contact item’s unclear strength defensible, which does not satisfy the retained modality convention. |

The new response says `incomplete`, unlike the preceding response’s `complete`. That change alone is not a completeness success: the stated reason matters. The additional question-instruction finding is a new qualitative observation, not a retroactive change to the original source labels or their counts. Original URL glyph and accessibility-reference uncertainties remain intact.

The experiment changed only the frozen exact-ID response schema and its neutral system instruction. It reused the same source, normalized record, evidence table, model, reasoning setting, provider routing and 8,192-token output cap. Private audits and expected answers were excluded. The request was 38,432 UTF-8 bytes, or 39,456 including the existing allowance, within the unchanged 40,000 guard. There was one call and no retry, repair, clipping or fallback. This is one reused development case, not a held-out accuracy measurement or evidence that the schema change caused the semantic difference.

The response used 8,284 prompt tokens and 6,195 completion tokens, including 155 reasoning tokens. OpenRouter reported $0.0826585; the frozen-rate usage estimate is separately $0.078518. The ledger retains the larger $0.161920 reservation, bringing cumulative conservative debit to $0.858310718 of the authorized $2. These are response reporting and conservative accounting, not a verified invoice.

The existing signed-job runner completed without an observed 1Password or macOS approval prompt and without a rebuild. This establishes continuity for this job in the current session, not across a reboot or locked Keychain. Production eligibility and action readiness remain false.

The next useful experiment is a source-first completeness pass: enumerate source obligations before showing the normalized record, then match each obligation to an operative field or mark it missing or uncertain. Evidence quotes must remain supporting material, not substitutes for record assertions. Compare that approach with this direct verifier on the existing targeted cases before expanding the sample or choosing a more expensive model. This is a recommendation, not an additional paid run performed here.

Verification is complete: 13 owner tests and 409 independent pre-release checks passed; all 45 postrun operational checks passed. Independent semantic review covered all 70 assessment reasons and global sections and verified 79 evidence selectors. All 5,055 prior artifacts remain unchanged.

Evidence: [final verification](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round9-live-exact-id/final-verification.json), [raw execution freeze](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round9-live-exact-id/execution/freeze.json), [independent operational audit](review/postrun/FINAL.md), [semantic findings](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round9-live-exact-id/semantic-review/findings.json), and [assessment-by-assessment review](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round9-live-exact-id/semantic-review/explanation-review.json).
