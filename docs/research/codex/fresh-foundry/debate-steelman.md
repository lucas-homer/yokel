# Debate gauntlet step 2 — Steelman defender

Purpose: defend each candidate in its strongest viable form under harsh constraints. Prior-art constraints matter: do **not** rebuild generic engagement portals, do not self-host broad scraper fleets before demand is proven, treat deadline correctness as a trust-critical product feature, and borrow from MAPLE/Mirrulations/Open States/Legistar/City Scrapers/Decidim/Pol.is/mySociety patterns without inheriting their weakest assumptions.

---

## 1. CommentWindow Registry / DocketClock

**Strongest version:** A boring, trusted civic infrastructure layer: “public participation deadlines as first-class objects.” It should not be a destination app or policy tracker. Its wedge is a federal-first, SLA-backed normalized API for comment windows, hearings, continuances, submission endpoints, confidence, provenance, and status changes. Build on Federal Register, Regulations.gov v4 freshness, and Mirrulations history rather than crawling everything from scratch.

**Narrowed MVP:** Federal rulemaking only. Canonical fields, provenance, confidence, last-seen timestamps, open/close status, submission URL, CSV/bulk export, ICS/RSS/webhooks, and a small dashboard for design partners. No state/local, no PDF scraping, no automated interpretation beyond deadline/status extraction.

**Distribution/funding adjustment:** Sell to people already punished by missed deadlines: associations, newsrooms, civic-data teams, regulatory vertical products, legal/policy shops, and internal portfolio products. Free schema/basic public data; paid API volume, webhooks, SLA, historical snapshots, and deadline verification support.

**Legitimacy safeguards:** Public source links; explicit confidence labels; change logs; “unknown/ambiguous” states; timezone handling; no silent corrections; human review for low-confidence/deadline-changing events; public incident reports for misses.

**Can it survive if scoped properly?** Yes. It is one of the cleanest gaps. It fails only if it promises cross-jurisdiction completeness too early or markets itself as a consumer civic app before downstream demand exists.

---

## 2. RecordReady Clerk Intake

**Strongest version:** A staff workflow tool, not an AI replacement for the official record. The product wins by making the last 72 hours before a meeting/comment close less chaotic: match inbound emails/forms/attachments/voicemails to agenda items, dedupe, queue staff review, send receipts, and export packets. It starts from the government’s actual messy inbox, where engagement portals often fail.

**Narrowed MVP:** One Legistar jurisdiction, one intake mailbox, one meeting body. Agenda-item matching, duplicate clustering, attachment capture, staff review/override, PDF/CSV packet export, and receipt emails. No autonomous filing decisions, no multi-channel omnichannel promise beyond email/import at first.

**Distribution/funding adjustment:** Sell through clerks, public-comment coordinators, agenda-management consultants, municipal innovation pilots, and small-jurisdiction open-government grants. Position as risk reduction and staff-time savings, not “AI civic engagement.”

**Legitimacy safeguards:** Human-in-the-loop review before anything enters packet; immutable audit trail; source-preserved attachments; transparent matching confidence; configurable procedural rules; retention/export policies aligned with public-records law; no viewpoint weighting.

**Can it survive if scoped properly?** Yes, but only if pilots prove measurable review-time reduction without adding legal anxiety. Fatal risk if clerks perceive it as changing official-record authority rather than preparing cleaner packets for staff approval.

---

## 3. Consensus Comment Room

**Strongest version:** A high-integrity comment-quality tool for organizers facing a live docket, designed to reduce duplicate form letters and surface real consensus plus dissent. The product is strongest when it produces a small number of evidence-backed official-record packets, not when it tries to create a general-purpose deliberation social network.

**Narrowed MVP:** One federal docket domain; organizer-created room; structured 7-question evidence/lived-experience interview; similarity detection; visible consensus/minority statements; human-reviewed packet; manual filing instructions and receipt capture. No one-click mass filing in v1.

**Distribution/funding adjustment:** Per-campaign fees for nonprofits/associations; foundation-funded public-interest rooms; possibly agency/ombuds pilots only when outputs are public and neutral. Bundle with DocketClock/vertical products rather than sell as a standalone habit app.

**Legitimacy safeguards:** User attestation; source-grounded summaries; disclose AI assistance; preserve minority reports; expose participant counts and verification levels; prohibit bulk paraphrase spam; maintain public export of method and packet; separate funder from moderation outcomes.

**Can it survive if scoped properly?** Conditional yes. It can survive as an embedded action-quality module. It likely fails as a standalone “AI consensus” brand because astroturf/capture perceptions are severe.

---

## 4. Affected-Party Verifier / Notice Compact

**Strongest version:** A neutral procedural trust primitive for land-use cases: verify affected status privately, report distinct arguments/counts by status, and never silence unverified people. It is not a neighborhood forum and not a developer outreach page. Its value is defensible case-scoped participation: residents, renters, businesses, workers, and other affected classes can be counted without exposing sensitive addresses.

**Narrowed MVP:** One city, one process type: zoning variances within statutory notice radius. Address-to-radius verification, renter self-attestation tier, private audit trail, staff/partner-reviewed packet, no broad public identity exposure.

**Distribution/funding adjustment:** Planning/legal-aid pilots; procedural-justice foundations; applicant-paid notice transparency only under strict non-success-fee and neutrality rules; API/add-on for participation vendors. Early credibility should come from legal-aid/planning-neutral pilots, not developers alone.

**Legitimacy safeguards:** Verified status cannot be required to speak; privacy-preserving hashing/minimal retention; distinct renter/owner/business tiers; publish methodology; independent governance/advisory review; anti-harassment controls; no campaign targeting resale.

**Can it survive if scoped properly?** Yes, but legitimacy is fragile. Fatal if it becomes a gatekeeping tool or looks applicant/developer-captured. The steelman is a neutral evidentiary layer, not exclusion.

---

## 5. Concern Router / Civic RouteMap

**Strongest version:** A professional navigator tool that answers: “what official process, if any, is the live lever for this concern at this location?” The key is conservative routing, explanation, and admitting uncertainty. It should serve librarians, newsrooms, legal aid, 311/hotline staff, and civic products before any direct consumer self-serve launch.

**Narrowed MVP:** One metro area plus federal dockets. Intake form for navigator use; search federal dockets, one state via Open States/Plural, and one Legistar city/county. Return likely endpoints, deadlines, confidence, eligibility/verification notes, and “why this matches.” Support “no reliable official path found.”

**Distribution/funding adjustment:** Library/newsroom/community-foundation pilots; legal-aid and civic-information philanthropy; SaaS/API for organizations that already triage resident questions. Avoid promising universal coverage to consumers.

**Legitimacy safeguards:** Source citations; confidence thresholds; human escalation queue; no hallucinated routes; clear distinction between official path, advocacy contact, and informational resource; logged corrections; local expert review for taxonomy.

**Can it survive if scoped properly?** Yes, as a navigator/API product. Direct consumer routing at broad scale is dangerous until accuracy and coverage are proven.

---

## 6. NoticeNail / Lot Line

**Strongest version:** A resident-side missing-signal capture network for legally posted site notices that never become friendly digital alerts. Its moat is not OCR alone; it is fast human verification, parcel matching, deadline extraction, and alerting nearby subscribed addresses/orgs before the window closes.

**Narrowed MVP:** One city with frequent posted notices and poor digital discoverability. Mobile photo capture; OCR only for address/case/deadline; human QA; verified public case cards; radius alerts; filing/hearing instructions. No national permit database and no guarantee that every notice is captured.

**Distribution/funding adjustment:** Local newsroom/foundation pilot; subscriptions for tenant groups, neighborhood associations, preservation groups, legal clinics, and hyperlocal media. Recruit volunteers through existing neighborhood/legal-aid channels, but fund QA as paid work.

**Legitimacy safeguards:** Prominent coverage limitations; timestamped photos; verification status; source links; no “all clear” messaging; privacy controls for submitters; anti-doxxing moderation; conservative deadlines; escalation for late/ambiguous notices.

**Can it survive if scoped properly?** Conditional. It can be powerful in one city with strong partners and human QA. It fails if users infer comprehensive coverage or if late/missed notices create false security.

---

## 7. Tenant Displacement Docket

**Strongest version:** An early-warning and action-prep layer for tenant-impacting land-use/permit events, built with tenant legal-aid/organizer partners. It should focus only on case types where an official deadline/appeal/comment/relocation-assistance window exists and where source data is early enough to matter.

**Narrowed MVP:** One tenant-protection-rich city; one case type such as demolition permits for rent-stabilized or multi-unit buildings. Human-reviewed alerts, translated deadline cards, evidence prompts, testimony/appeal checklists, and outcome tracking for a single anchor partner.

**Distribution/funding adjustment:** Legal-services innovation grants, housing foundations, nonprofit partner seats, council discretionary funding routed through tenant-serving organizations. Do not sell landlord-facing intelligence in the same market.

**Legitimacy safeguards:** Tenant safety/privacy by design; no public listing of vulnerable households; partner-controlled outreach; delay/withhold sensitive data that could aid harassment; legal-disclaimer and referral boundaries; source transparency; clear “not legal advice.”

**Can it survive if scoped properly?** Yes in select cities, with nonprofit/legal-aid anchoring. Fatal risk if source data is too late to create action or if the tool can be repurposed by landlords/speculators.

---

## 8. Conditions Keeper / Outcome Graph

**Strongest version:** The post-action accountability layer: after a vote/comment/approval/continuance, tell people what happened, what next window exists, and whether conditions/final text changed. It should make conservative outcome receipts, not claim causality. It is strongest as infrastructure embedded across other products and as a local watchdog/journalism tool.

**Narrowed MVP:** One city planning commission. Track continued dates, appeal deadlines, votes, and conditions of approval using manual extraction plus LLM-assisted human review. Send receipts with statuses like approved, denied, continued, appealable until X, condition changed, condition not found.

**Distribution/funding adjustment:** Local journalism grants, civic watchdog nonprofits, neighborhood councils, planning-law clinics, commissioner aides, and API modules for action products. Municipal transparency contracts are possible after public-interest credibility is established.

**Legitimacy safeguards:** Source-linked excerpts; human review; conservative labels; distinguish “condition in record” from “condition enforced”; right-of-correction workflow; no accusations of noncompliance without enforcement data; immutable version history.

**Can it survive if scoped properly?** Yes, especially as a module. Standalone pull may be weaker before users have live cases to follow.

---

## 9. CareRule Scout / Benefits Plainwatch

**Strongest version:** Expert-reviewed rule/change intelligence for disability, aging, Medicaid/HCBS, and benefits navigators—not direct panic alerts to vulnerable recipients. The product translates CMS/HHS rules, waiver amendments, SPAs, and state changes into profile-based “what might change” memos, guided comments, receipt capture, and final-action explanations.

**Narrowed MVP:** One program and region: HCBS waiver families/navigators in 2–3 states plus federal CMS rules. Expert-reviewed summaries, navigator-facing alerts, no direct-to-recipient mass alerts until validation. Manual filing/receipt support.

**Distribution/funding adjustment:** Disability/aging/health-access foundations; paid seats for P&A orgs, legal aid, care-coordination nonprofits, small provider associations; ombudsman partnerships if editorial independence remains clear.

**Legitimacy safeguards:** Expert review; “not legal advice”; calm risk framing; citations and confidence; plain-language plus original excerpts; no eligibility determinations; panic-control thresholds; correction pathway; partner-mediated outreach.

**Can it survive if scoped properly?** Yes, with a trusted intermediary model. Fatal if it sends inaccurate direct alerts that cause panic or missed benefits action.

---

## 10. Childcare Rule Radar / CareNotice Counsel

**Strongest version:** A counsel-lite rule radar for small childcare operators, sold through associations/CCR&R/shared-services networks. It must connect alerts to concrete license/cost/compliance risk, not generic “policy news.” The strongest comments are distinct operational evidence from providers about ratios, staffing, subsidy, inspections, training, and food-program burdens.

**Narrowed MVP:** One state, one provider type, three source classes: state register notices, childcare agency hearings, and HHS/ACF federal rules. Profile by license type/capacity/subsidy participation. Human-reviewed beta alerts; manual filing/receipt upload; post-adoption compliance briefs.

**Distribution/funding adjustment:** Bundle via state childcare association, CCR&R network, shared-services alliance, or compliance-training provider. Low per-site pricing only works if an intermediary handles trust and billing.

**Legitimacy safeguards:** Source-cited, reviewed summaries; avoid legal-advice claims; distinguish proposed from adopted rules; provider attestation for comments; no mass cloned comments; equity-aware translation/access; clear deadline/confidence labels.

**Can it survive if scoped properly?** Conditional yes. The buyer is exhausted and budget-constrained, so association bundling and tangible compliance/revenue relevance are mandatory.

---

## 11. Pharmacy Docket Desk

**Strongest version:** A regulatory action file for independent pharmacies, distributed through trusted pharmacy associations, PSAOs, buying groups, or wholesalers. The value is profile-based relevance across CMS/DEA/FDA/state boards/Medicaid/PBM-related rules and bills, with comment prompts, implementation checklists, receipt tracking, and final updates.

**Narrowed MVP:** One state plus federal CMS/DEA/FDA; independent pharmacies offering vaccines and Medicaid. Track open comment periods, state board hearings, and explicit pharmacy bills/rules. Source-cited confidence and human review for interpretation.

**Distribution/funding adjustment:** Monthly subscription bundled by buying groups/PSAOs/state associations; premium implementation/audit-prep exports; sponsor as a member benefit. Do not try to out-newsletter associations—make their alerts actionable and profile-specific.

**Legitimacy safeguards:** Pharmacist/attorney/policy expert review for high-stakes interpretation; no legal advice; source excerpts; confidence labels; correction workflow; comments based on real operational facts; vendor/sponsor conflict disclosures.

**Can it survive if scoped properly?** Yes commercially if distribution is through trusted channels. Fatal risks are trust/liability and being perceived as redundant with association newsletters.

---

## 12. Schoolyard Radius

**Strongest version:** A child-centered mitigation watch for decision windows near schools and childcare sites. It should not become an anti-housing mobilization machine. The strongest frame is safety, construction staging, traffic circulation, environmental review, air/noise, and Safe Routes mitigation—then outcome/condition tracking.

**Narrowed MVP:** One metro area; public K–8 schools only; projects above threshold within 1,000 feet or walking corridors. Three prompt categories: construction staging, traffic circulation, environmental review. District/PTA-facing dashboard plus free community alerts.

**Distribution/funding adjustment:** PTA council/district pilot; Safe Routes grants; local health/environment foundations; transportation-demand-management or Vision Zero funds. Position as mitigation and child-safety compliance, not development opposition.

**Legitimacy safeguards:** Explicit pro-mitigation framing; no student-level data; use public school geographies carefully; anti-harassment and anti-dogwhistle moderation; balanced prompts including conditions/solutions; source links; outcome labels.

**Can it survive if scoped properly?** Conditional. It has strong civic appeal but must be tightly constrained to safety/mitigation, or it will be captured by generalized NIMBY campaigns.

---

## 13. Open Issue Escalator

**Strongest version:** A bridge from chronic service complaints to real budget/procurement/committee levers. It should not be another 311 dashboard. The product clusters unresolved public 311 issues, watches agendas/budget items for relevant levers, alerts residents when testimony can matter, and tracks allocations/votes/work orders/deferrals.

**Narrowed MVP:** One city with Open311 and Legistar; one issue category, e.g., sidewalk/ADA hazards or flooding. Cluster public 311 records, watch relevant agendas/budget/procurement items, collect location-specific testimony packets, and track outcomes.

**Distribution/funding adjustment:** Public advocate/council office/department service-equity pilot; local newsroom/foundation support; eventually SocietyWorks-style SaaS for public dashboards/internal analytics. Tie funding to service equity and capital-planning accountability.

**Legitimacy safeguards:** Do not expose complainants unnecessarily; equity-aware aggregation; source-linked agenda matches; clear distinction between service ticket and policy/budget lever; avoid overpromising resolution; publish “no lever found” cases honestly.

**Can it survive if scoped properly?** Conditional. It survives where a recurring issue category truly connects to public levers. It fails if most clusters never become actionable and users experience only a more polished frustration dashboard.

---

# Cross-slate steelman conclusions

1. **Most defensible infrastructure:** CommentWindow Registry/DocketClock and Conditions Keeper/Outcome Graph.
2. **Most defensible staff SaaS:** RecordReady Clerk Intake.
3. **Most defensible navigator/API wedge:** Concern Router/Civic RouteMap.
4. **Most defensible local resident wedge:** NoticeNail/Lot Line or Affected-Party Verifier, but only one-city/one-process with human QA and privacy safeguards.
5. **Most defensible vertical commercial wedges:** Pharmacy Docket Desk and Childcare Rule Radar; CareRule/Benefits is strong but should start through expert intermediaries.
6. **Most fragile but mission-valuable:** Consensus Comment Room, Schoolyard Radius, Tenant Displacement Docket, and Open Issue Escalator—each can work only when constrained around evidence, safety, privacy, and real action windows.

The slate can survive debate if every idea obeys the same discipline: first prove one source, one jurisdiction/domain, one user workflow, one deadline/action loop, and one credible funding channel before expanding coverage.
