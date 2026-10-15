# Offline contract and request-size results

Completed and independently reviewed. Twelve owner tests pass, including the primary rerun; the reviewer passed nineteen tests total, including seven independent controls. Ten complete paired-request fixtures were measured. No provider calls, credentials, native builds or live jobs were used. All 1,147 original Round 8 and cap-probe files remain unchanged.

## Candidate changes

The inventory prompt now states the existing timing dependency rules explicitly. Non-calendar wording such as “as soon as possible” retains raw text and a null date value; the model must not invent a deadline or relationship. Facts only quoted as evidence do not establish structured coverage, and email addresses do not establish expanded personal names.

Independent review corrected an important distinction: faithfully representing source ambiguity does not itself make inventory coverage incomplete. The ambiguity remains explicit and still triggers the applicable uncertainty/review gates. Schema, assembler, model/provider settings, source payload and verifier request content remain unchanged.

The revised inventory request has an internal estimate of 22,141, below its unchanged 35,000 guard. The added instructions increase that estimate by 2,777 and its nominal reservation by $0.005554. These estimates are serialized UTF-8 bytes plus a 1,024 allowance, not measured model tokens.

## Full verifier-request measurements

| Case | Current stronger guard: 35,000 | Proposed stronger guard: 40,000 | Other constraint |
| --- | --- | --- | --- |
| Seven small authored fixtures | Both arms fit | Both arms fit | Includes timing, routes, disclosures, accessibility and represented ambiguity |
| Two Wisconsin diagnostic copies | Stronger fails | Both arms fit | Stronger estimates 38,321–38,347; Jev state headroom only 987–1,011 |
| Oversized authored fixture | Fails | Fails | Stronger estimate 50,180 and Jev state estimate 45,086 |

The guard comparison changes no request bytes or evidence. Jev's 64,000 total/32,000 state limits and stronger's 4,096 output allowance remain unchanged. Both requests must pass before either could be dispatched. Exact boundary and just-over-boundary checks pass. The original paid malformed inventory still fails; the diagnostic copies are not repaired observed results or semantic successes.

## Decision and limitations

The offline candidate is ready to form the basis of a separately bound, limited live experiment. A 40,000 stronger-only guard would clear the measured Wisconsin diagnostic requests, but it is not a general sizing solution. New generation could still fail structure, exceed either request guard, or omit/misrepresent source facts. A larger stress case already demonstrates this limitation.

No improvement in model instruction-following, completeness, accuracy or unseen-source performance has been measured. Structural validity and a model's completeness claim still require independent semantic verification. No further paid experiment was performed or prepared here.

Any future one-inventory/two-verifier candidate must carry the existing $0.261774 conservative debit. Under the proposed guard, its maximum new nominal reservation is $0.316528, for $0.578302 combined within the shared $2 guard. These are planning/accounting limits, not invoices.

Evidence: [prompt additions](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round8-offline-contract/prompt-delta.txt), [full measurements](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round8-offline-contract/REPORT.json), [independent review](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round8-offline-contract/review/REVIEW.json), [resolved review finding](review/FINDINGS.md), and [primary verification](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round8-offline-contract/execution/PRIMARY-VERIFICATION.json).
