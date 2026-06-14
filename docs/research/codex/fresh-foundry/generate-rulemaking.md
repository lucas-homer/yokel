# Fresh Civic-Tech Ideas: Federal + State Rulemaking Legibility for Non-Experts

Lens: products that make federal and state rulemaking understandable and actionable for people who do **not** know docket numbers, agency jargon, or administrative-law procedure. These do not try to become a generic civic platform; each starts with a narrow, deadline-driven use case.

---

## 1. CareRule Scout — Medicaid and disability-service rule changes for families

### Target user
Parents, guardians, disability advocates, home-care recipients, and small HCBS providers who rely on Medicaid waivers, state plan amendments, EPSDT, home-care hours, prior authorization, or covered therapy services.

### Painful trigger / deadline
A proposed federal CMS rule, state Medicaid waiver amendment, state plan amendment, or state administrative rule opens for comment with a 15–60 day window. The practical fear is: “Will my child/client lose hours, eligibility, therapy access, transportation, or reimbursement — and do I have time to object?”

### Data sources / protocols to build on
- **Federal Register API** and **Regulations.gov v4 API** for CMS/HHS proposed rules and comment periods.
- **Mirrulations S3/history** for prior comments, docket history, and final-rule comparisons.
- **Medicaid.gov waiver and state plan amendment pages**, CMS state waiver PDFs, and state Medicaid bulletin feeds.
- **State registers / eRulemaking portals** for Medicaid agency rules; start with 3–5 states with RSS/API/HTML that can be monitored reliably.
- **eCFR / GovInfo** for current CFR text and authority references.
- Architecture pattern: parallel fan-out over federal + selected state sources, then generator-critic summary review because false interpretation is high-harm.

### Action loop
1. User selects state, program, service type, and plain-language concern: “home care hours,” “autism therapy,” “transportation,” “eligibility renewal.”
2. System alerts only when a rule likely touches that profile, with a deadline, confidence level, source excerpts, and “what might change.”
3. Guided story builder asks for concrete facts: service hours, wait time, cost, care disruption, rural access, provider shortage.
4. User files via Regulations.gov or receives state-specific filing instructions; the product stores a receipt or screenshot.
5. When the final rule / waiver approval / agency response appears, the product labels whether the user’s issue was addressed, ignored, narrowed, or still pending.

### Why this does not duplicate incumbents
FiscalNote/Quorum/Plural are expensive policy-monitoring tools for professionals. Regulations.gov is a portal, not an “is my service at risk?” translator. Disability-rights groups send alerts, but usually per campaign and without personalized cross-state monitoring or outcome receipts.

### MVP
One user segment, one state cluster, one program: e.g., HCBS waiver families in California, New York, and Massachusetts plus federal CMS rules. Human-reviewed summaries, weekly digest, deadline calendar, comment coach, and outcome tracker. No national state coverage promise.

### Funding path
Foundation grants from disability, aging, and health-access funders; paid seats for protection-and-advocacy organizations, legal aid, care-coordination nonprofits, and small provider associations; eventually state Medicaid ombudsman / managed-care quality partnerships if neutrality is protected.

### Fatal risk
State Medicaid rule data is too fragmented and legally nuanced to summarize safely. A wrong alert could create panic or missed action. The product dies if it cannot maintain high-confidence source coverage and strong “not legal advice” trust boundaries.

---

## 2. Childcare Rule Radar — licensing and subsidy changes for small childcare operators

### Target user
Home-based childcare providers, small daycare directors, family childcare associations, and resource-and-referral agencies.

### Painful trigger / deadline
A state licensing agency or federal HHS/ACF rule proposes changes to staff ratios, background checks, training hours, subsidy reimbursement, inspection rules, facility standards, or eligibility paperwork. Operators may have only weeks to comment before a rule changes staffing costs or threatens license compliance.

### Data sources / protocols to build on
- **Federal Register API** and **Regulations.gov** for HHS/ACF and Child Care and Development Fund rules.
- **State administrative registers**, state child-care licensing rule pages, and agency bulletin RSS/email archives.
- **State eRulemaking systems** where available; fallback to monitored HTML/PDF with provenance and confidence.
- **eCFR** for federal baseline and crosswalks to proposed language.
- **NAICS / state licensing category taxonomy** for onboarding: family childcare home, center, after-school, infant/toddler, subsidy provider.
- Architecture pattern: router classifies rules into licensing / subsidy / workforce / facility buckets; generator-critic pass checks plain-language summaries against citations.

### Action loop
1. Provider enters state, provider type, capacity, subsidy participation, and topics they care about.
2. Alert card answers: “Does this likely affect you?”, “What operational step might change?”, “When is comment due?”, “What question should you ask the agency?”
3. Comment workshop turns provider facts into distinct evidence: staffing impact, parent affordability, rural access, compliance cost, closure risk.
4. Association packet mode clusters comments into themes without creating duplicate form letters.
5. After adoption, the product sends a compliance brief: effective date, checklist, what changed from proposal, and who to call.

### Why this does not duplicate incumbents
Childcare providers get newsletters and association alerts, but not personalized rule relevance with deadline tracking. B2B policy tools monitor legislation/regulation for lobbyists, not small operators. Government portals explain rules agency-by-agency, not across federal + state requirements in operator language.

### MVP
Launch in two states with strong childcare-rule publishing plus federal ACF monitoring. Cover only proposed rule notices and final rules, not inspections or individual licensing cases. Include a manual QA queue before every customer-facing alert.

### Funding path
State childcare associations, CCR&R networks, Early Childhood Funders Collaborative-style grants, shared purchasing by provider coalitions, and low-cost per-site subscriptions bundled with compliance training.

### Fatal risk
The buyer is budget-constrained and exhausted; even accurate alerts may not convert to paid subscriptions. The wedge fails if associations will not bundle it or if alerts feel like one more compliance burden.

---

## 3. Benefits Change Plainwatch — SNAP, TANF, UI, and Medicaid eligibility rule explainer

### Target user
Benefits recipients, legal-aid advocates, caseworkers, community navigators, and nonprofit staff who help people keep public benefits.

### Painful trigger / deadline
A federal or state agency proposes a rule affecting work requirements, eligibility verification, recertification, overpayment recovery, waiver policy, call-center standards, immigration-related eligibility, or benefit calculation. Non-experts often discover the change only after denial, churn, or paperwork failure.

### Data sources / protocols to build on
- **Federal Register API**, **Regulations.gov**, and **RegInfo.gov Unified Agenda** for USDA/FNS, HHS/CMS/ACF, and DOL/ETA rulemaking.
- **Mirrulations** for historical comments and final-rule lineage.
- **State registers / administrative code update feeds** for benefits agencies.
- **State policy manuals** and transmittals where public, with diffing against current versions.
- **eCFR / CFR annual editions** for federal baseline.
- **Legal Services Corporation / state legal-aid issue taxonomies** as tagging vocabulary.
- Architecture pattern: pipeline from detection → rule-to-benefit classification → plain-language risk brief → legal-aid review → public alert.

### Action loop
1. Navigator subscribes by state and benefit program, not by docket number.
2. Alert says: “This proposal could affect people who are unemployed, have irregular hours, are recertifying, are students, are immigrants, or use home care,” with citations.
3. The tool generates outreach copy for clinics, SMS scripts, and a “what evidence matters” comment guide.
4. Legal-aid or nonprofit users submit organizational comments; recipients can add lived-experience statements if safe.
5. Final action is translated into “what to do now”: watch mailbox, report hours, appeal deadline, renewal change, or no immediate action.

### Why this does not duplicate incumbents
Benefits delivery tools focus on applications and eligibility screening, not upstream rulemaking. Legal-aid groups monitor some changes manually. Policy platforms are too expensive and expert-facing. This product is rulemaking legibility specifically for benefits survival and navigator workflows.

### MVP
One program and one region: SNAP work/recertification rules in 5 states plus federal USDA/FNS dockets. Private beta with legal-aid reviewers; no direct-to-recipient mass alerts until summaries are validated.

### Funding path
Legal-aid technology grants, benefits-access foundations, nonprofit subscriptions, state coalition sponsorships, and eventually managed referral partnerships with benefit-navigation platforms.

### Fatal risk
Direct recipient alerts can cause fear or misinformation, especially when proposed rules never become final. If the product cannot distinguish “comment opportunity” from “you must act now,” it will harm trust and adoption.

---

## 4. SchoolRule Window — education rulemaking alerts for parents and local advocates

### Target user
Parents of students with disabilities, English learners, foster youth, rural students, and student-privacy advocates; also PTA policy chairs and small education nonprofits.

### Painful trigger / deadline
A federal Department of Education rule, state board of education rule, or state education agency regulation changes IEP procedures, discipline, school accountability, charter oversight, privacy, curriculum requirements, transportation, teacher certification, or funding formulas. The comment window closes before families know it exists.

### Data sources / protocols to build on
- **Federal Register API** and **Regulations.gov** for Department of Education and civil-rights rulemakings.
- **State board of education rulemaking calendars**, state administrative registers, and board agenda packets.
- **State education agency bulletin feeds** and proposed/final regulation pages.
- **ERIC / NCES metadata only for context**, not as primary rule sources.
- **eCFR** for federal regulatory baseline; state admin code where available.
- Architecture pattern: blackboard-style shared issue workspace for advocates, with adversarial verification on summaries because education terms are state-specific.

### Action loop
1. Parent or advocate subscribes by state, student need, and school type: IEP, discipline, English learners, rural transportation, privacy, charter enrollment.
2. Alert translates the rule into: affected students, stage of process, deadline, hearing date, and “questions to ask your school/state board.”
3. Guided comment flow helps families provide relevant experience without sharing sensitive student details unnecessarily.
4. Small groups can assemble a consensus packet: common harms, requested edits, and distinct family examples.
5. Outcome receipt tracks final adoption, board vote, agency response, effective date, and a plain-language “what changed from the proposal.”

### Why this does not duplicate incumbents
PTA and advocacy organizations issue alerts, but coverage is uneven and campaign-specific. Regulations.gov and state board sites require procedural knowledge. MAPLE-like tools cover legislation/testimony, not federal + state education rulemaking with parent-safe evidence coaching and outcome receipts.

### MVP
One issue vertical: special education procedural rules in 3 states plus federal Department of Education dockets. Start with curated monitoring and expert-reviewed summaries; add board-hearing reminders only for states with reliable calendars.

### Funding path
Disability-education foundations, parent-training-and-information centers, special-education advocacy nonprofits, PTA/state coalition subscriptions, and sponsored public-interest pilots.

### Fatal risk
Education rulemaking is politically polarized and child data is sensitive. The product fails if it becomes a culture-war amplification tool or mishandles private student information. It needs strict privacy defaults, neutral source-linked summaries, and issue scoping.
