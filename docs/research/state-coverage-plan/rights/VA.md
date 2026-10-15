# VA — access and rights check (Phase 1, step 1)

Retrieved 2026-10-15. Terms, legal, about, robots and two index pages (Town Hall forums list,
Register RSS subscribe page). No notices collected.
Confidence: **stated** / **inferred** / **unknown**. Nothing here is a legal conclusion.

## Surfaces

1. **Virginia Regulatory Town Hall** (`townhall.virginia.gov`), run by the Department of Planning
   and Budget (DPB). Actions, stages (incl. NOIRA), comment forums, meetings. Executive branch
   focus: "This website focuses on executive branch agencies. Information about other agencies is
   available at Virginia Register of Regulations" (https://townhall.virginia.gov/).
2. **Virginia Register of Regulations** (`register.dls.virginia.gov`), Virginia Code Commission
   and DLAS. The authoritative, official publication. Has an RSS feed (`/rss.aspx`).
3. **Code of Virginia** (`law.lis.virginia.gov`), only for statutes cited below.

### 1. Virginia Regulatory Town Hall

| Field | Finding | Evidence | Confidence |
|---|---|---|---|
| Terms | "Web policies" page: disclaimer, no copyright or reuse licence. Prohibits use "for other than its intended purposes" (undefined) and use for advertising or implying endorsement. Policies are "not ... a contract". | "Unauthorized attempts to modify any information stored on this system, to defeat or circumvent security features, or to utilize this system for other than its intended purposes are prohibited and may result in criminal prosecution." "The information and statements contained on this server shall not be used for the purposes of advertising, nor to imply the endorsement or recommendation of the Commonwealth of Virginia." "The following is not intended and should not be interpreted as a contract of any nature" (https://townhall.virginia.gov/policies.cfm) | stated |
| Collection method and rate | Public HTTP, no login for reading. robots.txt sets **Crawl-delay: 5**. It disallows `/L./`, `/l./` and `//`. Literally, `/L./` does not match the real listing paths (`/L/Forums.cfm` etc.); it may be a typo for `/L/`, which would block every listing page. No API or feed found on the forums page. Official alternative: registered-public e-mail notifications. | https://townhall.virginia.gov/robots.txt: "User-agent: * / Crawl-delay: 5 / Disallow: /L./ / Disallow: /l./ / Disallow: //". Home page: "Register as a public user - Receive emails when regulatory actions or meetings" | stated (file contents); the intent of `/L./` is **unknown** |
| Retain originals | Not addressed. | — | unknown (no restriction found) |
| Third-party processing | Not addressed. | — | unknown |
| Public display | Not addressed beyond the no-advertising/no-endorsement line. Note: the Town Hall also hosts public comments with personal data (name, e-mail, organisation are shared with agencies per the privacy policy); those are out of scope and should not be collected. | policies.cfm privacy section | inferred |

### 2. Virginia Register of Regulations

| Field | Finding | Evidence | Confidence |
|---|---|---|---|
| Terms | No terms of use page. Footer claims copyright. Statute requires publication on the Code Commission website; the Commission may arrange paid print editions. | Footer: "© Copyright Commonwealth of Virginia, 2013-2026. All rights reserved." Home: "The PDF version of the Virginia Register of Regulations posted on this site is the official legal resource (§ 2.2-4031 C of the Code of Virginia)." (https://register.dls.virginia.gov/). § 2.2-4031 C: "The Virginia Register of Regulations shall be published by posting the Register on the Virginia Code Commission's website." (https://law.lis.virginia.gov/vacode/title2.2/chapter40/section2.2-4031/). § 30-146 lets the Commission arrange for the Register to be "printed and published ... and sold" (https://law.lis.virginia.gov/vacode/title30/chapter19/section30-146/) | stated |
| Collection method and rate | Public HTTP, no login. No robots.txt (404). Official RSS 2.0 feed at `/rss.aspx` (HTTP 200, `text/xml`, ~134 KB). No rate guidance. | https://register.dls.virginia.gov/subscribe.aspx ("RSS 2.0 Link" → rss.aspx); robots.txt → 404 | stated |
| Retain originals | Not addressed. The "All rights reserved" footer is the only signal. | as above | unknown |
| Third-party processing | Not addressed. | — | unknown |
| Public display | Not addressed. Linking to the official PDF is the conservative choice. Paid print editions (§ 30-146) suggest the state sells copies, but the online version is the official one by statute. | as above | inferred |

## Questions for the reviewer

1. Town Hall robots.txt says `Disallow: /L./`. Do we read it literally (listing pages under `/L/`
   allowed) or as intending `/L/` (listing pages disallowed, so we must use the Register RSS and
   e-mail alerts instead)? (literal / intended `/L/` / ask DPB)
2. Should we e-mail DPB (Town Hall webmaster) to ask about automated access before collecting?
   (yes/no)
3. Does "All rights reserved" on the Virginia Register affect retaining PDFs internally? (yes/no)
4. Does it affect quoting short excerpts publicly with a link? (yes/no)
5. May we send Town Hall or Register documents to third-party processors (cloud PDF parser, LLM
   API)? (yes / no / local extraction only)
6. Is the Register RSS feed the preferred primary discovery route for VA? (yes/no)

## Provisional collection rule

- **Safe to begin now:** the Register RSS feed and Register HTML/PDF documents it links, sequential,
  identifying user agent, at least 5 seconds between requests (adopting Town Hall's crawl-delay
  as the state norm). Retain bytes and hashes internally only. Display = link to the official PDF.
- **Also safe:** Town Hall pages *outside* `/L/` (none needed so far), with Crawl-delay 5.
- **Blocked pending reviewer:** Town Hall `/L/` listing and forum pages (Q1–2); third-party
  processing (Q5); public excerpts beyond facts and dates (Q3–4). Never collect public comments or
  commenter details.
