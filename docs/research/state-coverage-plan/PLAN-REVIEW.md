# State coverage plan — critical review

Reviewed 2026-10-14 against the local draft, ADRs, research, contracts, and federal implementation. **Verdict: needs-rework.** The direction is sound, but the measurement and integration gates do not yet establish the promised coverage or safely deliver it.

The owner's decisions are taken as settled: a pre-customer bounded pilot; tractable states plus at least one hard state; comment windows and hearings with correct-or-flagged dates and evidence, with who-is-affected analysis deferred. None of the findings asks to reopen those decisions or restart the condition-extraction benchmark. The fixes below should become concrete implementation and acceptance work within the pilot, not another open-ended research program.

References use repository-relative `file:line` locations from the reviewed snapshot. No network, credentials, installations, builds, or commits were used. This review is the only file created.

## BLOCKER

### B1. The “independent census” has no independent completeness test

**Evidence:** `docs/plans/state-coverage.md:72–80` proposes issue-by-issue enumeration by agents, second-agent review, and an unspecified human sample. `docs/research/state-rulemaking-audit/README.md:51` calls for agency/process/time/source boundaries. The audit found VA's executive-branch limitation and unproven MA Register correspondence (`audit-findings.md:14,51`); WA has 14 proposal rows but 13 filing IDs, including a partial withdrawal (`state-rulemaking-spike/README.md:103–110`). Whole-register segmentation was not benchmarked (`state-coverage-plan/INVENTORY.md:64`).

**Problem:** Independence from adapter code is necessary but insufficient. If the census and adapter both enumerate the same incomplete index, or share the same parser's omission, recall can be 100% while notices are absent from both. Reviewing only enumerated notices cannot discover an omitted page, agency, attachment, or notice boundary. One “register issue by issue” recipe also cannot be assumed to fit CT histories, VA stages, and MA's public-notice list. The plan promises every in-scope notice without specifying whether the cohort is newly published notices, windows active during the interval, or changes to earlier proceedings.

**Proposed edit:** Replace Phase 1 item 1 with a deliverable named **census protocol and coverage manifest**, containing:

- The agency/process universe, inclusions/exclusions (including VA NOIRA stages), interval rule, and authority/source map. Separately enumerate new notices, carry-in active windows, and lifecycle events affecting older windows.
- An expected-publication manifest: every issue/page/attachment or portal/history slice, retrieval result, original-byte hash, and explicit missing/inaccessible entries. Reconcile contents against document bodies; cross-check the register with agency/portal histories for scope gaps. A second surface can expose omissions without being independent legal corroboration.
- Two enumeration passes from originals before the passes compare answers. Do not give the second enumerator only the first enumerator's list. Retain rejected/out-of-scope candidates and their reasons so false exclusions are auditable.
- Separate stable notice, proceeding, window, and update IDs. A comment window plus a hearing counts as two opportunities even if one notice contains both; a duplicate agency listing is not a new notice. Publish notice recall and opportunity recall separately, plus false-positive/duplicate counts.
- Human adjudication of all enumeration/label disagreements, lifecycle/date ambiguity, decisive visual marks, and missing-source cases; a stratified random source-page/issue audit covering exclusions as well as accepted records. Record sample size, selection method, reviewer time, and corrections. For small pilot censuses, checking all consequential date/role labels is preferable to a token sample.
- Frozen, versioned labels with evidence and an adjudication log. Later gold corrections must be possible and trigger transparent rescoring rather than preserving known mistakes for the sake of freezing.

If source-universe completeness cannot be established, record recall as **not established** and stop that state's statewide gate, or explicitly label a narrower agency/process service. Do not silently drop missing sources from the denominator. This is work required to build the first census, not a separate experiment round.

### B2. Phase 2 is not demonstrably additive, and it omits several migration seams

**Evidence:** The plan calls for one additive contract change (`docs/plans/state-coverage.md:28–30,98–116`) and later says confidence is unchanged (`:161–162`). Today:

- `packages/contracts/src/index.ts:307–328` accepts/mints federal IDs only; `:286–291` is a closed source enum.
- `:564–570` requires the UTC-close and federal raw-date properties, although their values are nullable. `:605–618` forbids a null UTC close at high, medium, low, or stale confidence. `:531–535` stores change history only as prior UTC closes.
- `apps/docketclock/src/ingest/observe.ts:60–71` sends every non-Regs/non-review source through the FR document dedupe key. `migrations/0011_human_review_source.sql:17–19` still restricts sources to the four federal/review values.
- `src/reconcile/reconcile.ts:155–159` selects only FR and Regs inputs; `:212–218` converts an FR date into an inferred Eastern end-of-day instant. `src/reconcile/persist.ts:92–110` bumps the public version only when the UTC close changes.
- `src/verify/run.ts:109–110,153` requires a UTC close and uses the Regs polling watch. API date filters also depend on UTC (`src/api/queries.ts:156–165`).

**Problem:** A correctly known WA date-only deadline or hearing with unresolved zone cannot simply become a medium/high state window under the current invariant. Changing `resolved_close_utc` to a temporal union, removing/renaming `raw_fr_close_date`, opening the source enum in place, or widening verdict kinds breaks consumers or validation assumptions. Adding optional fields without changing readers also loses state semantics. A hearing-time/precision/target change could leave the version unchanged when both old and new UTC closes are null. Passing existing federal fixtures alone cannot prove public compatibility.

**Proposed edit:** Add a Phase 2 compatibility/migration design with an explicit old/new wire-shape matrix. Preserve the existing federal schema, source meanings, ID minting, UTC semantics, and API defaults. Introduce versioned state/generalized schemas in the same shared package and an explicitly versioned or opt-in public surface; do not fork the shared contract by deployment. Keep legacy federal raw fields null for state records if a compatibility projection retains them—never populate them with state values. Define how old clients are prevented from receiving values they cannot parse.

Name the accompanying implementation work: registered source IDs and publisher lineage; state-native dedupe keys and indexes; observation/target linkage; DB constraints and migrations; state rulebook dispatch; versioning of every material temporal/lifecycle change; review and verification readers; state-aware query ordering/filtering and evidence links. Preserve original-byte hashes separately from the existing canonical-JSON `payload_hash` (`src/sources/payload.ts:21–27`). Require federal replay plus mixed-version API, migration, dedupe/reversion, date-only, multi-window, hearing-change, and state verification tests before Phase 3 scoring. This is a cross-pipeline feature, not just a schema freeze.

### B3. Shadow mode needs an enforced boundary before the first state ingest

**Evidence:** `docs/plans/state-coverage.md:122–138` routes state data through existing stages while promising nothing public; ADR 0013 `:31–32` repeats the promise. `apps/docketclock/src/api/queries.ts:147–185` lists shared `participation_windows` without a jurisdiction/release-status restriction; its detail, observation, and conflict paths read the same shared data. There is no proposed shadow isolation mechanism.

**Problem:** If the new adapters insert into shared production tables, “shadow” is only a label. Once schemas accept state rows, unfiltered reads can expose them; before that, incompatible rows can fail API validation. Even with a separate environment, the plan needs to name it and specify promotion. Labels added at Phase 5 are too late.

**Proposed edit:** Make a release boundary a prerequisite to the first state write. Choose a private shadow database/deployment using the same contract, or a deny-by-default eligibility filter enforced across list/detail/observation/conflict/export/alert surfaces and aggregate counts. Test direct-ID access as well as listings. Define per-state promotion, stable-ID/evidence continuity, rollback, and removal of live eligibility after a failed health/accuracy gate. Keep federal publication independent. Phase 5 should be a checkable release checklist, not merely “publish passing states.”

### B4. “Anything doubtful abstains to review” is not implemented by the existing queue

**Evidence:** `docs/plans/state-coverage.md:127–135` depends on the existing review CLI. `apps/docketclock/src/review/core.ts:52–73` only selects `conflicting` and `stale` windows; chain ambiguity and dead-letter triage are explicitly excluded. The plan's honest date state is `unknown` (`:42`), and source/segmentation failures may not create a window at all. ADR 0010 `:17–29,41–42` permits freshness equivalence only for narrowly proven Regs metadata changes.

**Problem:** A correctly abstaining state extractor can create an invisible review backlog. Expanding verdict types does not add those records to the queue or preserve the evidence needed to adjudicate them. Reusing latest-per-source review summaries (`src/review/core.ts:177–182,291–295`) also needs care when several documents from one registered state source support a window.

**Proposed edit:** Add a Phase 3 review-workflow slice before shadow scoring: candidate-level tasks for missing notices/attachments, extraction failures, `unknown`, identity/lifecycle ambiguity, and conflicting evidence; exact artifact/page/region display; evidence-bound verdicts; queue age and deadline-sensitive prioritization even when the UTC close is null; named reviewer capacity and escalation. Measure time through resolution, not just labeling time. Keep agent reference labels distinct from production human approvals. State evidence changes must invalidate affected verdicts conservatively; ADR 0010's Regs-only exception must not become a generic “same extracted dates” shortcut. Include change-and-reversion tests and all supporting artifact hashes.

## SHOULD-FIX

### S1. Six weeks can measure a finite census; it cannot certify ongoing 98% recall or zero error

**Evidence:** The targets are 98% discovery, zero wrong high/medium dates, and 95% updates (`docs/plans/state-coverage.md:39–45`); Phase 1 uses about six weeks (`:72`) and Phase 3 four consecutive weeks (`:140`). Notice volumes remain unmeasured (`INVENTORY.md:100–104`). CT's four/five open records and WA's 13 unique filings in one proposal section are snapshots, not weekly-volume estimates (`state-rulemaking-spike/README.md:73–99,105–110`).

**Problem:** A true, fully adjudicated census gives an exact rate for its finite interval, subject to reference errors. Generalizing to future weeks is a different claim. An illustrative census of 20 notices permits no misses at 98%; one miss yields 95%. Repeated template fields and duplicated documents are not independent trials. Zero errors among zero confident dates is vacuous. No finite sample proves a population error rate of zero.

For scale only, under independent Bernoulli trials, zero errors in `n` cases gives a one-sided 95% upper error bound of `1 - 0.05^(1/n)`: **13.9% at n=20; 5.82% at n=50; 2.95% at n=100; 1.00% at n=299**. Perfect discovery across **149** independent opportunities is needed for a one-sided 95% lower recall bound above 98%; perfect detection of **59** updates is needed for a lower bound above 95%. Template clustering weakens those interpretations. A random spot-check of 10 labels has roughly an **82%** chance of finding no errors when prevalence is 2% (independent approximation), so an unspecified fixed sample cannot establish reference quality.

**Proposed edit:** Keep zero observed wrong confident dates as an operational release criterion, explicitly not a statistical guarantee. Report numerator/denominator by state, comment/hearing role, confidence, and update type; include every high/medium assertion actually exposed during shadow, including assertions later corrected. Report source ambiguities, abstention share, unresolved reference cases, and sample limitations. Use the complete acceptance interval for aggregate recall and weekly reports for operational monitoring; zero-event weeks are **N/A**, not passes.

Predeclare the release rule after Phase 1 sizing and before acceptance outputs: finite-census recall ≥98%, zero observed wrong confident assertions, required scenario tests, and bounded live operational evidence. Low-volume states can ship with explicitly limited evidence and ongoing audit; do not wait indefinitely for 149 notices or invent a reliability claim. If the owner instead requires a confidence-bound guarantee, state the sample requirement and resulting timeline honestly. This preserves correct-or-flagged coverage without imposing a new arbitrary percentage of dates that must be resolved.

### S2. The holdout rules and four-week gate describe incompatible timelines

**Evidence:** Phase 3 lasts 3–4 weeks but requires four consecutive passing weeks plus implementation (`docs/plans/state-coverage.md:120,140–142`). The census is both fresh live data (`:137–138`) and frozen before the adapter, with nobody inspecting its window while building (`:173–175`). Phase 4 adds 2–3 states in 4–6 weeks with the same gate (`:144–157`).

**Problem:** A future live census cannot be frozen before adapter development. A historical hidden corpus can be frozen, but replaying it cannot establish actual publication-to-service lag. An operational reviewer must inspect live evidence; hiding that evidence from everyone makes production review impossible. A two-week repair also cannot demonstrate a new four-consecutive-week pass unless earlier results are improperly carried forward.

**Proposed edit:** Separate development fixtures, sealed historical acceptance data, and a prospective live ledger. Hide acceptance labels from builders, not source evidence needed for operations. Freeze the candidate adapter/rulebook version and scoring protocol at the start of a declared live acceptance interval; census builders independently capture and adjudicate that interval. Historical replay proves extraction/identity behavior; timestamped live runs prove timeliness, update response, and workload.

Show engineering time separately from calendar observation time. Allow roughly 3–4 weeks to implement the first complete vertical slice, then four live weeks (longer only where a predeclared publication-cycle requirement demands it). Stagger the remaining states in parallel where staffing permits and expose that staffing assumption. Retain the single bounded repair, but specify whether a repaired version restarts four weeks or passes a different, explicitly weaker acceptance rule. Passing states should release individually through Phase 5 while other pilots finish; one hard state's failure must not hold all useful coverage hostage.

### S3. Update recall has no longitudinal denominator, and “Verify” cannot fill the gap unchanged

**Evidence:** Update coverage is a percentage in `docs/plans/state-coverage.md:43`, but Phase 1's stability check is only a second fetch one week later (`:86`). CT disappearance is not closure evidence (`state-rulemaking-spike/README.md:79–99`); WA withdrawal can be partial (`:108–110`). The federal verifier requires a UTC close and Regs watch (`src/verify/run.ts:109–110,153`) and defaults to seven days with a fourteen-day no-check cap (`src/verify/select.ts:24–34`).

**Problem:** A latest snapshot cannot reconstruct all intervening changes, especially an edit followed by reversion, an older proceeding reopening, or a hearing cancellation outside a new-notice cohort. Four weeks may contain no rare lifecycle events. A successful re-fetch of the same source proves neither original extraction correctness nor discovery completeness.

**Proposed edit:** Add a separately maintained update ledger: affected window/notice, before/after retained bytes, source posting time or bounded first-seen interval, event type, exact target/scope, adapter observation time, reconciled visibility time, and review latency. Independently monitor known histories and new amendment notices, including events affecting records predating the census. Include corrections, shortened deadlines, hearing rescheduling/cancellation, partial withdrawals, and same-URL replacements, not just the three listed types.

Use all real updates in the live denominator; report zero as unmeasured. Require deterministic historical/replay cases for rare transitions without counting them as live recall. Specify polling/backfill retention and post-close follow-up per publication process, with a confirmed-check ledger independent of whether content changed. Do not inherit the federal seven-day horizon for a source that publishes relevant changes monthly. Keep independent census accuracy assessment separate from “no contradiction found on re-poll.”

### S4. State date policy needs precision, channel, and authority rules—not one time zone

**Evidence:** `docs/plans/state-coverage.md:104–114` proposes a local datetime “with a zone,” a jurisdiction legal zone, and multiple submission ways. The spike permits unresolved zones/anchors (`SPEC.md:80–98`), preserves receipt/postmark/portal distinctions (`:90`), and shows date-only WA comments, unresolved hearing zones, and different relative periods (`README.md:112–116,144–154`). MA's literal “EST” conflict and TN's date-role ambiguity remain unresolved (`INVENTORY.md:69–72`).

**Problem:** A calendar-date comparison can hide a real same-day hearing-time or cutoff conflict. A single state-level default is not evidence of the clock governing a particular agency, venue, or channel. “Several ways to submit” is insufficient if received-by and postmarked-by dates differ. Deferring who-is-affected conditions does not permit discarding conditions that define the deadline, hearing status, or scope of a partial withdrawal.

**Proposed edit:** Phase 1 records temporal ambiguities; Phase 2 freezes a versioned **source/process temporal policy** for each pilot before any normalized instant is asserted. Include literal zone text, nullable IANA zone, source authority/precedence, effective policy version, precision, inclusive/exclusive cutoff, relative anchor/counting rule, and channel/purpose-specific deadlines. Compare compatible roles at their asserted precision; only use date-only agreement when justified. Preserve unresolved local times without fabricating a UTC value. Explicitly model scheduled/not-scheduled/canceled/unknown hearings and targeted partial lifecycle changes. Add source lineage so CT JSON and its rendered view cannot count as independent corroborating sources. Preserve confidence vocabulary and deterministic principles, while admitting that state-specific derivation rules are new. Audience/eligibility inference remains deferred.

### S5. Timeliness needs two clocks and health needs a stale-data policy

**Evidence:** `docs/plans/state-coverage.md:40` measures publishing-to-showing lag; `:133–135,194` adds fetch/layout/silence alerts. Monthly delivery risk is already identified in `state-rulemaking-audit/README.md:91`. HTTP 200 sometimes returned empty shells or wrong pages (`:29`). The current review code explicitly notes that stale confidence is reserved and not currently produced (`src/review/core.ts:87–92`).

**Problem:** Showing a monthly publication the next day can satisfy ingestion latency while providing no useful advance notice. Publication dates may be date-only, backdated, or unknown; substituting fetch time makes measured lag artificially small. Silence can mean healthy low volume or a broken collector. Alerts alone do not prevent stale dates from remaining confidently public.

**Proposed edit:** Define lag from the earliest evidenced authoritative posting within the declared coverage scope to an evidence-backed, correctly typed public/shadow opportunity, including review delay. Preserve uncertainty bounds when posting time is unknown; mark unmeasurable cases separately. Also report lead time remaining before close/hearing and notices first discovered after the event. Monthly sources need an earlier official surface or an explicit delayed-service limitation that does not claim timely active coverage.

Require expected issue cadence, last successful full enumeration, page/row/attachment accounting, content-type/layout checks, cursor progress, backlog/dead letters, and last successful checks of known windows. Set cadence-aware thresholds and a named responder. Specify transitions to stale/coverage-degraded, alert suppression plus notification, and recovery/backfill verification. Test an empty-200 response, missed page, missed issue, and outage beyond index retention before release. Persist success checks even when hashes are unchanged, as the federal poller already does (`src/poll/poll.ts:25–32,51–63`).

### S6. Pilot candidates are reasonable leads; the selection gate does not guarantee the intended mix

**Evidence:** Candidates and substitutions appear at `docs/plans/state-coverage.md:66–68`; `:91–94` stops only if no state reaches 95% best-surface recall, while release needs 98%. Relevant source profiles are `state-rulemaking-audit/audit-findings.md:38,42,49,51–52` and `state-rulemaking-spike/README.md:71–124`.

**Assessment and proposed edits to the scorecards:**

- **WA:** Best-supported first implementation candidate: enumerable issue HTML and two guarded deterministic notice templates. Require dedupe across agency listings, body-level event classification, and targeted partial withdrawals. Do not call the whole state proven tractable from those templates.
- **CT:** Good structured candidate. Pair the open list with histories/original notices, resolve period GUID identity, and independently establish hearing discovery; the open-comment endpoint alone does not prove it. Record unsupported-backend stability risk.
- **VA:** Promising stage/action structure, but the inspected portal describes executive-branch scope. Reconcile the agency/process universe and make NOIRA inclusion explicit before claiming statewide coverage. The 53-forum snapshot is not throughput evidence.
- **MA:** Defensible hard candidate because public-page/Register completeness, document access, and time wording remain open. The census must compare authoritative Register contents or explain the unresolved denominator; using the public page as both gold and adapter is circular. Budget lawful reference access if necessary.
- **TN:** Defensible hard candidate for pagination, PDFs, and date-role association. A hearings table alone does not prove discovery of written-comment opportunities without hearings. Map those sources and retain the accommodation-versus-comment negative fixture.

Replace “best-surface” with **best justified combination of surfaces**, scored against B1's source universe. Make 95% an exploration signal, not a pilot-wide sufficient gate: each selected state needs a documented route to 98%, plus at least one selected state's measured acquisition/semantic difficulty satisfying the hard-state requirement. If no hard candidate has a credible route, use one bounded substitute selection or make an explicit scope decision; do not quietly ship an easy-only pilot. Retain the at-most-four live pilot bound.

### S7. Operating cost omits the work that keeps the coverage claim credible

**Evidence:** The only ongoing budget target is reviewer minutes (`docs/plans/state-coverage.md:45`); marginal cost lists engineering, templates, reviewer time, provider cost, and monthly breakages (`:146–155`). Each shadow census must be built again (`:137–138`), but no post-launch census/audit owner or cost is specified.

**Problem:** Complete independent enumeration, human reference adjudication, acquisition/rights fees, artifact storage, repair/backfill, and incident response can exceed parser cost. Four-week breakage observations do not estimate seasonal or long-term maintenance. Costs from 3–4 purposively selected states cannot alone establish 50-state feasibility.

**Proposed edit:** Set per-state setup and weekly operating budgets before shadow acceptance, with separate actual hours for acquisition, census/reference review, production review, engineering repair, and on-call work; include storage, vendors, and licensed reference access. Define a sustainable post-launch audit cadence: publication-manifest reconciliation every expected cycle, independently sampled source enumeration/labels, periodic fuller censuses, and immediate full investigation on misses. Name the owner and a response deadline. If exhaustive weekly censuses are discontinued, say that rolling recall is estimated, not continuously certified. Report cost per usable opportunity plus flagged/backlogged counts. The scale memo should give ranges by observed source archetype and explicitly unmeasured types, not multiply one marginal-cost figure by 50.

### S8. Access/retention clearance must precede collection that depends on it

**Evidence:** Phase 1 builds the census before mapping access/terms (`docs/plans/state-coverage.md:72–80`); the risk response is merely “prefer official free sources; record the terms” (`:196`). The inventory separates access price, automation, completeness, and reuse rights (`INVENTORY.md:105,148`). ADR 0012 authorizes bounded reviewed research releases, not new providers, budgets, or production changes (`:14–18,26–27`).

**Problem:** Free public viewing does not establish permission for automated acquisition, durable storage, vendor processing, or redistribution of retained originals. The plan's 100% original-byte evidence promise can be incompatible with a source's permitted reuse. Research execution controls also do not establish a production provider route.

**Proposed edit:** Move a source-specific access/rights check ahead of dependent automated census collection; record source terms, allowed collection method/rate, original retention, third-party processing, and what evidence can be exposed publicly. Resolve material ambiguity with the designated reviewer before relying on that source, using an allowed alternative if needed. Add a launch acceptance item for production parser/provider configuration, retention/restore, cost ceilings, and permitted evidence delivery. Reuse ADR 0012 controls for paid research where applicable without treating that ADR as blanket production authorization.

### S9. ADR 0013 needs a precise amendment and an actual release gate reference

**Evidence:** ADR 0013 says it amends the federal-only rule (`:5`), but also generalizes Eastern comparison (`:35–43`). ADR 0003 explicitly says America/New_York (`:19`). ADR 0013 names “its Phase 5 gate” (`:31`), while the plan's explicit state gates are in Phases 3/4 and Phase 5 has no stated gate (`docs/plans/state-coverage.md:140–169`). The ADR says comment windows/hearings only, while Phase 2 includes hearing-request windows.

**Proposed edit:** State that the exception allows research on the five named candidates and production eligibility for at most four selected pilot states, with any expansion governed by a new decision. Specify whether a stopped state's replacement counts against that bound. Preserve ADR 0003's federal America/New_York rule unchanged; add source/process-specific state policies under the new contract. Preserve append-only observations and suppression-plus-notification exactly. Point public eligibility to passing the state's Phase 3/4 acceptance gate **and** the explicit Phase 5 release checklist from B3. Clarify hearing-request treatment and lifecycle scope in both documents. On acceptance, update the root working instructions and canonical architecture through its documented generation workflow (or an explicit ADR override reference) so builders do not receive contradictory federal-only instructions. Keep Proposed until accepted; this review does not change its status.

## NOTE

### N1. Research conclusions are stronger than the retained evidence

**Evidence:** `docs/plans/state-coverage.md:13` says processing one notice is “largely solved”; ADR 0013 `:17–19` says research established how to process one notice. Yet `INVENTORY.md:72,83–84,102–106` records zero normalized results in R6, unsafe shadow acceptance in R5, unmeasured legal date normalization, and no transferable production contract. The benchmark calls Agentic strongest **in this sample** and its references agent-reviewed, not human gold (`state-rulemaking-benchmark/README.md:5,22–24`). R16–R19 tests conditions, fails its bar, and establishes no production eligibility (`clause-only-r16-r19/README.md:46–53`).

**Proposed edit:** Replace “largely solved” with “reusable parsing candidates and diagnostic fixtures exist; discovery, segmentation, date-role extraction, safe acceptance, and production normalization remain to be validated in the pilot.” Keep Agentic as a candidate supported by the inspected sample, not a universal winner. Preserve the sensible decision to park who-is-affected extraction. Replace “Nobody does this well” / “Nobody reliably covers…” (`plan:5`, `ADR:13`) with a product hypothesis: this research did not conduct a competitive coverage audit.

### N2. Add executable acceptance ownership in the existing phase-plan style

**Evidence:** `plans/review-resolve.md:34–50` inventories concrete seams and constraints; `plans/verification-accuracy.md:103–125` orders prerequisites and names migrations/implementation slices. The state plan names roles but not similarly concrete acceptance artifacts (`docs/plans/state-coverage.md:176–181`).

**Proposed edit:** For each phase, name one accountable owner, artifact paths, required evidence/checks, and the exact decision output. Split Phase 2/3 into reviewable slices for census/scoring, contracts/migrations, artifact retention, first adapter, reconciliation/review/verify, shadow isolation, and release. Identify Mini/CI validation for DB and build work under the repository's two-machine rule. Existing federal tests remain necessary; state acceptance must additionally cover the concrete failure modes above. This keeps execution finite and makes a failed gate produce a decision rather than another research round.

## Recommended disposition

Revise the plan before implementation authorization under it: settle B1–B4 and lock the measurement/timeline rules in S1–S3. Then proceed directly to the bounded census and first end-to-end state implementation. Release each passing state once its evidence and operational gate are complete; stop or explicitly rescope failures within the agreed repair budget. The strongest five issues are **B1 census independence, B2 contract compatibility, B3 shadow isolation, B4 review routing, and S1 statistical interpretation**.
