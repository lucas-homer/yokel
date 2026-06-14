# Technical Feasibility / Operations Ballot

Scoring: **1 = poor / high risk / high burden**, **10 = strong / low risk / low burden**. Overall is a simple average of the five operational criteria.

| Rank | Survivor | Data availability | MVP buildability | Maintenance burden | API/legal constraints | COGS | Overall |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | CommentWindow Registry / DocketClock | 9 | 8 | 7 | 8 | 8 | 8.0 |
| 2 | Pharmacy Docket Desk | 8 | 8 | 7 | 6 | 7 | 7.2 |
| 3 | RecordReady Clerk Intake | 7 | 7 | 6 | 6 | 7 | 6.8 |
| 4 | Childcare Rule Radar / CareNotice Counsel | 7 | 7 | 6 | 6 | 7 | 6.8 |
| 5 | CareRule Scout / Benefits Plainwatch | 7 | 6 | 5 | 5 | 6 | 5.6 |
| 6 | Conditions Keeper / Outcome Graph | 6 | 6 | 5 | 6 | 5 | 5.6 |
| 7 | Concern Router / Civic RouteMap | 6 | 5 | 4 | 6 | 5 | 5.2 |
| 8 | Tenant Displacement Docket | 5 | 5 | 4 | 4 | 4 | 4.4 |

## Rationale and required changes

**1. CommentWindow Registry / DocketClock — 8.0.** Best technical fit because the narrowed federal MVP has unusually strong source foundations: Federal Register, Regulations.gov, and Mirrulations. The happy path is straightforward deadline normalization plus provenance, webhooks, and bulk export; nil/empty/error paths are manageable if missing dates, withdrawn items, source conflicts, and fetch failures become explicit uncertainty states rather than silent data gaps. Required changes: keep the MVP federal-only, treat deadline corrections and source staleness as product primitives, and avoid state/local expansion until a funded QA model exists.

**2. Pharmacy Docket Desk — 7.2.** Data is comparatively available for a one-state plus CMS/DEA/FDA wedge, and the MVP can start as source-cited action files rather than deep workflow software. Maintenance is moderate because board calendars, Medicaid notices, and bill/rule feeds vary, but channel-led distribution keeps COGS and onboarding contained. Required changes: sell through associations/PSAOs/buying groups, use expert-reviewed summaries and disclaimers, and avoid legal interpretation beyond clearly sourced operational impact.

**3. RecordReady Clerk Intake — 6.8.** Buildability is solid for one Legistar jurisdiction and one mailbox: IMAP ingestion, agenda matching, clustering, review queues, receipt emails, and PDF/CSV export are all standard components. The operational risk is not data access so much as custody, auditability, security, and staff trust around official-record packets. Required changes: position as human-reviewed packet prep only, preserve immutable audit trails, support nil/empty/error cases such as unmatched agenda items or unreadable attachments, and integrate with existing clerk workflows instead of replacing them.

**4. Childcare Rule Radar / CareNotice Counsel — 6.8.** A one-state, one-provider-type MVP is feasible using state register notices, childcare agency hearings, and HHS/ACF federal sources. The main burden is ongoing expert review and taxonomy maintenance for license categories, subsidy participation, ratios, training, and background-check implications. Required changes: make an association/CCR&R/shared-services buyer mandatory, limit early outputs to human-reviewed operational impact and post-adoption briefs, and avoid broad direct-to-provider SaaS until bundled distribution is validated.

**5. CareRule Scout / Benefits Plainwatch — 5.6.** The demand is serious, but Medicaid/HCBS and benefits data is fragmented, legally nuanced, and easy to overstate. A narrow expert-reviewed navigator product is buildable, but nil/error paths are consequential: missing state notices, ambiguous eligibility effects, or stale PDFs can cause panic or missed action. Required changes: scope to one program/region, require legal-aid/P&A/navigator review, prohibit eligibility determinations and direct mass alerts in the MVP, and expose confidence plus source excerpts on every alert.

**6. Conditions Keeper / Outcome Graph — 5.6.** One planning commission with Legistar/manual extraction is buildable, especially for continuance dates, votes, appeal deadlines, and document-diff receipts. Feasibility drops when the product tries to infer enforcement, causality, or whether comments changed outcomes, because condition language and final documents are often ambiguous. Required changes: keep the MVP to source-linked receipts and next-window reminders, use human review for condition extraction, and explicitly mark missing minutes, inaccessible attachments, and ambiguous deadlines as unresolved.

**7. Concern Router / Civic RouteMap — 5.2.** The router has useful building blocks, but it combines several hard problems: natural-language concern classification, jurisdiction matching, live deadline discovery, and conservative confidence. Happy-path demos will be easy; nil/empty/error paths are the product risk because many concerns have no reliable official lever or only stale/indirect processes. Required changes: navigator-facing only, one metro plus federal/one-state/one-city sources, citations for every route, a first-class “no reliable path found,” and human escalation before any resident-facing recommendation.

**8. Tenant Displacement Docket — 4.4.** This is the hardest survivor operationally. Source data may be late, incomplete, or spread across permits, planning agendas, assessor records, rent-stabilized lists, and local rules; legal/privacy risk is high because public vulnerable-building intelligence can aid landlords or speculators. A partner-mediated MVP can be attempted, but it needs more operational design than the others. Required changes: one city, one case type, one legal-aid/tenant-union anchor, strict access controls, no public vulnerable-building database, human-reviewed alerts, and an explicit proof that data arrives early enough to intervene.
