# DocketClock research synthesis

## Executive answer

There is a real but narrow market gap for a **deadline-confidence layer** that reconciles Federal Register, Regulations.gov, and agency/procedural changes with source provenance. Orgs do encounter deadline ambiguity and cross-source mismatch risk, but most buyers experience it as part of a broader monitoring/triage/workflow burden rather than as a standalone “API problem.” The best wedge is not another open-comment tracker; it is a verified deadline primitive with conflict flags, evidence trails, alerts/webhooks, and integration into existing legal, policy, or regulatory-intelligence workflows.

The strongest commercial hypothesis: sell first to **law-firm current-awareness teams, regulatory-affairs/policy teams in highly regulated sectors, associations/coalitions, consultants, and existing platform/internal-tool builders** who already have workflows but still manually verify deadlines. The weaker hypothesis: broad enterprises will buy a raw deadline API at high ACV. Most enterprise spend is justified by full workflow, analyst curation, stakeholder management, comment drafting, reporting, or proprietary intelligence—not deadline data alone.

## Validation questions

### 1) Do orgs see Federal Register / Regulations.gov deadline mismatches?

**Yes, or at minimum they face documented conditions that create deadline mismatches, stale deadlines, and uncertainty.** The research found both direct examples and official-system mechanics that make mismatch likely.

Evidence:

- Federal Register and Regulations.gov expose different deadline fields and semantics: Federal Register has `comments_close_on`; Regulations.gov has `commentEndDate`, `openForComment`, `withinCommentPeriod`, `allowLateComments`, and `withdrawn` in document-level records. Source: https://open.gsa.gov/api/regulationsgov/ and https://www.federalregister.gov/developers/documentation/api/v1
- In a sampled Federal Register API record, Federal Register `comments_close_on` was `2019-03-14`, embedded Regulations.gov `comment_end_date` was `2019-03-15`, and the notice text said comments were due March 14—likely an end-of-day/timezone normalization issue. Source: https://www.federalregister.gov/api/v1/documents/2018-27875.json
- ACUS says Regulations.gov receives Federal Register data, but lifecycle linking depends on agencies entering identifiers correctly; missing or incorrect Regulations.gov document numbers, RINs, or Federal Register document numbers can make rulemaking context hard to discern. It also documents multiple e-dockets for one rulemaking, inconsistent document-type labels, parent/sub-agency search issues, and missing RINs. Source: https://www.acus.gov/document/improving-access-regulationsgovs-rulemaking-dockets
- GSA warns that Regulations.gov comment data has limitations and that some fields are managed solely by agencies. Source: https://open.gsa.gov/api/regulationsgov/
- The Federal Register API does not fully document all relevant field semantics. A maintainer said no field-definition document was available for many fields including `comments_close_on`, `comment_url`, `correction_of`, `corrections`, `docket_ids`, and `regulations_dot_gov_info`. Source: https://github.com/usnationalarchives/federalregister-api-core/issues/9
- Deadlines are dynamic. Examples include EPA’s NPDES permit notice chain with original notice, extension, then reopening; PHMSA’s 90-day extension plus late-comment language; EPA’s one notice extending two different comment periods to two different dates; HUD extending a comment period after a Regulations.gov migration/submission outage; and NPS specifying electronic comments due at 11:59 p.m. Eastern / 7:59 p.m. Alaska time. Sources: https://www.federalregister.gov/documents/2025/04/21/2025-06774/national-pollutant-discharge-elimination-system-npdes-2026-issuance-of-the-multi-sector-general, https://www.federalregister.gov/documents/2025/01/08/2024-31077/hazardous-materials-advancing-safety-of-highway-rail-and-vessel-transportation-extension-of-comment, https://www.federalregister.gov/documents/2025/02/21/2025-02910/two-actions-published-by-the-environmental-protection-agency-with-comment-periods-that-close, https://www.govinfo.gov/content/pkg/FR-2025-05-07/html/2025-07961.htm, https://www.federalregister.gov/documents/2026/04/10/2026-07006/alaska-hunting-and-trapping-in-national-preserves-extension-of-comment-period

Bottom line: even if users do not describe the problem as “FR vs Regulations.gov mismatch,” the underlying pain is real: single-source deadline metadata can be stale, ambiguous, incorrectly linked, timezone-shifted, or procedurally superseded.

### 2) How do they resolve deadline uncertainty?

They resolve it through **manual expert verification across sources**, not by trusting one metadata field.

Observed resolution patterns:

- Verify against the official Federal Register/govinfo PDF when legal reliance matters; FederalRegister.gov itself warns it is an unofficial XML rendition and legal users should verify against official editions. Sources: https://www.federalregister.gov/reader-aids/using-federalregister-gov/subscription-options-and-managing-your-subscriptions and https://www.federalregister.gov/reader-aids/developer-resources/federalregister-gov-is-open-source
- Read the Federal Register notice text, especially “Dates,” “Addresses,” and preamble language, rather than relying only on metadata.
- Cross-check docket IDs, RINs, Federal Register citations/document numbers, agency contacts, RegInfo/Unified Agenda references, and Regulations.gov docket/document pages.
- Track extensions, reopenings, corrections, withdrawals, and operational incidents. Example: SEC reopened several comment periods after a technological error and instructed commenters to check whether comments posted and resubmit if missing. Source: https://www.federalregister.gov/documents/2022/10/18/2022-22295/resubmission-of-comments-and-reopening-of-comment-periods-for-several-rulemaking-releases-due-to-a
- Contact the agency or listed notice contact when an agency does not participate in Regulations.gov or when submission practices are unclear. Regulations.gov FAQ notes not all agencies post dockets/comments/supporting materials there. Source: https://www.regulations.gov/faq
- Preserve proof of submission—copies, date, method, confirmation/tracking number—because submission status and late/failed submissions matter. FDA and practitioner guidance emphasize confirmations and records. Source: https://www.fda.gov/regulatory-information/federal-register-fr-notices/how-use-regulationsgov and https://ofwlaw.com/how-to-prepare-for-fda-and-usda-rulemaking/

### 3) How much manual review do they do?

**A lot, especially for high-stakes comments.** Automation helps discovery and routing, but expert review remains central.

Manual work includes:

- Selecting broad vs. narrow issue terms, agencies, dockets, RINs, and keywords for alerts.
- Verifying legal deadlines and submission channels in the notice text and official PDFs.
- Determining whether an “extension,” “correction,” “withdrawal,” or “reopening” actually changes the comment deadline. Example false-positive risk: a BLM notice title includes “Extension, Public Meetings and Correction,” but the extension concerns a public-land withdrawal term, not necessarily a comment-period extension. Source: https://www.federalregister.gov/documents/2023/12/14/2023-27468/notice-of-proposed-withdrawal-extension-public-meetings-and-correction-for-segments-of-the-colorado
- Reading dense preambles and agency questions; mapping impacts to operations, members, clients, or products; collecting evidence/cost data; and preparing legal/statutory arguments.
- Monitoring comments filed by others, allies/opponents, competitors, and associations.
- Coordinating assignments, coalition/member outreach, drafting, review, submission, and reporting.

Vendors implicitly validate this by selling workflow around monitoring: Quorum advertises alerts, summaries, tracking boards, assignments, comment drafting, and campaigns; FiscalNote sells monitoring, targeted notifications, centralized comments, sentiment/stance/theme analysis, and reports. Sources: https://www.quorum.us/blog/3-step-guide-to-regulatory-comment-tracking/ and https://fiscalnote.com/blog/regulatory-tracking-developing-a-winning-strategy

### 4) Would a deadline-confidence API be useful, or do existing platforms solve it?

**Useful, but only if it is meaningfully better than raw monitoring. Existing platforms solve adjacent workflow problems, not clearly the specific FR/Regulations.gov deadline-confidence problem.**

What exists:

- Official free APIs expose raw data but do not reconcile deadline conflicts or provide push confidence feeds. Sources: https://open.gsa.gov/api/regulationsgov/ and https://www.federalregister.gov/reader-aids/developer-resources/rest-api
- FRTracker is the closest prior art: open-comment pages, deadline calendars, alerts, API, RSS, and provenance-oriented methodology using FederalRegister.gov, eCFR, and Regulations.gov comments. But public materials do not claim explicit reconciliation of Federal Register `comments_close_on` vs. Regulations.gov `commentEndDate/openForComment` with confidence scoring. Sources: https://frtracker.app/methodology, https://frtracker.app/developers, https://frtracker.app/search
- Apify actors provide low-cost single-source Federal Register or Regulations.gov monitoring, scheduling, webhooks, Zapier/Make, and fields like `commentDeadline`, `commentEndDate`, `openForComment`, and `isCommentOpen`, but they do not reconcile sources. Sources: https://apify.com/teodor_banea/federal-register-monitor and https://apify.com/automation-lab/regulations-gov-scraper
- Microsoft’s GSA Public Comment connector exposes Regulations.gov actions/fields into Power Platform, but it is also single-source. Source: https://learn.microsoft.com/en-us/connectors/gsapubliccomment/
- Apogee tracks Federal Register open comment periods and deadlines, but public docs describe Federal Register API coverage rather than cross-source reconciliation. Source: https://apog.ai/docs/capabilities/regulatory-intelligence

Therefore the gap appears to be: **resolved deadline + confidence + provenance + conflict/change detection**, not generic search or alerts.

A useful API/feed should include:

- Resolved deadline and status.
- Source rows from Federal Register, Regulations.gov, govinfo/notice text, and agency pages where applicable.
- Confidence score or flags, not a silent “truth” field.
- Explanation: structured field vs. parsed DATES text vs. extension/reopening/correction chain.
- Timezone/submission-channel semantics.
- Change detection for extensions, reopenings, withdrawals, corrections, outages, and late-comment policies.
- Webhooks, CSV, Slack/email, audit logs, and embeddable evidence links.

### 5) Would they pay for the primitive, or only a full workflow product?

**They may pay for the primitive, but at infrastructure/feed prices unless it is bundled with workflow, coverage guarantees, support, or redistribution rights.** The highest ACVs belong to full workflow/intelligence products.

Evidence on willingness to pay:

- Raw monitoring is cheap/free: Regulations.gov API is free with key; FederalRegister.gov API is free; Apify Federal Register Monitor is $0.35 per 1,000 documents. Sources: https://open.gsa.gov/api/regulationsgov/, https://www.federalregister.gov/reader-aids/developer-resources/rest-api, https://apify.com/teodor_banea/federal-register-monitor
- Lightweight/self-serve tools anchor low prices: Plural self-serve legislative tracking is $59/month and professional tools are $5,000/year; RegAlytics Essentials is $49.99/month but excludes API; Regulation Roundup advertises free/paid briefing tiers. Sources: https://pluralpolicy.com/pricing/, https://www.regalytics.ai/pricing, https://regulationroundup.com/pricing/
- Full enterprise platforms command more because they bundle workflow, analysis, stakeholder management, reporting, curation, and procurement support. SpendHound reports FiscalNote average annual spend around $7,335 for SMBs and $67,404 for enterprises. Source: https://www.spendhound.com/marketplace/fiscalnote-pricing
- RegAlytics shows API/white-label rights can be valuable: Enterprise with unlimited API is listed at $10,250/month and White Label Enterprise at $15,000/month. Source: https://www.regalytics.ai/pricing
- AgencyIQ launched FDA-focused regulatory intelligence at $25k–$75k/year, showing high WTP for expert regulatory-affairs intelligence, not merely raw deadlines. Source: https://digiday.com/media/politicos-new-fda-focused-subscription-product-costs-75k-year/

Likely pricing implication:

- Narrow self-serve/API feed: roughly $50–$500/month for individuals/small teams.
- Professional/team confidence layer with alerts, evidence trails, exports, and support: roughly $5k–$25k/year.
- Enterprise/API/white-label with SLA, redistribution, bulk history, custom sources, and support: roughly $25k–$125k+/year.

## Market-gap assessment

### The real gap

The strongest gap is **not discovery of open comment periods**. That is already served by Federal Register, Regulations.gov, FRTracker, Apify, Regulation Roundup, Quorum, FiscalNote, Apogee, and others.

The stronger gap is **deadline reliability as an auditable primitive**:

- Reconcile Federal Register metadata, Federal Register DATES text, govinfo official text, Regulations.gov document state, docket/document relationships, extension/reopening/correction notices, RINs, docket IDs, and agency-specific instructions.
- Flag rather than hide ambiguity.
- Explain why the system believes a deadline is current.
- Provide evidence links and audit trails for legal/policy teams.
- Integrate into tools buyers already use.

### Why this gap exists

- Official systems are partially interoperable and agency metadata can be missing, inconsistent, or agency-controlled. Source: https://www.acus.gov/document/improving-access-regulationsgovs-rulemaking-dockets and https://open.gsa.gov/api/regulationsgov/
- FederalRegister.gov is convenient but unofficial for legal reliance. Source: https://www.federalregister.gov/developers/documentation/api/v1
- Existing commercial tools emphasize monitoring, workflow, curation, assignments, campaigns, and reports, not explicit deadline conflict resolution.
- Low-cost monitors commoditize single-source alerts, creating room only for a differentiated confidence/provenance layer.

### Product posture

Best positioning: **“deadline confidence infrastructure for public comment workflows.”** Avoid claiming to be the legal authority. Instead: “We show the operative deadline, source evidence, conflicts, and why human review may be needed.”

## Best customer segments

1. **Law firms and law librarians/current-awareness teams**
   - Pain: many clients, agencies, dockets, and subscriptions; high liability around missed deadlines; need citations and internal distribution.
   - Best offer: evidence-backed alerts, audit logs, internal newsletters, source snapshots, conflict flags, and redistribution rights.
   - Supporting source: Broadside says attorneys/policy advisors monitor dozens of dockets/agencies and may miss guidance/enforcement shifts until after comment windows close. https://broadside.app/product/broadside/for/law-firms

2. **Regulatory affairs teams in life sciences, food, chemicals, energy, transportation, finance**
   - Pain: high-stakes agency actions; comments affect product strategy/compliance.
   - Best offer: agency-specific monitors, verified deadline calendars, escalation flags, and integration into regulatory-intelligence workflows.
   - Supporting source: AgencyIQ FDA launch pricing at $25k–$75k/year indicates budgets for expert regulatory intelligence. https://digiday.com/media/politicos-new-fda-focused-subscription-product-costs-75k-year/

3. **Trade associations and advocacy coalitions**
   - Pain: member alerts, sign-on letters, coalition coordination, comment windows, and extensions.
   - Best offer: member-facing deadline widgets/newsletter blocks, coalition calendar, and confidence flags rather than API-only.
   - Supporting source: Quorum and FiscalNote sell public-affairs/regulatory tracking workflows including alerts, assignments, grassroots campaigns, and reports. https://www.quorum.us/blog/3-step-guide-to-regulatory-comment-tracking/ and https://fiscalnote.com/blog/regulatory-tracking-developing-a-winning-strategy

4. **Consultants, boutique policy shops, and internal tool builders**
   - Pain: need reliable substrate but may not want a full platform.
   - Best offer: API/webhooks/CSV with provenance, Slack/email, monitored docket folders, and reasonable monthly pricing.

5. **Regulatory-intelligence vendors, newsletters, and AI-agent builders**
   - Pain: already own the front-end/workflow but need defensible deadline data.
   - Best offer: enterprise API/white-label license with SLA and redistribution rights.
   - Supporting source: FiscalNote now markets PolicyNote API/MCP for internal dashboards, CRM, AI agents, and workflows. https://fiscalnote.com/products/policynote

## Strongest contrary evidence

- **Raw data is free or very cheap.** FederalRegister.gov and Regulations.gov APIs are free; Apify packages monitoring with webhooks for very low marginal cost. This pressures any standalone data product. Sources: https://open.gsa.gov/api/regulationsgov/, https://www.federalregister.gov/reader-aids/developer-resources/rest-api, https://apify.com/teodor_banea/federal-register-monitor
- **Incumbents already own the workflow budget.** Quorum, FiscalNote, Politico Pro, AgencyIQ, Apogee, FRTracker, Regulation Roundup, and similar products already provide alerts, dashboards, summaries, assignments, campaigns, and reports. Buyers may not want another vendor unless DocketClock integrates cleanly.
- **Some teams may treat manual legal review as non-substitutable.** Even a high-confidence API cannot replace reviewing the notice text, submission instructions, and official PDF for high-stakes matters. This limits liability claims and requires disclaimers.
- **Deadline mismatches may be episodic, not daily.** The pain is acute when it happens, but many routine notices may be handled adequately by existing metadata and alerts.
- **Procurement and trust burden is high.** A “deadline-confidence” product invites reliance. Enterprise buyers may demand SOC 2, SLAs, indemnity, security review, audit logs, and coverage guarantees before paying meaningful ACV.

## Recommended next validation interviews

Prioritize interviews that test whether the deadline-confidence primitive is painful enough to buy separately and how it must integrate.

1. **Law-firm regulatory/current-awareness librarian or knowledge-management lead**
   - Questions: How are comment deadlines captured? Who verifies them? Have mismatches/extensions caused issues? Would source-backed confidence flags reduce review time? Do they need redistribution rights?

2. **Regulatory affairs lead in FDA/USDA/EPA-regulated company**
   - Questions: Which sources/tools are checked before deciding a comment deadline? How often are deadlines manually verified against PDFs or agency pages? What is the cost of missing a comment window?

3. **Trade association government-affairs director**
   - Questions: How are member alerts and sign-on letter deadlines managed? How are extensions/reopenings detected? Would they buy an embeddable deadline calendar or newsletter feed?

4. **Boutique regulatory consultant / public-policy shop**
   - Questions: What tools are used today—FiscalNote, Quorum, spreadsheets, RSS, Google Alerts, official APIs? Where does manual verification happen? Would a $200–$1,000/month verified feed be acceptable?

5. **Existing platform/newsletter/API builder**
   - Questions: Do they already reconcile FR and Regulations.gov? Are deadline conflicts customer-facing? Would they license a confidence API or prefer to build it? What SLA/redistribution terms would matter?

6. **Former agency docket manager or Regulations.gov power user**
   - Questions: How often are metadata fields updated late or inconsistently? What edge cases cause public confusion? How should a third-party product rank source authority?

Interview success criteria:

- At least 3–5 concrete stories of deadline uncertainty, mismatch, extension/reopening misses, or manual verification burden.
- Clear current owner of deadline verification.
- Measurable review time or risk reduction.
- Willingness to pay for either: standalone feed/API, embedded widget/newsletter, or full workflow product.
- Identification of must-have trust features: official PDF links, source snapshots, audit logs, confidence flags, human review, SLA, or disclaimers.

## Recommended MVP

Build a narrow prototype around **confidence and provenance**, not generic monitoring:

- Ingest Federal Register records (`document_number`, `comments_close_on`, `dates`, `comment_url`, `docket_ids`, `regulations_dot_gov_info`, `publication_date`) and Regulations.gov document records (`documentId`, `objectId`, `docketId`, `frDocNum`, `commentStartDate`, `commentEndDate`, `openForComment`, `allowLateComments`, `withdrawn`, `lastModifiedDate`).
- Model deadlines at the **document level**, not only docket level, because dockets can contain multiple documents with distinct comment periods. Source: https://open.gsa.gov/api/regulationsgov/
- Display resolved deadline, source evidence, confidence level, conflict flags, and change history.
- Flag for human review when FR and Regulations.gov dates differ, extension/reopening/correction/withdrawal language appears, `commentEndDate` is null but status is open, status is closed with a future date, multiple deadlines appear in one notice, or timezone/submission-channel language is present.
- Ship alerts/webhooks/CSV/Slack/email before building a heavy workflow UI.
- Include explicit legal disclaimer: DocketClock is a research/monitoring aid; users should verify official notice text/PDF for legal reliance.
