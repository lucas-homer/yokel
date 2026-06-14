# Ensemble ballot — defensibility / negative selection

Scores are 1–10, where higher means more defensible after penalizing hidden fatal assumptions, incumbent-adjacent creep, weak novelty, and recurring civic-tech failure modes.

| Rank | Survivor | Defensibility | Resists incumbent adjacency creep | Risk-adjusted novelty | Avoids civic-tech failure modes | Overall |
|---:|---|---:|---:|---:|---:|---:|
| 1 | Pharmacy Docket Desk | 8 | 6 | 7 | 8 | 7.3 |
| 2 | CommentWindow Registry / DocketClock | 8 | 7 | 6 | 7 | 7.0 |
| 3 | Childcare Rule Radar / CareNotice Counsel | 7 | 6 | 7 | 8 | 7.0 |
| 4 | RecordReady Clerk Intake | 7 | 7 | 6 | 7 | 6.8 |
| 5 | CareRule Scout / Benefits Plainwatch | 7 | 6 | 7 | 6 | 6.5 |
| 6 | Tenant Displacement Docket | 6 | 7 | 7 | 5 | 6.3 |
| 7 | Conditions Keeper / Outcome Graph | 6 | 6 | 5 | 6 | 5.8 |
| 8 | Concern Router / Civic RouteMap | 5 | 5 | 6 | 5 | 5.3 |

## Rationale and required changes

**1. Pharmacy Docket Desk — 7.3.** This is the most defensible survivor because it has a concrete paying workflow, identifiable channels, and less dependence on mass civic behavior change. The main negative-selection issue is incumbent adjacency: associations, PSAOs, newsletters, and policy trackers already occupy the trust layer, so a direct SaaS wedge would likely lose. Required changes: make the channel the product surface, restrict to one state plus CMS/DEA/FDA, provide member-specific action files rather than generic alerts, and avoid counsel-like interpretation unless expert-reviewed.

**2. CommentWindow Registry / DocketClock — 7.0.** The federal-only deadline-object wedge is defensible because the source base exists and downstream tools genuinely need reliable plumbing. The fatal assumption would be that deadline correctness can be automated into an SLA cheaply; one wrong deadline can erase trust. Required changes: stay federal-only, publish provenance/confidence/change logs, treat uncertainty as a first-class state, and require human review for contested or changed deadlines before making strong reliability claims.

**3. Childcare Rule Radar / CareNotice Counsel — 7.0.** The pain is real and operational, but the product only survives if bundled through associations, CCR&Rs, or shared-service networks; exhausted providers are unlikely to buy or use another standalone alert inbox. Its novelty is stronger than generic policy tracking because it can map rules to provider type and compliance impact. Required changes: one state, one provider type, human-reviewed operational impact briefs, post-adoption compliance support, and no generic civic-engagement framing.

**4. RecordReady Clerk Intake — 6.8.** This has a concrete 72-hour staff workflow and a believable bounded MVP, but it sits close to agenda-management vendors and official-record custody risk. The hidden assumption is that staff will trust clustering/classification enough to save time without increasing procedural anxiety. Required changes: one Legistar jurisdiction, one mailbox, staff approval before anything becomes record-ready, immutable audit trail, export into existing workflows, and no autonomous official-record decisions.

**5. CareRule Scout / Benefits Plainwatch — 6.5.** High stakes and trusted-intermediary demand make this worth keeping, but the consequence of being wrong is unusually severe: panic, missed action, or quasi-legal advice around benefits. The assumption that fragmented Medicaid/HCBS sources can be summarized safely is not yet proven. Required changes: navigator/P&A/legal-aid audience only, one program and region, expert review, calm confidence-labeled framing, no eligibility determinations, and no direct mass alerts to recipients until validated.

**6. Tenant Displacement Docket — 6.3.** The need is urgent and differentiated, but the core premise depends on source data being early enough to matter and safe enough not to expose vulnerable tenants or buildings. If alerts arrive after strategic intervention windows, the product becomes anxiety infrastructure; if public, it can aid landlord or speculator targeting. Required changes: one tenant-protection-rich city, one case type, anchor legal-aid/tenant-union partner, organization-mediated access, strict anti-misuse controls, and proof that alerts precede actionable intervention windows.

**7. Conditions Keeper / Outcome Graph — 5.8.** The after-action loop is neglected, but novelty is weaker because much of the value is receipt tracking and reminders rather than a standalone product. The fatal creep risk is claiming enforcement, causality, or “your comment mattered” when the record only supports limited procedural facts. Required changes: start as a narrow source-linked receipt module for continuances, votes, appeal deadlines, and condition-text changes; avoid compliance accusations, outcome causality, and broad accountability claims until enforcement data is available.

**8. Concern Router / Civic RouteMap — 5.3.** This is the least defensible survivor because its central promise—mapping arbitrary concerns to the right official lever—is exactly where civic-tech tools often overpromise and burn trust. The hidden fatal assumption is that enough concerns have timely, legible, actionable official paths; many will not. Required changes: navigator-facing only, one metro plus tightly scoped federal/state/local sources, conservative confidence, citations for every route, “no reliable path found” as a normal answer, and human escalation before user-facing recommendations.
