# CT — access and rights check (Phase 1, step 1)

Retrieved 2026-10-15. Terms, legal and index pages only; one request to the JSON endpoint to
check its access model (headers + first bytes, not stored). No notices collected.
Confidence: **stated** / **inferred** / **unknown**. Nothing here is a legal conclusion.

## Surfaces

1. **Connecticut eRegulations System** (`eregulations.ct.gov`), maintained by the Secretary of
   the State. Includes the rendered "Regulations Open For Comment" list, public notices,
   regulation-making records, and the undocumented JSON route
   `/eRegsPortal/Browse/getOpenCommentPeriods`. This is the authoritative surface.
2. **CT.gov portal policies** (`portal.ct.gov`), linked from the eRegulations footer as
   "POLICIES". Applies by reference.
3. **Connecticut Law Journal** (`jud.ct.gov`), possible secondary surface for hearings. Only its
   robots.txt was checked.

### 1. eRegulations System (including the JSON route)

| Field | Finding | Evidence | Confidence |
|---|---|---|---|
| Terms | No eRegulations-specific terms of use. The site is the official record by statute, which requires it to be "easily accessible to and searchable by the public". Footer links to CT.gov policies (see surface 2). | CGS § 4-173b(a): "The eRegulations System shall be easily accessible to and searchable by the public and shall enable members of the public to request and receive an electronic notification when an agency posts a notice of intent to adopt regulations" (https://www.cga.ct.gov/current/pub/chap_054.htm#sec_4-173b). Official Version Statement: "Effective July 1, 2017, the Connecticut eRegulations System shall serve as the official version of the Regulations of Connecticut State Agencies and the electronic repository for the regulation-making record." (https://eregulations.ct.gov/eRegsPortal/Information/GetContent?id=BetaNote) | stated |
| Collection method and rate | Public HTTP, no login. No robots.txt (404). The JSON route returns `application/json` without auth, with `Cache-Control: no-cache, no-store` and F5-style `TS…` cookies (bot-management/load-balancer; inferred). The route is not documented anywhere and has no support or stability promise. No rate guidance. Official alternative: the statutory e-mail notification service. | `https://eregulations.ct.gov/robots.txt` → 404. `GET /eRegsPortal/Browse/getOpenCommentPeriods` → 200 JSON. About Us gives a support contact: "eRegulations Division Phone: (860) 509-6099, Email: Eregs.Support@ct.gov" (https://eregulations.ct.gov/eRegsPortal/Information/GetContent?id=AboutUs) | stated (observed); unknown whether the JSON route is intended for outside use |
| Retain originals | Not addressed. | — | unknown (no restriction found) |
| Third-party processing | Not addressed. | — | unknown |
| Public display | Not addressed on eRegulations. See CT.gov disclaimer for data-use liability language. | — | unknown |

### 2. CT.gov portal policies (applies by footer link)

| Field | Finding | Evidence | Confidence |
|---|---|---|---|
| Terms | Disclaimer of warranty and liability; data "are not legal documents". No copyright or reuse licence for state content. Permission needed only for the state arms/seal; CT.gov logo is copyrighted. | "The State of Connecticut shall not be held liable for improper or incorrect use of the data described and/or contained within this web site. These data and related graphics are not legal documents and are not intended to be used as such." "This disclaimer applies both to individual use of the data and aggregate use with other data." "Please be advised that permission is required to reproduce the [state arms and seal]" (https://portal.ct.gov/policies/disclaimer) | stated |
| Collection method and rate | `portal.ct.gov/robots.txt` allows `/` except beta/admin paths. Does not cover the `eregulations.ct.gov` host. | https://portal.ct.gov/robots.txt | stated |
| Retain originals | Not addressed. "Aggregate use with other data" is contemplated, which suggests reuse is expected. | as above | inferred |
| Third-party processing | Not addressed. | — | unknown |
| Public display | No restriction found except the seal/logo. Note: "not legal documents" conflicts with § 4-173b making eRegulations the official compilation; the disclaimer is portal boilerplate. | as above | inferred |

### 3. Connecticut Law Journal host (`jud.ct.gov`) — robots only

| Field | Finding | Evidence | Confidence |
|---|---|---|---|
| Collection method | robots.txt explicitly disallows AI and LLM crawlers site-wide (GPTBot, ChatGPT-User, ClaudeBot, anthropic-ai, CCBot, PerplexityBot, Google-Extended and others). It allows `*` except a few paths. | https://www.jud.ct.gov/robots.txt | stated |
| Other fields | Not checked; out of Phase 1 need unless hearings cannot be found on eRegulations. | — | unknown |

## Questions for the reviewer

1. May we poll the undocumented JSON route `getOpenCommentPeriods` (and the detail/history JSON),
   given no terms and no robots.txt? (yes / yes at a stated rate / no — rendered pages only)
2. Should we e-mail `Eregs.Support@ct.gov` before relying on the JSON route, to ask whether
   automated use is acceptable and whether it is stable? (yes/no)
3. Should we also subscribe to the statutory e-mail notification service as an official,
   independent cross-check? (yes/no)
4. May we retain notice originals and send them to third-party processors (cloud PDF parser, LLM
   API)? (yes / no / local extraction only)
5. If we later use the Connecticut Law Journal, does its AI-crawler block apply to us when an
   LLM-driven agent fetches pages, even though our collector would use its own user agent?
   (treat as applying / not applying)

## Provisional collection rule

- **Safe to begin now:** rendered eRegulations pages (open-for-comment list, notice and history
  pages) at most 1 request per 5 seconds, sequential, identifying user agent. Retain bytes and
  hashes internally. Link to eRegulations for display.
- **Blocked pending reviewer:** scheduled polling of the JSON route (Q1–2); third-party processing
  (Q4); any `jud.ct.gov` collection by LLM-driven tools (Q5).
