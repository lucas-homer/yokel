# Disposition of the R17 protocol re-review, round 2 (design r3)

Review: `../protocol-review-r2/REVIEW.md` (GPT-6 Astra, high; verdict "freeze after edits"), with `../protocol-review-r2/probe.py`, against `../design-r2/` (frozen, unchanged; its READY hashes still verify and the r2 probe still passes against it). Revised files are in this folder. No provider call, network access, credential access or R17 source-text read occurred.

**Counts: 9 round-2 findings (5 BLOCKER, 4 SHOULD-FIX) and 4 rulings.** 9 accepted. One of them (R2-B1) is accepted for every mechanism, but its release policy is left to the user as a two-variant slot, as instructed. 3 are accepted with a narrowing modification (R2-B2, R2-B5, R2-S2). 0 rejected. All 4 rulings applied.

Round-1 items the review left PARTIAL are closed through their round-2 successors: B1 → R2-B1; B3 and B4 → R2-B2 and R2-B3; B5 → R2-B4.

## Verification evidence (offline, `python3 -I -S -B` only)

- `fixtures/check.py`: **0 failures**. Scorer checks by section: 63 scorer cases (62 adjudicator gold, 1 mutation), 9 invalid references, 9 canonical reference examples, 15 decision fixtures, 18 ledger fixtures, 13 `decide` assembly runs, 10 gate self-tests. Adjudicator gate: **not run** (P5 needs real A1 and A2 sessions).
- A mutation pass flipped each of 192 expectations (relation, compound, invented, decision, outcome, ledger, assembly); every flip was caught.
- Every `probe.py` scenario, replayed with its exact mutations against the r3 scorer:

| Probe | r2 (pinned defect) | r3 |
|---|---|---|
| reference missing `not` | accepted; lost negator became `correct` | **rejected**: partition differs by 3 codepoints (V03) |
| false NOT under AND | relation correct, compound correct, no invented | **inversion** (mixed polarity), compound `relation_failed` (F15e) |
| false NOT lifted to T | T1–T6 pass | **T fails** (T1, T3, T4; T03) |
| whole clause on link, leaf = target | correct | **shortened** (F01d) |
| faithful `if → NOT('not') → leaf` | inversion | **correct**, NOT supported (F09b) |
| correct `onlyif` + extra `if` | correct | **contradiction** (F10g) |
| F05a/F05b same packet, opposite forms | both gold | F05b is a **mutation case**, never shown to adjudicators; the gold-consistency check rejects it if marked gold |
| units missing assertion/evidence | 34 of 35 | **0** of 62 gold cases |
| zero adjudicator directories | 48 checks, 0 failures | **fails**: "must be exactly ['A1', 'A2']" |
| orphan target | accepted | **rejected** (V05) |
| AD6 lag then catch-up | call 2 fails | **reconciled** cumulatively (L09); a stale zero now **halts** (L10) |

## Simplicity: where narrowing replaced machinery

The experiment is 6 calls on 3 sources. These fixes narrow what is scored instead of adding judgment:

1. **`carves_out_of` and its compound are removed.** An exception to the target is a separate EXCEPT relation; an exception to something named inside a clause is an EXC node (REFERENCE-SPEC §4.2 rule 5). This deletes a discretionary reference field, its cycle and validity checks (R2-B5), the `exc_verdict`/`wrong_base` scorer path, and the internal-vs-separate ambiguity (R2-S2). The scorer still checks a wrong-base EXC: it is an invented operator (F18).
2. **RESTRICT needs exclusive wording.** Bare qualifiers and relative clauses are part of the target (rule 7), so the "Only vendors with stalls" ambiguity and the discretionary "restrictive qualifier" relations disappear (R2-S2).
3. **NOT is not a compound.** NOT semantics are scored once, on the relation, by reference-relative polarity. An unsupported NOT is an invented operator. No NOT matching machinery was added (R2-B2).
4. **Typed structure is scored only where the reference declares a compound, and only when the relation itself is acceptable.** Otherwise the compound is `relation_failed`, and invented operators are checked only inside acceptable relations. A semantic error is therefore charged once, on the relation (R2-B2).
5. **Clause parts are credited only from leaves.** Link and operator evidence count only toward markers (R2-B3). This replaces the r2 "minimal witness" rule, which is deleted: polarity is now computed per claim, so a containing operator cannot lend an uninverted path.
6. **Ambiguous connective grouping is UNRESOLVED**, not a discretionary PART fallback (R2-S2). It leaves the denominator.
7. **The per-output `score` CLI is removed.** `decide` is the only decision entry point, so no partial helper can be mistaken for the gate (R2-S3).

Machinery added only where narrowing could not fix a defect: per-component polarity (B4), the extra-claim audit and the `opposite` form (B5.5), the declared-clause partition (REFERENCE-SPEC §4.2 rule 8), `decide`, the two-adjudicator gate, and `r17recon.py`.

## BLOCKER

### R2-B1. The hard cap was conditional; lag handling was not fail-closed — ACCEPTED (mechanics); policy left to the user

Mechanics (rulings 3 and 4):

- **Policy slot** (BUDGET §0; PROTOCOL P0): `RELEASE_POLICY = UNSET`, with two complete variants. While `UNSET`, nothing is released. The design does not pick a variant and does not infer acceptance of a conditional budget from approval of a hard cap.
- **No "guarantee" for admission-time enforcement.** r2's K-HARD/K-ADMIT branch and "The guarantee is §1" are deleted (BUDGET §7). BUDGET §3 now says the cap is hard only under P-HARD via E-1 or E-2.
- **Non-resetting key with a verified limit** `R0 × FLOOR ≤ L ≤ $1.73` and a checked reset policy (BUDGET §1 K2–K3). A limit below six floors fails (L04, L18).
- **Cumulative, bounded reconciliation** replaces AD6 (BUDGET §5 RECON; `r17recon.reconcile`): the zero baseline is pinned; usage `U` is compared with cumulative reported `C`; reads happen immediately and at 60, 300 and 900 s; the tolerance is `i × 1,000` nanoUSD; nothing is dispatched until reconciled; a stale zero waits and then halts; regression, a limit or reset change, or excess usage halts immediately; `KEY_USAGE_UNRECONCILED` → HALT (P in OPQ, O1-incomplete in FULL; fixtures L08–L15, A12, A13). Other debit terms record the halted attempt and never justify another admission. Run close retains `max(Σ debits, highest usage)` (L16).
- **Key capacity in admission:** `U + R × FLOOR ≤ L` alongside the operating limit (BUDGET §4 rule 4).

The two variants, as written in BUDGET §0:

- **P-HARD.** "Release only if documented charge-time enforcement, or a genuine pre-dispatch all-in upper bound, is established; otherwise the paid phase stays unreleased." E-1 and E-2 define "established", with pinned documentation captures and acceptance by the re-review.
- **P-ACCEPT.** "Release under the dedicated $1.73-limit key, with the user's explicit written acceptance that the bound is conditional, recording the stated residual risk." The acceptance must include the residual-risk statement quoted in BUDGET §0.

### R2-B2. Typed scoring was coverage matching and treated NOT asymmetrically — ACCEPTED, narrowed

- **Reference-relative polarity** (ADJUDICATION-SPEC B4; `Scorer.claim`). For every clause-part codepoint and every root-to-leaf path that carries it, `form_flip + path_flips + intact − |S(x)|` (mod 2) must take a single value. The reference's own negations (NOT ancestors, EXC carve-outs, PART negators) are counted, and an intact leaf keeping a negator as its own wording counts as that negation, not as a second flip. One value gives the role-table verdict; two values mean a component's polarity is wrong → `inversion`.
- **Fixtures, positive and negative:** a faithful explicit NOT (F09b, F22a, F23a), an intact negator (F09c, F22c, F23c), double negation (F09d, F23d, F24c wrong; F24a correct), local vs whole-clause negation (F22b, F23b wrong), the false NOT under AND (F15e), and an unsupported parity-neutral double NOT (F16b, invented).
- **Nesting:** an output child matches a reference child only if it carries **exactly** that child's clause parts, so reparenting is a mismatch (F25b) while a correctly nested or partly flattened tree is credited (F25a, F25c).
- **Unmatched operators including NOT** are invented unless supported (B7). A NOT is supported if its own evidence cites a reference negation word or an EXCEPT introducer of the target.
- **Modification (narrowing):** NOT is not a compound (simplicity 3), and compounds are scored only when their relation is acceptable (simplicity 4).

### R2-B3. Best-witness scoring masked extra scope errors and allowed clause evidence on the wrong leaf — ACCEPTED

- **Leaf-only clause content** (B2): clause parts are credited only from leaf evidence; link and operator evidence satisfy markers only. Whole-clause link evidence over an unrelated leaf → shortened (F01d). Broad operator evidence over fragmentary leaves → shortened (F01e). The same operator evidence is harmless over complete leaves (F01f).
- **Extra-claim audit** (B5.5a): every other claim that carries the complete clause parts, uses an applicability role and is not explicitly uncertain is checked. An `inversion` or `scope_change` on any of them → `contradiction`, critical if the relation is critical. Fixtures: an extra `if` (F10g), a correct-plus-harmful duplicate unit (F10i), an extra `unless` (F11a). **Compatibility rule:** `obj`, `acts` and `qual` assert no applicability and are compatible (F10h); an embedded copy is compatible (F12b); an explicitly uncertain alternative is compatible (F11b).
- **Contradictory units now affect harm** (B5.5b): Part A M4 maps a flat denial as `opposite` instead of dropping it into notes. An `opposite` unit with no link carrying a complete clause of the target is an unqualified denial → `contradiction` (F05c). A denial that links the clause is scored as a claim (F05d).

### R2-B4. The adjudicator gate was infeasible and accepted zero adjudicators — ACCEPTED

- **Scorer mutation tests are separated from gold packets.** `gold: false` cases (F05b) are never shown to adjudicators. All 62 gold cases carry unit `assertion` and `evidence`. `check.py` verifies that every gold mapping obeys M2 and that identical packets have one gold mapping, so F05a/F05b-style contradictions are rejected mechanically.
- **Blind packets** (`--emit-packets`): Part A, source, reference, output and four binding values under an opaque id and opaque `source_id`. They never include the case name, purpose, expectations or mapping. (The descriptive case ids would have hinted at answers; this was found and fixed during r3.)
- **Strict gate** (`--adjudications`): exactly `A1/` and `A2/`, each with exactly one file per gold packet, the pinned role, model and effort, a session id used nowhere else, the echoed bindings, and exact agreement on (target, unit, form). `basis` and notes are ignored. Zero, one or three adjudicators fail, as do a missing case, a wrong model, a reused session, a wrong hash and a wrong mapping (gate self-test, 10 scenarios).
- **Counts are reported separately** (scorer sections vs `adjudicator_gate`). The gate is "not run" until real sessions exist.
- **Repairs:** a reviewed, recorded fixture correction is allowed before freeze, then both adjudicators rerun the whole gate (ADJUDICATION-SPEC C4.5).

### R2-B5. The reference checker could not enforce the promised partition — ACCEPTED, narrowed

- **Declared clause and justified exclusions** (REFERENCE-SPEC §4.2 rules 8–9; schema `r17.ref.v3`): each relation lists its `clause` spans and `excluded` quotes (reason `target_reference`, `citation` or `aside`, with a note). `validate_reference` requires the counted codepoints of the clause to equal the disjoint union of introducer, markers, parts and exclusions, and the clause not to touch its target quote.
- **Other promised constraints are now mechanical:** orphan targets, field types (booleans, strings, gloss length, identifiers), operator markers, PART and marker content, arity and nid uniqueness.
- **Invalid-reference fixtures:** missing middle negator (V03, the probe), missing final words (V04), orphan target (V05), field type (V06), exclusion reason (V07), target words in clause (V08), operator without a marker (V09).
- **Modification:** `carves_out_of` is removed (simplicity 1), so its cycle and same-target checks are unnecessary. Human review still verifies that the declared clause and exclusions are faithful (PROTOCOL E5); the checker states that limit (REFERENCE-SPEC §7.2).

## SHOULD-FIX

### R2-S1. Ledger/release hash cycle; admission-state ambiguity — ACCEPTED

- **No cycle:** `INIT` pins static configuration only; the release record pins the `INIT` entry hash; `BIND_RELEASE` pins the release record before any `RESERVE` (BUDGET §4 rule 3; L07). The hashed byte sequences are defined exactly (rule 2).
- **Admission before `RESERVE`, under the lock, with no unresolved attempt and no unreconciled dispatch** (rule 4). The pending reservation is no longer double-counted (L02). Key capacity is included.
- **Recovery:** a no-mark crash resolves at 0 and may be re-admitted (rule 6, L06); a mark without a resolution reconciles, resolves conservatively and halts (rule 8); a torn tail goes to a sidecar, the ledger is truncated, `RECOVER` is appended, and the run fails closed (rule 9); the lock is never broken automatically (rule 10); directory fsyncs are required (rule 11). Still no retry after a mark (L05).
- **Rule 9 corrected (now rule 13):** any debit term over FLOOR, including a key-usage excess while AD4 passes, halts.

### R2-S2. Contradictory or discretionary reference segmentation — ACCEPTED, narrowed

- Rule 4 has one answer: every explicit structure word is a typed node, except a negator of a single component's own predicate. Unclear grouping makes the relation UNRESOLVED (`grouping unclear:`), the named uncertainty condition.
- Rule 5 gives an operational test for a separate EXCEPT relation vs an EXC node, with `attachment unclear:` defaulting to the separate relation.
- Rules 6 and 8 no longer conflict: target-naming words go in `excluded` (`target_reference`), never in a PART. Rule 6 states when a noun phrase may stand for an implied assertion (6.2, gloss `implied: `) and how to record an unresolvable attachment without inventing a target (6.3).
- Rule 7 requires exclusive wording for RESTRICT and keeps the head noun in the restricted population ("vendors with stalls").
- "Never choose a segmentation to change how many relations or logic nodes there are" (§1). The author never sees the compound floor (E2).
- Source-only canonical examples X01–X09, all wholly fictional and paired (X01/X02, X03/X04, X05/X01's R3, X06/X09), are in REFERENCE-SPEC §9 and checked as `reference_examples`, separately from the extraction fixtures.

### R2-S3. Binding and denominator checks must be executable — ACCEPTED

`r17score.py decide` (ADJUDICATION-SPEC C5) verifies source, reference, output and adjudication hashes; the exact live relation and compound id sets and critical flags against the frozen manifest; both adjudicator identities; allowed response states; call ordering; and nonnegative integer token counts. Only then does it compute bars, building cells from the manifest's ids. Rejection fixtures: swapped output (A02), wrong reference hash (A03), omitted relation (A04), missing adjudicator (A05), wrong identity (A06), negative tokens (A07), pending call in a final decision (A08).

### R2-S4. Exact stopping-state definitions — ACCEPTED

- Per-adjudicator phase states are `pass`/`fail` (scored complete) or `unreachable`/`reachable` (best case at an early stop). `reachable` is never a pass (PROTOCOL §8). `outcome()` rejects stops with no `unreachable` bar and mixtures of complete and best-case states (O02).
- An early OPQ split (`unreachable` vs `reachable`) is O4. Early FULL futility is O1. O1-disputed requires both FULL assessments to be complete (O01, O02, A11).
- `decide --interim` is the staged futility test (A09, A10).
- κ uses five mutually exclusive categories, as an exact fraction, undefined when p_e = 1 (ADJUDICATION-SPEC C3; K01).
- M6b `unscored_operators` is produced by the scorer.
- E10 sensitivity is defined (drop each flagged live relation, then all at once; recompute per adjudicator; report only) and implemented as `drop_relations` (C6; E01).

## Rulings applied

1. **O1-disputed:** kept. It requires both FULL assessments to be complete; OPQ adoption stands and FULL is neither adopted nor declared inferior (PROTOCOL §11).
2. **Screen:** "gives no advantage to either arm" is replaced by "uses the same selection rule for both arms; differential effects of this selected distribution are unmeasured" (PROTOCOL S6).
3. **$1.73 arithmetic:** six floors ($1.62) fit under $1.73 conditionally. The key limit must satisfy `R0 × FLOOR ≤ L ≤ $1.73` and enters admission. "≤ $1.73" alone is not treated as enforcement (BUDGET §0–§1, §4).
4. **Lag:** cumulative reconciliation with reads at 0/60/300/900 s, then HALT; no silent fallback for admission (BUDGET §5).

## Open issues

1. **`RELEASE_POLICY` is UNSET (blocking; user decision).** Under P-HARD the paid phase stays unreleased unless E-1 or E-2 is established; the primary's documentation check found no E-1 statement.
2. **Key endpoint details.** The usage field name and units on `GET /api/v1/key` are unconfirmed, and the `i × 1,000` nanoUSD tolerance is a policy that may need amending to the documented granularity.
3. **Equivalent typed rewrites are not credited.** `AND(A, NOT B)` for a reference `EXC(A, B)`, or De Morgan forms, score as swap or mismatch. The r2 role-table choice that `unless` with odd flips has indeterminate strength is retained (e.g. "No hearing unless X" scores `scope_change` against a COND).
4. **Gate feasibility is unproven until A1 and A2 run.** The inverse/opposite boundary (F05a, F05c, F05d) and duplicate restatements (F10i) are the likeliest disagreements. C4.5 allows a reviewed fixture correction.
5. **Narrowing lowers counts.** Removing the `carves_out_of` compound and sending ambiguous groupings to UNRESOLVED can lower `N_c` and `N`, raising the chance of `O1-untestable` or an E8 replacement. This is accepted as the cost of removing discretion.
6. **The adapter (P3) does not exist yet.** `r17recon.py` is reference semantics that the adapter must match. Durability rules (fsync, torn tail, lock) are specified but untested until P3.
7. **Unchanged limitations:** self-recorded retrieval chronology (F10), local-record reference chronology (E7), and no invoice verification.
