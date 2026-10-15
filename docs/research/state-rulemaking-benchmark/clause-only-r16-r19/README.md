# R16–R19 clause-only track: write-up and stop decision

**Decision (2026-10-14): the paid clause-only track stops here.** Across three paid rounds, the clause-only profile (`opaque`: L/R nodes and role-typed links only) never met its pre-registered bar. Each round failed for a different reason, and the fix for each failure worked. Further prompt patches would be tuned to outputs we have already inspected, so another round on these sources can no longer show generalization. Any future test needs a fresh, pre-selected source set.

## What was tested

R16 built a wire format (r16.w2.x) that the unchanged R14 checker accepts. It decodes into the unchanged r15.1 validator. R17 froze the design for a paid comparison:
- **Sources.** Three new Washington State Register notices, 26-19-039, -041 and -106 (S1–S3).
- **References.** Written by Fable and reviewed by Astra. They were committed before any output existed.
- **Scorers.** Two independent adjudicators, A1 (Fable) and A2 (Opus).
- **Thresholds.** Fixed in advance in `round17-paid-comparison/design-r3-1-paccept/ADJUDICATION-SPEC`:
  - D3 needs pooled correct ≥ 12/15 and acceptable ≥ 14/15.
  - D4 needs zero critical failures.
- **Futility rule.** The run stops as soon as the bar becomes unreachable.

The full typed profile was never run. The sources held 4 compound conditions, fewer than the 5 that E8 requires to test it.

R18 and R19 reran clause-only. Each changed exactly one prompt sentence (A5, then A7). Everything else stayed the same: sources, references, scorer specification, thresholds and runner. Each also used a fresh ledger namespace and recorded usage at INIT as the reconciliation baseline (A6).

## Results

| Round | Change | Calls | Outcome | Why it failed |
| --- | --- | --- | --- | --- |
| R17 | baseline r16.w2.1 | S1 | O3, mechanical | S1 output invalid. Unit 51 carried two `if` links, which role cardinality forbids, and clause-only has no AND node. The prompt never said one leaf may hold several fragments. |
| R18 | A5: merge same-role conditions into one multi-fragment leaf | S1 | O3 | Output validated, but EXCEPT R2–R4 scored `absent`. Leaves c9 and c10 held the reasons for the exemptions, not the exempted-case text (ADJ B2). |
| R19 | A7: keep the exact exemption wording on the linked leaf | S1, S2 | O3 | All 7 EXCEPT relations had full text on a leaf, but each scored `broad`: extraneous text exceeded 2×\|K\| (M8). On S2, R7 ("**only** licensed acute care hospitals which do not meet the definition of 'small business'…", critical) was linked `if` instead of `onlyif`, a critical scope change (D4). |

R19 bar arithmetic: after S2 there were 3 correct of 12 scored relations, with only 3 left in S3. D3 was therefore unreachable even without the D4 failure. S3 (26-19-106) was never run in any round.

Per-relation scores after the final round (R19):
- **COND R1, R2, R8 (S2, critical):** correct.
- **EXCEPT S1 R2–R4 and S2 R3–R6, R9:** broad.
- **RESTRICT S2 R7 (critical):** scope_change.
- **S1 R1:** excluded as UNRESOLVED.

## What is established

- **The wire format works against the live provider.** All four paid calls returned HTTP 200 with `finish_reason: stop` through OpenRouter to `openai/gpt-6.1-sol` in strict mode. That resolves R16's open "provider compatibility unverified" item. Completion tokens ran 4,785–5,682, well under the 16,384 cap and above R14's old 8,192 limit, which the R16 README had flagged as a headroom risk.
- **The scoring is reliable.** A1 and A2 agreed exactly on every scored relation: 3/3 in R18 and 12/12 in R19 (κ = 1). The adjudication spec gives consistent verdicts on these outputs.
- **Each prompt fix did what it was written to do:**
  - A5 removed the R17 cardinality failure.
  - A7 removed the R18 missing-text failure.
  - A7 also held on S2, which nobody had inspected when A7 was written.
- **The money controls held.** Every call reconciled exactly against key usage. The ledger debited conservatively (FLOOR $0.27 per call) and closed with no residue.

## What is not established

- **Whether clause-only can meet the bar.** Two gaps remain:
  - **Breadth.** EXCEPT leaves over-quote.
  - **Role choice.** An "only…" restriction was encoded as `if`. The prompt already defines `onlyif` as "source restriction", so with n=1 this may be a model error, not a guidance gap.
- **Generalization of any further prompt fix.** A5 and A7 were both written after inspecting S1 outputs. A fix for breadth or role choice would be written after inspecting S2 too, leaving only S3 unseen. That is too small a held-out set to carry a pre-registered bar of 15 relations.
- **Anything about the typed layer.** It was untestable on these sources (E8).
- **Extraction quality beyond these three notices.** At most 12 relations were ever scored, from two sources. No production eligibility or action readiness follows from this track.

## Spend

| Round | Provider-reported | Ledger debit (conservative) |
| --- | --- | --- |
| R17 | $0.0594085 | $0.27 |
| R18 | $0.059411 | $0.27 |
| R19 | $0.132917 | $0.54 |
| **Total** | **$0.2517365** | **$1.08** |

The provider-reported figures match the change in key usage exactly. Invoices were not checked against these figures. R17 ran under its own $2.00 cap. R18 and R19 ran within the user's $3 tolerance.

## If this track resumes

1. **Choose a fresh source set before writing any prompt change.** Freeze it and its references the same way R17 froze its own, then keep the outputs unseen until scoring.
2. **Size the set for both questions.** Enough EXCEPT and RESTRICT relations to carry D3, and at least 5 compound conditions so the typed profile is testable (E8). Then clause-only can be compared against full typed in one run, which was R17's original intent.
3. **Candidate prompt sentences**, to be frozen before the new sources are seen:
   - keep an exception leaf to the clause itself;
   - map "only…" scope restrictions to `onlyif`.
4. **Reuse everything else unchanged:** the R19 wire/adapter, the scorer specification and the runner, ledger and signing path.

## Evidence

- R16: [README](../round16-wire-compat/README.md), [final verification](../round16-wire-compat/FINAL-VERIFICATION.json).
- R17: [final](../round17-paid-comparison/FINAL.json), [primary decisions](../round17-paid-comparison/PRIMARY-DECISIONS.md), [sources](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round17-paid-comparison/sources/SELECTION.md).
- R18: [sketch](../round18-plan/SKETCH.md), [final](../round18-rerun/FINAL.json), [diagnosis of the EXCEPT loss](../round18-rerun/diagnosis/DIAGNOSIS.md).
- R19: [A7](../round19-rerun/amendments/A7.md), [review](../round19-rerun/review/REVIEW.md), [final](../round19-rerun/FINAL.json), decisions for [S1](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round19-rerun/adjudication/decision-s1/decide.out.json) and [S2](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round19-rerun/adjudication/decision-s2/decide.out.json).
