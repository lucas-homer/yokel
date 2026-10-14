# R17 adjudication specification (r17.adj.v2)

Normative for R17 scoring. **Part A** is the complete brief an adjudicator sees. **Part B** is the mechanical scoring that `fixtures/r17score.py` implements; adjudicators do not see it. **Part C** fixes the output format, denominators, disagreement handling, the fixture gate and the decision entry point. If Part B and `r17score.py` disagree, that is a defect to fix before freeze; neither one silently wins.

Design choice (unchanged): the only meaning judgment an adjudicator makes is the **target mapping**: which output units assert each reference target, and in which form. Everything downstream is mechanical, so both adjudicators score every item through the same deterministic rules, and the adjudicators never compute totals (R14 F7).

r3 narrows what is scored rather than adding judgment: clause text counts only where a leaf carries it (B2), typed structure is scored only where the reference declares a compound (B7), and the reference's `carves_out_of` field and its compound are removed (REFERENCE-SPEC r17.ref.v3).

---

## Part A — Adjudicator brief (the only part shown to adjudicators)

### A1. Inputs and isolation

You receive one packet containing exactly:

1. the source text;
2. the frozen reference for that source (format `r17.ref.v3`). Use its targets, and use each relation's `clause` only for rule M2; you may ignore `rationale`;
3. one extraction output record: a JSON object with `units` (each has `id`, `assertion` and `evidence`, a list of `[start, end]` codepoint ranges into the source), `nodes` and `links`;
4. the values `call_id`, `source_id`, `output_sha256` and `reference_sha256`, which you copy into your answer unchanged;
5. this Part A.

Work in a **fresh session** with no other context. Do not open other files, other outputs, other adjudicators' files or any scores. You will not be told which output format variant produced the record. Do not infer quality from structure. Your job is the mapping only.

### A2. The mapping task

For **every** reference target (`T1`, `T2`, ...), list the output units that assert the target, each with a `form`. Decide the form by asking these questions in order, using the unit's `assertion` read with its `evidence`:

1. **`direct`**: does the unit state the target's assertion itself, with the same action, the same actor or object, and the same modality direction? ("Comments must be received by the agency.")
2. **`inverse`**: does the unit state that the target's assertion does **not** hold for a population, case or circumstance **that the assertion names**? ("Small vendors are exempt from the fee", when the target is "the fee [applies]"; "The rule does not apply to tribal land.")
3. **`opposite`**: does the unit deny the target's assertion for the same actor, action or object **without naming any** such population, case or circumstance? ("No hearing will be held." "Night markets need not close by midnight.")
4. Otherwise the unit does not map to this target.

Rules:

- **M1 Meaning first.** Map from the assertion's meaning. Overlapping evidence alone is never enough.
- **M2 Evidence must touch.** A mapped unit's `evidence` must overlap the target's quote or the `clause` of at least one of that target's relations. Never map a unit with no such overlap. If you think one should be mapped anyway, record a `mapping_doubts` note instead.
- **M3 Scope.** A unit whose assertion is **broader** than the target (for example the whole paragraph's gist) or **narrower** (for example the target with a condition folded into the assertion text) still maps `direct` if a reader of that unit would take it as making the target's assertion. Note the breadth in `mapping_doubts`. A unit asserting a **different** assertion (a different actor, action or object) does not map.
- **M4 Denials are mapped, not dropped.** A unit that contradicts the target is listed as `opposite` (question 3). Do not leave it out and do not move it to notes.
- **M5 Several units.** List every unit that independently asserts the target (duplicates and restatements). Order does not matter.
- **M6 None.** If no unit asserts the target, give an empty list. That is a legitimate answer.
- **M7 Many-to-many.** One unit may map to several targets if it genuinely asserts each one.
- **M8 Do not judge conditions.** Do not look at whether the conditions, links or nodes are right. Map from the assertion and evidence only. Condition handling is scored mechanically after you finish.

### A3. Notes (never change scores)

- `mapping_doubts`: a list of `{"tid": "T1", "note": "..."}` for close decisions.
- `reference_defects`: a list of `{"rid": "R2" or null, "kind": k, "note": "..."}` where you believe the reference itself is wrong. `k` is one of `missing_relation`, `wrong_target`, `wrong_class`, `segmentation`, `critical_flag`, `quote`, `other`. These feed a sensitivity analysis only.
- `other`: a list of strings.

### A4. Output (exactly one JSON object)

```json
{
  "spec_version": "r17.adj.v2",
  "adjudicator": {"role": "A1", "model": "claude-fable-5-1", "effort": "high", "session": "<thread id>"},
  "call_id": "<given>",
  "source_id": "<given>",
  "output_sha256": "<given>",
  "reference_sha256": "<given>",
  "mappings": [
    {"tid": "T1", "units": [{"unit": 3, "form": "direct"}], "basis": "Unit 3 states that ..."}
  ],
  "notes": {"mapping_doubts": [], "reference_defects": [], "other": []}
}
```

Every reference target appears exactly once in `mappings`. `basis` is one or two sentences; it is kept for audit and never compared.

---

## Part B — Mechanical scoring (normative; implemented by `fixtures/r17score.py`)

### B1. Codepoint sets and negation sources

`counted(c)` is true unless `c` is Unicode whitespace or separator (Z*), punctuation (P*) or control (Cc). For a set of ranges, `cps(ranges)` is the set of counted codepoints.

For each reference relation `r`:

- `K_parts(r)` = `cps` of all PART quotes in `r.logic`;
- `K_markers(r)` = `cps` of `r.introducer` plus every `markers` quote at every level of `r.logic` (connectives, repeated introducers, negators, exception words);
- `K(r)` = `K_parts ∪ K_markers`. **Connectives and negators are required evidence for both arms.**
- `clause(r)` = `cps(r.clause)`. The reference checker guarantees `clause(r) = K(r) ∪ cps(r.excluded)` exactly (REFERENCE-SPEC §4.2 rule 8).
- For each `x ∈ K_parts(r)`, the **negation sources** `S(x)` are, in the reference logic: every `NOT` above `x` (its markers), every `EXC` whose carve-out contains `x` (its markers), and every negator marker of `x`'s own PART. `|S(x)|` is the reference's negation count for `x`.

### B2. Claims and witnesses

A **claim** is one link `ℓ` whose unit is mapped to `r`'s target, taken with that unit's form. A **witness** of a claim is a node path `p` from `ℓ`'s root to a node `v`. For a witness:

- `allcov` = `cps`(ℓ's evidence ∪ evidence of every operator on `p` above `v` ∪ evidence of every node in `v`'s subtree);
- `leafcov` = `cps`(evidence of the `L`/`R` leaves in `v`'s subtree);
- `credited` = `(leafcov ∩ K_parts(r)) ∪ (allcov ∩ K_markers(r))`.

**Clause text counts only where a leaf carries it.** Link and operator evidence (the wire's connective fragments) can satisfy markers, never clause parts. A link citing the whole clause over a leaf that quotes something else is `shortened` (fixtures F01d, F01e).

Coverage never combines two links, two units or two paths. A claim's **best witness** minimizes, in order: text status (B3), minus `|credited|`, extraneous count (B6), `|allcov|`, path.

### B3. Text status (from `credited`)

- `complete`: `K(r) ⊆ credited`
- `lost_marker`: `K_parts(r) ⊆ credited`, but some marker is missing
- `partial`: `credited` is non-empty but not as above
- `absent`: `credited = ∅`

Quote occurrences are resolved by explicit offsets (REFERENCE-SPEC §2). Covering an **earlier** "or" never covers the reference's second "or" (fixture F14).

### B4. Reference-relative polarity and role

For a claim on `ℓ` with form `F` (`form_flip` = 0 for `direct`, 1 for `inverse` and `opposite`), consider every root-to-leaf path in `ℓ`'s graph that ends at a leaf whose evidence contains some `x ∈ K_parts(r)`. For each such `x` and path:

`f = form_flip + path_flips + intact − |S(x)|   (mod 2)`

- `path_flips` counts edges out of a `NOT` and edges into an `EXC` carve-out (child 2). `AND`, `OR`, `ALT` and an EXC base add none.
- `intact` counts the sources in `S(x)` whose marker codepoints all lie in **that leaf's own evidence**: the leaf keeps the negator as its own wording, which is the same meaning as an explicit `NOT`.

If `f` takes one value `p` for every such `x` and path, the claim's role verdict is the table entry for (link role, `p` flips). If both values occur, **one component's polarity is wrong** and the claim's verdict is `inversion` (fixtures F15e, F22b, F23b).

Consequences, each fixed by a fixture: an explicit `NOT` that matches a reference negator is correct (F09b, F22a, F23a); an intact negative leaf is correct (F09c, F22c, F23c); a `NOT` over a leaf that still contains its negator negates twice (F09d, F23d, F24c); an exception whose clause is itself negative composes correctly through two supported NOTs (F24a); a reversed EXC inverts both sides (F07). Polarity is per claim, so a containing operator cannot lend a clause an uninverted path.

A claim is **explicitly uncertain** if the link has `q≠0`, or any node on any of those paths has `q≠0` or is `ALT`. Unit-level uncertainty does not count.

Role verdict for class `C` (unchanged from r2):

| role (after `p` flips) | COND | RESTRICT | EXCEPT | IRRESPECTIVE |
|---|---|---|---|---|
| `qual` | hedged | hedged | hedged | hedged |
| `obj`, `acts` | hedged if uncertain, else **role_loss** | same | same | same |
| `if` (even) | correct | hedged if uncertain, else **scope_change** | **inversion** | **inversion** |
| `onlyif` (even) | hedged if uncertain, else **scope_change** | correct | **inversion** | **inversion** |
| `unless` (even); `if`/`onlyif` (odd) | **inversion** | **inversion** | correct | **inversion** |
| `unless` (odd: positive, strength indeterminate) | hedged if uncertain, else **scope_change** | same | **inversion** | **inversion** |
| `regardless` (any) | **inversion** | **inversion** | **inversion** | correct |

The wire prompt says `if` asserts neither sufficiency nor necessity. The table never derives a role from Boolean implication; any change of strength is a **scope_change** unless it is explicitly hedged.

**Embedded.** If the claim's best witness node is a single `L` leaf, its status is `complete`, its verdict is not correct or hedged, and the same leaf completely carries another live relation `h` of the same target whose verdict through the same link is `correct`, then the claim's verdict is `embedded` (F12).

### B5. Relation verdict (precedence: the first rule that applies wins)

Contested relations are scored the same way and reported as `excluded_contested:<verdict>`. `UNRESOLVED` relations are excluded from the primary scores and reported in calibration (B8).

1. **No claim credits anything.** If a claim on a unit **outside** the mapping is `complete`, the verdict is `wrong_target`; otherwise `absent`. An empty mapping falls here.
2. Otherwise pick the **best claim** by: text status, more `credited`, role verdict (correct < hedged < embedded < scope_change < role_loss < inversion), fewer extraneous, smaller `allcov`, link index.
3. Best is `partial` → **shortened**. Best is `lost_marker` → **lost_connective**.
4. Best verdict is `inversion`, `role_loss` or `scope_change` → that verdict.
5. **Extra-claim audit** → **contradiction** if either holds:
   - (a) another claim carries the complete clause parts (`complete` or `lost_marker`), uses an applicability role (`if`, `onlyif`, `unless`, `regardless`), is not explicitly uncertain, and has verdict `inversion` or `scope_change` (F10g, F10i, F11a). `obj`, `acts` and `qual` claims assert no applicability and are compatible (F10h). An `embedded` copy is compatible (F12b).
   - (b) a unit mapped `opposite` has no link, other than `obj`/`acts`, whose leaves carry the complete parts of a live relation of the target: an unqualified denial (F05c). A denial that links the clause is scored as a claim like any other (F05d).
6. Best is correct or hedged and extraneous > 2 × |K(r)| → **broad**.
7. Otherwise the best verdict: **correct**, **hedged** or **embedded**.

Verdict groups:

| group | verdicts |
|---|---|
| harmful | absent, wrong_target, shortened, lost_connective, inversion, role_loss, scope_change, contradiction, cell_failed |
| complete (text) | correct, hedged, embedded, broad, inversion, role_loss, scope_change, contradiction |
| acceptable | correct, hedged, embedded, broad |
| critical requirement met | correct, hedged, broad |

`cell_failed` is assigned only by the decision entry point (C5) to every relation of a structurally failed cell; it never comes from scoring an output.

### B6. Extraneous coverage

`extraneous(w)` = `|allcov(w) − (cps(target quote) ∪ ⋃ clause(r') for all relations r' of the same target)|`. The target's own assertion, its relations' clauses and their exclusions are never extraneous.

### B7. Typed logic (FULL only; OPQ reports N/A)

**Compounds** are the `AND`, `OR` and `EXC` nodes of live relations (id `rid:nid`); they inherit `critical` from their relation. NOT is not a compound: its semantics are scored by B4 on the relation, and an unsupported NOT is an invented operator below. The r2 `exception_to` compound is removed with the reference's `carves_out_of` field.

For a compound `n` of relation `r`:

- If `r`'s verdict is not acceptable → `relation_failed` (not correct; the harm is already on `r`).
- Search the operators `O` in the subtree of `r`'s best witness node that have as many children as `n`. An output child **matches** a reference child when the output child's leaves carry exactly the reference child's clause parts among `K_parts(r)`: nothing missing and nothing from a sibling. This enforces nesting (F25b) as well as coverage.
  - `n` and `O` both `EXC`: base matches base and carve-out matches carve-out → **correct**; crossed → **exc_reversed**.
  - otherwise, if `O` ∈ {AND, OR, ALT, EXC} and a one-to-one matching of children exists: same operator → **correct**; `ALT` → **hedged**; different operator → **swap**.
  - Preference: correct > hedged > swap > exc_reversed.
- With no match: if some AND/OR/ALT/EXC operator in that subtree puts parts of two different children of `n` under different children → **mismatch**; otherwise **flattened** (kept in one leaf: not typed-correct, not harmful).

**Invented operator.** For each live relation with an acceptable verdict, look at the operators on its best witness path above `v` and in `v`'s subtree. An `AND`, `OR`, `EXC` or `NOT` with `q=0` is **invented** unless:

- it was matched to a reference compound above (including swap, mismatch and exc_reversed, so no operator is penalized twice);
- it is an `AND` whose every child carries at least one whole live relation and which carries at least two (the format allows one `if`/`onlyif`/`unless` link per unit, so separate conditions must be conjoined);
- it is an `EXC` whose base touches the target or carries a relation of the target, and whose carve-out carries an `EXCEPT` relation of the target (F06, F21);
- it is a `NOT` whose own evidence cites a negation word from the target's live relations (a NOT, EXC-carve-out or PART negator marker) or an `EXCEPT` introducer of the target (F08a, F24a).

Each invented operator is counted once, attributed to the lowest `rid` whose scope contains it, and is critical if any such relation is critical. Two NOTs citing nothing are parity-neutral, so the relation stays correct, but both are invented (F16b).

**Typed harmful** errors are swap, mismatch, exc_reversed and invented.

**M6b (reported, not scored).** `unscored_operators` lists the operator nodes outside every scored relation's witness scope.

### B8. Calibration (reported only)

For each `UNRESOLVED` relation, the result is `calibrated` if any complete claim is explicitly uncertain or uses `qual`; `asserted` if claims are complete but none is uncertain; otherwise `not_preserved`.

---

## Part C — Format, denominators, disagreement, fixture gate, decision

### C1. Who scores what

- **A1**: Fable 5.1 (`claudeAgent` / `claude-fable-5-1`, high, claude.ai subscription), in a fresh session per output. It must not be any session that authored or reviewed a reference.
- **A2**: Opus 5.5 (`claudeAgent` / `claude-opus-5-5`, high, subscription), in a fresh session per output.
- **Both adjudicators independently map every target for every scored output.** There is no sampling, and neither sees the other's files.

### C2. Denominators (frozen at reference freeze, before any dispatch)

- **Relations:** all reference relations with `contested = false` and `class ≠ UNRESOLVED`, per source and pooled. Both arms use the same denominator. An item is never dropped because an output failed. A structurally failed cell (truncated, invalid or refused) fails D1 directly; its relations are entered as `cell_failed`, never scored as partial content.
- **Compounds:** all compounds as defined in B7.
- The release record (PROTOCOL C6) publishes the **scoring manifest** (C5): per source the live relation ids and critical flags, the compound ids and critical flags, `N`, `n_s`, `N_c` and the required integer counts (PROTOCOL §11 table), before the first transport attempt.

### C3. Disagreement

- **Item level:** for every relation, compare A1's verdict with A2's. Report the exact-verdict agreement count, the disagreement list and **Cohen's κ over five mutually exclusive categories**: `correct`; `hedged_or_broad` (hedged, broad); `embedded`; `text_harmful` (absent, wrong_target, shortened, lost_connective); `semantic_harmful` (inversion, role_loss, scope_change, contradiction); plus `cell_failed` if present. κ = (p_o − p_e)/(1 − p_e) as an exact fraction; it is reported as undefined when p_e = 1. Reporting only; nothing is averaged or merged (fixture K01).
- **Bar level:** evaluate every bar (D for OPQ; D and T for FULL) **separately** under A1's scores and under A2's.
- **Outcome level:** PROTOCOL §11 combines the two bar results. No hybrid or best-of score is ever computed.

### C4. Fixture gate (before any reference is authored)

1. `python3 -I -S -B fixtures/check.py` exits 0. It reports scorer checks by section; these are **not** adjudicator results.
2. **Gold vs mutation.** Cases with `gold: true` are adjudicator gold packets: every unit carries `assertion` and `evidence`, every gold mapping obeys M2 (checked), and identical packets carry one gold mapping (checked). Cases with `gold: false` (F05b) are scorer mutation tests with a deliberately wrong mapping; they are never shown to an adjudicator.
3. `check.py --emit-packets DIR` writes one packet per gold case. A packet holds Part A, the source, the reference, the output and the four binding values, under an **opaque** id (`fx-…`). It never holds the case name, purpose, expected verdicts or mapping.
4. A1 and A2 each answer **every** packet, one fresh session per packet. `check.py --adjudications DIR` requires exactly `DIR/A1/` and `DIR/A2/`, each with exactly one file per gold packet (`<packet id>.json`). Each file must carry the right role, pinned model and effort, a session id used nowhere else, and the echoed `call_id`/`source_id`/`output_sha256`/`reference_sha256`; and its mapping must equal the gold mapping exactly on **(target, unit, form)**. `basis` and notes are never compared. Zero, one or three adjudicator directories fail (gate self-test in `check.py`).
5. If either adjudicator fails, the primary may correct a fixture **only through a recorded, reviewed fixture correction** (a gold mapping that Part A does not determine is a fixture defect), or revise Part A's wording. Then rerun **both** adjudicators on the whole repaired gate in new sessions. After two failed rounds, stop and escalate; the protocol cannot freeze.
6. Freeze `ADJUDICATION-SPEC.md`, `r17score.py`, `r17recon.py`, `cases.src.json`, `cases.json` and `check.py` by SHA-256 in the release record, with both adjudicators' gate reports.

### C5. Decision entry point

`r17score.py decide DECISION.json [--interim]` is the **only** decision gate; the per-output scorer is internal. Its inputs are the scoring manifest, one call record per planned cell, and the files by name. Before computing anything it checks, and rejects on any mismatch (fixtures A02–A08):

- manifest: version; adjudicators exactly A1/A2 with the pinned models and effort; exactly slots S1–S3; per slot the source and reference file SHA-256; the reference passes `validate-reference`; and its **live relation ids, critical flags and compound ids equal the manifest exactly**;
- call records: exactly S1–S3 × OPQ/FULL; each state is a final response state 2–13 or `skipped` (`pending` only with `--interim`); `completion_tokens` a nonnegative integer for states 10–13; for state 13 the output file's SHA-256 equals the record; no FULL call released unless OPQ passed under both and typed logic is testable; no call released after an unrun one;
- adjudications: for every state-13 cell, both `<call>.A1.json` and `<call>.A2.json`, with the pinned identity and the echoed `call_id`, `source_id`, `output_sha256` (of the actual file) and `reference_sha256` (from the manifest).

It then scores each cell under each adjudicator, builds cells **from the manifest's ids** (never from the score's own lists), and computes per-adjudicator phase states, bars and the outcome (PROTOCOL §8, §11), plus κ. `--interim` is the staged futility test after each call: unreleased cells are `pending` and best-case, and the outcome is `null` while no stopping state has been reached (fixture A09).

### C6. Reference-defect sensitivity (E10; reported only)

For each adjudicator, for each `reference_defects` entry with a non-null `rid` that is live: recompute that adjudicator's bars with that relation removed from every denominator (`drop_relations`), and report which bar results change. Then report the same with every flagged relation removed at once. Entries with `rid: null` (for example `missing_relation`) are listed, not computed. The primary result and outcome never change (fixture E01).
