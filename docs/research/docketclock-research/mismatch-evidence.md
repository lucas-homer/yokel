# Mismatch / data-quality evidence for docket deadline tracking

**Research value: high** -- Authoritative ACUS/GAO material plus Federal Register examples show real data-quality pain, while developer/API docs expose concrete field, timezone, pagination, and identifier traps.

## Documented facts

### 1) Regulations.gov, FederalRegister.gov, and Reginfo.gov are only partially interoperable

ACUS Recommendation 2018-6 states that FDMS/Regulations.gov receives a daily Federal Register data feed, but lifecycle linking depends on agencies entering identifiers correctly: Regulations.gov Document Number, RIN, and Federal Register Document Number. ACUS warns that if identifiers are missing or incorrect, users may have difficulty discerning rulemaking context. It also notes one docket can contain multiple Federal Register document numbers, while a single rulemaking can have multiple e-dockets.

Concrete documented problems:

- Agencies sometimes create **multiple e-dockets for the same rulemaking**; a user may find the NPRM docket and incorrectly conclude no final rule was issued.
- Parent/sub-agency splits can create separate dockets for one lifecycle.
- Document Type labels are used inconsistently: one agency may label an ANPRM as “Notice,” another as “Proposed Rule.”
- Searching a parent agency may not include sub-agency results, causing false negatives.
- Missing/incorrect RINs prevent Unified Agenda context from appearing in Regulations.gov.

Source: ACUS, “Improving Access to Regulations.gov's Rulemaking Dockets,” 2018/2019.

### 2) Comment data has known limitations and agency-configurable fields

GAO found public comment data is not always fully described. In sampled rulemakings from 10 agencies, only 48% to 87% of commenters with email addresses confirmed they submitted the comments; 5% to 30% said they did not. At eight agencies, most comments lacked email addresses. GAO also found duplicate-comment posting practices vary, meaning public data may not include every instance of a mass/near-duplicate comment.

GSA’s Regulations.gov API page now explicitly warns that comment data has limitations and that “some data fields are managed solely by agencies.” It lists always-available comment fields versus agency-configured fields that agencies may make accessible or inaccessible at any point. Agency-configurable fields include firstName, lastName, organization, email, postmarkDate, state, zip, etc.

Sources: GAO-21-103181; GSA Regulations.gov API “Data Limitations.”

### 3) API schema and field semantics are ambiguous enough that developers ask for definitions

In a Federal Register API GitHub issue, a user asked for definitions of 40+ JSON fields. The maintainer replied: “We don't currently have such a document available” and said fields were intended to be self-explanatory. The user specifically listed fields relevant to docket clocks and mismatch handling: `comment_url`, `comments_close_on`, `correction_of`, `corrections`, `docket_ids`, `regulation_id_number_info`, `regulations_dot_gov_info`, and others.

Source: usnationalarchives/federalregister-api-core issue #9.

### 4) Regulations.gov API requires non-obvious joins and has timezone traps

GSA’s v4 API docs and an independent Python-wrapper writeup document several gotchas:

- Comments are associated with **documents**, not directly with dockets; to get docket comments, callers must fetch documents for the docket, then fetch comments for each document.
- Filtering comments for a specific document uses the internal `objectId`/`commentOnId`, not the public `documentId`.
- For >5,000 comments, callers must page by `lastModifiedDate`; GSA’s own example says response timestamps are UTC but the next filter converts to Eastern time.
- The API uses different date formats: `postedDate` filters use `yyyy-mm-dd`, while `lastModifiedDate` uses `yyyy-mm-dd hh24:mi:ss`.
- The independent wrapper warns this UTC-vs-Eastern mismatch can cause errors if unaware, and `>=` pagination creates duplicates that clients must dedupe.
- Detail records often require one API call per comment; rate limits can force long waits on large dockets.

Sources: GSA Regulations.gov API examples; Will Jobs, “Downloading public comments with a simple-to-use Python wrapper for the Regulations.gov API,” 2021.

### 5) Comment period status is dynamic: extensions, reopenings, corrections, and multiple deadlines are common

Concrete Federal Register examples:

- **EPA NPDES Multi-Sector General Permit**, Docket EPA-HQ-OW-2024-0481: original notice Dec. 13, 2024; extension Feb. 3, 2025; then comment period reopened to May 19, 2025 in response to stakeholder requests. A tracker that only reads the first notice or first extension would be stale.
- **PHMSA HM-265**, Docket PHMSA-2018-0080: Oct. 28, 2024 NPRM comment period extended 90 days to Apr. 28, 2025; notice says late-filed comments will be considered “to the extent possible,” creating a distinction between formal close date and practical late-comment policy.
- **EPA two-actions extension notice**, Feb. 21, 2025: one Federal Register notice extended two separate comment periods with different new deadlines: FRL 12023-01-OW to Apr. 25, 2025 and FRL-12451-01-OW to Apr. 16, 2025. This is a field-modeling challenge if a tracker assumes one notice = one deadline.
- **BLM Utah withdrawal notice**, Dec. 14, 2023: title includes “Extension, Public Meetings and Correction,” but the “extension” is a proposed public-land withdrawal extension, not a comment-period extension. This is a keyword false-positive risk for deadline parsers.
- **NPS Alaska hunting/trapping extension**, Apr. 10, 2026: comments received/postmarked by Apr. 24, 2026; electronic comments via Federal eRulemaking Portal must be received by 11:59 p.m. Eastern / 7:59 p.m. Alaska time. This documents timezone-specific close semantics.

Sources: Federal Register notices linked below.

### 6) Regulations.gov operational incidents can force comment-period extensions

HUD published a May 7, 2025 Federal Register extension for “Affirmatively Furthering Fair Housing Revisions” after a Regulations.gov migration around Apr. 28, 2025. HUD discovered public comments were not being updated and that the ability to submit comments “did not appear to be operational.” HUD extended the period seven days, from May 2 to May 9, 2025, for people who may have tried unsuccessfully to submit.

Source: 90 FR 19262-19263, FR Doc. 2025-07961.

### 7) FederalRegister.gov itself warns it is not the official legal edition

FederalRegister.gov API documentation says the site is an XML rendition/prototype informational resource, not an official legal edition, and users relying on it for legal research should verify against the official Federal Register edition on govinfo.gov until official status is granted. For a docket-clock product, this means FederalRegister.gov is convenient but not the final legal authority.

Source: Federal Register API documentation.

## Inferred risks for a docket-clock system

These are not direct claims by the sources, but follow from documented mechanics above:

- A single-source deadline from FederalRegister.gov can be stale when later extension/reopening/correction notices update the operative close date.
- A single-source deadline from Regulations.gov can be wrong or ambiguous if agency-managed metadata is missing, late-updated, or tied to the wrong document/object ID.
- Treating docket-level `commentEndDate` as authoritative is risky where multiple documents in one docket have distinct comment periods.
- Keyword classification (“extension,” “correction,” “reopening”) needs legal-context parsing because “extension” may modify a land withdrawal or permit term, not a comment deadline.
- Deadline display should preserve timezone and submission-channel differences: electronic receipt by 11:59 p.m. ET may differ from mail postmark rules and local-time wording.
- A robust tracker should reconcile Federal Register document chains, Regulations.gov docket/document metadata, RINs, docket IDs, FR document numbers, and official govinfo text; flag conflicts rather than silently choosing one.

## Sources consulted

- ACUS, “Improving Access to Regulations.gov's Rulemaking Dockets” — interoperability, multiple e-docket, inconsistent labels, identifier failures. https://www.acus.gov/document/improving-access-regulationsgovs-rulemaking-dockets
- GAO, “Federal Rulemaking: Selected Agencies Should Fully Describe Public Comment Data and Their Limitations” — identity/data limitations and recommendations. https://www.gao.gov/products/gao-21-103181
- GSA, “Regulations.gov API” — API structure, data limitations, agency-configurable fields, objectId/commentOnId, pagination/timezone example. https://open.gsa.gov/api/regulationsgov/
- Federal Register API documentation — unofficial informational status of FederalRegister.gov XML rendition. https://www.federalregister.gov/developers/documentation/api/v1
- Federal Register API GitHub issue #9 — lack of field-definition document for keys including comment/deadline/correction fields. https://github.com/usnationalarchives/federalregister-api-core/issues/9
- Will Jobs, “Downloading public comments with a simple-to-use Python wrapper for the Regulations.gov API” — practical API gotchas: UTC/Eastern mismatch, objectId joins, 5,000-result cap, rate limits, dedupe. https://willjobs.com/blog/downloading-public-comments
- HUD, “Affirmatively Furthering Fair Housing Revisions; Extension of Comment Period,” 90 FR 19262-19263 — Regulations.gov migration/submission outage led to extension. https://www.govinfo.gov/content/pkg/FR-2025-05-07/html/2025-07961.htm
- EPA, “NPDES 2026 Multi-Sector General Permit; Reopening of Comment Period” — chained original + extension + reopening to new close date. https://www.federalregister.gov/documents/2025/04/21/2025-06774/national-pollutant-discharge-elimination-system-npdes-2026-issuance-of-the-multi-sector-general
- PHMSA, “Hazardous Materials... Extension of Comment Period” — 90-day extension and late-filed-comments language. https://www.federalregister.gov/documents/2025/01/08/2024-31077/hazardous-materials-advancing-safety-of-highway-rail-and-vessel-transportation-extension-of-comment
- EPA, “Two Actions... Notice of Comment Period Extensions” — one notice, two original notices, two distinct new deadlines. https://www.federalregister.gov/documents/2025/02/21/2025-02910/two-actions-published-by-the-environmental-protection-agency-with-comment-periods-that-close
- BLM, “Notice of Proposed Withdrawal Extension, Public Meetings and Correction...” — “extension/correction” title not necessarily comment-period change. https://www.federalregister.gov/documents/2023/12/14/2023-27468/notice-of-proposed-withdrawal-extension-public-meetings-and-correction-for-segments-of-the-colorado
- NPS, “Alaska; Hunting and Trapping in National Preserves; Extension of Comment Period” — explicit electronic deadline timezone semantics. https://www.federalregister.gov/documents/2026/04/10/2026-07006/alaska-hunting-and-trapping-in-national-preserves-extension-of-comment-period
