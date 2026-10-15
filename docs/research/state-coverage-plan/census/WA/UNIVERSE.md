# State universe: WA / v0.1-proposed (2026-10-15)

Status: **draft: proposal for owner signature. Not frozen.** Completeness: not established. Every
included process is single-lineage under current rights; see "Source map" and Q7.
Owner: primary (research child draft). Human reviewer: owner. Decision date: _pending owner signature_.
Protocol/schema versions: PROTOCOL v1.1. Rights: `wa-register` (allowed), `wa-ecology-pointers`
(on hold) and `wa-code-lookup` (on hold), all at version `2026-10-15.1`, owner decision `owner-2026-10-15`.
Proposed scope label shown to users: "Washington state agency rule-making notices published in the
Washington State Register (proposals, supplemental notices, continuances, withdrawals and expedited
rule makings). Preproposal statements, local clean-air agencies and APA-exempt materials are not
covered unless noted."
Statewide claim justified? **No.** Evidence: no lawful independent-lineage cross-check exists under
current rights (Q7). Several scope calls are still open (Q1–Q6).

Evidence basis: an attended scoping run on 2026-10-15 made 36 sequential requests to
`wa-register` hosts only, at least 6 s apart, with UA `DocketClock-research/0.1
(github.com/lucas-homer/yokel)`. All returned 200, with no 403 or 429. The log is at the end. It
fetched the Register landing and description, the issue list, the 2026 by-type index, nine issue
pages (26-11…26-19), eight PROP type indexes, four other 26-19 type indexes, the 26-19 closing-date
calendar PDF, the Agency/WAC list, seven filing bodies (HTML) and one filing PDF. No agency page,
`app.leg.wa.gov` or RCW page was fetched; both are on hold. Statute citations below are taken from
Register text and marked by source. Scratch bytes are in `/tmp`, outside git, and are not census
originals. All counts are planning estimates from index rows. None are census results.

## Agency and process universe

**Roster (dated 2026-10-15).** The universe is defined by the publication obligation, not by a list.
The Register "includes notices of proposed rules, emergency and permanently adopted rules, public
meetings, requests for public input…" and is the official publication: "the certified PDF Register
documents … constitute the official publication" (landing page, req 1; `description.htm`, req 2).
Roster source for enumeration: `lawfilesext.leg.wa.gov/law/wsr/AgencyWac.htm`, the "Agency-to-WAC
Title Association with Agency Filings" (req 35). It has about 798 filer links, including sub-units,
advisory committees and historical names with "See also" redirects. In step 3, roster = every filer
appearing in the interval and backward-search issue pages, checked against AgencyWac.htm. Each
entity is marked included or excluded by the rules below.
**Observed in 26-11…26-16 (six issues):** 143 distinct filers of any type. 43 filed PROP/EXPE,
about 125 deduped PROP+EXPE rows. Top filers: DOH 11, HCA 11, DOL 7, DFW 6, DCYF 5, Ecology 5,
L&I 5, CJTC 5. Local clean-air agencies filed 5 (Puget Sound 3, Spokane Regional 1, Olympic Region
1). Columbia River Gorge Commission filed 1.

| Agency ID/name | Roster authority, version, evidence locator | Process/stage | Included? | Reason/authority | Authoritative publication(s) | Gaps / single_lineage + human ref |
|---|---|---|---|---|---|---|
| All state agencies, boards, commissions, colleges/universities filing in WSR | AgencyWac.htm (req 35) ∪ interval issue pages | **CR-102 proposed rule, original notice**: written-comment window + each hearing | **Yes** | Core notice-and-comment. Agencies must publish a hearing notice ≥20 days before the hearing: "see RCW 34.05.320(1)" (closing calendar footnote 3, req 11). Body has "Hearing Location(s)" and "Submit Written Comments to … by …" (26-19-142, req 24) | Certified PDF filing (official) + Register HTML of same filing | single_lineage (Q7) |
| same | same | **CR-102 supplemental notice** ("Supplemental Notice to WSR 26-08-090", 26-19-019, req 25): new comment window + hearing | **Yes, as a new participation round on an existing proceeding** (Q3) | Sets its own window and hearing ("beginning September 11, 2026 … by October 27, 2026, at 11:59 p.m.") | same | same |
| same | same | **Continuance** of a proposal (description.htm lists "continuance" in the Proposed area) | **Yes, as an update** (reschedule/extension), not a new opportunity unless the reviewer rules it an independent reopening | Lifecycle event in plan scope | same | Not sampled in bodies. Rate unknown |
| same | same | **Withdrawal of proposed rules**: agency (including partial, e.g. "only for the CR-102 portion", 26-18-058, req 26) and Code Reviser 180-day lapse ("withdrawn by the office of the code reviser under RCW 34.05.335 (3), since the proposal was not adopted within the 180-day period", 26-14-050, req 27) | **Yes, as updates.** Keep the target and partial scope | Plan lifecycle: full/partial withdrawal | same | Targets can be ~8 months old (26-14-050 → WSR 25-21-115) |
| same | same | **CR-105 expedited rule making**: written-objection window | **Yes**, as a written-comment opportunity of subtype `objection` (Q4) | "IF YOU OBJECT … YOU MUST EXPRESS YOUR OBJECTIONS IN WRITING … BEGINNING September 15, 2026, at 12:00 a.m., AND RECEIVED BY …" (26-19-060, req 29). "A minimum of 45 days … No hearing is required, but the public may file written objections. See RCW 34.05.353" (calendar footnote 4) | same | same |
| same | same | **CR-101 preproposal statement of inquiry** | **Proposed: exclude as an opportunity** unless the body states a dated comment deadline or a scheduled public meeting on the rule. Then include as `early_stage` (Q1) | Sample 26-19-073 (req 30) has only "Interested parties can participate … by contacting …" with no date | same | ~19/issue. Every CR-101 body is still inspected (exclusion stratum) |
| same | same | **CR-103P permanent adoption** | **No** (not an opportunity). Inspected only as closure evidence for follow-up | Adoption is not on the plan's lifecycle list | same | — |
| same | same | **CR-103E emergency rules / rescissions** | **No** | No notice-and-comment opportunity in the filing. Statutory cite not verified (RCW pages on hold) | same | — |
| same | same | **MISC filings** (public meeting schedules, AG opinion summaries, governor orders, court rules, DOC APA-exempt rules, policy/interpretive statements, rules-coordinator notices) | **Default no.** Include only if a MISC body opens or changes a rule-making comment window or hearing (Q5) | description.htm area (6). Meetings, guidance and court rules are out of plan scope | same | ~25–47/issue. Inspect all (exclusion stratum) |
| Local air pollution control authorities (Puget Sound, Southwest, Spokane Regional, Olympic Region, Northwest, Yakima Regional, Benton clean air agencies) | AgencyWac.htm | their CR-102 | **Proposed: exclude** as local government (Q2) | 26-17-052 (req 28): "Proposal is exempt under RCW 70A.15.2040 (1)" | WSR | ~0.8/issue. Recorded as rejects |
| Columbia River Gorge Commission (bi-state compact) | AgencyWac.htm | its rule filings | **Owner call** (Q2) | Interstate body, not a WA agency | WSR | ~1 in 6 issues |
| Courts (Supreme Court rules in MISC), Legislature, Statute Law Committee housekeeping | — | — | **No** | Judicial/legislative, not agency rule-making | — | — |

Exceptions are checked agency by agency in the body, not from index labels: index labels "do not
establish event meaning" (template WA notes). Type index rows are deduped by WSR number. Holdovers
(see below) are attributed to the issue in which they appear.
**Explicit exclusions:** permits, guidance/interpretive and policy statements, legislation,
local government (Q2), who-is-affected analysis, open-public-meetings notices, emergency rules,
adoptions, public comments and commenter data.
**Narrow scope boundary:** opportunities whose authoritative publication is the WSR. Agency-only
announcements that never reach the WSR are outside the declared universe. They are a known
coverage gap, not misses (Q7).
**NOIRA/early-stage policy:** WA's early stage is the CR-101. Proposed default is in the table (Q1).
Decide before enumeration.

## Interval and cohorts

- **Proposed civil half-open interval:** `[2026-06-03, 2026-09-02)`, zone `America/Los_Angeles`.
  This is **six complete issues, 26-11 to 26-16, over 13.0 weeks**. Issue dates: 26-11 06-03,
  26-12 06-17, 26-13 07-01, 26-14 07-15, 26-15 08-05, 26-16 08-19. 26-13…26-16 are stated in the
  2026 closing-date calendar (req 11). 26-11/26-12 are inferred from the stated rule "distributed
  on the first and third Wednesdays of each month" (description.htm). Confirm them from the issue
  PDFs in step 3. 26-17 (2026-09-02) is excluded.
  *Justification:* complete biweekly cycles. Ending at 2026-09-02 leaves the per-process follow-up
  horizon (below) observable in issues already or soon published (through 26-21, 2026-11-04).
  The accounting zone does not decide any notice's legal clock.
- **Fallback (Q8):** five issues 26-12…26-16, `[2026-06-17, 2026-09-02)`, 11.0 weeks. Central
  projection ~166, low ~139. That low case may miss 149, which is why six issues is the recommendation.
- **Publication-time authority:** publication = the "Publication Date" (distribution date) of the
  issue in which the filing appears (closing calendar column 4). It is not the filing timestamp
  ("[Filed September 23, 2026, 11:30 a.m.]") and not the WSR number's issue prefix. **Holdovers
  break that prefix:** 26-17-052 (SWCAA) is listed in issue 26-19 as "26-17-052 holdover". 26-19
  also carries 26-18-017, and 26-13/14/17/18 each have 1–4. The online posting time-of-day is not
  evidenced; date precision only. The landing page's "Publication current through September 23,
  2026 and 26-19 register issue" does not match 26-19's publication date (2026-10-07). It looks
  like the RDS closing date. Treat it as unexplained, not as publication evidence. Filings in a
  boundary issue whose online availability before its date can't be shown stay in their issue; any
  dispute becomes a review case with the candidate retained.
- **Complete cycles and rate (index rows, deduped by WSR number):**

  | Issue | PROP rows | PROP rows with hearing date in index | no-date rows (likely withdrawals) | EXPE | PREP | MISC |
  |---|---|---|---|---|---|---|
  | 26-11 | 15 | 14 | 1 | 0 | 19 | 8 |
  | 26-12 | 14 | 14 | 0 | 4 | 16 | 17 |
  | 26-13 | 17 | 14 | 3 | 1 | 25 | 29 |
  | 26-14 | 26 | 21 | 5 (incl. 5 Code Reviser withdrawals 26-14-049…053) | 4 | 16 | 28 |
  | 26-15 | 25 | 23 | 2 | 3 | 21 | 47 |
  | 26-16 | 18 | 18 | 0 | 1 | 19 | 34 |
  | **Σ 26-11…16** | **115** | **104** | **11** | **13** | **116** | **163** |
  | 26-17 / 18 / 19 (rate check only) | 18 / 13 / 29 | 17 / 9 / 29 | 1 / 4 / 0 | 1 / 2 / 3 | 22 / 24 / 21 | 23 / 15 / 39 |

- **Projected opportunities for the proposed interval (new-notice cohort; arithmetic):**
  - Upper: every hearing-bearing PROP row is a new round with one comment window and one hearing.
    104 × 2 + 13 EXPE objection windows = **221**.
  - Central: 15% of hearing-bearing rows are continuances (updates, not new rounds).
    104 × 0.85 × 2 + 13 = 176.8 + 13 ≈ **190**.
  - Low: 30% continuances. 104 × 0.70 × 2 + 13 = 145.6 + 13 ≈ **159**.
  - The continuance share is an **assumption**. None of the 3 hearing-bearing PROP bodies sampled
    was a continuance. Multi-hearing notices would raise the count (Q6).
  - CR-101s are excluded from the projection (Q1).
  - Expected updates in the interval: ≥11 no-date PROP rows, plus continuances and supplemental
    re-rounds on older proceedings.
- **Target, projected count and independence limits:** target ≥149. Projected range 159–221,
  central ~190. Independence is weakened by template clustering. Every CR-102 uses the same form,
  and agencies file batches (e.g. HCA files 3 same-day proposals with identical hearing times;
  26-19 DCYF has 3 at "10/27/2026 10:00AM").
- **Low-volume shortfall:** none projected. If step-3 index accounting projects <149 before any
  enumeration or adapter output, the predeclared extension adds whole issues backward (26-10, then
  26-09), up to a 17-week maximum (start 2026-05-06). Budget: the WA Phase 1 envelope below.
- **New-notice rule:** earliest evidenced authoritative publication (the issue date as above)
  inside the interval.
- **Carry-in rule and backward search boundary:** an opportunity opened by a filing published
  before 2026-06-03 whose comment close, hearing or objection deadline is ≥ 2026-06-03 (local date).
  Boundary is statutory: a proposal not adopted within 180 days of publication is withdrawn by the
  Code Reviser under RCW 34.05.335(3) (quoted in 26-14-050, req 27). Start − 180 d = 2025-12-05.
  Search issues **25-23 (2025-12-03) through 26-10 (2026-05-20)**, 12 issues, one issue of margin.
  These two dates are computed from the first/third-Wednesday rule; confirm them in step 3. The
  archive reaches back to 05-19 (WsrByIssue.htm, req 3).
  EXPE objection windows (≥45 days) fall well inside this boundary. CR-101s have no window.
  *Open caveat:* whether a supplemental notice restarts the 180-day clock isn't verified (statute
  page on hold). The supplemental is itself a filing in range, so the boundary holds unless an
  older chain is continued without a new filing. Flag any such case for review.
- **Older-proceeding updates/reopenings:** search all PROP/EXPE/MISC rows in the interval issues
  for references to earlier WSR numbers (supplementals, continuances, withdrawals). Resolve each
  target by WSR number through the archive (any age; 26-14-050 targets 25-21-115, about 8 months
  back). An unresolvable target gets `target_unresolved_reason` + review.
- **Other interval updates:** continuances, withdrawals and supplementals in issues 26-12…26-16
  that target proposals first published in 26-11…26-15. Overlapping cohorts deduped by entity ID.
- **Post-close follow-up per process (proposed; outside-interval events reported separately, not scored):**
  - *CR-102 comment/hearing:* through the first issue published on or after the opportunity's last
    close/hearing date, plus one further issue. Basis: continuance hearing notices must publish
    ≥20 days ahead (RCW 34.05.320(1), calendar). Agency withdrawals/supplementals appear in the next
    issues. For 26-16 opportunities (hearings from about 2026-09-08) that runs to about 26-20/26-21
    (2026-10-21/11-04).
  - *CR-105 objection:* through the issue after the objection deadline (≥45 days after
    publication), roughly 26-20 for 26-16.
  - *Code Reviser 180-day withdrawals* (about 2027-02 for 26-16) fall **outside** the horizon.
    Report them as outside-interval lifecycle, unscored.
  - Polling/backfill: re-check the by-type index and the next issue page once per issue
    publication (biweekly). The index is a permanent archive, so backfill = re-read the issue.
    Never inherit the federal 7-day horizon.

## Authority, access and source map

| Source ID/lineage | Agencies/processes covered | Authority/precedence evidence | Rights record/version; collection allowed? | Method/rate | Retain originals? | Third-party/public-evidence limits | Cadence/retention | Gaps |
|---|---|---|---|---|---|---|---|---|
| `wa-register` / lineage `wa-cro` (Code Reviser's Office): certified PDF filings (`/law/wsrpdf/YYYY/II/NN-II-NNN.pdf`) | all included rows | "certified PDF Register documents … constitute the official publication" | `wa-register` 2026-10-15.1; allowed | sequential, ≥5 s, identifying UA | yes (internal) | public notices to LlamaParse/LLM OK; display = link + deadline/hearing sentence | biweekly (1st/3rd Wed); permanent archive since 05-19 | none observed; PDF text layer native (26-19-142.pdf: 5/5 pages with text) |
| `wa-register` / `wa-cro`: filing HTML (`/law/wsr/…/NN-II-NNN.htm`) | same | same publisher; navigation copy of the certified PDF | same | same | yes | same | same | Same lineage as the PDF. Long filings over WAC 1-21-040 page limits point to another issue ("Reviser's Note"); follow those links |
| `wa-register` / `wa-cro`: issue pages `II/NN-II.htm`, by-type indexes `WSRNN-IITYPE.htm`, type PDFs `NN-IIPROP.pdf`, `WSRDocsByType26.htm`, `WsrByIssue.htm`, `law/wsr/agency/*.htm`, closing-date calendar | enumeration/expected-unit sources | same | same | same | yes | — | same | Index rows ≠ unique notices (dedupe). Hearing-date column is index metadata only |
| `wa-register` / `wa-cro`: Agency Rule Making Activity Report, quarterly reports (`leg.wa.gov/media/…`) | possible consistency check | CRO | same | same | yes | — | quarterly | **Same lineage**: can expose omissions but not independent corroboration |
| `wa-ecology-pointers` (agency site) | link discovery only | agency | on hold; no retention | — | **no** | Ecology terms bar "use in a political campaign or lobbying effort" | — | Not a manifest cross-check source |
| `wa-code-lookup` (`app.leg.wa.gov`, RCW/WAC) | statute verification | — | on hold | — | no | — | — | Statute citations here come only from Register text (Q10) |

Active census: WA/CT/VA/TN. Rights linkage: `wa-register` @ `2026-10-15.1`. Rate ≥5 s, sequential,
identifying agent, stop on 403/429, never bypass bot protection.
**Cross-check strategy and independent gap detection.** Same lineage only:
- WSR filing numbers are sequential per issue (26-19-001…144). Every number must resolve to a
  filing in its own issue or as a holdover in a later one. This is a strong omission detector for
  the index.
- The issue page, by-type index and per-agency pages must agree.
- The type PDF table of contents must match the bodies.

All of these share the CRO lineage.
**Independent-lineage cross-check: none lawful under current rights.** Agency rule-making pages are
the only plausible different-lineage source, and they are pointer-only (DECISIONS.md, WA default).
Every included (agency, process) row is therefore `single_lineage: true`, pending a human review
reference, and **completeness is capped at "not established"** (Q7). Shared-backend views (HTML,
PDF, indexes, agency pages under `/law/wsr/agency/`) are one lineage. Lawful paid reference access:
none needed; the Register is free.

## Expected publications and surface tests

| Source/process | Expected units | Expectation evidence | Filters/pagination/terminal proof | Full-body cross-check | Agency/history cross-check | Missing units/reviewer decision |
|---|---|---|---|---|---|---|
| WSR issues 26-11…26-16 (interval) | 6 issue pages; 36 by-type indexes (6 types × 6); 36 type PDFs; 616 filings of all types (69+82+119+123+131+92 issue rows, reqs 18–23, 31, 33), each as HTML + certified PDF | closing calendar + WsrByIssue | none; static pages. Terminal = last WSR sequence number per issue + holdovers listed | type PDF TOC vs filing bodies | sequence-number closure; agency pages under `/law/wsr/agency/` (same lineage) | none yet |
| Backward search 25-23…26-10 | 12 issue pages + PROP/EXPE indexes + bodies of candidate carry-ins only | 180-day rule | same | same | same | dates of 25-23/25-24 to confirm |
| Follow-up 26-17…26-21 | issue pages + PROP indexes | follow-up rule | same | same | same | 26-20 (10-21) and 26-21 (11-04) not yet published |

Manifest snapshot/hash: not started (out of scope for step 2). Unknown counts: PDF page totals per
issue, continuance share, multi-hearing share (all null, not zero). Stability re-fetch: step 7.

## Temporal ambiguity notes seen (for the step-4/5 temporal log)

- Comment close and hearing times carry **no zone wording**: "by November 23, 2026, 11:59 p.m.",
  "at 8:00 a.m." (26-19-142), "by October 27, 2026, at 11:59 p.m." (26-19-019). Keep the zone null
  unless reviewed. Don't normalise to UTC.
- Comment **open** times are later than publication: "beginning October 19, 2026, 12:00 p.m." on a
  notice published 2026-10-07 (26-19-142).
- **Multi-day hearing**: "On November 19-21, 2026, at 8:00 a.m. … or virtual" (one or three hearings? Q6).
- **Date-only hearing**: "On October 27, 2026, telephonic" (26-19-019; the index shows no time).
- **Comment close after the hearing date, date-only**: SWCAA hearing 10/28 6:00 p.m.; comments
  "by October 30, 2026" (26-17-052).
- **Received-by condition**: EXPE "AND RECEIVED BY …" (26-19-060).
- **Negative fixtures**: accommodation deadlines ("Assistance for Persons with Disabilities … by
  November 12, 2026"), "Date of Intended Adoption", filing timestamps.
- **Relative/derived clocks**: first permissible hearing = publication + 20 days. Expedited
  adoption ≥45 days after distribution. 180-day lapse anchored on "distributed on November 5,
  2025" (26-14-050). Calendar closing times are "12:00 noon".
- **Holdovers**: the WSR number's issue prefix ≠ publication issue (above).

## Enumeration, labels and review (steps 4–6; not started)

Not applicable at step 2. One input for planning: the projected central count (~190) exceeds 150.
That moves WA to the random-audit regime, so mandatory reviews plus seeded audit apply, not a
check of every label. Expected mandatory-review drivers: holdovers, partial withdrawals, supplemental
re-rounds, multi-day hearings, zone-less times.

## Sizing and freeze

- **LlamaParse need (estimate):** filing HTML and certified PDFs are born-digital. The sample PDF
  has native text on 5/5 pages; the calendar PDF also has native text. Expected no-text pages are
  embedded maps/figures/scans, which are rarely deadline-bearing.
  - Assumptions: ~600 interval filings + ~150 carry-in/follow-up bodies at ~4 PDF pages each
    ≈ 3,000 pages. 0–1% lack usable native text = 0–30 pages.
  - × 10 credits/page = **0–300 credits** against the WA envelope of 2,000. Reserve 300 before
    dispatch. Expected actual is near 0; only pages that fail extraction go to LlamaParse.
- Shared envelopes unchanged: WA 2,000 / CT 2,000 / VA 2,000 / TN 4,000 / reserve 2,000.
- Format mix: HTML + certified PDF per filing. Templates: CR-101/102/103/105 forms plus free-text
  withdrawals and continuances.
- Development/holdout split, live interval, release rule: not set at step 2.

## Questions for the reviewer

1. **CR-101 preproposals:** exclude as opportunities unless the body states a dated comment
   deadline or a scheduled public meeting on the rule, in which case include as `early_stage`?
   (yes / always exclude / always include)
2. **Non-state filers:**
   a. Exclude local clean-air agencies (Puget Sound, Southwest, Spokane Regional, Olympic Region,
      Northwest, Yakima, Benton) as local government? (yes/no)
   b. Columbia River Gorge Commission: include or exclude? (include/exclude)
3. **Supplemental notices** (RCW 34.05.340 per the Register's "Supplemental Notice to WSR …"):
   count their comment window and hearing as new opportunities, i.e. an independently reopened
   round on the same proceeding? (yes/no)
4. **CR-105 expedited** objection windows: count as written-comment opportunities with subtype
   `objection`? (yes/no)
5. **MISC filings:** default exclude, but include any MISC body that opens or changes a
   rule-making comment window or hearing? Every MISC body is inspected as an exclusion stratum.
   (yes/no)
6. **Hearing counting:** a multi-day hearing ("November 19-21") and a notice listing several
   hearing sessions count as one hearing opportunity per notice, or one per listed date/session?
   (per notice / per date-session)
7. **Independent lineage:** accept `single_lineage: true` for all WA processes, which caps WA at
   "not established" and blocks any statewide claim? Or open a rights review of agency rule-making
   pages for the top filers (DOH, HCA, DOL, DFW, DCYF, L&I) as a retained cross-check?
   Ecology's terms are restrictive. (accept / open review)
8. **Interval:** sign `[2026-06-03, 2026-09-02)` America/Los_Angeles, issues 26-11…26-16, 13 weeks
   (projected ~159–221)? Or the 11-week fallback `[2026-06-17, 2026-09-02)` (~139–190)? Either
   comes with the predeclared backward extension rule. (13-week / 11-week)
9. **Carry-in boundary and follow-up:**
   a. Sign the 180-day statutory backward search (issues 25-23…26-10)? (yes/no)
   b. Sign the per-process follow-up horizons above, with Code Reviser 180-day withdrawals
      reported outside the interval and unscored? (yes/no)
10. **Statute access:** allow read-only, non-retained lookups on `app.leg.wa.gov` (RCW 34.05) to
    verify the cited sections (34.05.310/.320/.330/.335/.340/.350/.353)? Otherwise they stay
    "per Register text". (yes/no)

## Request log (2026-10-15, UTC; UA `DocketClock-research/0.1 (github.com/lucas-homer/yokel)`)

Requests to `http://` URLs were redirected by the server to the same `https://` path (final URL recorded in the scratch log).

| # | Time (UTC) | URL | Status |
|---|---|---|---|
| 1 | 2026-10-15T16:22:03Z | `leg.wa.gov/state-laws-and-rules/washington-state-register/` | 200 |
| 2 | 2026-10-15T16:22:13Z | `leg.wa.gov/media/gp4bdjsf/description.htm` | 200 |
| 3 | 2026-10-15T16:22:19Z | `lawfilesext.leg.wa.gov/law/wsr/WsrByIssue.htm` | 200 |
| 4 | 2026-10-15T16:22:26Z | `lawfilesext.leg.wa.gov/law/wsr/2026/WSRDocsByType26.htm` | 200 |
| 5 | 2026-10-15T16:22:43Z | `lawfilesext.leg.wa.gov/law/wsr/2026/19/WSR26-19PROP.htm` | 200 |
| 6 | 2026-10-15T16:22:49Z | `lawfilesext.leg.wa.gov/law/wsr/2026/19/WSR26-19PREP.htm` | 200 |
| 7 | 2026-10-15T16:22:56Z | `lawfilesext.leg.wa.gov/law/wsr/2026/19/WSR26-19EXPE.htm` | 200 |
| 8 | 2026-10-15T16:23:03Z | `lawfilesext.leg.wa.gov/law/wsr/2026/19/WSR26-19MISC.htm` | 200 |
| 9 | 2026-10-15T16:23:09Z | `lawfilesext.leg.wa.gov/law/wsr/2026/19/WSR26-19EMER.htm` | 200 |
| 10 | 2026-10-15T16:23:15Z | `lawfilesext.leg.wa.gov/law/wsr/2026/19/26-19.htm` | 200 |
| 11 | 2026-10-15T16:23:45Z | `lawfilesext.leg.wa.gov/law/wsr/2026/19/ClosingDateCalendar.pdf` | 200 |
| 12 | 2026-10-15T16:23:51Z | `lawfilesext.leg.wa.gov/law/wsr/2026/18/WSR26-18PROP.htm` | 200 |
| 13 | 2026-10-15T16:23:58Z | `lawfilesext.leg.wa.gov/law/wsr/2026/17/WSR26-17PROP.htm` | 200 |
| 14 | 2026-10-15T16:24:05Z | `lawfilesext.leg.wa.gov/law/wsr/2026/16/WSR26-16PROP.htm` | 200 |
| 15 | 2026-10-15T16:24:11Z | `lawfilesext.leg.wa.gov/law/wsr/2026/15/WSR26-15PROP.htm` | 200 |
| 16 | 2026-10-15T16:24:18Z | `lawfilesext.leg.wa.gov/law/wsr/2026/14/WSR26-14PROP.htm` | 200 |
| 17 | 2026-10-15T16:24:24Z | `lawfilesext.leg.wa.gov/law/wsr/2026/13/WSR26-13PROP.htm` | 200 |
| 18 | 2026-10-15T16:25:00Z | `lawfilesext.leg.wa.gov/law/wsr/2026/18/26-18.htm` | 200 |
| 19 | 2026-10-15T16:25:07Z | `lawfilesext.leg.wa.gov/law/wsr/2026/17/26-17.htm` | 200 |
| 20 | 2026-10-15T16:25:13Z | `lawfilesext.leg.wa.gov/law/wsr/2026/16/26-16.htm` | 200 |
| 21 | 2026-10-15T16:25:20Z | `lawfilesext.leg.wa.gov/law/wsr/2026/15/26-15.htm` | 200 |
| 22 | 2026-10-15T16:25:26Z | `lawfilesext.leg.wa.gov/law/wsr/2026/14/26-14.htm` | 200 |
| 23 | 2026-10-15T16:25:32Z | `lawfilesext.leg.wa.gov/law/wsr/2026/13/26-13.htm` | 200 |
| 24 | 2026-10-15T16:25:57Z | `lawfilesext.leg.wa.gov/law/wsr/2026/19/26-19-142.htm` | 200 |
| 25 | 2026-10-15T16:26:03Z | `lawfilesext.leg.wa.gov/law/wsr/2026/19/26-19-019.htm` | 200 |
| 26 | 2026-10-15T16:26:09Z | `lawfilesext.leg.wa.gov/law/wsr/2026/18/26-18-058.htm` | 200 |
| 27 | 2026-10-15T16:26:16Z | `lawfilesext.leg.wa.gov/law/wsr/2026/14/26-14-050.htm` | 200 |
| 28 | 2026-10-15T16:26:23Z | `lawfilesext.leg.wa.gov/law/wsr/2026/17/26-17-052.htm` | 200 |
| 29 | 2026-10-15T16:26:29Z | `lawfilesext.leg.wa.gov/law/wsr/2026/19/26-19-060.htm` | 200 |
| 30 | 2026-10-15T16:26:35Z | `lawfilesext.leg.wa.gov/law/wsr/2026/19/26-19-073.htm` | 200 |
| 31 | 2026-10-15T16:27:40Z | `lawfilesext.leg.wa.gov/law/wsr/2026/12/26-12.htm` | 200 |
| 32 | 2026-10-15T16:27:46Z | `lawfilesext.leg.wa.gov/law/wsr/2026/12/WSR26-12PROP.htm` | 200 |
| 33 | 2026-10-15T16:27:52Z | `lawfilesext.leg.wa.gov/law/wsr/2026/11/26-11.htm` | 200 |
| 34 | 2026-10-15T16:27:59Z | `lawfilesext.leg.wa.gov/law/wsr/2026/11/WSR26-11PROP.htm` | 200 |
| 35 | 2026-10-15T16:33:55Z | `lawfilesext.leg.wa.gov/law/wsr/AgencyWac.htm` | 200 |
| 36 | 2026-10-15T16:34:24Z | `lawfilesext.leg.wa.gov/law/wsrpdf/2026/19/26-19-142.pdf` | 200 |
