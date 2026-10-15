# R15 Condition/Qualification Preservation — TEST-PLAN.md (Fable advisory, refined; execution pending)

## Provenance
Authored via the Claude.ai Max bridge (Fable 5.1) as advisory design. No research/extraction provider experiment, no API/OpenRouter route, no paid experiment, no implementation run. Earlier advisory text is retained as history; this file is the current plan.

## Purpose
Discriminate full preservation of supported conditions/qualifications from coherent-but-incomplete extraction, inversion, scope leakage, contradiction collapse and serialization clipping, in source-only semantic inventories. Representation is unspecified. Structural validity is never evidence of semantic completeness.

## Oracle tiers
- **Tier A — deterministic.** Runs only on authored fixtures whose expected atoms/operators/scopes carry an explicit, reviewed mapping from the implementation's representation to fixture atoms, and on known-bad outputs (regression shapes). Byte/hash checks apply to evidence spans and receipts only.
- **Tier B — advisory.** Paraphrase entailment, normative force, scope ambiguity, materiality of uncovered spans, adequacy of uncertainty notes. Needs AI/human review even where metadata automates a known inversion or loss. Unseen-source completeness is always Tier B.
- **Triage signals (neither tier's verdict).** Dangling punctuation, non-terminal fragments, trailing commas, empty strings, script-set differences. They queue a string for atom-level survival and advisory review; they are not semantic failures by themselves. No translation capability is required; a supported proper name or term in another script is acceptable when grounded.

## Outcome vocabulary (per fixture, per atom; never summed)
- PRESERVED — expected atoms, operators, scope targets, dimensions and references present, grounded, not inverted; contradictions and ambiguities carried explicitly.
- BOUNDED-FAIL — explicit failure under the implementation's declared capacity policy (inclusive/exclusive/sentinel; per-unit or whole-inventory). No partial salvage, clipping or repair.
- SILENT-LOSS — atom, operator, scope, dimension or reference absent or shortened with no failure signal.
- INVERTED — operator, polarity, scope, modality or comparator contradicts the fixture.
- COLLAPSED — a fixture-marked contradiction or ambiguity resolved to one reading without uncertainty.
- FABRICATED — content not grounded in fixture bytes (resolved missing section, filled timezone, inferred status).
- NOT-EXPOSED / POLICY-UNDECLARED — bound or capacity policy not declared; recorded, not scored.

## Boundary rule
For each declared bound B, probe B-1, B, B+1 and interpret results by the declared inclusive/exclusive/sentinel policy. Exactly-B passing is not assumed. Global request/inventory limits may fail as whole-inventory BOUNDED-FAIL without naming a unit; per-unit limits should name the unit only if the implementation declares per-unit semantics. Local byte/char/token estimates are not matched-tokenizer or live-fit guarantees.

## Reference rule
A reference to content not in the supplied excerpt is UNAVAILABLE-IN-EXCERPT. That is not a jurisdictional/external legal classification. Unavailable references retain their target identifier and are not resolved. An invalid internal link is an inventory ID that points to no inventory node; it is a structural defect, distinct from an unavailable source reference. Waiver interaction with an unavailable requirement is UNKNOWN, not asserted either way.

## Test families (12)
| ID | Family | Fixtures | Tier A (automatic) | Tier B (advisory) |
|---|---|---|---|---|
| TF-01 | Full vs coherent-but-incomplete conjunction | FX-A, FX-A2 | atom coverage; grammatical-prefix detection | paraphrase adequacy |
| TF-02 | Boolean/operator inversion | FX-B, FX-A | operator per group; nesting shape | alternate encodings |
| TF-03 | Baseline vs granted-waiver scope; nested exceptions | FX-A2, FX-B, FX-E | waiver trigger ≠ offer; waived-set equality | scope paraphrase |
| TF-04 | Unavailable references vs invalid internal links | FX-B, FX-G, FX-S2 | unavailable marker + identifier; no resolution text; dangling-ID detection | reference-class choice where ambiguous |
| TF-05 | Modal strength, bare imperative, contradiction | FX-C | label within allowed set; both statements present | justification of chosen force |
| TF-06 | Proposed vs current status scope | FX-C, FX-C2 | status within allowed set per duty | scope-uncertainty wording |
| TF-07 | Independent clock/date/tz/receipt dimensions | FX-D | per-dimension equality incl. ABSENT | added-inference labeling |
| TF-08 | Unicode exact evidence and receipts | FX-F | evidence/receipt byte equality; no NFC collapse; declared offset unit; separator retention | paraphrase grounding |
| TF-09 | Capacity bounds and payload growth | FX-L | outcome consistent with declared policy; no clipped strings; growth table | growth acceptability |
| TF-10 | Receipts, coverage, truncation/receipt drift | FX-R, FX-A trunc | hash equality; span bounds; atom disappearance matches deletion | uncovered-span materiality |
| TF-11 | Member-scoped permissions, exception leakage | FX-E | member×condition×exception matrix | sufficiency vs necessity labels |
| TF-12 | Structure-only validity and regression string shapes | FX-S1, FX-REG | cycle/dangling/duplicate detection; triage flags; atom survival | whether a flagged string was the only carrier |

## Execution notes (Codex, later)
- `python -I`; fixtures in their own directory; scripts elsewhere; fixture bytes canonical.
- Fixture files keep `source` (bytes) separate from `expected` (checker data). No test instructions inside `source`.
- Contradiction variants require both statements plus uncertainty; coherent scope-change variants edit every conflicting sentence and require the new scope.
