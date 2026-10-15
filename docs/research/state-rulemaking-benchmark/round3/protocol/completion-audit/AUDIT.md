# Independent verifier completion audit

The reported pilot counts reproduce exactly from retained responses, frozen labels and the frozen evaluator. Each provider completed 15 calls; C007 was a deterministic no-call abstention in both arms. C016 was excluded from primary resolved-gate metrics before execution. All request bytes, response hashes, input copies, returned model identifiers and parsed results verify. No provider calls were made by this audit.

| Measure | Jev 1.13.0 | GPT 4.1 nano |
| --- | ---: | ---: |
| Challenge cases escalated including C007 | 9/10 | 3/10 |
| Provider-evaluated challenge cases escalated | 8/9 | 2/9 |
| Correct controls accepted | 3/4 | 4/4 |
| Resolved text-gate agreement including C007 | 13/15 | 8/15 |
| Resolved provider-only text-gate agreement | 12/14 | 7/14 |
| Source conflicts escalated | 2/2 | 2/2 |
| Source conflicts explicitly identified | 2/2 | 0/2 |

These are selected challenge gate outcomes, not field extraction accuracy or deployment error rates. A safe escalation can have an incorrect reason. Jev falsely marked source conflict in C005, C009 and C011. Nano escalated C014 and C015 while labeling conflict absent. Dimension accuracy and exact case records are in audit.json.

Both accepted C002, where supplied independent text has the correct email and the candidate has a missing letter. The shared deterministic checks compare candidate value with claim prose, but do not compare the proposed email exactly with the source email. Strengthening that code check is a concrete next experiment; do not claim the present baseline represents all useful deterministic validation. Both also accepted C003, a corrupted email faithfully present in the supplied parser text. That text-support result is expected, but it fails original-source fidelity. Jev accepted 5 nonambiguous cases, including 2 known source-incorrect cases. Nano accepted 12: 5 known incorrect, 2 unresolved by source and 1 source-correct but unsupported by its parser evidence, alongside 4 correct controls.

Jev returned 36,172 input and 2,611 output tokens. At the frozen input-token rate, its list-price equivalent is $0.001519224; no dollar charge was returned. Nano returned 22,756 prompt and 320 completion tokens, with $0.0024036 reported cost. Its upstream component is already included. Both are below the pilot's nominal budget, but these differing billing measures do not establish a combined cash invoice. Latencies are recorded request-wrapper observations, not a controlled throughput comparison.

## Ancillary freeze deviation

Eleven of twelve frozen entries are unchanged. My finalization of protocol/challenge-label-review.json occurred 0.744 seconds after the primary freeze and before the first request. Only its status changed and a final_resolution object was added. Reconstructing the prior bytes from those two changes reproduces the frozen SHA-256 exactly. Runtime input, model code, rubrics and evaluation labels are unchanged; the note records decisions already present in those frozen labels. The historical freeze and current note are preserved. freeze-deviation.json gives timestamps, hashes and the exact difference; reconstructed-frozen-review-note.json is explicitly a later reconstruction.

The execution bundle contains no evaluator labels, and raw payloads contain only source_text, candidate and evidence. The wrapper does not establish operating-system read isolation, so do not describe input-directory separation as an enforced filesystem sandbox. Reviewer-selected windows and authored candidates remain a developmental semantic challenge. Full routing, automatic retrieval, fresh evaluation and production acceptance remain unvalidated.
