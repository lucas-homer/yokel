# State coverage plan (r2, approved 2026-10-15)

**Goal:** make DocketClock the source people trust for state comment periods and hearings, as they
can for federal ones. It must find every in-scope notice, get the dates right or say it isn't
sure, and show the source for every fact.

Our product hypothesis is that nobody does this well, and that is why it is worth doing. We have
not run a competitive coverage audit, so this is a hypothesis, not a finding.

**Decision basis:** [ADR 0013](../decisions/0013-state-coverage-pilot.md), accepted: a bounded
pilot ahead of a customer. The inputs are summarized in
[`INVENTORY.md`](../research/state-coverage-plan/INVENTORY.md).

Revision r2 addresses the cross-provider review in
[`PLAN-REVIEW.md`](../research/state-coverage-plan/PLAN-REVIEW.md). Section references such as
(B1) or (S3) point to its findings.

## What the research changes

1. **We have reusable parts for processing a notice, but not a validated pipeline.**
   - **Parsing:** LlamaParse Agentic is the strongest PDF candidate on the inspected sample, with
     native text and the original bytes kept alongside it.
   - **Fixtures and adapters:** there are good fixtures and two guarded deterministic adapters (CT
     JSON and WA HTML).
   - **Still to validate in this pilot:** date-role extraction, safe automatic acceptance and
     production normalization. Research showed role errors, an unsafe shadow acceptance (R5) and
     no transferable contract. (N1)
2. **For no state do we know:**
   - whether we can find every notice;
   - how many notices there are each week;
   - whether we catch updates;
   - how much review work a state creates;
   - what a state costs to run.

   For federal data, ADR 0003 could say discovery is not the value. For states, discovery **is**
   most of the value.

3. **State support is a cross-pipeline feature, not a schema tweak.** The federal assumptions run
   through the contracts, the database constraints, ingest, reconcile, review, verify and the API
   (B2).

## Definition of "covered" (v1)

### Scope

- **In scope:** rulemaking participation opportunities.
  - Opportunity types: written-comment windows, hearings and hearing-request windows.
  - Their lifecycle events: extensions, shortened deadlines, corrections, reopenings, hearing
    reschedules and cancellations, and full or partial withdrawals.
  - Deadline-defining conditions, such as "received by" versus "postmarked by" or the target of a
    partial withdrawal, are kept, because they define the date.
- **Out of scope:** who-is-affected conditions, permits, guidance, legislation and local
  government.
- **Counting:** a notice with a comment window and a hearing counts as two opportunities, and a
  duplicate listing is not a new one.
- **Per state:** each state declares its agency and process universe in Phase 1. For example, VA
  Town Hall covers the executive branch. Anything narrower than statewide is labelled as such and
  never presented as statewide.

### Targets

Scored against the state's census for a declared acceptance interval:

| Promise                                                                                                                                | Release criterion                                                                                                                 |
| -------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| **Discovery:** notice recall and opportunity recall, reported separately                                                               | ≥ 98% on the finite census                                                                                                        |
| **Correctness:** wrong dates among everything exposed at high or medium confidence during shadow, including assertions later corrected | 0 observed                                                                                                                        |
| **Honesty:** unresolved dates                                                                                                          | `unknown` or `conflicting`, with evidence and a review task; never a guess                                                        |
| **Updates:** live updates reflected, from the update ledger                                                                            | ≥ 95%. Zero live events means "unmeasured", not a pass; rare transitions also need passing replay tests.                          |
| **Timeliness:** lag from the earliest evidenced authoritative posting to a correctly typed opportunity, including review delay         | Median ≤ 1 business day and max ≤ 3, where posting time is evidenced. Also report the lead time left before the close or hearing. |
| **Evidence:** facts linked to the retained original bytes and an exact location                                                        | 100%, within what each source's terms allow                                                                                       |
| **Operating load:** hours per state per week, split by activity                                                                        | Within the per-state budget set at the end of Phase 1                                                                             |

**How to read these numbers (S1).**

- They are finite-census results and operational release criteria, not statistical guarantees
  about future weeks.
- For scale: with zero errors in _n_ independent cases, the 95% upper bound on the error rate is
  13.9% at n = 20, 2.95% at n = 100 and 1% at n = 299.
- Showing that recall is above 98% with 95% confidence needs about 149 independent opportunities
  with zero misses.
- Repeated templates weaken all of this.
- We report numerators, denominators and limits per state, and we never present a low-volume
  state's pass as a reliability guarantee.
- The precise release rule for each state is fixed after the Phase 1 sizing and before any
  acceptance output exists.

**Monthly sources.** A state whose only official surface is monthly can't offer timely active
coverage. It either gets an earlier official surface or ships with an explicit "delayed source"
limitation (S5).

## Phases

Every phase has an owner, artifacts and one decision. A failed gate produces a decision to stop,
narrow the scope or make one bounded repair; it never starts an open-ended round. Engineering time
and calendar observation time are shown separately (S2).

### Phase 0: decide and define (about 2 days)

- **Owner:** primary and owner.
- **Work:** accept or edit ADR 0013 and the coverage definition. Set the Phase 1 budget: agent
  time, paid parsing and reviewer hours.
- **Decision:** ADR accepted. On acceptance, update `AGENTS.md` and the architecture note through
  its generator or an explicit ADR override, so builders don't get contradictory "federal-only"
  instructions (S9).

### Phase 1: source universe, census and selection (about 3 weeks; research children plus a human reviewer)

Candidates: **WA**, **CT** and **VA** (tractable), and **MA** and **TN** (hard). Scorecard notes
from the review (S6):

- **WA:** dedupe across agency listings, classify events from the notice body, and handle partial
  withdrawals.
- **CT:** combine the open list with histories, resolve period identity, and discover hearings
  separately. The backend is unsupported, which is a stability risk.
- **VA:** settle the executive-branch scope and whether NOIRA stages are included.
- **MA:** the public page can't be both the gold standard and the adapter. Compare against the
  Register, or record the denominator as unresolved and budget for lawful reference access.
- **TN:** a hearings table doesn't cover comment windows that have no hearing. Map those sources.

For each candidate:

1. **Access and rights check, before collection (S8).** Record the following and resolve
   ambiguities with the designated reviewer before relying on the source:
   - the source's terms;
   - the allowed collection method and rate;
   - whether originals may be retained;
   - whether third parties may process them;
   - what evidence may be shown publicly.
2. **Census protocol and coverage manifest (B1):**
   - **Universe:** agencies and processes, inclusions and exclusions, the interval rule, and the
     authority and source map. New notices, carry-in active windows and lifecycle events on older
     proceedings are enumerated separately.
   - **Expected-publication manifest:** every issue, page and attachment, or every portal or
     history slice, with the retrieval result, the original-byte hash, and explicit entries for
     anything missing or inaccessible. Contents are cross-checked against the documents
     themselves and against agency or portal histories.
   - **Two blind enumeration passes from the originals.** The second pass doesn't see the first
     pass's list. Rejected candidates are kept, with reasons.
   - **Separate IDs** for notice, proceeding, opportunity and update.
   - **Human adjudication** of every disagreement, every lifecycle or date ambiguity, every
     decisive visual mark and every missing source. Add a stratified random audit of pages and
     issues that covers exclusions as well as inclusions. Check all consequential date and role
     labels when the census is small, and record the sample method and reviewer time.
   - **Versioned labels** with an adjudication log. Later corrections are allowed and trigger
     transparent rescoring.
   - **Completeness rule:** if the completeness of the source universe can't be established,
     recall is "not established". The statewide claim then stops, or the service is explicitly
     narrowed.
3. **Surface map.** For each discovery surface, and for the best justified _combination_ of
   surfaces, record which census items it would have found. Note retention windows, pagination and
   cadence.
4. **Temporal ambiguity log.** Record zone wording, relative anchors, counting rules, cutoffs and
   channel-specific deadlines (S4).
5. **Sizing:**
   - opportunities per week;
   - format mix;
   - number of templates;
   - a stability re-fetch;
   - an initial estimate of setup cost and weekly operating cost.

**Artifacts:** `docs/research/state-coverage-plan/census/<state>/` (protocol, manifest, labels,
adjudication log) and `scorecards/<state>.md`. Bulk raw captures go to hash-keyed storage outside
git.

**Decision:** select up to 4 pilot states.

- Each selected state needs a documented route to 98%.
- At least one selected state must meet the hard-state bar. If no hard candidate has a credible
  route, allow one bounded substitution or make an explicit scope decision; never quietly ship an
  easy-only pilot.
- Set each state's per-state budget and its precise release rule now.

### Phase 2: versioned state contract and pipeline compatibility design (about 2 weeks; can overlap late Phase 1)

- **Owner:** contract-keeper, with the adversary verifying.
- **Federal behaviour is preserved exactly:** existing schemas, source meanings, ID minting, UTC
  semantics, API defaults and ADR 0003's America/New_York rule (B2, S9).

Deliverables:

- **Compatibility matrix** of the old and new wire shapes. State and generalized schemas live in
  the same shared package, versioned alongside the federal ones, and are exposed through an
  explicitly versioned or opt-in API surface.
  - Old clients never receive values they can't parse.
  - Legacy federal raw fields stay null on state records and are never filled with state values.
- **State IDs:** `ocd-participation-window/state-xx/...` with source-native aliases and a reviewed
  merge and split policy.
- **Source lineage:**
  - a registered source registry, not new hard-coded enum values;
  - lineage, so CT JSON and its rendered page can't count as two independent corroborations.
- **Temporal policy per source and process (S4):**
  - the literal zone text and a nullable IANA zone;
  - source authority and precedence, and the policy version;
  - precision, and whether a cutoff is inclusive or exclusive;
  - relative anchor and counting rule;
  - channel- and purpose-specific deadlines.
  - Roles are compared at their asserted precision. Unresolved local times are kept and never
    fabricated into UTC.
- **Opportunities and lifecycle:**
  - several opportunities per proceeding;
  - hearing status: scheduled, not scheduled, cancelled or unknown;
  - targeted partial lifecycle relations.
- **Review verdicts** cover event type, role, identity, precision and visual marks. Agent
  reference labels stay distinct from human production approvals.
- **Pipeline seams to change (named, not implied):**
  - source registry and DB constraints (`migrations/0011`);
  - state dedupe keys (`ingest/observe.ts:60–71`);
  - an original-byte hash separate from `payload_hash` (`sources/payload.ts:21–27`);
  - state rulebook dispatch (`reconcile/reconcile.ts:155–218`);
  - versioning on every material temporal or lifecycle change, not only a UTC-close change
    (`reconcile/persist.ts:92–110`);
  - review and verify readers (`verify/run.ts:109–153`);
  - API filtering and ordering (`api/queries.ts:147–185`).

**Decision:** contract frozen. The test plan must include federal replay, mixed-version API,
migration, dedupe and reversion, date-only, multi-opportunity, hearing-change and state-verify
tests, plus fixtures from the Phase 1 census for every pilot state.

### Phase 3: first state, built as slices, then a live acceptance interval

- **Owners:** builders in worktrees, then the integrator. DB and build validation run on the Mini
  and in CI (the two-machine rule).
- **Engineering, about 4–5 weeks:** reviewable slices, in order. The first three must exist before
  the first state write.

1. **Release boundary (B3).** A deny-by-default eligibility filter enforced on every surface:
   list, detail, direct-ID, observations, conflicts, export, alerts and aggregate counts. A
   private shadow deployment of the same contract is the alternative. Either way it includes
   per-state promotion, rollback, and removal of eligibility after a failed gate. Tests include
   direct-ID access.
2. **Review workflow (B4).** Candidate-level tasks for:
   - missing notices or attachments;
   - extraction failures;
   - `unknown` items;
   - identity or lifecycle ambiguity;
   - conflicts.

   Tasks show the exact artifact, page and region. Verdicts are bound to evidence. The queue
   prioritizes by deadline even when the UTC close is null, and has named reviewer capacity and
   escalation. Evidence changes invalidate affected verdicts conservatively, and ADR 0010's
   Regs-only exception doesn't generalize.

3. **Health and staleness (S5).** Track expected cadence, the last full enumeration,
   page/row/attachment accounting, layout checks, cursor progress and dead letters. Persist
   successful checks even when the hash is unchanged. Thresholds are cadence-aware and there is a
   named responder. A defined path covers going stale or coverage-degraded, suppression with
   notification, and recovery with backfill. Tests cover an empty 200 response, a missed page, a
   missed issue and an outage beyond index retention.
4. **Update ledger (S3).** For each update, record:
   - the before and after bytes;
   - the posting time, or a bounded interval in which it was first seen;
   - the event type and target;
   - the observation time, visibility time and review latency.

   The ledger also monitors known histories and older proceedings. The post-close follow-up
   horizon is set per publication process, not inherited from the federal seven days.

5. **The state adapter or adapters, extraction, and reconciliation.** Deterministic parsing comes
   first. An LLM handles only candidate fields, with exact locations. Anything doubtful becomes a
   review task.

**Acceptance (S2):** builders see development fixtures, which are kept separate from two
acceptance sets:

- **(a) Sealed historical set:** a Phase 1 census slice that builders never see, frozen before
  the build. Replay proves extraction and identity.
- **(b) Live acceptance interval of 4 weeks:** declared in advance, with the adapter and rulebook
  version and the scoring protocol frozen at its start.
  - Census builders capture and adjudicate the interval independently.
  - Only the labels are hidden from builders. Operators still see the live evidence.
  - It proves timeliness, update response and workload.

**Decision:** the state passes (a) and (b) against its predeclared release rule. Otherwise it gets
one bounded repair, after which a fresh 4-week interval restarts with no carried-forward weeks.
If the repair fails too, stop the state or narrow it, and write down why.

### Phase 4: remaining pilot states (staggered; about 2–3 weeks of engineering per state, plus a 4-week interval each)

- **Staffing:** states run in parallel where staffing allows, and the plan states that
  assumption.
- **Per-state accounting (S7):** actual hours, split by acquisition, census and reference review,
  production review, repair and on-call, plus storage, vendor and reference-access costs.
  Report cost per usable opportunity and backlog counts.
- **Release:** each state releases individually through Phase 5 when it passes. One hard state's
  failure doesn't hold back the others.

### Phase 5: release checklist and scale memo

Each passing state goes through a checkable release checklist:

- the eligibility flip, using the release boundary;
- evidence exposure within the source's terms;
- the production parser and provider configuration, with cost ceilings;
- retention and restore;
- the audit cadence after launch (below);
- the named owner.

**Audit after launch (S7):**

- reconcile against the publication manifest every expected cycle;
- sample enumeration and labels independently;
- run a fuller census periodically;
- investigate any miss in full, immediately.

If exhaustive censuses stop, rolling recall is described as _estimated_, not certified.

**Scale memo:** cost ranges by observed source archetype, such as register issues, JSON portals or
PDF-only sources, with unmeasured archetypes named explicitly. It is not one figure multiplied by 50. It feeds the next ADR.

## How we run it

- **Agents:**
  - research children: Codex for offline work, Claude for anything needing the network;
  - contract-keeper and adversary for Phase 2;
  - builders in worktrees, then the integrator;
  - work by one provider is reviewed by the other.
- **Data on `main`:** censuses, labels, manifests and fixtures go into the repo. Bulk raw captures
  go to hash-keyed storage outside git (see the PR #128 size discussion).
- **Not in v1:** who-is-affected conditions; local government; national volume estimates before
  Phase 4 data exists.

## Main risks

| Risk                                              | Early signal                           | Response                                                                           |
| ------------------------------------------------- | -------------------------------------- | ---------------------------------------------------------------------------------- |
| The source universe can't be shown to be complete | Phase 1 manifest gaps                  | Narrow the declared scope, or stop the state; never drop gaps from the denominator |
| Review load doesn't scale                         | Hours over budget in the live interval | More deterministic parsing per template; raise abstention only with evidence       |
| Sources break, move or go quiet                   | Stability re-fetch; health slice       | Cadence-aware silence alerts, stale transitions, census canaries                   |
| Legal date semantics                              | Temporal ambiguity log                 | Per-process temporal policy; `unknown` until reviewed                              |
| Terms of use, access or retention limits          | Phase 1 rights check                   | Allowed alternative source, or limit the evidence exposed                          |
| Low volume makes the evidence thin                | Phase 1 sizing                         | Ship with stated limits and ongoing audit; never claim a guarantee                 |
| The plan drifts into research                     | A phase over its timebox               | The gate decides; no extra rounds without a new decision                           |
