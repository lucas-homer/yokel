# WA — access and rights check (Phase 1, step 1)

Retrieved 2026-10-15. Terms, legal and index pages only; no notices collected.
Confidence: **stated** = the source says it; **inferred** = my reading; **unknown** = not found.
Nothing here is a legal conclusion.

## Surfaces

1. **Washington State Register (WSR)**, published by the Code Reviser's Office (Statute Law
   Committee). Hosts: `leg.wa.gov` (landing), `lawfilesext.leg.wa.gov` (issue indexes, HTML and
   certified PDF filings), `app.leg.wa.gov` (RCW/WAC lookup). This is the authoritative surface.
2. **Agency rule-making pages** (e.g. `ecology.wa.gov`). One agency sampled (Ecology). Terms vary
   by agency.

### 1. Washington State Register

| Field | Finding | Evidence | Confidence |
|---|---|---|---|
| Terms | No terms of use or reuse licence for the Register. A statute requires free permanent public access. The site disclaimer warns only about RCW/WAC *resale*, not the Register. | RCW 1.08.080: "Current digital copies of the Revised Code of Washington, the Washington Administrative Code, the Washington State Register, and the session laws ... shall be maintained and made freely available for permanent public access on the code reviser or legislative website." (https://app.leg.wa.gov/RCW/default.aspx?cite=1.08.080). Disclaimer: "Any user intending to obtain the Revised Code of Washington or the Washington Administrative Code for the purpose of selling the same is advised to contact the Washington State Statute Law Committee, which claims copyright for both codes" (https://leg.wa.gov/disclaimer/). Footer on every page: "© Copyright 2026. All Rights Reserved." | stated (statute, disclaimer); inferred that the copyright claim on codes does not extend to Register notices — the footer is generic and ambiguous |
| Official version | The certified PDFs on the Code Reviser site are the official Register. | "The Statute Law Committee declares that the certified PDF Register documents on the Code Reviser's website constitute the official publication of the Washington State Register." (https://leg.wa.gov/state-laws-and-rules/washington-state-register/); also https://leg.wa.gov/media/lklg25lk/officialstatement.htm | stated |
| Collection method and rate | Public HTTP, no login, no paywall. No robots.txt (404 on `leg.wa.gov`, `lawfilesext.leg.wa.gov`, `app.leg.wa.gov`). No published API or rate guidance for the Register. Issue indexes are static HTML (`WsrByIssue.htm`, `WSRDocsByType26.htm`). | robots.txt fetches returned 404 on all three hosts. Index links at https://leg.wa.gov/state-laws-and-rules/washington-state-register/ | stated (absence observed); rate is unknown — use a conservative self-imposed limit |
| Retain originals | Nothing found that forbids keeping copies. The statute's purpose is "permanent public access". | RCW 1.08.080 above | inferred |
| Third-party processing (cloud parser / LLM API) | Not addressed anywhere. | — | unknown |
| Public display | Nothing restricts linking or quoting. The disclaimer disclaims accuracy: "Neither the State of Washington nor any agency ... warrants the accuracy, reliability, or timeliness of any information in the Public Access System". | https://leg.wa.gov/disclaimer/ | inferred for quoting/republishing; stated for the accuracy disclaimer |

### 2. Agency rule-making pages (sample: Department of Ecology)

| Field | Finding | Evidence | Confidence |
|---|---|---|---|
| Terms | Restrictive. Content is claimed as Ecology's copyright; **commercial and political use, including "any use in a political campaign or lobbying effort", is prohibited**. Data use is allowed with credit and a link. | "The Material on the website is intended for users' educational or research purposes. Commercial and political use of any Ecology Material are specifically prohibited. This restriction includes any commercial publication of material and any use in a political campaign or lobbying effort for any person, party or ballot measure." "Use of data from Ecology's web sites — provided the Washington State Department of Ecology is credited as the data provider and a link is provided to the Ecology data source web page." "All other uses of Material from Ecology's websites are prohibited without prior express written authorization from Ecology." (https://ecology.wa.gov/about-us/accountability-transparency/website-information/copyright-information) | stated |
| Collection method and rate | robots.txt allows public pages (disallows only `/admin`, `/Special-Pages`, shared assets). No rate guidance. | https://ecology.wa.gov/robots.txt | stated |
| Retain originals | Not addressed; "all other uses ... prohibited without prior express written authorization" could be read to cover it. | as above | unknown |
| Third-party processing | Not addressed; same catch-all applies. | as above | unknown |
| Public display | Linking "unrestricted". Data use with credit + link. Republishing text is not clearly allowed. | as above | stated (links, data); unknown (text excerpts) |

Other agencies' terms were not checked. Expect variation.

## Questions for the reviewer

1. May we treat Register filings (notices on `lawfilesext.leg.wa.gov`) as free to collect, retain
   and quote, given RCW 1.08.080 and no Register-specific terms? (yes/no)
2. Does the generic "© Copyright 2026. All Rights Reserved." footer on `leg.wa.gov` change that
   answer? (yes/no)
3. May we send Register PDFs/HTML to third-party processors (cloud PDF parser, LLM API) during
   Phase 1 research? (yes / no / only text we have extracted locally)
4. Ecology prohibits "use in a political campaign or lobbying effort". Is helping members of the
   public comment on a rule "lobbying" for this purpose? (yes / no / ask Ecology in writing)
5. Should agency pages be used only as links and pointers, with the Register as the sole
   evidence source? (yes/no)
6. What request rate should we self-impose where no guidance exists? (choose: 1 req/5 s /
   1 req/s / other)

## Provisional collection rule

- **Safe to begin now:** Register issue indexes and individual Register filings on
  `lawfilesext.leg.wa.gov`, sequential requests, identifying user agent, at most 1 request per
  5 seconds (self-imposed). Retain bytes and hashes internally. Store links to the official
  certified PDF.
- **Blocked pending reviewer:** third-party processing (Q3); any public display beyond a link plus
  short factual excerpt (Q1–2); collection from agency pages beyond reading them to find links
  back to the Register (Q4–5); any agency whose terms have not been checked.
