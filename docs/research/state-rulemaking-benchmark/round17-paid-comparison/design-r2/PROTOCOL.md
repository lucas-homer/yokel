# R17 paid comparison: clause-only (OPQ) vs full profile, protocol design r2

Status: **design draft r2 (r17.d2)**, revised after `protocol-review/REVIEW.md` (GPT-6 Astra, high: "freeze after edits"). It **authorizes nothing**. It supersedes `../design/` (r17.d1, frozen, unchanged). Every finding and its disposition is in [DISPOSITION.md](DISPOSITION.md). Arithmetic and enforcement are in [BUDGET.md](BUDGET.md); the reference author's brief is [REFERENCE-SPEC.md](REFERENCE-SPEC.md); scoring is [ADJUDICATION-SPEC.md](ADJUDICATION-SPEC.md), implemented by `fixtures/r17score.py` and tested by `fixtures/check.py`. Paths are relative to `docs/research/state-rulemaking-benchmark/` (BENCH). No provider call, network access or credential access occurred while writing it.

Labels: **VERIFIED** (file:line or a reproduced offline command), **PROPOSAL** (a design choice, normative once frozen), **ESTIMATE**, **CONDITION** (an unverified premise; see BUDGET §3).

## 0. Question

On three WSR notices that have **not previously been used as extraction or evaluation test inputs in the recorded benchmark**, does the r16.w2.1 **opaque** (clause-only, OPQ) profile preserve scope and exception clauses completely, and link them correctly, well enough to be the **provisional default for the next research round**? If it does, does the **full** profile's typed logic layer (AND/OR/NOT/EXC/ALT; FULL) add correct structure without losing clauses or output headroom? `production_eligible` and `action_ready` stay false under every outcome. One draw per cell cannot support claims of statistical superiority, production readiness or capacity on longer notices.

## 1. Facts the design rests on (VERIFIED unless marked)

- **F1.** r16.w2.1 profiles: `opaque` permits only L/R nodes with `a=[]` and appends the instruction to keep complete clauses in exact fragments with their source-supported links. `full` permits AND/OR/NOT/EXC/ALT (`round16-wire-compat/protocol-w2-1/wire.py:240-243,308-318`).
- **F2.** Link roles are `if, onlyif, unless, regardless, obj, acts, qual`, with at most one `if`/`onlyif`/`unless`/`obj` link per unit; `qual` requires link q≠0. `if` asserts neither sufficiency nor necessity (`round15-condition-preservation/protocol-revised/stage-a.system.txt`, "Each l link").
- **F3.** Request settings come from frozen r15.1 bytes with `max_tokens: 8192`. R17's only body delta is 16,384 (PRIMARY-DECISIONS Q2).
- **F4.** `validate_response` requires finish `stop` and the **unmodified** `build()` plan (`wire.py:261-275`).
- **F5.** Provider acceptance of the depth-8 schema, output headroom and extraction quality are unverified (`round16-wire-compat/README.md:25-31`).
- **F6.** Structural validity is not meaning (`round15-condition-preservation/README.md:22`). R14's real output truncated qualifications (`round14-semantic-contract/RECOVERY.md:23`).
- **F7.** R14's reference and assessment ran in one session, and its summary totals disagreed with its own entries (`RECOVERY.md:29`). R17 separates the roles and computes every total mechanically.
- **F8. Prior exposure, corrected.** The candidate IDs appear in BENCH only in R12 `source/FRAME.json`, R14 `source/SELECTION.json` and R17 files (review S4, search over all BENCH including `artifacts/`). That supports **no recorded prior test use**. However, R12 `source/SELECTION-REPORT.md:5` says all 28 filings were **opened during frame construction**. The sources are therefore *not wholly unseen*: they were exposed during frame construction and never used as test inputs. Absence from external sessions or training data cannot be established.
- **F9. Sources are selected and frozen** (`round17-paid-comparison/sources-r2/READY.json`, recorded 2026-10-13T22:07:03Z). Selected: **26-19-039, 26-19-041, 26-19-106**. Reserves, all passing every screen: **26-19-116, 26-19-123, 26-19-135**. Guarded bytes for selected sources are 20,376–22,129 (SCREEN.json). The first retrieval run (`sources/`) failed on sandbox DNS and is frozen as evidence.
- **F10.** The keyword screen script `sources/screen.py` (sha256 `f3c43e7e…c8b`) was pinned in the first-run READY at 22:05:25Z, before the r2 retrieval (attempts started 22:06:41Z). Both times are self-recorded, not independent timestamps. Its exact semantics are in §3 S6.

## 2. Arms

- **R1. OPQ:** r16.w2.1 `build(source, "opaque")`.
- **R2. FULL:** r16.w2.1 `build(source, "full")`.
- **R3.** Same sources and same settings except the profile: model `openai/gpt-6.1-sol`, reasoning low, `max_price` unchanged (2/10), OpenAI-only routing, no fallbacks, and the single declared delta `max_tokens` 8,192 → **16,384**. One sample per arm per source.
- **R4. No R14-format arm (PROPOSAL).** The r14.2 format has no clause fragments or scope links, so B-rules would score two arms mechanically and the third by judgment only. Its truncation failure mode is already shown (F6), and R15 makes exact-clause preservation the baseline for any typed layer. Arithmetic: at the $0.27 floor, three more calls are $0.81, so $1.62 + $0.81 = $2.43 > $2.00 (BUDGET §6). The r1 $0.55/$2.17 estimate is withdrawn.
- **No Phase B** (PRIMARY-DECISIONS Q4). Any regression-control idea is future work.

## 3. Sources (done; recorded here for completeness)

- **S1.** Three sources: 26-19-039, 26-19-041, 26-19-106 (F9).
- **S2. Universe:** the frozen WSR 26-19 PROP frame (R12 `FRAME.json`), excluding prior test inputs 26-19-016 and 26-19-023.
- **S3. Size rule** (prospective, applied to frozen metadata): `readable_text_chars ≤ 6,300`. Six candidates, ascending ID.
- **S4. Retrieval** (approved, PRIMARY-DECISIONS Q5): an unauthenticated GET of each official URL; exact bytes archived; extraction by a byte-identical copy of `round14-semantic-contract/source/extract_source.py`. All six candidates returned HTTP 200 on the first attempt.
- **S5. Gates:** text ≤ 6,500 characters; `measure()` `under_guard` with guarded bytes ≤ 32,000 for both profiles; `build()` succeeds for both.
- **S6. Keyword screen, exact semantics as executed** (PRIMARY-DECISIONS Q6, kept). For each term, `len(re.findall(r"\b" + re.escape(term) + r"\b", text, re.IGNORECASE))`, on the raw extracted text:
  - Terms are counted **independently**. Overlaps are counted once per term: "only if" scores for `only if`, `only` and `if`. `exception`/`exceptions` and `waive`/`waiver` are separate terms, and neither matches the other because of the closing `\b`.
  - A multiword term matches only with **exactly one ASCII space** between its words. Phrases split by a newline or by multiple spaces do not match.
  - There is no Unicode or whitespace normalization, and there are no inflections beyond the listed terms.
  - Pass rule: ≥ 1 exception-class hit and ≥ 3 total hits.

  This is **exception-enriched sampling, not content-blind sampling**. It is blind to people (no human or model read text to screen it), but it depends on content and favors explicit lexical cues over implicit scope. Applying it to both arms gives no advantage to either arm, but it limits generalization. Exception hits in the selected sources come mainly from `exempt`/`exemption` (SCREEN.json), which may be notice-form boilerplate. The reference decides the real structure (E8).
- **S7. Finite fallback** (PROPOSAL; replaces the r1 26-20 extension). Only the three reserves, in ascending ID order (116, 123, 135). There is no new frame without a new design and review.
- **S8.** Frozen: `sources-r2/READY.json`.
- **S9.** Sources are never edited, clipped or chunked. Before dispatch, people and models read a source only to write or review its reference (E1–E6). The design author has not read any source text.

## 4. Release preconditions (all required before the first transport attempt)

If any precondition is unmet, the paid phase **stays unreleased**. That outcome costs nothing and is not a result.

- **P1. Hard-cap enforcement (B1).** A dedicated R17 OpenRouter key with a verified credit limit, per BUDGET §1 K1–K3: the user's attestation, a machine check of `limit`/`usage`/`limit_remaining` by the native runner, and fail-closed handling. **If the user cannot provide such a key, nothing is released, and no soft-budget substitution is allowed.**
- **P2. Ledger** initialized in the new namespace (BUDGET §4), with `INIT` pinning cap, operating limit, floor, key label and limit, and the release-record hash.
- **P3. Adapter** pinned with its tests (PRIMARY-DECISIONS Q2). The tests must show:
  - the dispatched body equals the `build()` body except `max_tokens: 16384`;
  - `len(exact dispatched serialization) + 1024 ≤ 40,000`, recomputed immediately before transport;
  - both `plan.request_sha256` and `dispatched_body_sha256` are recorded;
  - validation uses the unmodified plan;
  - `DISPATCH_MARK` is fsynced before the socket send;
  - the §7 response-state table and AD1–AD7 are implemented as specified;
  - no automatic retry exists.
- **P4. Sources** frozen (F9). Done.
- **P5. Scoring frozen before any reference is authored** (ADJUDICATION-SPEC C4): `check.py` exits 0. Both adjudicators reproduce every fixture mapping exactly, so all fixture verdicts match. REFERENCE-SPEC, ADJUDICATION-SPEC, `r17score.py`, `cases*.json` and `check.py` are hashed. The critical-label policy (REFERENCE-SPEC §5) is frozen with them.
- **P6. References** authored, reviewed and frozen (§5), with sufficiency (E8) met and the integer threshold table published (§11).
- **P7. Release record** (C6) signed and verified by the dispatch gate.
- **P8. Roles and auth.** Claude roles (reference author Fable, A1 Fable, A2 Opus) run on the `claudeAgent` subscription. Confirm `claude auth status` shows `authMethod: claude.ai` and that no `ANTHROPIC_API_KEY` override exists (check variable names only). The reference reviewer is GPT-6 Astra through the T3 Codex provider, never an `openrouter/*` model.
- **P9. Futility decision before paying.** If E8 declares typed logic untestable, FULL is **omitted** from the plan and `R` starts at 3 (BUDGET §4 rule 3).

## 5. Reference expectations (frozen before any model output exists)

- **E1. Author:** Fable 5.1 (`claudeAgent` / `claude-fable-5-1`, high, subscription). One **isolated** session per source, with no inherited conversation. Its complete input packet is enumerated and retained: the source's `parsed-body.txt`, `source_id`, `source_text_sha256`, and REFERENCE-SPEC.md, supplied **inline in the prompt**. Its instructions forbid opening any other file and any browsing. The session's tool log is retained. **Any file read or fetch outside the packet invalidates that reference**, and it is redone in a new session.
- **E2. What the author never sees:** the wire format, r15/r16 prompts, link-role names, the arm hypotheses, this protocol, BUDGET, ADJUDICATION-SPEC, any R14–R16 output or reference, or the E8 floors. The design author wrote REFERENCE-SPEC without reading any R17 source text (S9).
- **E3. Format:** REFERENCE-SPEC §8 (`r17.ref.v2`). Every quote has explicit codepoint offsets and an occurrence index. Relations carry logic trees whose connectives and negators are required evidence.
- **E4. Mechanical check:** `r17score.py validate-reference` checks quotes, offsets, occurrences, overlap, schema and `carves_out_of`. Every failure goes back to the author, still before any output exists. Iterations are logged.
- **E5. Independent review:** GPT-6 Astra (high) through the T3 Codex provider, in an **isolated session per source with no inherited conversation**. Its packet (source, REFERENCE-SPEC, reference draft) is enumerated, supplied inline and retained, and the same read prohibition applies. It files objections of the kinds listed in REFERENCE-SPEC §7.
- **E6. Exchange:** the author answers each objection once, accepting or maintaining. The reviewer may reply once. Items still disputed after two rounds become `contested:true`, set by the primary with both positions recorded. Contested items leave the primary denominators and are reported separately. Every prompt, attachment, objection and answer is retained.
- **E7. Freeze:** `reference/READY.json` pins, per source, the prompts, packets, raw results, the reference JSON, quote-check outputs, review exchanges, tool logs, model IDs and efforts. **The dispatch gate must verify this immutable, recorded reference freeze before the first transport attempt.** Its hash is bound into the release record (C6) and into every per-call intent. Hashes prove which content each step depended on. They do not prove chronology. If the user authorizes it, the primary commits and pushes the reference freeze before releasing OPQ1, which gives an externally recorded ordering. Otherwise ordering rests on local records, and that limitation is stated in FINAL.json.
- **E8. Sufficiency** (checked at freeze, before dispatch; deterministic):
  - Per source: ≥ 2 live relations (`contested:false` and class ≠ UNRESOLVED), and ≥ 1 of them EXCEPT or RESTRICT. A source that fails is replaced by the next reserve (S7), whose reference is produced by E1–E7.
  - Pooled: ≥ 12 live relations. If three passing sources pool fewer than 12, replace the passing source with the fewest live relations (ties: the higher ID) by the next reserve, and repeat. If the reserves run out, **stop before any paid call** and report.
  - Pooled ≥ 5 live compounds (ADJUDICATION-SPEC B7). If fewer, typed logic is **untestable**, FULL is omitted (P9), and the best possible outcome is `O1-untestable`. Sources are **not** replaced to chase compounds.
  - Every replacement is recorded with its reason. All of this happens before any output exists.
- **E9. Crosswalk:** superseded by ADJUDICATION-SPEC B4–B7. Polarity composes through roles, NOT, EXC and unit form. A change of strength is a hedge **only when explicitly uncertain**; otherwise it is a scope change (harmful). Embedded, broad, contradiction and the typed rules are defined there and tested by fixtures.
- **E10. Reference defects** noted by adjudicators feed a sensitivity analysis only and never change primary scores.

## 6. Calls and request

- **C1. Calls and order** (pre-registered; review S1). At most 6, sequential, ascending source ID within each arm:
  1. **S1-OPQ → S2-OPQ → S3-OPQ.** Score and adjudicate each call before releasing the next (§8).
  2. **Decide OPQ** on the complete D bar under both adjudicators, and freeze that adjudication (hashes) **before** any FULL release.
  3. **Only if both pass OPQ and typed logic is testable: S1-FULL → S2-FULL → S3-FULL**, with futility stops.

  This order spends money on prerequisites first and gives up the r1 ABBA temporal balancing. Drift between the OPQ and FULL phases is confounded with arm. That tradeoff is accepted for the default-adoption objective. A complete six-cell descriptive comparison and the r1 "O3b" (FULL passes while OPQ fails) are **not** guaranteed by this design.
- **C2. `max_tokens` = 16,384.** ESTIMATE of need for sources ≤ 6,500 characters: roughly 1 token per source character for base units, plus about 150–210 (OPQ) or 280–400 (FULL) tokens per relation. FULL may exceed the D5 headroom. That would be a finding.
- **C3. The only body delta** from `build()` is `max_tokens`. The adapter builds the body from `plan["body"]` with exactly that delta, recomputes the guard on the exact dispatched bytes, records both hashes, and validates with the unmodified plan (P3).
- **C4. No retry, repair, clipping, chunking, narrowing, fallback model or prompt change.** There is no re-release of any kind (B2). This deletes the r1 C7.
- **C5. Retained per call:** raw response bytes and SHA-256, headers, HTTP status, content, `finish_reason` and native finish, model, provider, the full `usage` object as raw text, the reported cost decimal string, the debit and its basis, key usage before and after, the response state (§7), and the validation result or `WireError.code`.
- **C6. Release record** (before OPQ1) pins:
  - this protocol, BUDGET, REFERENCE-SPEC and ADJUDICATION-SPEC hashes;
  - the scorer and fixture hashes, and the fixture-agreement reports for A1 and A2;
  - `sources-r2/READY.json` and `reference/READY.json`;
  - the published `N`, `n_s`, `N_c`, critical counts and the integer threshold table;
  - the six (or three) plan hashes and dispatched-body hashes;
  - the ledger `INIT` hash, the key attestation and the machine-check record;
  - adapter and test hashes.

  **Each per-call intent**, written before `DISPATCH_MARK`, binds the release-record hash, the reference-freeze hash, the plan hash, the dispatched-body hash and a unique job/claim id. The dispatch gate refuses on any mismatch.

## 7. Response states and stop rules

**Pause vs halt.**

- A **resumable pause** is a planned wait: after each call while it is scored and adjudicated, and between the phases. It is also any pre-dispatch failure where no `DISPATCH_MARK` was written. Such a failure costs nothing and is fixed offline. Fixing it re-freezes any changed artifact, and a changed protocol, spec or scorer needs re-review.
- A **terminal halt** ends the paid phase. No further release is ever made.

**Ordered response-state table** (each attempt gets the first row that matches; every row from 2 down keeps its debit per BUDGET §4):

| # | State | Classification | Effect |
|---|---|---|---|
| 1 | Pre-transport check fails (guard, delta, hash, binding, ledger admission, key check) and no `DISPATCH_MARK` | pre-dispatch integrity | resumable pause; debit 0 |
| 2 | `DISPATCH_MARK` written, then no HTTP status (connect error, timeout, crash) | transport-uncertain | **terminal halt**; partial |
| 3 | HTTP 401 / 403 | auth failure, not schema | terminal halt; partial |
| 4 | HTTP 402, or a body naming a credit or key limit | payment or limit refusal (the hard cap working) | terminal halt; partial |
| 5 | HTTP 429 | rate limit, not schema | terminal halt; partial (no retry) |
| 6 | HTTP 400 / 422 whose body explicitly names `response_format`, schema, a parameter or an unsupported keyword | **schema/parameter rejection** | terminal halt. Dispatchability finding: "provider acceptance failed for r16.w2.1 (profile)"; quality inconclusive |
| 7 | Any other 4xx, or 5xx | other client/provider error | terminal halt; partial |
| 8 | HTTP 200 but unparseable, no `choices`, or more than one choice | malformed response | terminal halt; partial |
| 9 | HTTP 200, AD1–AD7 fail (missing or malformed usage or cost, token or cost bounds, identity, key reconciliation, ledger) | billing/integrity anomaly | **terminal halt**; content retained and described, never scored for the decision |
| 10 | `finish_reason` ∉ {stop, length}, or a non-empty refusal, or a tool call | content-bearing refusal or termination | **arm failure** (structural); not a halt by itself |
| 11 | `finish_reason = length` | truncation (output fit) | **arm failure**; no salvage |
| 12 | `stop`, and `validate_response` raises | structural invalidity (`WireError` code) | **arm failure** |
| 13 | `stop` and valid | valid | score (§8) |

Notes:

- An empty message that carries only reasoning or refusal fields falls into row 10. HTTP 200 with no choices or no usage falls into row 8 or 9.
- Only row 6 supports the conclusion "schema rejected". Rows 3–5 and 7 say nothing about the schema.
- Timeouts and transport errors (row 2) may follow billable generation, and their probability may depend on output length and therefore on the profile. They are never treated as neutral: the run stops partial. The r1 "cannot bias" claim is deleted.
- An arm failure (rows 10–12) on **OPQ** fails D1 and stops the run with outcome O3 (§8). On **FULL** it fails T1 and stops FULL with O1. It is recorded as **an observed failure of that profile on that source**, not as universal schema rejection, and nothing is inferred about the other arm. An OPQ truncation says nothing about whether FULL would fit; the r1 H7 inference is deleted.

## 8. Staged scoring and futility (pre-registered)

After each valid call (row 13), run before the next release:

1. `r17score.py score` under each adjudicator's mapping. A1 and A2 each map in fresh sessions (ADJUDICATION-SPEC Part A).
2. **Futility test** under each adjudicator separately, using `r17score.futile()`: the bar is evaluated with every unrun cell set to perfect (valid, 0 tokens, every live relation correct, every unrun compound correct).

**OPQ phase.**

- **Mechanical futility.** Any OPQ arm failure (rows 10–12), or `completion_tokens > 13,926`, means D1 or D5 can no longer pass. Stop: outcome **O3**.
- **Semantic futility.** If D is unreachable under **both** adjudicators, stop: **O3**. If it is unreachable under exactly one, stop: **O4**. Either way OPQ cannot be adopted, so further OPQ calls cannot change the decision.
- After OPQ3: both pass D → freeze the OPQ adjudication and continue to FULL (if testable). Both fail → **O3**. They split → **O4**. FULL is not run after O3 or O4. That is an explicit pre-registered futility, not a finding about FULL.

**FULL phase** (only after OPQ passes under both).

- **Mechanical futility.** Any FULL arm failure, `completion_tokens > 13,926`, or `2 × Σ FULL completion tokens so far > 3 × Σ OPQ completion tokens` (T6 can no longer pass). Stop: **O1**.
- **Semantic futility.** If T is unreachable under **either** adjudicator, stop: **O1**. The typed layer needs both, so it cannot be adopted.

Every unrun cell is recorded as **"not run — pre-registered futility (rule id)"** and receives no score. Unobserved FULL scores are never extrapolated.

## 9. Metrics (definitions in ADJUDICATION-SPEC Part B)

- **M1. Structural validity:** response state 13. Binary per call.
- **M2. Output use:** `completion_tokens`, `reasoning_tokens`, the fraction of 16,384, and tokens per source character. The FULL/OPQ ratio is reported per source and pooled. The pooled ratio is `Σ FULL completion_tokens / Σ OPQ completion_tokens` over complete pairs, with reasoning included on both sides. It is **undefined (and T6 fails)** if any paired cell is missing or failed, or if the denominator is 0. Total billed cost and total debit are reported per arm.
- **M3. Text coverage** (complete / lost_connective / shortened / absent / wrong_target) through one minimal witness on a mapped unit. Connectives and negators are required evidence. This metric was called "completeness" in r1; it is coverage only, and adoption is also gated on M4/M5.
- **M4. Semantic verdict per relation:** correct, hedged, embedded or broad (acceptable), and the harmful set. Role composition covers roles, NOT, EXC and unit form.
- **M5. Harmful errors** (the harmful verdict set), flagged critical or noncritical, plus the **critical-requirement check** (verdict ∈ {correct, hedged, broad}).
- **M6. Typed logic** (FULL only): compound verdicts and invented connectives. M6b reports operators outside every selected witness (not scored). OPQ reports N/A.
- **M7. Calibration** (reported): UNRESOLVED relations, calibrated / asserted / not preserved.
- **M8. Breadth** (reported): extraneous codepoints per relation. Values over 2 × |K| make a relation `broad`.
- **Agreement** (reported): item-level A1/A2 agreement and κ (ADJUDICATION-SPEC C3).

## 10. Adjudication procedure

- A1 (Fable 5.1, high) and A2 (Opus 5.5, high) **each map every target of every scored output**, independently, in fresh sessions, one session per output. Neither sees the other's files or any totals. No sampling (B5).
- The OPQ adjudication is frozen (by hash) before any FULL release and is never revised afterwards.
- There is no arm masking. FULL is recognizable from its typed nodes, and the staged order reveals the phase. The mitigation is that the only judgment is the target mapping (ADJUDICATION-SPEC A2), whose rules ignore conditions, links and nodes (M8). Everything else is mechanical.
- Reference-defect notes and scorer objections are reported and fed to sensitivity analysis only.

## 11. Decision rule (thresholds fixed now)

**G0. Evidence gate.** Preconditions P1–P9 held. Every call that was released resolved in states 10–13, or was skipped by a pre-registered futility rule. No terminal halt occurred in the phase whose result is claimed. Adjudicator files are complete for every scored output.

**D. Default bar**, applied to an arm, separately under each adjudicator:

- **D1.** M1 valid on all 3 sources.
- **D2.** Text-complete ≥ **0.90** pooled, and ≥ **0.75** on every source.
- **D3.** Correct ≥ **0.75** pooled, and acceptable (correct + hedged + embedded + broad) ≥ **0.90** pooled.
- **D4.** **Zero critical failures of any category.** Every critical relation's verdict ∈ {correct, hedged, broad}. Critical absence, wrong target, lost connective, shortening, inversion, role loss, unhedged scope change, contradiction and embedded-only all fail. At most **1** harmful verdict on a **noncritical** relation, pooled. The one-error allowance never covers a critical item.
- **D5.** Every call's `completion_tokens` ≤ **13,926** (85% of 16,384). This measures headroom at this source size only. It is not evidence of fit on the longer, excluded notices.

**T. Typed-layer bar** (FULL vs OPQ, under the same adjudicator):

- **T1.** FULL passes D1–D5.
- **T2.** FULL text-complete count ≥ OPQ count − 1, **and** every critical relation that is text-complete under OPQ is text-complete under FULL. The allowance is noncritical only: about 8.3 points at N = 12.
- **T3.** FULL correct count ≥ OPQ correct count.
- **T4.** ≥ 5 live compounds, and M6 correct ≥ **0.90**.
- **T5.** Zero critical typed harmful errors, and ≤ 1 typed harmful error in total.
- **T6.** Pooled FULL/OPQ completion-token ratio ≤ **1.5** (`2 × ΣFULL ≤ 3 × ΣOPQ`; M2 definition). 1.5× is a **preselected engineering tradeoff** (cost and headroom), not a validated quality or utility threshold. Per-source ratios are reported. A single source over 1.5× does not fail T6 by itself, but it is flagged.

**Required integer counts** (`ceil(rate × N)`). The exact row for the frozen `N`, each `n_s` and `N_c` is published in the release record:

| N (pooled) | D2 complete ≥ | D3 correct ≥ | D3 acceptable ≥ |
|---:|---:|---:|---:|
| 12 | 11 | 9 | 11 |
| 13 | 12 | 10 | 12 |
| 14 | 13 | 11 | 13 |
| 15 | 14 | 12 | 14 |
| 16 | 15 | 12 | 15 |
| 18 | 17 | 14 | 17 |
| 20 | 18 | 15 | 18 |
| 24 | 22 | 18 | 22 |

Per source with `n_s` = 2, 3, 4, 5, 6, 8 or 10, the requirement is 2, 3, 3, 4, 5, 6 or 8 complete. A source with 2–3 relations therefore needs perfect preservation. Compounds: `N_c` = 5–9 needs **all** correct; 10 needs 9; 15 needs 14.

**Outcomes** (`r17score.outcome()`, fixture O01):

| Outcome | Condition | Meaning |
|---|---|---|
| **O2** | OPQ passes D under A1 and A2, and FULL passes T1–T6 under A1 and A2 | provisional typed-layer default for the next research round (exact clauses still the leaves); **requires new-source replication** |
| **O1** | OPQ passes D under both; FULL fails or is futile under at least one adjudicator | provisional clause-only default for the next research round; typed layer not adopted; requires replication |
| **O1-disputed** | OPQ passes under both; FULL passes under one and fails under the other (both complete) | as O1; the disagreement is reported |
| **O1-untestable** | OPQ passes under both; fewer than 5 compounds (FULL omitted) | as O1; typed layer untested |
| **O1-incomplete** | OPQ passes under both; the FULL phase hit a terminal halt | as O1; typed comparison partial |
| **O3** | OPQ fails D under both, or fails mechanically (D1/D5) | no default adopted under this protocol |
| **O4** | the adjudicators split on OPQ D | inconclusive; no adoption |
| **P** | a terminal halt during the OPQ phase | partial evidence only; no decision |

Every outcome rests on one sample per cell, three sources and an AI-authored reference. Two adjudicators agreeing does not remove generation noise or shared reference error, and relations within a notice are not independent. The thresholds are absolute research gates, not significance tests. FINAL.json reports, for each criterion, the **margin in items** (observed count minus required count). An adoption with margin 0 on any criterion is labelled **"at threshold — fragile"**. It also reports the E10 reference-defect sensitivity result.

## 12. Execution order (each step frozen before the next)

1. Freeze this protocol, BUDGET, REFERENCE-SPEC, ADJUDICATION-SPEC, the scorer and the fixtures, after re-review.
2. P5 fixture gate (A1 and A2 on the fixtures; `check.py --adjudications`).
3. E1–E8 references, reviews and freeze. Apply E8 replacements if needed. P9 decision. Publish counts.
4. P1 key creation and verification (by the user), P2 ledger `INIT`, P3 adapter freeze, dry-run receipts (guards and hashes), P8 auth check, C6 release record, and the optional commit and push of the freezes.
5. OPQ phase with per-call scoring and futility (§8). Freeze the OPQ adjudication.
6. FULL phase if eligible.
7. FINAL.json: every receipt, both score sets, the agreement report, the outcome, margins, sensitivity, and the "not run — futility" entries.

## 13. What this cannot establish

- Run-to-run variance (n = 1 per cell). O1 and O2 are provisional and need replication on new sources.
- Generalization beyond three exception-enriched, short (≤ 6,500 characters) WSR 26-19 proposal notices, or capacity on longer notices.
- Human-gold accuracy; correctness of deadlines or units outside scope relations.
- Invoice-verified spend.
- Schema **enforcement** as opposed to acceptance (`round16-wire-compat/design/DESIGN.md:226`).
- Freedom from prior exposure (F8).
- Cryptographic chronology of the reference freeze (E7).

## 14. Primary decisions incorporated, and open items

Resolved (PRIMARY-DECISIONS, 2026-10-13):

- **Q1.** The $2.00 is a new R17 ledger (BUDGET §4).
- **Q2.** Adapter override with dual hashes (P3, C3).
- **Q3.** Reviewer: GPT-6 Astra (E5).
- **Q4.** No Phase B.
- **Q5.** Retrieval approved and done (F9).
- **Q6.** Keyword screen kept; its exact semantics are now documented (S6).

Open, and blocking release:

- **K.** The user creates and attests the dedicated key. The provider's key-information endpoint and limit-enforcement semantics must be confirmed (BUDGET §1). If they cannot be, nothing is released.
- **AD6.** The latency and granularity of provider key-usage reporting are unknown. If they make AD6 unworkable, it needs a protocol amendment and re-review; it is not silently dropped.
- **Re-review** of this r2 (cross-provider, per the delegation rules) before freeze.
