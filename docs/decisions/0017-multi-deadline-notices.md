# 0017. Notices that set more than one participation deadline

- Status: Proposed. The operator picks a model before any build starts.
- Date: 2026-10-28
- Issues: #137 (general problem), #124 (FDA petitions, first slice). #127 is the contrast case.
- Builds on: [0010](0010-review-evidence-freshness.md), [0014](0014-portal-close-echo-preserves-pin.md),
  [0015](0015-agent-review-authority.md), [0016](0016-fr-amendment-close.md). Contract 0.12.0,
  `reconcile-v2.4`.
- Evidence: [`docs/plans/multi-deadline-measurement.md`](../plans/multi-deadline-measurement.md).
- Review: round 1 by Codex GPT-6 Astra (high). It rejected the first draft's staging and routing
  rule; this text is the revision. See the review log at the end.

## Context

Some notices set several deadlines, each for a different action or a different class of
participant. DocketClock has one window per FR document with one operative close. The reconciler
assumes FR `comments_close_on` and the portal's `commentEndDate` describe the same action, and
compares them. In these notices they often describe different actions.

**What the measurement found (2026-10-28).** It is a screen, so the counts are a lower bound.

1. **Small, and concentrated in a few agencies.**
   - 155 notices; 154 of the 5,090 FR-backed comment windows (3.0%); 37 open.
   - Six agencies hold 88%: FCC, NRC, FDA, ITC, STB, EPA. 71% use near-verbatim DATES templates.
   - Classes: reply 72, hearing request 37, petition 26 (all FDA, #124), PRA 16, and opposition 4.
     Opposition means a later round that is another class's first chance; it covers 2 to 4 notices.
2. **The main harm is mostly silent.**
   - 54 windows (35% of the class; 22 open, 20 at HIGH) show a later round as their close. Usually
     that is an FCC or ITC reply round.
   - 48 of the 54 never reach the queue, because both sources agree on the later date.
   - 17 show a round restricted to a class (ITC eligible parties, an STB applicant, DEA
     registrants).
3. **The queue sees part of it.**
   - 10 of the 37 live queue items are in this class. At most 6 of them are pure role conflicts:
     IRS 2026-18574 is a real ADR 0016 correction, 2026-21939 is a first-chance case, and both ITC
     items state a 5:15 p.m. filing time.
   - 12 verdicts, all pins on the initial comment date. The second deadline survives only in note
     prose.
4. **FR metadata drifts, and the fix depends on it.**
   - FR has revised `comments_close_on` on 42 of the 155 since we fetched, always toward the
     initial round. DocketClock reads each FR document once.
   - Refreshing FR alone would turn 22 mismatches into 49: 33 added, 6 cleared, and 2026-21939 would
     become HIGH on the supporters' date.
   - Yet only 6 of the 54 later-round closes have a _stored_ structured value on the initial round.
     After a refresh, 42 do.
5. **The chronologically first deadline is often not the comment close.** It is a PRA or
   hearing-request date in 30 notices.

**Current policy.**

- **2026-10-17, operator, interim.** The initial deadline is the close, and later deadlines go in
  the notes (`plans/review-learning-loop.md`, `plans/review-autopilot.md`). The rule is recorded in
  no ADR.
- **Autopilot `pin_close` rule.** The rule (skill rule 2) accepts "a petition, reply, meeting or
  effective date" as explaining a competing value.
- **The gaps.** The interim rule only reaches windows in the queue. The autopilot rule does not
  handle a later round that is someone's first chance.

**Seams that matter.**

- **Keyed by `ocd_id`.** Verdicts, conflicts, accuracy records, change history and ADR 0016
  amendment links are all keyed by `ocd_id`.
- **The queue selects only `conflicting` or `stale`.** An informational flag on a HIGH window is
  invisible to review.
- **Status comes from the portal too.** A machine-derived window is `open` while the portal's
  `openForComment` is true, whatever its close.
- **Verification watches.** They don't re-snapshot a window whose close moves _earlier_
  (`verify/run.ts`).

## Vocabulary (proposed; the operator's working definition, sharpened by the data)

- **Deadline.** A dated action a notice sets. It has:
  - a _kind_: initial comment, opposition, reply, hearing request, petition, PRA/ICR, meeting or
    registration, effective date, other;
  - a _participant class_: anyone, or a named class;
  - a _route_;
  - any _condition_, e.g. STB's "if any comments are filed";
  - a date, with its time only if the text states one;
  - its evidence.
- **Comment period.** A round in which some class of participant may, _for the first time in this
  notice_, submit written views the agency says it will consider on the proposal.
  - Supporters' initial round and opponents' first round both count.
  - These do not count: a reply restricted to answering filed comments, and a filing that starts or
    joins a separate proceeding (a petition docket, a hearing, an intervention).
  - The data shows why this test, and not "a substantive submission", is needed. FDA due-diligence
    petitions and NRC hearing requests are substantive and broadly open, and both go to a
    different route.
- **Initial comment round.** The comment period the notice's general invitation opens, _as amended_
  (ADR 0016). It is not "the first deadline".
- **Related deadline.** Any other deadline in the notice.

## Foundations every option needs

- **F1. A DATES-text deadline classifier, `deadline-v1`.**
  - It is a pure, versioned function over the stored `raw_dates_text`, the same pattern as the
    fr-v3 flags derived from `raw`. No new observation is written and nothing is backfilled.
  - It recognizes the seven template families first.
  - Its output is one of three:
    - `single`: zero or one participation deadline. Derivation stays byte-identical to today's.
    - `classified`: every deadline has a kind, class and date.
    - `unresolved`: the text carries more than one deadline, but at least one role, class or date
      can't be attributed. Typical causes are truncated text, an unstated class, dates out of order
      (FERC 2026-12712), two same-kind recipients (NOAA 2026-19258), or a first-chance round with no
      sibling to carry it.
- **F2. Conservative source-to-deadline routing.**
  - **Matching a date is a candidate, never proof.** A structured value (FR metadata, or the portal
    close with its open/withdrawn flags) is routed to a classified deadline only when _all_ of these
    hold:
    1. Its Eastern date equals that deadline's date on the **effective timeline**, which includes
       ADR 0016 amendments.
    2. No other deadline shares that date or lies within 7 days of it. Routing abstains on
       collisions, so a +1-day portal error can't be "explained" by a neighbouring deadline. The
       cost is measured: 2 of the 155 notices have deadlines 7 days apart or closer (IRS 2026-18574,
       3 days; PRC 2026-11157, 7 days). Both would go to the unresolved state.
    3. The notice matched a template family whose metadata behaviour has been measured (e.g. FCC FR
       and portal carrying the reply date), or a human verdict already attributed the role.
  - **Otherwise** the value is unexplained, and it conflicts as it does today. That keeps the #127
    class live. An extension that moves the initial round onto the reply date is a collision, so
    routing abstains.
  - **Flags follow the date.** A portal value routed to the reply round carries its
    `openForComment`/`withdrawn` flags with it. They no longer decide the comment period's status.
  - **Corroboration.** The comment period's close may move to the classified initial round only if
    a structured value routed to it corroborates it. This is ADR 0016 §8's discipline: a text parse
    alone never moves a published close.
- **F3. An honest unresolved state.**
  - When F1 says `unresolved`, or F1 says `classified` but no structured value corroborates the
    initial round, the window must not claim its retained date is the comment-period close.
  - Instead it keeps the retained date as `resolved_close_utc` and gains the flag
    `deadline_role_unresolved`. Its confidence is capped at MEDIUM: HIGH would assert we know what
    kind of period closes. The display names both dates and says the role is unconfirmed.
  - **New queue reason.** The queue gains `deadline_role_unresolved`, selected by flag next to
    `conflicting | stale`. It is counted in the queue gauge as its own reason.
  - **Precedence.** An honored `pin_close` outranks the cap, because a human attributed the role.
    The classifier is not new evidence, so existing pins stay honored (ADR 0010 is unchanged).
  - **ADR 0015.** It must allow an `escalate` that parks this reason, because today an escalation
    must park a conflicting or stale item.
- **F4. FR refresh for open windows, shipped with F1 to F3, never before them.**
  - This was ADR 0016's known gap. Refreshing FR appends an observation, so it is new evidence to
    the verdict-freshness rules exactly as today.
  - **Release gate.** Replay F1 to F4 over the stored log plus today's FR values before release.
    Report:
    - classifier precision, on a held-out hand-labelled set;
    - the abstention rate;
    - how many of the 54 later-round closes become corroborated (expected about 42);
    - how many conflicts are explained, and how many become `deadline_role_unresolved`;
    - zero explained conflicts on the adversarial fixtures.
  - **Adversarial fixtures:**
    - a portal error of +1 day landing on another deadline;
    - two actions on one date;
    - an extension landing on the reply date;
    - a reply-only amendment;
    - 2026-21939.

## Options

### (a) Sibling windows, one per action or participant class

Each deadline becomes its own `ParticipationWindow`, with its own OCD-ID, linked by the shared
`fr_document_number`.

- **Identity.**
  - The existing ID stays on the initial comment round, so every current comment ID and verdict
    history keeps its meaning.
  - Siblings get one trailing segment: `ocd-participation-window/federal/{frDocNum}/{kind}:{class}`,
    e.g. `/petition:due-diligence` or `/comment:opponents`. The qualifier is derived from the role,
    never from a date.
  - The `OcdId` regex gains the optional segment, and `makeOcdId` gains a `round` argument.
  - Consumers that take the last path segment as the document number break: in this repo, two
    review display lines (`review/core.ts`, `review/cli.ts`). The API's `/v1/windows/*` wildcard
    route already accepts slashes.
- **Contract.** A `round` field, new `WindowType` members or `comment` plus `round`, and the
  widened `OcdId` (a contract-keeper ruling on the LOCKED identity scheme).
- **Isolation is not automatic. Different IDs over shared observations need an explicit evidence
  boundary:**
  - Each sibling consumes only its own classified deadline and the structured values F2 routes to
    it, with their flags.
  - `human_review` observations target exactly one `ocd_id`.
  - **Freshness.** It stays ADR 0010's whole-observation rule, applied conservatively: a new
    observation of the shared FR document or portal document invalidates the verdicts on _every_
    sibling it could feed. Unknown changes still invalidate. That fails in the safe direction (a
    re-review, never a silent overlay).
  - Scoped freshness is a later refinement, and it needs its own proof.
  - The ADR 0014 echo rule applies only to the sibling that the portal value is routed to under F2.
- **Amendments.** Per-action amendment outcomes need their own design (see increment 2). The ADR
  0016 resolver is a single comment-close chain, and it stays that way for the base window.
- **API.** 2–5 rows per notice, grouped by `fr_document_number`. Each row has its own status,
  confidence, verdicts and accuracy trail.
- **Cost.** Applied to every kind, about 170 extra windows, most of them single-source, plus the
  widest change to consumers.

### (b) One window holding several typed deadlines

`ParticipationWindow` gains `deadlines[]`, each with its own close, confidence, flags, provenance
and status.

- **Identity.** Unchanged, with a deadline key per entry.
- **Contract.** `HumanReviewVerdict`, `ConflictRecord` and `AccuracyRecord` all gain the key, and
  `change_history` becomes per deadline.
- **Every keyed subsystem must thread the key:** verdict honoring (0010, 0014), amendments (0016),
  the queue, verification and the CLI. Any one that forgets it leaks a verdict across deadlines.
- **Window-level confidence.** It needs an aggregate that hides a weaker deadline behind a stronger
  one.
- **Verdict.** (b) is (a) rebuilt inside a row, with more places to get isolation wrong. Not
  recommended.

### (c) One close, plus documentary related deadlines

The window keeps one close: the comment period's, under F1 to F3. It gains `related_deadlines[]`.

- **What an entry is.** It is an _interpretation_ of the notice's text, not a neutral copy.
- **What an entry carries:**
  - a stable key (`kind:class`), kind, class, route and condition;
  - a date, and the time only if stated;
  - the classifier version;
  - its evidence: the observation id, payload hash and up to 15 verbatim words.
- **Revisions.** Changing an entry bumps the window `version`, and `change_history` records the old
  list, so `change_history` is no longer close-only.
- **Limits in this ADR's scope:**
  - **No reminders on entries.** Anything that reminds needs its own lifecycle, which is a sibling.
  - **No amendment updates.** If an amendment is linked to the window, an entry shows "as printed in
    the original notice; FR {doc} may have changed it".
  - **No verdicts.** A wrong entry is corrected by a classifier version bump plus a fixture. A
    disputed entry surfaces through `deadline_role_unresolved`.
- **Contract (0.13.0, additive):** `DeadlineKind`, `RelatedDeadline`, `related_deadlines` (default
  `[]`), the flags `secondary_deadline_explained` (informational) and `deadline_role_unresolved`,
  and an opportunity read field (see Status).
- **Where (c) alone falls short.** Opponents' round in 2026-21939 is a comment period, and #124's
  petitions need independent review. Neither has a home in documentary entries.

## Decision (proposed)

**Recommended: (c) as documentary context, plus (a) siblings for any deadline that needs a public
"open" claim, reminders or its own review. Never (b).**

**Gate 0 (before build).** Hand-label a held-out set of DATES texts not used to write the
classifier. Run the F4 replay and adversarial fixtures. The operator sees precision, abstention and
coverage before increment 1 starts. This is "validate before building".

**Increment 1: F1 to F4 and (c).** Contract 0.13.0, `reconcile-v2.5`.

- **Closes.** Comment-period closes move to the initial round only where corroborated. Everything
  else goes to `deadline_role_unresolved` (MEDIUM, queue-visible) instead of keeping a silent
  HIGH.
- **First-chance gate.** A notice with an opposition or first-chance round is always
  `unresolved`, so it stays in the queue until increment 2 gives that round a home. 2026-21939's
  conflict is never retired by routing.
- **Amendments.** ADR 0016 is unchanged in scope. An amendment whose text carries more than one
  deadline stays `ambiguous`, as today. Routing uses the amended initial date wherever 0016 moved it.
- **Status.**
  - The window's `status` becomes the **comment period's** status, derived from its own close and
    the flags routed to it.
  - A new read field, `open_opportunities: [{kind, class, date, ocd_id?}]`, lists every deadline
    still upcoming. It is computed at read time and drawn from siblings and related entries.
  - The API's `status=open` filter keeps meaning "comment period open". A new `has_open_opportunity`
    filter covers "anything still open".
  - Which of these drives the headline is decision 3.
- **Verification migration.** This is required engineering, not an option.
  - **The problem.** Moving a close earlier does not create a new verification watch, and a
    pending watch could then grade a reinterpretation as a source-evidence miss.
  - **Pending watches.** For windows whose close moves because of F1 to F4, close the pending watch
    with a new `AccuracyBasis` member, `reinterpreted`. It is excluded from the headline ratio, as
    `unverified_lapsed` is.
  - **New watches.** Snapshot the new version only if it is published before its own close. A
    backdated close (already past when first published) is never graded, because it was never
    claimed in time.
  - **Finalized records.** Kept as they are, including the 15 that graded a reply or opposition
    close.

**Increment 2: sibling windows, contract 0.14.0.** Siblings for:

- **first-chance rounds** (2–4 notices): comment periods by definition;
- **FDA due-diligence petitions** (#124): 26 notices, 4 open, separate docket, own review history;
- any class the operator wants reminders for (decision 5).

Increment 2 also carries:

- **Its own amendment design:**
  - an action-scoped binding (which window does this amendment's sentence target);
  - the close in force per action;
  - chronology and the post-lapse guard per action;
  - the ADR 0016 §8 corroboration on the final date per action;
  - verdict freshness over the historical effects per action.
  - Fixtures: change then reversion, ambiguous target, same-day amendments, a single-deadline move.
- **Sibling retirement.** A minted sibling ID is public. It is retired by deriving it as `unknown`
  with a `retired` tag, never by deleting the row. Rollback of increment 2 means "stop deriving,
  mark retired", not "drop".

**Why this shape.**

- It fixes the measured harm, the silent later-round closes, only where a structured source
  confirms the role. It says so honestly everywhere else.
- It keeps every existing OCD-ID and verdict meaning.
- It spends sibling identity only where a deadline makes a public claim of its own.
- Documentary entries never pretend to be reviewed truth.
- (c) alone fails #124 and 2026-21939. (a) everywhere mints about 170 parse-only windows nobody
  reviews. (b) threads a new key through every trust primitive.

### Interim review-policy rule (until increment 1 ships)

This becomes the next policy version after v1.2 (#138). It goes into the review policy and the
autopilot skill as rule 2a, **subordinate to rules 1 and 3**. It changes only which date is "the
operative comment deadline" and what counts as explaining a competing value.

> **2a. Multi-deadline notices.**
>
> - **Which date.** When the notice's DATES text sets more than one participation deadline, the
>   operative comment deadline is that of the **initial comment round**: the round the notice's
>   general invitation to comment opens, **as amended** by any extension or correction this policy
>   accepts.
>   - It is not the chronologically first date; a PRA or hearing-request date often comes first.
>   - A competing value that is another deadline in the text explains the discrepancy only if all of
>     these hold:
>     - its date equals that deadline exactly;
>     - no other deadline in the text shares that date;
>     - no later round is the **first chance to comment for some class** of participant.
> - **Escalate under rule 1** when:
>   - a later round is a class's first chance (2026-21939);
>   - roles, classes or the order of dates can't be told from the text;
>   - a document states a time other than 11:59 p.m. Eastern, as the ITC notices do (5:15 p.m. via
>     EDIS).
> - **Unchanged.** Identity, the full search, the withdrawal check (rule 3) and the independent
>   verifier apply exactly as they do today.
> - **The note.** It lists every deadline as `kind · date · time if stated · who may file · route`.

Expected effect on today's queue, subject to the full search and the verifier:

- **Pins:** FDA 2026-20766 (Dec 8), DHS 2026-20660 (Nov 9), DEA 2026-19538 (Dec 23), FCC
  2026-10407 and 2026-11353, and PRC 2026-11157 (the initial round in each). The interim rule
  needs exact equality only, not F2's 7-day margin; a human or the verifier reads the text.
- **Escalations:** ITC 2026-10910 and 2026-10914 (stated 5:15 p.m. time), and Copyright 2026-21939
  (first chance).
- **Not a multi-deadline case:** IRS 2026-18574, which is an ADR 0016 correction.
- **Out of reach:** the 48 silent windows. That needs increment 1.

### Where #124 fits

#124 is increment 2's first sibling class. Its six fixtures plus 2026-20766 become the
petition-window fixtures.

- **The shared docket.** FDA-2013-S-0610 is shared across products. A notice-derived identity
  (`{frDocNum}/petition:due-diligence`) keeps unrelated products apart.
- **Time precision.** The petition time stays null unless the text states one; the comment form's
  11:59 p.m. is never copied onto it.
- **Existing verdicts.** The eight existing comment pins stay honored. F1 is a pure function over
  stored raw text, so it adds no new evidence. A later F4 FR refresh does add evidence, and those
  pins are re-reviewed under ADR 0010 like any others.
- **Before increment 2.** The petition is a documentary related entry: shown, never reminded.

## Consequences

- **Contracts and versions.**
  - 0.13.0: `DeadlineKind`, `RelatedDeadline`, `related_deadlines`, two flags,
    `open_opportunities`, and `AccuracyBasis.reinterpreted`.
  - 0.14.0: the `OcdId` widening and `round`.
  - `reconcile-v2.5`; classifier `deadline-v1`; the review policy's next version.
- **Windows change.** Where corroborated, FCC, ITC and PRC closes move **earlier**. That makes a new
  window version, and `change_history` keeps the old close. For open windows the comment period may
  turn `closed` while `open_opportunities` still lists the reply round.
  - Consumers must be told before release. Anyone filtering `status=open` loses those notices
    unless they adopt `has_open_opportunity`.
- **About 12 of the 54 become `deadline_role_unresolved`** at MEDIUM and enter the queue. That is
  the price of not asserting a role we can't confirm, paid in the safe direction.
- **The queue.** It loses the pure role conflicts (at most 6 of today's 10) and gains the unresolved
  reason. Both are counted separately.
- **Regression fixtures** (#137 and #124 acceptance):
  - 2026-21939, 2026-19538, 2026-20766 and 2026-20660;
  - one per template family;
  - FERC 2026-12712 and NOAA 2026-19258 (unresolved);
  - the 13 same-date two-action notices (no routing);
  - the F4 adversarial set.
- **Rollback.**
  - Increment 1: revert to `reconcile-v2.4` and run the projection sweep. Entries empty, flags gone,
    closes back. AccuracyRecords already written with `reinterpreted` stay as written; they are
    append-only.
  - Increment 2: siblings are retired, not deleted (above).

## Decisions only the operator can make

1. **The comment-period definition.** Adopt the sharpened test, or keep "substantive submission".
   Under the latter, FDA petitions and NRC hearing requests are comment periods.
2. **PRA.** Is it a comment period or a related deadline? Its date precedes the rule's comment close
   in 15 of 16 notices.
3. **The headline.** Choose among the comment period's close, the next deadline **open to anyone**,
   or the next deadline of any kind. "The next one a user can use" isn't computable, because the
   user's class is unknown. Also decide what a notice with nothing open to anyone shows, such as ITC
   five-year reviews.
4. **What `status: open` means** in the API and on consumer surfaces: the comment period
   (recommended), or any opportunity.
5. **Which classes get reminders.** Each such class becomes a sibling in increment 2. Restricted
   classes opt-in only?
6. **Scope of increment 2.** Build FDA petitions now (#124: 4 open), or wait for demand? Promote NRC
   hearing requests (28, restricted, separate route)?
7. **How the accuracy gauge shows history.** Footnote the 15 reply-close records, or not. The record
   handling itself is not optional: records are append-only, and `reinterpreted` is required.
8. **The public join key.** The sibling OCD-ID format, and how consumers are told.
9. **Ratify interim rule 2a.**

Not operator choices, because they are required for correctness: verdict isolation (an
`ocd_id`-scoped evidence boundary), the honest unresolved state, the verification migration,
conservative routing, and retire-not-delete.

## Review log

- **Round 1 (2026-10-28, Codex GPT-6 Astra, high), cross-provider.** 12 findings, 10 of them P1.
  All 12 accepted; this text is the revision. The reviewer's verdict: selective siblings plus
  documentary context is the right direction, but the staging and the routing rule as drafted were
  not. Folded in:
  1. Routing by date equality alone could explain away a genuine conflict. F2 now needs equality on
     the effective timeline, no collision within 7 days, and a measured template or a human
     attribution. It abstains otherwise.
  2. The corroboration gate left most of the silent harm untouched (6 of 54 corroborated). The
     unresolved state (F3) and the FR refresh (F4) are now part of increment 1, gated by a replay.
  3. A flag on a HIGH window is invisible to the queue. Added the `deadline_role_unresolved` cap and
     queue reason, the ADR 0015 parking change, and precedence under honored pins. Removed the
     contradiction between "byte-identical" and "new reason".
  4. "0016 unchanged" was unsafe for selective amendments. Increment 1 keeps 0016's single chain;
     per-action amendments are a designed part of increment 2.
  5. Sibling isolation is not automatic. Added the evidence boundary, conservative freshness and
     echo scoping.
  6. "Asserts nothing" was false for related entries. They are now interpretations, with keys,
     conditions, version history, no reminders and no amendment updates.
  7. Status would not have flipped, because portal flags would keep the window open. Flags now
     follow routing; added `open_opportunities` and the filter semantics.
  8. Moving a close earlier breaks verification watches. Added the verification migration and the
     `reinterpreted` basis.
  9. The ITC pins in the interim rule would have violated rule 1's time clause. Rule 2a is now
     subordinate to rules 1 and 3 and selects the amended date; the ITC items escalate.
  10. Number corrections: 33 added, not 31; 48 silent; IRS excluded; the FDA verdict count.
  11. Prevalence is a lower bound, and template frequency is not precision. Added gate 0.
  12. First-chance cases are gated until increment 2. Related-entry revisions are versioned.
      Sibling rollback is retire, not delete.
