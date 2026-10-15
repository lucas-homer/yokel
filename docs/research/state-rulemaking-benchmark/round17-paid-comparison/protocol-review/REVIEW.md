# R17 adversarial protocol review

**Verdict: freeze after edits; do not freeze r17.d1 as-is.** The paired, source-only research comparison is viable. Its arithmetic is mostly correct, but its hard-cap claim, reservation accounting, semantic scoring and adjudicator agreement gate are not ready. This review neither authorizes dispatch nor proposes increasing the user's $2.00 cap.

Reviewed offline on 2026-10-13. Paths below are relative to `docs/research/state-rulemaking-benchmark/` unless stated otherwise. Only this review was written; no network/provider calls, credential access, installs or commits. Python was invoked only as `python3 -I -S -B`.

The reviewed design files match `round17-paid-comparison/design/READY.json`:

- `PROTOCOL.md`: `8a9904082c0839a70a1117c76fc7ca0691d04968b3bdf0b69be1985b81f44ccb`
- `BUDGET.md`: `35e685a18d2343d2b55a521bcb7264c142ddb4c571a1e33c8cfdb9af68079385`

## Re-derived budget and what the receipts establish

Evidence: R14 `execution/run/result.json:1`, `execution/run/ledger.json:1`, `recovery/PRIMARY-POSTRUN.json:9-14`, and `runtime/adapter.py:9-24,113-125`. These are one observation, not a current provider price contract.

| Quantity | Re-derived value |
|---|---:|
| Prompt tokens / completion tokens | 6,730 / 7,231 |
| Nested reasoning tokens / cache-write tokens / cached tokens | 57 / 6,727 / 0 |
| Reported prompt / completion cost | $0.0168235 / $0.0723100 |
| Effective prompt rate | $2.499777117384844 per million |
| Completion rate | exactly $10 per million |
| Cache-write rate, **conditional on $2/M for the remaining 3 tokens** | exactly $2.50/M |
| R14 nominal estimate: 6,730 × $2/M + 7,231 × $10/M | $0.0857700 |
| Cache-write increment: 6,727 × $0.50/M | $0.0033635 |
| Reported total | $0.0891335 |
| All-prompt-at-$2.50 estimate | $0.0891350 |
| R14 actual conservative debit | max($0.20, $0.0891335, $0.0857700) = **$0.20** |
| Conditional R17 maximum: 40,000 × $2.50/M + 16,384 × $10/M | **$0.26384/call** |
| Six conditional maxima / six $0.27 reservations | **$1.58304 / $1.62** |
| Margin of six reservations to new $2 cap / $1.80 operating limit | $0.38 / $0.18 |

**The design did not accidentally choose the wrong observed rate.** Its $2.50/M prompt allowance is a sensible envelope for this receipt. However, the receipt does not separately identify the base and cache-write unit prices; the $2/$2.50 split assumes the base price from the adapter/settings. A single weighted observation cannot prove bounds for every future billing category.

R14 reports `total_tokens:13961 = 6730 + 7231`, and places `reasoning_tokens:57` inside `completion_tokens_details`. Its completion bill equals `7231 × $10/M`; adding 57 again would give $0.07288, inconsistent with the receipt. This supports treating reasoning as included, without double-counting, for this observed call. It does **not** prove enforcement of `max_tokens` on the route: R14 ended `stop` at 7,231, below 8,192. There is no cap-hit evidence here. BUDGET A1 correctly calls that unproven; §2 should use equally qualified wording.

The inherited `request-settings.json` pins prompt/completion `max_price` to **2/10**, OpenAI routing, no fallback, low reasoning and 8,192 output tokens. R17 changes only the last value to 16,384. R14's prompt cost exceeded `6730 × $2/M` by $0.0033635 while that price setting was in use. Thus **2 is not an observed all-in prompt-billing ceiling**; the cache-write interpretation explains the difference. The receipt does not prove how the setting limits other surcharges. Do not raise it silently: C3 permits only the output-cap delta.

## BLOCKER findings

### B1. Post-response alarms are not enforcement of the hard $2 cap

**Evidence:** BUDGET §§3–6; PROTOCOL H3–H5; R16 `protocol-w2-1/wire.py:335-344`.

The byte guard is `len(serialized_request) + 1024 ≤ 40000`, not a provider token count. Even if the content tokenizer uses at most one token per UTF-8 byte, the provider can add message/schema templates or transform the schema. Neither the template overhead nor a bound on it is established locally. R14's 4.21 B/token observation is slack in one request, not a proof for another request/schema. The S5 32,000-byte screen adds practical slack but does not establish the missing contract.

BUDGET A2 says H4 checks prompt tokens. H4 actually checks **cost against observed token counts** and $0.27; it never checks `prompt_tokens > 40000`. For example, 45,000 prompt tokens and 10,000 completion tokens billed at the assumed rates cost $0.2125. H4 and H5 both pass despite a violated A2. The missing direct check is a real specification error, although even adding it only detects a violation after spending.

The same timing problem applies to price drift, unbounded/unreported usage, and output-cap enforcement. H4/H5/H10 cannot stop the call that already crossed the cap. The claim that $0.20 covers rate error has no established magnitude bound. The draft's double-price example considers only call 1. At a ledger state of $1.53, H3 admits another $0.27 release; a doubled conditional maximum costs $0.52768, making **$2.05768** before H4 fires. Such a ledger state is admitted by the draft's retry/recycling rules (three contentless attempts at $0.27 plus three completed attempts at $0.24). Even without retries, five $0.27 debits followed by a $0.70 charge total $2.05. These are counterexamples to the claimed guarantee if its assumptions fail, not predictions that the provider will overbill.

**Suggested edit — BUDGET §§2–6 and PROTOCOL H1/H4/H5:** Label $0.26384/$1.62 as **conditional bounds**, state the exact conditions, and remove the unconditional “cannot exceed” and arbitrary double-price guarantee. Make dispatch conditional on documented enforcement sufficient for the hard authorization: either an experiment-isolated provider spending limit that actually rejects charges beyond its remaining allowance, or verified all-in rate/token/overhead bounds enforced before dispatch. A signed manifest, byte guard or post-response ledger alone does not supply that enforcement. If neither can be established, the paid phase stays unreleased; do not substitute a soft budget for the approved hard cap. Add explicit prompt, completion, nested usage and finite/nonnegative cost checks with fail-closed receipts, while stating that these are anomaly detection, not retroactive cost prevention.

### B2. The proposed debit drops the reservation floor and retries do not reserve the remaining experiment

**Evidence:** BUDGET V8 versus §6 rules 2/5; PROTOCOL C7/H3/G0; R14 adapter `recoverable()` and `native()`.

R14 uses `max(reservation, reported, rate_estimate)` on success and failure. R17 rule 2 changes this to `max(reported, rate_estimate)` when usage exists. That is an unacknowledged policy change, not reuse of conservative R14 accounting. It also allows under-reported usage to release reservations.

**Six × $0.27 does survive the R14 formula** if the new reservation is $0.27 and the conditional bounds hold: the floor sets every debit to $0.27. Even retaining the literal old $0.20 floor would not push six bounded calls above $1.62. The error is dropping the floor, not an arithmetic need to add $0.20 on top of $0.27.

C7 checks the next retry, not the funding of all unresolved required calls. With the corrected $0.27 floor, a failure plus its successful retry plus the other five planned calls costs seven reservations, **$1.89 > $1.80**. The retry can be permitted early, then the last required call is blocked, guaranteeing G0 failure after paid work. The $1.62 table describes six attempts, not six successful cells plus retries.

**Suggested edit — BUDGET §6 and PROTOCOL C7/C6:** Debit in integer nanoUSD as `max(270000000, upward_rounded_reported, conservative_rate_estimate)` for every possibly dispatched attempt; recover available billing evidence even from rejected responses. Keep an exclusive, durable R17 aggregate that includes unresolved/pending reservations before any new release, and reconcile it after crashes. Admission must reserve **all remaining required calls**, not merely the next one. With the present $1.80 operating limit and this floor, delete the R17 retry allowance; a contentless failure ends the paid phase as partial/inconclusive. Any different attempt plan requires revised arithmetic and review within the same $2 authorization. Do not recycle uncertain charges or conflate this ledger with R14's historical balance.

### B3. “Complete preservation” and “scope correct” can reward missing logic or the wrong path

**Evidence:** PROTOCOL E3/E9/M3–M6, especially lines 162–179; r15.1 `stage-a.system.txt` definitions of fragments, links and operators.

- M3 removes connective words, including `or`, from required coverage. For a clause “unless A or B”, an opaque leaf with separate exact fragments “A” and “B” under an `unless` link can pass M3/M4 while losing the `or`. OPQ has no M6 safeguard. If the reference instead splits A/B into relations, the compound connective is still unscored for OPQ. This can reward precisely the clause loss the experiment is meant to detect.
- M3 unions **all** fragments under **all** links for a target. A clause assembled partly from one correct link and partly from an unrelated/wrong-role link can be called complete. M4's “a covering leaf” does not specify whether that leaf must cover all K, whether a multi-leaf subtree qualifies, or whether M3 coverage from other roots counts. A literal single-leaf requirement also penalizes a faithful FULL decomposition into several leaves. Results depend on how the reference author chose relation granularity.
- U(tid) uses row overlap plus assessor confirmation without a rule for broad evidence, contradictory assertion text, multiple units, duplicate targets or an empty mapping. Same-row evidence is not proof that a unit asserts the target. M8 is only reported, so unrelated broad fragments can earn completeness with no adoption consequence.
- E9 treats any EXC carve-out below a target link as correct without defining the outer link role, intervening NOT/EXC operators or double negation. Its role-only inversion table does not resolve those paths. A `qual` path versus a certain applicability assertion also needs distinct treatment. M6 does not fully specify member matching, extra children, partial coverage, nested/repeated operators or duplicate compound matches.
- E3 provides occurrences for target/clause quotes, but no occurrence field for each connective quote. Repeated `or`/`unless` strings make E4's claimed exact range resolution ambiguous. “Hedged” also lacks explicit completeness, mapping and contradiction prerequisites.

**Suggested edit — PROTOCOL E3/E4/E9/M3–M6:** Preserve every meaning-bearing connective and negator in exact evidence for **both** arms; allow its evidence in leaf, operator or link fragments, but do not delete it from the requirement. Give every quoted occurrence explicit source offsets/occurrence resolution. Freeze relation/compound segmentation rules. Score a relation through one identified target-link-root/subtree witness with complete member coverage and an explicitly supported semantic path; never borrow coverage from another role/path. Define unit matching by assertion meaning plus evidence, empty/duplicate mappings, uncertain versus asserted roles, broad/conflicting leaves, EXC/NOT composition and error precedence. Include authored fixtures for the cases above and require both adjudicators to produce the same machine-readable judgments on them before freeze. If coverage and semantic sufficiency are separate metrics, call M3 “text coverage” and gate adoption on the latter too.

### B4. D permits critical omissions and some critical scope errors

**Evidence:** PROTOCOL D2–D4/M5/E9.

A permitted concrete result has 12 relations, four per source: 11 complete, one **critical relation absent**, nine correct and two hedged. It meets pooled M3 11/12 = 0.9167, minimum per-source M3 3/4 = 0.75, M4 correct 9/12 = 0.75 and correct-plus-hedged 11/12 = 0.9167. The missing relation has no partial leaf and no inverted link, so M5 need not flag it at all. D4 therefore permits adoption with a missing critical exception.

Separately, D4 bans critical **polarity inversions**, but permits one “other harmful” error even if it is a critical wrong governed unit, critical conflation or silently shortened critical leaf. E9 counts `COND→onlyif` and `RESTRICT→if` as harmless hedges without requiring uncertainty; a confidently strengthened/weakened restriction may change applicability. The wire prompt says `if` asserts neither sufficiency nor necessity, so this must be adjudicated from the asserted meaning, not by assuming formal Boolean implication.

**Suggested edit — PROTOCOL D/M5/E9:** Require complete preservation and a correct, or explicitly unresolved and non-assertive, target/role for **every critical relation**. Count critical absence, wrong target, lost connective, contradictory extra applicability claims and overconfident scope changes as critical failures. Change D4 to “zero critical harmful errors of any category”; keep any one-error allowance only for noncritical errors. Define when a role substitution is a harmless explicit hedge, rather than granting that status from the role name alone. Freeze this policy before references so critical labels cannot be changed after seeing outputs.

### B5. The two-adjudicator outcome is undefined for half the noncritical items

**Evidence:** PROTOCOL M-note lines 185–188 and G0.

Adjudicator 2 scores critical items and only 50% of the rest, but G0 requires agreement on the overall outcome and M-note says to compute it “under both” judgments. There is no rule for the other half of adjudicator 2's entries. Copying adjudicator 1 would yield a hybrid score, not an independently replicated outcome; treating them as missing changes denominators. With only 12 relations, one noncritical item can cross a threshold. “O4 for that criterion” also conflicts with O4 being a run outcome.

**Suggested edit — PROTOCOL M-note/G0:** Have the second adjudicator independently score **all** primary-denominator relations, compounds and target mappings for this small experiment. Freeze the output format, denominator handling and item-level disagreement policy; compute each complete score independently and report one run-level O4 if the outcomes differ. If retaining sampling, label it an audit, define the hybrid explicitly, and use best/worst possible assignments to unsampled items to detect threshold ambiguity; do not call that full adjudicator agreement.

## SHOULD-FIX findings

### S1. Order and futility spend money after adoption is impossible; OPQ truncation does not prove FULL truncation

**Evidence:** PROTOCOL C1/H7/A3/G0/O1–O3 and §10 step 6.

The current order is OPQ1, FULL1, FULL2, OPQ2, OPQ3, FULL3. If OPQ2 truncates, two FULL calls have already been paid and A4 declares the run non-decisive. FULL2 might already have completed successfully on that very source, directly refuting H7's “FULL will not fit either.” Tokens are not a monotone function of profile: exact-clause repetition, shared typed nodes and generation choices differ.

One FULL structural failure already makes D1's 3/3 impossible. Waiting for **two** such failures wastes a further FULL call. A single D5 violation also defeats that arm, but does not stop anything. If OPQ fails D, O2 cannot occur, yet the design continues all FULL calls to identify at most the replication-only O3b. If E8 declares compounds untestable before dispatch, T4 already rules out O2 but three FULL calls are still planned. Those calls can be useful exploratory diagnostics, but should not be sold as necessary for the default decision.

**Suggested edit — PROTOCOL C1/H7/A3/G0/O/§10:** Use the required order below, score prerequisites before funding the next arm, and add explicit early decision states. Count an observed arm failure as a finding, not universal schema rejection. Mark unrun cells “not run—pre-registered futility”; never assign invented scores. If the primary instead wants a complete paired descriptive study, retain a fixed paired order but remove the unsupported H7 inference and accept that the full six calls are diagnostic expenditure regardless of adoption futility. Do not combine the two rationales.

### S2. Transport, HTTP and retry classifications conflict

**Evidence:** PROTOCOL C7/H2/H8/H9/A4.

C7 permits a contentless 429 retry; H2 says **any** 4xx terminates the run as schema rejection. A 401, 402, 403 or 429 is not evidence that the schema was rejected. H9 says pause/continue, while A4 says an H9-halted run is never a decision. “No model content” is undefined for an empty message with reasoning/refusal fields, or HTTP 200 with no choices/usage. A timeout before receiving a body can follow billable generation; absence of observed output does not prove that retries are statistically neutral because timeout probability may depend on output length/profile.

**Suggested edit — PROTOCOL C4/C7/H2/H8/H9/A4:** Following B2, remove retries for this attempt budget. Otherwise write a single ordered response-state table distinguishing parameter/schema rejection, auth/payment/rate-limit failure, content-bearing refusal/error, missing/malformed usage, transport uncertainty and structural invalidity. Any possibly dispatched attempt keeps its debit. Limit “schema acceptance failed” to explicit schema/parameter evidence. Distinguish a resumable pause from a terminal halt, and delete the categorical “cannot bias” assertion.

### S3. Reference isolation is sensible, but a hash is not proof of precedence

**Evidence:** PROTOCOL E1/E2/E5–E7/E10/C6.

The intended design is sound: source-only author; separate reviewer; fresh assessor; frozen primary reference; post-output defects only in sensitivity analysis. No R17 extraction output exists in the reviewed inputs, and I found no evidence of an actual reference leak. The author necessarily sees the reviewer's source-derived objections; that is permitted reference work, not extraction-output contamination.

However, placing a reference digest in a release file proves a content dependency, not when either file was made. A self-reported UTC time adds no independent ordering guarantee. A “fresh session” can still receive inherited parent context, and E5 does not explicitly require a fresh reviewer context. The author may receive objections derived from that context if it is not isolated. Historical-output-informed design is not itself a breach, but a packet carrying historical model answers/arm hints would be.

**Suggested edit — PROTOCOL E1/E2/E5–E7/C6:** Require isolated author/reviewer sessions with no inherited conversation and an enumerated, retained input packet limited to source, neutral spec and reference-review exchanges. Prohibit browsing other benchmark/reference/output files from those sessions. Freeze the neutral spec before source inspection and retain all prompts/attachments/objections. Replace “That proves ordering” with “The dispatch gate must verify this immutable, recorded reference freeze before the first transport attempt.” Bind release hash and reference hash into each durable pre-transport intent/unique claim and preserve the ordered release/dispatch evidence. Do not claim cryptographic chronology from hashes alone.

### S4. The pool is unused as test input, not wholly unseen; screen details remain discretionary

**Evidence and search:** `rg -l -uuu` across **all BENCH**, including `artifacts/` and round frames, for the seven unused ≤8,000-character IDs and their compact numeric spellings returned only R12 `source/FRAME.json`, R14 `source/SELECTION.json` and the R17 draft. No candidate-ID paths were found. A broader separator-tolerant search found unrelated Texas IDs/dates, not additional WA uses. No exact `26-19`/`2026/19` matches appeared in `artifacts/`. This supports **no recorded previous benchmark test use**; it cannot establish absence from external sessions, image-only material, aliases without IDs or training data.

More directly, R12 `source/SELECTION-REPORT.md:5` says **all 28 unique filings were opened** to construct the frame. Thus the blanket “never-used/unseen” phrasing overstates novelty if it means no prior agent exposure. The six S3 candidates and their character counts do match the frozen metadata; 26-19-133 is correctly excluded by 6,300. Excluding the two actual prior test notices is sound.

S3/S5 are prospective mechanical rules, but S6 is not yet executable or fully specified. Do `exception(s)` and `waive(r)` mean optional suffixes? Does “only if” count once or also as “only” and “if”? That phrase plus one exception hit can pass or fail depending on overlap policy. Multiword phrases split by extraction newlines need a fixed whitespace policy. Case folding, word boundaries, inflections and repeated occurrences need examples. No screen script is present in the reviewed R17 tree. This is a preregistered **intent**, not yet a frozen mechanical screen. S7's 26-20 extension also needs the exact inherited size rules, maximum issue/candidate extent and a disposition for retrieval failures. E8 specifies per-source replacement, but not how to handle three passing sources whose pooled relation count is below 12, or how many replacement sets to try for compounds.

**Suggested edit — PROTOCOL F8/S2–S9/E8/§11:** Say “not previously used as extraction/evaluation test inputs in the recorded benchmark; already exposed during frame construction.” If absolutely no prior agent exposure is required, choose a genuinely new frame instead. Freeze exact lexicon expansions, Unicode/whitespace normalization for screening only, longest-match/overlap policy and hit-count fixtures **before retrieval/inspection**, with deterministic ascending selection and exhaustive rejection records. Define a finite fallback and deterministic reference-sufficiency replacements; stop before paid calls if the pooled floor fails. Report the screen as exception-enriched sampling, not content-blind sampling: it is human-blind but depends on content and favors explicit lexical cues over implicit scope. Its shared application is not evidence of favoritism toward either arm, but restricts generalization.

### S5. Achievable thresholds are coarse research gates; 1.5× is a policy choice

**Evidence:** PROTOCOL D/T/O/§11.

At the minimum 12 relations, D2 needs 11 complete; D3 needs 9 correct and 11 correct-or-hedged. A source with 2 or 3 relations effectively needs perfect preservation to meet 0.75. At 5–9 compounds, T4's 0.90 requires all compounds correct; at 10 it suddenly permits one error. These thresholds are mathematically achievable, but highly discrete and sensitive to reference segmentation. Relations within three notices are not independent samples. One draw per cell cannot estimate model variance, and two adjudicators agreeing does not remove generation noise or shared reference error. O2 can therefore choose FULL on a lucky draw. The text already honestly limits adoption to the next research round; keep that limitation.

The 1.5× cap is a defensible cost preference, not a validated quality/utility threshold. Freeze the pooled definition as `sum(FULL completion_tokens) / sum(OPQ completion_tokens)` over complete paired calls, with reasoning included in both. It weights long outputs more heavily, can hide a >1.5× source, and a verbose/duplicative OPQ denominator makes FULL easier to pass. A zero/failed/missing denominator must be undefined, never favorable. D5 measures observed cap headroom, not fit on the much longer excluded notices. T2's one-item loss allowance is roughly 8.3 percentage points at N=12, and should never cover a critical loss.

**Suggested edit — PROTOCOL D/T/O:** Publish required integer counts for the frozen denominators before dispatch; make O1/O2 “provisional default for the next research round, requiring new-source replication.” Retain per-source ratios and total billed/debited cost alongside the pooled ratio; define failed/missing cases. Explain 1.5× as a preselected engineering tradeoff and restrict T2's allowance to noncritical relations. Do not claim statistical superiority, production readiness or extrapolated source-size capacity.

## NOTE findings and primary-decision reconciliation

**N1 — Q1/Q2/Q3 are compatible and should replace open questions in the frozen text.** A new R17 ledger is explicitly approved; the historical **$0.094009282** is irrelevant to R17 capacity and stays untouched. The adapter override with two hashes and an unchanged validation plan matches R16's requirements. The actual guard must remain `len(exact dispatched serialization) + 1024`, not simply request bytes. Pin the adapter and its tests as release prerequisites. The choice of Astra as reference reviewer matches E5. Suggested edit: resolve Q1–Q3 in PROTOCOL and BUDGET rather than leaving competing branches normative.

**N2 — Q4 is a binding “no Phase B”, with a limited arithmetic rationale.** Eight maximum reservations are $2.16, so the primary is correct that **eight fully reserved calls** exceed $2. However, the draft's dropped-floor observed-debit recycling condition could sometimes admit two extra calls; that explains why its optional Phase B language differs. With a $0.27 floor, six successful Phase A calls alone use $1.62 and cannot meet the draft's Phase B threshold of $1.26. Suggested edit: delete Phase B authorization paths from PROTOCOL C7/R5 and BUDGET §6.5 for R17, retaining any regression-control idea only as future work. Do not treat “observed spend was low” as overriding the explicit primary decision.

**N3 — Q5/Q6 resolve preference/authorization, not implementation.** Q5 approves source retrieval; this reviewer made none. The design can record that approval instead of presenting retrieval as unresolved. Q6 accepts the lexicon concept, but does not resolve the overlapping-hit and normalization ambiguities in S4 above. Suggested edit: incorporate these decisions into PROTOCOL Q5/Q6, while preserving the pre-retrieval screen freeze gate. The claim “kept as written (mechanical, pre-registered)” is premature until that script/rule is pinned.

**N4 — Several safeguards are sound.** Same frozen source per arm, no clipping/chunking, no content-bearing retries, exact dual-hash dispatch binding, retained rejected responses, quote anchoring, cross-provider reference review, immutable primary labels, and explicit `production_eligible:false`/`action_ready:false` are appropriate. R14-format exclusion is methodologically defensible without the speculative $0.55 estimate; under R14's literal $0.20 conservative floor, three such calls would debit at least $0.60, and $1.62 + $0.60 = $2.22. Suggested edit: correct or remove R4(d)'s $0.55/$2.17 estimate and retain the clearer unequal-representation/scoring rationale. Do not add a third arm merely to repair that small arithmetic rationale.

## Required call order and freeze conditions

For the stated **default-adoption** objective, require:

1. Finish all offline/source/reference/scorer freezes and budget-enforcement verification. If E8 already makes typed adoption untestable, decide and freeze whether to omit FULL before paying; do not discover that futility after dispatch.
2. **S1-OPQ → S2-OPQ → S3-OPQ**, ascending selected ID. Reconcile each receipt before the next release. Stop on irreversible structural/headroom/critical failure; after three valid calls, adjudicate the complete OPQ D bar before any FULL release.
3. Only if OPQ passes and typed adoption remains testable: **S1-FULL → S2-FULL → S3-FULL**. Skip the remaining FULL calls after the first irreversible T/D failure (including one structural failure, not two), with explicit “not run—futility” receipts. Do not extrapolate unobserved FULL scores.
4. Update G0/O1–O4 to permit a **limited, pre-registered decision** from an observed irreversible failure: OPQ failure means no adoption under this protocol, while fully adjudicated OPQ success plus FULL failure supports the provisional OPQ default. Transport/billing/integrity uncertainty remains partial/inconclusive. O3b and a complete six-cell descriptive comparison are not guaranteed by this staged design.

This order trades the draft's limited temporal balancing for prerequisite-first spending; record that tradeoff. “OPQ truncated, therefore FULL cannot fit” must be deleted regardless of order. If complete paired comparative estimation is instead the objective, revise the stop policy accordingly before freeze rather than pretending the staged design estimates all six cells.

**Acceptance for freeze:** close B1–B5 with concrete protocol/budget edits, implement and freeze the scorer/reference/screen specifications they depend on, reconcile primary decisions, and regenerate design READY hashes. The budget remains **$2.00 hard maximum**, with **$1.62 for six $0.27 reservations only under established rate/token bounds**. No live enforcement verification was attempted in this offline review; that unresolved prerequisite belongs to the primary before release.
