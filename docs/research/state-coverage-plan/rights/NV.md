# NV — access and rights check (backup hard candidate, ADR 0013 Amendment 1)

Retrieved 2026-10-15. Robots, privacy/disclaimer and help pages, the Register home, Latest
Additions and 2026 numerical index, one Register hearing notice, the state public-notice homepage,
and one agency (DMV) listing plus one workshop notice. 13 requests in total. Request log:
[`../census/BACKUP-HARD-CANDIDATE.md`](../census/BACKUP-HARD-CANDIDATE.md#request-log).
Confidence: **stated** / **inferred** / **unknown**. Nothing here is a legal conclusion.

## Surfaces

1. **Register of Administrative Regulations**, Legislative Counsel Bureau (LCB), at
   `www.leg.state.nv.us/Register/`. Static HTML indexes (a 4-week "Latest Additions" list and yearly
   subject/numerical indexes) link to PDFs by LCB file number and suffix: I initial draft, P LCB
   draft, RP revised, NW notice of workshop, NH notice of hearing, NI informational statement, A
   adopted, AP approved, W withdrawn.
2. **Nevada Public Notice Website**, `notice.nv.gov`, run by the Department of Administration
   under NRS 232.2175. This is the open-meeting board for every public body, state and local. Each
   entry links out to the body's own site or file.
3. **Agency sites** where workshop and hearing notices actually live (sample: DMV,
   `dmv.nv.gov/publicmeetings.htm`). Hosts vary widely, including Google Drive and Wix file links seen
   on `notice.nv.gov`.

### 1. Register (LCB)

| Field | Finding | Evidence | Confidence |
|---|---|---|---|
| Terms | No terms of use or reuse statement found. The homepage links only "Contact Us" and "Privacy Policy" (nv.gov's). | https://www.leg.state.nv.us/ (footer links); https://www.nv.gov/privacy-policy/ §6.4: "Information provided on state of Nevada web sites is intended to provide immediate access to public information." | stated (absence observed); inferred that the nv.gov policy covers LCB only loosely (LCB is legislative, the policy targets executive-branch sites) |
| Collection method and rate | Public HTTP, no login. `robots.txt` disallows `*.axd`, `Reports`, `ExhibitDocument`, some fiscal notes, lobbyist test and opinions. `/Register/` is allowed. No rate guidance. The Latest Additions index keeps only 4 weeks. | https://www.leg.state.nv.us/robots.txt; "This list includes all proposed or adopted regulations that have been added to the Register on the Internet during the last 4 weeks." (https://www.leg.state.nv.us/Register/indexes/DailyUpdates.htm) | stated |
| Retain originals | Not addressed. | — | unknown (no restriction found) |
| Third-party processing | Not addressed. DECISIONS item 1 allows public notices to go to LlamaParse and LLM APIs. | DECISIONS.md item 1 | stated (our rule) |
| Public display | Not addressed. | — | unknown |

### 2. Nevada Public Notice Website (Department of Administration)

| Field | Finding | Evidence | Confidence |
|---|---|---|---|
| Terms | No terms page. The help page states public viewing needs no account. | "The Public Notice Website is open to the public to view notices posted. No account or login is required. Accounts/Logins are used only by the Public Bodies to post notices." (https://notice.nv.gov/Home/Help) | stated |
| Collection method and rate | `robots.txt` returns 404. The homepage is server-rendered HTML listing upcoming meetings by date with an outbound link per entry. Rulemaking workshops and hearings are mixed with every other public meeting, for example "DMV Public Hearings & Workshops", "Division of State Lands" ("public-meeting-to-review-regulations..."), and an LP-gas board PDF on `_files/ugd/` (Wix). Posting deadline is statutory. | https://notice.nv.gov/robots.txt (404); https://notice.nv.gov/; "Posting the notice on the official website of the State pursuant to NRS 232.2175 not later than 9 a.m. of the third working day before the meeting is to be held" (help page, citing NRS 241.020) | stated |
| Retain / third-party / display | Not addressed. | — | unknown |

### 3. Agency sites (sample: DMV)

| Field | Finding | Evidence | Confidence |
|---|---|---|---|
| Terms | Not read (homepage policy links not fetched). | — | unknown |
| Collection method and rate | `robots.txt` disallows only `/news/template/`. The public-meetings page lists regulation workshops with agenda PDFs (native text). | https://dmv.nv.gov/robots.txt; https://dmv.nv.gov/publicmeetings.htm | stated |
| Independent lineage | Yes, and in this sample it is the *only* lineage. The DMV workshop notice for LCB file R166-26 (Oct 16, 2026, posted Sept 29) has no NW entry on the Register, which lists only R166-26I and R166-26P. | "Notice of Workshop to Solicit Comments on Proposed Regulation R166-26 ... Friday October 16, 2026 at 1:30pm" (https://dmv.nv.gov/public_meetings/10-16-26_regulations_agenda.pdf); 2026 numerical index | stated |

Every other agency host is unchecked. Expect dozens of hosts, some third-party (Google Drive, Wix).

## Questions for the reviewer

1. May we collect, retain and quote Register PDFs and indexes, given no LCB terms? (yes/no)
2. May we read `notice.nv.gov` listings as the discovery surface for workshops and hearings? It has
   no robots file and no terms, and posting there is statutory. (yes/no)
3. Workshop and hearing notices mostly live on agency hosts, some of them third-party (Google Drive,
   Wix). Should a census check terms per host and skip restricted or third-party hosts as labelled
   gaps, or is NV out of scope for the pilot because of this? (per-host / out of scope)
4. Would we accept a "Register-only" narrowed claim, which would miss most workshop and hearing
   dates, or is that the easy-only conversion the plan forbids? (accept narrowed / reject)

## Provisional collection rule

- **Safe to begin now:** none beyond what is logged. NV is a research candidate only.
- **On reviewer yes to Q1–Q2:** Register indexes and PDFs and `notice.nv.gov` listing pages,
  sequential, identifying user agent, at least 5 seconds apart, stop on any 403/429. Poll the 4-week
  Latest Additions page at least every 3 weeks if collection starts, or reconcile from yearly indexes.
- **Blocked:** agency hosts until each one's terms are checked (Q3); third-party file hosts pending
  Q3.
