# Final seasoned portfolio — Fresh civic idea foundry

## Portfolio summary

The final portfolio uses the full fresh-foundry workflow: generator breadth across deliberation, infrastructure, land use, rulemaking, sustainability, and vertical operator ideas; curated slate merging; adversarial red-team; feasibility and product-demand attacks; steelman narrowing; neutral adjudication; and five ensemble ballots for civic impact, defensibility, feasibility, funding, and product/market.

Scores below normalize the product ballot to a 10-point scale and average it with civic impact, defensibility, feasibility, and funding. The numbers are decision aids, not mechanical winners; scope discipline and risk posture matter more than tiny score differences.

| Rank | Final idea | Final score summary | Portfolio role |
|---:|---|---|---|
| 1 | CommentWindow Registry / DocketClock | 7.64 avg: strongest feasibility, best infrastructure primitive | Shared deadline substrate |
| 2 | Pharmacy Docket Desk | 7.50 avg: strongest funding/product wedge | Commercial vertical wedge |
| 3 | Childcare Rule Radar / CareNotice Counsel | 7.36 avg: strong channel-led operator product | Public-interest operator vertical |
| 4 | RecordReady Clerk Intake | 7.28 avg: highest civic legitimacy/staff workflow | Government operations wedge |
| 5 | CareRule Scout / Benefits Plainwatch | 7.10 avg: high-stakes equity, expert-heavy | Navigator/intermediary intelligence |
| 6 | Tenant Displacement Docket | 6.42 avg: lower feasibility but highest human-stakes local pilot | Guarded impact pilot |

---

## 1. CommentWindow Registry / DocketClock

**Tagline:** Public participation deadlines as reliable, subscribable objects.

**Final score summary:** Avg 7.64. Civic impact 7.8, defensibility 7.0, feasibility 8.0, funding 7.4, product/market 8.0. Best technical substrate and most reusable portfolio infrastructure.

**Target user:** Civic-data teams, associations, newsrooms, legal/policy shops, vertical rule-radar products, and downstream civic-action tools.

**Painful trigger / deadline:** A comment window, hearing, extension, reopening, or final-action link changes and a downstream operator misses it, destroying user trust.

**Specific problem:** Federal public-comment deadlines exist across Federal Register and Regulations.gov, with history in Mirrulations, but there is no normalized deadline object with provenance, confidence, status changes, watchlists, webhooks, RSS/ICS, and correction workflow.

**Solution:** A federal-first API and bulk feed for open/closing comment windows: canonical IDs, open/close datetime, timezone, submission URL, source provenance, last-seen timestamp, confidence, status changes, webhooks, RSS/ICS, CSV/bulk export, and a design-partner dashboard for source disputes.

**What it builds on:** Federal Register API, Regulations.gov v4, Mirrulations/mirrulations-search, Open Civic Data-style IDs, webhook/RSS/ICS conventions.

**Why it fills a gap / not duplicate:** Federal Register and Regulations.gov are source portals/APIs, not deadline-SLA products. Mirrulations is a mirror/history layer, not a maintained confidence-scored participation-deadline feed.

**MVP scope:** Federal rulemaking only. No state/local scraping. No automated filing. Include provenance, confidence, stale-source states, correction logs, watchlists, webhooks, CSV, RSS/ICS, and human review for contested deadline changes.

**Action / impact loop:** Downstream product subscribes to closing windows → alerts affected users → user acts in that downstream product or official portal → DocketClock emits closed/extended/reopened/final-linked updates → downstream product follows up.

**Funding model:** Free schema/basic public data; paid API volume, webhooks, SLA, historical snapshots, organization watchlists, and deadline-verification support for associations, newsrooms, and vertical products.

**Key risks:** One wrong deadline can erase trust; federal-only may feel too narrow; state/local expansion becomes a scraper-maintenance graveyard; “SLA” implies costly operations.

**Mitigations:** Keep v1 federal-only; publish provenance and change logs; make unknown/stale/conflicted states first-class; suppress alerts on stale sources; use human review for changed or contested deadlines; expand only when a funded source cluster exists.

**Candid verdict:** Best infrastructure bet. Build as boring trust plumbing, not a resident destination app.

---

## 2. Pharmacy Docket Desk

**Tagline:** Member-specific regulatory action files for independent pharmacies.

**Final score summary:** Avg 7.50. Civic impact 6.8, defensibility 7.3, feasibility 7.2, funding 8.0, product/market 8.2. Strongest commercial wedge and sustainability profile.

**Target user:** Independent retail pharmacies, compounding pharmacies, DME counters, long-term-care pharmacy operators, state pharmacy associations, buying groups, PSAOs, and wholesalers.

**Painful trigger / deadline:** CMS, DEA, FDA, state board, Medicaid, PBM, or state legislative changes can affect reimbursement, controlled substances, compounding, audits, vaccination authority, or inventory before small owners hear in time.

**Specific problem:** Pharmacy owners already receive broad newsletters, but not a source-cited action file mapped to their license/profile, deadlines, hearings, comment opportunities, implementation risks, and final updates.

**Solution:** Channel-led counsel-lite inbox: profile-based relevance memos, comment/board-hearing prompts, suggested operational evidence, manual filing guidance, receipt tracking, and final-rule/bill/board-vote updates.

**What it builds on:** Federal Register, Regulations.gov, Mirrulations, Open States/Plural, state pharmacy-board calendars/agendas, Medicaid notices, MAPLE-style event/notification patterns, WriteToThem-style routing.

**Why it fills a gap / not duplicate:** Quorum/FiscalNote serve policy teams; associations send broad alerts; compliance tools manage current obligations. The gap is personalized, source-cited regulatory action files for independent operators, delivered through trusted channels.

**MVP scope:** One state plus federal CMS/DEA/FDA; independent pharmacies offering vaccines and Medicaid; track open comment periods, state board hearings, and explicit pharmacy bills/rules; expert-reviewed summaries; no legal advice.

**Action / impact loop:** Alert matched to pharmacy profile → owner/association submits operational evidence or board testimony → receipt stored → final rule/bill/board vote tracked → implementation/audit-prep checklist issued.

**Funding model:** Association/PSAO/buying-group/wholesaler sponsored member benefit; per-member monthly bundle; premium implementation and audit-prep exports. Avoid direct one-by-one SMB acquisition until channel validation is strong.

**Key risks:** Trusted incumbents already own attention; incorrect interpretation creates legal-liability anxiety; sponsors may want advocacy slant; owners may ignore another inbox.

**Mitigations:** Make associations/PSAOs the product surface; strengthen rather than replace existing advocacy; use pharmacist/attorney/policy expert review; cite sources; disclose conflicts; prioritize patient-access/community-health consequences.

**Candid verdict:** Best revenue wedge, but only if channel-led. Kill direct SaaS if associations say newsletters already solve the job.

---

## 3. Childcare Rule Radar / CareNotice Counsel

**Tagline:** What proposed rules mean for your childcare license, staffing, costs, and compliance calendar.

**Final score summary:** Avg 7.36. Civic impact 7.4, defensibility 7.0, feasibility 6.8, funding 7.6, product/market 8.0. Strong channel-led public-interest vertical.

**Target user:** Home-based childcare providers, independent centers, small daycare directors, Head Start subcontractors, childcare associations, CCR&R agencies, shared-services alliances.

**Painful trigger / deadline:** Licensing, subsidy, staff-ratio, background-check, training, food-program, inspection, or reimbursement rules change with short comment/hearing windows and later create cost or license risk.

**Specific problem:** Small providers are exhausted and budget constrained; they cannot decode state registers or federal HHS/ACF notices, yet those rules can change staffing, reimbursement, paperwork, or license exposure.

**Solution:** Association-led operator-profiled rule radar: relevance cards by license type/capacity/subsidy participation, human-reviewed operational impact memos, evidence-based comment prompts, manual filing/receipt support, and post-adoption compliance briefs.

**What it builds on:** State administrative registers/bulletins, childcare licensing-board calendars, agency hearings, CCDF plan/amendment notices, Federal Register, Regulations.gov, HHS/ACF rules, eCFR, licensing-category taxonomy, RuleBox-style classifiers, MAPLE-style digest/archive.

**Why it fills a gap / not duplicate:** Associations and agencies send generic updates; policy trackers are expert-facing. This maps proposed rules to provider subtype and operational consequences in trusted, bundled workflows.

**MVP scope:** One state, one provider type, three source classes: state register notices, childcare agency hearings, and HHS/ACF federal rules. Human-reviewed beta alerts, manual filing instructions, receipt upload, and post-adoption compliance briefs.

**Action / impact loop:** Provider profile → relevant alert → provider supplies staffing/cost/waitlist/subsidy facts → distinct comment or association packet → receipt captured → final/adopted rule translated into checklist and effective dates.

**Funding model:** State childcare association bundle, CCR&R/shared-services networks, compliance-training partners, early-childhood funders, subsidized per-site access for low-income-area providers.

**Key risks:** Direct providers may not pay or engage; state taxonomies are brittle; wrong interpretation causes license anxiety; product may appear to help operators resist safety regulation.

**Mitigations:** Make association/CCR&R the buyer; human-review every impact brief; distinguish proposed vs adopted; emphasize child access, provider viability, and compliance readiness; avoid legal-advice claims.

**Candid verdict:** Strong if bundled through a trusted channel. Weak as standalone direct-to-provider SaaS.

---

## 4. RecordReady Clerk Intake

**Tagline:** Turn the messy pre-meeting inbox into a reviewed, source-linked official-record packet.

**Final score summary:** Avg 7.28. Civic impact 8.4, defensibility 6.8, feasibility 6.8, funding 6.8, product/market 7.6. Highest legitimacy score and clearest government workflow pain.

**Target user:** City/county clerks, planning-board staff, agency public-comment coordinators, and small jurisdictions without robust engagement operations.

**Painful trigger / deadline:** The 72 hours before a meeting or comment close, when staff must process emails, attachments, screenshots, petitions, webforms, and late comments into the official packet.

**Specific problem:** Public input arrives through messy real-world channels, not only official portals. Staff must match comments to agenda items, avoid lost attachments, handle duplicates, send receipts, and preserve auditability under deadline pressure.

**Solution:** Clerk-facing intake desk that ingests one mailbox/form, suggests agenda-item matches, clusters duplicates, extracts attachments/location references, queues staff review, sends receipt emails, and exports PDF/CSV packets into the existing workflow.

**What it builds on:** Legistar OData, Open Civic Data Event/Organization concepts, City Scrapers patterns, MAPLE-style receipts/archive, Decidim-style verification concepts, IMAP/Gmail/Graph ingestion, CSV/webform import.

**Why it fills a gap / not duplicate:** Engagement suites collect comments in their own portals. RecordReady starts from the government’s actual inbox and prepares defensible packets without asking residents to change behavior.

**MVP scope:** One Legistar jurisdiction, one meeting body, one intake mailbox; email and attachment handling; agenda matching suggestions; duplicate clustering; staff review/override; receipt emails; PDF/CSV export. No autonomous official-record decisions and no voicemail unless demanded by a pilot.

**Action / impact loop:** Resident submits through normal channel → staff see suggested match/cluster → staff approves packet inclusion → resident receives receipt → meeting outcome can later be sent as a conservative follow-up.

**Funding model:** B2G SaaS for clerks/agencies, municipal innovation/open-government pilots, state clerk association bundles, add-on for agenda-management consultants and smaller jurisdictions.

**Key risks:** Official-record custody and public-records security are serious; procurement can be slow; agenda-management incumbents may add this; review queue can become another inbox.

**Mitigations:** Human approval before packet export; immutable audit trail; source-preserved attachments; unmatched/unknown queues; retention/export policies aligned to clerk rules; prove reduced staff time and fewer missed/misfiled comments.

**Candid verdict:** Real pain and civic legitimacy. Build only with a clerk co-design partner who defines the official-record boundary.

---

## 5. CareRule Scout / Benefits Plainwatch

**Tagline:** Expert-reviewed rule-change intelligence for benefits and care navigators before families are harmed.

**Final score summary:** Avg 7.10. Civic impact 8.4, defensibility 6.5, feasibility 5.6, funding 7.2, product/market 7.8. Highest equity/stakes among rulemaking products, but expert-heavy.

**Target user:** Disability advocates, Medicaid/HCBS families via intermediaries, care recipients, legal-aid benefits navigators, P&A organizations, aging/disability nonprofits, small HCBS provider associations.

**Painful trigger / deadline:** CMS/HHS rules, Medicaid waiver amendments, SPAs, state benefit rules, manuals, or transmittals open for comment or change implementation with practical consequences for service hours, eligibility, transportation, reimbursement, or recertification.

**Specific problem:** Vulnerable families and navigators cannot monitor dense federal/state benefits sources. Wrong or overbroad alerts can cause panic, but missed changes can mean lost services or missed comment windows.

**Solution:** Navigator/intermediary-facing intelligence: source excerpts, calm “what might change” summaries, confidence labels, guided lived-experience or organizational comments, receipt capture, and final-action explanation. No direct mass recipient alerts in MVP.

**What it builds on:** Federal Register, Regulations.gov, Mirrulations, Medicaid.gov waiver/SPAs, CMS PDFs, state registers/eRulemaking portals, eCFR/GovInfo, state policy manuals/transmittal diffing, legal-aid issue taxonomies.

**Why it fills a gap / not duplicate:** Policy platforms are expensive and expert-facing; benefits tools focus on applications, not upstream rulemaking. The gap is safe translation for trusted navigators and organizations.

**MVP scope:** One program/region: e.g., HCBS waiver families/navigators in 2–3 states plus federal CMS rules. Expert-reviewed summaries, weekly digest, deadline cards, manual comment guidance, receipt capture, no eligibility determinations.

**Action / impact loop:** Expert-validated alert → navigator shares with affected clients/orgs as appropriate → lived-experience or organizational comment prepared → receipt stored → final action explained as addressed/partially addressed/rejected/not found/pending.

**Funding model:** Disability/aging/health-access foundations; paid seats for P&A orgs, legal aid, care-coordination nonprofits, small provider associations; ombudsman partnerships only if editorial independence is clear.

**Key risks:** State Medicaid/benefits data is fragmented and legally nuanced; summaries can become unauthorized legal advice; direct alerts can cause panic; expert review raises COGS.

**Mitigations:** Intermediary-first; expert review before publication; citations and confidence; no eligibility determinations; calm risk framing; correction path; avoid storing sensitive diagnosis/service data unless strictly needed.

**Candid verdict:** Mission-critical, but not a mass consumer alert app. Treat as expert-reviewed navigator infrastructure.

---

## 6. Tenant Displacement Docket

**Tagline:** Early land-use and permit warnings routed safely through tenant-defense partners.

**Final score summary:** Avg 6.42. Civic impact 8.2, defensibility 6.3, feasibility 4.4, funding 6.6, product/market 6.6. Lower average because operations are hard, but the human stakes justify a guarded pilot.

**Target user:** Tenant organizers, legal-aid housing teams, community land trusts, anti-displacement coalitions, and renters only through trusted partner-mediated outreach.

**Painful trigger / deadline:** Demolition, condo conversion, substantial alteration, lot merger, short-term-rental legalization, rezoning, appeal, or relocation-assistance windows begin before tenants understand the threat.

**Specific problem:** Generic permit portals expose cases but not tenant-defense relevance; tenant tools often activate after landlord action. Legal aid and organizers need earlier, verified signals for case types where intervention windows still exist.

**Solution:** Partner-controlled early-warning watch for one tenant-impacting case type in one tenant-protection-rich city: human-reviewed deadline cards, translated evidence prompts, appeal/testimony checklists, strict access controls, and outcome tracking.

**What it builds on:** Accela/EnerGov/Socrata permits, ArcGIS parcel/planning layers, Legistar/City Scrapers agendas, rent-stabilized/multi-unit lists, assessor data, code-enforcement/eviction data where legally usable, local rules library.

**Why it fills a gap / not duplicate:** It bridges land-use decision windows and tenant-defense workflows before displacement is locked in, while avoiding public vulnerable-building intelligence.

**MVP scope:** One city, one case type such as demolition permits for rent-stabilized/multi-unit buildings, one anchor legal-aid or tenant-union partner, human-reviewed alerts, no public searchable vulnerable-building database, no landlord-facing product.

**Action / impact loop:** Case source triggers review → partner receives deadline card → organizer/legal aid decides outreach → tenants provide facts/evidence safely → testimony/appeal/checklist prepared → hearing/permit/continuance/appeal outcome tracked.

**Funding model:** Legal-services innovation grants, housing foundations, council discretionary funding via nonprofit partner, organizational seats for tenant unions/community land trusts.

**Key risks:** Source data may arrive too late; public alerts can aid landlords/speculators; legal rules are local and nuanced; wrong alerts cause panic and missed alerts create reliance harm.

**Mitigations:** Prove early-enough signal before scaling; partner-mediated access only; strict anti-misuse controls; human review; privacy minimization; no public vulnerable-tenant intelligence; clear legal-referral boundaries.

**Candid verdict:** Not the easiest business, but the strongest guarded impact pilot. Advance only with an anchor partner and early-signal proof.

---

## Process note: orchestration patterns and changes from the prior Pi portfolio

The fresh workflow used a Claude-style multi-pass foundry rather than a single ranked synthesis: broad generator lenses produced many candidates; a curator merged overlaps into 13 slate ideas; red-team/product/feasibility attackers found fatal assumptions; a steelman pass narrowed viable forms; an adjudicator advanced only 8 survivors; then five voters scored survivors from different lenses.

Compared with the prior Pi portfolio, the fresh process became more vertical, channel-led, and risk-gated:

- **Kept and sharpened:** DocketClock survived as the clearest infrastructure primitive, now explicitly federal-only with provenance, confidence, stale states, and human review.
- **Replaced broad prior verticals:** Prior ScopeWatch/CodeRed-style small-operator concepts evolved into more concrete **Pharmacy Docket Desk** and **Childcare Rule Radar**, where channels and painful regulatory consequences are clearer.
- **Shifted from consumer land-use to guarded partner pilots:** Prior Lot Line/Block Whip-style resident land-use energy was not selected as a broad public product; the portfolio keeps only **Tenant Displacement Docket** as partner-mediated, access-controlled, and city/case-type scoped.
- **Split modules from standalones:** Comment Workshop / Closed the Loop became embedded patterns rather than final standalone products. The fresh slate’s **Conditions Keeper** was valuable but deferred as an add-on/receipt layer.
- **Raised legitimacy standards:** Consensus, verification, routing, and affected-party tools were not killed for lack of imagination; they were deferred because the debate showed astroturf, exclusion, wrong-routing, privacy, and false-security risks strike the core mechanism.
- **Used ensemble disagreement productively:** Civic-impact voters favored RecordReady, CareRule, Tenant, and Conditions; funding/product voters favored Pharmacy, Childcare, and DocketClock; feasibility favored DocketClock and Pharmacy. The final portfolio balances both by including one infrastructure layer, two sustainable verticals, one government operations wedge, one expert equity product, and one guarded high-impact pilot.

---

## Not selected / deferred

| Idea | Decision | Why |
|---|---|---|
| Conditions Keeper / Outcome Graph | Deferred / module | Valuable after-action receipt layer, but weaker standalone pull and risk of overclaiming enforcement or causality. Use inside DocketClock, RecordReady, Tenant, or land-use products. |
| Concern Router / Civic RouteMap | Deferred | Real navigator pain, but arbitrary concern-to-official-lever routing is accuracy-sensitive and often returns no path. Revisit as a professional navigator tool after source coverage and human escalation are proven. |
| Consensus Comment Room | Deferred / embedded module | Useful for trusted campaigns, but standalone product is vulnerable to AI-laundered astroturf and weak recurring demand. |
| Affected-Party Verifier / Notice Compact | Deferred | Geospatially feasible, but privacy and exclusion/gatekeeping risks require neutral governance before productization. |
| NoticeNail / Lot Line | Deferred | Compelling local signal, but false-security and human-QA burden are too high without a funded one-city operation. |
| Open Issue Escalator | Deferred | Needs a known recurring budget/procurement/hearing lever; otherwise becomes another frustration dashboard. |
| Schoolyard Radius | Not selected as standalone | Too likely to become anti-housing mobilization and commercially fragile; salvage only as mitigation-focused Safe Routes/district functionality. |
| Consensus/Comment Workshop standalone | Not selected | Keep the evidence interview, attestation, similarity checks, and receipt concepts as modules inside selected products. |
| Generic RuleRadar / Statehouse RuleWatch | Split / deferred | Too horizontal. Viable pieces became Pharmacy, Childcare, and CareRule; other verticals require anchor-channel validation. |
| PermitShield Auto / TenantCare Rule Desk | Deferred | Plausible but narrower, source-fragmented, and less validated than pharmacy/childcare/care-rule wedges. |
