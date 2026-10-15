# Jev and deterministic verification — developmental pilot

Completed October 6, 2026 Pacific. Research only; no production ingestion or state expansion.

**Jev earned a place in the next experiment as a semantic verifier. It did not earn authority to accept notices without source checks.** In this small selected challenge, it caught substantially more problems than GPT-4.1 Nano. Both models missed a literal email typo even when the correct spelling was supplied. A deterministic comparison caught it immediately.

## What ran

The native-text baseline replayed 28 previously reviewed notices, retaining 264 literal candidates with source offsets. All 28 documents routed to further review, including three empty native-text inputs requiring parser fallback. Sixteen offline tests passed. This measures candidate extraction behavior and conservative routing, not extraction accuracy or complete normalization.

Separately, 16 reviewer-authored claim cases tested verification: four correct controls, four projections from actual retained parser errors/role loss, and eight controlled mutations. These cases deliberately reuse documents and source passages. The excerpts were selected and scoped by reviewers; this does not measure automated retrieval, document segmentation, or the baseline's own candidate accuracy.

Both verifier arms received identical source/candidate/evidence state and the same four rubrics: support, role, conditions, and source conflict. The frozen rule requires all four favorable labels and passing deterministic checks. Confidence was retained but did not change the rule. Jev requested and returned `jev-1.13.0`; OpenRouter requested and returned `openai/gpt-4.1-nano` (a catalog model ID, not proof of immutable underlying weights). Each made 15 successful requests with no retries. C007's null candidate was blocked before inference in both arms.

## Frozen pilot results

| Measure | Jev | GPT-4.1 Nano |
| --- | ---: | ---: |
| Detectable errors sent to review, among model-eligible cases | 8/9 | 2/9 |
| Detectable errors sent to review, including shared deterministic abstention | 9/10 | 3/10 |
| Correct controls accepted as text-supported | 3/4 | 4/4 |
| Source-conflict cases sent to review | 2/2 | 2/2 |
| Known same-parser corruption accepted as text-supported | 1/1 | 1/1 |

One additional case, C016, was declared ambiguous before execution and excluded from primary determinate metrics. Both models accepted it. Its displaced hearing-date association may reasonably be reconstructed from the supplied text; the original parser-fidelity failure does not force a semantic-verification failure.

The deterministic baseline cannot establish semantic roles and therefore has zero automatic acceptance coverage. Routing everything to review avoids acceptance errors but is not a useful accuracy win. The model comparison above shows the incremental behavior on scoped claims, not a validated reduction in whole-document review workload.

The nine model-eligible detectable errors comprise seven controlled mutations and two projections of observed parser errors. Jev flagged all seven mutations and one of those two projections; Nano flagged two mutations and neither projection. Do not interpret these enriched, correlated counts as natural error rates or national accuracy.

## Findings that change the design

**Exact destinations belong in code.** C002 proposes `DNRAministrativeRulesComments@wisconsin.gov` while its supplied source says `DNRAdministrativeRulesComments@wisconsin.gov`. Both models accepted the incorrect candidate. Jev assigned its supported label probability 0.95, demonstrating that a high reported probability can accompany a consequential error on this task. The frozen deterministic checks verified quote integrity and candidate/claim consistency, but did not compare the destination against source email tokens. That was a baseline omission.

A separate, explicitly post-hoc exact-token check rejects C002 and preserves the correct control. It is not folded into the frozen scores. It also accepts C003, where the parser text and candidate both contain the same wrong address. That is the expected evidence limitation: matching a corrupted text channel does not verify the PDF. Independent evidence or visual review is still required.

**Jev helped with meaning and scope, but over-escalated one correct control.** It flagged unsupported filing/comment roles, an anticipated date asserted as actual, lost hearing conditions, malformed date-range evidence, and unresolved source conflicts. It also rejected the correct initial-hearing date range C004 over qualifications belonging to a separate possible extension. That is a real scope/false-escalation issue under the predeclared label, retained in the score.

**A useful routing outcome does not guarantee correct diagnostic labels.** Nano sent both conflict cases to review but labeled conflict absent; other dimensions triggered review. Jev sometimes combined supported with conflict present. Preserve the component outputs and evidence rather than presenting a single trust score or treating a model's diagnosis as a proven fact.

**Nano is not suitable as the sole semantic gate under this tested prompt and configuration.** This result is about this specific comparator, not all inexpensive general models. There was no prompt tuning, model swap, or threshold selection after seeing responses. Jev answered four independent Choice questions; Nano produced one structured response with four labels. Interface and option-order effects were not isolated, so this is a comparison of tested configurations, not model weights alone.

## Cost and execution

- Jev: 36,172 input tokens; 2,611 reported output tokens. At the documented $0.042 per million input tokens and free outputs, nominal list-price equivalent **$0.001519224**.
- OpenRouter Nano: 22,756 input tokens; 320 output tokens; **$0.0024036 reported usage cost**, already including upstream inference.
- Thirty successful provider requests, zero failed requests, zero retries. These values are not reconciled cash invoices. Development/review effort and historical parsing charges are separate. [TypeSafe published model/pricing](https://docs.typesafe.ai/models); the OpenRouter catalog snapshot is retained under verifiers/model-catalog-snapshot.json.

The input code, runtime bundle, evaluation labels, rubric and challenge contract retained their frozen hashes. One ancillary protocol review note changed 0.744 seconds after the freeze, before the first provider call, while its child task finalized the handoff; only status/final-resolution metadata changed. The freeze mismatch is retained and audited rather than overwritten. It did not change runtime requests, labels, or the acceptance policy. The staged runner receives no evaluation labels; separation is by explicit file inputs and code allowlists, not a claimed operating-system isolation boundary.

## What this supports next

Keep exact strings, date validity/arithmetic, types and provenance checks in code. Use Jev experimentally to judge narrow semantic relationships and conditions. Escalate missing or changed source evidence to a parser or source reviewer, and unresolved source conflicts to review; a more expensive model cannot create missing evidence.

Before fresh testing, connect an automated proposer/context selector to the verifier, incorporate exact destination checks, and freeze a complete routing policy. Then evaluate on new source families with real scans, source-image review, and explicit acceptance/error criteria. This pilot does **not** complete automated normalization, cost-optimal parser routing, fresh evaluation, or deployment validation.

## Artifacts

- [Native baseline](baseline/README.md), [baseline summary](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round3/baseline/summary.json).
- [Frozen inputs and code hashes](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round3/execution/freeze.json), [hash verification](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round3/execution/freeze-verification.json).
- [Jev metrics](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round3/execution/jev-metrics.json), [Nano metrics](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round3/execution/openrouter-metrics.json), [cost ledger](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round3/execution/cost-ledger.json).
- [Post-hoc destination check](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round3/execution/posthoc-destination-check.json).
- [Challenge and label history](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round3/challenge/contract.json), [pre-run label review](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round3/protocol/challenge-label-review.json).
- [Verifier implementation](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round3/verifiers/verifier.py), [broader protocol](protocol/protocol.md).

The raw responses, exact requests, status records and per-case outputs are retained under execution/jev and execution/openrouter. Runtime candidates are reviewer-authored; references are agent-adjudicated and not human gold labels.

Independent verification: [completion audit](protocol/completion-audit/AUDIT.md) and [adapter audit](verifiers/postrun-audit.md).
