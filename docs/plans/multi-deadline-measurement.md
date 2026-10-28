# Multi-deadline notices: measurement (2026-10-28)

Status: spike result. It feeds [ADR 0017](../decisions/0017-multi-deadline-notices.md) (Proposed)
and issue #137; #124 is its first concrete slice. Read-only throughout: no verdicts written, no
windows changed, no autopilot state touched.

## Headline

- **The class is small.** This is a lower bound from a screen, not a classifier result: see Method. **155** FR notices set two or more participation deadlines on different
  dates. **154** of them back a comment window DocketClock holds:
  - **3.0%** of the 5,090 FR-backed comment windows;
  - **2.7%** of all 5,694 comment windows. The 497 Regulations.gov-only windows have no DATES text,
    so they could not be measured;
  - **37 are open**, 3.5% of the 1,071 FR-backed open windows.
- **It is concentrated and templated.** Six agencies hold 136 of the 154 (88%): FCC 36, NRC 28,
  FDA 27, ITC 18, EPA 14, STB 13. 110 of the 155 come from near-verbatim DATES templates in seven agency families: FCC, NRC, FDA, ITC, STB, EPA and PRC.
- **The hard case is rare.** In only **2 to 4 notices** is a later round some group's _first_
  chance to comment:
  - Copyright Office 2026-21939 (open);
  - Copyright Office 2026-11545 (closed);
  - STB 2026-17024 (open, role uncertain);
  - FCC 2026-03070, which sets oppositions with no comment window held.
- **The main harm is mostly silent.** For **54 of the 154 windows (35%)** DocketClock's current
  close is a later round, almost always a reply round:
  - 22 of them are open, and 20 are at HIGH confidence;
  - in 17 the date shown belongs to a round restricted to a class of participant (ITC eligible
    parties, an STB applicant, DEA registrants and applicants). 8 of those are open, 7 at HIGH;
  - **48 of the 54 never reach the review queue**, because both sources agree on the later date. The
    other 6 are live conflicts.
  - **Corroboration coverage.** Only 6 of the 54 have a _stored_ FR or portal value equal to the
    initial-round date. With FR re-read today, 42 of the 54 do (36 of the 48 silent ones). Any fix
    that needs a structured source to confirm the initial round therefore depends on refreshing FR.
- **Queue share:**
  - 23 of the 89 windows that ever had a cross-source conflict (26%) are in this class;
  - **10 of the 37 live queue items (27%)** are in this class;
  - 12 windows carry verdicts. Every one is a `pin_close` on the initial comment deadline (11) or
    its extension (1). No verdict records the second deadline except in free-text notes.
- **FR metadata is not stable for this class.** Since we fetched them, FR has revised
  `comments_close_on` on **42 of the 155**, every time from the later round to the initial-comment
  date. DocketClock reads each FR document once (7,724 FR observations for 7,724 documents).
  - If every FR value were re-read today, FR/portal mismatches in this class would rise from
    **22 to 49**: 33 new false conflicts (FCC, ITC, PRC, Copyright, FERC), and 6 cleared.
  - One cleared case is 2026-21939. It would go to HIGH on Dec 7, 2026 for everyone, which is
    exactly the outcome the autopilot escalated against.

A measured "small" holds for the class as a whole. The silent mis-close is not small inside it: a
third of these windows tell users the wrong round is closing.

## Method

1. **Universe.** Every `federal_register` observation in the k3d DB (7,724), joined to its window
   (status, confidence, flags, resolved close, raw FR and portal values). The data was read with
   read-only SQL (`default_transaction_read_only=on`) and the review CLI (`queue`, `log`,
   `corpus`). The DATES text is the FR API `dates` field stored in `raw_dates_text`.
2. **Candidates.** Every notice whose DATES text has two or more distinct calendar dates after the
   following were removed: publication dates of other documents, history ("originally closed X",
   "extended from X") and range starts. That leaves **466 candidates**, in 311 distinct templates
   once dates are normalized.
3. **Labels.** Every date was labelled with one kind: initial comment, opposition (a later round
   that is a different class's first chance), reply, hearing request, petition, PRA/ICR, meeting,
   effective, reference or other. Each submission deadline also got who may file and the route.
   - The 44 repeating templates (199 notices) were labelled by hand, rule by rule.
   - The 267 one-off texts were labelled by two child tasks against a written rubric.
   - A first Codex GPT-6 Luna pass was discarded: it called 2026-21939's initial round an
     "opposition" and hearing dates hearing requests. It was relabelled by Claude Opus 5.5.
     The other half was labelled by Claude Sonnet 5.5 and spot-checked by hand.
   - Hand checks against published text:
     - ITC 2026-15646: both rounds are restricted and are filed in EDIS by 5:15 p.m.;
     - NRC 2026-19812: hearing requests are open to "any person whose interest may be affected",
       via E-Filing.
4. **Multi-deadline** means two or more submission deadlines (initial comment, opposition, reply,
   hearing request, petition, PRA) on **different dates**. Excluded:
   - one date with two actions, e.g. "comments and requests for a hearing by X" (13 notices);
   - two same-kind dates for different recipients (NOAA 2026-19258, two councils);
   - application, grant, nomination and auction deadlines.
5. **What each source stored.** Each stored value was matched to the deadline kind of the same
   Eastern date: the FR `comments_close_on`, the portal `commentEndDate` (converted to Eastern),
   DocketClock's `resolved_close_utc`, and the live FR value re-read on 2026-10-28 (155 documents,
   FR API, no key).

**Limitations.**

- The FR `dates` field is truncated in 4 of the 155. The labels hold on what is visible.
- Relative deadlines are not counted, e.g. NRC's "request SUNSI access within 10 days".
- The 497 portal-only windows are unmeasured.
- Labels come from DATES text, not full notices. "Who may file" is "unclear" where DATES does not
  say: 11 reply and 13 hearing-request entries.
- **The counts are a screen, so they are a lower bound on prevalence.** Distinct-date selection
  leaves out the cases most dangerous to a date-matching design: one date for two actions (13
  notices), two same-kind recipients, and relative deadlines. Template frequency does not measure
  how precise a classifier would be. A replay on a held-out labelled set is still owed before any
  build (ADR 0017, gate 0).

## Deadline classes

The kinds a notice adds besides its initial comment round. The 2 notices that add both a reply and a
PRA round are counted under reply.

| Class                                          | Notices (open) | Agencies                                             | Who may file the later deadline                                                                                                              | Route of the later deadline                                          | FR stored → FR today                            | Portal stores                       | DocketClock shows         | Ever in queue / live | Verdicts |
| ---------------------------------------------- | -------------- | ---------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- | ----------------------------------------------- | ----------------------------------- | ------------------------- | -------------------- | -------- |
| **Reply**                                      | 72 (22)        | FCC 36, ITC 18, STB 12, PRC 3, Copyright, FERC, USTR | FCC, PRC and Copyright: anyone, answering filed comments. STB: **the applicant only**. ITC: **eligible parties only**                        | FCC ECFS and STB e-filing as for comments; ITC: EDIS for both rounds | reply 43, initial 27 → initial 63, reply 7      | reply 45, initial 12, none 13       | **reply 48**, initial 22  | 5 / 5                | 0        |
| **Hearing request**                            | 37 (6)         | NRC 28, EPA 2, IRS, EEOC, DEA, FDA, FWS, NOAA, SEPA  | NRC: "any person whose interest may be affected". DEA: **registered manufacturers and applicants**. IRS and EEOC: anyone (requests to speak) | NRC E-Filing (different)                                             | initial 37 → initial 37                         | initial 27, hearing 1 (DEA), none 8 | initial 35                | 3 / 2                | 0        |
| **Petition**                                   | 26 (4)         | FDA 26 (patent-term notices, #124)                   | any interested person                                                                                                                        | **docket FDA-2013-S-0610**, not the product docket                   | petition 9, initial 17 → petition 7, initial 19 | initial 9, none 17                  | initial 26 (8 by verdict) | 9 / 1                | 8        |
| **PRA/ICR**                                    | 16 (3)         | EPA 12, BOEM 2, DHS, BLM                             | anyone                                                                                                                                       | OMB/OIRA (reginfo.gov), different                                    | PRA 5, initial 11 → initial 14, PRA 2           | initial 9, none 6                   | initial 14                | 5 / 1                | 4        |
| **Opposition: first chance for another class** | 4 (2)          | Copyright 2, STB, FCC                                | opponents (Copyright 2026-21939); commenters on renewal petitions (2026-11545)                                                               | same                                                                 | mixed                                           | mixed                               | mixed                     | 1 / 1                | 0        |

Totals: 155 notices, 37 open, 23 ever in the queue, 10 live, 12 with verdicts.

The chronologically first deadline is often **not** the initial comment deadline: 32 of 155.

- In 15 notices it is the PRA date. EPA's OMB copy is due at 30 days and the rule comment at 45–60.
- In 15 it is the hearing request, set before the comment close: NRC 5, EPA 2, and one each
  for EEOC, STB, IRS, DEA, SEPA, FDA, FWS and NOAA.
- The other 2 are an FCC opposition round and an FERC notice whose printed reply date (Jul 24)
  precedes its initial date (Aug 24), most likely an agency typo.

A later deadline follows the initial close in 123 notices, by 32 days at the median and 131 at
most.

## Examples (verbatim DATES text)

- **Reply, open to anyone: FCC 2026-16196** (open, HIGH, close shown Nov 5). "Comments are due on
  or before September 21, 2026 and reply comments are due on or before November 5, 2026." Both FR
  (as fetched) and the portal store Nov 5, so DocketClock shows the reply date as the close at
  HIGH. FR today says Sep 21.
- **Reply restricted to the applicant: STB 2026-21628.** "Comments may be filed by December 7, 2026. If any comments are filed, Applicants may file a reply by December 21, 2026. If no opposing
  comments are filed by December 7, 2026, this notice shall be effective on December 8, 2026."
- **Restricted rounds, different route: ITC 2026-17862** (open, HIGH, close shown Nov 16).
  "...the deadline for responses is October 1, 2026. Comments on the adequacy of responses may be
  filed with the Commission by November 16, 2026." Both rounds are for interested parties or
  eligible parties only, and are filed in EDIS by 5:15 p.m.
- **Hearing request, restricted class: DEA 2026-19538** (live conflict). "Registered bulk
  manufacturers of the affected basic class(es), and applicants, therefore, may submit electronic
  comments on or objections to the issuance of the proposed registration on or before December 23, 2026. Such persons may also file a written request for a hearing on the application on or before
  November 23, 2026." The portal stores the hearing-request date.
- **Hearing request before comments: NRC 2026-17147.** "Submit comments by September 21, 2026. A
  request for a hearing must be filed by September 10, 2026."
- **Petition: FDA 2026-20766** (live conflict, #124). The comment/redetermination round closes
  Dec 8, 2026. Due-diligence petitions are due Apr 7, 2027, to docket FDA-2013-S-0610. FR stored
  the petition date and has since changed to Dec 8.
- **PRA: DHS 2026-20660** (live conflict). "Comments must be received on or before November 9, 2026. Information collection comment period: Comments on the information collection described in
  the Paperwork Reduction Act section below must be received by December 7, 2026."
- **First chance for another class: Copyright Office 2026-21939** (live conflict, escalated in
  shadow mode).
  - Dec 7, 2026: initial comments from proponents, supporters and neutral parties.
  - Feb 22, 2027: "Written response comments ... from those who oppose".
  - Mar 22, 2027: replies from supporters and neutral parties.
  - FR stored Mar 22 and has since changed to Dec 7. The portal stores Dec 7.

## Share by agency

| Agency                                                             | Multi-deadline / FR-backed comment windows | Share                                             |
| ------------------------------------------------------------------ | ------------------------------------------ | ------------------------------------------------- |
| International Trade Commission                                     | 18 / 21                                    | 86%                                               |
| Surface Transportation Board                                       | 13 / 34                                    | 38%                                               |
| Nuclear Regulatory Commission                                      | 28 / 125                                   | 22%                                               |
| Federal Communications Commission                                  | 36 / 194                                   | 19%                                               |
| Food and Drug Administration                                       | 27 / 221                                   | 12%                                               |
| Environmental Protection Agency                                    | 14 / 280                                   | 5%                                                |
| Copyright Office                                                   | 3 / 6                                      | 50%                                               |
| Postal Regulatory Commission                                       | 3 / 72                                     | 4%                                                |
| BOEM                                                               | 2 / 17                                     | 12%                                               |
| Ten others (EEOC, IRS, DEA, DHS, FERC, USTR, SEPA, BLM, FWS, NOAA) | 1 each                                     | ≤ 3% except EEOC (1/3), USTR (1/5) and SEPA (1/1) |

## Review-queue history

- **Live queue items in this class (10 of 37).**
  - Multi-stage FCC 2026-10407 and 2026-11353, PRC 2026-11157, and ITC 2026-10910 and 2026-10914.
    In each, FR stored the initial date and the portal the reply or adequacy date. These are the 5
    "multi-stage" items in `plans/review-learning-loop.md`.
  - FDA 2026-20766, DHS 2026-20660, DEA 2026-19538, Copyright 2026-21939.
  - IRS 2026-18574, whose live conflict is the ADR 0016 correction rather than its hearing date.
- **Retired:** 13 windows, all resolved by human verdicts or by the portal moving.
- **Verdicts.**
  - 8 FDA patent notices pinned on the comment date (2026-09-20, the #124 batch), including
    2025-23868. FDA 2026-08455, a hearing-request notice, retired without a verdict.
  - 3 EPA PRA notices pinned on the rule comment date, plus 2026-07800 pinned on an extended comment
    date (2026-09-26/28).
  - Every FDA note mentions the petition deadline in prose. Nothing structured carries it, so a
    consumer sees a closed window and no petition opportunity.
- **No verdict has ever pinned a later round.** This matches the 2026-10-17 interim rule. But the
  rule only reaches windows that enter the queue. 48 of the 54 windows above that show a later round
  as their close never do.
- **Not every live item in this class is a false conflict.** IRS 2026-18574's conflict is a genuine
  ADR 0016 correction. Copyright 2026-21939's must stay visible until opponents' round has a home.
  Both ITC items share a template whose body text sets a 5:15 p.m. EDIS filing time (read on
  2026-15646). The review policy's rule 1 sends a stated non-11:59 p.m. time to escalation whatever
  the date. So at most 6 of the 10 are pure explained-by-role conflicts: FCC ×2, PRC, FDA, DHS, DEA.
- **Accuracy records.** 67 records graded these windows "correct". 15 of those graded a reply or
  opposition close, 14 of them at HIGH. The headline accuracy gauge counts a reply-round close as
  a correct comment close.

## What the data says about the working definition

The operator's working definition is: _a comment period is a deadline by which some group of the
public can make a substantive submission on the proposal; replies, hearing requests, petitions and
PRA are related; the headline is the next deadline a user can actually use; the window stays open
while any opportunity is open._ The data agrees with most of this and disagrees in five places.

1. **"First deadline is the close" (#137's interim wording) is wrong as written.** The
   chronologically first deadline is a PRA or hearing-request date in 30 notices. The rule has to
   say _the initial comment round's deadline_, which is also how the 2026-10-17 note phrased it
   ("initial deadline").
2. **"Some group of the public" admits rounds a non-expert cannot use.**
   - 20 initial rounds are restricted: ITC interested parties (18), DEA registrants and applicants,
     and the Copyright supporters' round.
   - 32 reply entries and 23 hearing-request entries are restricted to a class.
   - DocketClock doesn't know who the user is, so "the next deadline a user can actually use" is not
     computable. The computable version is _the next deadline open to anyone_, with restricted
     deadlines shown and labelled with the class that may file.
   - On that reading, an ITC five-year review has **no** deadline open to the general public. The
     window would then need an honest "parties only" state rather than "open".
3. **Petitions and NRC hearing requests are substantive and broadly open.** FDA due-diligence
   petitions are open to "any interested person". NRC hearing requests are open to "any person
   whose interest may be affected". As written, the definition makes both comment periods, while
   the operator lists them as related. A sharper test fits the data: _a written view the agency
   says it will consider on this proposal_, as opposed to _a filing that starts or joins a separate
   proceeding_ (a petition docket, a hearing, an intervention). Both of these go to a different
   route (FDA-2013-S-0610, NRC E-Filing), which supports the split.
4. **PRA comments fit the definition but not the list.** They are open to anyone and substantive
   on the information collection. In 15 of 16 notices the PRA date comes _before_ the rule's
   comment close. If PRA counted as a comment period, "next usable deadline" would make the OMB
   date the headline for 2–4 weeks on most EPA rules. That reads as an operator decision, not a
   data question.
5. **"Open while any opportunity is open" needs two words, not one.**
   - FCC reply rounds are open to anyone, and both sources store the reply date in 41 notices.
   - If the window is "open" through the reply round, "open" no longer means "the comment period
     is open".
   - So a consumer needs the comment period's own state ("initial comments closed Sep 21") beside
     the opportunity state ("reply comments due Nov 5, answering filed comments"). The status enum
     alone cannot carry both.

The opposition case (2026-21939) is handled correctly by the definition: the opponents' Feb 22 round
is a comment period, because it is their first substantive chance. It is 2 to 4 notices, all from
two agencies with a fixed procedure.

## Implications for the design

- **Rare overall (3%), so the fix must stay proportionate.** But it is common inside six agencies,
  and recognizable from near-verbatim templates in 110 of the 155 (71%). A deterministic DATES classifier
  is feasible; an LLM is not needed.
- **The queue is not the main target.** The 48 silent later-round closes are. Any fix that only
  changes review policy leaves them in place.
- **Refresh and classification have to ship together.** A fix for FR re-fetching (ADR 0016's known
  gap: "FR revising its own metadata") must not land before deadline classification. Alone, it
  creates 33 false conflicts and turns 2026-21939 HIGH on the supporters' date. But classification
  without the refresh can corroborate the initial round for only 6 of the 54. Together they reach 42.
- **#124 is the biggest single sub-class with independent stakes:** 26 FDA notices, 4 open, 8
  verdicts already, and a different submission docket.

## Review log

- **Round 1 (2026-10-28, Codex GPT-6 Astra, high), cross-provider.** Numeric corrections folded in:
  33 added conflicts, not 31; 48 of the 54 are silent, not all 54; the FDA verdict count; and at
  most 6 of the 10 live items are pure role conflicts. Also added: the lower-bound qualification and
  the corroboration-coverage figures (6 stored, 42 after a refresh). Design findings are answered
  in ADR 0017's review log.
