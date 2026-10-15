# State coverage pilot — access and rights summary (Phase 1, step 1)

Retrieved 2026-10-15. Per-state detail, verbatim quotes and URLs: [WA](WA.md), [CT](CT.md),
[VA](VA.md), [MA](MA.md), [TN](TN.md). Findings, not legal conclusions. "Provisional" means the
rule holds until the reviewer answers the questions below.

**Across all five states:** no source says anything about third-party processing (cloud PDF
parsers, LLM APIs). No source publishes an API or rate guidance; the only rate signal is VA Town
Hall's `Crawl-delay: 5`. Nowhere is retaining originals forbidden in so many words.

| State | Surface | Collect OK? | Retain originals? | Third-party processing? | Public display | Blockers |
|---|---|---|---|---|---|---|
| WA | State Register (`lawfilesext.leg.wa.gov`) | **Yes, provisional.** No robots.txt; free public access by statute (RCW 1.08.080) | Probably yes (inferred; statute promotes permanent access) | Not addressed | Link + excerpts probably fine; generic "All Rights Reserved" footer | None for collection; WA-Q2/Q3 |
| WA | Agency pages (Ecology sample) | Read for links only | Unclear ("all other uses prohibited") | Unclear | Links unrestricted; data with credit; **"political campaign or lobbying effort" use prohibited** | WA-Q4/Q5; other agencies unchecked |
| CT | eRegulations rendered pages | **Yes, provisional.** No robots.txt; statute requires public access (CGS § 4-173b) | Not addressed | Not addressed | Not addressed; portal disclaimer only | — |
| CT | `getOpenCommentPeriods` JSON route | **Hold** — undocumented, no support or stability promise | Not addressed | Not addressed | n/a | CT-Q1/Q2 |
| CT | CT Law Journal (`jud.ct.gov`) | Not needed now | — | — | — | robots.txt blocks AI/LLM crawlers (ClaudeBot, GPTBot etc.) |
| VA | Virginia Register (`register.dls.virginia.gov`) incl. RSS | **Yes, provisional.** No robots.txt; official RSS feed | Unclear ("All rights reserved" footer) | Not addressed | Link to official PDF; excerpts unclear | VA-Q3/Q4 |
| VA | Regulatory Town Hall | **Hold for `/L/` pages** — robots.txt `Disallow: /L./` may be a typo for `/L/`; `Crawl-delay: 5` | Not addressed | Not addressed | No advertising/endorsement use | VA-Q1/Q2 |
| MA | SOC public-hearings page + notice PDFs | **No.** Linked terms prohibit "scraping" or "crawling, whether by automated means or manually"; Incapsula bot protection | Unclear ("derivative works" clause) | Not addressed | Link only for now | MA-Q1–Q3 |
| MA | Massachusetts Register (paid) | **No** until subscription terms read; $225/yr online; electronic text "unofficial" | Unknown | Unknown | Unknown | MA-Q4 |
| MA | Agency pages on mass.gov | **Hold.** robots.txt unreadable (403) | Conflict: public record "any purpose" vs Commonwealth copyright "fair use" only | Not addressed | Fair use (comment, news, research) | MA-Q5 |
| TN | Administrative Register (`tnsos.org/rules/`, `publications.tnsosfiles.com`) | **Yes, provisional, attended only.** No reuse terms; "official publication"; CloudFront WAF in front | Probably yes (inferred) | Not addressed | Linking allowed "not ... within frames" | TN-Q2 for scheduled polling; TN-Q4 |
| TN | Agency pages on tn.gov | Allowed by robots.txt (`Allow: /`) | Not addressed | Not addressed | Not addressed | Not core |

## Consolidated questions for the reviewer

Cross-cutting (answer once):

- **X1.** May we send state notice documents (public, no stated restriction) to third-party
  processors — cloud PDF parser or LLM API — during Phase 1? (yes / no / only text we extract
  locally / decide per state)
- **X2.** What self-imposed rate applies where no guidance exists? (1 request per 5 s, matching VA
  Town Hall / 1 per second / other)
- **X3.** Default public display for state evidence: (link only / link + short factual excerpt /
  full document mirror)
- **X4.** Should we contact the operating office before scheduled collection where the access
  model is unclear (CT JSON, VA Town Hall, TN WAF, MA)? (yes for all / only MA / no)

Per state (full wording in each file):

- **WA-1/2.** Treat Register filings as free to collect, retain and quote despite the generic
  "All Rights Reserved" footer? (yes/no)
- **WA-4/5.** Is helping the public comment "lobbying" under Ecology's terms, and should agency
  pages be pointers only? (yes/no each)
- **CT-1/2.** Poll the undocumented JSON route, and e-mail `Eregs.Support@ct.gov` first?
  (yes/no each)
- **CT-3.** Subscribe to the statutory e-mail notifications as a cross-check? (yes/no)
- **CT-5.** Does `jud.ct.gov`'s AI-crawler block apply to LLM-driven fetching by us? (yes/no)
- **VA-1.** Read Town Hall `Disallow: /L./` literally or as `/L/`? (literal / `/L/` / ask DPB)
- **VA-3/4.** Does the Register's "All rights reserved" limit internal retention or short public
  excerpts? (yes/no each)
- **VA-6.** Make the Register RSS the primary VA discovery route? (yes/no)
- **MA-1/2/3.** Does the SOC scraping ban cover the hearings page; ask SOC for permission; is
  manual review acceptable meanwhile? (yes/no each)
- **MA-4.** Buy the $225/yr online Register after reading its subscriber agreement? (yes/no)
- **MA-5.** Are mass.gov hearing notices "any purpose" public records or fair-use-only? (choose)
- **MA-7.** Deprioritise MA as a pilot candidate given the above? (yes/no)
- **TN-2.** Ask the Division of Publications about an allowed rate before scheduled polling?
  (yes/no)
- **TN-5.** Use `PendingRules.php` as the surface for comment windows without a hearing? (yes/no)

## Provisional collection rule (all states)

- **Can begin now, attended, sequential, identifying user agent, ≥5 s between requests, stop on
  403/429:** WA Register; CT eRegulations rendered pages; VA Register (RSS + linked documents);
  TN T.A.R. tables and filing PDFs. Keep originals and hashes internally. Public display = link
  to the official source.
- **Blocked pending reviewer:** all third-party processing (X1); CT JSON polling; VA Town Hall
  `/L/` pages; everything automated in MA; mass.gov; unattended TN polling; agency-page
  collection beyond link discovery; public excerpts beyond facts and dates.
- **Never:** circumvent bot protection or WAFs; collect public comments or commenter personal
  data; put credentials in files.

## Could not access

- `sec.state.ma.us` blocks plain HTTP clients and the AI fetch tool (Incapsula). A headless
  browser was refused on the first request and then loaded the terms, about-register and hearings
  pages. No further MA requests were made after that.
- `mass.gov/robots.txt`: 403 to every client tried except a browser (not retried in a browser).
- MA Register subscriber agreement: behind account creation; not read.
- `tnsos.org/robots.txt`: CloudFront 403 "Request blocked".
- Only one WA agency (Ecology) and no CT, VA, MA or TN agency terms beyond portal-level pages were
  checked.
