# Debate gauntlet: feasibility attack + rescue

Source read: `fresh-foundry/curated-slate.md` and `civic-tech-prior-art-scan.html`.

Prior-art baseline used throughout:

- Federal rulemaking is technically feasible if built on **Federal Register + Regulations.gov APIs for freshness** and **Mirrulations S3/search patterns for history**. Do not rebuild the mirror.
- Local agendas are feasible in Legistar jurisdictions via the **public auth-free Legistar OData API**, but long-tail local systems are permanent scraper maintenance.
- Land-use/permit/parcel products are the hardest: Accela/EnerGov/Socrata/ArcGIS/assessor data are city-specific and often do not expose clean public-action deadlines.
- Decidim/Consul are reference patterns, not code dependencies, because they are heavy government-hosted AGPL platforms.
- Any product that asserts deadlines, affected status, legal meaning, or official submission must support happy/nil/empty/error paths and conservative “unknown/no reliable path found” outcomes.

Verdict key: **green** = buildable with narrow scope and known APIs; **yellow** = feasible only with a very tight jurisdiction/domain wedge and human QA; **red** = not credible as described without a funded data partner or narrowing.

---

## 1. CommentWindow Registry / DocketClock

**Technical verdict: green for federal-only MVP; yellow for state/local expansion.** Confidence: 75.

**Feasibility attack**

- **Data/API:** Federal Register, Regulations.gov, and Mirrulations make the federal wedge real. Legistar helps with local meetings but does not provide comment-period objects. State registers and clerk continuances are heterogeneous.
- **Ingestion burden:** Federal ETL is medium. State/local creates a scraper-maintenance business unless scoped jurisdiction by jurisdiction.
- **Entity resolution:** Needs canonical docket/rule/document/comment-period objects and source-level provenance. Cross-linking Federal Register ↔ Regulations.gov is feasible; local agenda item ↔ permit/docket is often fuzzy.
- **LLM/COGS:** LLM can summarize/propose deadline extraction, but deadline values must be deterministic or human-verified. COGS manageable for metadata-first federal monitoring.
- **Submission/channel constraints:** API/webhooks/RSS/ICS are safe. “Where can action be filed?” must not imply automated filing unless endpoint is verified.
- **Security/privacy:** Low PII if mostly watchlists. Higher if user alerts store issues/locations.
- **Minimum credible proof:** A public federal deadline API with freshness checks and a provenance dashboard that catches source changes, withdrawals, reopening, and corrections.

**Shadow paths**

- Happy: docket has explicit open/close dates → normalized deadline with source URL and confidence.
- Nil: no comment close date → emit `unknown_deadline`, not a guessed date.
- Empty: API returns no open dockets for watchlist → send no-results heartbeat, not silence.
- Error: Regulations.gov/API/mirror stale → degrade to last-known with stale marker and suppress SLA claims.

**Smallest feasible MVP**

Federal-only: open-comment dockets from Federal Register + Regulations.gov, canonical fields, confidence/provenance, watchlists, RSS/ICS/webhooks, CSV export, and a manual verification queue for contested dates.

**Technical kill condition**

If design partners require state/local deadline coverage before paying, kill or spin down: the proposed architecture becomes a bespoke scraper ops company before the federal substrate proves value.

---

## 2. RecordReady Clerk Intake

**Technical verdict: yellow.** Confidence: 75.

**Feasibility attack**

- **Data/API:** One Legistar jurisdiction plus one mailbox is feasible. IMAP/Gmail/Graph ingestion is standard. Voicemail transcription and attachment parsing increase risk.
- **Ingestion burden:** Inbound messages are messy but bounded if one mailbox and one meeting body. Attachments/screenshots/petition links require human review.
- **Entity resolution:** Hardest part is matching comments to agenda items/dockets under ambiguity. Requires “unmatched/needs staff decision” as first-class state.
- **LLM/COGS:** LLM classification and extraction costs are acceptable at municipal inbox scale, but official-record output cannot be unsupervised.
- **Submission/channel constraints:** Receipts must follow clerk policy and retention rules. Export format must match existing packet workflow.
- **Security/privacy:** High: public comments may include addresses, phone numbers, medical/legal details, minors, and attachments. Needs access controls, audit log, retention/deletion policy.
- **Minimum credible proof:** Staff can process a real meeting packet faster with lower missed-item rate than manual workflow, while every automated match is reviewable.

**Shadow paths**

- Happy: inbound email clearly references agenda item → suggested match, extracted speaker/contact/attachment, receipt draft.
- Nil: no agenda or docket reference → route to unmatched queue.
- Empty: no messages before meeting → generate empty packet with audit trail.
- Error: mailbox/API/transcription fails → do not lose messages; show ingestion health and retry/backfill.

**Smallest feasible MVP**

One Legistar body, one intake mailbox, email + PDF/image attachment handling, agenda-item matching suggestions, duplicate clustering, staff review queue, receipt email, and PDF/CSV export. No voicemail in MVP unless customer demands it.

**Technical kill condition**

If staff will not allow the system to touch official-record material without full procurement/security review, or if packet export cannot fit their legal format, kill the SaaS wedge and reposition as internal triage prototype.

---

## 3. Consensus Comment Room

**Technical verdict: yellow.** Confidence: 75.

**Feasibility attack**

- **Data/API:** Federal dockets are available. Pol.is-style clustering patterns are known. Direct automated submission is constrained and reputationally risky.
- **Ingestion burden:** Low for one docket room; moderate if evidence uploads and attestation are included.
- **Entity resolution:** Needs participant identity/session integrity, duplicate participant handling, and mapping interview answers to claims/evidence, not just text similarity.
- **LLM/COGS:** Summarizing many comments and drafting packets can get expensive but manageable per campaign. Human review is required to avoid hallucinated consensus.
- **Submission/channel constraints:** Manual filing instructions and receipt capture are safer than API submission. Regulations.gov submission automation may trigger anti-spam/astroturf concerns.
- **Security/privacy:** Sensitive political views and lived-experience details. Requires explicit consent, provenance, dissent preservation, and export controls.
- **Minimum credible proof:** A room produces fewer, more distinct, source-backed comments than form-letter mobilization, and participants accept how dissent is represented.

**Shadow paths**

- Happy: enough participants answer prompts → clusters, consensus/minority statements, reviewed packet.
- Nil: user gives no evidence or attestation → include as low-confidence opinion or exclude from evidence claims.
- Empty: room has too few participants → produce individual comment help, not “consensus.”
- Error: LLM clustering/summarization fails → preserve raw answers and fall back to manual synthesis.

**Smallest feasible MVP**

One federal domain, organizer-created room, 7-question structured interview, similarity clustering, human-reviewed consensus/minority packet, manual filing instructions, receipt upload/capture, public provenance page.

**Technical kill condition**

If organizers or agencies perceive the output as AI-laundered astroturf despite provenance/dissent controls, kill automated synthesis and keep only structured evidence collection.

---

## 4. Affected-Party Verifier / Notice Compact

**Technical verdict: yellow.** Confidence: 75.

**Feasibility attack**

- **Data/API:** Parcel/radius verification is feasible in cities with accessible GIS/assessor/OpenAddresses data. Renter/business/worker status cannot be fully verified from public data.
- **Ingestion burden:** One city/process type is manageable. Multi-city parcel schemas and geocoding edge cases are large ongoing work.
- **Entity resolution:** Address ↔ parcel ↔ notice radius is tractable but must handle multi-unit buildings, bad geocodes, PO boxes, homelessness, workers, parents, and businesses.
- **LLM/COGS:** Minimal LLM required; better as rules/geospatial plus staff audit.
- **Submission/channel constraints:** Official packets can report status counts/arguments but should not exclude unverified speakers.
- **Security/privacy:** Very high: private addresses, tenancy status, possibly protected populations. Needs hashing, separation of identity from public comments, audit access, and threat modeling for landlord/developer misuse.
- **Minimum credible proof:** For one variance case, the system accurately verifies address-in-radius and produces a staff-acceptable packet without exposing private addresses.

**Shadow paths**

- Happy: address geocodes inside radius → verified affected status with private audit trail.
- Nil: user lacks address or declines verification → allow unverified comment.
- Empty: no affected residents participate → report zero verified participants, not “no affected parties.”
- Error: GIS/geocoder unavailable or ambiguous → mark pending/manual review; do not deny status.

**Smallest feasible MVP**

One city, zoning variance notice radius, address-to-parcel/radius verification, renter self-attestation, private audit trail, staff-reviewed packet with aggregate counts and arguments.

**Technical kill condition**

If local parcel/address data cannot reliably resolve multi-unit and renter addresses, or if partners need legally binding verification rather than advisory status labels, kill the verifier claim.

---

## 5. Concern Router / Civic RouteMap

**Technical verdict: yellow.** Confidence: 75.

**Feasibility attack**

- **Data/API:** Sources exist for federal dockets, state bills, Legistar, boundaries, and some local processes. No single authoritative “concern → civic lever” graph exists.
- **Ingestion burden:** One metro + federal + one state is feasible. Broad coverage becomes source integration sprawl.
- **Entity resolution:** Hard: map plain-language concern + location to issue taxonomy, jurisdiction, live process, deadline, and eligibility. False positives are the core risk.
- **LLM/COGS:** LLM classification can help but must be bounded by indexed official sources and conservative thresholds. RuleBox-style cheap classifiers may be better after initial labeling.
- **Submission/channel constraints:** Should be navigator-facing first. Consumer self-serve wrong routing will burn trust.
- **Security/privacy:** Intake may include legal/housing/health facts; avoid storing unnecessary PII and make “no reliable path found” normal.
- **Minimum credible proof:** Navigators agree that top results are useful and safely caveated for a real intake sample, including correct “no official path found” outcomes.

**Shadow paths**

- Happy: concern and location match active process → return official path, deadline, confidence, why matched.
- Nil: no location or vague concern → ask clarifying question or return broad resources.
- Empty: no live lever found → explicit no-path result with monitoring option.
- Error: upstream source fails → suppress affected source or mark stale; do not hallucinate route.

**Smallest feasible MVP**

Navigator form for one metro: federal dockets, one Open States state, one Legistar city/county, geocoded jurisdiction lookup, conservative confidence, citations, and no-path state.

**Technical kill condition**

If validated navigator cases require many local non-Legistar/permit sources before useful routing appears, kill the broad router and pivot to a narrower vertical source product.

---

## 6. NoticeNail / Lot Line

**Technical verdict: yellow leaning red.** Confidence: 75.

**Feasibility attack**

- **Data/API:** OCR + photo upload is easy. Matching notices to parcels/cases/deadlines depends heavily on local permit/planning systems and notice formatting.
- **Ingestion burden:** Human QA is not optional. National permit database is explicitly infeasible; one city only.
- **Entity resolution:** Hard: photo text → address/case number → parcel → official case → deadline. Notices may omit key fields or be damaged.
- **LLM/COGS:** OCR/vision costs are manageable at local volume; QA labor dominates.
- **Submission/channel constraints:** Alerts to nearby subscribers create reliance risk; must distinguish “captured notice” from complete official coverage.
- **Security/privacy:** Photos can include homes, people, license plates; radius alerts can enable harassment. Need redaction and abuse controls.
- **Minimum credible proof:** In one city, captured notices can be verified and alerted fast enough to beat 10–20 day windows with acceptable false-negative caveats.

**Shadow paths**

- Happy: clear photo with case/deadline/address → verified case card and radius alert.
- Nil: missing deadline/case number → create pending card, no deadline alert until verified.
- Empty: no notices captured in area → do not imply no projects; show coverage gap.
- Error: OCR/case lookup fails → route to human QA or reject as unverifiable.

**Smallest feasible MVP**

One city, photo upload, OCR only for address/case/deadline, parcel lookup, human verification queue, public case card, opt-in radius alerts. No automated legal advice or completeness claims.

**Technical kill condition**

If notices are too inconsistent to verify before deadlines without heavy field/human operations, kill or reframe as newsroom tipline rather than alert infrastructure.

---

## 7. Tenant Displacement Docket

**Technical verdict: yellow.** Confidence: 75.

**Feasibility attack**

- **Data/API:** Feasible only in tenant-protection-rich cities with open permits, rent-stabilized/multi-unit lists, assessor data, and known case triggers. Many cities will not expose early enough signals.
- **Ingestion burden:** Moderate-to-high city-specific ETL across permits, parcels, ordinances, agendas, and legal-aid rules.
- **Entity resolution:** Address/building ↔ permit/case ↔ tenancy/rent-stabilization status is hard and legally nuanced.
- **LLM/COGS:** Summaries/checklists should be expert-reviewed. Translation adds cost and liability.
- **Submission/channel constraints:** Appeals/testimony requirements are local and deadline-sensitive; must avoid legal-advice posture.
- **Security/privacy:** Very high. Tenant targeting, landlord misuse, immigration/domestic-safety concerns. Public alerts should avoid identifying vulnerable tenants.
- **Minimum credible proof:** A legal-aid/tenant-union partner confirms alerts are earlier than their current process and actionable for a selected case type.

**Shadow paths**

- Happy: demolition permit on protected multi-unit building → reviewed alert with deadline and checklist.
- Nil: building has unknown tenancy/protection status → low-confidence/internal review, not public tenant warning.
- Empty: no relevant cases → partner dashboard says no reviewed alerts, not no displacement risk.
- Error: permit feed delayed or missing → stale-source banner and no “all clear.”

**Smallest feasible MVP**

One city, one case type such as demolition permits for rent-stabilized/multi-unit buildings, one anchor partner, human-reviewed alerts, deadline cards, evidence prompts, outcome tracking.

**Technical kill condition**

If source data does not reveal tenant-impacting cases before the appeal/comment window, kill the early-warning claim.

---

## 8. Conditions Keeper / Outcome Graph

**Technical verdict: yellow.** Confidence: 75.

**Feasibility attack**

- **Data/API:** Legistar actions/votes/minutes are available in many cities. Permit status/attachments and condition documents are uneven.
- **Ingestion burden:** One planning commission is feasible with manual extraction. Automated condition extraction across jurisdictions is not.
- **Entity resolution:** Must track a case across agenda items, continuances, minutes, attachments, final documents, appeal periods, and permit enforcement IDs.
- **LLM/COGS:** LLM-assisted condition extraction is useful but needs human review because condition language is ambiguous.
- **Submission/channel constraints:** Outcome receipts must be conservative; avoid claiming enforcement/noncompliance without evidence.
- **Security/privacy:** Lower than verifier/tenant products, but comments and appeals may include personal data.
- **Minimum credible proof:** For one commission, users receive accurate continued-date/appeal/conditions updates faster than manually monitoring agendas/minutes.

**Shadow paths**

- Happy: case continued/approved with conditions → updated outcome receipt with source links.
- Nil: minutes omit appeal deadline or conditions → mark unknown and queue manual review.
- Empty: no action taken/no meeting record yet → pending state with next check.
- Error: Legistar/attachment fetch fails → stale marker and retry, no outcome assertion.

**Smallest feasible MVP**

One city planning commission, watch bookmarked cases, track continuance date, appeal deadline, vote, and conditions using Legistar plus manual/LLM-assisted extraction with human approval.

**Technical kill condition**

If final conditions/appeal deadlines are not published in accessible documents soon enough for reminders, kill the “next-window” promise.

---

## 9. CareRule Scout / Benefits Plainwatch

**Technical verdict: yellow.** Confidence: 75.

**Feasibility attack**

- **Data/API:** Federal CMS/HHS rulemaking is feasible. Medicaid waivers/SPAs, state registers, manuals, and transmittals are fragmented and legally nuanced.
- **Ingestion burden:** High unless narrowed to one program and 2–3 states with expert partners.
- **Entity resolution:** Need map from rule/SPA/manual change to program, population, benefits, eligibility, geography, and comment/action deadline. Many changes are not simple docket objects.
- **LLM/COGS:** Expert-reviewed summaries are mandatory. LLM can draft plain-language impact hypotheses but cannot be final authority.
- **Submission/channel constraints:** Direct-to-recipient alerts can cause panic; start with navigators/P&A/legal-aid.
- **Security/privacy:** If profiles include disability/care details, treat as highly sensitive. Avoid storing diagnosis/service data where possible.
- **Minimum credible proof:** Experts validate that alerts are relevant, accurate, and not panic-inducing for one program/region.

**Shadow paths**

- Happy: CMS/state notice matches profile → cited summary, “might change,” deadline, comment guide.
- Nil: profile lacks program/state/service details → broad digest or ask navigator to complete.
- Empty: no matching changes → periodic “no reviewed changes” digest.
- Error: source PDF/manual unavailable or parsing fails → queue expert review, no alert.

**Smallest feasible MVP**

HCBS waiver families/navigators in 2–3 states plus federal CMS rules, expert-reviewed alerts/summaries, no direct mass recipient push, manual comment guidance and receipt capture.

**Technical kill condition**

If state sources cannot be monitored with enough reliability or expert review cannot be funded, kill the family-facing alert product and keep only federal/navigator research briefs.

---

## 10. Childcare Rule Radar / CareNotice Counsel

**Technical verdict: yellow.** Confidence: 75.

**Feasibility attack**

- **Data/API:** One state’s register, childcare agency calendars, and HHS/ACF federal rules are feasible. 50-state coverage is not an MVP.
- **Ingestion burden:** State register + agency hearings + licensing taxonomy require manual mapping but bounded in one state.
- **Entity resolution:** Need connect rule text to license type, capacity, subsidy participation, food program, staff ratio, inspection category.
- **LLM/COGS:** Low-to-medium at one-state scale; summaries and applicability need human review to avoid quasi-legal advice errors.
- **Submission/channel constraints:** Manual filing/receipt upload is safer. Providers are time-constrained; alerts must be very actionable.
- **Security/privacy:** Business/license profile data is moderately sensitive. Avoid child-specific data.
- **Minimum credible proof:** A childcare association confirms alerts catch relevant windows and reduce interpretation burden for a provider subtype.

**Shadow paths**

- Happy: notice matches license profile → reviewed alert with operational impact and filing steps.
- Nil: missing license/profile data → generic association-level alert.
- Empty: no relevant notices → digest says no reviewed changes for profile.
- Error: register/calendar scrape fails → stale-source banner and no all-clear.

**Smallest feasible MVP**

One state, one provider type, state register notices + childcare agency hearings + HHS/ACF rules, human-reviewed beta alerts, manual filing instructions, receipt upload.

**Technical kill condition**

If association bundle/channel is unavailable and individual providers will not maintain profiles or pay, kill the standalone SaaS despite technical feasibility.

---

## 11. Pharmacy Docket Desk

**Technical verdict: green-yellow.** Confidence: 75.

**Feasibility attack**

- **Data/API:** Federal Register/Regulations.gov plus one state board/Medicaid notices and Open States pharmacy bills are feasible. Board calendars may require scraping.
- **Ingestion burden:** One state + federal CMS/DEA/FDA is manageable if scoped to independent retail pharmacies.
- **Entity resolution:** License/profile ↔ rule/bill/board item taxonomy matters: vaccines, Medicaid, controlled substances, compounding, DME, audits.
- **LLM/COGS:** Cited memos/checklists can be generated cheaply at this source volume but require expert/legal review for interpretation.
- **Submission/channel constraints:** Manual comment/board-hearing prompts and receipt tracking are safe. Avoid legal advice and compliance guarantees.
- **Security/privacy:** Business profile data and compliance/audit concerns are sensitive but less risky than health-recipient PII if no patient data is stored.
- **Minimum credible proof:** State association/PSAO validates relevance and willingness to distribute to members.

**Shadow paths**

- Happy: CMS/DEA/FDA/state board item matches pharmacy profile → memo, deadline, suggested evidence prompts.
- Nil: profile lacks services/licensure details → broad pharmacy digest.
- Empty: no matching items → weekly no-change digest.
- Error: board page/API unavailable → stale marker and manual check queue.

**Smallest feasible MVP**

One state plus federal CMS/DEA/FDA, independent pharmacies offering vaccines and Medicaid, explicit pharmacy bills/rules/board hearings, confidence labels, source citations, manual filing/receipt tracking.

**Technical kill condition**

If association/PSAO channel says existing newsletters already satisfy the need or refuses to endorse counsel-lite interpretations, kill direct-to-pharmacy acquisition.

---

## 12. Schoolyard Radius

**Technical verdict: yellow.** Confidence: 75.

**Feasibility attack**

- **Data/API:** School locations, public K–8 data, GIS buffers, crash/GTFS layers, and local planning feeds exist unevenly. Childcare data adds complexity; start with public schools.
- **Ingestion burden:** One metro is feasible; walking-corridor routing and environmental layers add nontrivial GIS work.
- **Entity resolution:** Project/case ↔ parcel/route/buffer ↔ school boundary/walking corridor. Must avoid over-alerting every nearby permit.
- **LLM/COGS:** LLM useful for prompt categories and mitigation comment drafting, but geospatial filtering/ranking should be deterministic.
- **Submission/channel constraints:** Comments should be mitigation/safety-framed; avoid becoming generic anti-housing alerting.
- **Security/privacy:** Do not expose child-level data. Be careful with school safety and location-based alerting.
- **Minimum credible proof:** PTA/district/safe-routes partner validates that ranked alerts are relevant and not noise for real recent cases.

**Shadow paths**

- Happy: project within threshold and category match → alert with safety relevance and comment prompts.
- Nil: missing project geometry → use address/parcel fallback or manual review.
- Empty: no projects near school → no-change digest, not safety assurance.
- Error: planning/GIS source fails → stale coverage marker and suppress all-clear.

**Smallest feasible MVP**

One metro, public K–8 schools, projects within 1,000 feet or simple walking corridor, three categories: construction staging, traffic circulation, environmental review; human-reviewed alerts.

**Technical kill condition**

If local planning feeds lack geocodable project locations or produce too many irrelevant alerts after filtering, kill the radius product or narrow to one case type.

---

## 13. Open Issue Escalator

**Technical verdict: yellow leaning red.** Confidence: 75.

**Feasibility attack**

- **Data/API:** Open311 and Legistar are feasible where both exist. The hard part is proving a recurring service complaint maps to a real budget/procurement/hearing lever.
- **Ingestion burden:** One issue category in one city is manageable. Cross-category “civic lever” matching is broad and fuzzy.
- **Entity resolution:** Need cluster tickets by location/problem, then map to agenda items, budget lines, capital projects, contracts, or committee topics. This is weakly structured.
- **LLM/COGS:** LLM can classify agenda relevance, but false positives will frustrate residents. COGS manageable; human validation likely required.
- **Submission/channel constraints:** Must avoid promising that testimony will fix service issues. Outcome tracking depends on work-order/budget data availability.
- **Security/privacy:** Public 311 data may contain addresses or sensitive conditions; equity overlays can stigmatize locations if mishandled.
- **Minimum credible proof:** For one category, clusters regularly connect to actual public levers and residents/council staff agree the testimony packet is useful.

**Shadow paths**

- Happy: unresolved sidewalk/ADA cluster maps to committee/capital-plan agenda → alert and collect testimony.
- Nil: ticket lacks location/category → exclude or manual classify.
- Empty: clusters have no public lever → show “monitoring/no lever found,” not a campaign.
- Error: Open311/Legistar feed fails → stale marker and no escalation claims.

**Smallest feasible MVP**

One city with Open311 + Legistar, one issue category such as sidewalk/ADA hazards or flooding, public 311 clustering, relevant-agenda watch, testimony packet builder, outcome tracker for agenda/vote/allocation status.

**Technical kill condition**

If most clusters do not connect to actionable public levers within a reasonable window, kill: it becomes another frustration dashboard, not an escalator.

---

# Cross-candidate feasibility ranking

## Most buildable first wedges

1. **CommentWindow Registry / DocketClock, federal-only** — strongest API/data foundation and cleanest proof.
2. **Pharmacy Docket Desk, one state + federal** — narrow payer/channel, manageable sources, lower PII.
3. **RecordReady Clerk Intake, one Legistar jurisdiction/mailbox** — technically bounded but security/procurement-heavy.
4. **Childcare Rule Radar, one state/provider type** — feasible with association channel and human review.
5. **Conditions Keeper, one planning commission** — viable if final docs/appeal deadlines are accessible.

## Feasible only with strict partner/jurisdiction wedge

- **Concern Router** — valuable but must start navigator-facing and support no-path.
- **Affected-Party Verifier** — geospatially feasible, privacy/procedurally risky.
- **CareRule Scout** — needs expert review and very narrow program/state scope.
- **Tenant Displacement Docket** — only works where early permit/protection data exists.
- **Schoolyard Radius** — GIS feasible, alert relevance/noise is the risk.
- **Consensus Comment Room** — technically easy enough, reputational/provenance risk dominates.

## Highest technical/data-risk candidates

- **NoticeNail / Lot Line** — photo/OCR is easy; timely official case/deadline verification is the hard part.
- **Open Issue Escalator** — clustering 311 is easy; finding actual public levers often may not happen.

# Architectural rescue pattern

For any candidate advanced to implementation, require this minimum architecture before coding:

1. **Canonical source object:** every alert/comment/packet points to immutable source URLs, fetched timestamps, parser version, and confidence.
2. **Unknown as a first-class state:** no deadline, no match, no route, no source, and stale source must be valid product outcomes.
3. **Human-review gate for high-stakes assertions:** deadlines, affected status, legal/procedural meaning, official-record classification, and health/benefits impact.
4. **Narrow source contract:** one jurisdiction/domain/source class in MVP; no “national” promise until the data operations are measured.
5. **Rollback/suppression:** if upstream feeds fail or parser confidence drops, suppress alerts that would create false certainty.
6. **Privacy minimization:** store only what is required for matching/receipts; separate public comments from private verification/profile data.
7. **Proof metric:** each MVP must prove either earlier discovery, less staff time, fewer missed deadlines, or higher-quality official-record submissions against a real partner workflow.
