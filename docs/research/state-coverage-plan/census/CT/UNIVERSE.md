# State universe: CT / v0.1-proposed (2026-10-15)

Status: **draft: proposal for owner signature. Not frozen.** Completeness: not established (no
independent lineage yet; see "Source map").
Owner: primary (research child draft). Human reviewer: owner. Decision date: _pending owner signature_.
Protocol/schema versions: PROTOCOL v1.1; rights `ct-rendered` / `ct-json` / `ct-policy-reference` /
`ct-law-journal` at version `2026-10-15.1` (owner decision `owner-2026-10-15`).
Proposed scope label shown to users: "Connecticut state agencies' regulation notices posted on the
eRegulations System (CGS § 4-168). Agency-only, Law Journal-only and operational-policy notices are
not covered."
Statewide claim justified? **No.** Evidence: every included process is single-lineage under current
rights (Q5/Q6), and lifecycle events below the notice level sit on held JSON routes (Q3).

Evidence basis: an attended scoping run on 2026-10-15 made 18 requests (log at the end). It covered
rendered/server HTML pages, three server-rendered notice-search result pages and eight sampled
notice-of-intent PDFs. Nothing was stored in git; scratch bytes stayed in a temp directory outside
the repo and are not census originals. All counts below are planning estimates, not census results.

## Agency and process universe

Roster (dated 2026-10-15): the universe is defined by the **posting obligation**, not by a list.
CGS § 4-168(a) requires every agency adopting a regulation to post its notice of intent on the
eRegulations System. The Secretary of the State's "Regulation-Making in Connecticut" page says so
explicitly ("The notice must be posted on the eRegulations System": `Information/GetContent?id=RegulationMaking`,
req 6). The search form's agency picklist is filled by JSON and was not called. Enumeration route:
take the union of agencies in the server-rendered notice search over the history boundary, in yearly
slices. **Observed 2023-10-16 → 2026-10-12:** 24 distinct posting agencies across 199 notices. DCP 53,
DEEP 26, DPH 22, Board of Labor Relations 15, SOTS 14, DOL 14, SEEC 7, DSS 7, SDE 5, POST Council 5,
Insurance 5, DAS 4, PURA 3, DOT 3. Another 10 agencies had 1–2 notices each.

| Agency ID/name | Roster authority, version, evidence locator | Process/stage | Included? | Reason/authority | Authoritative publication(s) | Gaps / single_lineage + human ref |
|---|---|---|---|---|---|---|
| All UAPA agencies posting on eRegulations | CGS § 4-168(a) posting duty; SOTS RegulationMaking page (req 6); notice-search union (reqs 7–9) | Notice of intent (NOI): written-comment window | **Yes** | Rulemaking comment window. NOI states ≥30-day period and usually an explicit end date (8/8 sampled) | eRegulations NOI PDF (`Search/getDocument?guid=`), listed in `Search/PublicNoticesResults` | single_lineage pending Q5; human ref _pending_ |
| same | NOI text citing § 4-168(b) (reqs 11, 12) | Hearing-request window (15 persons / gov't subdivision or agency / association ≥15 members; within 14 days of posting) | **Yes when stated in the notice** (2/8 sampled). Statutory-only, unstated windows are a reviewer choice (Q1) | In-scope opportunity type. Unstated windows need a relative-date calculation from posting, which has no approved policy (PROTOCOL §5) | NOI PDF | same |
| same | NOI text | Public hearing: definite (1/8) or conditional on request (2/8, one with a pre-set date/time) | **Yes**. Conditional hearings counted with the condition retained (Q2) | In-scope opportunity type. Condition defines whether it occurs | NOI PDF; later-scheduled hearings appear only in RMR history (`getPublicHearingDetails`, JSON) | **Gap:** hearings scheduled after a request are on held JSON (Q3) |
| same | eRegulations RMR page wiring (req 10) | Comment-period extension, hearing reschedule/cancel, correction | **Yes (lifecycle)** | In-scope lifecycle | RMR History/Notes (`getRMRHistory`, `getRMRNotes`, JSON). No such notice type exists in the notice search (only NOI/NOD seen in 3 years) | **Gap:** held route (Q3). Without it, extension recall is unmeasurable |
| same | notice search (reqs 7–9) | Reopened period: a new NOI on an older proceeding | **Yes** (new opportunity, separately identified) | Independently reopened round | NOI listed by publish date regardless of proceeding age. 10 such NOIs in 3 years (e.g. PR2024-059 on 2026-09-01, PR2024-008 on 2026-10-13) | Period identity: the open list lacks period GUIDs. Use NOI GUID + publish date as the native period alias |
| same | notice search | Notice of Decision (NOD) | **Yes as lifecycle/update** (closes the round; "will not proceed" = withdrawal-like). Not an opportunity | Lifecycle | NOD PDF via notice search | Meaning per NOD needs body classification |
| same | SOTS RegulationMaking page | Emergency regulations, technical amendments | **No** (no participation opportunity). A later NOI for the permanent rule is captured as an NOI | No comment/hearing stage | Browse/EmergencyRegulations (JSON shell) | — |
| same | SOTS page; PR2024-059 NOI ("policies and procedures … until final regulations are adopted") | Operational policies (interim policies with their own notice/comment, e.g. DSS § 17b-10) | **Undecided (Q4)** | May carry comment windows. Plan excludes guidance, but statutory interim policies are closer to rulemaking | Browse/OperationalPolicies (JSON shell); some notices are published in the CT Law Journal (blocked) | Gap if included |
| LRRC (General Assembly) | SOTS page | LRRC review/hearings | **No** | Legislative branch | — | — |
| Attorney General | SOTS page | Legal-sufficiency review | **No** | Not a participation opportunity | — | — |
| Non-UAPA bodies (judicial branch, municipalities, quasi-public entities with own procedures) | CGS § 4-166 "agency" definition (not fetched; cga.ct.gov is not in surfaces.json) | any | **No** | Outside UAPA or local government | — | Q7 asks to confirm the exclusion list |
| Petitions for regulation (§ 4-174) | — | Petition decisions | **No** | Not an agency-noticed comment opportunity | — | — |

NOIRA/early-stage policy: CT has no NOIRA stage. Pre-NOI "informal input" requests are not
eRegulations notices and are excluded.

Agency-specific exceptions are checked by classifying every NOI body (sample shows two templates:
SOTS Form ICM-NOI and agency letterhead). Some agencies (e.g. SEEC) point to their own portal.ct.gov
pages for hearing details. Those pages are on hold as a source (Q5).

## Interval and cohorts

- **Proposed civil half-open interval:** `[2024-10-14, 2026-10-12)`, i.e. 104 complete Monday-start
  weeks. Accounting boundary zone: America/New_York, 00:00 Monday. This zone does not decide any
  notice's legal clock. Justification: eRegulations posts continuously, with no issue cycle, so the
  complete publication cycle used here is the civil week. Two years is the shortest window whose
  projection gets reasonably close to the target (below) while keeping review inside the 240-minute
  budget. Dates were chosen from volume only; no adapter output exists.
- **Publication-time authority:** the notice-search `PublishDate` (server epoch ms; e.g. PR2024-059
  NOI = 2026-09-01T17:51Z) and the system-stamped PDF header "Posted 9/1/2026". If they disagree, or a
  notice falls within 24 h of either boundary, it becomes a review case, retained pending decision.
- **Rate evidence (notice search, reqs 7–9):**

  | Window | NOIs | distinct proceedings | NODs |
  |---|---|---|---|
  | 2023-10-19 → 2024-10-15 | 39 | — | 36 |
  | 2024-10-15 → 2025-10-15 | 44 | — | 30 |
  | 2025-10-15 → 2026-10-15 | 28 | — | 23 |
  | **[2024-10-14, 2026-10-12)** | **71** | 62 | 53 |
  | [2023-10-16, 2026-10-12) | 110 | 95 | 89 |
  | [2026-07-20, 2026-10-12) (12 weeks) | 10 | 10 | 4 |

  The 1-year query (75 rows) matched the 3-year query's subset exactly. The 3-year query returned
  exactly 200 rows, which may be a result cap. Census acquisition must use ≤1-year slices and prove
  a terminal condition per slice.
- **Opportunities per NOI** (8 sampled NOIs, 2024-06 → 2026-10, reqs 11–18): 8 comment windows, 2
  stated hearing-request windows, 1 definite hearing and 1 conditional hearing with a set date/time.
  A third notice (PR2026-018) says a hearing "will be scheduled if requested" with no date. It is
  counted only if a hearing is later scheduled. That gives **12/8 = 1.5 per NOI** (plausible range
  1.25–2.0; n = 8 is tiny).
- **Projection (arithmetic):** 71 NOIs × 1.5 = **≈107 new-notice opportunities** (range 89–142). Add
  ≈3–6 carry-in opportunities (open list held 4–5 records at a time in earlier research; ≈2–4 NOIs
  active at start × 1.5). **Shortfall against 149: ≈42.** Zero-miss 95% upper error bound at n = 107
  is 2.76%, versus 1.99% at 149. NOIs share two templates, so independence is weaker than n suggests.
- **Alternatives for the reviewer (Q8):**
  (B) `[2023-10-16, 2026-10-12)`, 156 weeks: 110 × 1.5 ≈ **165**. Meets the target, but needs about
  1.5× the review minutes, and the oldest year's 200-row result needs re-slicing.
  (C) Keep the 104 weeks but count the statutory hearing-request window on every NOI (Q1): 71 × 2.25
  ≈ **160**. Every unstated window would carry a relative "14 days after posting" date, which stays
  `unknown`/relative until a temporal policy exists.
  (D) A 12-week slice gives only ≈15 opportunities. Not recommended.
  **Recommendation: A, with the shortfall stated.** Pick B if the owner raises CT review time.
- **Low-volume shortfall / maximum extension:** a maximum of 156 weeks (option B). Beyond that,
  report CT as low-volume, with no ≥98% claim at 95% confidence.
- **New-notice rule:** earliest evidenced authoritative publication inside the interval.
- **Carry-in rule and backward boundary:** search every NOI published in
  `[2024-04-15, 2024-10-14)` (26 weeks) and include any whose stated comment close, hearing date or
  hearing-request deadline is on or after 2024-10-14. Extend the search backward in 13-week steps
  until a full 13-week step yields no NOI still active at start. Authority: § 4-168 sets a ≥30-day
  minimum and no maximum. Sampled periods ran 30–33 days and stated hearings fell inside the period.
  The archive is not the limit: the notice search reaches back to proceedings begun 2015-03-23, and
  a legacy 2013–2016 page exists.
- **Older-proceeding updates/reopenings:** the notice search lists by publish date regardless of
  tracking-number age, so new NOIs and NODs on old proceedings fall inside the interval naturally
  (10 old-proceeding NOIs in 3 years). Non-notice updates (extensions, hearing changes) are only on
  held JSON, so for those the history universe is **unresolved** (Q3).
- **Other interval updates:** NODs and any re-posted or amended NOI documents. A deadline change does
  not create a new opportunity. A new NOI on the same tracking number does.
- **Overlap:** cohorts deduped by entity ID. Identity tuple: (tracking number, NOI document GUID,
  opportunity role). NOI GUID + publish date is the native period alias.
- **Post-close follow-up:** comment window and hearing-request window run to close + 30 days. Hearings
  run to the hearing date + 14 days. NOD watch runs to close + 180 days, since § 4-168 links LRRC
  submission to 180 days from NOI posting for mandatory regs. Follow-up outside the interval is
  reported separately. Backfill uses the same notice-search slices. No federal 7-day horizon.

## Authority, access and source map

| Source ID/lineage | Agencies/processes covered | Authority/precedence evidence | Rights record/version; collection allowed? | Method/rate | Retain originals? | Third-party/public-evidence limits | Cadence/retention | Gaps |
|---|---|---|---|---|---|---|---|---|
| L1 `ct-eregs` / Notice search results (server-rendered HTML with embedded rows) | All NOIs/NODs since 2015-03-23 | § 4-173b official repository; § 4-168 posting duty | `ct-rendered` 2026-10-15.1, **allowed** | POST `Search/PublicNoticesResults` with date filters, 1 req/5 s | yes (internal) | LlamaParse/LLM ok (public notices); public evidence = link + factual sentence | continuous; history since 2015 | possible 200-row cap; agency picklist and status filter are JSON-filled |
| L1 / NOI & NOD PDFs `Search/getDocument?guid=` | same | official notice | `ct-rendered`, **allowed** | GET | yes | same | permanent | none seen |
| L1 / Browse/OpenForComment, ProposedRegulations, RecentRegulations, RMRView | open list, proposal list, history | — | Pages allowed, but they are **JS shells** (reqs 1, 3, 5, 10). Data loads from `getOpenCommentPeriods`, `getProposedRegulations`, `GetRecentRegulations`, `getRMRHistory`, `getRMRNotes`, `getRMRSummaryInformation`, `getPublicHearingDetails` | **Not used** | — | — | — | Rendering them in a browser would call the held `getOpenCommentPeriods` route and run the F5 bot-defense script that the page serves. Treated as held (Q3) |
| L1 / eRegulations e-mail notification service (§ 4-173b) | NOI postings | statutory | no surface record | — | — | — | — | Same backend lineage, so not independent. Useful only as a timeliness probe (Q6) |
| L2 agency pages `portal.ct.gov/<agency>` | some hearings/notices (e.g. SEEC NOI points there) | agency-published | `ct-policy-reference` **on_hold** | none | no | — | — | Only plausible independent lineage (Q5) |
| L3 Connecticut Law Journal `jud.ct.gov` | some agency notices (e.g. operational policies) | official journal | `ct-law-journal` **blocked** (robots.txt bars AI crawlers) | none | no | — | weekly | blocked; recorded as gap |

Active census: WA/CT/VA/TN. Rights linkage: `ct-rendered@2026-10-15.1` (collected);
`ct-json@2026-10-15.1` (held, not called); `ct-policy-reference@2026-10-15.1` (held);
`ct-law-journal@2026-10-15.1` (blocked). Rate: ≥5 s, sequential, UA `DocketClock-research/0.1
(github.com/lucas-homer/yokel)`. No 403/429 occurred on eRegulations. The responses set F5 `TS…`
cookies and the HTML embeds an obfuscated bot-defense script. Plain HTTP did not trigger it.

**Cross-check strategy:** notice search ↔ NOI bodies (same lineage, internal consistency). The search
also gets checked against itself across overlapping date slices. **Independent lineage: none lawful
today.** Every included process is therefore `single_lineage: true` pending Q5. Completeness
verdict ceiling: **not established**. Shared-backend views (open list, history JSON, e-mail alerts,
notice search) are all L1. Lawful paid reference access: none needed.

## Expected publications and surface tests

| Source/process | Expected units | Expectation evidence | Filters/pagination/terminal proof | Full-body cross-check | Agency/history cross-check | Missing units/reviewer decision |
|---|---|---|---|---|---|---|
| Notice search, slices | 9 quarterly slices covering the interval + carry-in window (~9 POSTs) | reqs 7–9 | Date filters; no pagination seen. Terminal proof = slice rows < cap and overlap agreement with neighbours | each row's PDF | none (L1 only) | cap behaviour unknown, so use quarterly slices |
| NOI PDFs | ≈71 interval + carry-ins (≈125 pages at ~1.75 pages/NOI) | 8-sample page counts 1–4 | one per row GUID | — | — | — |
| NOD PDFs | ≈53 (page count unknown) | search | per row | — | — | null until fetched |
| RMR history/hearing JSON | ≈62 proceedings × 2–3 routes | req 10 wiring | — | — | — | **held → `not_attempted`, gap** |

Unknown counts: NOD pages, any amended-NOI replacements under the same GUID, CLJ-only notices.
Stability re-fetch: not done (scoping only).

## Enumeration, labels and review

Not started (§4–§5 are future steps). Mandatory human-review estimate (illustrative): a small
census (≤150), so every consequential date/role gets checked. About 110 opportunities × 1.5 min =
165 min, plus a minimal audit (~50 min), comes to ≈215 of 240 min. Option B (~165 opportunities)
would exceed 240.

Temporal notes seen during scoping (for the temporal log):
- Closes are given in several forms: date-only ("shall end on April 3, 2025"), with a time and no
  zone ("Monday, July 20, 2026 at 5:00pm"), and relative ("within thirty (30) days of the start of
  the public comment period", PR2024-059, which also states "October 2, 2026"; both are retained).
- Earlier research: the JSON close for PR2026-014 was 03:45Z while the rendered Notes said
  "11:45 PM" with no zone, so the zone is unresolved.
- Hearing-request deadline is relative to posting ("not later than fourteen (14) days after the
  date of posting"). It is never calculated without a policy.
- A conditional hearing with a pre-set date/time (PR2024-059: "Thursday, September 17, 2026 1:30
  PM … will be scheduled … if requested") needs a condition-preserving label.
- System "Posted m/d/yyyy" header vs. agency "Dated" signature line vs. search PublishDate: these are
  distinct roles, and the signature date is not publication.

## Sizing and freeze

- NOIs/week ≈ 0.68 (71/104). Opportunities/week ≈ 1.0 (stated-only). NODs/week ≈ 0.51.
- Format: all 8 sampled NOIs were native-text PDFs (Word-produced or form-produced; 1–4 pages,
  1,500–3,700 chars/page). Two templates (Form ICM-NOI; agency letterhead).
- **LlamaParse estimate:** ≈125 NOI pages + ≈90 NOD pages (assumed ~1.7/NOD) ≈ 215 pages. 0/8
  sampled lacked a usable text layer, so the expected fallback is ≤10% ≈ 22 pages × 10 ≈ **220
  credits**. Worst case 25% ≈ 54 pages ≈ 540 credits. Allocation 2,000, so it fits with headroom.
  Option B: ≈ 330 / 810 credits.
- Setup/weekly cost, development/holdout split, live interval: later steps.

## Questions for the reviewer

1. Should statutory § 4-168(b) hearing-request windows that the NOI does **not** state count as
   opportunities? (yes, labelled relative/unknown close / no, only notice-stated windows: recommended)
2. Count conditional hearings ("will be scheduled if requested", with or without a pre-set date) as
   hearing opportunities with the condition retained? (yes: recommended / only once confirmed held)
3. "Rendered pages" on eRegulations are JS shells over JSON routes. Confirm the reading that the
   census uses only server HTML + documents, with no browser rendering, so RMR history, hearing
   details and extensions stay a gap? Or authorize read-only `getRMRHistory`, `getRMRNotes` and
   `getPublicHearingDetails` at 1 req/5 s for ≈62 proceedings (≈190 requests), pending the CT
   inquiry? (gap / authorize)
4. Are operational-policy notices with comment periods (e.g. DSS § 17b-10) in scope? (no:
   recommended for v1, labelled exclusion / yes)
5. May agency pages on `portal.ct.gov` be read as an independent-lineage cross-check for hearings and
   notices? (yes, read-only, 1 req/5 s / no, accept single_lineage and "not established")
6. Should we subscribe to the statutory eRegulations e-mail notifications as a same-lineage
   timeliness probe? (yes/no)
7. Is the excluded-entity list (legislative/LRRC, AG review, judicial branch, municipalities,
   quasi-publics outside UAPA, § 4-174 petitions) accepted? (yes/edit)
8. Interval: A `[2024-10-14, 2026-10-12)`, ≈107 projected, shortfall ≈42 (recommended); B 156 weeks,
   ≈165, over the review budget; or C, A plus Q1=yes, ≈160? (A/B/C)
9. Are NODs labelled as lifecycle updates (not opportunities), with "will not proceed" treated as a
   withdrawal-type event? (yes/no)

## Request log (attended scoping run, 2026-10-15, UA `DocketClock-research/0.1 (github.com/lucas-homer/yokel)`, ≥5 s apart)

| # | URL | Time (UTC) | Status |
|---|---|---|---|
| 1 | https://eregulations.ct.gov/eRegsPortal/Browse/OpenForComment | 16:22:47 | 200 (JS shell) |
| 2 | https://eregulations.ct.gov/eRegsPortal/Search/PublicNotices | 16:22:57 | 200 |
| 3 | https://eregulations.ct.gov/eRegsPortal/Browse/ProposedRegulations | 16:23:04 | 200 (JS shell) |
| 4 | https://eregulations.ct.gov/eRegsPortal/Information | 16:23:10 | 200 |
| 5 | https://eregulations.ct.gov/eRegsPortal/Browse/RecentRegulations | 16:23:17 | 200 (JS shell) |
| 6 | https://eregulations.ct.gov/eRegsPortal/Information/GetContent?id=RegulationMaking | 16:23:32 | 200 (HTML fragment) |
| 7 | POST …/Search/PublicNoticesResults (PublishedDateAfter=07/01/2026, Before=10/15/2026) | 16:23:52 | 200 (18 rows) |
| 8 | POST …/Search/PublicNoticesResults (After=10/15/2023, Before=10/15/2026) | 16:24:38 | 200 (200 rows; possible cap) |
| 9 | POST …/Search/PublicNoticesResults (After=10/15/2024, Before=10/15/2025) | 16:25:20 | 200 (75 rows) |
| 10 | https://eregulations.ct.gov/eRegsPortal/Search/RMRView/PR2024-059 | 16:25:43 | 200 (JS shell; JSON not called) |
| 11 | …/Search/getDocument?guid={20195EA0-0000-C62D-B563-53BCF41E5272} (PR2024-059 NOI) | 16:25:52 | 200 PDF 4 pp |
| 12 | …/getDocument?guid={10CB21A1-0000-CA12-9D09-EA4D27EC16C3} (PR2026-018) | 16:26:29 | 200 PDF 2 pp |
| 13 | …/getDocument?guid={E0D4D59E-0000-C316-AE8D-7B3B0AC70272} (PR2026-003) | 16:26:37 | 200 PDF 1 p |
| 14 | …/getDocument?guid={60C1CB9A-0000-C011-AC98-D85713B55B1C} (PR2025-027) | 16:26:44 | 200 PDF 2 pp |
| 15 | …/getDocument?guid={D0897B98-0000-C119-A0F8-330A2E1F0742} (PR2025-016) | 16:26:51 | 200 PDF 2 pp |
| 16 | …/getDocument?guid={501F5D95-0000-C016-B015-07291C12B342} (PR2025-001) | 16:26:58 | 200 PDF 1 p |
| 17 | …/getDocument?guid={40426493-0000-CC10-9BE9-8D8F3D3B25AA} (PR2024-053) | 16:27:05 | 200 PDF 1 p |
| 18 | …/getDocument?guid={5061E48F-0000-C510-B544-8B74445DE9A2} (PR2024-014) | 16:27:13 | 200 PDF 1 p |

Not called: `getOpenCommentPeriods` or any other JSON route; `jud.ct.gov`; `portal.ct.gov`;
`cga.ct.gov` (statute text; not in surfaces.json). Statute provisions are cited from the notices
and the SOTS page above, not from the statute text.
