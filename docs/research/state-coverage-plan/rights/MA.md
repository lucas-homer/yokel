# MA — access and rights check (Phase 1, step 1)

Retrieved 2026-10-15. Terms, legal, about, robots and one index page (public hearings). No notices
or PDFs collected.
Confidence: **stated** / **inferred** / **unknown**. Nothing here is a legal conclusion.

**Access note.** `www.sec.state.ma.us` sits behind Imperva/Incapsula bot protection. Plain HTTP
clients (curl) and an AI fetch tool got "Request unsuccessful. Incapsula incident ID …" pages. A
headless browser was blocked on the first request and then allowed on later ones. `www.mass.gov`
returned 403 to curl and the fetch tool, even for robots.txt, but loaded in the headless browser.
The site is actively filtering automated clients.

## Surfaces

1. **SOC "Notices of Public Review of Prospective Regulations"** page
   (`www.sec.state.ma.us/divisions/pubs-regs/public-hearings.htm`). Bi-weekly lists with notice
   PDFs (571 PDF links on the page, all on the same host) and "Accessible web version" HTML pages
   under `/divisions/pubs-regs/hearings/html/`. Header: "Published in compliance with M.G.L.
   c.30A, s.2 and s.3."
2. **Massachusetts Register** (paid; print is official). Online subscription via a login.
3. **Agency pages on `mass.gov`** (agencies post their own hearing notices). Governed by the
   Mass.gov Terms of Use.

### 1. SOC public-hearings page

| Field | Finding | Evidence | Confidence |
|---|---|---|---|
| Terms | The page footer links "Terms and Conditions" (`/divisions/terms.htm`). That page **prohibits scraping and crawling, automated or manual**. Its "Acceptable Use" text is written around business records and filings, so whether it is meant to cover publication pages is unclear — but it is linked from this page. Copyright footer: "© 2026 Secretary of the Commonwealth of Massachusetts." | "Prohibited Activities ... “Scraping” or “crawling,” whether by automated means or manually, to access, view, or collect information is prohibited." "Acceptable Use: This website may be used only for lawful purposes, and in accordance with these terms to search individual business records, to submit filings on behalf of your organization or another entity which has authorized you to do so." "WARNING: By accessing this website, you consent to system monitoring for law enforcement and other purposes. Unauthorized use of or access to the site may subject you to criminal prosecution and penalties." "Reverse-engineering, disassembling, decompiling, modifying, or creating derivative works is prohibited by applicable law." (https://www.sec.state.ma.us/divisions/terms.htm) | stated (text, footer link); scope **unknown** |
| Collection method and rate | robots.txt allows `/divisions/pubs-regs/` (it disallows `/Pubs`, `/Publications`, `/Bookstore`, `/search`, `/spr` and others). But the terms prohibit scraping, and bot protection blocks automated clients. No API, feed or rate guidance found. | https://www.sec.state.ma.us/robots.txt; terms above | stated; **conflict** between robots.txt and terms |
| Retain originals | Not addressed directly. "creating derivative works is prohibited" may bear on derived records. | terms above | unknown |
| Third-party processing | Not addressed. | — | unknown |
| Public display | Not addressed; copyright footer only. Linking is not restricted on this page. | — | unknown |

### 2. Massachusetts Register (paid)

| Field | Finding | Evidence | Confidence |
|---|---|---|---|
| Terms | Paid. Print: $300/yr, $15/issue. Online: $225/yr via account. **Electronic text is unofficial.** Statute lets the Secretary set prices outside normal public-document fees. Subscriber agreement terms not seen (behind account creation). | "Print: Annual subscriptions cost $300. Single issues cost $15. Online: Annual subscriptions costs $225." "Any text published in electronic versions of the Register is unofficial and for informational purposes only." (https://www.sec.state.ma.us/divisions/pubs-regs/about-register.htm). M.G.L. c.30A § 6: "The prices to be charged for the Massachusetts Register may be set without reference to the statutory charges for public documents fixed by chapter two hundred and sixty-two." It must publish "all notices filed in accordance with sections two and three, except that the secretary may summarize the content of any notice filed" (https://malegislature.gov/Laws/GeneralLaws/PartI/TitleIII/Chapter30A/Section6) | stated; subscriber terms **unknown** |
| Collection method and rate | Login and payment required. Online Register search at `/reg_pub/` (login). Robots.txt disallows `/Bookstore`. Automated access almost certainly governed by the subscriber agreement and the scraping ban. | as above | stated (paywall); inferred (automation barred) |
| Retain originals | Unknown until the subscriber agreement is read. | — | unknown |
| Third-party processing | Unknown until the subscriber agreement is read. | — | unknown |
| Public display | Unknown; likely restricted for a paid product. | — | unknown |

### 3. Agency pages on mass.gov

| Field | Finding | Evidence | Confidence |
|---|---|---|---|
| Terms | Mixed. Public records "can be copied and used for any purpose", and "all laws and regulations are public record". But the Commonwealth claims copyright in "most of the content on Mass.gov" and allows only fair use without permission. Agencies may add their own terms. | "All of the material posted on the Commonwealth's websites and available to the public without use of an authenticating and authorizing mechanism (such as a "PIN" or password) is public record. Most of the public record posted on Commonwealth websites can be copied and used for any purpose. For example, all judicial opinions and all laws and regulations are public record." "With respect to material in which the Commonwealth holds the copyright, including the design, layout, and other features of Mass.gov, and most of the content on Mass.gov, the Commonwealth forbids any copying or use other than "fair use" under the Copyright Act. "Fair use" includes activities such as criticism, comment, news reporting, teaching, research, and other related activities." "If you want to make use other than "fair use" of any information on this website, you must seek permission directly from Mass.gov" (https://www.mass.gov/massgov-terms-of-use) | stated; the two passages conflict for hearing notices — **unknown** which governs |
| Collection method and rate | robots.txt could not be read (403 to non-browser clients). No scraping clause in the Mass.gov terms. | https://www.mass.gov/robots.txt → 403 | unknown |
| Retain originals | Unclear (see conflict above). | — | unknown |
| Third-party processing | Not addressed. | — | unknown |
| Public display | Fair use (comment, news reporting, research) permitted; beyond that needs permission. | as above | stated |

## Questions for the reviewer

1. Does the SOC "Terms and Conditions" scraping ban apply to the public-hearings page and its
   notice PDFs? (yes / no / ask SOC in writing)
2. If unclear, should we write to the SOC Publications & Regulations Division to ask for
   permission for low-rate automated collection of the hearings page? (yes/no)
3. Until answered, is **manual** human review of the hearings page acceptable for the Phase 1
   census? The terms say scraping "whether by automated means or manually" is prohibited.
   (yes/no)
4. Should we buy an online Register subscription ($225/yr) for lawful reference access to resolve
   the denominator, after reading its subscriber agreement? (yes/no)
5. Are hearing notices on mass.gov "public record ... used for any purpose" or Commonwealth
   copyright limited to fair use? (public record / fair use only / ask)
6. May any MA document be sent to third-party processors (cloud PDF parser, LLM API)? (yes / no /
   after Q1 and Q5)
7. Given the scraping ban and bot protection, should MA be deprioritised as a pilot candidate?
   (yes/no)

## Provisional collection rule

- **Safe to begin now:** nothing automated. Reading the terms, the Register price page and M.G.L.
  c.30A (on `malegislature.gov`, robots.txt `Disallow:` empty) is fine. Linking to SOC and
  mass.gov pages is fine.
- **Blocked pending reviewer:** any automated or bulk collection from `sec.state.ma.us` (Q1–3);
  bypassing bot protection (never — do not use headless browsers or other tools to get around
  Incapsula); Register access (Q4); mass.gov collection (Q5); third-party processing (Q6).
