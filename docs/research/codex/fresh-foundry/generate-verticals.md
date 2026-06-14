# Fresh Civic-Tech Verticals: Lite In-House Counsel for Underserved Small Operators

Lens: small operators who cannot afford policy counsel, but lose money or licenses when they miss comment windows, compliance elections, hearings, renewals, or implementation dates.

## 1. CareNotice Counsel — rule radar for independent childcare centers

### Target user
Independent childcare centers, family childcare homes, Head Start subcontractors, and small after-school programs in one state cluster, starting with operators serving subsidy/voucher families.

### Painful trigger / deadline
A state child-care agency proposes changes to subsidy reimbursement rates, staff-child ratios, background-check procedures, QRIS requirements, food-program paperwork, or licensing rules. The operator gets a PDF notice or trade-association email too late, misses the public-comment window or rate-setting hearing, then absorbs a reimbursement cut, new staffing burden, or licensing deficiency.

### Data / protocols / repos to build on
- State register / administrative bulletin RSS, HTML, and PDF notices.
- State childcare licensing-board calendars and agency hearing pages.
- Child Care and Development Fund plan/amendment notices from state agencies and HHS/ACF.
- `Regulations.gov` + Federal Register for HHS/ACF federal rules.
- City Scrapers pattern for agency calendars; MAPLE-style digest/action archive; DocketClock-style deadline objects; RuleBox-style cheap classification rules.
- Optional: NACCRRA/Child Care Aware provider datasets only for enrichment, not as system-of-record.

### Action loop
Operator enters license type, county, capacity, subsidy participation, ages served, and food-program participation. The service monitors proposed rules and hearings, routes items through a childcare-specific classifier, then sends a card: “This may affect staffing ratios for toddlers; comment closes May 14; hearing is May 8; likely cost: one extra aide at your capacity.” The action flow asks for concrete facts — waitlist, staffing vacancy time, subsidy share, weekly cost — drafts a non-template comment, files or guides filing, stores the receipt, and watches the final rule for whether the issue was addressed.

### Why not duplicate
Generic policy trackers are too expensive and require docket literacy. Associations cover big issues but do not personalize by license type, subsidy mix, or county. Government portals publish notices but do not translate “proposed amendment to 55 Pa. Code Chapter X” into “your infant room ratio may change.” This is not a broad parent-advocacy app; it is operator survival counsel.

### MVP
One state, one operator type, and three source classes: state register notices, childcare agency hearings, and HHS/ACF federal rules. Human-review every alert in beta. Support comment drafting and manual receipt upload before attempting automated submission.

### Funding path
Per-site subscription priced below one hour of attorney time; state childcare association bundle; philanthropic subsidy for providers in low-income areas; later white-label for shared-services alliances and childcare business coaches.

### Fatal risk
State notices are too inconsistent and politically sensitive to trust without human review. If alerts miss a licensing-critical change, the product loses credibility immediately.

---

## 2. Pharmacy Docket Desk — compliance counsel for independent pharmacies

### Target user
Independent retail pharmacies, compounding pharmacies, durable medical equipment counters inside pharmacies, and small long-term-care pharmacy operators.

### Painful trigger / deadline
A CMS, DEA, FDA, state board of pharmacy, Medicaid agency, or PBM-related state bill changes reimbursement, prior authorization, controlled-substance reporting, compounding rules, inventory requirements, vaccination authority, or audit exposure. The pharmacy owner misses the comment deadline or board meeting and later faces clawbacks, new software costs, or loss of service line.

### Data / protocols / repos to build on
- Federal Register + `Regulations.gov` for CMS, FDA, DEA, HHS/OIG rules.
- Mirrulations S3 history and `mirrulations-search` schema for dockets, open comment periods, and collections.
- Open States / Plural API for state PBM, Medicaid, scope-of-practice, and board bills.
- State pharmacy-board agenda pages and disciplinary/rulemaking calendars via City Scrapers-style spiders.
- NABP/e-profile links as reference only; not a primary data dependency.
- MAPLE notification/event model; WriteToThem-style routing for legislators/boards; generator-critic review for legal-risk summaries.

### Action loop
Onboarding captures NPI/NCPDP type, state licenses, Medicaid participation, compounding status, DMEPOS enrollment, controlled-substance schedules handled, and services offered. Alerts are framed as “commercial/legal exposure memos”: effective date, comment deadline, affected workflows, suggested evidence, and whether an association is already acting. The product produces a pharmacist-specific comment or board testimony, queues reminders before the hearing, records confirmation, then tracks final rule, bill status, or board vote and produces an implementation checklist.

### Why not duplicate
FiscalNote/Quorum serve lobbyists and chains; pharmacy associations send newsletters but do not maintain a personalized deadline/action file for each independent. Compliance SaaS focuses on current obligations, not proposed changes while there is still time to act. This is a vertical counsel inbox for the owner-operator.

### MVP
Start with one state plus federal CMS/DEA/FDA, targeting independent pharmacies that offer vaccines and Medicaid. Track only open comment periods, board hearings, and state bills with explicit pharmacy terms. No claims of legal advice; summaries cite source text and confidence.

### Funding path
Monthly subscription through buying groups, PSAOs, state pharmacy associations, or wholesaler-sponsored member benefits. Add premium “implementation checklist” and audit-prep exports.

### Fatal risk
Pharmacy owners may already trust associations and ignore another alert channel unless it clearly saves money or prevents audit exposure. Also, incorrect interpretation creates legal-liability anxiety.

---

## 3. PermitShield Auto — deadline monitor for small auto repair and body shops

### Target user
Independent auto body shops, collision repair centers, small mechanics, tire shops, smog-check stations, and mobile repair operators, starting in air-quality-regulated metro areas.

### Painful trigger / deadline
A city, county, state air district, environmental agency, fire marshal, or occupational-safety body changes VOC paint limits, spray-booth permits, hazardous-waste handling, stormwater rules, zoning use permits, inspection schedules, or smog-program requirements. The shop misses the workshop/comment deadline and later gets hit with equipment upgrades, fines, or permit delays.

### Data / protocols / repos to build on
- Local air-quality district rulemaking calendars and workshop notices.
- State environmental agency rulemaking pages and registers.
- EPA dockets via Federal Register, `Regulations.gov`, and Mirrulations for national air/waste rules.
- Local council agendas via Legistar OData for zoning, fees, and business-license ordinances.
- Fire-code / building-code adoption hearings from municipal agenda systems.
- City Scrapers diff/dedup pattern; Legistar OData; Open States for state bills; RuleBox classifiers for NAICS/operator terms.

### Action loop
The shop enters address, NAICS/services, spray booth status, hazardous-waste generator category, smog license, number of employees, and equipment dates. The system resolves jurisdiction and monitors air district + city + state sources. Each alert says: “Rule 1151 amendment workshop in 12 days; affected if you use solventborne coatings; likely action: submit equipment-cost data or attend workshop.” It collects quotes, downtime estimates, compliance history, and customer impacts, then drafts a shop-specific comment or testimony and tracks workshop notes, board adoption, effective date, and compliance tasks.

### Why not duplicate
Environmental compliance consultants help after a rule is real; policy trackers are not priced for five-bay shops; city portals are impossible to watch across air district, city, fire, and state layers. This is not a generic small-business city-hall tracker; it is a permit-and-rule early-warning system for auto shops.

### MVP
One air district and its largest Legistar city. Track only auto-refinish VOC rules, hazardous-waste notices, business-license fees, and zoning/use-permit hearings. Deliver alerts by SMS/email with human-verified source links and manual filing instructions.

### Funding path
Trade-association bundle, insurer/carrier risk-prevention sponsorship, paint/equipment distributor channel, or $49–$99/month per shop for compliance-deadline monitoring.

### Fatal risk
The jurisdiction stack is fragmented and local consultants may own the relationship. If the MVP tries to cover every permit type, it becomes an unmaintainable scraper graveyard.

---

## 4. TenantCare Rule Desk — counsel-lite for small assisted-living and group-home operators

### Target user
Small assisted-living facilities, adult residential facilities, behavioral-health group homes, sober-living homes where regulated, and disability-service providers with 5–80 beds.

### Painful trigger / deadline
State health or human-services agencies propose changes to staffing ratios, medication administration, incident reporting, reimbursement, fire/life-safety rules, admission/discharge rights, or inspection protocols. Local zoning boards also hear spacing, conditional-use, or neighborhood-opposition matters. Operators miss comment periods or hearings and then face impossible staffing mandates, reimbursement gaps, or zoning restrictions.

### Data / protocols / repos to build on
- State administrative registers and health/human-services rulemaking calendars.
- Medicaid waiver amendment notices, HCBS settings-rule notices, and CMS/HHS dockets via Federal Register and `Regulations.gov`.
- State legislature bills via Open States / Plural.
- Local zoning/council hearings via Legistar OData and City Scrapers-style spiders.
- ArcGIS/Socrata zoning layers where available for spacing/conditional-use overlays.
- Decidim-style verification concepts for facility-address standing; MAPLE-style watchlists/digests; Pol.is-style consensus only for trade-group campaigns.

### Action loop
Onboard by facility license, bed count, payer mix, county, property address, service population, and waiver participation. The product creates a “regulatory calendar” of comment deadlines, hearings, implementation dates, and renewal/transition dates. Alerts are written as mini counsel memos: affected license types, operational burden, deadline, action options, evidence needed, and reputational sensitivity. The action flow gathers staffing rosters, vacancy rates, reimbursement math, resident-impact facts, and anonymized scenarios; drafts a comment; reminds the operator or association before hearings; and tracks final rule, waiver approval, local vote, and implementation tasks.

### Why not duplicate
Large provider associations and counsel represent chains; small homes are often isolated and discover changes through inspections or angry neighbors. Existing compliance tools manage current checklists, not proposed rules and public processes. Land-use tools track projects, not the intersection of care licensing + zoning + Medicaid deadlines.

### MVP
One state with a clear administrative register and one facility class, e.g. adult residential facilities or assisted living. Track state agency rulemaking, Medicaid waiver notices, and Legistar zoning hearings in two cities. No resident-data storage; use anonymized operational evidence.

### Funding path
Provider-association bundle, managed-care/community-care network sponsorship, per-facility subscription, or foundation-backed access for homes serving Medicaid residents. Later upsell implementation checklists and board-packet exports.

### Fatal risk
The sector is politically and legally sensitive: bad guidance can harm residents or appear to help operators resist safety rules. The product must emphasize substantive evidence, resident impact, and source-cited informational guidance, not anti-regulation campaigning.
