# State universe: MS / v0.1-proposed (2026-10-15)

Status: **draft: proposal for owner signature. Not frozen.** Completeness: not established. Every
included process is single-lineage except a narrow MDEQ row; see "Agency cross-check" and Q8.
Owner: primary (research child draft). Human reviewer: owner. Decision date: _pending owner signature_.
Protocol/schema versions: PROTOCOL v1.1. Rights: `ms-sos-admin-search` (allowed, retain originals),
`ms-sos-reference` (allowed, no retention) and `ms-agency-rulemaking` (allowed, read-only cross-check),
all at version `2026-10-15.3`, owner decision `owner-2026-10-15c` (DECISIONS items 10–13).
Proposed scope label shown to users: "Mississippi state agency rule filings in the Secretary of
State's Administrative Bulletin: proposed rules' comment periods and oral-proceeding (hearing)
request windows, scheduled oral proceedings, and withdrawals. Temporary (emergency) rules, Medicaid
State Plan notices and agency-only announcements are not covered."
Statewide claim justified? **No.** Evidence: the only independent source covering an interval
proposal is MDEQ's own notice page (one proposal). MID's page covers a subset, and none of its
entries fall in the proposed interval. Medicaid, MSDH, MDHS and PERS publish no proposal notices
that could be found. DOR was skipped on its terms. Per DECISIONS item 11, MS is therefore
single-lineage and completeness is "not established".

Evidence basis: an attended scoping run on 2026-10-15 made **42 HTTP requests** (15 to
`www.sos.ms.gov`, 27 to five agency hosts), sequential and at least 6 s apart, with UA
`DocketClock-research/0.1 (+https://github.com/lucas-homer/yokel)`. There was no 403, no 429 and no
Cloudflare challenge. One earlier attempt failed at local TLS verification before any HTTP exchange;
it is logged. The run also reused the scout's same-day scratch copies (bulletin page, `Admin.js`,
two service responses, four forms, Medicaid homepage) without re-fetching them. Scratch bytes are in
`/tmp/ms-scope`, outside git, and are not census originals. All counts are planning estimates from
bulletin records. None is a census result. No statute host was used: DECISIONS item 6 names only WA
and VA hosts. Statute citations below are quoted from the forms or from `rights/MS.md`, unverified.

## What the bulletin service is (and isn't)

- `BulletinSearch(agency, ruleSummary, order, dir, filingType, date1, date2, dateType, page, n)`
  returns `^`-separated records ending `|<count>|0`. Each record has `~`-separated fields: agency,
  "Compilation" flag (always `False` so far; meaning unknown), proposed, final, effective and
  withdrawal dates, rule name, summary, system number (filing ID), notice-form file, EIS file and
  full-text file. Notice forms are at `ACProposed/<8-digit id>a.pdf` for every filing type.
  `filingType` 0/5/10 = All/Final/Proposed. `dateType` 0/1/2/3 = final/proposed/effective/withdrawal date.
  Note the scout's MS.md reads field 2 as "withdrawn flag"; `Admin.js` labels it "Compilation".
- **Each filing gets its own system number.** A final adoption is a new filing whose record repeats
  the original proposal's date. Proposal records are not updated when finalized: 0 of 580 proposal
  records overlap final IDs, and 2 of 580 carry a final date.
- **Structured type flags are unreliable.** The type-10 "Proposed" query misses filings that
  only the All-types query returns. Among them: "Notice of Public Hearing" filings (27810, 28031), a
  temporary rule (28650, form ticks "Temporary: Original filing … Immediately upon filing"), a
  withdrawal with no withdrawal date (28892 withdraws "System ID # 28873"), and records with
  impossible dates (28938: proposed 4/1/2026, effective 10/1/2026, but its system number places it
  around 2026-10-01). So every record outside the plain proposal/final pattern needs body
  classification.
- **Volume** (2025-01-01 → 2026-10-15, 93 weeks): **580 proposals** (6.2/wk), **573 finals**,
  **23 withdrawal-dated records** since 2024-01-01 (about 9/yr), and **8 other-class** records. There were 62
  distinct proposing agencies and 64 distinct filers of any type. The bulletin's own agency picklist
  (`agenciesDelim`) has 144 entries across 40 Code titles.
- **Image-only forms: 13 of 13 sampled** (4 by the scout, 9 here; proposals, a final, a
  withdrawal, a temporary rule, and a pre-2026 proposal). Each is one page, an image XObject with no
  fonts, from a Fujitsu (PFU) or PaperCut scanner. Native text is unusable for every notice form.
- **FILED stamp vs record date: all 8 forms read here that have a bulletin record match** (the
  scout found 2 more). The ninth form read, 27884, has no record. Each form also carries the system number handwritten under the stamp
  ("Accepted for filing by 28676 …"). That is a second identity alias.

## Agency and process universe

**Roster (dated 2026-10-15).** The universe is defined by the filing obligation, not by a list. SOS
is "the official registrar for the rules of all state agencies and the publisher of the Mississippi
Administrative Bulletin" (`Admin.js`). The roster used for enumeration is every filer appearing in
the interval, backward-search and follow-up records. It is checked against the bulletin picklist
(144 entries; scout r05, `agenciesDelim`). Entries are agency names keyed to Code titles. Each filer
is classified by the rules below.
**Observed in the proposed interval:** 109 proposals from 32 agencies. Top filers: Division of
Medicaid 24, Education 12, Community College Board 12, Health (MSDH) 9, Post-Secondary Financial
Assistance Board 5, Development Authority 5.

| Agency ID/name | Roster authority, version, evidence locator | Process/stage | Included? | Reason/authority | Authoritative publication(s) | Gaps / single_lineage + human ref |
|---|---|---|---|---|---|---|
| All filers in the Administrative Bulletin | bulletin picklist (144 entries) ∪ interval/backward/follow-up records | **Proposed rule (SOS APA Form 001, "Proposed Action on Rules")**: written-comment window | **Yes** | Form boilerplate: "At any time within the twenty-five (25) day public comment period, written submissions … may be submitted to the filing agency" (28676, 28657, 28651, 28763 forms) | Notice form `ACProposed/<id>a.pdf` (image-only) + bulletin record (date, agency, rule) | single_lineage except the MDEQ row (Q8) |
| same | same | **Oral-proceeding request window** (form box "Presently, an oral proceeding is not scheduled") | **Yes, as a hearing-request opportunity** with its condition kept (Q5) | "an oral proceeding must be held if a written request … is submitted by a political subdivision, an agency or ten (10) or more persons … within twenty (20) days after the filing of this notice" | same | Checkbox is decisive. MSDH 28651 ticks **neither** box, so it is a review case |
| same | same | **Scheduled oral proceeding** (box "An oral proceeding is scheduled … Date/Time/Place") | **Yes, hearing opportunity** | MDEQ 28720: "August 4, 2026 Time: 2:00 p.m., Place: … 515 E. Amite St." (60 days after filing). This variant form **omits the 20/25-day boilerplate entirely** | same | Comment window on such variants: Q4 |
| same | same | **Separate "Notice of Public Hearing" filings** (other-class records, e.g. 27810 Cosmetology 2025-01-06, 28031 Pharmacy 2025-05-12) | **Yes, hearing opportunity** linked to its proposal by rule name/agency (Q6) | Title text "Notice of Public Hearing-Title 30 …". Bodies not yet inspected | same | ~2/yr in sample. Linkage is a review case |
| same | same | **Withdrawal** (W-type records, final form with "Action taken: Withdrawn", or other-class forms like 28892) | **Yes, as updates.** Target = the withdrawn system number | "Withdrawal of system number 28321" (28365 rule field). 28892 withdraws 28873 because "there was an internal conflict with the date chosen for the public hearing" | form + record | Targets can be 2.5 years old (Pharmacy 27786/7 withdraw proposals from 2022). Bulletin withdrawal date is missing on some (28892) |
| same | same | **Final action, adopted** (with/without changes, by reference, repeal adopted) | **No** as an opportunity or a scored update. Closure evidence for follow-up only (Q7) | Adoption isn't on the plan's lifecycle list (same as WA CR-103P) | form + record | 573 finals in 93 weeks; final − proposed lag p50 36 d, p90 104 d, p95 175 d, max 1,404 d |
| same | same | **Temporary (emergency) rules**: "Temporary Rules: Original filing / Renewal" | **No** (labelled exclusion, inspected as an exclusion stratum) | No participation opportunity on the form (28650) | form | Hidden among other-class records and 62 finals with final = proposed date; body check required |
| Division of Medicaid | picklist | **State Plan / waiver public notices** (outside the bulletin) | **No** (labelled exclusion, as VA Q6) | Not APA rule filings | — | — |
| Agencies' own announcements never filed with SOS (e.g. MID's "Part 101 Minimum Standards Certification" proposal, comments "until 4:00 pm, Monday, October 26, 2026", with no matching bulletin record through 2026-10-15) | agency pages | any | **Outside the declared universe**; recorded as a coverage lead | The bulletin is the authoritative publication | — | Possibly the missing 28935 (PDF 404). Reviewer note |
| Local government, legislature, courts | — | — | **No** | Not state-agency rule filings | — | — |

Exceptions are checked agency by agency in the form body, not from structured type flags (see above).
**Explicit exclusions:** permits, guidance, legislation, local government, who-is-affected analysis,
temporary rules, Medicaid State Plan notices, economic impact statements, final adoptions as
opportunities, public comments and commenter data.
**Narrow scope boundary:** opportunities whose authoritative publication is a filing in the SOS
Administrative Bulletin. Agency-only notices are a known coverage gap, not misses.
**Early-stage policy:** MS has no pre-proposal notice stage in the bulletin. None is included.

## Interval and cohorts

- **Proposed civil half-open interval (Option A):** `[2026-05-18, 2026-08-17)`, 13 complete
  Monday-start weeks, zone `America/Chicago`. The zone is for accounting only; it doesn't decide any
  legal clock. The bulletin posts continuously, so the complete publication cycle is the civil week.
  - *Selection rule, stated before any adapter exists:* take the most recent 13 complete weeks
    whose scored follow-up horizon (below: filing + 25 d + 30 d = 55 d) ends on or before the last
    complete week before freeze (2026-10-12). The last interval filing is 2026-08-16, and
    2026-08-16 + 55 d = 2026-10-10.
  - *Disclosure:* I had seen weekly volume before writing this rule. It happens to include the
    late-May surge (29 proposals in the week of 2026-05-25, mostly Medicaid).
  - Weekly proposals: 12, 29, 14, 11, 4, 8, 5, 6, 1, 7, 3, 5, 4.
- **Option B (alternative, Q1):** `[2026-01-12, 2026-04-13)`, under the rule "most recent 13 weeks
  whose full lifecycle horizon (filing + 180 d ≈ p95 final lag) is observable". 66 proposals
  from 24 agencies (Education 20). Weekly: 7, 13, 2, 3, 3, 4, 3, 2, 6, 8, 7, 8, 0.
- **Publication-time authority:** the FILED stamp date on the form, read visually (date only, no
  time). The bulletin record date is an index of it, and any mismatch is a review case. The online
  posting time of historical records is not observable: posting lag is **unmeasured**, never zero.
  Not a publication time: DocuSign timestamps ("5/21/2026 | 2:19 PM CDT" on 28651), Submit Date,
  and signature dates.
  **System numbers are not strictly date-ordered.** 53 records sit more than 3 days earlier than a
  lower-numbered record. The interval's records span IDs 28645–28905: 229 records dated in the
  interval, 261 IDs in the span. The 32 interleaved IDs are boundary review cases, retained pending
  decision.
- **Projected opportunities, Option A (arithmetic):**
  - *New-notice cohort.* 109 proposals × 2 (comment window + either hearing-request window or
    scheduled hearing) = **218** central. Low: 20% yield only one stated opportunity (variant forms
    without boilerplate, or misfiled temporary rules), so 87 × 2 + 22 = **196**. High: add 0–2
    separate hearing-notice filings, **≈220**.
  - *Carry-in cohort.* Proposals filed 2026-04-23 → 05-17 have comment windows still running at start
    (31). Those filed 2026-04-28 → 05-17 also have running request windows (25). Add 0–5 scheduled
    hearings on older proposals: **≈50–60**.
  - **Total ≈ 246–285, central ≈ 274.** That is above 149, and above 150, so MS falls in the
    random-audit regime.
  - Independence is weak. Every proposal uses one SOS form, with at least three agency variants seen
    (standard; MDEQ hearing variant without boilerplate; MSDH variant with a Smartsheet comment link).
    Medicaid filed 24 of 109.
- **Projected, Option B:** 66 × 2 = 132 new (low ≈120). Carry-in: 13 comment + 9 request windows
  ≈ 22. **Total ≈ 142–154.** The new-notice cohort alone misses 149.
- **Low-volume shortfall:** none projected for A. If step-3 accounting projects fewer than 149
  before enumeration, add whole weeks backward to a maximum of 17 weeks (start 2026-04-20; that
  window held 143 proposals). Budget: the MS credit allocation below.
- **New-notice rule:** FILED stamp date inside the interval.
- **Carry-in rule and backward search boundary:**
  - *Comment and request windows.* An opportunity filed before 2026-05-18 counts when its relative
    clock (25 d comment / 20 d request, from filing) reaches 2026-05-18 or later. Inspect every
    proposal form with record date in **[2026-04-13, 2026-05-18)**: 39 forms, being the 25-day reach
    plus a 10-day margin for stamp/record mismatch.
  - *Scheduled hearings.* Hearing dates are not bounded by the 25-day period (MDEQ: 60 d after
    filing), and no statutory maximum has been verified. Inspect all proposal and other-class forms
    filed **[2026-02-16, 2026-04-13)** (13 weeks back from start; about 46 forms) for oral-proceeding dates
    on or after start. Extend backward in 13-week steps until a full step yields none (same rule as
    CT).
  - *Archive reach.* The bulletin is not the limit: withdrawal records reference 2022 proposals,
    and the 2024-01 withdrawal-date query returned 23 records.
- **Older-proceeding updates and reopenings:** withdrawals in the interval may target proposals of
  any age (lag up to 903 d). Resolve each by system number through the bulletin and its form.
  Re-proposals (e.g. MDEQ withdraw-and-refile) are **new** proposals with new system numbers, so
  they are separately identified rounds, linked to the prior one by rule name/agency for review.
  43 finals in the interval close older proposals. They are closure evidence only (Q7).
- **Other interval updates:** withdrawals (1 W-type record in A: 28656, withdrawing a 2025-12-31
  proposal; others may hide in other-class records) and hearing notices on interval proposals.
  **The expected update count is tiny (≈1–4), so update recall will likely be unmeasured.**
  Cohorts are deduped by entity ID.
- **Post-close follow-up per process** (proposed; outside-interval events reported separately,
  unscored):
  - *Comment window and request window:* through filing + 25 d + 30 d. Basis: hearing notices and
    withdrawals cluster soon after filing (28892 came 16 d after 28873); median final lag is 36 d.
  - *Scheduled hearing:* through hearing date + 30 d, for reschedule/cancel/withdraw filings. Hearings
    after 2026-09-12 run past the freeze; report them as pending.
  - *Closure (finals):* through filing + 180 d (p95 175 d). Reported outside the interval. 22 of 109
    Option-A proposals have no matching final yet (87 matched by agency + rule name).
  - *Late withdrawals* (up to ~2.5 years) are outside the horizon.
  - *Polling/backfill:* re-query the service by each date type over the horizon, plus an ID-sequence
    sweep. The service retains history, so backfill is a re-query. Never inherit the federal 7-day
    horizon.

## How deadlines are labelled (proposal; Q2–Q4)

Each MS opportunity is stated on the form, so it counts. Its *date* is relative:

| Role | Literal wording | Anchor | Proposed label |
|---|---|---|---|
| Hearing-request window | "within twenty (20) days after the filing of this notice"; request "should be submitted to the agency contact person" | Filing, stated; evidence is the FILED stamp locator | `relative`: anchor = filing date (stamp, date precision), rule "20 days after", cutoff and received/submitted condition **unknown**. Condition: no oral proceeding scheduled |
| Comment window | "At any time within the twenty-five (25) day public comment period" | **Not stated** (implied filing) | `relative`: anchor wording unstated, length 25 d, cutoff unknown |
| Scheduled hearing | Form "Date / Time / Place" | — | Literal local date/time, zone wording none, IANA zone null unless reviewed |

**Recommendation:** do not assert a computed date (stamp + 20/25 d) as the close. Keep it only as a
derived annotation, with the stamp and boilerplate locators, for Phase 2 temporal policy. Evidence
that computation would be wrong:
- MID's own notices state closes **25, 27 and 28 days** after filing: 28339 filed 2025-10-30 →
  "until 4:00 p.m., Monday, November 24, 2025"; 28491 filed 2026-02-10 → "through 4:00 p.m.,
  Monday March 9, 2026"; 28937 filed 2026-10-01 → "until 4:00 pm, Thursday, October 29, 2026".
- MDEQ's notice for 28720 (filed 2026-06-05) states "written comments should be delivered … by the
  end of business on August 4, 2026", which is **60 days** after filing.

So the 25-day figure is a statutory minimum, not the close. Where an independent agency notice
states a close, record it as separate-lineage evidence and mark the role `conflicting` pending human
precedence review (Q3). Never silently prefer one.

## Authority, access and source map

| Source ID/lineage | Agencies/processes covered | Authority/precedence evidence | Rights record/version; collection allowed? | Method/rate | Retain originals? | Third-party/public-evidence limits | Cadence/retention | Gaps |
|---|---|---|---|---|---|---|---|---|
| L1 `ms-sos` / BulletinSearch service records | all included rows (index: date, agency, rule, system number, file names) | SOS official registrar/publisher (`Admin.js`) | `ms-sos-admin-search` @2026-10-15.3, **allowed** | POST, one request ≥5 s; Cloudflare fronts the host: stop on any challenge/403/429 | yes (internal) | public notices to LlamaParse/LLM OK; display = link + deadline sentence | continuous; history ≥2022 | Type flags and dates unreliable (above). No deadline fields. 27884 absent from every query |
| L1 / notice forms `ACProposed/<id>a.pdf` | all included rows (opportunity evidence) | the filed form, stamped | same, **allowed** | GET | yes | same | permanent so far | **Image-only (13/13)**. 28935 → 404 |
| L1 / full text `<id>b.pdf`, EIS | only where the form refers to them | — | same | GET | yes | same | — | Not needed for dates in any sample |
| L2 `ms-mdeq` / MDEQ "Proposed Regulation Changes" + agency public-notice PDFs (`wp-content/uploads/…`) | MDEQ proposals and hearings | agency-authored notice; MDEQ disclaimer: website "not a legal substitute for the official administrative files" | `ms-agency-rulemaking` @2026-10-15.3, **allowed** (terms not restrictive) | GET | yes (internal) | same | **Rolling: shows the current item only.** Stale: the 2026-08-19 proposal 28873 and its withdrawal are absent | History not enumerable from the page; a `wp-sitemap.xml` exists (untested) |
| L3 `ms-mid` / MID "Regulations → Proposed Regulations" + `…/YYYY/MM/YYYYMMProposedreg.pdf` | MID Commissioner proposals (Title 19 Parts 1, 5, 101) | agency notice; disclaimer: "informal service that is not official in nature" | same, **allowed** (accuracy disclaimer only) | GET | yes | same | **Keeps older entries** back to 2025-07 | Omits State Fire Marshal (Part 7) and 2026-08 proposals 28862/28868; 4–5 entries vs ~14 MID proposals since 2025 |
| `ms-sos-reference` (robots, disclaimer) | rights evidence | — | allowed, **no retention** | GET | no | — | — | — |

Active census: WA/CT/VA/TN, plus MS as the ADR 0013 Amendment 1 backup hard candidate. Rights
linkage: surfaces above @`2026-10-15.3`. Rate ≥5 s, sequential, identifying agent; stop on
403/429/challenge; never bypass bot protection. The 15 SOS responses carried `server: cloudflare`;
none was challenged. **Scheduled polling still waits on the SOS courtesy note** (`outreach/MS.md`,
DECISIONS item 10).
**Same-lineage completeness check:** the system-number sequence (below).
**Independent lineage:** MDEQ (L2) for MDEQ rows only; MID (L3) has no interval coverage. Lawful
paid reference access: none needed.

### Agency cross-check (DECISIONS item 11; ~5 agencies sampled)

| Agency (interval proposals, A) | Host / terms check | What exists | Verdict |
|---|---|---|---|
| Division of Medicaid (24) | `medicaid.ms.gov`. robots 404 (scout). No terms page found: script-rendered app | Homepage links rules only to SOS. `/sitemap.xml` 404; `/public-notices/` 404 (app shell) | **No cross-check**: `single_lineage` |
| MSDH, Health (9) | `msdh.ms.gov`. robots allows `/page/`, disallows `/documents/`, `/policy/`. No terms page found | Regulation, Legislation and Board of Health pages: no proposal notices. The Board "approves all Rules" at quarterly meetings (open meetings, excluded) | **No cross-check**: `single_lineage` |
| MDEQ (1: 28720) | `www.mdeq.ms.gov`. robots allows; disclaimer is accuracy-only (**not restrictive**) | Agency notice PDF (native text, 2 pp) **matches** the form's hearing ("August 4, 2026, at 2:00 P.M.") and **adds** a dated comment close the form lacks | **Cross-check available** for 28720. The page is rolling and stale, so future rows need a capture at filing time |
| DOR, Revenue (4) | `www.dor.ms.gov`. Policy: "The use of content, reports, images and logos on the DOR site by any other website is prohibited by law. The use of the reports and data without the consent of DOR is a violation of Mississippi copyright and other proprietary rights." | Not fetched beyond robots/home/policy | **Skipped: restrictive terms** (recorded per DECISIONS item 5) |
| MDHS, Human Services (2) | `www.mdhs.ms.gov`. robots open. No terms page ("Privacy Policy" links to non-discrimination statements) | Public Notices category is sporadic. One 2024-08-20 "ORAL PROCEEDING ANNOUNCEMENT". Nothing for interval proposals 28646 / 28803 | **No cross-check** for the interval: `single_lineage` |
| MID, Insurance (3) | `www.mid.ms.gov`. robots open; disclaimer accuracy-only (**not restrictive**) | Proposed-regulations list with explicit closes and times; history kept | **Partial.** Covers no interval proposal (28711 is Part 7; 28862/28868 not listed), so `single_lineage` for A. Useful temporal evidence |
| PERS (0 in A; 8 in 2026) | `www.pers.ms.gov`. disclaimer accuracy-only | Board Regulations lists adopted rules only | **No cross-check** |
| Not sampled: Education `mdek12.org`, Community College Board `mccb.edu`, Wildlife `mdwfp.com`, Development Authority `mississippi.org` | **outside** the `ms-agency-rulemaking` host pattern (`*.ms.gov`) | — | Would need a new rights decision (Q8) |

**Per-process conclusion:**
- Comment window, request window and scheduled hearing: **cross-check available for MDEQ only.**
  For the other agencies, `single_lineage: true` (human ref pending Q8).
- Hearing-notice filings, withdrawals and closure: `single_lineage: true` everywhere. MDEQ's page
  did not show the 28892 withdrawal.
- **Completeness verdict ceiling: not established.**

## Expected publications and surface tests

| Source/process | Expected units | Expectation evidence | Filters/pagination/terminal proof | Full-body cross-check | Agency/history cross-check | Missing units/reviewer decision |
|---|---|---|---|---|---|---|
| Bulletin records, backward + interval + follow-up (filing dates 2026-02-16 → 2026-10-12) | **System numbers 28497–28951** (455 IDs; 454 returned by today's date-type queries) | ID sequence | Query each date type (proposed/final/withdrawal/effective) with `filingType` 0, in ≤13-week slices. Terminal proof per slice: the `\|N\|0` count equals parsed rows and N < `numberToDisplay`. **Then the union must cover every integer ID** | each record vs its form (stamp, handwritten number, form section ticked) | MDEQ L2 for MDEQ rows | Each unreturned ID gets a direct form GET. Result recorded: PDF exists = search omission; 404 = gap, human review |
| Notice forms | one per ID above (~455, one page each) | 13/13 single-page sample | GET per ID | — | — | none yet |
| MDEQ / MID notices | per agency row in range | agency page lists | page snapshot + PDF per listed notice | vs SOS form | — | rolling pages: capture at a defined time, record staleness |

**ID gap accounting (evidence for the rule).** Today's queries over 2025-01-01 → 2026-10-15 cover
IDs 27805–28964 (1,160 IDs):
- Type-10 proposal + final + withdrawal queries returned 1,150. Plus all-types proposed-date and
  effective-date queries: **1,158 of 1,160**.
- Of the scout's 4 unexplained IDs, 3 are now explained: 28892 is a withdrawal with no withdrawal
  date; 28899 is a Cosmetology filing with proposed = effective, likely temporary; 28938 is the MID
  record with inconsistent dates.
- **Two remain.** **27884** has a PDF (Community College Board proposal, FILED 2025-02-26) but
  **no record in any query**. That is a measured search-surface omission. **28935** returns 404:
  unknown, review.
- The census treats each such ID as a manifest entry with its probe evidence. Zero is never
  assumed.

Unknown counts (null, not zero): share of variant forms, scheduled-hearing share (1 of the 5 proposal
forms read here; the scout's 4 were not tallied), other-class bodies in range, full-text page counts.
Manifest snapshot/hash: not started (step 3). Stability re-fetch: step 7.

## Temporal and visual notes for the step-4/5 log

- Relative clocks anchored on a hand-applied stamp. The comment period's anchor is not stated.
- Agency-stated closes are later than stamp + 25 d (above), and have times-of-day with no zone
  wording ("4:00 pm", "end of business").
- **Decisive visual marks:** the oral-proceeding checkbox, typed "X" vs ticked box, and **neither
  box ticked** (28651); the Temporary/Proposed/Final section ticked; "Withdrawn" in the Final
  section; the handwritten system number.
- **Negative fixtures:** Submit Date, DocuSign envelope and signature timestamps, "Proposed final
  effective date: AUG 01 2026" (28676), and effective dates on finals.
- An extra comment channel: "Written submissions … may be submitted via the following link:
  https://app.smartsheet.com/…" (28651).

## Enumeration, labels and review (steps 4–6; not started)

Planning inputs only:
- **A projects ≈274 opportunities (>150), so MS is in the random-audit regime.**
- **Review-budget risk.** If every proposal form's checkbox counts as a mandatory "decisive visual
  mark" review, Option A needs ~140 forms × ~1 min ≈ 140 min. Add boundary IDs (32 × 0.5 ≈ 16),
  ID gaps and other-class bodies (~6 × 3 ≈ 18) and agency conflicts (~2 × 3): **≈180 min mandatory
  before any random audit.** That is against 240 min if MS gets the standard 4 h (Q12).
- Option B roughly halves the form count (≈80 forms → ≈110 min mandatory).
- Both passes must inspect rendered images for every form (text layer `none`).

## Sizing and freeze

- **LlamaParse (MS allocation ≤1,430 credits from the 2,000 reserve, DECISIONS item 12).**
  Every form is one image-only page, so 10 credits per form.

  | Tier | Option A pages | A credits | Option B pages | B credits |
  |---|---|---|---|---|
  | 1. Deadline-bearing: interval proposals + carry-in proposals (strict 25-d reach) + other-class/withdrawal forms | 109 + 31 + ~3 = **143** | **≈1,430** | 66 + 13 + ~2 = 81 | ≈810 |
  | 2. Finals in interval + follow-up finals | 119 + 23 = 142 | 1,420 | 64 + 29 = 93 | 930 |
  | 3. Backward-search forms + margin forms | ~46 + 8 | 540 | ~47 | 470 |
  | **Full coverage** | ~331 | **≈3,310** | ~221 | ≈2,210 |

  - The owner's "full coverage" figure (1,430) assumed ~63 proposals + ~80 finals at 4.8/wk.
    Measured 13-week windows hold 55–125 proposals, so **full coverage does not fit for either
    option.**
  - Recommendation (Q9): fund Tier 1 only. Finals and backward forms get rendered-image inspection
    only; they carry no deadlines, and final dates are in the record.
  - Tier 1 for A uses the whole 1,430 with **no retry margin**. Ask the primary to hold ~150 of the
    remaining 570 reserve for retries.
  - Ongoing: ~6 proposals/wk ≈ 60 credits/wk for proposals alone (the scout's 110/wk included finals).
- Shared envelopes: WA 2,000 / CT 2,000 / VA 2,000 / TN 4,000 / reserve 2,000 (MS draws from the reserve).
- Format mix: one-page scanned SOS Form 001 per filing (proposal/final/temporary/withdrawal all on
  the same form). Native-text agency notices for MDEQ/MID only.
- Development/holdout split, live interval, release rule: not set at step 2.

## Questions for the reviewer

1. **Interval:** sign Option A `[2026-05-18, 2026-08-17)` America/Chicago (13 weeks, ~246–285
   projected, most recent with observable scored follow-up)? Or Option B `[2026-01-12, 2026-04-13)`
   (~142–154, full lifecycle observable, cheaper)? Either comes with the 17-week maximum
   backward-extension rule. **Recommend A.** (A / B)
2. **Deadline labels:** label comment and request closes as `relative` (anchor = FILED stamp,
   date precision; comment anchor wording "unstated"), keeping stamp + N days only as a derived,
   non-asserted annotation? Alternatives: assert computed dates, or mark them `unknown`.
   **Recommend relative.** (relative / computed / unknown)
3. **Agency-stated closes** (MDEQ, MID) that differ from the form's 25-day minimum: record them as
   separate-lineage evidence and mark the role `conflicting` pending human precedence review, rather
   than auto-preferring the agency date? **Recommend yes.** (yes / agency date controls)
4. **Variant forms without the 20/25-day boilerplate** (e.g. MDEQ with a scheduled hearing): count a
   comment window only where some source states one (here, MDEQ's notice), never from statute alone
   (consistent with CT Q1)? **Recommend yes.** (yes/no)
5. **Hearing-request window:** count as its own opportunity, conditional on "not scheduled", with
   forms ticking neither box as mandatory review cases (condition retained)? **Recommend yes.** (yes/no)
6. **Other-class filings:** count separate "Notice of Public Hearing" filings as hearing
   opportunities linked to their proposal, and exclude temporary rules as a labelled, inspected
   exclusion? **Recommend yes, yes.** (yes/no each)
7. **Finals:** treat adopted finals as closure evidence only (unscored, like WA CR-103P), but count a
   final or other form marked "Withdrawn" as a withdrawal update? **Recommend yes.** (yes/no)
8. **Cross-check outcome:**
   a. Accept `single_lineage: true` for all rows except MDEQ, with completeness capped at "not
      established" (DECISIONS item 11)? (yes/no)
   b. Open a rights check for the top filers outside the `*.ms.gov` pattern (Education
      `mdek12.org`, Community College Board `mccb.edu`)? **Recommend a = yes; b = no for Phase 1**
      (Medicaid/MSDH show agencies here largely defer to SOS). (yes/no)
9. **Credits:** fund Tier 1 only (≈1,430 for A), with finals and backward forms inspected as
   images only? And ask the primary to hold ~150 reserve credits for retries? Full coverage would
   need ≈3,310 (A) or ≈2,210 (B), exceeding the 2,000 reserve. **Recommend Tier 1 + 150 hold.**
   (Tier 1 / Tier 1 + hold / switch to B and fund Tiers 1–2 ≈1,740)
10. **Carry-in boundary and follow-up:**
    a. Sign the 25-day + 10-day-margin carry-in window and the 13-week stepped backward search for
       scheduled hearings? (yes/no)
    b. Sign the per-process follow-up horizons, with closure (+180 d) and late withdrawals reported
       outside the interval, unscored? (yes/no)
11. **ID-sequence accounting:** require every integer system number in range to resolve to a record
    or a direct form probe, treating "PDF but no record" (27884) as a search-surface omission and a
    404 (28935) as a reviewed gap? **Recommend yes.** (yes/no)
12. **Review budget and visual marks:** give MS 240 minutes. Treat only *disputed or ambiguous*
    checkbox/stamp marks as mandatory reviews; clear, agreed marks go to the scan stratum (all
    up to 20). **Recommend yes.** If every mark must be reviewed, choose Option B. (yes / all marks
    mandatory)
13. **Statute lookup:** allow a read-only, non-retained lookup of Miss. Code Ann. § 25-43-3.104 (and
    any maximum-interval rule for hearings or adoption) on an official host to be named? Otherwise
    citations stay "per form text". (yes/no)
14. **Publication time:** accept the FILED stamp date as the publication-time proxy, with online
    posting lag recorded as unmeasured for the historical census? **Recommend yes.** (yes/no)

## Request log (2026-10-15, UTC; UA `DocketClock-research/0.1 (+https://github.com/lucas-homer/yokel)`)

Service POST bodies used `tmpAgency:""`, `tmpRuleSum:""`, `tmpOrder:"FilingID"`, ascending, page 0.
Only the varying parameters are shown. `—` = TLS verification failed locally before any HTTP
exchange.

| # | Time (UTC) | Method | URL / parameters | Status, bytes |
|---|---|---|---|---|
| — | 18:54:21Z | POST | `sos.ms.gov/adminsearch/AdminSearchService.asmx/BulletinSearch` (Python client; local CA error) | no exchange |
| q01 | 18:54:33Z | POST | BulletinSearch: type 10 (Proposed), proposed date 01/01/2025–10/15/2026, n 700 | 200 JSON 217,223 (580 rows) |
| q02 | 18:54:56Z | POST | BulletinSearch: type 0, final date 01/01/2025–10/15/2026, n 900 | 200 JSON 221,773 (573) |
| q03 | 18:55:06Z | POST | BulletinSearch: type 0, withdrawal date 01/01/2024–10/15/2026, n 900 | 200 JSON 8,436 (23) |
| q04 | 18:55:33Z | POST | BulletinSearch: type 0, effective date 01/01/2025–12/31/2027, n 900 | 200 JSON 229,727 (591) |
| q05 | 18:55:48Z | POST | BulletinSearch: type 0, proposed date 01/01/2025–10/15/2026, n 1500 | 200 JSON 429,587 (1,131) |
| p01 | 18:57:32Z | GET | `sos.ms.gov/adminsearch/ACProposed/00028650a.pdf` | 200 PDF 373,219 |
| p02 | 18:57:39Z | GET | `…/ACProposed/00028892a.pdf` | 200 PDF 404,102 |
| p03 | 18:57:45Z | GET | `…/ACProposed/00028935a.pdf` | **404** text/html 1,245 |
| p04 | 18:57:51Z | GET | `…/ACProposed/00027884a.pdf` | 200 PDF 380,529 |
| p05 | 18:57:58Z | GET | `…/ACProposed/00028656a.pdf` | 200 PDF 375,105 |
| p06 | 18:58:05Z | GET | `…/ACProposed/00028763a.pdf` | 200 PDF 374,603 |
| p07 | 18:58:11Z | GET | `…/ACProposed/00028676a.pdf` | 200 PDF 367,663 |
| p08 | 18:58:18Z | GET | `…/ACProposed/00028657a.pdf` | 200 PDF 360,802 |
| p09 | 18:58:25Z | GET | `…/ACProposed/00028720a.pdf` | 200 PDF 416,606 |
| p10 | 18:58:31Z | GET | `…/ACProposed/00028651a.pdf` | 200 PDF 358,305 |
| a01 | 18:59:44Z | GET | `medicaid.ms.gov/sitemap.xml` | 404 |
| a02 | 18:59:50Z | GET | `medicaid.ms.gov/public-notices/` | 404 (app shell 278,716) |
| a03 | 18:59:59Z | GET | `msdh.ms.gov/robots.txt` | 200 text 1,284 |
| a04 | 19:00:05Z | GET | `msdh.ms.gov/` | 200 HTML 40,646 |
| a05 | 19:00:14Z | GET | `msdh.ms.gov/page/30.html` | 200 HTML 37,673 |
| a06 | 19:00:20Z | GET | `msdh.ms.gov/page/30,0,216.html` | 200 HTML 31,505 |
| a07 | 19:00:27Z | GET | `msdh.ms.gov/page/19,0,124.html` | 200 HTML 36,268 |
| a08 | 19:00:34Z | GET | `www.mdeq.ms.gov/robots.txt` | 200 text 208 |
| a09 | 19:00:41Z | GET | `www.mdeq.ms.gov/` | 200 HTML 68,655 |
| a10 | 19:00:48Z | GET | `www.mdeq.ms.gov/disclaimer/` | 200 HTML 49,645 |
| a11 | 19:00:54Z | GET | `www.mdeq.ms.gov/about-mdeq/regulations/` | 200 HTML 52,579 |
| a12 | 19:01:02Z | GET | `www.mdeq.ms.gov/wp-content/uploads/2026/06/Public-Notice-Regs-Pt.-7-Ch.-1-2026-FINAL.pdf` | 200 PDF 116,198 |
| a13 | 19:01:15Z | GET | `www.dor.ms.gov/robots.txt` | 200 text 2,027 |
| a14 | 19:01:22Z | GET | `www.dor.ms.gov/` | 200 HTML 268,591 |
| a15 | 19:01:29Z | GET | `www.dor.ms.gov/internet-security-policy` | 200 HTML 141,575 (restrictive; DOR stopped here) |
| a16 | 19:01:41Z | GET | `www.mdhs.ms.gov/robots.txt` | 200 text 173 |
| a17 | 19:01:48Z | GET | `www.mdhs.ms.gov/` | 200 HTML 156,103 |
| a18 | 19:01:55Z | GET | `www.mdhs.ms.gov/publicnotice/` | 200 HTML 119,311 |
| a19 | 19:02:02Z | GET | `www.mdhs.ms.gov/eccd/rules-regulations/` | 200 HTML 135,931 |
| a20 | 19:02:09Z | GET | `www.mid.ms.gov/robots.txt` | 200 text 179 |
| a21 | 19:02:25Z | GET | `www.mid.ms.gov/` | 200 HTML 124,843 |
| a22 | 19:02:32Z | GET | `www.mid.ms.gov/mississippi-insurance-department/mississippi-insurance-department-website-disclaimer/` | 200 HTML 105,041 |
| a23 | 19:02:51Z | GET | `www.mid.ms.gov/mississippi-insurance-department/legal/regulations/` | 200 HTML 142,103 |
| a24 | 19:03:14Z | GET | `www.pers.ms.gov/robots.txt` | 200 text 2,027 |
| a25 | 19:03:20Z | GET | `www.pers.ms.gov/` | 200 HTML 61,554 |
| a26 | 19:03:27Z | GET | `www.pers.ms.gov/disclaimer` | 200 HTML 37,387 |
| a27 | 19:03:36Z | GET | `www.pers.ms.gov/board-regulations` | 200 HTML 94,888 |

Totals: 42 HTTP exchanges (SOS 15, agencies 27) plus one pre-exchange TLS failure. No 403/429.
`server: cloudflare` on all 15 SOS responses; no challenge page or `cf-mitigated` header. Medicaid's
robots.txt (404) and homepage come from the scout's same-day log (r13–r14), not re-fetched.
Image-only status was checked from PDF object structure (one image XObject, no `/Font`). All nine
forms here were read visually from rendered pages. MDEQ notice text came from macOS PDFKit (native
text, 2 pages).
