# Prior art / competitors: Federal Register + Regulations.gov comment-period tracking

**Research value: high** -- There are many deadline/status trackers and API wrappers, but I found **no clear product that explicitly reconciles Federal Register `comments_close_on` vs Regulations.gov `commentEndDate/openForComment` discrepancies with provenance/confidence**; the closest competitors expose single-source deadlines, alerts, feeds, or workflow integrations.

## Executive assessment

| Offering | Directness | Source(s) used | Deadline/status support | Reconciliation? | API/feed/webhook? |
|---|---:|---|---|---|---|
| **FRTracker** | High | FederalRegister.gov API, eCFR, Regulations.gov for comments | Open-comment pages, calendar, deadlines, comment status | **Partial adjacency**: links FR docs to Regulations.gov comments; methodology/provenance strong, but no stated FR-vs-Regulations.gov deadline conflict resolver | Public API; RSS feeds; alerts mention email/webhook |
| **Apify Federal Register Monitor** | Medium-high | Federal Register API | `commentDeadline`, `isCommentOpen`, `daysUntilCommentClose`; filters for open/closing comments | No; FR-only | Apify API, scheduler, Zapier/Make, webhooks, email alerts |
| **Apify Regulations.gov Scraper/Crawler** | Medium-high | Regulations.gov v4 API | `commentEndDate`, `openForComment`, `withinCommentPeriod`, `allowLateComments` | No; Regulations.gov-only | Apify API, scheduler, Slack/webhook/Zapier/Make integrations |
| **GSA / Microsoft Power Platform connector** | Medium | Regulations.gov API | Exposes document fields incl. `commentEndDate`, `commentStartDate`, `openForComment`, `withinCommentPeriod`, `allowLateComments` | No; connector to one source | Power Automate/Logic Apps actions; no native reconciliation |
| **Apogee Regulatory Intelligence** | Medium | Federal Register API | Natural-language Federal Register search with open-comment status/deadlines | No; FR-only | Product docs do not expose public API/webhook specifics for this capability |
| **Federal Register API / Regulations.gov API** | Infrastructure | Official sources | FR: `comments_close_on`; Regs.gov: `commentEndDate/openForComment/withinCommentPeriod` | No; raw systems of record | REST APIs; no deadline webhook/feed by themselves |
| **Open-source wrappers / MCPs** | Adjacent | One official API each | Search/comment-period tracking fields | No | Code/API wrappers; typically no feeds/webhooks |

## What exists

### 1) FRTracker — strongest direct prior art, but not a docket-deadline reconciler

FRTracker is the most directly competitive product surface: it has open comment period pages, a compliance calendar, feeds, alerts, API, and explicit methodology/provenance.

**Evidence snippets**

- Product/search page: “**988,406 FR documents · 7,137 CFR parts · 1,398,393 obligations extracted · 1080 open for comment**”; “Create alerts for agencies, rules, searches, and comment periods. Get daily or weekly email digests when things change.” It also labels data “**sourced from eCFR and federalregister.gov. Updated hourly**.” URL: https://frtracker.app/search
- Methodology: “All data comes from official U.S. government sources: **eCFR** … **Federal Register** … via federalregister.gov API”; “**Comment period tracking with open/closed status**”; “FRTracker indexes public comments submitted through **Regulations.gov**.” URL: https://frtracker.app/methodology
- Comment data provenance/limitations: “Comment metadata and text are retrieved from the **Regulations.gov public API**”; comment dataset is “**partial**”; comment counts “should not be cited as complete counts.” URL: https://frtracker.app/methodology
- API docs: endpoints include `/api/fr-docs`, `/api/export/fr-docs`, `/api/export/comments?doc={document_number}`, `/api/comments/export.csv?doc={document_number}`; response includes `_meta.source = frtracker.app`. URL: https://frtracker.app/developers
- Signals/feeds: search results show “Regulatory Signals … **RSS Feed**” and Daily Briefing says “**subscribe via RSS feed**.” URLs: https://frtracker.app/signals, https://frtracker.app/briefing

**Assessment**

- **Directness:** High for tracking comment periods and alerts; high for provenance discipline.
- **Sources:** FederalRegister.gov + eCFR for FR/CFR; Regulations.gov for comments.
- **Reconcile?** I found no explicit claim that it compares FR `comments_close_on`/DATES text against Regulations.gov `commentEndDate/openForComment`, detects mismatches, or emits confidence for deadline truth. Its provenance is stronger around obligations, comments, and content hashes than around deadline discrepancy resolution.
- **API/feed:** Yes: public/authenticated API; RSS feeds; alert UI suggests email and webhook options.

### 2) Apify actors — many single-source deadline monitors with webhook plumbing

Apify has multiple actors wrapping either Federal Register or Regulations.gov. They are operationally close because Apify adds scheduling, dataset export, and webhooks, but most are thin single-source extractors.

#### Federal Register Monitor - US Rules & Comment Tracker

**Evidence snippets**

- “This Actor searches the **Federal Register API** … extracts structured data including document metadata, **comment deadlines**, agency information, and CFR references.”
- Inputs include `onlyOpenComments` and `commentDeadlineWithinDays`.
- Output example has `commentDeadline`, `isCommentOpen`, `daysUntilCommentClose`, `docketIds`, and `scrapedAt`.
- Integrations: “**Zapier / Make**,” “**Webhooks** — send results to your API endpoint after each run,” “Email alerts.”
- Pricing: “$0.35 per 1,000 documents.”

URL: https://apify.com/teodor_banea/federal-register-monitor

**Assessment:** Medium-high directness. Uses Federal Register API only; no reconciliation with Regulations.gov. Strong feed/webhook capability via Apify platform.

#### Regulations.gov Scraper / Crawler

**Evidence snippets**

- Regulations.gov Scraper: “extracts federal regulatory data from the **official Regulations.gov API**”; modes: Search, Docket, Comments.
- Output fields include `commentEndDate`, `openForComment`, `withinCommentPeriod`, `frDocNum`, `withdrawn`, `scrapedAt`.
- Integrations: “**Slack or webhook** — Set up alerts when new proposed rules are published … trigger notifications when comment periods open or close”; “Zapier or Make”; Apify API/custom pipeline.
- Regulations.gov Crawler: “Query the official **regulations.gov v4 API** … Requires a free API key.”

URLs: https://apify.com/automation-lab/regulations-gov-scraper, https://apify.com/jungle_synthesizer/regulations-gov-crawler/api

**Assessment:** Medium-high directness for docket/comment-period monitoring. Uses Regulations.gov-only fields; no Federal Register comparison or discrepancy semantics.

### 3) Official APIs — raw substrate, no reconciliation or push feeds

#### Regulations.gov API

**Evidence snippets**

- “Regulations.gov offers a **GET API for documents, comments, and dockets**.” Endpoints: `/v4/documents`, `/v4/comments`, `/v4/dockets`.
- Document status FAQ: “The new `/v4/documents` carries a **withdrawn** field. This is a boolean field.”
- Data limitations: “some data fields are **managed solely by agencies**”; agencies can update configurable fields.
- Requires `X-Api-Key`; comments API restricted to “50 requests per minute” and “500 requests per hour.”

URL: https://open.gsa.gov/api/regulationsgov/

**Assessment:** Infrastructure. Exposes the Regulations.gov side of deadline/status truth (`commentEndDate`, `openForComment`, etc. via API/connector docs), but no FR comparison and no webhooks.

#### Federal Register API

**Evidence snippets**

- “No API keys are needed”; endpoints for published documents, public inspection documents, agencies.
- Data “comes pre-processed” from GPO MODS/bulkdata plus cleanup.
- Search results/docs list fields including `comments_close_on`, `comment_url`, `docket_ids`, `regulations_dot_gov_info`.
- Legal notice: FederalRegister.gov is an “unofficial informational resource” until ACFR grants official legal status; users should verify against official editions.

URLs: https://www.federalregister.gov/reader-aids/developer-resources/rest-api, https://www.federalregister.gov/developers/documentation/api/v1

**Assessment:** Infrastructure. Gives canonical Federal Register publication deadline metadata and DATES text, but no push feed or Regulations.gov status comparison.

### 4) Microsoft GSA Public Comment connector — enterprise workflow adapter for Regulations.gov

**Evidence snippets**

- “Provides access to the **Regulations.gov public commenting apparatus**. Query federal regulatory dockets, documents, and public comments submitted through the US GSA.”
- Actions include “List documents,” “Get document by ID,” “List dockets,” “List comments,” and “Creates a new comment.”
- Document schema exposes `frDocNum`, `allowLateComments`, `commentEndDate`, `commentStartDate`, `withinCommentPeriod`, `openForComment`, `withdrawn`.
- Available in Power Automate / Logic Apps / Power Apps / Copilot Studio; throttling 100 calls / 60 seconds.

URL: https://learn.microsoft.com/en-us/connectors/gsapubliccomment/

**Assessment:** Medium directness. Useful for workflow automation around Regulations.gov deadlines/status; no FR reconciliation. Because Power Automate can trigger workflows, it is adjacent to webhook/feed functionality, but the connector itself is a pull/action adapter.

### 5) Apogee Regulatory Intelligence — natural-language regulatory search, FR-only

**Evidence snippets**

- “2 capabilities covering **Federal Register search, open comment period tracking**, agency activity monitoring, and regulatory outcome prediction.”
- “Powered by the **Federal Register API** with coverage from 1994 to the present, updated daily.”
- Open comment tracking surfaces proposed rules/notices “currently accepting public comments, with **deadline dates and submission instructions**.”
- Data includes “comment period status, effective dates, and agency metadata.”

URL: https://apog.ai/docs/capabilities/regulatory-intelligence

**Assessment:** Medium directness. Competitor for discovery and triage; no evidence of Regulations.gov integration, deadline reconciliation, provenance/confidence, or public webhook/feed API.

### 6) Open-source wrappers / MCP servers — adjacent building blocks

**Evidence snippets**

- `1102tools/regulationsgov-mcp` search result: “MCP server for the **Regulations.gov API** … dockets, documents, comments, and **comment period tracking**”; tools include `search_documents`, `get_document_detail`, `search_comments`.
- `1102tools/federal-register-mcp` search result: “MCP server for the **Federal Register API** … proposed rules, final rules, notices, comment periods, and regulatory tracking since 1994.”
- `willjobs/regulations-public-comments`: “User-friendly API to download public comments, documents, and dockets from v4 of the Regulations.gov API”; schemas include `commentEndDate`, `commentStartDate`, `allowLateComments`, `frDocNum`.
- `judgelord/regulationsdotgov` / `q-w-a/regulationsgov`: R/Python packages for Regulations.gov API access; examples surface `commentEndDate`, `openForComment`, object IDs.
- `Pipeworx @pipeworx/federal-register`: “Federal Register is the canonical source”; docs note `comments_close_on` is the field for public comment window deadlines.

URLs: https://github.com/1102tools/regulationsgov-mcp, https://github.com/1102tools/federal-register-mcp, https://github.com/willjobs/regulations-public-comments, https://github.com/judgelord/regulationsdotgov, https://github.com/q-w-a/regulationsgov, https://pipeworx.io/docs/reference/federal-register/

**Assessment:** Adjacent. These reduce API integration friction but do not appear to reconcile cross-source deadlines or expose deadline feeds/webhooks.

## Reconciliation / provenance / confidence findings

### Reconciliation is the apparent gap

Across searched products and docs, I found repeated support for **tracking** deadlines/status from one source, but no explicit claim of:

- comparing Federal Register `comments_close_on` or DATES text to Regulations.gov `commentEndDate`;
- detecting “FR says closed / Regs.gov says open” or timezone/end-of-day discrepancies;
- ranking source authority for deadline conflicts;
- exposing a resolved deadline with provenance and confidence.

Closest adjacency:

- FRTracker records strong methodology/provenance for obligations, comments, content hashes, extraction quality, and limitations, and it combines Federal Register + Regulations.gov data. But its public methodology does **not** describe a deadline reconciliation algorithm.
- Regulations.gov exposes operational status fields (`openForComment`, `withinCommentPeriod`, `allowLateComments`) while Federal Register exposes legal publication/DATES-derived fields (`comments_close_on`, `dates`, `comment_url`). Existing tools tend to choose one.

### Provenance/confidence is rare for deadlines

- FRTracker has provenance/confidence-like mechanics for other layers: content hashes, deterministic extraction, actor confidence, quality tiers, partial coverage caveats, `_meta.source` in API responses. But not for comment deadline resolution.
- Apify actors include `scrapedAt` and source-specific fields; this is timestamp provenance, not confidence.
- Official APIs are source-of-record metadata but do not annotate confidence.

## Market/competitor implications for DocketClock

1. **Differentiator:** “Deadline reconciliation with provenance/confidence” appears under-served. Position against trackers as: not just another FR/Regs.gov monitor, but a deadline truth layer that explains source disagreement.
2. **Must-have parity:** Search/filter by agency, docket, keyword; open-comment filter; deadline calendar; daily/weekly alerts; API; webhook/feed delivery.
3. **Strong evidence fields to ingest:**
   - Federal Register: `document_number`, `comments_close_on`, `dates`, `comment_url`, `docket_ids`, `regulations_dot_gov_info`, `publication_date`, `corrections` / extensions.
   - Regulations.gov: `commentEndDate`, `commentStartDate`, `openForComment`, `withinCommentPeriod`, `allowLateComments`, `withdrawn`, `frDocNum`, `lastModifiedDate`, `objectId`, `docketId`.
4. **User-facing proof:** Competitors rarely show why a deadline is believed. Expose a resolved deadline plus source rows, observation timestamps, parser path (structured field vs DATES text), conflict flags, and confidence.

## Sources consulted

- FRTracker methodology — data sources, comment coverage, provenance/limitations: https://frtracker.app/methodology
- FRTracker developers/API — endpoints, rate limits, `_meta.source`: https://frtracker.app/developers
- FRTracker search/alerts — open-comment count and alert UI: https://frtracker.app/search
- FRTracker signals / briefing — RSS/feed evidence: https://frtracker.app/signals, https://frtracker.app/briefing
- Regulations.gov API — official v4 documents/comments/dockets API and limitations: https://open.gsa.gov/api/regulationsgov/
- Federal Register developer resources/API — official REST API, fields/data-origin/legal notice: https://www.federalregister.gov/reader-aids/developer-resources/rest-api, https://www.federalregister.gov/developers/documentation/api/v1
- Apify Federal Register Monitor — FR deadline tracker with webhooks: https://apify.com/teodor_banea/federal-register-monitor
- Apify Regulations.gov Scraper/Crawler — Regulations.gov comment period tracker/API wrapper: https://apify.com/automation-lab/regulations-gov-scraper, https://apify.com/jungle_synthesizer/regulations-gov-crawler/api
- Microsoft GSA Public Comment connector — Power Platform adapter for Regulations.gov fields/actions: https://learn.microsoft.com/en-us/connectors/gsapubliccomment/
- Apogee Regulatory Intelligence — Federal Register open-comment tracking: https://apog.ai/docs/capabilities/regulatory-intelligence
- Open-source wrappers/MCPs — adjacent API integration projects: https://github.com/1102tools/regulationsgov-mcp, https://github.com/1102tools/federal-register-mcp, https://github.com/willjobs/regulations-public-comments, https://github.com/judgelord/regulationsdotgov, https://github.com/q-w-a/regulationsgov, https://pipeworx.io/docs/reference/federal-register/
