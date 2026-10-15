# Disposition of the R17 protocol review (design r2)

Review: `../protocol-review/REVIEW.md` (GPT-6 Astra, high; verdict "freeze after edits"), against r17.d1 (`../design/PROTOCOL.md` sha256 `8a990408…1ccb`, `../design/BUDGET.md` sha256 `35e685a1…9385`; both frozen and unchanged). Revised files are in this folder. Section references below point into them.

**Counts: 14 findings (5 BLOCKER, 5 SHOULD-FIX, 4 NOTE).** 12 accepted as suggested, 2 accepted with a stated modification (B5, S4), 0 rejected.

## BLOCKER

### B1. Post-response alarms are not enforcement of the hard $2 cap — ACCEPTED

The edits:

- **Enforcement.** The hard cap now rests on an experiment-isolated provider spending limit, which is a **hard release precondition**: BUDGET §1 K1–K4; PROTOCOL P1.
  - A dedicated OpenRouter key, used only for R17, with a credit limit.
  - Verified before release by (1) the user's attestation and (2) a machine read of `limit`/`usage`/`limit_remaining` by the native runner with the injected key, failing closed.
  - The endpoint path and fields are marked UNVERIFIED offline and must be confirmed from current provider documentation.
- **Limit semantics.** The documented enforcement semantics decide the limit value: $2.00 if the limit rejects charges beyond the allowance (K-HARD); ≤ $1.73 if it is only checked when a request is admitted, or if the semantics are undocumented (K-ADMIT). In that case the conditional residual is disclosed and must be accepted by the user.
- **Fallback.** No key, no release. A soft budget is not substituted (BUDGET §1, PROTOCOL P1).
- **Conditional bounds.** $0.26384 and $1.62 are relabelled as **conditional bounds** with explicit conditions CN1–CN5 (BUDGET §3). The unconditional "cannot exceed $1.62" and the double-price containment example are deleted (BUDGET §7).
- **Anomaly checks.** Fail-closed checks AD1–AD7 are added and labelled **anomaly detection, not cost prevention** (BUDGET §5): the direct `prompt_tokens ≤ guarded bytes ≤ 40,000` check that r1 lacked; completion ≤ 16,384; nested-usage consistency; finite, nonnegative, rate-bounded cost parsed as a decimal; identity; key-usage reconciliation; and ledger-chain integrity.
- **Wording.** BUDGET's cap-enforcement wording is now qualified like A1 (V3: the cap was never hit).

### B2. The floor was dropped and retries did not reserve the remaining experiment — ACCEPTED

The edits (BUDGET §4; PROTOCOL C4, §7):

- **Floor restored, in integer nanoUSD.** Debit = `max(270,000,000, ceil(reported), p×2,500 + c×10,000, ceil(key-usage delta))` for every possibly dispatched attempt. Billing evidence is recovered from error bodies too.
- **Admission reserves all remaining required calls:** `Aggregate + R × FLOOR ≤ 1.8e9`. The aggregate includes pending reservations.
- **Retries deleted.** The retry allowance and C7 are removed. A contentless or uncertain failure is a terminal halt, and the result is partial or inconclusive.
- **Durable ledger.** An exclusive, hash-chained, fsynced, append-only R17 ledger, with recomputed aggregates and crash reconciliation (a mark without a resolution resolves at the floor or more, then halts). It is separate from R14's ledger.
- **Arithmetic.** The admission table shows $1.62 against $1.80 at every release, and why a seventh reservation ($1.89) cannot fit.

### B3. "Complete" and "scope correct" could reward missing logic or the wrong path — ACCEPTED

New normative specs, plus an executable scorer and fixtures:

- **Required evidence (ADJUDICATION-SPEC B1).** Connectives, repeated introducers, negators and exception words are reference `markers`, and they are **required evidence for both arms**. Fixtures F01a/F01c/F09/F14 cover this.
- **Occurrence resolution (REFERENCE-SPEC §2; `validate_reference`).** Every quote carries explicit codepoint offsets **and** an occurrence index; both must agree. Fixtures F14 and V01 cover this.
- **Frozen segmentation (REFERENCE-SPEC §4.2–4.3).** One relation per introducer per target. Coordinated components share one logic tree, and AND/OR are allowed only with a quoted connective. Nested qualifications stay inside their parent (including an `EXC` logic node). Exemption-phrased sentences are handled. Every character of a clause belongs to exactly one of introducer, marker or part.
- **One witness, no borrowing (ADJUDICATION-SPEC B2).** Each relation is scored through **one** link-path witness on a mapped unit. Coverage is never unioned across links, units or paths. Only **minimal** witnesses count, so a containing EXC cannot lend a clause an uninverted path. Fixtures F02, F04 and F07 cover this.
- **Unit matching (ADJUDICATION-SPEC Part A).** Matching is by assertion meaning **plus** evidence overlap (M1–M8), with explicit rules for empty mappings, several units, many-to-many, broader or narrower units, contradiction, and the `direct`/`inverse` form. Fixtures F03a/F03b/F04/F05a/F05b cover this. This is the **only** adjudicator judgment; everything downstream is mechanical (`r17score.py`).
- **Composition (ADJUDICATION-SPEC B4).** EXC/NOT composition and double negation are defined by polarity flips through NOT, the EXC carve-out and inverse form. A change of strength is a hedge only when explicitly uncertain. Fixtures F06/F07/F08a/F08b/F10a–f cover this.
- **Error precedence (B5).** absent / wrong_target → shortened / lost_connective → inversion / role_loss / scope_change → contradiction → broad → correct / hedged / embedded. Broad and conflicting leaves are defined by extraneous coverage and contradiction rules. Fixtures F11a/F11b/F12/F13 cover this.
- **Coverage vs semantics.** M3 is now called **text coverage**, and adoption is also gated on semantic verdicts (D3/D4).
- **Fixture gate (ADJUDICATION-SPEC C4; PROTOCOL P5).** 34 authored fictional scorer cases, 2 invalid-reference cases and 11 decision cases. One extra case pins the real R15 expanded record to prove format compatibility. Both adjudicators must reproduce every fixture mapping exactly before freeze. `check.py` passes (48 checks). A mutation run that flipped each expected relation, compound, invented and decision value was caught every time (76/76).

### B4. D permitted critical omissions and some critical scope errors — ACCEPTED

- **D4 rewritten** (PROTOCOL §11): **zero critical failures of any category**. Every critical relation must be correct, explicitly hedged, or broad-but-correct. Critical absence, wrong target, lost connective, shortening, inversion, role loss, unhedged scope change, contradiction and embedded-only all fail. The one-error allowance applies to **noncritical** harmful verdicts only.
- **Role substitution** (COND↔onlyif, RESTRICT↔if, obj/acts, indeterminate strength) counts as a harmless hedge **only when explicitly uncertain** (link or path `q≠0`, or `ALT`). Otherwise it is `scope_change` or `role_loss`, both harmful.
- The review's 12-relation counterexample is fixture D01 (D4 fails). Fixtures D02–D04 cover the allowance and the embedded-critical case.
- The critical-label policy is frozen before references (REFERENCE-SPEC §5; PROTOCOL P5).

### B5. The second adjudicator's outcome was undefined for half the items — ACCEPTED with modification

- **Accepted.** A2 independently maps **all** targets of every scored output. There is no sampling. Two complete score sets are computed, one per adjudicator. The output format, denominators (frozen at reference freeze, published in the release record), item-level agreement reporting and bar evaluation per adjudicator are frozen (ADJUDICATION-SPEC C1–C3; PROTOCOL §10–11). No hybrid score exists.
- **Modification.** The review says "report one run-level O4 if the outcomes differ". This design applies O4 when the adjudicators **split on the OPQ default**. When they agree on OPQ but split on FULL, the outcome is **`O1-disputed`**: the agreed clause-only default stands, the typed layer is not adopted, and the split is reported.
- **Reason.** O2 already requires both adjudicators, so a FULL split can never adopt the typed layer. Calling the whole run O4 would throw away an OPQ decision both adjudicators agree on, over a disagreement about an add-on that is rejected either way. Flagged for the re-review to confirm.

## SHOULD-FIX

### S1. Order and futility; OPQ truncation does not prove FULL truncation — ACCEPTED

- **Order.** The required order is now OPQ1 → OPQ2 → OPQ3 → adjudicate and freeze OPQ → FULL1 → FULL2 → FULL3 (PROTOCOL C1).
- **Futility** (PROTOCOL §8; `r17score.futile`; fixtures U01–U03):
  - per-call scoring before each release;
  - mechanical stops: arm failure, headroom, and T6 unreachable;
  - semantic stops: D unreachable under both adjudicators (O3) or under one (O4) in the OPQ phase; T unreachable under either adjudicator in the FULL phase;
  - FULL omitted before paying when typed logic is untestable (P9);
  - one FULL structural failure stops FULL, rather than waiting for two.
- **Limited decisions.** G0/O now allow limited pre-registered decisions from irreversible failures. Unrun cells are "not run — pre-registered futility", never scored or extrapolated.
- **H7 deleted.** The "FULL cannot fit either" inference is gone. An observed arm failure is a finding about that profile and source only (PROTOCOL §7 notes).
- **Tradeoffs recorded.** The order gives up ABBA balancing, phase drift is confounded with arm, and O3b and a full six-cell descriptive study are not guaranteed.

### S2. Transport, HTTP and retry classifications conflicted — ACCEPTED

Retries are removed (B2). A single **ordered response-state table** separates the cases (PROTOCOL §7):

- pre-dispatch integrity (a resumable pause, debit 0);
- transport uncertainty;
- auth, payment/limit and rate-limit failures, none of which is schema evidence;
- explicit schema or parameter rejection, now the only basis for "schema rejected";
- other HTTP errors;
- malformed responses;
- billing or integrity anomalies;
- content-bearing refusal or termination;
- truncation, structural invalidity and valid.

"No content" covers empty or reasoning-only messages and HTTP 200 without choices or usage. Every possibly dispatched attempt keeps its debit. Pause and halt are distinguished. The categorical "cannot bias" claim is deleted.

### S3. Reference precedence: a hash is not proof — ACCEPTED

- **Isolation.** Author and reviewer sessions are isolated, with no inherited conversation. Each input packet is enumerated, supplied inline and retained, and tool logs are kept. A read outside the packet invalidates that reference (PROTOCOL E1, E5, E6). The neutral spec is written by a design author who has not read any source and is frozen before authoring (E2, P5).
- **Wording.** "That proves ordering" is replaced by "the dispatch gate must verify this immutable, recorded reference freeze before the first transport attempt" (E7).
- **Binding.** The release and reference hashes are bound into every per-call intent (C6).
- **Chronology.** The hashes-only limitation is stated. An optional commit and push gives an externally recorded ordering, if the user authorizes it.

### S4. Pool "not wholly unseen"; screen details discretionary — ACCEPTED with modification

- **Accepted.** The wording now reads: "not previously used as extraction/evaluation test inputs in the recorded benchmark; exposed during frame construction (R12 opened all 28 filings)" (PROTOCOL §0, F8, §13).
- **Accepted.** The executed screen's exact semantics are documented from the pinned `screen.py`: whole-word regex, case-insensitive, overlaps counted per term, a single literal space in phrases, no normalization (S6). It is labelled **exception-enriched sampling, not content-blind**.
- **Accepted.** The fallback is now finite and deterministic: the three frozen reserves only, with no 26-20 extension (S7). E8 adds deterministic replacement for the pooled floor (replace the smallest passing source, with a tie rule) and stops before paid calls if the reserves are exhausted. Compounds never trigger replacement.
- **Modification.** Freezing the lexicon expansions, normalization, overlap policy and hit-count fixtures **before retrieval** cannot be done after the fact. The retrieval is done (F9).
- **Reason it is acceptable.** The screen script was pinned by hash in the first-run READY (22:05:25Z) before the r2 retrieval (22:06:41Z). These are self-recorded times, as stated. Its literal behavior was never changed, so no discretion entered after content was available. Re-screening with a newly specified rule now would itself depend on content. The overlap and normalization behavior is therefore documented as executed, and the limitation is recorded rather than "fixed".

### S5. Thresholds are coarse; 1.5× is a policy choice — ACCEPTED

- **Integer counts.** A required-count table is published (PROTOCOL §11). The exact row for the frozen denominators goes into the release record before dispatch.
- **Provisional outcomes.** O1 and O2 are now "provisional default for the next research round, requiring new-source replication".
- **Ratio.** The pooled ratio is defined as `ΣFULL/ΣOPQ` completion tokens over complete pairs, with reasoning included. It is undefined, and therefore fails, on a missing, failed or zero denominator. Per-source ratios are reported and a single source over 1.5× is flagged. Total billed cost and debit are reported (M2).
- **1.5× and T2.** 1.5× is described as a preselected engineering tradeoff. T2's allowance is restricted to noncritical items.
- **Noise.** Per-criterion item margins are reported, with an "at threshold — fragile" label. D5 is stated to measure headroom at this source size only. The non-independence and n=1 limits are restated, with no claims of superiority, production readiness or extrapolated capacity.

## NOTE

### N1. Q1–Q3 compatible; resolve them in the frozen text — ACCEPTED

Resolved in PROTOCOL §14 and BUDGET (Q1 new ledger; Q2 adapter override with dual hashes and `len(exact dispatched serialization)+1024` guard; Q3 Astra). The adapter and its tests are release prerequisites (P3). The historical $0.094009282 is untouched and not used for capacity.

### N2. Q4 is a binding "no Phase B" — ACCEPTED

Phase B is deleted everywhere: r1 R5, C7, Q4 and BUDGET rule 5. It is noted as future work only.

### N3. Q5/Q6 resolve preference, not implementation — ACCEPTED

Q5 is recorded as approved and done (F9). Q6 is recorded as kept, with the overlap and normalization behavior documented from the pinned script rather than called "mechanical, pre-registered" without qualification (S6; see S4 for the pre-retrieval limitation).

### N4. Several safeguards are sound; fix R4(d) — ACCEPTED

The r1 safeguards are kept: same frozen source per arm; no clipping, chunking or content retries; dual-hash binding; retained rejected responses; quote anchoring; cross-provider reference review; immutable primary labels; `production_eligible:false` and `action_ready:false`. R4(d) is corrected to $0.81 for three floor-reserved calls, giving $2.43 > $2.00, and the $0.55/$2.17 estimate is withdrawn (PROTOCOL R4; BUDGET §6). No third arm is added.

## Additional changes found while authoring the fixtures (not raised by the review)

1. **Minimal-witness rule.** Without it, a witness at an EXC parent scored a clause that sits under the carve-out as uninverted, which is borrowed structure (fixture F07).
2. **EXC logic node** in the reference grammar. Without it, a correct nested "exception to an exception" in FULL would have been scored as an invented connective (fixture F21, the frozen R15 expanded record).
3. **Cross-relation AND is not invented.** The wire format allows only one `if`/`onlyif`/`unless` link per unit, so separate conditions must be conjoined (fixture F18).
4. **One operator, one error.** An operator already judged swap, mismatch, exc_reversed or wrong_base is not also counted as invented (fixture F17).
5. **`embedded` verdict.** An exception kept verbatim inside its host condition's leaf is not harmful, but it is not linked. It fails the critical requirement (fixture F12, D04).
6. **Reference `rationale` field** for every relation, to support review and the UNRESOLVED class.

## Unchanged by design

The cost arithmetic follows the review's re-derivation: effective prompt $2.499777/M, completion $10/M, a conditional maximum of $0.26384 per call, a $0.27 floor, $1.62 for six calls, a $1.80 operating limit and a $2.00 hard cap. `max_price` stays unchanged.
