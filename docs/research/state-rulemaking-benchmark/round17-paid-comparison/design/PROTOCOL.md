# R17 paid comparison: clause-only (opaque) vs full profile, protocol design

Status: **advisory design draft (r17.d1)**. It authorizes nothing. No provider call, network access or credential access occurred, and no file outside this folder changed. Paths are relative to `docs/research/state-rulemaking-benchmark/` (BENCH). Budget arithmetic is in [BUDGET.md](BUDGET.md).

Labels: **VERIFIED** (file:line, or a reproduced offline command), **PROPOSAL** (a design choice, normative once frozen), **ESTIMATE** (a forecast), **ASSUMPTION** (an unverified premise that a stop rule guards).

## 0. Question

On new, never-used source-only inputs, does the r16.w2.1 **opaque** (clause-only) profile preserve scope and exception clauses completely, and link them correctly, well enough to become the default? Does the **full** profile's typed logic layer (AND/OR/NOT/EXC/ALT) add correct structure without losing clauses or output headroom? This is a research default decision only. `production_eligible` and `action_ready` stay false whatever the outcome.

## 1. Verified facts the design rests on

- F1. r16.w2.1 offers two profiles. `opaque` permits only L/R nodes with `a=[]` and appends an instruction to keep complete clauses in exact fragments. `full` permits AND/OR/NOT/EXC/ALT. Source: `round16-wire-compat/protocol-w2-1/wire.py:240-243,308-318`; operator and role enums at `round15-condition-preservation/protocol-revised/compact.py:18-20`.
- F2. Link roles are `if, onlyif, unless, regardless, obj, acts, qual`. A unit may carry at most one link each of if/onlyif/unless/obj. `qual` requires link q≠0 and unit p2/q≠0. Source: `round15-condition-preservation/protocol-revised/stage-a.system.txt` (the "Each l link" paragraph).
- F3. Request settings come from frozen r15.1 bytes with `max_tokens: 8192` (`request-settings.json:4`, loaded at `wire.py:329`). Raising the cap therefore changes the dispatched body away from the `build()` body.
- F4. `validate_response` requires finish `stop` (`wire.py:263`). It rebuilds `build(source, profile)` and requires `plan.request_sha256` to equal the rebuilt hash (`wire.py:275`). The plan passed to validation must be the unmodified `build()` plan.
- F5. Open items stated by R16: provider acceptance of the depth-8 schema, output headroom, and extraction quality are all unverified. A dispatch adapter must recompute the guard and the request hash on the actual body and raise the output cap. Source: `round16-wire-compat/README.md:25-31`.
- F6. Structural validity does not establish meaning. Shortened leaves, missing links, wrong governed units and swapped operators can all pass validation. Source: `round15-condition-preservation/README.md:22`. R14's real output had truncated qualifications in units 88, 95, 96, 98 and 99 (`round14-semantic-contract/RECOVERY.md:23`).
- F7. R14's reference and assessment ran in the **same** Fable session (`round14-semantic-contract/assessment/REPORT.json`, `roles.semantic_judgments`). Fable's summary totals disagreed with its own entries, so they went unused (`RECOVERY.md:29`).
- F8. Selection universe: the frozen WSR 26-19 PROP frame (`round12-automated-scope/source/FRAME.json`) and the ordered candidate list (`round14-semantic-contract/source/SELECTION.json:30-222`). The used notices are 26-19-016 (R12/R13) and 26-19-023 (R14, plus R15/R16 development). An exact-ID search of BENCH, including `artifacts/` (run 2026-10-13), found the other seven eligible IDs only in FRAME.json and SELECTION.json. **No candidate source text exists in the repo**, so retrieval is required.
- F9. Offline sizing of the two in-repo texts is in BUDGET.md V11. Both fit with more than 15,000 bytes of guard headroom.

## 2. Arms

- **R1. Arm OPQ:** r16.w2.1 `build(source, "opaque")`.
- **R2. Arm FULL:** r16.w2.1 `build(source, "full")`.
- **R3.** Both arms use the same sources and the same request settings except the profile. The settings are model `openai/gpt-6.1-sol`, reasoning low, `max_price`, provider pinning, and one declared delta: `max_tokens` 8,192 → **16,384** (C2). One sample per arm per source.
- **R4. No R14-format arm on fresh sources (PROPOSAL, justified).** Running R14's format is *possible*: r14.2 passed the R14 checker and returned HTTP 200. The R14 checker incompatibility concerned r15's schema, not R14's own. It is excluded from the comparison for these reasons:
  - (a) **Unfair scoring.** r14.2 has no clause fragments or scope links. M3/M4 would be mechanical for two arms and judgment-only for the third, which biases the comparison.
  - (b) **Its failure mode is already shown.** R14's real output on a fresh source truncated qualifications (F6).
  - (c) **R15 names exact-clause preservation as the baseline** for any typed layer (`round15-condition-preservation/README.md:28`).
  - (d) **Budget.** Three more calls would reserve about $0.55, taking the total to about $2.17, over the cap (BUDGET §5). Fitting it would mean cutting to 2 sources.
  - (e) **Engineering cost.** The R14 runtime is pinned to a single source (`runtime/input-pins.json`, `sizing-decision.json`).
- **R5. Optional Phase B (not authorized by this protocol).** One R14-era comparison is cheap and honest: run OPQ and FULL on **26-19-023**, where R14's completed output already exists, as a **labelled regression control**. It is a known-failure, design-exposed source, so it never counts toward the decision rule (§9). It needs a new source-only scope/exception reference made in a fresh session, a separate primary release, and the BUDGET §6 rule-5 feasibility check.

## 3. Sources

- **S1. Count:** **3** new sources. Phase A is 3 × 2 = 6 calls.
- **S2. Universe:** the frozen WSR 26-19 PROP frame (F8). Exclude 26-19-016 and 26-19-023: they are prior test inputs and 26-19-023 is a known failure. Immediately before selection, re-run the exact-ID and URL search over all of BENCH, `artifacts/` included, and freeze the result.
- **S3. Prospective size rule:** frame `readable_text_chars ≤ 6,300`, applied to frozen metadata before retrieval. Eligible in ascending ID order: **26-19-039 (4,845), 26-19-041 (5,818), 26-19-106 (4,117), 26-19-116 (3,202), 26-19-123 (6,220), 26-19-135 (6,184)**. 26-19-133 (7,539) is excluded by this rule. The rule is tighter than R14's 8,000 so the full profile's output has room under 16,384 tokens (BUDGET §4, ESTIMATE).
- **S4. Retrieval and extraction:** repeat R14's method. Use an unauthenticated, time-bounded GET of the official URL, archive the exact bytes, and extract with a copy of `round14-semantic-contract/source/extract_source.py` (stdlib HTMLParser), all hash-pinned. Retrieval is a separately approved network step; this design performs none. Retrieve all six S3 candidates before any screening, so screening cannot depend on retrieval order.
- **S5. Post-extraction mechanical gates:**
  - extracted body ≤ 6,500 characters;
  - `measure(source, p)` returns `under_guard` for both profiles, with guarded bytes ≤ 32,000;
  - `build()` succeeds for both profiles.
- **S6. Content-blind structure screen (PROPOSAL).** A frozen script counts case-insensitive, whole-word lexicon hits in the extracted body. No human or model reads the text for screening.
  - Exception class: `unless, except, exception(s), exempt, exemption, waive(r), notwithstanding, excluding, other than, in lieu of, does not apply, do not apply`.
  - Scope class: `if, only if, provided that, subject to, applies to, apply to, applicable to, limited to, only`.
  - **Pass** requires ≥ 1 exception-class hit and ≥ 3 total hits.
  - Limitation: WSR CR-102 boilerplate may contain such words. That is acceptable, because the reference decides the real structure (E8).
- **S7. Selection:** the first 3 candidates in ascending ID order that pass S5 and S6. If fewer than 3 pass, build a new frame for WSR 26-20 with the R12 FRAME method, freeze it before retrieving candidates, and continue in its ascending order. Record every disposition.
- **S8. Freeze:** `sources/READY.json` pins the original bytes, extracted text, extraction script, screen script and output, `measure()` output for both profiles, the selection trail and the prior-use search. No reference, prompt exposure or output is involved yet.
- **S9.** Before any dispatch, the people involved may read the sources only to write the reference. Sources are never edited, clipped or chunked. A source that fails S5 is skipped, never trimmed.

## 4. Reference expectations (frozen before any model output exists)

- **E1. Author:** Fable 5.1 (`claudeAgent` / `claude-fable-5-1`, effort high, claude.ai subscription; confirm `authMethod: claude.ai` and no API-key override first). One **fresh session per source**. That session never sees outputs and never assesses them (fixes F7).
- **E2. Exposure:** the extracted `parsed-body.txt` and the frozen `REFERENCE-SPEC` (E3) only. The author does not see r15/r16 prompts, the wire format, link-role names, the R14 outputs or references, or the arm hypotheses. Markup-only facts may be noted in `out_of_scope_notes` and are never scored (as in R14).
- **E3. Neutral reference schema (PROPOSAL; frozen as `REFERENCE-SPEC.md` before E1 runs):**
  - `targets[]`: `{tid, quote, occurrence, gloss}`. The quote is the governed assertion (what is conditioned or excepted).
  - `relations[]`: `{rid, tid, clause_quote, clause_occurrence, connective_quotes[], relation, critical, critical_reason, contested, contested_reason}`.
    - `relation` ∈ {`COND` (if/when/where), `RESTRICT` (only if/only/limited to/applies only to population), `EXCEPT` (unless/except/exempt/does not apply), `IRRESPECTIVE` (regardless/notwithstanding), `UNRESOLVED`}.
    - `connective_quotes` mark marker words such as "unless" or "or" so M3 can exclude them (M3 note).
    - `critical` = mis-scoping would change what a busy reader may or must do: who may comment, which rule or deadline applies, whether an obligation applies.
  - `compounds[]`: `{cid, tid, connective ∈ {and, or, alternative, exception_to, unspecified}, members[rid…] (ordered [base, carveout] for exception_to), connective_quote, critical, contested}`.
  - `out_of_scope_notes[]`.
- **E4. Mechanical quote check:** a script resolves every quote and occurrence to exact codepoint ranges in the source. Any miss returns to the author, still before outputs. Iterations are logged.
- **E5. Independent review:** a second model sees the source, `REFERENCE-SPEC` and the reference, never outputs. It files objections: missing relations, wrong target, wrong relation class, wrong compound connective or order, over- or under-flagged `critical`. Default reviewer: GPT-6 Astra, high, through the T3 Codex provider (cross-provider; never an `openrouter/*` model). Fallback: Opus 5.5, high (subscription). See Q3.
- **E6. Adjudication:** the author answers each objection once. Items still unresolved after **two** review rounds are marked `contested:true` with both positions recorded. Contested items leave the primary denominators and are reported separately.
- **E7. Freeze:** `reference/READY.json` pins, per source, the prompt, raw result, reference JSON, quote-check output, review transcripts and adjudication log, with UTC timestamps, model IDs and effort. Its SHA-256 must appear in the dispatch release record (C6). That proves ordering: reference before outputs. The reference never enters a request.
- **E8. Sufficiency (checked at freeze time, before dispatch):**
  - each source has ≥ 2 non-contested relations and ≥ 1 `EXCEPT` or `RESTRICT`;
  - pooled ≥ 12 non-contested relations;
  - pooled ≥ 5 non-contested compounds, needed for typed criteria T4.
  - A source failing its per-source floor is replaced by the next S7 candidate. This is still pre-output, so it is not selection on outcome. Record the replacement. If pooled compounds stay < 5 after S7 is exhausted, typed-logic accuracy is declared **untestable** in advance and the FULL arm can be judged only on D criteria.
- **E9. Crosswalk (PROPOSAL; frozen by the primary with reviewer sign-off before dispatch; neither the reference author nor the assessor writes it):**

| Reference relation | Correct | Hedged (not correct, not harmful) | Polarity inversion (harmful) |
|---|---|---|---|
| COND | `if` | `onlyif`, `qual`(q≠0) | `unless`, `regardless` |
| RESTRICT | `onlyif` | `if`, `qual`(q≠0) | `unless`, `regardless` |
| EXCEPT | `unless`; FULL only: carve-out child of an `EXC` node under a target link | `qual`(q≠0) | `if`, `onlyif`, `regardless` |
| IRRESPECTIVE | `regardless` | `qual`(q≠0) | `if`, `onlyif`, `unless` |
| UNRESOLVED | any role with link q≠0 | — | — (excluded from primary denominators) |

Any other role (`obj`, `acts`) on a scoped relation is **wrong role**: not correct, but not a polarity inversion. Compound mapping (FULL): and→`AND`; or→`OR` (hedged: `ALT` with q1); alternative→`ALT` or `OR`; exception_to→`EXC` with children [base, carveout]; unspecified→any operator with q≠0.

- **E10.** Assessors may file "reference defect" notes after seeing outputs. These are reported and run as a sensitivity analysis but **never change primary scoring**.

## 5. Calls and request

- **C1. Calls:** 6. Order is pre-registered and balanced ABBA:
  1. S1-OPQ
  2. S1-FULL
  3. S2-FULL
  4. S2-OPQ
  5. S3-OPQ
  6. S3-FULL

  Sources are numbered by ascending WSR ID. Calls are sequential, and each completes, with its receipt, before the next release.
- **C2. max_tokens = 16,384.** This is 2.27× R14's observed 7,231. Justification: BUDGET §4–5 (worst case $0.26384 per call, $0.27 reserved, $1.62 total). ESTIMATE of need for a source of 6,500 characters or less:
  - base units ≈ 1.0 token per source character (R14: 7,231 / 7,208, one observation);
  - per scope relation, about 150–210 tokens (OPQ) or 280–400 tokens (FULL), from R15 authored pair sizes (`round15-condition-preservation/README.md:14-15`) at 3.14 B/token, plus about 8 tokens per object fragment (`round16-wire-compat/design/DESIGN.md:269`);
  - at 20 relations: OPQ ≈ 10.7k, FULL ≈ 14.5k. FULL may therefore exceed the D5 headroom bar. That is a legitimate finding, not a design flaw.
- **C3. The only body delta from `build()`:** `max_tokens` 8,192 → 16,384. No other key changes. The dispatcher must:
  - (a) construct the dispatched body from `plan["body"]` with exactly this delta;
  - (b) recompute the guard on the exact dispatched bytes (≤ 40,000) and `dispatched_body_sha256`;
  - (c) record both `plan.request_sha256` (`build()` hash) and `dispatched_body_sha256`;
  - (d) call `validate_response(raw, finish, source, plan["table"], plan["profile"], plan=plan)` with the **unmodified** `build()` plan (F4).

  Whether the delta is applied by the dispatcher or by a thin r17 wrapper is Q2. Either way, the plan stays bound to `build()`.
- **C4. No automatic retry, repair, clipping, chunking, narrowing, fallback model or prompt change.** This keeps R14's norm (`round14-semantic-contract/runtime/adapter.py:97`: `automatic_retry: False`).
- **C5. Retained per call:** raw response bytes and SHA-256; the content body; `finish_reason` and native finish; model; provider; `usage` (prompt, completion, reasoning, cache read/write); reported cost; the debit; and the validation result or `WireError.code`. A rejection receipt is written for every `ValueError`.
- **C6. Release record before call 1** pins: this protocol's READY hash, `sources/READY.json`, `reference/READY.json`, the crosswalk, the frozen scorer and rubric hashes, the six plan hashes plus dispatched-body hashes, the ledger initial state, and Q1's answer.
- **C7. Re-release (the only departure from R14, narrowly bounded).** The primary may re-dispatch a planned call **once**, by explicit release and never automatically, only if:
  - the first attempt returned **no model content at all** (transport error, timeout before body, HTTP 5xx/429 with no `choices`);
  - **and** BUDGET §6 rule 5 holds, with the failed attempt debited at its full $0.27.

  A response with any content (truncated, invalid, rejected or valid) is never re-dispatched, because that would select on outcome. Re-dispatching a contentless failure cannot bias arm comparison, because no output was observed.

## 6. Stop rules

**Run-halting rules.** No further releases; Phase A ends.

- **H1. Pre-dispatch integrity:**
  - any `build()` failure;
  - dispatched-body guard > 40,000;
  - a body delta other than C3;
  - a missing or mismatched READY, reference or crosswalk hash;
  - Q1 unresolved.

  Outcome: no spend; fix offline.
- **H2. Provider schema rejection:** any HTTP 4xx, or any error naming `response_format`, the schema, a parameter or an unsupported keyword, on **any** call. Outcome: "provider acceptance failed for r16.w2.1". That is a dispatchability *result*, but quality is inconclusive. The first call (S1-OPQ) serves as the acceptance probe. FULL has the same depth and a superset of operators, so an OPQ rejection implies a rework for both.
- **H3. Budget:** a release would make `cumulative_debit + 0.27 > 1.80`.
- **H4. Price drift:** a receipt where `reported_cost > prompt_tokens × 2.5e-6 + completion_tokens × 1e-5 + $0.0001`, or `reported_cost > $0.27`.
- **H5. Cap breach:** `completion_tokens > 16,384` (assumption A1 has failed).
- **H6. Identity:** returned model ≠ `openai/gpt-6.1-sol` or provider ≠ OpenAI. The response is retained and excluded.
- **H7. Baseline does not fit:** any **OPQ** call ends with `finish_reason = length`. The clause-only baseline exceeds 16,384 tokens, FULL will not fit either, and the cap or size plan needs revision.
- **H8. Unexpected termination:** `finish_reason` ∉ {stop, length}, for example `content_filter` or `error`.
- **H9. Transport failure** with no content. Pause; continue only through C7.
- **H10. Integrity:** a raw response is not retained or hashed, a ledger write fails, or a receipt is inconsistent.

**Arm-level rules.** These do not halt the run.

- **A1. FULL truncation** (`length`): record an output-fit failure for that source. No repair, salvage or retry.
- **A2. Validation failure** (`WireError`/`ValueError` after `stop`): record a structural failure with its code. No repair.
- **A3. Futility:** after 2 FULL failures under A1/A2, skip the remaining FULL call, since FULL already fails D1. Release OPQ calls normally.
- **A4.** A run halted by H2–H10 keeps every completed receipt. They are reported as partial evidence, never as a decision.

## 7. Result vs inconclusive

- **Result:** all 6 planned calls are resolved. Each call is valid or failed for an arm-attributable reason (A1/A2, or A3 skip), and G0 holds (§9). The decision outcome is O1, O2 or O3.
- **Partial findings,** reportable but not a decision: provider acceptance of the r16.w2.1 schema (yes after the first HTTP 200 with a valid parse); observed completion tokens and tokens per character per arm; cost.
- **Inconclusive (O4):** any H2–H10 halt before all six are resolved; G0 fails; or the outcome differs between the two adjudicators (M-note).

## 8. Metrics

All metrics apply per source and pooled, over non-contested reference items unless stated. Mechanical metrics come from a **frozen scorer script**, implemented and tested on authored fixtures before C6. Assessors never compute totals (F7).

- **M1. Structural validity:** finish `stop` and `validate_response` passes. Binary per call.
- **M2. Output use:** `completion_tokens`, `reasoning_tokens`, fraction of 16,384, completion tokens per source character, and the FULL/OPQ completion ratio per source and pooled.
- **M3. Clause-preservation completeness.** Let K(rel) be the codepoints of the clause range that are not whitespace, minus the reference's `connective_quotes` codepoints and one trailing `. , ; :`. Coverage is the union of fragment ranges (leaf `x`, operator `x`, link `x`) of all nodes reachable from links whose unit is in U(tid). U(tid) is the set of output units mapped to the reference target. Candidates are units whose `e` spans overlap the target quote's rows; the assessor confirms the mapping.
  - complete: K ⊆ coverage
  - partial: 0 < |K ∩ coverage| < |K|
  - absent: no overlap

  Report the complete-rate (primary) and M3b, "preserved anywhere" (coverage by any fragment in the output).
- **M4. Scope-link accuracy, end to end** (denominator: all non-contested relations).
  - A relation is **correct** if M3 is complete, a covering leaf is reached through a link to a unit in U(tid) with a Correct role (E9), and no single leaf under that link fully contains another non-contested relation's clause of a conflicting class for the same target (the "conflated leaf" check).
  - Hedged and wrong are reported separately.
  - Also report correct + hedged.
- **M5. Harmful errors**, counted per arm, with `critical` flagged:
  - polarity inversion (E9);
  - wrong governed unit on a critical relation;
  - conflated leaf;
  - a partial-coverage leaf on a critical relation whose link has q0 (silently shortened, as in F6).
- **M6. Typed-logic accuracy** (FULL only; denominator: non-contested compounds). Correct if an operator node maps per E9 and its child subtrees cover distinct members (EXC order [base, carveout]).
  - Typed harmful errors: AND↔OR swap, EXC order reversed, and invented connective (a q0 operator joining leaves where the reference has no compound, or has `unspecified`).
  - For OPQ, M6 is N/A by design. Its compounds are scored through M3/M4 only.
- **M7. Calibration** (reported only): the share of contested or UNRESOLVED reference items the output marks with q≠0.
- **M8. Over-breadth** (reported only): |coverage| / |K| per matched relation; flag values above 3.

**M-note: assessment procedure.**

- **Adjudicator 1:** Fable 5.1, high, in a **fresh session** that is neither the reference author nor its reviewer. It confirms U(tid) mappings, M4 and M6 judgments, and M5 flags.
- **Masking:** outputs are shown as "A"/"B" under a pre-registered seed. FULL is recognizable by its typed nodes, so the masking is partial; this is a limitation.
- **Adjudicator 2:** Opus 5.5, high, independently judges every critical item and a pre-registered 50% sample of the rest.
- **Disagreement:** compute the decision under both adjudicators' judgments. If the outcome differs, the outcome is O4 for that criterion. Report agreement.

## 9. Decision rule (thresholds fixed now)

**G0. Evidence gate** (otherwise O4): all 6 calls resolved per §7; E8 sufficiency met (compound sufficiency only gates T4); adjudicators agree on the outcome.

**D. Default bar** (applied to an arm):

- **D1.** M1 valid on 3/3 sources.
- **D2.** M3 complete-rate pooled ≥ **0.90**, and ≥ **0.75** on every source.
- **D3.** M4 correct pooled ≥ **0.75**, and correct + hedged ≥ **0.90**.
- **D4.** **Zero** critical polarity inversions; ≤ **1** other harmful M5 error pooled.
- **D5.** Every call's `completion_tokens` ≤ **13,926** (85% of 16,384). This keeps operational headroom: 19 of 28 frame notices are longer than 8,000 characters (`round14-semantic-contract/source/SELECTION.json:10,12`).

**T. Typed-layer bar** (FULL, compared with OPQ):

- **T1.** FULL passes D1–D5.
- **T2.** FULL M3 complete count ≥ OPQ count − 1 (non-inferior preservation).
- **T3.** FULL M4 correct count ≥ OPQ count.
- **T4.** ≥ 5 non-contested compounds exist (else "typed untested"), and M6 correct ≥ **0.90**.
- **T5.** Zero critical typed harmful errors; ≤ 1 total.
- **T6.** Pooled FULL/OPQ completion-token ratio ≤ **1.5**.

**Outcomes:**

- **O1. Adopt clause-only as default; typed layer not adopted:** OPQ passes D, and FULL fails any T (including "typed untested").
- **O2. Adopt the typed layer** (FULL profile as default, with exact clauses still as leaves): OPQ passes D, and FULL passes T1–T6.
- **O3. Neither ready:** G0 holds and OPQ fails D. A variant, **O3b**, applies if FULL passes D, T4, T5 and T6 while OPQ fails D. That is anomalous enough to require replication before any adoption.
- **O4. Inconclusive:** G0 fails.

Every outcome is one sample per arm on 3 sources against an AI reference. Thresholds are absolute bars, not significance tests. A one- or two-item difference between arms is within unmeasured run-to-run variance. Any adoption means "default for the next research round". It is not production readiness.

## 10. Execution order (each step frozen before the next)

1. Resolve Q1–Q6; freeze this protocol, `REFERENCE-SPEC.md`, the crosswalk, the S6 lexicon script, the scorer (with fixture tests), the adjudication rubric and the masking seed.
2. S2–S8 source selection and freeze (network step separately approved).
3. E1–E8 reference, review and freeze.
4. Build 6 plans; apply C3; produce the dry-run receipts (guard and hashes); C6 release record.
5. Dispatch in C1 order under §6.
6. Run mechanical scoring, then adjudicators 1 and 2, then apply the decision rule; write FINAL.json with every receipt.

## 11. What this cannot establish

- Run-to-run variance (n = 1 per cell).
- Generalization beyond one WSR issue and short notices (≤ 6,500 characters).
- Human-gold accuracy.
- Correctness of deadline dimensions or units outside scope relations (recorded, not scored).
- Invoice-verified spend.
- Whether the provider *enforced* the schema rather than merely accepting it (HTTP 200 shows acceptance only; `round16-wire-compat/design/DESIGN.md:226`).

## 12. Open questions for the primary

- **Q1. Ledger:** is the $2.00 a fresh R17 ledger? If it is cumulative with R14's $1.906, R17 cannot run (BUDGET §6.6).
- **Q2. max_tokens delta:** dispatcher override with a dual-hash record, or a thin r17 request wrapper? The transport-mapping task decides; C3's invariants must hold either way.
- **Q3. Reference reviewer:** GPT-6 Astra via Codex (cross-provider, default) or Opus 5.5 (subscription)? Does Codex-provider use count against anything? It is not OpenRouter spend.
- **Q4. Phase B:** run the 26-19-023 regression control (2 calls) after Phase A if the observed debit allows?
- **Q5. Network approval** for retrieving six WSR notices (S4), and who performs it.
- **Q6. Screen:** accept the S6 lexicon screen, or prefer a pure first-3-by-ID rule? The pure rule is less selective but risks sources with no exception structure, caught later by E8 replacement.
