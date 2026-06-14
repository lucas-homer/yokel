# Curated slate for debate

No final ranking implied. These are clustered candidates after merging overlapping generator outputs and prior research themes.

---

## CommentWindow Registry / DocketClock

- **Merged source lenses:** infrastructure `CommentWindow Registry`; sustainability `ClerkLoop` deadline-object layer; prior DocketClock / deadline API research.
- **Target user:** Civic-data teams, associations, newsrooms, vertical rule-radar products, and eventually clerks/agencies that need reliable public participation deadlines.
- **Pain/deadline:** Comment windows, hearings, continuances, and final-action links are buried across Federal Register, Regulations.gov, Legistar, state registers, PDFs, and clerk workflows; a wrong or missed deadline destroys trust.
- **Core solution:** SLA-backed public-comment/hearing deadline objects with provenance, confidence, status changes, webhooks, RSS/ICS, and bulk exports.
- **Data/building blocks:** Federal Register API, Regulations.gov v4 read APIs, Mirrulations/mirrulations-search, Legistar OData, City Scrapers patterns, Open Civic Data IDs/schema, ICS/webhooks.
- **Gap filled:** A normalized “what is open, what is closing, where can action be filed?” substrate for downstream civic tools; not another engagement portal.
- **MVP:** Federal-only deadline API with canonical fields, confidence labels, watchlists, webhooks, CSV/bulk export, and source-provenance dashboard for design partners.
- **Funding path:** Free public schema/basic data; paid API volume, webhooks, SLA, historical snapshots, and deadline-verification support for associations/newsrooms/vertical products.
- **Main risk:** Deadline correctness is unforgiving, and state/local expansion can become a scraper-maintenance graveyard.

---

## RecordReady Clerk Intake

- **Merged source lenses:** deliberation `RecordReady Triage Desk`; sustainability `ClerkLoop`; infrastructure `Comment Receipt & Outcome Graph` as downstream receipt primitive.
- **Target user:** City/county clerks, planning-board staff, agency public-comment coordinators, and small jurisdictions without robust engagement operations.
- **Pain/deadline:** In the 72 hours before a meeting or comment close, staff must turn messy emails, voicemails, webforms, screenshots, attachments, and petition links into an official-record packet.
- **Core solution:** Clerk-facing intake desk that matches inbound public input to agenda items/dockets, clusters duplicates, extracts claims/attachments/location references, sends receipts, and exports record-ready packets.
- **Data/building blocks:** Legistar OData, OCD Event/Organization concepts, City Scrapers for non-Legistar meetings, MAPLE-style receipts/archive, Decidim-style verification tiers, IMAP/Gmail/Graph ingestion, CSV/webform import, voicemail transcription.
- **Gap filled:** Starts from the government’s messy inbound reality rather than asking residents to use a new engagement portal.
- **MVP:** One Legistar jurisdiction, one intake mailbox, agenda-item matching, duplicate clustering, staff review queue, PDF/CSV packet export, and receipt emails.
- **Funding path:** B2G SaaS for clerks/agencies; municipal innovation/open-government pilots; add-on for agenda-management consultants and smaller jurisdictions.
- **Main risk:** Staff may not trust automated classification near the official record unless review time drops materially without legal/procedural risk.

---

## Consensus Comment Room

- **Merged source lenses:** deliberation `Consensus Comment Composer`; sustainability `Consensus Docket Room`; prior `Consensus Comment`; infrastructure `Comment Receipt & Outcome Graph`.
- **Target user:** Civic nonprofits, neighborhood coalitions, associations, issue campaigns, and agencies/foundations sponsoring better high-volume public comment.
- **Pain/deadline:** A rulemaking or hearing window closes in 10–60 days; organizers have passion and petition lists, but duplicate form letters are discounted and raw opinions are hard to convert into substantive comments.
- **Core solution:** Docket-native deliberation room that clusters participant views, surfaces consensus and minority concerns, collects attested facts, and produces a small set of official-record comment packets.
- **Data/building blocks:** Regulations.gov, Federal Register, Mirrulations, Legistar for local items, Pol.is/vTaiwan consensus patterns, similarity detection, MAPLE-style receipts and follow-up.
- **Gap filled:** Moves from volume mobilization to action quality: fewer, distinct, evidence-backed comments with visible consensus strength.
- **MVP:** One domain of federal dockets; organizer-created room; 7-question evidence interview; human-reviewed consensus packet; manual filing instructions/receipt capture before any submission automation.
- **Funding path:** Per-campaign nonprofit/association fee; foundation-funded public-interest rooms; agency or ombuds pilots only with public exports and neutrality safeguards.
- **Main risk:** Perception of AI-laundered astroturf or agency-funded consensus laundering if provenance, dissent, and user attestation are weak.

---

## Affected-Party Verifier / Notice Compact

- **Merged source lenses:** deliberation `Affected-Party Verifier`; sustainability `Notice Compact`; prior `Block Whip` verification/action mode.
- **Target user:** Planning departments, zoning boards, legal-aid housing teams, neighborhood organizers, planning commissioners, and applicants who need auditable affected-neighbor participation.
- **Pain/deadline:** In rezoning, variance, permit appeal, and environmental-review windows, officials receive broad comments but cannot easily distinguish affected residents, renters, owners, nearby businesses, workers, parents, or general public.
- **Core solution:** Neutral affected-status layer: define a parcel/radius/district/polygon, privately verify relationship to the area, collect comments, and report distinct arguments/counts by status without excluding unverified speakers.
- **Data/building blocks:** Parcel/address GIS via ArcGIS/Socrata/assessor data, Legistar/City Scrapers agendas, MapIt-style geocoding, Decidim verification tiers, privacy-preserving address hashing, optional USPS validation.
- **Gap filled:** Trust primitive for official packets and case-scoped organizing; not a generic neighborhood discussion forum or developer project page.
- **MVP:** One city and one process type: zoning variances within notice radius; address-to-radius verification, renter self-attestation, private audit trail, staff-reviewed packet.
- **Funding path:** Planning/legal-aid pilots, procedural-justice foundations, applicant-paid notice transparency with strict non-success-fee rules, API/add-on pricing for civic participation vendors.
- **Main risk:** Verification can become exclusionary, privacy-invasive, or perceived as developer/government capture.

---

## Concern Router / Civic RouteMap

- **Merged source lenses:** deliberation `Concern Router for Newsrooms and Hotlines`; infrastructure `Civic RouteMap`; prior routing/address-to-action research.
- **Target user:** Local reporters, library civic navigators, 311-style hotlines, community foundations, legal-aid help desks, associations, and civic-action products.
- **Pain/deadline:** A resident concern or rumor surfaces, but no one knows whether the live lever is a docket, council item, zoning hearing, school-board vote, agency rule, state bill, or official contact before the window closes.
- **Core solution:** Plain-language concern + location resolver that returns likely official processes/endpoints, confidence, deadlines, eligibility/verification requirements, and “why this matches.”
- **Data/building blocks:** Federal Register/Regulations.gov/Mirrulations deadline feeds, Open States/Plural, Legistar OData, City Scrapers, Census TIGER/Line, local GIS boundaries, MapIt/WriteToThem routing patterns, RuleBox classifiers.
- **Gap filled:** The missing bridge from ambient public concern to the procedural venue where input actually counts.
- **MVP:** One metro area plus federal dockets; navigator-facing intake form; search across federal dockets, one state via Open States, and one Legistar city/county; conservative confidence thresholds.
- **Funding path:** Library/newsroom/community-foundation pilots; civic information philanthropy; SaaS/API for newsrooms, advocacy coalitions, legal-aid and civic-action products.
- **Main risk:** Wrong routing burns trust; “no reliable official path found” must be a supported outcome, not a failure state.

---

## NoticeNail / Lot Line

- **Merged source lenses:** land-use `NoticeNail`; prior `Lot Line`; infrastructure `Civic RouteMap`/parcel-routing concepts.
- **Target user:** Tenants’ unions, neighborhood reporters, block-level volunteers, preservation groups, legal-aid partners, renters/homeowners in cities with poor digital planning feeds.
- **Pain/deadline:** A posted site notice appears with a hearing/appeal/comment deadline 10–20 days away; the people most affected may not see it, and the digital case record is hard to find.
- **Core solution:** Mobile photo capture + OCR + human verification creates a public case card, matches parcel/address/deadline, and alerts nearby subscribed addresses/orgs with filing/hearing steps.
- **Data/building blocks:** OCR for notice fields, county assessor/city parcel GIS/OpenAddresses, Accela/EnerGov/Socrata/ArcGIS case enrichment, Legistar planning items, City Scrapers, human QA queue.
- **Gap filled:** Resident-side missing-signal capture for legally posted notices that do not become friendly digital alerts.
- **MVP:** One city with frequent posted notices and poor discoverability; OCR address/case number/deadline only; verified case cards and radius alerts; no national permit database.
- **Funding path:** Local newsroom/foundation pilot; subscriptions for neighborhood associations, tenant groups, preservation nonprofits, hyperlocal media, and land-use legal clinics.
- **Main risk:** Missed or late notices create false security; data quality and timing may be too inconsistent without heavy human review.

---

## Tenant Displacement Docket

- **Merged source lenses:** land-use `Tenant Displacement Docket`; rulemaking `Benefits Change Plainwatch` where benefits/housing stability overlaps; prior land-use anti-displacement themes.
- **Target user:** Tenant organizers, legal-aid housing teams, renters in small buildings, community land trusts, anti-displacement coalitions.
- **Pain/deadline:** Demolition, condo conversion, lot merger, short-term-rental legalization, substantial alteration, or rezoning starts appeal/comment/relocation-assistance windows before tenants understand the threat.
- **Core solution:** Early-warning watch for tenant-impacting planning/permit cases, translated into deadline cards, evidence prompts, testimony/appeal checklists, and outcome tracking.
- **Data/building blocks:** Accela/EnerGov/Socrata permits, ArcGIS parcel/planning layers, Legistar/City Scrapers agendas, rent-stabilized building lists, assessor data, code-enforcement/eviction data where legally usable, local rules library.
- **Gap filled:** Bridges land-use decision windows and tenant-defense workflows before displacement is locked in.
- **MVP:** One tenant-protection-rich city and one case type, e.g. demolition permits for rent-stabilized/multi-unit buildings; partner with one legal-aid/tenant-union anchor; human-reviewed alerts.
- **Funding path:** Legal-services innovation grants, housing foundations, council discretionary funding via nonprofit partner, organizational seats for tenant unions/community land trusts.
- **Main risk:** Privacy/safety concerns and landlord misuse; source data may not reveal tenant-impacting cases early enough.

---

## Conditions Keeper / Outcome Graph

- **Merged source lenses:** land-use `Conditions Keeper`; infrastructure `Comment Receipt & Outcome Graph`; prior `Closed the Loop`; sustainability `Open Issue Escalator` outcome-receipt pattern.
- **Target user:** Neighbors, neighborhood councils, local reporters, planning-law clinics, planning commissioners’ aides, and civic-action products needing post-action accountability.
- **Pain/deadline:** After “approved with conditions,” “continued,” or “appealable within X days,” residents lose the next actionable window and cannot tell whether promised conditions survived into final documents.
- **Core solution:** Bookmark a case/action; extract continuance dates, appeal deadlines, conditions, votes, amendments, final rules, or response-to-comments; send conservative outcome receipts and next-window reminders.
- **Data/building blocks:** Legistar actions/votes/minutes/attachments, City Scrapers agendas/minutes, Accela/EnerGov permit status/attachments, PDF text extraction, condition-object schema, Federal Register/Regulations.gov for federal receipt graph.
- **Gap filled:** The neglected after-action loop: what happened, what deadline comes next, and whether the record addressed the user’s issue.
- **MVP:** One city planning commission: track continued date, appeal deadline, and conditions of approval with manual extraction plus LLM-assisted human review.
- **Funding path:** Local journalism grants, civic watchdog nonprofits, neighborhood council subscriptions, planning-law clinics, municipal transparency contracts; API module for action products.
- **Main risk:** Ambiguous condition language and inaccessible enforcement data can produce false accusations or overclaim impact.

---

## CareRule Scout / Benefits Plainwatch

- **Merged source lenses:** rulemaking `CareRule Scout` and `Benefits Change Plainwatch`; verticals `TenantCare Rule Desk` where HCBS/assisted-living operator concerns overlap; prior Statehouse RuleWatch caution.
- **Target user:** Disability advocates, Medicaid/HCBS families, care recipients, legal-aid benefits navigators, protection-and-advocacy orgs, small HCBS providers.
- **Pain/deadline:** Federal CMS/HHS rules, Medicaid waiver amendments, state plan amendments, and state benefit rules open for comment with practical fears about service hours, eligibility, transportation, reimbursement, or recertification.
- **Core solution:** Profile-based rule/change alerts with source excerpts, confidence, plain-language “what might change,” guided lived-experience or organizational comments, receipt capture, and final-action explanation.
- **Data/building blocks:** Federal Register, Regulations.gov, Mirrulations, Medicaid.gov waiver/SPAs, CMS PDFs, state registers/eRulemaking portals, eCFR/GovInfo, state policy manuals/transmittal diffing, legal-aid issue taxonomies.
- **Gap filled:** Translates high-stakes benefits rulemaking from docket/register language into navigator and family workflows without pretending to be legal advice.
- **MVP:** One program and region, e.g. HCBS waiver families in 2–3 states plus federal CMS rules, with expert-reviewed summaries and no direct-to-recipient mass alerts until validated.
- **Funding path:** Disability/aging/health-access foundations; paid seats for P&A orgs, legal aid, care-coordination nonprofits, small provider associations; possible ombudsman partnerships.
- **Main risk:** Wrong alerts can cause panic or missed action; state Medicaid/benefits data is fragmented and legally nuanced.

---

## Childcare Rule Radar / CareNotice Counsel

- **Merged source lenses:** rulemaking `Childcare Rule Radar`; verticals `CareNotice Counsel`; prior `RuleRadar for Small Operators` verticalization.
- **Target user:** Home-based childcare providers, independent centers, small daycare directors, Head Start subcontractors, childcare associations, CCR&R agencies.
- **Pain/deadline:** Licensing, subsidy, staff-ratio, background-check, training, food-program, inspection, or reimbursement rules change with short comment/hearing windows and later create cost or license risk.
- **Core solution:** Operator-profiled rule radar that tells a provider whether a proposed rule likely affects their license type/capacity/subsidy participation, then helps produce distinct operational evidence comments and post-adoption compliance briefs.
- **Data/building blocks:** State administrative registers/bulletins, childcare licensing-board calendars, agency hearings, CCDF plan/amendment notices, Federal Register/Regulations.gov for HHS/ACF, eCFR, licensing-category taxonomy, RuleBox classifiers, MAPLE-style digest/archive.
- **Gap filled:** “Lite counsel” for small childcare operators who cannot decode state register notices or afford policy staff.
- **MVP:** One state, one provider type, three source classes: state register notices, childcare agency hearings, and HHS/ACF federal rules; human-reviewed beta alerts; manual filing/receipt upload.
- **Funding path:** State childcare association bundle, CCR&R networks, early-childhood funders, low-cost per-site subscription bundled with compliance training/shared-services alliances.
- **Main risk:** Budget-constrained exhausted buyers may ignore even accurate alerts unless associations bundle it and alerts clearly reduce cost/license risk.

---

## Pharmacy Docket Desk

- **Merged source lenses:** verticals `Pharmacy Docket Desk`; prior `ScopeWatch`/small-operator rule-radar lessons.
- **Target user:** Independent retail pharmacies, compounding pharmacies, DME counters, long-term-care pharmacy operators, state pharmacy associations, buying groups/PSAOs.
- **Pain/deadline:** CMS, DEA, FDA, state boards, Medicaid agencies, and PBM-related bills/rules can affect reimbursement, prior authorization, controlled substances, compounding, inventory, vaccination authority, or audit exposure before small owners hear in time.
- **Core solution:** Pharmacy-specific counsel-lite inbox: relevance memos, comment/board-hearing prompts, implementation checklists, receipt tracking, and final-rule/bill/board-vote updates based on license/profile.
- **Data/building blocks:** Federal Register/Regulations.gov, Mirrulations, Open States/Plural, state pharmacy-board calendars/agendas, Medicaid agency notices, City Scrapers patterns, MAPLE event/notification model, WriteToThem-style routing.
- **Gap filled:** Personalized regulatory action file for independent pharmacies, positioned between generic policy trackers and broad association newsletters.
- **MVP:** One state plus federal CMS/DEA/FDA; independent pharmacies offering vaccines and Medicaid; track open comment periods, board hearings, and explicit pharmacy bills; source-cited confidence labels.
- **Funding path:** Monthly subscription through buying groups, PSAOs, state associations, wholesalers as member-benefit sponsors; premium implementation/audit-prep exports.
- **Main risk:** Owners may trust associations already, and incorrect interpretation creates legal-liability anxiety.

---

## Schoolyard Radius

- **Merged source lenses:** land-use `Schoolyard Radius`; rulemaking `SchoolRule Window` for education-rule alerts; prior land-use alert/digest patterns.
- **Target user:** PTA leaders, principals, school-site councils, child-care operators, safe-routes advocates, district facilities staff, child-health/environment coalitions.
- **Pain/deadline:** Development, street, construction staging, toxic-site, environmental-review, or transportation changes near schools are discovered after the planning/comment/hearing window closes.
- **Core solution:** School/child-care radius and walking-corridor watch that ranks nearby decision windows by safety, traffic, construction, air/noise, and environmental relevance; prompts mitigation comments and tracks outcomes/conditions.
- **Data/building blocks:** State education/NCES/local district GIS, child-care licensing data, ArcGIS/Socrata/Accela/EnerGov planning data, environmental-review notices, Legistar/City Scrapers agendas, Safe Routes/crash/GTFS/Vision Zero layers, buffer/route geometry.
- **Gap filled:** Child-centered decision-window product, distinct from generic safe-routes planning tools or developer-hosted project pages.
- **MVP:** One metro area, public K–8 schools only, projects above threshold within 1,000 feet or walking corridors; three prompt categories: construction staging, traffic circulation, environmental review.
- **Funding path:** PTA council/district pilot, Safe Routes grants, local health/environment foundations, transportation-demand-management funds, district dashboard plus free PTA/community tier.
- **Main risk:** Can become anti-housing mobilization unless tightly framed around safety/mitigation and privacy-sensitive child data handling.

---

## Open Issue Escalator

- **Merged source lenses:** sustainability `Open Issue Escalator`; infrastructure `Comment Receipt & Outcome Graph`; prior FixMyStreet/Open311 and outcome-loop research.
- **Target user:** Residents, neighborhood groups, council offices, public advocates, public-works departments, local newsrooms, foundations focused on service equity.
- **Pain/deadline:** Chronic 311/service issues stay atomized; residents do not know when recurring problems become budget hearings, capital plans, procurement votes, committee agendas, or rule changes where testimony can matter.
- **Core solution:** Cluster unresolved service complaints and watch for the next real civic lever; alert residents when a hearing/vote/budget line appears; collect location-specific testimony; track votes, allocations, work orders, deferrals, or rejections.
- **Data/building blocks:** Open311 GeoReport v2, FixMyStreet/SocietyWorks lessons, Legistar budget/procurement/committee items, City Scrapers, MapIt-style jurisdiction matching, census/equity overlays, MAPLE digest/outcome receipts.
- **Gap filled:** Converts complaint systems into deadline-timed participation and budget/policy evidence rather than another ticket dashboard.
- **MVP:** One city with Open311 and Legistar; one issue category such as sidewalk/ADA hazards or flooding; cluster public 311 records, watch relevant agendas, collect testimony packets, track outcomes.
- **Funding path:** Council office/public advocate/department service-equity pilot, local newsroom/foundation support, then SocietyWorks-style SaaS for public-facing dashboards and internal analytics.
- **Main risk:** If most issues never connect to an actionable public lever, the product becomes another frustration dashboard.

---

# Discarded / merged

- **Civic SourceOps:** Useful reliability tooling, but too meta for the debate slate unless a paying civic-data operator exists. Merged as an operational requirement for CommentWindow Registry, RouteMap, and local-source products.
- **Permit Pulse:** Not strong as a standalone because most permits have no public action lever and notification fatigue is likely. Merged into NoticeNail/Lot Line, Tenant Displacement Docket, Schoolyard Radius, and Open Issue Escalator as a filtered digest layer.
- **ParcelWatch:** Valuable backend, but risky as a standalone infrastructure business before demand is proven. Merged into land-use candidates as scoped city/source normalization, not a broad national API promise.
- **Generic RuleRadar for Small Operators:** Too horizontal. Split into Childcare Rule Radar, Pharmacy Docket Desk, and pieces of CareRule/Benefits; other verticals like auto shops and group homes remain possible later wedges.
- **PermitShield Auto:** Plausible but narrower and more source-fragmented than pharmacy/childcare; defer unless an air-district/trade-association anchor funds the MVP.
- **TenantCare Rule Desk:** Merged into CareRule/Benefits for Medicaid/HCBS rule monitoring; separate assisted-living/group-home operator product deferred because of resident-safety and anti-regulation perception risks.
- **SchoolRule Window:** Merged into Schoolyard Radius as an education-adjacent child-impact alert; standalone state education-rulemaking is politically polarized and data-fragmented.
- **Concern Router vs Civic RouteMap:** Merged into one navigator/API candidate; separate consumer self-serve router deferred until professional navigator workflows prove accuracy.
- **Consensus Comment Composer vs Consensus Docket Room:** Merged into Consensus Comment Room; standalone deliberation network discarded.
- **Comment Workshop:** Kept as a required action module inside Consensus Comment, CareRule, Childcare, Pharmacy, and RecordReady flows rather than a slate candidate by itself.
- **Closed the Loop / Receipt Engine:** Merged into Conditions Keeper/Outcome Graph and embedded across candidates; weak standalone initial pull.
- **ClerkLoop:** Split between CommentWindow Registry and RecordReady Clerk Intake; broad resident watchlist + clerk SaaS bundle is too much for one MVP.
- **Notice Compact:** Merged into Affected-Party Verifier; applicant-paid model kept only as a funding option with neutrality safeguards.
- **Statehouse RuleWatch:** Not included as a generic 50-state product; folded into domain-specific rule products where source scope and payer are clearer.
- **Benefits-only/SNAP/TANF/UI Plainwatch:** Merged into CareRule/Benefits; direct-to-recipient alerts deferred until legal-aid review and panic/misinformation controls are proven.
- **Generic civic habit/streak product:** Discarded as too generic and not deadline/pain anchored.
- **Duplicate-of-incumbent engagement portals, generic discussion rooms, generic permit/newsletter feeds, and broad civic dashboards:** Dropped because they duplicate Granicus/PublicInput/EngagementHQ, Decidim/Consul, city portals, or existing policy-monitoring/newsletter patterns without a sharper deadline/action/outcome wedge.
