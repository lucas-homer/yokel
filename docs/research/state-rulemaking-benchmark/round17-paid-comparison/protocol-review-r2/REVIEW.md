# R17 adversarial protocol re-review, round 2

**Verdict: freeze after edits; do not freeze or release design-r2 as written.** The staged comparison remains viable. Restoring conservative accounting and complete adjudication helped substantially, but the hard-cap fallback is still conditional, and executable counterexamples defeat the semantic and fixture gates.

Reviewed offline, 2026-10-13. Paths below are relative to R17; line numbers refer to the pinned r2 files. All ten `design-r2/READY.json` hashes matched. No network/provider calls, credential access, source-text reads, installs or commits. Only this directory was written. R17 `parsed-body.txt`, HTML, attempt bodies and source-derived anchors were not read. Fictional scoring fixtures, including the pinned R15 fictional control used by `check.py`, were read.

## Verification

Executed only with `python3 -I -S -B`:

- `design-r2/fixtures/check.py`: **48 checks, 0 failures**; cases hash `056a49d9ebafdb0c766de2f1f4a5ffb22af34f78ab6ca70f0baecbcce0a0ef63`; scorer hash `a39e31d9e84692a69c09128f9646d781a901f55ec8b546efad2f7e758b7bcd14`.
- `protocol-review-r2/probe.py`: all assertions passed, reproducing the defects described below. These assertions pin **current incorrect behavior**, not acceptance expectations. The script reads fixtures/specifications and screen code only and writes nothing.
- Both screen-script copies match the first-run pinned hash `f3c43e7e2a3ee53aeab11a6769018c322e319d7ab1de367c0727378756d7cc8b`.

No adjudicator sessions were run. Passing the existing checks proves conformance to those expectations, not semantic correctness or inter-adjudicator agreement.

## Round-1 disposition verified

“FIXED” here means the particular design defect is addressed; it does not certify that future release prerequisites have been executed.

| Finding | Status | Evidence and remaining issue |
|---|---|---|
| B1 Hard cap | **PARTIAL** | BUDGET §1 introduces a dedicated key and fail-closed gate; §5 adds missing anomaly checks. K-ADMIT still relies on unverified CN1–CN5 while §3 calls §1 a guarantee. See R2-B1. |
| B2 Floor and retries | **FIXED** | BUDGET §4.2–7 restores `max(FLOOR, …)`, pending reservations, remaining-call funding and no retries; PROTOCOL C4 agrees. Ledger construction/admission details still need R2-S1. |
| B3 Coverage and semantic paths | **PARTIAL** | ADJ B1–B7 adds required markers, single/minimal witnesses and composition. Coverage can still mask incorrect semantics, and correct NOT structure is penalized: R2-B2/B3. |
| B4 Critical omissions/errors | **PARTIAL** | PROTOCOL D4 and `bar_D` correctly reject the original critical-absence counterexample. However, critical false-correct verdicts and masked extra scope changes still pass: R2-B2/B3. |
| B5 Complete second adjudication | **PARTIAL** | ADJ C1–C3 and PROTOCOL §§10–11 remove sampling and hybrid scores. The O1-disputed modification is sound. The purported mapping-agreement gate is impossible as specified and can vacuously pass: R2-B4. |
| S1 Order/futility | **FIXED** | PROTOCOL C1, P9, §8: OPQ first, stop on irreversible failure, skip untestable FULL, no inference that OPQ truncation predicts FULL. Early-stop outcome wording needs R2-S4. |
| S2 Failure classes | **FIXED** | PROTOCOL §7 has an ordered response-state table, no retries, distinct auth/payment/rate-limit/schema states and retained debits. |
| S3 Independence/precedence | **FIXED** | PROTOCOL E1–E7 enumerates isolated packets, prohibits outside reads, retains exchanges, binds hashes and expressly disclaims cryptographic chronology. No actual reference leak found. |
| S4 Selection/screen | **FIXED, modified** | PROTOCOL F8/F10, S6–S7/E8 and matching screen hashes support the bounded, exception-enriched selection with disclosed prior exposure and locally recorded chronology. Accept item 2 below; remove the overclaim of arm neutrality. |
| S5 Noise/thresholds | **FIXED** | PROTOCOL §11 publishes integer thresholds, noncritical-only T2 allowance, provisional outcomes/replication, paired ratio and item margins. §13 limits generalization. |
| N1 Q1–Q3 | **FIXED** | PROTOCOL P2/P3, C3/C6 and §14: new ledger, exact dispatched-byte guard/dual hashes, unchanged validation plan, Astra reviewer. |
| N2 No Phase B | **FIXED** | PROTOCOL §2/C4 and BUDGET §4.6 delete it. |
| N3 Q5/Q6 | **FIXED, modified** | PROTOCOL F9/S6/§14 records retrieval and actual pinned screen behavior. Pre-retrieval chronology remains a disclosed local-record claim. |
| N4 Safeguards/arithmetic | **FIXED** | PROTOCOL R3/R4, S9/C4/E7 retains safeguards and corrects third-arm reservations to $0.81 and total $2.43. |

Totals: **10 FIXED, 4 PARTIAL, 0 NOT FIXED** (two FIXED accept the disclosed screen modification).

## BLOCKER findings

### R2-B1. K-ADMIT does not establish the authorized hard cap; lag handling is not fail-closed

**Evidence:** BUDGET:14,22,42–50,98–104; PRIMARY-DECISIONS addendum. Provider facts are accepted from the primary's supplied check; this reviewer did not browse.

The $1.73 branch explicitly depends on an unverified maximum call cost. A limit checked at admission can admit a call from zero usage that later costs over $2.00. The limit value alone cannot rule that out. CN1–CN4 are exactly the unestablished bounds identified in round 1. Calling the residual conditional and requesting acceptance is honest disclosure, but does not satisfy the existing **hard** authorization. BUDGET:50's “The guarantee is §1” conflicts with §1's own qualifications. PROTOCOL:266 also says unknown enforcement semantics block release, while K2 permits that branch with acceptance.

Sequential transport does not establish “at most one unaccounted charge”: completed calls can remain unposted. AD6 permits `delta = 0` after a positive-cost call, so its stated inequality has no way to identify lag and trigger polling. A reproducible benign example: call costs $0.10 then $0.06; key snapshots are $0, $0, $0.16. Call 1 passes AD6 immediately; the correctly caught-up cumulative usage then fails call 2's $0.060001 allowance. Worse, if all snapshots remain zero, every release can pass this check. This is not evidence that OpenRouter behaves that way; it is an uncovered permitted state.

**Suggested edit:** retain an explicit unreleased branch unless either (a) documented charge-time enforcement contains every billable component within the total cap, or (b) a genuine pre-dispatch all-in upper bound is established. A new authorization to accept a conditional budget would change the premise and must not be inferred from approval of a hard cap. Keep the dedicated key as defense in depth. Replace AD6 with cumulative, bounded reconciliation as specified under item 4 below; require a non-resetting cap and verify its reset policy. Remove “guarantee” for K-ADMIT.

### R2-B2. Typed scoring is coverage matching, not structure preservation, and treats NOT asymmetrically

**Evidence:** ADJ B2/B4/B7; scorer:249–263,273–295,352–360,467–485,507–512. `compounds()` excludes NOT, and the invented-operator check excludes it too. Typed child matching uses only source-codepoint containment; it ignores polarity within each child. Relation composition uses only the selected witness's ancestor path, not the reference component's own polarity.

**Reproduced false positive:** mutate fictional `F15b-and-correct` ("Guards must report if a door is open and a lamp is out") from `AND(A,B)` to `AND(NOT(A),B)`, retaining exact evidence. Result: **relation correct, critical AND compound correct, zero invented operators**. The chosen witness is the AND root; the false NOT below it is never charged. A synthetic 12-relation/6-compound aggregate with these accepted verdicts passes **T1–T6**. This is a decision-bar counterexample, not a claim about any real R17 source or output.

**Reproduced false negative:** fictional `F09` says "A lamp tax applies if the shop is not licensed." Give FULL the faithful `if → NOT → [the shop is; licensed]`, with exact `not` evidence on NOT. The reference represents that negation inside a PART as §4.3 permits. Result: **critical inversion**, although OPQ's intact negative clause would be correct. Even using an explicit reference NOT node would not fix the current class-only polarity comparison. This can systematically disadvantage faithful FULL decompositions.

**Suggested edit:** compare reference-relative component semantics recursively, including NOT and ordered EXC placement; allow an intact leaf to preserve its internal wording without treating its lexical negation as a second flip. Matching a child must establish its required polarity and nesting, not just contain its words. Check unmatched asserted operators, including NOT. Add positive/negative fixtures for nested NOT, local versus whole-clause negation, double negation, and nested operator reparenting before accepting typed adoption. The present specs and implementation largely agree on this defect; fixing just Python is insufficient.

### R2-B3. Best-witness scoring masks critical extra scope errors and permits clause evidence on the wrong leaf

**Evidence:** ADJ B2, B5.2/B5.5; scorer:385–413; ADJ A2 M4/M8 and A3.

**Reproduced:** add a confident `if` link to the correct `onlyif` output of `F10e`. Both point to the complete critical restriction. The first is a `scope_change` under the normative table, yet the result remains **correct**. B5 checks only additional `inversion` witnesses; the correct witness hides the added harmful strength assertion. D4's zero-critical-error wording is therefore not enforced.

A second reproduction puts all of `F01b`'s exception clause on the **link evidence**, while its leaf quotes only the target assertion. B2 unions these and scores the exception **correct**, even though the linked condition leaf no longer contains the condition. This is permitted scorer behavior, not an offset or graph error. The wire defines link fragments as connective evidence; citation coverage cannot establish that the actual linked node preserves the condition.

There is a related blind spot in mapping: M4 excludes an opposing assertion and relegates it to notes that never affect scores. A correct mapped unit plus an unambiguously contradictory extra unit can therefore evade the critical-harm gate entirely.

**Suggested edit:** independently audit additional asserted applicability claims rather than selecting only their best witness. At minimum, harmful unhedged extra scope changes must fail a critical item just as extra inversions do; give contradictory unit assertions a machine-readable judgment that affects harm. Distinguish structural/leaf coverage from connective citations: clause PART content must be carried by the corresponding leaf/subtree, while link/operator evidence may satisfy the markers it actually represents. Add fixtures for full-clause link citations, broad operator evidence and correct-plus-harmful duplicates. Do not require extra `obj`/`acts` links to be errors merely because they serve a separate legitimate purpose; define the semantic compatibility rule.

### R2-B4. The adjudicator gate cannot be performed as specified, and accepts zero adjudicators

**Evidence:** ADJ A1–A4 and C4; `check.py`:67–74,203–220; cases `F05a`/`F05b`.

- **34 of 35 scorer cases omit both unit assertion and unit evidence.** `build_output()` builds units as `{id}` only. Part A requires meaning-first mapping from exactly those missing fields and forbids inferring mappings from the condition graph.
- `F05a-inverse-form-unit` and `F05b-inverse-unit-mapped-direct` have identical source, output and reference meaning (only the administrative source ID differs), but expect opposite forms for unit 2. F05b intentionally tests a *wrong supplied mapping*. It cannot also be an independent adjudicator gold answer under the same instructions. Revising Part A “only, never expectations” cannot resolve that contradiction.
- `check.py --adjudications DIR` loops over whatever subdirectories exist and never requires A1/A2. Running its gate on this review directory with **zero adjudicator subdirectories** returned **48 checks, 0 failures**. One submitted adjudicator can likewise satisfy the loop.

**Suggested edit:** separate scorer-input mutation tests (including deliberately bad mappings) from genuine blind-adjudicator fixtures. Populate the latter with complete assertion/evidence fields and one consistent gold mapping per semantic packet; withhold purpose/expected/mapping fields from packets. Require exactly the designated A1 and A2 reports, correct identities, complete case counts and metadata/hash binding. Report scorer-check counts separately from adjudicator counts. Permit reviewed fixture corrections before freeze; then rerun both adjudicators on the repaired gate. Agreement should be exact on normalized target/unit/form data, not free-text `basis` or session metadata.

### R2-B5. The reference checker cannot enforce its promised complete partition

**Evidence:** REFERENCE §4.2.8, §7.1, §8, §10; scorer:103–161. The schema contains no independently declared clause extent or explicit excluded ranges. The checker checks only the supplied quotes for overlap and validity; it does not check that the clause is completely partitioned.

**Reproduced:** delete `not` from the reference's PART markers in fictional F09, leaving the negative word in the source and the output still omitting it. `validate_reference()` accepts the reference, and the previously `lost_connective` output becomes **correct**, critical requirement met. The checker also accepts an orphan target despite §3's requirement that every target have a relation. Semantic review remains necessary, but the claimed mechanical coverage guarantee is currently nonexistent.

**Suggested edit:** add declared clause ranges and explicit, justified exclusions, then verify equality between their counted codepoints and the disjoint introducer/marker/PART union. Mechanically reject orphan targets, invalid field types, illegal cycles in `carves_out_of`, and the other promised schema constraints. Human/source-only review must still verify that the declared clause range and exclusions are faithful. Include missing-middle-negator and missing-final-component invalid-reference fixtures.

## SHOULD-FIX findings

### R2-S1. Ledger/release hash cycle and admission-state ambiguity

PROTOCOL P2 says `INIT` pins the release-record hash; C6 says that release record pins the `INIT` hash. Full-file hashes cannot normally satisfy this circular dependency. **Edit:** `INIT` pins static budget/key configuration only; the release record pins `INIT`; a later `BIND_RELEASE` entry pins the release record before any RESERVE/DISPATCH. Define each hashed byte sequence explicitly.

BUDGET §4 includes pending reservations in Aggregate and also includes their calls in `R`, so a pending call can be reserved twice if admission runs after RESERVE. With six-call funding, the first pending reservation changes $1.62 to $1.89 and falsely fails admission. **Edit:** admit before writing RESERVE under the exclusive lock; require no unresolved dispatched attempt; or compute `Aggregate + FLOOR × remaining_unreserved_calls`. Define no-mark crash recovery, torn-tail handling, durable lock ownership/recovery and directory durability. Retain no retry after a dispatch mark. A key-delta debit over FLOOR can be an AD6 anomaly without AD4 failing; correct §4.9's parenthetical.

### R2-S2. Reference authoring still has contradictory or discretionary segmentation instructions

The brief is source-only and does not reveal arm hypotheses, output examples, thresholds or floors: **no independence breach found**. However, §4.2.4 allows nested qualifications to be typed nodes **or part of a PART**, leaving the compound denominator discretionary. §4.2.4 versus .5 needs an operational distinction between an internal exception and a separate `carves_out_of` relation. Rule .6 asks exemption PARTs to include target-naming words, while .8 says not to include target words. The worked example uses `the new fee` as T3 despite the fallback for an unstated positive target in .6; it must explicitly explain when a noun phrase may stand for an inferred positive applicability assertion. The `Only vendors with stalls` example also needs to account for the whole restricted population without losing `vendors`.

**Edit:** canonicalize these choices using wholly fictional paired examples; define how to mark unresolvable attachment without inventing a target. Publish a deterministic preference for explicit nested structure when supported, with PART fallback only under a named uncertainty condition. Never tune segmentation to meet the compound floor. Add source-only author/reviewer fixtures separately from the extraction scorer fixtures.

### R2-S3. Binding and denominator checks must be executable

The scoring CLI checks `spec_version` but ignores adjudication `output_sha256`, `reference_sha256`, call/source IDs and adjudicator identity (`r17score.py`:687–693). `validate_mapping` validates entries, not the envelope. `bar_D`/`bar_T` derive denominators from supplied lists, not the frozen release manifest, so an assembly bug can silently omit items. The planned dispatch gate does not itself validate a later adjudication file.

**Edit:** provide a strict assembly/validation entry point that verifies actual input hashes, exact frozen source/relation/compound ID sets and critical flags, both adjudicator identities, allowed response states and nonnegative integer token counts before computing bars. Add rejection cases for a swapped output, wrong reference hash, omitted relation and missing adjudicator. Helpers may remain internal, but cannot be advertised as the complete decision gate without this wrapper.

### R2-S4. Outcome and reporting implementation need exact stopping-state definitions

At an early OPQ stop, one adjudicator can find D unreachable while the other only finds it **still reachable**. That is not yet a complete pass/fail split, although §8 correctly labels the run O4. Similarly, early FULL futility is O1, not O1-disputed unless both FULL assessments are complete. `outcome()` accepts only pass booleans/None and lacks an explicit scored-complete versus best-case-reachable state. **Edit:** encode the distinction and add early-stop outcome fixtures; never report an unrun cell as an actual pass.

Specify κ's mutually exclusive categories: ADJ's existing groups overlap (`correct` is complete, acceptable and critical-met), so “κ over relation verdict groups” is not reproducible. `M6b` outside-witness operators are promised but not returned by the scorer; produce that list mechanically. Define E10 sensitivity calculations rather than leaving an unnamed analysis to the end. These reports must not alter frozen primary outcomes.

## Rulings on the four referred questions

**1. O1-disputed: acceptable.** OPQ's complete independent D pass under both adjudicators is already frozen before FULL. A later FULL split does not undo that evidence. O1-disputed adopts only the provisional OPQ research default; FULL must not be adopted or declared inferior. Require both FULL assessments to be complete for the disputed subtype; early futility remains O1, terminal FULL halt O1-incomplete. This is a limited pre-registered decision, not a hybrid score.

**2. Post-hoc screen documentation: acceptable with disclosed limitations.** The unchanged script hashes support documenting executed semantics rather than inventing a replacement after retrieval. The first READY records 22:05:25Z and r2 READY records 22:07:03Z; the supplied retrieval chronology is consistent with the claimed pin-before-fetch order, but those are not independently attested times. I did not open attempt bodies to investigate further. Retain the old/new manifests and exact lexicon/script. “Exception-enriched,” finite reserves and corrected prior-exposure wording are appropriate. Replace PROTOCOL S6's “gives no advantage to either arm” with **“uses the same selection rule for both arms; differential effects of this selected distribution are unmeasured.”** Shared selection does not prove equal ease for different representations. No re-fetch is needed merely to accept this modification.

**3. $1.73 arithmetic: six admissions fit conditionally; enforcement is still unresolved.**

- Six floor reservations: `6 × $0.27 = $1.62`, leaving **$0.11** below a $1.73 key cap, $0.18 below OPERATING and $0.38 below the user cap.
- Six conditional actual maxima: `6 × $0.26384 = $1.58304`, leaving **$0.14696** under the key cap.
- Before call 6, five floors are $1.35; adding the last $0.27 fits. The conceptual one-request overshoot bound is `$1.73 + $0.26384 = $1.99384`, with $0.00616 slack, **only if** the per-call bound and the accounting/enforcement assumptions hold. It is not needed to fund the planned six calls under those bounds.
- “≤ $1.73” alone does not guarantee six-call capacity: a user can set a much smaller limit. For floor-funded capacity require `6 × FLOOR ≤ verified non-resetting key limit ≤ $1.73` (or three floors if FULL is pre-omitted), and include key capacity alongside OPERATING in admission. A lower cap may still suffice at actual prices, but cannot be represented as fully funded under this policy.
- Lag does not reduce the conservative local ledger or justify more calls. It can break per-call delta attribution, and absent a documented settled/enforced balance it defeats the rationale that only one unpaid/unaccounted request can exceed the remaining key allowance. Resolve R2-B1 before release.

**4. Use bounded cumulative reconciliation, then halt; do not silently fall back for admission.** A concrete amendable rule:

1. Pin initial zero usage, exact decimal parsing, cap and **no-reset** policy. Maintain cumulative response-reported nanoUSD `C` from that baseline and monotonic provider usage `U`. Never replace the comparison baseline with a stale sample.
2. After every possibly dispatched attempt, including the final one, check the key immediately, then at elapsed **60, 300 and 900 seconds** if still lagging. Those are a maximum of four reads total; no new paid dispatch during reconciliation. Retain timestamps, permitted fields and hashes. No reads were performed in this review.
3. Under the existing tolerance, call `i` is reconciled only if `|U − C| ≤ i × 1,000 nanoUSD`, usage is monotonic, the cap/reset settings are unchanged, and the read is valid. This symmetrically detects a stale zero instead of accepting it as proof. The tolerance is an explicit measurement policy; amend it before release if documented reporting granularity requires a different value. It cannot prove invoice correctness or replace cap enforcement.
4. Lower-than-expected usage waits; regression, changed/reset/unlimited cap, or excessive usage halts immediately. After the final unsuccessful read or an exhausted read-error budget, write `KEY_USAGE_UNRECONCILED` and **HALT**. OPQ halt means P; FULL halt after a frozen OPQ pass means O1-incomplete. Missing usage on the response already halts under AD1–AD4.
5. On timeout, resolve the charge conservatively using `max(FLOOR, reported, rate estimate)` and all attributable recovered usage. At run close retain at least `max(sum(per-attempt conservative debits), highest cumulative key usage since zero)` as the run debit; do not double-charge delayed usage to the next cell. Append upward reconciliation entries if needed. Missing key evidence is “unreconciled,” not zero. Falling back to the other debit terms is appropriate **for recording the halted attempt**, not for admitting another one under the current hard-cap story.

## Required closeout

Repair R2-B1–B5 and the binding/assembly issues before freeze; retain paid-release blocking if enforcement cannot be established. Rebuild and pin fixtures, add these adversarial cases with corrected expectations, run both real blind adjudicators on feasible fixture packets, then regenerate READY hashes and request re-review. Keep reference authors source-only and keep all scoring decisions blind to R17 source content during these repairs. The protocol architecture does not require redesign; its current gate implementations require correction.
