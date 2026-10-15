# R17 adjudication specification (r17.adj.v1)

Normative for R17 scoring. **Part A** is the complete brief an adjudicator sees. **Part B** is the mechanical scoring that `fixtures/r17score.py` implements; adjudicators do not see it. **Part C** fixes the output format, denominators, disagreement handling and the fixture gate. If Part B and `r17score.py` disagree, that is a defect to fix before freeze; neither one silently wins.

Design choice (B3/B5): the only meaning judgment an adjudicator makes is the **target mapping**: which output units assert each reference target, and in which form. Everything downstream is mechanical, so both adjudicators score every item through the same deterministic rules, and the adjudicators never compute totals (R14 F7).

---

## Part A — Adjudicator brief (the only part shown to adjudicators)

### A1. Inputs and isolation

You receive exactly four things:

1. the source text (`parsed-body.txt`);
2. the frozen reference for that source (format: REFERENCE-SPEC.md §8, `r17.ref.v2`), in which you may ignore `rationale`;
3. one extraction output record: a JSON object with `units` (each has `id`, `assertion`, `evidence`, ...), `nodes` and `links`;
4. this Part A.

Work in a **fresh session** with no other context. Do not open other files, other outputs, other adjudicators' files or any scores. You will not be told which output format variant produced the record. Do not infer quality from structure. Your job is the mapping only.

### A2. The mapping task

For **every** reference target (`T1`, `T2`, ...), list the output units that **assert the same governed assertion** as the target. Each listed unit gets a `form`:

- `direct`: the unit asserts the target's assertion itself ("Comments must be received by the agency").
- `inverse`: the unit asserts the target's carve-out or negation as its own assertion ("Small vendors are exempt from the fee", when the target is "the fee [applies]"; "The rule does not apply to X").

Rules:

- **M1 Meaning first.** Map a unit only if its `assertion` text, read with its own evidence, states the target's assertion: the same action, the same actor or object, and the same modality direction (or exactly its negation or exemption, for `inverse`). Overlapping evidence alone is never enough.
- **M2 Evidence must touch.** A mapped unit's `evidence` spans must overlap the target quote or the quote of at least one of that target's relations. Never map a unit with no such overlap. If you think one should be mapped anyway, record a `mapping_doubts` note instead.
- **M3 Scope.** A unit whose assertion is **broader** than the target (for example the whole paragraph's gist) or **narrower** (for example the target with a condition folded into the assertion text) still maps if a reader of that unit would take it as making the target's assertion. Note the breadth in `mapping_doubts`. A unit asserting a **different** assertion (a different actor, action or object) does not map.
- **M4 Contradiction.** A unit asserting the **opposite** of the target without stating it as an exception (for example the target says hearings will be held and the unit says no hearing will be held) does not map. Record it in `mapping_doubts`.
- **M5 Several units.** List every unit that independently asserts the target (duplicates and restatements). Order does not matter.
- **M6 None.** If no unit asserts the target, give an empty list. That is a legitimate answer.
- **M7 Many-to-many.** One unit may map to several targets if it genuinely asserts each one.
- **M8 Do not judge conditions.** Do not look at whether the conditions, links or nodes are right. Map from the assertion and evidence only. Condition handling is scored mechanically after you finish.

### A3. Notes (never change scores)

- `mapping_doubts`: per-target notes when a decision was close.
- `reference_defects`: places where you believe the reference itself is wrong. These feed a sensitivity analysis only.
- `other`: anything else.

### A4. Output (exactly one JSON object)

```json
{
  "spec_version": "r17.adj.v1",
  "adjudicator": {"role": "A1", "model": "claude-fable-5-1", "effort": "high", "session": "<thread id>"},
  "call_id": "S1-OPQ",
  "source_id": "26-19-0xx",
  "output_sha256": "<given>",
  "reference_sha256": "<given>",
  "mappings": [
    {"tid": "T1", "units": [{"unit": 3, "form": "direct"}], "basis": "Unit 3 states that ..."}
  ],
  "notes": {"mapping_doubts": [], "reference_defects": [], "other": []}
}
```

Every reference target appears exactly once in `mappings`. `basis` is one or two sentences.

---

## Part B — Mechanical scoring (normative; implemented by `fixtures/r17score.py`)

### B1. Codepoint sets

`counted(c)` is true unless `c` is Unicode whitespace or separator (category Z*), punctuation (P*) or control (Cc). For a set of ranges, `cps(ranges)` is the set of counted codepoints.

For each reference relation `r`:

- `K_parts(r)` = `cps` of all PART quotes in `r.logic`;
- `K_markers(r)` = `cps` of `r.introducer` plus every `markers` quote at every level of `r.logic` (connectives, repeated introducers, negators, exception words);
- `K(r)` = `K_parts ∪ K_markers`. **Connectives and negators are required evidence for both arms** (B3).

For a logic node `n`: `K(n)` = `cps` of all quotes and markers in `n`'s subtree.

### B2. Witnesses (one subtree, no borrowed coverage)

A **witness** is `(link ℓ, path p)`, where `p` is a node path from `ℓ`'s root node to some node `v`. Every distinct path in the output graph is a separate witness. Its coverage is

`cov(ℓ,p)` = `cps`(ℓ's evidence ∪ evidence of every operator on `p` above `v` ∪ evidence of every node in `v`'s subtree).

Coverage never combines two links, two units or two paths.

A witness is **minimal for r** if no child extension `(ℓ, p+[c])` has text status at least as good and covers at least as many `K(r)` codepoints. Only minimal witnesses are candidates, so a containing operator cannot lend a clause a path that the clause does not actually occupy. For example, a clause sitting under an EXC carve-out is judged at that carve-out, not at the EXC's parent.

`U(t)` = the units the adjudicator mapped to target `t`, each with a form. The candidates for `r` are the minimal witnesses whose link's unit is in `U(r.tid)`.

### B3. Text status of a witness

- `complete`: `K(r) ⊆ cov`
- `lost_marker`: `K_parts ⊆ cov` but some marker codepoint is missing
- `partial`: some but not all of `K(r)` is covered (and not `lost_marker`)
- `absent`: `cov ∩ K(r) = ∅`

Quote occurrences are resolved by explicit offsets (REFERENCE-SPEC §2). Covering an **earlier** "or" never covers the reference's second "or" (fixture F14).

### B4. Role composition

Start from the link role and apply flips along `p`:

- the unit's form `inverse` adds one flip;
- each edge out of a `NOT` adds one flip;
- each edge into an `EXC` carve-out (child 2) adds one flip;
- edges out of `AND`, `OR` and `ALT`, and into an `EXC` base, add none.

A path is **explicitly uncertain** if the link has `q≠0`, any node on `p` (including `v`) has `q≠0`, or `p` passes through an `ALT`. Unit-level uncertainty does not count.

Role verdict for class `C`:

| role (after flips) | COND | RESTRICT | EXCEPT | IRRESPECTIVE |
|---|---|---|---|---|
| `qual` | hedged | hedged | hedged | hedged |
| `obj`, `acts` | hedged if uncertain, else **role_loss** | same | same | same |
| `if` (0 flips) | correct | hedged if uncertain, else **scope_change** | **inversion** | **inversion** |
| `onlyif` (0 flips) | hedged if uncertain, else **scope_change** | correct | **inversion** | **inversion** |
| `unless` (0 flips); `if`/`onlyif` with odd flips | **inversion** | **inversion** | correct | **inversion** |
| `unless` with odd flips (positive, strength indeterminate) | hedged if uncertain, else **scope_change** | same | **inversion** | **inversion** |
| `regardless` (any flips) | **inversion** | **inversion** | **inversion** | correct |

An even number of flips returns the original role, so double negation counts as the original role (fixture F08b). The wire prompt says `if` asserts neither sufficiency nor necessity. The table therefore never derives a role from Boolean implication; it only composes polarity, and any change of strength is a **scope_change** unless it is explicitly hedged (B4).

**Embedded.** If the witness node `v` is a single `L` leaf, `r`'s verdict there is not correct or hedged, the leaf also completely covers another live relation `h` of the same target, and `h`'s verdict through the same witness is `correct`, then `r`'s verdict there is `embedded`. The exception is kept verbatim inside the host condition's leaf, but it is not linked.

### B5. Relation verdict (precedence: the first rule that applies wins)

Contested relations are scored the same way and reported as `excluded_contested:<verdict>`. `UNRESOLVED` relations are excluded from the primary scores and reported in calibration (B8).

1. **No candidate covers anything.** If a witness on a unit **outside** `U` covers `K(r)` completely, the verdict is `wrong_target`; otherwise `absent`. An empty `U` falls here.
2. Otherwise pick the best candidate by: text status (complete < lost_marker < partial), then more `K(r)` covered, then role verdict (correct < hedged < embedded < scope_change < role_loss < inversion), then fewer **extraneous** codepoints (B6), then smaller coverage, then link index, then path.
3. Best is `partial` → **shortened**. Best is `lost_marker` → **lost_connective**.
4. Best role verdict is `inversion`, `role_loss` or `scope_change` → that verdict.
5. Another candidate is complete, has role verdict `inversion` and is **not** explicitly uncertain → **contradiction** (a contradictory extra applicability claim).
6. Best is correct or hedged and extraneous > 2 × |K(r)| → **broad**.
7. Otherwise the best role verdict: **correct**, **hedged** or **embedded**.

Verdict groups:

| group | verdicts |
|---|---|
| harmful | absent, wrong_target, shortened, lost_connective, inversion, role_loss, scope_change, contradiction |
| complete (text) | correct, hedged, embedded, broad, inversion, role_loss, scope_change, contradiction |
| acceptable | correct, hedged, embedded, broad |
| critical requirement met | correct, hedged, broad |

A **critical** relation therefore fails unless it is completely preserved on a mapped unit with a correct role, or with an explicitly uncertain non-assertive role (B4). Embedded, absent, wrong target, lost connective, inversion, contradiction and overconfident scope change all fail it.

### B6. Extraneous coverage

`extraneous(w)` = `|cov(w) − (K(target quote) ∪ ⋃ K(r') for all relations r' of the same target)|`. Text belonging to the same target's own assertion or its other relations is not extraneous.

### B7. Typed logic (FULL only; OPQ reports N/A)

**Compounds** are every `AND`, `OR` and `EXC` node in a live relation's logic tree (id `rid:nid`), plus every `carves_out_of` link (id `rid:exc`). A compound inherits `critical` and `contested` from its relation.

For an AND/OR/EXC logic compound `n` of relation `r`:

- If `r`'s verdict is not text-complete → `relation_failed` (not correct; its harm is already counted on `r`).
- Search operators `O` in the subtree of `r`'s best witness node that have the same number of children as `n`:
  - for an `EXC` `n` and an `EXC` `O`, ordered: base ⊇ `K(child1)` and carve-out ⊇ `K(child2)` → **correct**; reversed → **exc_reversed**;
  - otherwise, if `O` ∈ {AND, OR, ALT, EXC} and there is a one-to-one assignment of `O`'s children to `n`'s children with child-subtree coverage ⊇ `K(child)`: same operator → **correct**, `ALT` → **hedged**, different operator → **swap**.
  - Preference: correct > hedged > swap > exc_reversed.
- With no match: if some AND/OR/ALT/EXC operator in that subtree puts two different members of `n` in different children → **mismatch**; otherwise **flattened** (kept in one leaf: not typed-correct, not harmful).

For an exception_to compound (`r` carves out of `h`), using clause parts only, because introducers may sit on links or operators:

- an EXC reachable from a mapped unit with `K_parts(r)` in its base and `K_parts(h)` in its carve-out → **exc_reversed** (checked first);
- `r` not text-complete → `relation_failed`;
- an EXC with `h` in its base and `r` in its carve-out → **correct**;
- `r`'s best path enters an EXC carve-out whose base does not hold `h` → **wrong_base**;
- otherwise → **flattened**.

**Invented connective.** For each live, text-complete relation, look at the operators on its best witness path and in its best subtree. An `AND`, `OR` or `EXC` operator with `q=0` is **invented** unless one of these holds:

- it was matched to a reference compound by a rule above (including swap, mismatch, exc_reversed or wrong_base, so no operator is penalized twice);
- it is a cross-relation `AND` whose every child holds at least one whole reference relation and which joins at least two relations (the format allows one `if`/`onlyif`/`unless` link per unit, so separate conditions must be conjoined);
- it is an `EXC` whose base touches the target or holds a relation of the target, and whose carve-out holds an `EXCEPT` relation of the target.

Each invented operator is counted once, attributed to the lowest `rid` whose witness contains it, and is critical if any relation containing it is critical. Operators outside every selected witness are reported (M6b) but not scored.

**Typed harmful** errors are swap, mismatch, exc_reversed, wrong_base and invented.

### B8. Calibration (reported only)

For each `UNRESOLVED` relation, the result is `calibrated` if any complete candidate is explicitly uncertain or uses `qual`; `asserted` if candidates are complete but none is uncertain; otherwise `not_preserved`.

---

## Part C — Format, denominators, disagreement, fixture gate

### C1. Who scores what

- **A1**: Fable 5.1 (`claudeAgent` / `claude-fable-5-1`, high, claude.ai subscription), in a fresh session per output. It must not be any session that authored or reviewed a reference.
- **A2**: Opus 5.5 (`claudeAgent` / `claude-opus-5-5`, high, subscription), in a fresh session per output.
- **Both adjudicators independently map every target for every scored output.** There is no sampling, and A2 never sees A1's file or the reverse (B5).
- `r17score.py score` runs once per (output, adjudicator). That gives two complete, independent score sets per output.

### C2. Denominators (frozen at reference freeze, before any dispatch)

- **Relations:** all reference relations with `contested = false` and `class ≠ UNRESOLVED`, per source and pooled. Both arms use the same denominator. An item is never dropped because an output failed. A structurally failed cell (truncated, invalid or refused) gets **no** item verdicts and fails D1 directly. It is never scored as partial content.
- **Compounds:** all live compounds as defined in B7.
- The release record (PROTOCOL C6) publishes `N`, per-source `n_s`, `N_c`, the critical count and the required integer counts (PROTOCOL §11 table) before the first transport attempt.

### C3. Disagreement

- **Item level:** for every relation and compound, compare A1's verdict with A2's. Report the agreement count, the disagreement list and Cohen's κ over relation verdict groups. Reporting only; nothing is averaged or merged.
- **Bar level:** evaluate every bar (D for OPQ; D and T for FULL) **separately** under A1's scores and under A2's.
- **Outcome level:** PROTOCOL §11 combines the two bar results. The OPQ default needs both adjudicators to pass OPQ. If they split on OPQ, the outcome is O4 (inconclusive). The typed layer needs both to pass FULL. If they split on FULL, the outcome is `O1-disputed`: the clause-only default stands and the typed layer is not adopted. No hybrid or best-of score is ever computed.

### C4. Fixture gate (before any reference is authored)

1. `python3 -I -S -B fixtures/check.py` exits 0. Every expected judgment in `fixtures/cases.json` is reproduced.
2. A1 and A2, each in fresh sessions that see only Part A plus each fixture's source, reference and output (never `expected`), produce adjudication files for every scorer fixture case. `check.py --adjudications DIR` must report **zero** failures: every mapping equals the expected mapping exactly (units **and** forms), so every verdict matches.
3. If either adjudicator fails, revise Part A's wording only, never the expectations, and rerun both in new sessions. After two failed rounds, stop and escalate to the primary. The protocol cannot freeze.
4. Freeze `ADJUDICATION-SPEC.md`, `r17score.py`, `cases.src.json`, `cases.json` and `check.py` by SHA-256 in the release record.
