# MS — access and rights check (backup hard candidate, ADR 0013 Amendment 1)

Retrieved 2026-10-15. Robots, disclaimer and index pages, two calls to the bulletin search service
that the SOS search page itself uses, and four one-page notice forms. 15 requests in total. Request
log: [`../census/BACKUP-HARD-CANDIDATE.md`](../census/BACKUP-HARD-CANDIDATE.md#request-log).
Confidence: **stated** = the source says it; **inferred** = my reading; **unknown** = not found.
Nothing here is a legal conclusion.

## Surfaces

1. **Mississippi Administrative Bulletin**, Secretary of State (SOS). The bulletin page on
   `www.sos.ms.gov` is an iframe around `www.sos.ms.gov/adminsearch/default.aspx?current_page=Bulletin`.
   That page has no server-rendered rows. Its own script (`Admin.js`) calls the ASP.NET service
   `AdminSearchService.asmx/BulletinSearch`, which returns `~`/`^`-delimited records (agency,
   withdrawn flag, proposed/final/effective/withdrawal dates, rule name, summary, filing ID, and the
   file names of the notice, economic impact statement and full-text PDFs). This is the authoritative
   surface. SOS calls itself "the official registrar for the rules of all state agencies".
2. **Filing PDFs** under `www.sos.ms.gov/adminsearch/ACProposed/<8-digit filing ID>{a,b}.pdf`:
   `a` = SOS APA Form 001 notice, `b` = full text. Static files, no login.
3. **Agency pages** (e.g. Division of Medicaid). Cross-check only; one sampled, see below.

### 1–2. Administrative Bulletin and filing PDFs (SOS)

| Field | Finding | Evidence | Confidence |
|---|---|---|---|
| Terms | No reuse licence and no copyright statement for bulletin content. The site disclaimer governs "all access to, and any use of" the site. It requires lawful use and prohibits use "for other than its intended purposes". It points to the Public Records Act for copies. | "All access to, and any use of, information contained in this website is governed by the following disclaimers and limitations on use. Users agree to use the SOS website solely for lawful purposes." "Requests to view documents or to obtain copies of documents should be made in accordance with the Mississippi Public Records Act of 1983 and the corresponding SOS policies and procedures." "Unauthorized attempts to modify any information stored on this site, to defeat or circumvent security features, or to utilize this site for other than its intended purposes are prohibited." (https://www.sos.ms.gov/disclaimer) | stated; **inferred** that reading the public bulletin at 1 req/5 s is an intended purpose, given the service's stated purpose ("allows you to conduct a search ... of the rules ... which have been proposed for public comment") |
| Official status | SOS is the official registrar and publisher of the bulletin. Electronic copies may differ from printed versions. | "The Mississippi Secretary of State's Office is the official registrar for the rules of all state agencies and the publisher of the Mississippi Administrative Bulletin." (`Admin.js`, rendered on the bulletin page). "electronic versions of documents appearing on this site may not display the text of these documents exactly as the printed versions." (disclaimer) | stated |
| Collection method and rate | Public HTTP, no login. `robots.txt` is the stock Drupal file. It disallows only admin, search, user and core paths, so `/adminsearch/` and `/adminsearch/ACProposed/` are not disallowed. Note that `/search/` is disallowed but `/adminsearch/` is a different path. No API documentation, feed or rate guidance. **Cloudflare is in front**: the search page embeds Cloudflare's passive `/cdn-cgi/challenge-platform/` script. None of our 15 requests was challenged or refused. The service call is the same POST the page's search button sends. | https://www.sos.ms.gov/robots.txt (200); https://www.sos.ms.gov/adminsearch/default.aspx?current_page=Bulletin (page source); https://www.sos.ms.gov/adminsearch/AdminSearchService.asmx/js (method signature `BulletinSearch(tmpAgency, tmpRuleSum, tmpOrder, tmpOrderDirec, tmpTypeF, tmpSearchDate1, tmpSearchDate2, tmpDateType, pageNum, numberToDisplay)`) | stated (robots, observed); rate **unknown**; whether the service route is acceptable is **unknown**, the same position CT's JSON route was in before DECISIONS item 7 |
| Retain originals | Not addressed. Nothing forbids keeping copies. | disclaimer above | inferred |
| Third-party processing | Not addressed by SOS. DECISIONS item 1 already allows openly published state notices to go to LlamaParse and LLM APIs. These forms are public and need no login. | DECISIONS.md item 1 | stated (our rule); unknown (SOS view) |
| Public display | Linking not addressed for SOS's own pages. The disclaimer disclaims accuracy. Nothing on quoting. | "the SOS ... expressly deny any warranty of the accuracy, adequacy, completeness, legality, reliability, or usefulness of any information published by this system" (disclaimer) | unknown (quoting); stated (accuracy disclaimer) |

### 3. Agency pages (sample: Division of Medicaid)

| Field | Finding | Evidence | Confidence |
|---|---|---|---|
| Terms | Not found. The homepage menu is script-rendered and the static HTML exposes no policy link. | https://medicaid.ms.gov/ | unknown |
| Collection method and rate | `robots.txt` returns 404. The only rulemaking link in the static homepage is "Administrative Code", and it points back to `sos.ms.gov`. | https://medicaid.ms.gov/robots.txt (404); homepage link to https://www.sos.ms.gov/regulation-enforcement/administrative-code | stated (observed) |
| Independent lineage | Not established. The one agency sampled defers to the SOS bulletin. | as above | inferred |

## Questions for the reviewer

1. May we collect, retain and quote MS bulletin records and notice PDFs, given the "lawful purposes" /
   "intended purposes" disclaimer and no reuse terms? (yes/no)
2. May we read the bulletin through the `AdminSearchService.asmx/BulletinSearch` POST that the
   SOS search page itself sends, at 1 request / 5 s? There is no server-rendered alternative. This
   is the same question as CT item 7. (yes / no / ask SOS first)
3. Cloudflare fronts the site. Should we ask SOS for a rate or an allow-listed user agent before
   scheduled polling, as with TN? (yes/no)
4. Miss. Code Ann. § 25-43-3.104 sets the 25-day comment period and 20-day oral-proceeding request
   window that the form describes. Is a read-only statute lookup on a Mississippi code host allowed,
   like DECISIONS item 6 for WA and VA? (yes/no; host to be named)
5. Agency pages give no independent lineage in the one sample. Should MS be accepted as
   single-lineage with the filing-ID sequence as the completeness check (see the census note)?
   (yes / no / sample more agencies first)

## Provisional collection rule

- **Safe to begin now:** none beyond what is logged. MS is a research candidate only, and the
  Amendment 1 rights check is this file.
- **On reviewer yes to Q1–Q2:** bulletin service queries by date window and the linked
  `ACProposed/*a.pdf` notice forms (and `*b.pdf` full text only where the form refers to it),
  sequential, identifying user agent, at least 5 seconds apart, stop on any 403/429 or Cloudflare
  challenge page. Retain bytes and hashes internally. Display = link plus the short sentence that
  sets the window.
- **Blocked:** any request that meets a Cloudflare challenge (never solve or evade it); scheduled
  polling until Q3 is settled; statute lookups until Q4; agency pages beyond pointer use until their
  terms are read.
