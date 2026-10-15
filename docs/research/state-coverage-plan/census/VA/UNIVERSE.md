# State universe: VA / v0.1-proposed (2026-10-15)

Status: **draft: proposal for owner signature. Not frozen.** Completeness: not established. Every
included process is single-lineage while Town Hall is on hold; see "Source map" and Q8.
Owner: primary (research child draft). Human reviewer: owner. Decision date: _pending owner signature_.
Protocol/schema versions: PROTOCOL v1.1. Rights: `va-register` and `va-register-rss` (allowed);
`va-townhall-listings` and `va-code-reference` (on hold), all at version `2026-10-15.1`, owner
decision `owner-2026-10-15`, open outreach `rights/outreach/VA.md`.
Proposed scope label shown to users: "Virginia regulatory actions published in the Virginia Register
of Regulations: notices of intended regulatory action, proposed and fast-track regulations, petitions
for rulemaking and periodic-review comment periods. Hearings announced only on Town Hall are not
covered."
Statewide claim justified? **No.** Evidence: single lineage (Q8), a known hearing-announcement gap
(Town Hall-only meetings, Q9) and open scope calls (Q1–Q7).

Evidence basis: an attended scoping run on 2026-10-15 made 30 sequential requests to
`register.dls.virginia.gov` only, at least 6 s apart, with UA `DocketClock-research/0.1
(github.com/lucas-homer/yokel)`. 29 returned 200 and one returned **500**
(`publicdocket.aspx`, not retried). No 403 or 429. The log is at the end. It fetched the home page,
RSS feed, 11 issue TOCs (42:20–43:04), section pages (periodic reviews, general notices, petitions),
5 notice detail pages, the Register information page, publication deadlines, the citizen
participation page and one issue PDF. **No Town Hall URL** and **no `law.lis.virginia.gov` URL**
was fetched; both are on hold. Statute references come from Register text. Scratch bytes are in
`/tmp`, outside git, and are not census originals. All counts are planning estimates from TOC
labels. None are census results.

## Agency and process universe

**Roster (dated 2026-10-15).** The universe is defined by the filing/publication obligation. The
Register says "All regulations must be filed with the Registrar of Regulations for them to become
law" and "The Virginia Register provides a snapshot of all regulatory activity happening in
Virginia" (citizen_participation, req 27). It also says new and amended regulations "both as
proposed and as finally adopted, are required by law to be published in the Virginia Register"
(Register information page, req 26). The Register is **broader than Town Hall**: "Not all state
agencies' regulations are found on the Town Hall" (req 27). Exempt bodies publish here too, e.g.
SCC under § 2.2-4002 A 2 (req 6) and the Board of Wildlife Resources under § 2.2-4002 A 3 (req 24).
Roster source for enumeration: VAC title + agency code (e.g. `4VAC15`) of every action in the
interval and backward-search TOCs. The canonical agency list is the Virginia Administrative Code
agency index on `law.lis.virginia.gov`, which is on hold (Q10). The Register's cumulative table
(`/documents/cumultab.pdf`) is an allowed same-lineage alternative.
**Observed in 42:20–43:04 (11 issues):** 41 distinct VAC agency codes with non-final actions.
Top: 4VAC15 (DWR) 12, 12VAC30 (DMAS) 11, 12VAC5 (Health) 9, 9VAC25 (State Water Control Board) 7,
18VAC110 (Pharmacy) 7, 2VAC5 (Agriculture) 6, 18VAC41 6, 8VAC20 5.

| Agency ID/name | Roster authority, version, evidence locator | Process/stage | Included? | Reason/authority | Authoritative publication(s) | Gaps / single_lineage + human ref |
|---|---|---|---|---|---|---|
| All agencies publishing in the Register (APA and APA-exempt) | VAC agency codes in TOCs (reqs 3, 9–18); VAC index on hold (Q10) | **NOIRA** (§ 2.2-4007.01): written-comment window; a hearing-request window if the notice offers one | **Yes** (Q1) | "Notice is hereby given in accordance with § 2.2-4007.01 … Public Comment Deadline: October 21, 2026" (6VAC20-90, req 8). The plan requires a NOIRA decision; recommended include | Register issue PDF (official, § 2.2-4031 C) + Register HTML details | single_lineage (Q8); Town Hall forum dates may differ (Q9) |
| same | same | **Proposed regulation (standard APA)**: comment window (≥60 days) + each scheduled hearing | **Yes** | "receives public comments for a minimum of 60 days" (req 26). Header fields "Public Hearing Information" / "Public Comment Deadline" (2VAC5-360: published 10-05, deadline 12-04, "No public hearing is currently scheduled", req 25) | same | Hearings scheduled later may appear **only on Town Hall** (Q9) |
| same | same | **Proposed regulation, APA-exempt agencies** (DWR, SCC, others claiming § 2.2-4002) | **Yes**: comment window; SCC "hearing upon request" is a hearing-request window (Q2) | DWR 4VAC15-20: "Public Comment Deadline: August 17, 2026" (req 24). SCC 20VAC5-340: "A public hearing will be held upon request. Public Comment Deadline: October 9, 2026" and the order invites parties to "request a hearing" (req 6) | same | SCC docket (`scc.virginia.gov`) has no rights record |
| same | same | **Fast-track** (§ 2.2-4012.1): comment window; objections by ≥10 persons convert it to standard process | **Yes**, comment subtype `objection_capable` | "fewer than 10 persons object" (req 26). 9VAC25-210: published 09-21, "Public Comment Deadline: October 21, 2026. Effective Date: November 5, 2026" (req 7) | same | same |
| same | same | **Petition for rulemaking, initial agency notice** (§ 2.2-4007): 21-day comment window | **Yes** | "Public comment on the petition will be received from September 7, 2026, to September 28, 2026" (12VAC5-410, req 20) | Register "Petitions for Rulemaking" section | ~0.5/issue (estimate) |
| same | same | **Petition agency decision** | No opportunity. **Update** (closes the petition proceeding) | "Agency Decision: Request denied" (9VAC25-31, req 19) | same | — |
| same | same | **Periodic review / small business impact review, agency notice with comment period** (§§ 2.2-4007.1, 2.2-4017) | **Proposed yes**, subtype `periodic_review` (Q3) | "Public comment period begins September 21, 2026, and ends October 12, 2026" (13VAC6-11/-20, req 4). Some periodic notices piggyback on a NOIRA ("The Notice of Intended Regulatory Action … serves as the agency notice", req 22); dedupe those to the NOIRA window | Register "Periodic Reviews" section | ~0.5/issue (estimate). Reports of findings: excluded |
| same | same | **Final regulation** | No opportunity | Adoption | same | — |
| same | same | **§ 2.2-4007.06 request window** (25+ persons may request more comment on changes made after proposal, during the 30-day final adoption period) | **Proposed: exclude** as an opportunity, record as candidate rejects (Q4) | Info page (req 26). Not separately noticed. Its applicability turns on "certain changes"; volume would be large (~9.5 finals/issue) | same | — |
| same | same | **Governor-required additional 30-day comment period; agency suspension/re-solicitation notices** | **Yes**, as a new participation round on an existing proceeding | "Notice of the additional public comment period required by the Governor will be published in the Virginia Register" (req 26) | same | Not observed in the sample |
| same | same | **Action Withdrawn**; extensions; corrections/errata to deadlines or hearings | **Yes, as updates** | "Action Withdrawn" entries in 42:20 (4), 42:22 (2), 43:01 (1), 43:02 (1); Errata section (type 11) | same | — |
| same | same | **Emergency regulations, extensions of emergency** | No (but a companion NOIRA counts as a NOIRA) | § 2.2-4011; effective on filing (req 26) | same | — |
| same | same | **General Notices**: informal comment on draft regulations before a NOIRA (e.g. DBHDS 12VAC35-260, "Public Comment Deadline: September 25, 2026", req 5) | **Owner call** (Q5); proposed include as `early_stage` when dated | Pre-APA-stage participation on a named regulation | Register "General Notices" | — |
| DMAS (12VAC30) | — | **General Notices: "Opportunity for Public Review of and Comment on Intent to Amend State Plan"** (5 in 43:03) | **Proposed: exclude** (Q6) | Medicaid State Plan public notice, not a VAC regulatory action | same | Volume swing ~0–5/issue |
| DEQ and others | — | General Notices: enforcement orders, TMDLs, permits, reports, workgroup meetings | **No** | Enforcement/permits/meetings are out of scope | same | Inspect as exclusions |
| — | — | Guidance documents; Governor's executive orders; forms; legislative objections | **No** | Guidance/legislative are out of plan scope | — | — |
| Local government, courts, General Assembly | — | — | **No** | Plan exclusion | — | — |

Exceptions are checked in the notice body, not from TOC labels. One 43:01 NOIRA was listed under
"Regulations" with the label "(Notice of Intended Regulatory Action)", not in the NOIRA section.
**Explicit exclusions:** as in the table, plus public comments and commenter data (never collected).
**Narrow scope boundary:** opportunities published in the Virginia Register. Town Hall-only
meetings, forums and comment dates are outside the declared universe while Town Hall is on hold.
That is a named gap (Q9), not misses.
**NOIRA/early-stage policy:** proposed include NOIRA (Q1). Pre-NOIRA informal comment is Q5.
Decide before enumeration.

## Interval and cohorts

- **Proposed civil half-open interval:** `[2026-01-26, 2026-07-27)`, zone `America/New_York`.
  This is **13 complete issues, Vol. 42 Iss. 12–24, over 26.0 weeks**. Dates are stated in RSS
  item titles (req 2), e.g. "Volume 42, Issue 12 - Monday, 26 Jan 2026" … "Volume 42, Issue 24 -
  Monday, 13 Jul 2026". 42:25 (2026-07-27) is excluded.
  - *Justification:* VA volume is about a quarter of WA's per week. 149 cannot be reached in 12
    weeks; see the arithmetic below. Ending at 42:24 leaves the longest common window observable
    before Phase 1 ends: a 60-day proposed period runs to about 09-11, plus the 19-day filing lag
    and one issue, which lands in 43:05 (2026-10-19).
  - **This exceeds the ~12-week guidance and says so.** Alternatives are in Q7.
- **Publication-time authority:** publication date = issue date in the RSS title / issue header.
  Filing cutoff: "Items received later than noon on the specified deadline date are published in
  the next issue" (req 28). Filing deadlines are Wednesdays, 19 days before the Monday issue.
  Time-of-day of online posting is not evidenced; date precision only.
  Pre-publication material exists. The home page lists "Regulations Effective before Publication
  in the Register" with filing date, effective date and a future "Register Date" (req 1). The
  earliest authoritative publication is the issue unless the owner rules that the home-page
  pre-publication list counts (Q11). Boundary disputes are review cases with candidates retained.
- **Complete cycles and observed rate (TOC labels, 11 issues, reqs 3, 9–18):**

  | Issue (date) | NOIRA | Proposed | Fast-track | Σ notices | Action Withdrawn | Final |
  |---|---|---|---|---|---|---|
  | 42:20 (05-18) | 4 | 2 | 1 | 7 | 4 | 10 |
  | 42:21 (06-01) | 2 | 0 | 2 | 4 | 0 | 6 |
  | 42:22 (06-15) | 5 | 3 | 2 | 10 | 2 | 4 |
  | 42:23 (06-29) | 3 | 1 | 2 | 6 | 0 | 2 |
  | 42:24 (07-13) | 3 | 5 | 1 | 9 | 0 | 6 |
  | 42:25 (07-27) | 4 | 12 (DWR cluster) | 1 | 17 | 0 | 6 |
  | 42:26 (08-10) | 0 | 1 | 0 | 1 | 0 | 9 |
  | 43:01 (08-24) | 2 | 2 | 4 | 8 | 1 | 19 |
  | 43:02 (09-07) | 12 | 0 | 8 | 20 | 1 | 10 |
  | 43:03 (09-21) | 2 | 1 | 9 | 12 | 0 | 15 |
  | 43:04 (10-05) | 4 | 2 | 4 | 10 | 0 | 18 |
  | **Σ** | **41** | **29** | **34** | **104** | **8** | **105** |

- **Projected opportunities for the proposed interval (arithmetic):**
  - Mean NOIRA+proposed+fast-track = 104 / 11 = **9.45 notices/issue**, one comment window each.
  - Extras per issue (estimates; sample is thin):
    - petition initial notices ≈ 0.5 (1 seen in 2 petition sections, reqs 19–20);
    - periodic-review comment notices ≈ 0.5 (1 dated window in 3 sections, reqs 4/21/22);
    - scheduled hearings on proposals ≈ 0.35 × (29/11 = 2.6) ≈ 0.9 (0 of 3 sampled proposals had
      a scheduled hearing; SCC offers a hearing on request).
    - Extras total ≈ 1.9/issue.
  - Central: (9.45 + 1.9) × 13 = 11.35 × 13 ≈ **148**.
  - Low: uses only the overlapping sampled issues 42:20–42:24 (36 / 5 = 7.2 notices).
    (7.2 + 1.9) × 13 ≈ **118**.
  - High: spike issues like 43:02/42:25 recur. (14) × 13 ≈ **182**.
  - **Seasonal caveat:** 42:12–42:19 (Jan–May, during and just after the General Assembly session)
    were **not sampled**. Their rate is unknown.
- **Target and independence limits:** target ≥149. Central projection 148, **at or just below
  target. Likely shortfall 0–31; a low case of ~118 is plausible.** Clustering is strong:
  - DWR filed 12 proposed chapters in one issue (42:25) and 11 finals in 43:03, presumably sharing
    one comment process;
  - DMAS and Pharmacy file in batches;
  - fast-track and NOIRA are fixed templates.

  About 148 notices is **not** 148 independent trials.
- **Low-volume shortfall and extension rule (predeclared):** step-3 TOC accounting happens before
  any enumeration or adapter output. If it projects <149, extend backward by whole issues (42:11,
  42:10, …) to a maximum of all Vol. 42 before 42:25, i.e. start 2025-08-25 (~27 additional weeks).
  Even then, if the count is below 149, report the shortfall honestly. Budget: the VA envelope below.
- **New-notice rule:** earliest evidenced authoritative publication (issue date) inside the interval.
- **Carry-in rule and backward search boundary:** opportunities opened before 2026-01-26 whose
  close, hearing or request deadline is ≥ 2026-01-26. There is no statutory lapse cap of the WA
  kind in the sources read, so the boundary is evidence-based:
  - Scan TOCs backward from 42:11, issue by issue.
  - Stop at the first issue older than start − (largest publication→deadline/hearing lag observed
    among all notices scanned so far) − one cycle.
  - Minimum floor: 42:06 (2025-11-03). That is 12 weeks, covering a 60-day proposal plus a 30-day
    extension margin.
  - If the rule cannot terminate inside Vol. 42 (the first issue is 2025-08-25), completeness for
    carry-ins is unresolved.
  - The archive reaches Vol. 25 (2008) via RSS, which has 472 issue items (req 2).
- **Older-proceeding updates/reopenings:**
  - Every Register action carries a stable proceeding key `VA.R. Doc. No.` (e.g. "R27-8520; Filed
    August 25, 2026", req 8; "R26-8702", req 24).
  - Updates in the interval (Action Withdrawn, errata, Governor additional comment, re-proposals,
    petition decisions) are resolved to their target by Doc. No. through the archive, at any age.
  - The Register's public docket route (`publicdocket.aspx`) returned **HTTP 500** (req 29). It was
    not retried and is not relied on.
  - Unresolvable targets get `target_unresolved_reason` + review.
- **Other interval updates:** updates in 42:13–42:24 targeting notices first published in
  42:12–42:23. Overlapping cohorts deduped by entity ID.
- **Post-close follow-up per process (proposed; outside-interval events reported separately, unscored):**
  - Horizon: the second issue published after the opportunity's close or last hearing date.
  - Basis: an extension or withdrawal filed just before close is published ≥19 days later (noon
    Wednesday cutoff → Monday issue, req 28).
  - NOIRA/fast-track/petition/periodic: close + ~4–5 weeks.
  - Proposed: close (≥60 days) + ~4–5 weeks.
  - For 42:24 opportunities this runs to about 43:05/43:06 (2026-10-19 / 11-02).
  - Polling/backfill: re-read each new issue TOC and its Errata/Withdrawn entries once per biweekly
    issue. The archive is permanent, so backfill = re-read.
  - Fast-track conversions and § 2.2-4007.06 suspensions after the horizon are reported outside
    the interval.

## Authority, access and source map

| Source ID/lineage | Agencies/processes covered | Authority/precedence evidence | Rights record/version; collection allowed? | Method/rate | Retain originals? | Third-party/public-evidence limits | Cadence/retention | Gaps |
|---|---|---|---|---|---|---|---|---|
| `va-register` / lineage `va-dlas` (Code Commission/DLAS): issue PDF `/volNN/issII/vNNiII.pdf` | all included | "The PDF version … is the official legal resource (§ 2.2-4031 C)" (home, req 1) | `va-register` 2026-10-15.1; allowed | sequential, ≥5 s, identifying UA | yes (internal) | public notices to LlamaParse/LLM OK; display = link + deadline/hearing sentence | biweekly Mondays; archive to 2008 | 43:03 PDF: 76 pages, 75 with native text, 1 blank (req 30) |
| `va-register` / `va-dlas`: `toc.aspx`, `issue.aspx?type=N` sections, `details.aspx?id=N` | same | same publisher, HTML view of the PDF | same | same | yes | same | same | Same lineage as the PDF. TOC ≠ section contents: petitions and periodic reviews are listed only inside section pages |
| `va-register-rss` / `va-dlas`: `rss.aspx` | expected-issue list | issue-level items, titles carry issue dates; no `pubDate` element | `va-register-rss` 2026-10-15.1; allowed | same | yes | — | 472 items back to 25:01 (2008-09-15) | **Same lineage** as the Register (surfaces.json note) |
| `va-register` home "Regulations Effective before Publication" | early signal for some emergency/exempt items | Registrar | same | same | yes | — | rolling | Not an issue; publication-time status is Q11 |
| `va-townhall-listings` (DPB): `/L/` forums, meetings, actions | upstream for executive agencies ("Once through the review process, the regulation is sent to the Virginia Register", req 27) | different publisher/system | **on hold**, no collection | — | no | — | — | Only plausible independent lineage; also the hearing-announcement source (Q8, Q9) |
| `va-code-reference` (`law.lis`) | statute text, VAC agency index | — | on hold | — | no | — | — | Statute citations here come from Register text (Q10) |

Active census: WA/CT/VA/TN. Rights linkage: `va-register` + `va-register-rss` @ `2026-10-15.1`.
Rate ≥5 s, sequential, identifying agent, stop on 403/429, never bypass bot protection.
**Cross-check strategy and gap detection.** Same lineage only:
- The RSS issue list must match the publication schedule (req 28) and the archive.
- Issue PDF contents must match the TOC, section pages and details pages.
- Doc. No. continuity across stages (NOIRA → proposed → final) must hold.

All of these share the `va-dlas` lineage.
**Independent-lineage cross-check: none lawful under current rights.** Town Hall is a different
system and publisher (DPB). It is the natural cross-check for executive agencies, but its `/L/`
pages are on hold pending `outreach/VA.md`. SCC and exempt agencies would need their own sources.
Every included (agency, process) row is therefore `single_lineage: true`, pending a human review
reference, and **completeness is capped at "not established"** (Q8). Lawful paid reference access:
none needed.

## Expected publications and surface tests

| Source/process | Expected units | Expectation evidence | Filters/pagination/terminal proof | Full-body cross-check | Agency/history cross-check | Missing units/reviewer decision |
|---|---|---|---|---|---|---|
| Register issues 42:12–42:24 (interval) | 13 issue PDFs (~76 pp each ≈ 990 pp); 13 TOCs; section pages (types 4, 8, 10, 11) per issue as present; one details page per action (≈ 13 × ~25 incl. finals) | RSS titles + publication schedule | No pagination. Terminal = section list in TOC | PDF ↔ TOC/sections/details | Doc. No. chain (same lineage) | none yet |
| Backward search 42:06…42:11 (+ further per stop rule) | TOCs + section pages + details pages of candidate carry-ins | stop rule above | same | same | same | Rule may not terminate inside Vol. 42 → unresolved |
| Follow-up 42:25…43:06 | TOCs + Errata/Withdrawn/section pages | follow-up rule | same | same | same | 43:05 (10-19), 43:06 (11-02) not yet published |

Manifest snapshot/hash: not started (step 3). Unknown counts, null rather than zero: petition and
periodic-review rates, hearing share, Jan–May volume, SCC request-deadline wording. Stability
re-fetch: step 7.

## Temporal ambiguity notes seen

- Comment deadlines are **date-only, no time or zone**: "Public Comment Deadline: October 21,
  2026" (reqs 7, 8). Inclusive/exclusive is unstated. Do not invent end-of-day.
- Range wording: "from September 7, 2026, to September 28, 2026" (petition, req 20); "begins
  September 21, 2026, and ends October 12, 2026" (periodic review, req 4). Inclusivity is unstated.
- Statutory relative clocks (from req 26, not computed into labels):
  - proposed comment "minimum of 60 days";
  - Governor comments within 15 days after;
  - 30-day final adoption period;
  - 21-day legislative objection response;
  - fast-track objection threshold of 10 persons;
  - § 2.2-4007.06 threshold of 25 persons.
- Fast-track effective date (Nov 5) follows its comment deadline (Oct 21). This is a negative
  fixture: an effective date is not a deadline.
- "Regulations effective before publication": filing → effective → later Register date (req 1).
  Effective and filing dates are not participation clocks.
- SCC "hearing will be held upon request". The request deadline is in the order text, and its
  exact wording was not extracted (req 6).
- Short informal windows: DBHDS draft published 09-21 with deadline 09-25 (req 5).
- Filing cutoff "noon" Wednesdays; publication Mondays.
- A different deadline on Town Hall forums is possible but not observable (on hold).

## Enumeration, labels and review (steps 4–6; not started)

Not applicable at step 2. One input for planning: the central projection (~148) is ≤150, so the
small-census rule applies. **Every consequential date and role label gets a human check.** At
~1 min per label (illustrative) that is ~150 min before mandatory cases. Together they may exceed
the 240-minute VA budget (Q12).

## Sizing and freeze

- **LlamaParse need (estimate):**
  - Pages: 13 interval issue PDFs ≈ 990 pages. Carry-in and follow-up items are read as HTML
    details pages, which have native text.
  - Sample: 75/76 PDF pages have native text. The one empty page is a layout blank, verified by
    rendering, not parsing.
  - Expected pages with content but no usable text: 0–2% = 0–20 pages.
  - × 10 credits/page = **0–200 credits** against the VA envelope of 2,000. Reserve 200 before
    dispatch. Expected actual is ~0.
- Shared envelopes unchanged: WA 2,000 / CT 2,000 / VA 2,000 / TN 4,000 / reserve 2,000.
- Format mix: issue PDF (official) + HTML details pages. Templates: NOIRA, proposed (APA, exempt,
  SCC order), fast-track, petition notice/decision, periodic-review notice, general notice.

## Questions for the reviewer

1. **NOIRA:** include each NOIRA's dated comment window (and any hearing-request offer) as an
   opportunity? (yes/no)
2. **APA-exempt agencies** (SCC, DWR, others claiming § 2.2-4002) that publish proposals with
   comment deadlines: include them? And count SCC "hearing upon request" as a hearing-request
   window? (yes/no; yes/no)
3. **Periodic-review agency notices** with dated comment periods: include as subtype
   `periodic_review`, deduped when the notice piggybacks on a NOIRA? (yes/no)
4. **§ 2.2-4007.06 final-adoption request window:** exclude as an opportunity and record finals as
   rejects? (yes/no; including it would add up to ~9.5 candidates/issue)
5. **Informal pre-NOIRA comment** on named draft regulations in General Notices (e.g. DBHDS
   12VAC35-260): include as `early_stage` when a deadline is dated? Applies symmetrically with WA
   CR-101 Q1. (yes/no)
6. **DMAS State Plan amendment comment notices** (General Notices): exclude as non-VAC/State Plan
   actions? (yes/no)
7. **Interval:** pick one.
   - (a) Sign `[2026-01-26, 2026-07-27)` America/New_York, 42:12–42:24, 26 weeks, projected
     118–182 (central 148), with the predeclared backward extension to Vol. 42 start.
   - (b) 12 weeks `[2026-05-04, 2026-07-27)`, 42:19–42:24, projected ~55–84 (shortfall ~65–94).
   - (c) All of Vol. 42 before 42:25: `[2025-08-25, 2026-07-27)`, 48 weeks, projected ~220–340.
8. **Independent lineage:** accept `single_lineage: true` for every VA process, which caps VA at
   "not established", until DPB answers `outreach/VA.md`? Or prioritise that outreach for
   Town-Hall-as-cross-check? (accept / prioritise outreach)
9. **Town Hall-only hearings and forum dates:** accept as a named coverage gap in the scope label
   ("hearings announced only on Town Hall are not covered") until Town Hall is cleared? (yes/no)
10. **Statute/VAC access:** allow read-only, non-retained lookups on `law.lis.virginia.gov` to
    verify cited sections (§§ 2.2-4002, -4007, -4007.01, -4007.06, -4007.1, -4011, -4012.1, -4017,
    -4031) and to enumerate the VAC agency index as the roster? (yes/no)
11. **Pre-publication home-page list** ("Regulations Effective before Publication … Register Date"):
    treat it as non-authoritative early signal only, so publication = issue date? (yes/no)
12. **Review budget:** with ≤150 opportunities every consequential date and role label gets a
    human check. Accept a likely overrun of the 240-minute VA budget? Or move to option 7(c),
    which takes VA above 150 and into the audit regime? (accept overrun / choose 7(c) / other)

## Request log (2026-10-15, UTC; UA `DocketClock-research/0.1 (github.com/lucas-homer/yokel)`)

Request 30 used `http://`; the server returned the PDF (final URL in the scratch log). Request 29
returned 500 and was not retried.

| # | Time (UTC) | URL | Status |
|---|---|---|---|
| 1 | 2026-10-15T16:28:28Z | `register.dls.virginia.gov/` | 200 |
| 2 | 2026-10-15T16:28:35Z | `register.dls.virginia.gov/rss.aspx` | 200 |
| 3 | 2026-10-15T16:28:52Z | `register.dls.virginia.gov/toc.aspx?voliss=43:03` | 200 |
| 4 | 2026-10-15T16:29:20Z | `register.dls.virginia.gov/issue.aspx?voliss=43:03&type=10` | 200 |
| 5 | 2026-10-15T16:29:26Z | `register.dls.virginia.gov/issue.aspx?voliss=43:03&type=8` | 200 |
| 6 | 2026-10-15T16:29:40Z | `register.dls.virginia.gov/details.aspx?id=12473` | 200 |
| 7 | 2026-10-15T16:29:47Z | `register.dls.virginia.gov/details.aspx?id=12481` | 200 |
| 8 | 2026-10-15T16:29:54Z | `register.dls.virginia.gov/details.aspx?id=12482` | 200 |
| 9 | 2026-10-15T16:30:04Z | `register.dls.virginia.gov/toc.aspx?voliss=43:04` | 200 |
| 10 | 2026-10-15T16:30:11Z | `register.dls.virginia.gov/toc.aspx?voliss=43:02` | 200 |
| 11 | 2026-10-15T16:30:18Z | `register.dls.virginia.gov/toc.aspx?voliss=43:01` | 200 |
| 12 | 2026-10-15T16:30:24Z | `register.dls.virginia.gov/toc.aspx?voliss=42:26` | 200 |
| 13 | 2026-10-15T16:30:31Z | `register.dls.virginia.gov/toc.aspx?voliss=42:25` | 200 |
| 14 | 2026-10-15T16:30:38Z | `register.dls.virginia.gov/toc.aspx?voliss=42:24` | 200 |
| 15 | 2026-10-15T16:30:44Z | `register.dls.virginia.gov/toc.aspx?voliss=42:23` | 200 |
| 16 | 2026-10-15T16:30:51Z | `register.dls.virginia.gov/toc.aspx?voliss=42:22` | 200 |
| 17 | 2026-10-15T16:30:57Z | `register.dls.virginia.gov/toc.aspx?voliss=42:21` | 200 |
| 18 | 2026-10-15T16:31:04Z | `register.dls.virginia.gov/toc.aspx?voliss=42:20` | 200 |
| 19 | 2026-10-15T16:31:32Z | `register.dls.virginia.gov/issue.aspx?voliss=42:25&type=4` | 200 |
| 20 | 2026-10-15T16:31:39Z | `register.dls.virginia.gov/issue.aspx?voliss=43:02&type=4` | 200 |
| 21 | 2026-10-15T16:31:45Z | `register.dls.virginia.gov/issue.aspx?voliss=43:02&type=10` | 200 |
| 22 | 2026-10-15T16:31:52Z | `register.dls.virginia.gov/issue.aspx?voliss=42:24&type=10` | 200 |
| 23 | 2026-10-15T16:31:58Z | `register.dls.virginia.gov/issue.aspx?voliss=42:24&type=8` | 200 |
| 24 | 2026-10-15T16:32:20Z | `register.dls.virginia.gov/details.aspx?id=12374` | 200 |
| 25 | 2026-10-15T16:32:27Z | `register.dls.virginia.gov/details.aspx?id=12507` | 200 |
| 26 | 2026-10-15T16:32:34Z | `register.dls.virginia.gov/issue.aspx?voliss=43:04&type=2` | 200 |
| 27 | 2026-10-15T16:32:40Z | `register.dls.virginia.gov/citizen_participation.shtml` | 200 |
| 28 | 2026-10-15T16:32:57Z | `register.dls.virginia.gov/issue.aspx?voliss=43:04&type=3` | 200 |
| 29 | 2026-10-15T16:34:02Z | `register.dls.virginia.gov/publicdocket.aspx?status=&type=3` | 500 |
| 30 | 2026-10-15T16:34:31Z | `register.dls.virginia.gov/vol43/iss03/v43i03.pdf` | 200 |
