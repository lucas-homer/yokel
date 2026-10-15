# Backup hard candidate (ADR 0013 Amendment 1): shortlist, scope and recommendation

Research child report, 2026-10-15. Owner decides. Nothing here selects a state or starts a census.
Rights files: [`../rights/MS.md`](../rights/MS.md), [`../rights/AL.md`](../rights/AL.md),
[`../rights/NV.md`](../rights/NV.md). Scratch bytes are in `/tmp/backup-hard-scope/` and are not in
git. 39 requests, all logged below, with no 403 or 429 responses.

## Shortlist

The pool is the July audit's 19 freshly inspected states, minus WA, CT, VA, MA and TN, which
leaves 14: AL, AK, AR, CA, GA, HI, IA, MS, NE, NJ, NV, OR, SD and UT. I picked three from the audit
and inventory text, before fetching anything.

- **MS (Mississippi).** The audit's only visually verified scanned notice. Its one-page proposal
  form had an imperfect text layer and a stamp the text layer dropped. The extraction experiment
  produced one of the three serious semantic failures: a hearing-request period was put in the
  comment-deadline field. The inventory says no complete discovery route was established. Hard on
  both PDF/visual ambiguity and role complexity, with a single official registrar, so plausibly
  collectable.
- **AL (Alabama).** The only state whose audited source is a monthly PDF bulletin (`/api/aam/`),
  "not a normalized JSON notice API", with only three pages inspected. Monthly-only publication
  tests the plan's delayed-source rule. Notice-level extraction from a dense multi-agency issue was
  untested. Plausibly collectable through one official GET route.
- **NV (Nevada).** The audit found a rolling index that keeps only four weeks and flagged joins to
  hearing notices as untested. That pointed to an acquisition and reference-gap problem: dates
  might live off-Register. The LCB host is static HTML, so it is plausibly collectable.

Not shortlisted:

- **HI:** a department directory with newspaper notices. Too likely to have no lawful complete
  route.
- **NJ:** vendor-hosted Register with unknown automation rights.
- **AR:** paid bulk files.
- **NE:** mid-migration with a partial table.
- **SD:** a 20-day archive, but otherwise thin evidence.
- **OR:** session-parameter links.
- **GA:** agency-scope only.
- **AK, IA, CA, UT:** structured or semi-structured, so they look easy or they are feed-only.

## What the light scope found

### MS: hard on visual and semantic grounds; one central, enumerable route

- **Route.** The bulletin is only reachable through the page's own `BulletinSearch` service call.
  The page renders no rows itself. A query for proposed filings dated 2026-07-01 to 2026-10-15
  returned **73 proposals from 28 agencies**, about **4.8 a week** (range 0–12). Each record holds
  agency, rule, summary, filing ID and the proposed date. It holds **no comment or hearing
  deadline**.
- **Native text.** All four notice forms sampled (`000289{52,44,40,28}a.pdf`) are **image-only**.
  Each is one page with an image XObject, no font resources and Producer "PaperCut" (a copier
  scan). Two were checked visually.
- **Where the deadlines are.** The windows are **relative and boilerplate**. The form says a
  hearing must be held if requested "within twenty (20) days after the filing of this notice". It
  also says written submissions may be made "within the twenty-five (25) day public comment
  period". The anchor is the hand-applied "FILED" stamp, which matched the record's proposed date
  in both forms checked visually. Whether an oral proceeding is scheduled is a checkbox on the
  scan.
- **Roles.** One comment window and one hearing-request window per proposal, plus an occasional
  scheduled oral proceeding. This is the exact role confusion the audit measured.
- **Completeness check.** Filing IDs are sequential across all filing types. Proposed filings plus
  final-dated filings in the same window covered **155 of the 159** IDs between 28794 and 28952.
  Four were unexplained (28892, 28899, 28935, 28938). The IDs can be enumerated, which gives a
  within-lineage completeness check.
- **Cross-check.** None was established. The one agency sampled (Medicaid) links back to SOS.

### AL: moderate difficulty; semantically cleaner than expected

- **Volume.** The September 2026 issue has 60 pages and **39** APA-2 notices. August has 65 pages
  and **47** notices. That is about **9–11 notices a week**, but proceedings are fewer, because one
  ADEM hearing covered 10 per-rule notices.
- **Where the deadlines are.** Every notice has an explicit "FINAL DATE FOR COMMENT AND COMPLETION
  OF NOTICE" in native text. Hearings appear in free text, sometimes before the comment end date:
  for example, an ADPH hearing on Oct 8 with comments due Nov 4.
- **Native text.** Pages without native text: September **6 of 60** (pp. 29–34, six whole notice
  pages); August **2 of 65**. The table of contents extracts in scrambled column order.
- **Cadence.** Monthly. October was not yet published on Oct 15 (404). The "Agency Proposed Rules"
  view is a persisted-query-only GraphQL app. We did not use it.
- **Cross-check.** The ADEM event page independently confirms the Nov 19, 2026 10:00 a.m.
  Division 4 hearing.

### NV: hardest on acquisition; weakest lawful completeness route

- **The Register mostly lacks the dates.** The 2026 numerical index lists **178** LCB file numbers
  and **147** LCB drafts (P). Only **7** file numbers have a Register notice of workshop or hearing
  (NW/NH). The 4-week Latest Additions list had **zero** NW/NH among 115 entries.
- **Measured reference gap.** DMV's own workshop notice for R166-26 (Oct 16, 2026) is not on the
  Register, which has only R166-26I and R166-26P.
- **Where discovery happens.** It depends on `notice.nv.gov`, the open-meeting board for every
  public body in the state. It links out to dozens of agency hosts, including Google Drive and Wix
  files.
- **Native text.** Both sampled PDFs have native text (13 of 13 and 6 of 6 pages).
- **Volume.** About **3.6 new drafts a week**. The sampled proceedings had both a workshop and a
  hearing, but I did not verify whether the statute requires both.

## Comparison

| | MS | AL | NV |
|---|---|---|---|
| **Hard-state evidence (measured)** | 4/4 notice forms image-only; windows relative to a stamped filing date; checkbox semantics; audit's measured hearing-request vs comment confusion; listing only via a script-called service | 6/60 and 2/65 pages lack native text; monthly-only cadence; per-rule notice fragmentation; TOC extraction scrambled; deadlines otherwise explicit | Register carries NW/NH for 7/178 proceedings; R166-26 workshop absent from Register; discovery via a statewide all-bodies meeting board linking to scattered hosts |
| **Collection route** | SOS bulletin service (the page's own POST) plus static `ACProposed` PDFs. robots allows. Disclaimer: "lawful purposes". **Cloudflare in front; never challenged** | One official GET per month (`/api/aam/YYYY-MM`). No robots file, meta robots "all". "All rights reserved" footer | LCB static indexes and PDFs (robots allows) plus `notice.nv.gov` (no robots, statutory posting) plus per-agency hosts (terms unchecked, some third-party) |
| **Volume estimate** | ~4.8 proposals/wk → ~5 comment + ~5 hearing-request windows/wk; ~63 proposals in a 13-week census; finals ~6/wk for lifecycle | ~40–47 notices/month; proceedings fewer; ~3 issues per 13 weeks | ~3.6 drafts/wk; up to ~7 workshop/hearing opportunities/wk |
| **Where deadlines live** | Inside image-only forms, as relative boilerplate anchored to the stamp. Structured record has proposed date only | Native-text "FINAL DATE FOR COMMENT" field; hearings in free text | Inside agency notice PDFs off-Register (native text in sample) |
| **Pages lacking native text** | 100% of sampled notice pages (4/4) | ~3–10% of issue pages | 0% in sample (19/19 pages had text) |
| **LlamaParse at ~10 credits/page vs 2,000 reserve** | Census: ~63 proposal forms + ~80 final/withdrawal forms ≈ 143 pages ≈ **1,430 credits**. Fits, with little room for retries. Proposals only ≈ 630. Ongoing ≈ 110 credits/wk, which exceeds the reserve after the census | ~6–20 pages over 3 issues ≈ **60–200 credits** | Agency PDFs mostly native in sample: **~0–300 credits** (unknown host mix) |
| **Independent-lineage cross-check** | Not established (Medicaid defers to SOS); filing-ID sequence gives a within-lineage completeness check | Yes for ADEM (one agency, one hearing confirmed) | Register vs agency vs notice board, but the Register lacks most notices, so the "cross-check" is the primary source |

## Recommendation: MS

MS is the backup hard candidate that clears the bar on measured evidence and still has a lawful,
bounded route:

- **It is hard for the right reasons.** These are the difficulties the product must handle and has
  already failed on once: scanned forms, checkbox semantics, relative windows anchored to a stamp,
  and hearing-request versus comment roles. The audit's MS failure is a ready regression case.
- **It has one official registrar** with sequential filing IDs. A census can reconcile completeness
  against the ID sequence. Neither NV nor AL offers that, and NV's scattered hosts make a
  completeness claim close to impossible within the 4-hour review budget.
- **Volume is low but real** (~5 proposals a week), and parsing cost fits the 2,000-credit reserve
  for a 13-week census.

AL is the fallback if MS's service route is refused. It meets the bar more weakly: monthly cadence
and some image-only pages, but explicit deadlines. NV is not credible for the pilot. Its difficulty
is real, but a completeness claim needs a per-host rights check across dozens of agency and
third-party hosts.

**MS limits to state plainly:**

- It is likely to be single-lineage, so recall is capped unless an agency cross-check is found.
- Deadlines are derived from boilerplate and the filing date. The rulebook must label them as
  computed, or abstain, under the "date-only/local/relative ambiguity" scenario.
- Ongoing parsing of about 110 credits a week needs a Phase 5 parser ceiling.
- Cloudflare could start challenging at any time, which would stop collection.

## Owner questions

1. Name **MS** as the backup hard candidate under Amendment 1? (yes / AL instead / none)
2. Allow the SOS `BulletinSearch` service POST at 1 request / 5 s, as with CT item 7? There is no
   rendered alternative. (yes / ask SOS first)
3. Accept MS as single-lineage, with the filing-ID sequence as the completeness check, or fund a
   short agency cross-check sample first (about 5 agencies, terms checked)? (accept / sample)
4. Reserve the 2,000 LlamaParse credits for MS, about 1,430 for the census, or limit parsing to
   proposal forms (about 630) and track finals through the bulletin record only? (full / proposals
   only)
5. Send MS SOS a short courtesy note on rate and user agent before any scheduled polling, as with
   TN? (yes/no)

## Request log

UA `DocketClock-research/0.1 (github.com/lucas-homer/yokel)`. Requests were sequential, at least 5
seconds apart, with redirects followed. Columns are UTC time, state, scratch ID, URL, status, type
and bytes.

| UTC | State | ID | URL | Result |
|---|---|---|---|---|
| 2026-10-15T17:04:04Z | MS | r01 | https://www.sos.ms.gov/robots.txt | 200 text/plain 2027 |
| 2026-10-15T17:04:13Z | MS | r02 | https://www.sos.ms.gov/ | 200 text/html 141745 |
| 2026-10-15T17:04:23Z | MS | r03 | https://www.sos.ms.gov/disclaimer | 200 text/html 108498 |
| 2026-10-15T17:04:29Z | MS | r04 | https://www.sos.ms.gov/regulation-enforcement/administrative-code/administrative-bulletin | 200 text/html 112640 |
| 2026-10-15T17:04:43Z | MS | r05 | https://www.sos.ms.gov/adminsearch/default.aspx?current_page=Bulletin | 200 text/html 11736 |
| 2026-10-15T17:05:01Z | MS | r06 | https://www.sos.ms.gov/adminsearch/Admin.js | 200 application/javascript 58296 |
| 2026-10-15T17:05:18Z | MS | r07 | https://www.sos.ms.gov/adminsearch/AdminSearchService.asmx/js | 200 application/x-javascript 5048 |
| 2026-10-15T17:05:30Z | MS | r08 | POST https://www.sos.ms.gov/adminsearch/AdminSearchService.asmx/BulletinSearch (proposed, proposed-date 07/01–10/15/2026) | 200 application/json 27468 |
| 2026-10-15T17:05:57Z | MS | r09 | https://www.sos.ms.gov/adminsearch/ACProposed/00028952a.pdf | 200 application/pdf 58220 |
| 2026-10-15T17:06:02Z | MS | r10 | https://www.sos.ms.gov/adminsearch/ACProposed/00028944a.pdf | 200 application/pdf 52008 |
| 2026-10-15T17:06:08Z | MS | r11 | https://www.sos.ms.gov/adminsearch/ACProposed/00028940a.pdf | 200 application/pdf 55019 |
| 2026-10-15T17:06:13Z | MS | r12 | https://www.sos.ms.gov/adminsearch/ACProposed/00028928a.pdf | 200 application/pdf 54110 |
| 2026-10-15T17:06:45Z | MS | r13 | https://medicaid.ms.gov/robots.txt | 404 text/html 146 |
| 2026-10-15T17:07:03Z | MS | r14 | https://medicaid.ms.gov/ | 200 text/html 278716 |
| 2026-10-15T17:07:27Z | AL | r01 | https://admincode.legislature.state.al.us/robots.txt | 200 text/html 1855 (app shell, no robots file) |
| 2026-10-15T17:07:33Z | AL | r02 | https://admincode.legislature.state.al.us/ | 200 text/html 1855 |
| 2026-10-15T17:07:43Z | AL | r03 | https://admincode.legislature.state.al.us/main.47d2713d41a4b6b8.js | 200 application/javascript 997363 |
| 2026-10-15T17:08:17Z | AL | r04 | POST https://admincode.legislature.state.al.us/api/graphql (filingsViewer, proposals) | 200 application/json 45 (`PersistedQueryOnly`; not retried) |
| 2026-10-15T17:08:52Z | AL | r05 | https://admincode.legislature.state.al.us/api/aam/2026-09 | 200 application/pdf 2812335 |
| 2026-10-15T17:10:13Z | AL | r06 | https://alison.legislature.state.al.us/robots.txt | 200 text/html 58303 (app page, no robots file) |
| 2026-10-15T17:10:18Z | AL | r07 | https://admincode.legislature.state.al.us/api/aam/2026-10 | 404 (not yet published) |
| 2026-10-15T17:10:30Z | AL | r08 | https://admincode.legislature.state.al.us/api/aam/2026-08 | 200 application/pdf 1683103 |
| 2026-10-15T17:10:44Z | AL | r09 | https://adem.alabama.gov/robots.txt | 200 text/plain 2027 |
| 2026-10-15T17:10:49Z | AL | r10 | https://adem.alabama.gov/ | 200 text/html 84826 |
| 2026-10-15T17:11:13Z | AL | r11 | https://adem.alabama.gov/events-meetings/division-4-rulemaking | 200 text/html 60272 |
| 2026-10-15T17:11:27Z | NV | r01 | https://www.leg.state.nv.us/robots.txt | 200 text/plain 451 |
| 2026-10-15T17:11:32Z | NV | r02 | https://www.leg.state.nv.us/Register/indexes/DailyUpdates.htm | 200 text/html 104233 |
| 2026-10-15T17:11:52Z | NV | r03 | https://notice.nv.gov/robots.txt | 404 text/html 1245 |
| 2026-10-15T17:11:57Z | NV | r04 | https://notice.nv.gov/ | 200 text/html 153816 |
| 2026-10-15T17:12:18Z | NV | r05 | https://notice.nv.gov/Home/Help | 200 text/html 12379 |
| 2026-10-15T17:12:23Z | NV | r06 | https://www.leg.state.nv.us/Register/ | 200 text/html 32088 |
| 2026-10-15T17:12:35Z | NV | r07 | https://www.leg.state.nv.us/Register/indexes/2026_NAC_REGISTER_NUMERICAL.htm | 200 text/html 469562 |
| 2026-10-15T17:12:49Z | NV | r08 | https://www.leg.state.nv.us/ | 200 text/html 59668 |
| 2026-10-15T17:12:55Z | NV | r09 | https://www.leg.state.nv.us/Register/2026Register/R149-26NH.pdf | 200 application/pdf 385136 |
| 2026-10-15T17:13:09Z | NV | r10 | http://nv.gov/privacy-policy/ → https://www.nv.gov/privacy-policy/ | 200 text/html 39559 |
| 2026-10-15T17:13:26Z | NV | r11 | https://dmv.nv.gov/robots.txt | 200 text/plain 40 |
| 2026-10-15T17:13:31Z | NV | r12 | https://dmv.nv.gov/publicmeetings.htm | 200 text/html 97895 |
| 2026-10-15T17:13:46Z | NV | r13 | https://dmv.nv.gov/public_meetings/10-16-26_regulations_agenda.pdf | 200 application/pdf 381052 |
| 2026-10-15T17:14:11Z | MS | r15 | POST https://www.sos.ms.gov/adminsearch/AdminSearchService.asmx/BulletinSearch (all types, final-date 07/01–10/15/2026) | 200 application/json 33313 |

Totals: MS 15, AL 11, NV 13. All candidates were under the 40-request limit. Native-text
measurements used macOS PDFKit page text on the scratch copies. Image-only status was confirmed by
the PDF object structure (image XObjects, no fonts) and by visual inspection of two MS forms.
