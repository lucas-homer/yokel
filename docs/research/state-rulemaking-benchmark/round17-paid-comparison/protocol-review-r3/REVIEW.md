# R17 adversarial protocol review — round 3

**Verdict: freeze after edits.** Two reproducible scoring defects can change this six-call experiment's research-default decision. Neither requires redesign. Do not freeze r3 as written. The user's eventual P-HARD/P-ACCEPT choice is separate from this verdict; no policy choice is made here.

Reviewed offline on 2026-10-13 against `design-r3/READY.primary.json`. All **11 pinned hashes match**. Paths below are relative to R17 unless stated otherwise.

## Evidence and boundaries

Executed with `python3 -I -S -B`:

- `design-r3/fixtures/check.py`: **0 failures**; 63 scorer cases, 62 gold cases, 9 invalid references, 9 reference examples, 15 decision checks, 18 ledger checks, 13 assembly checks, 10 gate self-tests. Actual adjudicator gate: **not run**.
- `protocol-review-r3/probe.py`: all assertions pass. It ports every round-2 probe scenario to r3's schema/API, with assertions for the repaired behavior, and adds the counterexamples below. The old probe asserts *incorrect r2 behavior*, so running it unchanged would neither target r3 nor constitute an acceptance test.
- Both blocker examples also pass the **frozen r16.w2.1 `validate_response`**, using its unchanged request plan. Each is assembled into six wire-validated fictional outputs, bound to both adjudicators' synthetic envelopes, and passed through **`decide`**. Both produce **O2**. These are executable counterexamples, not actual adjudicator responses or paid results.

No network/provider calls, credentials, installs, commits, or R17 source-text reads. No `parsed-body.txt`, original HTML or attempt bodies were opened. Read only protocol/code/metadata and fictional fixtures, including the existing R15 fictional control used by `check.py`. Wrote only this review directory. The synthetic runs use 12 relations, 9 compounds, four live relations and a RESTRICT per source, with plausible synthetic token counts; they meet the experiment's E8 count gates. They make no claim about the unread selected notices.

## Round-2 disposition

FIXED means the identified design defect is repaired, not that future execution prerequisites have happened. PARTIAL identifies a remaining enforceability or scoring gap, not rejection of the accepted narrowing.

| R2 finding | Status | Re-review evidence |
|---|---|---|
| **B1 — cap/reconciliation** | **PARTIAL** | Policy variants now state their premises honestly; cumulative lag/catch-up and persistent-zero probes behave correctly. P0 is fail-closed in text, but its executable release predicate is absent (R3-S1); reconciliation misses an intra-poll regression (R3-S3). The policy choice itself remains solely the user's. |
| **B2 — polarity/typed structure** | **PARTIAL** | False NOT under AND now gives `inversion` / `relation_failed`; T4 fails. Faithful explicit NOT now gives `correct`. Nested reparenting fixtures pass their rejection expectations. A second confident, wrong typed claim still escapes the best-witness scope (R3-B1). |
| **B3 — extra claims/wrong leaf** | **PARTIAL** | Whole-clause link evidence over the wrong leaf gives `shortened`; added confident `if` beside `onlyif` gives `contradiction`. The new `opposite` mapping still permits an outright reversed assertion to score correct (R3-B2). |
| **B4 — adjudicator fixture gate** | **FIXED** | F05b is mutation-only; all 62 gold cases have assertions/evidence; zero adjudicators is rejected; A1/A2 identity, exact normalized mapping and freshness are checked by the fixture gate. Actual gate execution remains P5. |
| **B5 — reference partition** | **FIXED** | Removing F09's `not` fails the exact partition check (three missing counted codepoints); orphan target rejected. Declared clause/exclusion fidelity is explicitly left to source-only review. Removed `carves_out_of` needs no cycle checker. |
| **S1 — ledger hash cycle/admission** | **FIXED** | INIT → release record → BIND_RELEASE is acyclic; admission precedes RESERVE; unresolved/reconciliation guards and crash rules are explicit. L01–L18 pass. Adapter durability remains the stated P3 prerequisite. |
| **S2 — segmentation** | **FIXED** | Deterministic explicit-structure rule, named UNRESOLVED fallback, separate/internal exception test, target-reference exclusions and whole restricted-population examples resolve the contradictions. Scoped limitations below. |
| **S3 — binding/denominators** | **PARTIAL** | `decide` now checks hashes, source/call identities, exact relation/compound sets and flags, both models, states and tokens; A02–A08 reject. Unlike the fixture gate, it does not reject reused adjudicator sessions (R3-S2). |
| **S4 — stopping/reporting** | **FIXED** | Complete vs reachable/unreachable states, O1-disputed boundary, early O4/O1, κ, M6b and sensitivity definitions are explicit; supplied decision/assembly tests pass. Acceptance of a malformed post-halt history is noted separately below. |

**5 FIXED; 4 PARTIAL; 0 NOT FIXED.** All original executable semantic counterexamples are repaired. The two blockers below are additional counterexamples against the revised design.

## BLOCKER

### R3-B1 — A correct claim hides a confident AND→OR duplicate, allowing O2

**Location:** ADJUDICATION-SPEC B5.5a/B7; `fixtures/r17score.py:514`, `:568`, `:606`.

Start with F15b: “Guards must report if a door is open and a lamp is out.” Keep its correct `if → AND(A,B)` claim. Add a second unit asserting the same target, with its own `if → OR(A,B)` graph and exact evidence. Both units map `direct` under M5; both claims are confident. Each unit has only one `if`, so this is wire-valid.

**Observed:** relation `correct`; critical compound `correct`; `invented=[]`; the wrong OR is merely listed under `unscored_operators`. The relation audit checks polarity/role but not this operator swap. Typed scoring and invented-operator auditing examine only the winning claim's scope.

The twelve-relation/nine-compound six-cell reproduction returns **O2 with every T bar true under both adjudicators**. Removing the masking correct copy, leaving the same wrong OR, changes `decide` to **O1**. The full six-output reproduction survives actual frozen wire validation.

**Why it meets the blocker bar:** duplicate/restated assertions are explicitly supported, and a model can decompose those restatements inconsistently. One confidently wrong critical AND/OR claim should fail T5 even when another copy is right. This changes whether FULL becomes the next research default; it is not a production-only concern.

**Suggested edit:** preserve the winning witness for coverage/credit, but audit typed semantics of every additional complete, confident applicability claim on mapped units. Charge an incompatible swap/reversal/mismatch on a critical relation as critical typed harm (or an explicitly defined contradiction), once per offending assertion/operator. Keep compatible duplicate graphs and genuinely unscored unrelated operators harmless. Add correct+wrong duplicate and correct+correct duplicate fixtures, including a `decide` outcome assertion. Do not solve this by declaring every outside-witness operator harmful.

### R3-B2 — `opposite` plus `regardless` erases reversal of the target itself

**Location:** ADJUDICATION-SPEC B4 (`regardless (any)`), B5.5b; `fixtures/r17score.py:323`, `:406`, `:468`.

Start with F19: “Tolls apply to every wagon regardless of the driver's age.” Change the sole output assertion to **“Tolls do not apply to any wagon.”** Map it `opposite`, retaining the complete age clause and its confident `regardless` link.

**Observed:** `polarity=1`, but verdict **`correct`**. `role_verdict` leaves the `regardless` polarity unchanged by every flip. The complete linked clause also exempts the unit from `unqualified_opposites`. Thus neither mechanism charges the reversed assertion. This is not the legitimate F05d exception reformulation.

In the full reproduction, this is a critical fee-applicability relation in OPQ1, labelled under REFERENCE §5 (F19's original fixture flag is noncritical). All references, manifests and both mapping envelopes agree. **`decide` still returns O2**, including after wire validation of all six outputs. A critical reversed OPQ assertion should fail D4 and prevent adoption, ordinarily stopping at OPQ1 with O3 when both mappings agree.

**Why it meets the blocker bar:** IRRESPECTIVE is a scored class, and `notwithstanding`/irrespective clauses are expressly in scope. Correctly identifying an opposite assertion must not turn that assertion into a correct result merely because its age/weather/etc. factor is irrelevant.

**Suggested edit:** distinguish reversal of the target assertion (`form`) from negation of an irrelevant clause component. An `opposite` target joined by `regardless` cannot be correct for the positive IRRESPECTIVE target. Preserve direct-form `regardless` under irrelevant-factor negation, and retain legitimate inverse exception cases. Add direct/opposite IRRESPECTIVE fixtures and a critical OPQ `decide` rejection/failure case; align B4 and Python.

## SHOULD-FIX

### R3-S1 — UNSET is blocked by specification, not by the executable admission fixture

**Location:** BUDGET §0/§4.3–4; PROTOCOL P0/P3/P7; `r17recon.py:59`.

With six required calls, zero usage, limit $1.73, `INIT.release_policy='UNSET'` and a BIND_RELEASE entry, **`admit` returns `(True, None)`**. P-HARD/P-ACCEPT without policy evidence behave identically. The L fixtures omit the policy altogether. This does **not** demonstrate an actual dispatch bypass: the adapter does not exist, and the separately required dispatch gate must verify P0 and C6. It does show that conformance to L01–L18 cannot establish the requested mechanical UNSET prohibition.

Both variants are internally consistent as conditional release specifications: P-HARD requires accepted E-1/E-2 evidence; P-ACCEPT requires the user's explicit residual-risk acceptance; both retain the same key and ledger safeguards. No choice or further argument about their merits is needed.

**Suggested edit:** add a pure, pinned release-validation predicate and mandatory P3 tests for UNSET/missing/unknown policy, policy disagreement between artifacts, and missing/wrong policy evidence. Reject UNSET in `admit` as defense in depth, or explicitly require validated release state as input. Evidence acceptance is a recorded human decision, not something the money-arithmetic helper can infer. The future socket gate must fail these tests before release; selecting a policy alone never passes them.

### R3-S2 — Paid adjudication freshness is weaker than fixture-gate freshness

**Location:** `r17score.py:894`; compare `check.py:479`; PROTOCOL §10 and ADJ C1.

Set every A1 paid-output envelope to the same A1 session ID, and every A2 envelope to the same A2 session ID, preserving correct models and hashes. The six-cell run still returns **O2**. This directly detectable cross-output context reuse violates the required fresh session per output, even though the fixture gate rejects the analogous condition. No actual session reuse or independence breach was observed in this review.

**Suggested edit:** require all scored-output session IDs to be unique across roles and calls. Bind forbidden reference-author/reviewer session IDs and the frozen OPQ adjudication hashes into a run-level evidence manifest where available. Add reused-session and changed-frozen-OPQ rejection tests. This prevents routine orchestration mistakes; it need not claim cryptographic proof of isolation.

### R3-S3 — Reconciliation ignores regression between polling reads

**Location:** BUDGET §5 RECON.3–4; `r17recon.py:119`.

For attempt 2, prior reconciled usage $0.10, cumulative reported $0.16, reads at 0/60/300 seconds of **$0.15 → $0.14 → $0.16** produce `RECONCILED, 160000000`. The text says a decreased U halts immediately, but Python compares each read only with the previous *call's* $0.10 baseline. The caught-up result does not undo the observed regression.

**Suggested edit:** retain the largest valid usage observed during the polling sequence and halt on any subsequent lower read; add this fixture. This is below BLOCKER here: it changes anomaly handling, but the reproduced sequence does not itself establish excess spend under either selected policy.

## NOTE

- **Narrowing is coherent, with a narrower claim.** Removing NOT from the compound denominator does not remove its relation-polarity checks; unacceptable relations do not shrink the frozen compound denominator (`relation_failed` remains an item). Dropping `carves_out_of` removes cross-relation attachment credit; plain subject qualifiers now belong to targets; UNRESOLVED grouping leaves primary denominators. Frozen E8 floors and independent reference review prevent adjusting those choices after seeing outputs. **Edit:** keep final adoption language explicitly limited to declared live relations and AND/OR/EXC compounds. Do not describe O2 as validation of all scope qualifiers or all cross-relation attachments. The broad-target mapping rule M3 is not a separate test of every qualifier moved into a target.
- **`opposite` with `qual`.** Adding a complete uncertain `qual` link to F05c's opposite unit changes `contradiction` to `correct` via its other, good unit. The present rules permit this because qualification need not assert applicability and uncertain alternatives are tolerated. Unlike R3-B2, whether this is unacceptable depends on the intended interpretation of a hedged qualification. **Edit:** explicitly state whether `qual` suffices to discharge an otherwise unqualified denial and add a fixture; do not silently infer unit-level uncertainty from it.
- **Post-halt record validation.** A six-cell record with S2-FULL halted but S3-FULL still released is accepted as O1-incomplete. The outcome is conservative, and the live adapter's HALT guard remains mandatory, so this is not evidence of actual additional spend. **Edit:** reject any released call after a terminal halt in the six-call order; test both final and interim assembly. Prefix ordering around unrun cells is insufficient to check this history.
- **Partition limits are now honest.** A reference author could still misdeclare a clause or misuse an exclusion, but that is explicitly E5's semantic-review job. No additional blocker follows from the checker being unable to infer the entire correct reference from raw text. Keep the source-only review prerequisite.

Freeze after the two scoring edits and their regression checks; address the small executable-gate mismatches before paid release. P5, reference freeze, policy selection/evidence, key verification and P3 remain mandatory future prerequisites, not approvals supplied by this review.
