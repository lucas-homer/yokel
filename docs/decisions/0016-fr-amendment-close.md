# 0016. A verified FR extension or correction moves the original window's FR close

- Status: Accepted
- Date: 2026-10-27
- Builds on: the #31 chain pass (cross_window conflicts) and [0014](0014-portal-close-echo-preserves-pin.md).
  Contract 0.12.0; `reconcile-v2.4`; FR parser `fr-v3`; GovInfo parser `govinfo-v1`.
- Plan: `docs/plans/fr-amendment-linking.md` (root cause, evidence, required outcomes).

## Context

Every window's FR side came from one place: the latest `federal_register` observation of that
window's own ocd_id. An extension or correction is a separate FR document with its own ocd_id. The
chain pass could link it to the original, but it only wrote a `cross_window` ConflictRecord, and
nothing fed the amendment's date back into the original's derivation. So the original kept its
superseded FR close forever and sat CONFLICTING (`fr_regs_date_mismatch`) against a portal that
had already moved. Three live windows showed the three ways this fails:

- **Census 2026-18481 / 2026-20328.** Confidently linked (shared docket and RIN), but the date was
  never taken.
- **USDA 2026-18531 / 2026-19710.** Linked only by the LLM adjudicator. The FR API's `dates` field
  is truncated mid-sentence. The citation `(91 FR 57828)` and "on or before November 2, 2026"
  exist only in the published text. The amendment's own `comments_close_on` is 2026-09-11, which
  is the original's publication date and an FR extraction error.
- **IRS 2026-18574 / C1-2026-18574.** Never chained. A correction document's title carries no
  "Correction" keyword and its action/dates are empty, so the keyword flags never fire. The new
  date exists only in the published instruction: `October 16, 2026'' should read `October 26,
  2026''. The FR API does carry the structured link: `correction_of`.

Moving a published close is exactly where fake certainty does the most damage, so any fix had to
default to "unchanged".

## Decision

1. **Published text is an observation.** For FR amendment documents in the 120-day keyword
   lookback, the poller fetches the GPO rendition from GovInfo
   (`content/pkg/FR-{date}/html/{doc}.htm`). It appends that as a `govinfo` observation on the
   amendment's own ocd_id. `raw_dates_text` holds the DATES section, or the correction
   instructions for a correction. The fetch is append-only, payload-hash deduped and capped per
   cycle. `govinfo` was already an ObservationSource and a 0001 CHECK member.
   - **NUL normalization.** `raw` is the upstream page verbatim except for U+0000. GPO renditions
     carry NULs as page-break artifacts (49 of 717 live pages), and Postgres can store U+0000 in
     neither text nor JSONB. They are stripped before anything is stored, hashed or extracted, so
     `payload_hash` is over the normalized raw and stays deterministic. This is the one deliberate
     deviation from "verbatim".
   - **Bounded retry.** Failures go through the shared `poll_dead_letter` ledger (source `govinfo`).
     A 404 on or within 3 days of publication means "not published yet" and is never recorded. A
     later 404, or any fetch, parse or ingest error, counts as a failure. Candidates are ordered by
     consecutive failures, then newest first, so documents that keep failing can never starve a
     fresh one. After 3 consecutive failures a document is dead-lettered, and from then on only a
     daily slow drain retries it.
2. **`correction_of` is a correction (`fr-v3`).** Old rows are never backfilled. Every chain and
   amendment read derives the flag from `raw`, so fr-v2 rows behave identically.
3. **Deterministic identity.** `linkBasis` identifies a pair by one of four bases, strongest first:
   - `correction_of`: FR states the link, so no docket is needed.
   - `doc_number`: a shared docket, and B's FR or published text names A's document number.
   - `docket_rin`: a shared docket and a shared non-empty RIN.
   - `citation`: B's text carries A's FR citation as a whole token, and that citation is unique
     across all candidates. It also needs a shared docket, a shared RIN, or B's title starting with
     A's title.

   A shared RIN is only ever a corroborator. The old rule is a subset of this, so every existing
   confident link stays confident. Some LLM-only links (USDA) become confident and lose
   `llm_corroborated`. An LLM verdict is never a basis.

4. **The amended close is resolved by a pure, conservative rulebook** (`resolveAmendedClose`).
   Only deterministically linked amendments are evidence. Tightened after the round-1
   adversarial review:
   - **Reopenings and withdrawals** never move a date: the outcome is `ambiguous`.
   - **Corrections.** A correction moves the close only through a published "X should read Y"
     instruction whose own sentence places it in the DATES section, with X equal to the close in
     force. A mention of "DATES" elsewhere in the body binds nothing, and a `;` continues the same
     instruction.
     - **Closed-world allowlist (round 3).** Rounds 1 and 2 rejected named roles, and each round
       found a new escape ("public symposium", "oral presentations", "public inspection", "petitions
       for reconsideration"). So the rule is now an allowlist. The GPO correction header ("In
       [proposed rule] document N beginning on page P in the issue of <day>, <date>, make the
       following correction:") and the quoted strings are removed. Then **every** remaining word
       must be one of:
       - location vocabulary: page, column, line, paragraph, section, heading, DATES, under,
         ordinals, top / bottom / from, numbers and document numbers;
       - explicit comment-period vocabulary: comment(s), period, deadline, date, close, must be
         received / submitted, by, which;
       - correction boilerplate: in, of, the, and, should read, make the following correction, as
         follows, same.
     - Any other word is a qualifier we don't understand, and the instruction binds nothing.
     - **The corpus's 12 real correction bodies:**
       - Two bind: C1-2026-18574 (IRS, Oct 16 → Oct 26) and C1-2026-19812 ("in the DATES
         section, in the fourth and fifth [[Page 64409]] line", Dec 28 → Nov 30).
       - C1-2026-16331's two date pairs sit outside DATES and bind nothing.
       - C1-2026-09289's seven pairs are text, not dates.
       - The other eight have no "should read" date pair; they are "the heading should read as
         set forth above" or similar.
   - **Extensions: comment context.** Text is read sentence by sentence; a sentence mixing roles is
     split at `;`. Each clause gets one role:
     - _comment_: about comments or the comment period;
     - _unresolved_: comments mixed with another role, or an information-collection / Paperwork
       Reduction Act clause;
     - _noncomment_: an established other role, such as a hearing, meeting, registration, request
       to speak or effective date;
     - _neutral_: no role words at all.

     A deadline phrase (on or before, on or by, no later than, to / until / through, must be
     received / submitted / postmarked by …, closes / ends on) supplies a candidate only inside a
     comment clause.

   - **Extensions: the second-deadline guard.** Every other date in any clause whose non-comment
     role is not established (comment, unresolved and, since round 2, neutral clauses) must equal
     the single candidate. Recognized phrasing doesn't matter, so this catches "Therefore, they
     should be submitted … by September 15".
     - **Context only, never value (round 3).** The only exclusions are noncomment clauses and
       dates whose own text marks them as a citation, or as a past or replaced close:
       - "published (in the Federal Register (FR)) (at 91 FR N) (on) D", "published at 91 FR N
         (D)", "Dated: D";
       - "originally / previously … D", when that keyword governs this date: same clause, within
         60 characters, no other date in between;
       - "(was / had been) scheduled to close on D", "would have closed on D", "closed / ended on
         D";
       - "extended from D to …", "the D due date … is extended".

       Rounds 1–2 also dropped a date equal to the close being extended or on or before
       publication. That is gone: "Electronic submissions must still reach the agency by October
       16, 2026" is a live second deadline whatever its value.

     - A date-bearing extension whose guard finds a competing date but which yields no candidate
       is `ambiguous` (round 2), and that poisons the chain.
     - Over-detection can only add ambiguity.

   - **Extensions: the date itself.** It is read from the published DATES. FR `dates` is used only
     when it agrees with a valid FR `comments_close_on`. A plausible FR `comments_close_on` that
     disagrees with the text gives `ambiguous`; one on or before the amendment's publication is
     ignored as an extraction error. This cross-check runs before a restatement is accepted
     (round 2).
   - **Chronological chain.** Amendments are evaluated in publication order against the close in
     force: the original's, then each verified amendment's.
     - Each must be published on or before the close it amends; a gap is a reopening in substance
       and gives `ambiguous`.
     - An extension must move the close later. Restating the close an earlier amendment set
       confirms it (no change); restating the original close gives `ambiguous`.
     - Amendments on the same day must agree, and any ambiguity makes the whole outcome
       `ambiguous`.
     - `amendment` is the last verified one; `observation_ids` lists every verified one.
   - **Measured on the 717 real GovInfo pages** (DATES or correction text, no original context),
     against the pre-review resolver:
     - A single date: 241 before, 226 after round 1, 226 after round 2, 225 after round 3.
     - Ambiguous: 2, then 3, then 125, then 177.
     - None: 474, then 488, then 366, then 315.
     - Round 1 changed two dates. EPA 2026-20982 now reads its "on or by November 30" comment
       deadline, not its Oct 19 hearing-request cutoff. Interior 2026-14450 is ambiguous (Aug 17
       written comments vs Sep 15 information-collection comments).
     - Round 1 also removed a date from 14 documents: 7 effective dates, petitions, objection or
       hearing-request deadlines and a CBP test period; 5 information-collection lines; 2 mixed
       "comments and requests for a public hearing" sentences.
     - Round 2 moved 122 documents from none to ambiguous: date-bearing text with no recognized
       deadline, such as "DoD will consider all comments received by …" or "FRA must receive
       comments … by …". These leave a window unchanged.
     - No date was lost or added in round 2.
     - Round 3 moved 51 documents from none to ambiguous: newly counted, context-free dates such as
       "Applicable August 20, 2026" or "takes effect on September 23, 2026". One document lost its
       date: 2026-16083's "As of July 21, 2026, the proposed rule … is withdrawn" now competes with
       its Sep 8 comment deadline. The extension documents behind the MEDIUM → CONFLICTING windows
       (2026-17132, 17649, 17741) keep their dates, because their citation and "due date … is
       extended" phrasing is excluded by context.

5. **`reconcile-v2.4` applies it before the rulebook.**
   - With `amended`, the FR side's Eastern close becomes the amended date. FR-vs-Regs agreement
     and mismatch are then judged exactly as before.
   - The informational ConflictFlag `fr_close_amended` (contract 0.12.0) rides along, and the
     amendment's observations join `current_observation_ids`.
   - `raw_fr_close_date` keeps the original FR value.
   - `none` and `ambiguous` give byte-identical output.
   - Every path that derives a window passes the same outcome: `reconcileOcdId` (FR and Regs
     ingest, the rederive sweep, the status refresh, the review write) and the review CLI's direct
     calls. The loader reads only the observation log, so the blind derivation leaks no verdict.
   - After the chain pass, the poller re-derives the originals of every confident link, so a newly
     arrived amendment moves its original in the same cycle.
6. **Only derivation sources are evidence about a window (amends ADR 0010's freshness rule).**
   `DERIVATION_SOURCES` = `federal_register`, `regulations_gov`: the only sources `reconcile()`
   reads for a window's own deadline. It is named explicitly, never "every source that is not
   `human_review`", so a future source has to be added deliberately.
   - **Why it changed.** A GovInfo row lands on the amendment document's own chain. `reconcile()`
     never reads it there; only the original window's amendment loader does. Under the v2.3 rule
     ("every newer non-human observation is evidence") it superseded honored verdicts anyway. The
     2026-10-27 replay lost 12, four of them on open windows (2026-18218, 18297, 18298, 18300).
     2026-15026 fell back to a junk 1900-01-01 portal close. The ADR 0010 / 0014 principle applies:
     no new evidence, no invalidation.
   - **What follows the rule.** `selectHonoredVerdict` counts only derivation-source observations as
     newer evidence, which covers the queue's escalation marks, the gauge, `review log` and `corpus`,
     since they all ask the engine. The review write's evidence set and race check
     (`latestSourceHashes`, `--expect`, `reviewed_payload_hashes`) use the same list. `review show`
     lists exactly those hashes under "latest per source" and shows GovInfo separately as `context`.
     Verify's post-close "confirmed check" counts only `RECONCILE_INPUT_SOURCES` (the derivation
     sources plus `human_review`): a GovInfo fetch checks nothing about the window's close.
   - **What still invalidates a verdict.** A newer FR observation, and a newer Regs observation
     beyond the ADR 0010 / 0014 exceptions, exactly as before. `reconcile-v2.4` is unreleased, so
     the rule ships in v2.4 with no further version bump.

7. **A linked amendment newer than the verdict is new evidence (round 1, finding 1).** Since v2.4
   a deterministically linked amendment is an input to the original window's derivation. So it is
   evidence for that window's verdict, although it lives on another chain.
   - **The test is effect over history** (round 2: the ADR 0010 way). `reconcile()` stays pure:
     the loader passes the resolver's inputs (`ReconcileOptions.amendmentInputs`) with a
     **timeline**.
     - **The timeline:** the linked evidence set as it stood after each fetch time of any candidate
       amendment's FR or GovInfo row. A candidate is any document whose rows ever carried an
       amendment signal, and its linkage is re-decided per state from its rows as of that time.
     - **The rule:** `selectHonoredVerdict` takes the state at the verdict's `fetched_at` as the
       baseline. If any later state derives a different outcome (amended date vs the original's,
       or a different amended date), the verdict is superseded, exactly like a newer FR
       observation.
     - **So:** a material change followed by a reversion never revives a verdict, and a re-fetch
       deriving the same outcome never invalidates one. A document that becomes linked, or stops
       being one (for example, a later row that drops its amendment flags), is a change.
     - **Citation uniqueness is counted per state (round 3).** A document carrying A's citation
       counts from its first FR fetch on, and every such arrival is a timeline boundary. Round 2
       used today's count in every state. That let an unrelated document sharing A's citation,
       arriving later, erase an extension from the past and revive the verdict that extension had
       superseded. A verdict that was superseded stays superseded.
     - A caller holding only an outcome, with no timeline, falls back to the outcome's own fetch
       times; an unknown time counts as newer.
   - **The full linked set is used,** not only date-bearing amendments. A reopening linked after a
     pin un-amends the window, and that is new evidence. A GovInfo copy of an extension the
     reviewer already had, confirming the same date, is not.
   - **Same rule everywhere follow-up 3 aligned.** The review core's honored checks (queue marks,
     gauge, `show`, `log`, `corpus`, the write's confirmation) ask the engine with the same inputs.
     The review write binds a verdict to the linked amendments' latest FR and GovInfo observations
     too: `reviewed_payload_hashes`, `--expect` and the race check. `review show` lists them under
     "latest per source" as `linked amendment …`. Escalations un-park by the same rule.
   - **On the replay's seven closed pinned windows that gain `fr_close_amended`** (2026-07061,
     07800, 10815, 12621, 13294, 13674, 16965), every amendment's FR row was fetched before the
     verdict, and every pin already equals the amended date. Four GovInfo copies were fetched later
     but confirm the same date. All seven stay honored.

8. **The corroboration backstop (round 4; the primary's decision).** Four review rounds each found a
   new way DATES wording could slip a wrong date past the parser: hearing ranges, unrecognized
   second deadlines, anaphora, role words, quoted qualifiers, digit tokens, loose "originally" /
   "closed" context. The tail of FR phrasing is long, and a text parse alone must never move a
   published close. So the parser is no longer the only gate.
   - **The rule.** An amended date moves the original window's FR side only when an independent
     signal corroborates it: (a) the window's own latest portal close (Regulations.gov
     `commentEndDate`, as an Eastern calendar date) equals it, or (b) the amendment that set it
     carries its own FR `comments_close_on`, plausible (after that document's publication) and
     equal to it.
   - **Otherwise** the outcome is `ambiguous`, the reason is recorded
     (`corroborateAmendedClose`), and the window derives byte-identically to having no amendment.
   - **Chains.** Only the FINAL effective date needs corroboration, and only from the amendment
     that set it. Intermediate steps still pass every resolver check.
   - **Where it applies.** In the derivation (`reconcile()`), which holds the portal close, not in
     the resolver; the parser has to stay correct on its own. The verdict-freshness rule (§7) still
     compares the resolver's effects, deliberately. A newly read but uncorroborated amendment date
     doesn't move the window, but it does send a human verdict back for re-review. Conservative in
     both directions.
   - **Effect on the production copy:**
     - Census (portal and B's FR value), USDA (portal; B's FR value is the bad 09-11) and IRS
       (portal) still amend.
     - EPA 2026-05167 (FR-only) still moves, because extension 2026-08518's FR value corroborates.
     - All seven high → high windows are corroborated twice.
     - 12 of the 13 closed MEDIUM → CONFLICTING windows stay conflicting, each corroborated by its
       extension's own FR value. 2026-13761 reverts to unchanged: its extension 2026-18218 really
       does say Dec 7, but its FR value (07-08) is an extraction error and the portal never moved.
       That is the price, paid in the safe direction.

## Consequences

- Census, USDA and IRS become HIGH with `fr_close_amended` and leave the review queue. Every other
  recorded window derives byte-identically (proven on the stored production log).
- The rulebook cannot move a date on an LLM link, on a reopening or withdrawal, on a post-lapse
  amendment, or on text carrying more than one deadline. FR's amendment metadata is never trusted
  on its face. An honored human verdict still overlays afterwards, exactly as before.
- **The post-lapse guard covers corrections too.** A correction published after the original close
  is `ambiguous`, which goes beyond the plan's extension-only wording. That is deliberate: a date
  change printed after the period ended is a reopening in substance.
- The poll cycle gains two passes: `govinfo` (before chain) and `amended_originals` (after chain).
  Both are isolated and counted in `docketclock_poll_pass_failures_total`. The first deploy
  backfills GovInfo text for every recent amendment over a cycle or two.
- `loadAmendmentEvidence` runs on every `reconcileOcdId`, so it must be cheap. The first per-call
  query took 0.4–5.4 s on a production copy (p50 3.4 s, p95 6.5 s), and a full re-derive extrapolated
  to hours.
  - **The amendment corpus.** The candidate set for every window is drawn from one corpus: the
    latest FR row of each document whose latest row carries an amendment signal, plus its latest
    GovInfo text. It is memoized per pool client behind a freshness stamp (table OID, and the row
    count and max `fetched_at` of the FR and GovInfo rows). The log is insert-only, so every change
    the corpus reads bumps the stamp. A transaction always builds a private corpus, so uncommitted
    rows never leak. The dev-only #O4 backfill, which bypasses the append-only trigger, requires a
    restart of long-lived processes.
  - **Indexes (migration 0013).** It adds the window-by-`ocd_id` index main never had, the stamp
    index, the amendment partial index and the citation expression index.
  - **Results.** p50 1.1 ms, p95 2.0 ms. A full re-derive takes 24–29 s; main took 65 s, and 15 s
    once it also gets the `ocd_id` index.
  - **Equivalence.** The original query is kept as a test oracle.
- Known gaps, unchanged:
  - FR revising its own metadata after we fetched (ICE 2026-20660) needs an FR re-fetch for open
    windows.
  - Portal-only extensions (EPA 2026-18134) have no FR amendment to link.
  - A correction of an extension (a correction whose `correction_of` names B) is not chained back
    to A.
