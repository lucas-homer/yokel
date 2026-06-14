# Debate gauntlet step 1: RED TEAM

Scope: attack every candidate in `fresh-foundry/curated-slate.md` using the prior-art scan and seasoned concepts as context. This is not a ranking and does not propose winners.

## Calibration

- **Size estimate:** curated slate is ~5,500-6,500 words, with 13 active candidates and 10+ implementation units per candidate.
- **Risk signals:** external APIs, government records, official deadlines, legal/procedural reliance, land-use/property data, address verification, benefits/Medicaid, childcare licensing, pharmacies/controlled substances, privacy, public-record legitimacy, AI summarization/classification, and B2G/B2B funding.
- **Depth:** deep red-team pass.

---

## 1. CommentWindow Registry / DocketClock

**Fatal risks**
- The value proposition is “reliable deadline object,” but the hardest part is not schema design; it is liability-grade operational correctness. A single wrong close date can destroy the exact trust the product sells.
- Federal-first may be too narrow for willingness to pay. The prior research says Federal Register/Regulations.gov/Mirrulations already cover much of the federal monitoring backbone; buyers may see this as a convenience layer, not a must-have.
- “SLA-backed” implies support, verification, incident response, and correction workflows before the product has enough revenue to fund them.

**Nonfatal risks**
- Timezone, extensions, reopening, withdrawal, duplicate dockets, agency-specific submission portals, and “comments due by received/postmarked/filed” semantics will create edge cases that do not fit a clean canonical object.
- The product may be invisible infrastructure: valuable to downstream tools but hard to get noticed or budgeted as a standalone line item.
- Open/free public schema plus paid SLA can undermine itself if the free tier is good enough for most civic users and paid users are too few.

**Duplication / prior-art concerns**
- Regulations.gov, Federal Register APIs, Mirrulations, mirrulations-search, and spicy-regs already solve much of the federal raw-data problem.
- Prior scan explicitly recommends building on Mirrulations for history and direct APIs for freshness; rebuilding an index without a differentiated reliability model is likely duplicate infrastructure.
- Commercial policy trackers could add better deadline exports faster than this can build buyer trust.

**Data / maintenance traps**
- State/local expansion is the obvious growth story but becomes the known “scraper graveyard”: City Scrapers-style custom spiders, Legistar variants, PDF-only notices, agency portals, and permanent breakage.
- Even federal sources are not one source: non-Regulations.gov agencies, agency websites, PDF notices, and portal-specific submission rules break the clean substrate premise.
- Provenance dashboards do not fix wrong data; they only explain why the product was wrong.

**Funding / adoption traps**
- Newsrooms and civic-data teams often need data but have weak budgets. Associations may already have policy staff or commercial trackers.
- Agencies/clerks are listed as eventual users, but they may not buy a third-party representation of their own deadlines unless there is procurement, indemnity, and records-policy comfort.
- API volume/webhooks/SLA pricing needs high-volume users; many civic use cases are low-volume but high-support.

**Legitimacy / privacy risks**
- Low privacy risk, but high legitimacy risk: a third party declaring “what is open” may be blamed when agencies disagree or change rules.
- If confidence labels are too prominent, users may not trust it; if too subtle, users may over-rely on it.

**Provisional verdict: salvage**
- Strong as a component, dangerous as a standalone promise. Kill any state/local or “SLA-backed” ambition until federal deadline correctness, correction workflows, and paid buyer urgency are proven.

---

## 2. RecordReady Clerk Intake

**Fatal risks**
- Clerks do not primarily need clever classification; they need defensible records handling. If automation misfiles, drops, deduplicates, or summarizes public input incorrectly, the product creates procedural risk rather than reducing work.
- B2G sales to small jurisdictions may be slower and more expensive than the problem can support.
- The product touches official record custody. Many jurisdictions already have agenda-management, email archiving, public-records, or case-management vendors; inserting a new intake layer may be institutionally unacceptable.

**Nonfatal risks**
- Staff review queues can become another inbox if matching confidence is not extremely high.
- Duplicate clustering is politically sensitive: people may interpret grouping as discounting comments.
- Voicemail transcription, attachments, petition links, screenshots, and forwarded email chains create a messy evidentiary surface.

**Duplication / prior-art concerns**
- Granicus/PublicInput/EngagementHQ/CitizenLab/Decidim occupy government-bought participation and intake-adjacent workflows.
- MAPLE-style receipts and Decidim-style verification are useful references, but clerks may prefer vendor-native modules from their existing agenda/records stack.
- This risks becoming a feature inside agenda-management suites rather than an independent product.

**Data / maintenance traps**
- Legistar helps only one class of agenda matching. Non-Legistar jurisdictions, ad hoc boards, PDFs, and local naming conventions require bespoke configuration.
- Mailbox ingestion is brittle: permissions, retention policies, public-records rules, spam, attachments, legal holds, and Microsoft/Google admin constraints.
- “Record-ready packet” formats are jurisdiction-specific and may require custom exports per clerk.

**Funding / adoption traps**
- Small jurisdictions have the pain but least procurement capacity. Large jurisdictions have money but already have entrenched vendors and legal review.
- Innovation/open-government pilots may fund prototypes but not long-term operations.
- Staff adoption depends on measurable time savings during crunch periods; if the system requires training and review, it may fail the “72 hours before meeting” use case.

**Legitimacy / privacy risks**
- Contains PII, potentially sensitive public comments, addresses, phone numbers, disability/benefits/housing facts, and attachments.
- Receipts can create expectations of official acceptance; if the jurisdiction has legal requirements for filing, the tool may accidentally mislead residents.

**Provisional verdict: weak**
- Real pain, but the buyer, procurement path, and records-risk burden are brutal. Salvage only with a clerk co-design partner willing to define the official-record boundary and acceptance criteria.

---

## 3. Consensus Comment Room

**Fatal risks**
- The central premise can be attacked from both sides: agencies may see AI-mediated consensus packets as laundered mass advocacy, while organizers may see minority-preserving deliberation as slowing mobilization.
- If it succeeds at producing “fewer, better” comments, it may reduce the visible volume that campaign funders and organizers value.
- Neutrality is nearly impossible when rooms are created by advocacy organizations or funded by agencies/foundations.

**Nonfatal risks**
- The 10-60 day window is short for recruiting, deliberating, fact-checking, drafting, reviewing, and filing.
- Participants may not want to complete a seven-question evidence interview; campaigns optimize for low-friction action.
- Consensus outputs can flatten real conflict; minority reports can be ignored.

**Duplication / prior-art concerns**
- Pol.is/vTaiwan, Decidim, Consul, MAPLE, Regulations.gov, Resistbot/5 Calls, Phone2Action/CQ Engage/New/Mode all touch pieces of deliberation, commenting, or campaign mobilization.
- The prior scan warns deliberation tools need durable funding and that action tools already exist for org campaigns.
- “Comment Workshop + Closed the Loop” appears as a cross-cutting module in prior seasoned ideas; standalone deliberation was already judged weak.

**Data / maintenance traps**
- Substantive-comment quality requires docket-specific issue understanding, not just clustering participant views.
- Receipt capture and final-action tracking depend on inconsistent agency responses and docket metadata.
- Similarity detection can create false confidence that comments are distinct enough to matter.

**Funding / adoption traps**
- Nonprofits and neighborhood coalitions are budget-constrained and campaign-based.
- Agency/ombuds pilots create legitimacy problems; public-interest foundation funding may not sustain operations.
- Per-campaign fees are lumpy and require sales exactly when organizers are under deadline pressure.

**Legitimacy / privacy risks**
- Highest astroturf/perception risk of the slate. “AI helped a group produce official-record comments” is an easy attack line.
- User attestation, dissent preservation, and provenance help but may not overcome distrust.
- Collecting lived experience and affected-status facts creates sensitive data retention questions.

**Provisional verdict: weak**
- Useful as an embedded workflow for an already trusted organization, but weak as a product. The legitimacy attack is not incidental; it strikes the core mechanism.

---

## 4. Affected-Party Verifier / Notice Compact

**Fatal risks**
- Verification can invert the civic principle it claims to protect: officials may start weighting verified nearby property owners more than renters, workers, unhoused people, parents, or broader affected communities.
- Address/radius status is legally and politically loaded. The tool could become a procedural weapon for developers, neighborhood opponents, or governments.
- “Neutral affected-status layer” is not neutral in practice; whoever defines radius, relationship categories, and reporting format shapes political legitimacy.

**Nonfatal risks**
- Self-attestation for renters weakens verification; hard verification for renters increases exclusion.
- Applicants funding notice transparency creates perceived capture even with non-success-fee rules.
- Staff-reviewed packets may be too slow for short notice windows.

**Duplication / prior-art concerns**
- Decidim/Consul verification tiers, MapIt-style geocoding, coUrbanize/PublicInput/developer project portals, and existing statutory notice procedures all partially overlap.
- The differentiated part is not technology but institutional acceptance of a new affected-status report.
- If planning departments already have legal notice lists, they may not want a parallel private verifier.

**Data / maintenance traps**
- Parcel, assessor, rental, business, school, district, and radius data are inconsistent and often stale.
- Geocoding edge cases matter: corner parcels, multifamily buildings, ADUs, PO boxes, shelters, informal tenants, workers, and parents with children near a site.
- Private audit trails can become discoverable or subpoenaed.

**Funding / adoption traps**
- Legal-aid/planning pilots are plausible but narrow; applicant-paid model is reputationally dangerous.
- Planning departments may avoid buying tools that change who appears “legitimate” in contentious hearings.
- Civic participation vendors might copy verification as a feature if demand appears.

**Legitimacy / privacy risks**
- Serious privacy risk from address verification, relationship-to-place data, and case-specific political participation.
- Could chill participation if residents fear landlords, developers, employers, or agencies learning their position.
- Reporting counts by status can be misused to discount unverified speakers.

**Provisional verdict: weak**
- The premise is attractive, but the failure mode is exclusionary civic infrastructure. Salvage only if it explicitly prevents verified status from becoming a gate or ranking signal.

---

## 5. Concern Router / Civic RouteMap

**Fatal risks**
- The product promises to resolve vague concerns into official levers, but many concerns have no live procedural path. If “no reliable official path found” is common, perceived product value may collapse.
- Wrong routing is worse than no routing: it sends people to irrelevant officials or expired processes and burns trust with navigators.
- Cross-source routing requires solving nearly every hard ingestion problem at once: dockets, bills, local agendas, districts, GIS, deadlines, and eligibility.

**Nonfatal risks**
- Plain-language concern classification will struggle with rumors, partial facts, sarcasm, multilingual input, and ambiguous locations.
- Conservative confidence thresholds protect trust but may produce too many non-answers.
- Navigator-facing workflow may reduce consumer risk but limits scale and makes sales/services heavier.

**Duplication / prior-art concerns**
- mySociety’s WriteToThem/MapIt proves routing to representatives; Resistbot/5 Calls handle simple action paths; Open States/Plural, Legistar/Councilmatic, and policy trackers handle known-process discovery.
- The white space is cross-domain routing for non-experts, but that is also the hardest claim to validate.
- Prior scan’s “sharpest wedge” is location-based watch+act; this candidate may be too broad compared with scoped verticals.

**Data / maintenance traps**
- Every added source expands false-positive surface. Matching a resident concern to a docket requires not just metadata but semantic issue understanding.
- Local boundaries, agency jurisdiction, school districts, special districts, and state/federal preemption make “where to act” nontrivial.
- Deadlines and eligibility requirements are exactly the fields most likely to be missing or stale.

**Funding / adoption traps**
- Libraries, newsrooms, legal aid, and community foundations are mission-fit but budget-light.
- SaaS/API for advocacy/civic products competes with the fact those products may already use specialized data providers.
- The support burden for navigators could become consulting rather than software.

**Legitimacy / privacy risks**
- Concern text can include sensitive legal, immigration, health, housing, workplace, or family details.
- If the tool recommends advocacy steps, users may interpret it as legal/civic advice.
- Routing can amplify rumors into official processes if not carefully constrained.

**Provisional verdict: weak**
- Big white space, but too much surface area for an MVP. Salvage only as a narrow navigator tool over a very limited source set and with “no path found” treated as first-class output.

---

## 6. NoticeNail / Lot Line

**Fatal risks**
- The product creates a false-security problem: subscribed residents may assume they will be notified, but photo capture is opportunistic and incomplete.
- Human verification is not a mitigation detail; it is the product. Without a dense capture/QA network, notices will be missed or late.
- It may systematically privilege neighborhoods with volunteers, smartphones, and civic capacity, worsening participation inequity.

**Nonfatal risks**
- OCR on posted notices will fail on glare, weather, handwriting, bad angles, multilingual notices, and missing fields.
- Case matching can be slow or impossible when notices use internal IDs not exposed in public portals.
- Radius alerts can become noise if many notices are technically nearby but not actionable.

**Duplication / prior-art concerns**
- coUrbanize/PublicInput/developer pages, city portals, Symbium, and local permit trackers cover fragments.
- The resident-side missing-signal capture is differentiated, but it is closer to local journalism/community operations than scalable software.
- Prior research says land-use/permits are the net-new hard domain nobody has solved; this directly enters that swamp.

**Data / maintenance traps**
- Accela/EnerGov/Socrata/ArcGIS enrichments vary wildly by city and often omit the public action lever.
- Legal notice requirements differ by process; posted notice may not equal open comment or appeal rights.
- Maintaining city-specific parsing rules and source mappings will be continuous labor.

**Funding / adoption traps**
- Neighborhood associations, tenant groups, and hyperlocal media have limited budgets.
- Foundation/newsroom pilots may not fund the boring QA operations after launch.
- Subscriptions are hard when the product is only valuable during rare nearby events.

**Legitimacy / privacy risks**
- Photos may include addresses, people, license plates, or private property context.
- Alerts can be weaponized for anti-housing mobilization or harassment of applicants.
- Late/mistaken alerts can create blame and procedural confusion.

**Provisional verdict: weak**
- Compelling story, but operationally fragile. Salvage only in one city with a paid human-verification operation and explicit false-negative disclaimers.

---

## 7. Tenant Displacement Docket

**Fatal risks**
- Source data may not reveal tenant-impacting cases early enough to be useful. If demolition/alteration/rezoning signals arrive after legal strategy windows close, the product becomes post-hoc anxiety.
- Safety and misuse risks are severe: landlords, speculators, or anti-tenant actors could use the watchlist to identify organizing targets or vulnerable buildings.
- The product may imply legal rights or deadlines that vary building-by-building and tenant-by-tenant.

**Nonfatal risks**
- “Tenant-impacting” classification is legally nuanced and locally specific.
- Human-reviewed alerts may not scale beyond one city/type.
- Translating alerts into action without legal advice is hard when the next step often is legal advice.

**Duplication / prior-art concerns**
- Housing legal-aid orgs, tenant unions, city open-data teams, anti-displacement coalitions, and local journalists already maintain ad hoc trackers in some markets.
- Generic land-use/permit products overlap, but may lack tenant framing.
- The moat is partner workflow and local rules, not data technology.

**Data / maintenance traps**
- Rent-stabilized lists, assessor records, code enforcement, eviction data, ownership structures, permit descriptions, and planning cases are fragmented and legally constrained.
- Data can be stale or wrong in ways that harm tenants: owner names, unit counts, stabilization status, current occupancy.
- Outcome tracking requires legal/procedural knowledge and may involve non-public settlements or negotiations.

**Funding / adoption traps**
- Legal aid and tenant unions need this but are underfunded and overloaded.
- Council discretionary/foundation funding is politically vulnerable.
- Direct renter adoption is difficult because users may only need it during crisis and may not trust unknown tools.

**Legitimacy / privacy risks**
- High privacy/safety risk: building-level alerts can expose tenant vulnerability, organizing activity, or displacement risk.
- Multilingual and undocumented tenants may avoid tools that collect address or status data.
- A wrong alert can cause panic; a missed alert can create reliance harm.

**Provisional verdict: salvage**
- The pain is real and mission-critical, but it should not be broad public infrastructure by default. Salvage as a partner-controlled legal-aid/tenant-union internal tool with strict access controls.

---

## 8. Conditions Keeper / Outcome Graph

**Fatal risks**
- The promise “whether promised conditions survived” may require legal interpretation and enforcement data that is not public, structured, or timely.
- Ambiguous condition language can make the product look like it is accusing officials/developers of noncompliance without enough evidence.
- Users may want causality (“did my comment matter?”), but the product can only safely provide correlation and status labels.

**Nonfatal risks**
- Continued dates and appeal deadlines are easier than condition enforcement; the candidate may overreach by bundling them.
- PDF extraction from minutes, attachments, staff reports, and resolutions will produce noisy outputs requiring human review.
- Post-action engagement may have lower user urgency than pre-deadline alerts.

**Duplication / prior-art concerns**
- Councilmatic/Legistar already expose actions, votes, minutes, and subscriptions in some jurisdictions.
- Decidim accountability and MAPLE-style receipts cover the conceptual loop.
- The differentiated condition-object schema may be speculative unless more than one downstream product consumes it.

**Data / maintenance traps**
- Conditions often live across staff reports, motions, amended resolutions, recorded covenants, permit systems, inspection records, and enforcement databases.
- “Final” documents can lag or change after meetings.
- Federal response-to-comments and local land-use conditions are very different data models; combining them may create false generality.

**Funding / adoption traps**
- Watchdog/newsroom/foundation money may fund investigations but not a durable SaaS.
- Municipal transparency contracts are politically awkward if the tool spotlights noncompliance.
- Neighborhood councils may lack budgets and may only care about a few cases per year.

**Legitimacy / privacy risks**
- Lower PII risk if it tracks cases, but reputational/legal risk from overclaiming violations or impact.
- Outcome receipts can disappoint users if most labels are “not found” or “no observable effect.”

**Provisional verdict: salvage**
- Salvage the narrow “next window / continued / appeal deadline” receipt loop. Attack the broader condition/enforcement graph as too interpretive and data-poor for v1.

---

## 9. CareRule Scout / Benefits Plainwatch

**Fatal risks**
- Wrong or oversimplified benefits alerts can cause panic, missed action, or harmful choices for disabled people, families, and care recipients.
- Medicaid waivers, SPAs, state rules, manuals, and transmittals are legally nuanced; “plain-language what might change” can drift into unauthorized legal advice.
- The data domain is fragmented across federal and state sources, and often the real policy change is in guidance, contracts, rate tables, manuals, or implementation memos rather than formal rulemaking.

**Nonfatal risks**
- Expert review is required, which limits speed and margins.
- Direct-to-recipient alerts are deferred, but without them the product may be mainly a professional policy tool for orgs that already monitor changes.
- Profile-based relevance requires collecting sensitive program, disability, family, provider, and geography information.

**Duplication / prior-art concerns**
- Legal aid, protection-and-advocacy orgs, disability coalitions, provider associations, Medicaid consultants, and policy newsletters already monitor parts of this space.
- Commercial trackers serve institutional policy teams; the gap is navigator/family translation, but that gap requires trust more than software.
- PolicyEngine is tangential but signals that benefits domains attract specialized modeling efforts.

**Data / maintenance traps**
- State portals are inconsistent; Medicaid.gov waiver/SPA postings may be incomplete or hard to map to practical impact.
- Rules may have comment windows, but operational impact depends on later approvals, state implementation, managed-care contracts, and county practices.
- Keeping summaries current across 2-3 states plus CMS may already be too much without paid experts.

**Funding / adoption traps**
- Foundations may fund pilots, but paid seats for P&A/legal-aid/care nonprofits compete with direct service budgets.
- Small providers may pay only if reimbursement/compliance impact is clear; families likely cannot be the payer.
- Ombudsman partnerships could create neutrality and liability constraints.

**Legitimacy / privacy risks**
- High sensitivity: disability, Medicaid status, care needs, family circumstances.
- Alerts can be misread as eligibility determinations or legal advice.
- Panic/misinformation controls are not optional; they are core product requirements.

**Provisional verdict: weak**
- Mission-important but high-stakes and expert-heavy. Salvage as a back-office expert-reviewed digest for a single trusted partner, not a broad profile-based alert product.

---

## 10. Childcare Rule Radar / CareNotice Counsel

**Fatal risks**
- The target buyers are exhausted, budget-constrained operators who may not pay for or act on alerts unless an association/CCR&R makes it unavoidable.
- Incorrect interpretation can create license-risk anxiety, but avoiding interpretation makes the product just another newsletter.
- State-by-state childcare regulation is highly fragmented; one-state MVP may not prove scalable economics.

**Nonfatal risks**
- Providers may care more about compliance after adoption than comments before adoption.
- Alerts must distinguish license type, capacity, subsidy participation, food program, Head Start, staffing model, and local rules; onboarding may be burdensome.
- Manual filing/receipt upload reduces action-loop elegance.

**Duplication / prior-art concerns**
- Childcare associations, CCR&R agencies, shared-services alliances, licensing agencies, and compliance-training vendors already communicate rule changes.
- The product overlaps with “RuleRadar for Small Operators” patterns and may be a vertical newsletter plus comment coach.
- Commercial compliance/training platforms could add rule alerts as member content.

**Data / maintenance traps**
- State registers, agency hearings, board calendars, CCDF notices, licensing manuals, emergency rules, and guidance emails are inconsistent.
- Practical effect often depends on agency interpretation, inspection practice, and subsidy-contract rules not visible in formal notices.
- Taxonomy maintenance for licensing categories is state-specific and brittle.

**Funding / adoption traps**
- Low-cost per-site subscriptions may not cover expert review and source maintenance.
- Association bundles require partnership sales and revenue sharing.
- Funders may prefer direct supply subsidies/training over civic-comment tooling.

**Legitimacy / privacy risks**
- Moderate privacy risk from business/license profiles and compliance concerns.
- “Counsel-lite” positioning risks sounding like legal/compliance advice.
- Could be perceived as helping operators resist safety regulations unless framed carefully.

**Provisional verdict: salvage**
- More commercially plausible than many civic ideas, but only if bundled through an association and tied to concrete compliance/cost outcomes. As standalone civic participation, weak.

---

## 11. Pharmacy Docket Desk

**Fatal risks**
- Independent pharmacies already sit in dense association, PSAO, wholesaler, buying-group, and consultant networks. The product must beat trusted incumbent channels, not just generic policy trackers.
- Incorrect legal/regulatory interpretation around DEA/FDA/CMS/state boards/PBMs can create serious liability anxiety.
- The domain is politically and commercially contested; neutral “counsel-lite” may be impossible when reimbursement, PBMs, controlled substances, and scope fights are advocacy-heavy.

**Nonfatal risks**
- Owners are overloaded; they may ignore even relevant alerts unless there is immediate reimbursement/audit/compliance impact.
- State board calendars and Medicaid notices are inconsistent.
- Implementation checklists may be more valuable than comment prompts, shifting the product toward compliance consulting.

**Duplication / prior-art concerns**
- State pharmacy associations, NCPA, PSAOs, wholesalers, PBM consultants, compliance vendors, and law firms already provide alerts.
- Quorum/FiscalNote/Plural serve larger association policy staff.
- The gap is personalization for small owners, but associations may already deliver “good enough” newsletters and calls to action.

**Data / maintenance traps**
- Federal Register/Regulations.gov are manageable; state boards, Medicaid bulletins, PBM legislation, and emergency rules are fragmented.
- “Likely affects your license/profile” requires maintaining pharmacy-type, services, payer, Medicaid, compounding, DME, vaccination, and controlled-substance mappings.
- Board decisions may happen in minutes, guidance, FAQs, or enforcement patterns outside formal rulemaking.

**Funding / adoption traps**
- Selling through buying groups/PSAOs/associations gives distribution but compresses margins and requires trust.
- Per-pharmacy subscriptions face SMB churn and “association already sends this” objections.
- Sponsors may want advocacy slant, undermining neutrality.

**Legitimacy / privacy risks**
- Business-profile data may reveal services, payer mix, controlled-substance exposure, audit concerns.
- Advice disclaimers may not prevent users from relying on memos as legal guidance.

**Provisional verdict: weak**
- Potentially fundable, but differentiation is suspect. Kill unless discovery shows associations/PSAOs fail a specific high-cost alert job that owners will pay separately to solve.

---

## 12. Schoolyard Radius

**Fatal risks**
- The product can easily become anti-housing mobilization wrapped in child safety language.
- Child-centered alerts require careful handling of school/childcare locations, walking routes, and possibly parent/community participation data; the reputational risk of misuse is high.
- Many nearby projects will have ambiguous or indirect child impact, making ranking subjective and contested.

**Nonfatal risks**
- PTA leaders and principals are time-constrained and may not want another alert channel.
- Public schools only in MVP avoids some privacy issues but misses childcare/private/after-school populations.
- “Construction staging, traffic circulation, environmental review” may require different data sources and expertise.

**Duplication / prior-art concerns**
- Safe Routes, Vision Zero, district facilities planning, environmental justice tools, city project pages, coUrbanize/PublicInput, and local advocacy groups overlap.
- The distinct “decision-window” framing is real but may be a feature of land-use/radius products rather than standalone.
- Prior seasoned ideas had SchoolRule Window folded into this because standalone education-rule alerts were weak; that consolidation may still be too broad.

**Data / maintenance traps**
- School/childcare GIS, walking corridors, crash data, GTFS, environmental layers, Accela/EnerGov, and Legistar all have different update cycles and quality.
- Project impact cannot be inferred from proximity alone; a project 1,000 feet away may be irrelevant, while a route-disrupting project farther away may matter.
- Outcome/condition tracking inherits all Conditions Keeper problems.

**Funding / adoption traps**
- PTA councils and schools often lack discretionary tech budgets.
- Safe Routes/health/environment grants are project-based and may not sustain product operations.
- Districts may avoid tools that mobilize parents against city projects or expose district inaction.

**Legitimacy / privacy risks**
- Child safety framing can inflame public meetings and stigmatize housing, shelters, or infrastructure projects.
- Parent/location subscription data is sensitive.
- Must avoid implying official school endorsement of campaigns.

**Provisional verdict: weak**
- The child-safety frame is powerful but dangerous. Salvage only as mitigation-focused support for trusted school/district partners, not open-ended public mobilization.

---

## 13. Open Issue Escalator

**Fatal risks**
- The main risk in the slate is likely true: most 311 complaints never connect to an actionable public lever. If so, the core conversion engine rarely fires.
- Clustering complaints into budget/policy evidence may raise expectations that testimony will fix service delivery, when the bottleneck may be operations, procurement, staffing, or capital backlog.
- Departments may resist a product that turns unresolved tickets into public pressure campaigns.

**Nonfatal risks**
- Complaint data is noisy, duplicated, unevenly reported, and biased toward neighborhoods with more access/trust.
- Matching issue clusters to agenda items or budget lines is semantically hard and may produce spurious links.
- Residents with chronic issues may be too frustrated to engage in another process.

**Duplication / prior-art concerns**
- Open311, FixMyStreet/SocietyWorks, SeeClickFix-style products, BoardStat, council office workflows, and city dashboards already cover complaint intake/monitoring.
- The new piece is escalation to civic levers, but that may be rare and labor-intensive.
- mySociety/SocietyWorks shows a B2G model, but also means a mature incumbent exists in the service-reporting adjacent space.

**Data / maintenance traps**
- Open311 availability and fields vary; many cities lack clean public status histories.
- Legistar budget/procurement/committee items are not written in resident complaint vocabulary.
- Equity overlays can reveal disparities but not necessarily actionable deadlines.

**Funding / adoption traps**
- Council/public advocate pilots are political and may not survive administration changes.
- Departments may buy internal analytics, not public escalation.
- Newsroom/foundation support can fund watchdog stories, not ongoing routing operations.

**Legitimacy / privacy risks**
- Complaint locations can expose residents, encampments, accessibility needs, flooding damage, or neighborhood vulnerabilities.
- Clustering can misrepresent individual complaints as a collective demand.
- Equity framing based on biased complaint data can produce misleading conclusions.

**Provisional verdict: weak**
- Strong civic narrative, weak conversion mechanics. Salvage only for one issue category where a known public lever recurs predictably, such as annual capital planning for ADA sidewalks or flooding.

---

# Cross-candidate kill shots

1. **Most candidates assume source data reveals the action window early enough.** That is unproven for local land use, permits, benefits implementation, board calendars, and 311-to-budget escalation.
2. **“Human review” appears as a mitigation but often means the business is services-heavy.** If correctness requires experts or local operators, software margins and scale claims should be discounted.
3. **The slate repeatedly sells trust primitives into contested legitimacy spaces.** Verification, consensus, receipts, affected status, and outcome labels are not neutral UI components; they redistribute credibility.
4. **Funding is weakest where civic impact is strongest.** Tenants, families, residents, PTAs, newsrooms, legal aid, and neighborhood groups often need the tools but cannot sustain them.
5. **The prior-art gap is real but not automatically a business.** Volunteer projects died and commercial tools avoided this seam because sustaining data quality, not imagining product surfaces, is the hard part.
