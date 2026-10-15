# R18 S1-OPQ offline diagnosis

**Classification: (a) prompt guidance gap, specifically inverse exemption leaf coverage.** The observed model omitted required leaf text despite general preservation instructions; the prompt does not explain how an exemption asserted in unit prose must also preserve the exempted case on a leaf. A model capability limitation is unproven. This is not an impossible opaque encoding or demonstrated scoring/reference defect.

Paths below are relative to `docs/research/state-rulemaking-benchmark`. Source offsets are Unicode codepoints, end-exclusive, into `round17-paid-comparison/sources-r2/26-19-039/parsed-body.txt` (also `PACKET.json#/source`). File `:N` references denote line numbers; JSON `#/…` denotes a field. Quotes and ranges were checked against the packet source.

## Where the text went

Frozen `round17-paid-comparison/reference/26-19-039/reference.json#/relations` gives:

| Relation | Exact clause and source offsets | Required parts / markers |
|---|---|---|
| R2 | [3273,3297) `This rule is exempt from` | `This rule` [3273,3282); `is exempt from` [3283,3297) |
| R3 | [3457,3520) `This rule proposal, or portions of the proposal, is exempt from` | `This rule proposal` [3457,3475), `portions of the proposal` [3480,3504); `or` [3477,3479), `is exempt from` [3506,3520) |
| R4 | [4087,4118) `rule proposal:\n\nIs fully exempt` | `rule proposal` [4087,4100); `Is fully exempt` [4103,4118) |

`round18-rerun/adjudication/S1-OPQ/output.expanded.json` has precisely these relevant links and leaves:

- Unit 45 → `if` → c9; link evidence `[]`, q=0. c9 is L, no children, q=0, one fragment [3369,3454): `because the content of the rule "is explicitly and specifically dictated by statute."` (s39, head `because the content`, tail `dictated by statute."`, both occurrence 1). This begins **72 codepoints after** R2's end. Unit evidence is s39 [3211,3456), encompassing R2, its target [3298,3367), and the reason. Its assertion explicitly says the rule is exempt from the statute's requirements.
- Unit 46 → `if` → c10; link evidence `[]`, q=0. c10 is L, no children, q=0, one fragment [3599,3694): `under RCW  19.85.025(3) as the rule content is explicitly and specifically dictated by statute.` (s43, head `under RCW`, tail `dictated by statute.`, both occurrence 1). This begins **79 codepoints after** R3's end and ends **393 before** R4's start. Unit evidence: s41 [3457,3588), s43 [3589,3695), s47 [4064,4102), s49 [4103,4120). It includes all counted R3/R4 text; R4's intervening blank line is outside these evidence rows but irrelevant to B1. Its assertion explicitly reports full exemption and the introductory proposal-or-portions alternative.

Neither unit has another condition link. Both have context dependency d=[9], which propagates no applicability. Inspecting **all eleven leaves c1–c11** finds no overlap with any R2–R4 clause. Thus the needed text is in unit evidence and paraphrased in assertions, not another leaf or link. c10's later `Is exempt` sentence does not substitute for the reference occurrence; the actual c10 fragment starts after those words anyway.

## What the model was told

`diagnosis/exact-system-prompt.txt` is the exact dispatched system message, verified equal to offline `wire.build(source, 'opaque')`; dispatched messages and schema match the builder. Relevant exact wording:

- :4: “Conditions belong in source-derived fragments and global g nodes, not repeated capped s/g/r prose.”
- :8: “w if (condition, no sufficiency/necessity claimed), onlyif (source restriction), unless (carveout against assertion), regardless (source says irrespective), obj (directive content/performance, not applicability), acts (unit acts on condition, no effect computed), qual (qualification with unresolved applicability-logic role; link q!=0 and governed unit p2/q!=0 required).”
- :15: “Opaque profile: only L/R nodes with a=[] are permitted. Preserve complete clauses in exact fragments and their source-supported links; use uncertainty and qual for unresolved logic. Do not emit typed-logic nodes.”
- :16 (A5): “If a unit has several conditions of the same role (if, onlyif, unless or obj), emit a single link of that role to one L leaf whose fragments cover each condition in source order (up to 8). Never emit two links of the same role on one unit.”

The base r15.1 prompt also defines EXC [base,carveout], but opaque explicitly prohibits typed operators. The schema permits all seven roles and 1–8 leaf fragments through host validation; it adds no exemption semantics. `unless` covers a carveout **against the unit assertion**. It is not automatically right when the assertion itself says “X is exempt from Y”: that assertion already reverses the implied target. No prompt example or rule explains this inverse case, distinguishes exempted subject from explanatory reason, or requires that subject on a leaf despite being in assertion prose. General preservation guidance is present, so this is a specific underspecification, not absence of any guidance. Nothing explicitly steers exemptions to `if`; that role is in fact compatible here. Replacing `if` with `unless` alone would not repair coverage and would give the wrong polarity once coverage is restored.

## Counterfactual and scoring assessment

The released spec is `round17-paid-comparison/design-r3-1-paccept/ADJUDICATION-SPEC.md`, identified by R18 release-input. B2 (:94) says: “Clause text counts only where a leaf carries it.” B1 (:80–84) separates clause parts from markers; parts must be on leaves, while markers may also be on links. B4 accepts `if`/`onlyif` with odd polarity for EXCEPT. Both original adjudicators map units 45/46 as **inverse**; they supply mappings, not the mechanical scores (Part A M8).

`counterfactual/validate.py` imports unchanged r16.w2.2, its pinned r15.1 dependencies, and the released scorer read-only. It reconstructs the validated wire from the expanded original and changes **only c9/c10 fragments and glosses**: c9 quotes R2; c10 quotes R3 and R4 as two ordered fragments, including the cross-row R4 wording. Units 45/46 and every link remain unchanged. This is a minimal representability proof, not a proposed replacement extraction: the reasons removed from these leaves remain in unit evidence.

Run: `python3 -B docs/research/state-rulemaking-benchmark/round18-rerun/diagnosis/counterfactual/validate.py`.

**Result:** unchanged `validate_response` passes, including r15.1 validation and round-trip checks. Original output scores absent; the counterfactual scores **correct for R2, R3 and R4 under both original mappings**, with complete coverage, zero extraneous counted codepoints, and no contradictory claims. In B4, inverse contributes one flip, with no NOT/EXC paths or reference negators, so `if` has the accepted odd polarity. R3's OR is preserved textually; typed correctness is N/A for OPQ. A new adjudicator following M8 has unchanged assertion/evidence to map, though no new adjudication was performed.

B2 is reasonable for a benchmark of structural clause preservation: broad unit evidence alone cannot prove that a specific case is attached correctly. It is stricter than semantic recall; “absent” here does **not** mean the model failed to understand or mention the exemption. Whole-rule inverse/opposite mapping is a documented close call, but both adjudicators agree and there is no demonstrated reference error or encoding impossibility.

## Proposed R19 sentence

“For an exemption or exception, preserve the exact exempted case and exemption wording in the linked L leaf even when already stated in the unit assertion, using if when the unit asserts the exemption itself and unless when the clause carves out of the unit assertion; explanatory reasons alone do not preserve the exempted case.”

Append only to the clause-only prompt; no wire change was made. The sentence is gated to exceptions/exemptions, preserves assertion-relative roles, and leaves COND, RESTRICT, IRRESPECTIVE, object roles, uncertainty and A5 cardinality unchanged. It contains no source-specific names, offsets or reference targets.

## Open uncertainties

Offline evidence establishes a sufficient representational repair, not the causal effect of that sentence on a future generation. One output cannot establish a model limitation or rule out stochastic failure to apply the general instructions. The primary must decide whether to preregister a prompt-only R19 test and how to assess generalization beyond this now-inspected source; the original R18 result remains unchanged.
