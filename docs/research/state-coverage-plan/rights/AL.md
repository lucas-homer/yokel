# AL — access and rights check (backup hard candidate, ADR 0013 Amendment 1)

Retrieved 2026-10-15. Robots and app shell, the app bundle (to find routes and footer text), one
GraphQL call (refused), the September and August 2026 *Alabama Administrative Monthly* issues, a
404 for October, and three ADEM pages as a cross-check sample. 11 requests in total. Request log:
[`../census/BACKUP-HARD-CANDIDATE.md`](../census/BACKUP-HARD-CANDIDATE.md#request-log).
Confidence: **stated** / **inferred** / **unknown**. Nothing here is a legal conclusion.

## Surfaces

1. **Alabama Administrative Monthly (AAM)**, published by the Legislative Services Agency (LSA),
   Administrative Procedure Division. One PDF per month at
   `admincode.legislature.state.al.us/api/aam/YYYY-MM` (60–65 pages in the two issues sampled).
   Each proposal is a one-page APA-2 "Notice of Intended Action". The authoritative surface.
2. **Agency Proposed Rules** view on the same host (`/agency-proposed-rules`). This is a
   JavaScript app backed by `/api/graphql`, which answered our query with `PersistedQueryOnly`. It
   only accepts the app's pre-registered query hashes. It was not used further (see Q2).
3. **Agency pages** (sample: ADEM, `adem.alabama.gov`). Cross-check only.

### 1–2. AAM and the admin code app (LSA)

| Field | Finding | Evidence | Confidence |
|---|---|---|---|
| Terms | No terms of use page found. The app footer claims copyright and names LSA as official publisher. No reuse licence. | "The Alabama Legislative Services Agency serves as the official publisher of the Alabama Administrative Code and Administrative Monthly." "Copyright © Alabama Legislative Services Agency. All rights reserved." (footer text in https://admincode.legislature.state.al.us/main.47d2713d41a4b6b8.js, rendered on every page) | stated; **inferred** that the generic copyright line is ambiguous for agency notices, as on WA's `leg.wa.gov` |
| Collection method and rate | Public HTTP, no login. There is no robots file: `/robots.txt` returns the app's HTML shell (200). The shell carries `<meta name="robots" content="all">` and `NX_PUBLIC_ROBOTS:'all'`. The monthly PDF route is a plain GET. The GraphQL API is restricted to persisted queries. No rate guidance. | https://admincode.legislature.state.al.us/robots.txt (HTML, 200); `POST /api/graphql` → `{"errors":[{"message":"PersistedQueryOnly"}]}`; https://admincode.legislature.state.al.us/api/aam/2026-09 (200, PDF, 2.8 MB); `/api/aam/2026-10` → 404 on 2026-10-15 (not yet published) | stated (observed); rate **unknown** |
| Retain originals | Not addressed. | — | unknown (no restriction found) |
| Third-party processing | Not addressed by LSA. DECISIONS item 1 allows public notices to go to LlamaParse and LLM APIs. | DECISIONS.md item 1 | stated (our rule); unknown (LSA view) |
| Public display | Not addressed beyond the copyright line. | footer above | unknown |

`alison.legislature.state.al.us/robots.txt` also returns an HTML page rather than a robots file.

### 3. Agency pages (sample: ADEM)

| Field | Finding | Evidence | Confidence |
|---|---|---|---|
| Terms | No terms, disclaimer or copyright link in the homepage's static links. | https://adem.alabama.gov/ | unknown |
| Collection method and rate | `robots.txt` is the stock Drupal file and does not disallow public pages. ADEM lists its own rulemaking hearings as events. | https://adem.alabama.gov/robots.txt | stated |
| Independent lineage | Yes for this agency. The ADEM event page independently states the Division 4 hearing that the September AAM prints: "Public Hearing November 19, 2026 10:00 a.m. Division 4 Rulemaking 1400 Coliseum Blvd, Montgomery, AL 36110" (https://adem.alabama.gov/events-meetings/division-4-rulemaking). | as quoted | stated (one agency) |

## Questions for the reviewer

1. May we collect, retain and quote AAM issues and their APA-2 notices, given the generic "All rights
   reserved" footer and no reuse terms? (yes/no)
2. The proposals view uses a persisted-query-only GraphQL API. Do we stay with the monthly PDF route
   and leave the API alone unless LSA documents or permits it? (yes / ask LSA)
3. AAM is monthly, and October was not yet out on 2026-10-15. Accept AAM as a monthly-only source
   with an explicit delayed-source limitation, or require earlier discovery from agency pages?
   (accept / require)
4. May we read agency pages such as ADEM's as cross-checks where no terms are published? DECISIONS
   item 5 says to check terms first; none were found. (yes/no)

## Provisional collection rule

- **Safe to begin now:** none beyond what is logged. AL is a research candidate only.
- **On reviewer yes to Q1:** monthly `/api/aam/YYYY-MM` PDFs, sequential, identifying user agent,
  at least 5 seconds apart, stop on any 403/429. Retain bytes and hashes internally. Display = link
  plus the "FINAL DATE FOR COMMENT" sentence.
- **Blocked:** the GraphQL API (Q2); agency pages beyond pointer use until Q4.
