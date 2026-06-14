# Final synthesis: seasoned civic-tech project portfolio

## Adjudication summary

I did not average the lens rankings. The final portfolio favors ideas with: (1) an acute deadline or material consequence, (2) a narrow user/payer wedge, (3) source data that exists now, (4) a credible path around civic-tech maintenance and funding traps, and (5) an explicit answer to “how do I know my effort was not wasted?”

The strongest pattern is **deadline-driven monitoring + quality-preserving action + honest outcome receipts**, not generic civic engagement. The main split in the foundry outputs is that product/civic-impact liked local land-use organizing, feasibility/adversarial preferred federal rulemaking data, and funding liked infrastructure/B2G. The synthesis below keeps local ideas only where they are tightly scoped and funded, and promotes federal/state/regulatory ideas where the data substrate is stronger.

## Scoreboard

| Rank | Final idea | Status | Why it made the cut |
|---:|---|---|---|
| 1 | **ScopeWatch: practice rule radar for independent clinicians** | Lead wedge | Strong willingness to pay; rules affect revenue, scope, and claim risk; federal CMS/HHS data can support a narrow MVP. |
| 2 | **DocketClock: comment-deadline API and alert layer** | Enabling infrastructure | “Deadline as a first-class civic object” is the cleanest gap; useful to every other product if kept federal/high-confidence first. |
| 3 | **CodeRed: local rule radar for independent food-service operators** | Vertical local wedge | Concrete SMB pain, repeat local exposure, reachable through associations/chambers; Legistar-first MVP avoids parcel-data trap. |
| 4 | **Lot Line + Block Whip: verified affected-neighbor land-use alerts and action** | High-impact but city-scoped | Best consumer civic story and strongest local leverage, but only viable in qualified data-rich cities; must avoid NIMBY/false-security failure. |
| 5 | **Comment Workshop + Closed the Loop: quality comment coach and outcome receipt engine** | Cross-cutting product/module | Directly addresses wasted civic effort and form-letter discounting; works as a module behind vertical alert products. |
| 6 | **Watershed Watch: permit/docket radar for regional environmental groups** | Foundation/regional pilot | Mission fit and action loop are strong; only viable with anchor funders and a limited geography/source set. |
| 7 | **Statehouse RuleWatch by issue domain** | Deferred-but-promising | Real white space, but not as a 50-state generic product. Consider later as “state rulemaking for water/childcare/eldercare” with grant/open-data backing. |

### Deferred or merged

| Idea | Decision | Note |
|---|---|---|
| **RuleRadar for Small Operators** | **Merged/split** | Too horizontal. Its viable pieces become ScopeWatch, CodeRed, or a future one-vertical operator product. |
| **ParcelWatch** | **Merged as backend only** | Valuable, but dangerous as a standalone per-city infrastructure business before demand is proven. Build only what Lot Line/Watershed need. |
| **Permit Pulse** | **Merged/deferred** | Useful retention layer for Lot Line, but noisy as a standalone because most permits have no public action lever. |
| **Consensus Comment** | **Merged as feature** | Strong for already-mobilized campaigns, weak as a destination product. Use inside Block Whip/Watershed/Comment Workshop. |
| **Closed the Loop** | **Merged as feature** | Essential retention primitive, but weak initial pull alone. |
| **Comment Workshop** | **Kept as module/product** | Valuable only if optimized for fewer better comments, not mass AI paraphrasing. |
| **Generic civic habit/streak product** | **Deferred** | Aspirational frequency is not enough; must attach to real stakes and deadlines. |

---

## 1. ScopeWatch — practice rule radar for independent clinicians

**Tagline:** “Know which rule changes your reimbursement, scope, or compliance risk before it becomes final.”

**Target user:** Solo and small-group clinicians or practice managers, starting with one specialty such as PT/OT, behavioral health, optometry, or nurse practitioners in a small set of high-churn states.

**Specific problem:** Independent practices lack compliance/policy staff. CMS, HHS, state Medicaid, and licensing-board changes can alter reimbursement, scope of practice, documentation, and legal exposure. They often learn after claims are denied or workflows must change.

**Solution:** Onboard by specialty, state, payer mix, and practice size. Monitor Federal Register/Regulations.gov for CMS/HHS rulemakings first; later add state Medicaid and board notices selectively. Use Mirrulations/spicy-regs for historical context and RuleBox-style cached classification rules to map dockets to specialty profiles. Each alert explains: “Does this hit you?”, likely revenue/legal direction, deadline, source links, and what evidence would make a useful comment.

**Why this is a gap / not duplicate:** Associations and lobbyists serve members and large systems; Quorum/FiscalNote are B2B policy tools. The gap is “does this proposed rule affect *my small practice* and what can I do this week?”

**What it builds on:** Federal Register API, Regulations.gov data, Mirrulations S3 mirror, spicy-regs DuckDB/Parquet/MCP pattern, RuleBox-style classification, MAPLE-style digest/archive patterns.

**MVP scope:** One specialty, federal CMS/HHS only, 3–5 states for profile relevance but not state ingestion. Human-reviewed relevance labels during beta. No legal-advice claims; no fully automated filing. Provide draft guidance and manual submission/receipt capture if public submission APIs are unavailable.

**Action / impact loop:** Alert → user contributes real operational facts → comment filed manually or through supported channel → receipt stored → final rule watched → plain-language update: addressed, partially addressed, rejected with reason, not found, or still pending.

**Business / funding model:** SMB subscription or association bundle. Price around practice value, not “civic participation”: e.g. per-practice monthly subscription, association sponsorship, billing-consultant channel.

**Key risks:** Existing associations may already own trust; relevance false positives kill confidence; liability if framed as compliance advice; state data becomes a scraper swamp.

**Mitigations:** Start through trusted intermediaries; show source citations and confidence; frame as policy monitoring, not legal advice; keep state ingestion narrow and funded by specialty demand.

**Candid verdict:** Best first commercial wedge. It is civic-tech by outcome, but it should be sold as risk/revenue intelligence for small practices.

---

## 2. DocketClock — the comment-deadline API and alert layer

**Tagline:** “Every public-comment window as a reliable, subscribable deadline object.”

**Target user:** Civic orgs, associations, newsroom/product builders, vertical products in this portfolio, and eventually agencies or clerks needing structured deadline/intake workflows.

**Specific problem:** Comment deadlines are buried in inconsistent source systems. Regulations.gov has fields, state/local sources vary, and no normalized API answers: “What is open, what closes soon, where can someone act, and how confident is this deadline?”

**Solution:** Build a federal-first deadline index with canonical objects: source ID, title, agency, open/close date, timezone/confidence, status, submission URL, official source, last-seen timestamp, and watchlist/ICS/webhook support. Add state/local only after high-confidence source playbooks exist.

**Why this is a gap / not duplicate:** Regulations.gov is a portal, not a user-centered deadline service. Mirrulations mirrors data but does not operate a maintained alert product. Open States/Legistar/OCD do not model public-comment deadlines as first-class cross-source objects.

**What it builds on:** Regulations.gov and Federal Register freshness APIs, Mirrulations history, mirrulations-search fields such as `is_open_for_comment` and comment dates, Open Civic Data IDs/schema ideas, ICS/webhook conventions.

**MVP scope:** Federal comment deadlines only. REST/CSV/ICS/webhook outputs. Explicit confidence fields. No B2G dashboard, no resident verification, no state/local PDF scraping in v1.

**Action / impact loop:** Deadline discovery prevents missed windows; downstream products report when an item closes, finalizes, or changes status. DocketClock should not itself overclaim political impact.

**Business / funding model:** Open schema/free public tier; paid API volume, SLA, webhooks, and organization watchlists. B2G clerk dashboard only after a vertical product creates verified input that agencies actually want.

**Key risks:** Two-sided marketplace trap; wrong deadlines are catastrophic; public Regulations.gov submission API availability may be limited; state/local expansion explodes maintenance.

**Mitigations:** Keep v1 read-only and federal; publish provenance/confidence; separate deadline discovery from submission; add sources only with maintenance budgets.

**Candid verdict:** The best infrastructure idea, but not the first consumer app. It should be built as the shared substrate behind vertical wedges.

---

## 3. CodeRed — local rule radar for independent food-service operators

**Tagline:** “City hall changes that can cost your restaurant money, license risk, or operating flexibility — before the vote.”

**Target user:** Independent restaurants, cafes, food trucks, bodegas, caterers, and local restaurant/chamber associations in one launch city.

**Specific problem:** Food-service operators are blindsided by sidewalk-dining rules, parklet changes, license fees, plastics/organics mandates, health-board hearings, signage rules, scheduling ordinances, and permit changes. These are local, consequential, and often decided in committee before owners hear about them.

**Solution:** Onboard by business address and type. Resolve jurisdictions/districts. Monitor Legistar city/county agenda and bill data first; add selected board-of-health or licensing sources only where partner demand exists. Classify restaurant-relevant items into a small vocabulary and produce short “what this could change / what you can still do” cards.

**Why this is a gap / not duplicate:** Gov participation suites are project silos. Quorum/FiscalNote serve lobbyists and large organizations. Restaurants need a city-specific operator brief and 2-minute action path, not a generic legislative tracker.

**What it builds on:** Legistar OData Web API, City Scrapers pattern for limited long-tail sources, MapIt-style address-to-jurisdiction mapping, WriteToThem-style routing, RuleBox-style local-topic classification.

**MVP scope:** One city, one subvertical, Legistar-first. Track council/committee items and fee/ordinance changes; do not attempt national health-code or permit ingestion at launch. Partner with an association/chamber/BID for distribution.

**Action / impact loop:** Alert → owner submits distinct operational evidence or signs an association packet → hearing/vote tracked → update explains vote, amendments, and next compliance/action step.

**Business / funding model:** Association/chamber bundle, sponsored city pilot, or per-location SMB subscription. Sell time/risk savings, not “civic engagement.”

**Key risks:** Low-margin SMB churn; local data fragmentation; perceived industry lobbying; no universal local submission path.

**Mitigations:** Use trusted local channels; start with money/license-risk topics only; require distinct evidence rather than form letters; route to official email/forms manually where needed.

**Candid verdict:** A strong local vertical wedge if brutally scoped. It should not become “city hall tracker for every small business.”

---

## 4. Lot Line + Block Whip — affected-neighbor land-use alerts and verified action

**Tagline:** “Never miss the hearing for a project inside your legal notice radius — and organize useful, verified neighbor input.”

**Target user:** Renters, homeowners, small landlords, and the one motivated neighbor who would organize around a specific rezoning/variance if they knew early enough.

**Specific problem:** Residents often learn about nearby development after the effective comment/hearing window. Mailed notices are legalistic, easy to miss, and disconnected from maps, deadlines, and action. When neighbors do respond, officials discount identical form letters or broad Nextdoor outrage.

**Solution:** In qualified cities, watch zoning/variance/development-case sources with reliable geometry, hearing dates, and status. Match cases to a private watched address/radius. For high-salience cases, organizer mode verifies affected addresses, collects distinct comments, clusters consensus conditions, tracks hearing turnout, and produces a source-linked testimony packet.

**Why this is a gap / not duplicate:** coUrbanize/PublicInput are gov/developer project silos; Symbium is parcel-compliance lookup; city trackers are analytics/search. The gap is resident-side discovery tied to legal proximity plus quality-preserving action.

**What it builds on:** ArcGIS/Socrata/Accela where available, Legistar planning agendas, parcel/geocoding sources, OCD Event schema, City Scrapers patterns, Decidim-style verification, Pol.is-style consensus, MapIt-style geo resolution.

**MVP scope:** One data-rich city, one process type: rezoning/variance cases within statutory/legal-notice radius. Manual city qualification and human QA for early alerts. Organizer mode only after an alert; Permit Pulse becomes a later digest layer.

**Action / impact loop:** Address watch → source-linked alert with deadline → verified affected-neighbor comments/RSVPs → hearing/vote/disposition tracked → honest receipt: approved, denied, conditions changed, continued, or no observable effect.

**Business / funding model:** Free/low-cost consumer layer funded by a neutral land-use data/API customer, local newsroom/nonprofit sponsorship, legal/planning org pilots, or foundation support. Avoid monetizing outrage from affluent homeowners.

**Key risks:** Parcel/geospatial data may not exist or be stale; false negatives create false security; NIMBY capture; renter exclusion; privacy risk around home addresses.

**Mitigations:** Launch only where authoritative data is clean; show source/provenance and confidence; store addresses minimally; make renter verification easy; frame campaigns around specific conditions/tradeoffs, not default opposition.

**Candid verdict:** The cleanest consumer civic story and highest local leverage, but technically and politically fragile. Worth doing only as a narrow city-scoped wedge, not a national promise.

---

## 5. Comment Workshop + Closed the Loop — quality comment coach and impact receipt engine

**Tagline:** “Submit fewer, better comments — then find out what happened.”

**Target user:** People or groups already facing a live docket/hearing through ScopeWatch, CodeRed, Lot Line, Watershed Watch, or an external organizer.

**Specific problem:** Mass-action tools create duplicate comments that officials discount; users do not know what makes a comment substantive; after submitting, they hear nothing and assume their effort was wasted.

**Solution:** A guided evidence-collection and drafting flow that asks for real facts, costs, local observations, alternatives, and affected status. It checks for duplication against the platform archive, discourages low-value template comments, and gives manual filing instructions or supported submission where available. The receipt engine stores the user’s main claims and tracks final rules, votes, minutes, or response-to-comments.

**Why this is a gap / not duplicate:** Resistbot/5 Calls optimize volume and Congress outreach. Pol.is supports deliberation but not comment-quality coaching or official-record follow-up. Regulations.gov does not help users make relevant, substantive comments or explain outcomes.

**What it builds on:** Federal Register/Regulations.gov, Mirrulations/spicy-regs for response/final-rule comparison, Legistar votes/minutes where available, MAPLE archive/digest patterns, Pol.is consensus concepts, Decidim accountability concepts.

**MVP scope:** Attach to curated federal dockets or one vertical product. No generic weekly habit app. No bulk paraphrasing. No one-click submission promise unless an official endpoint is available. Capture manual receipt/tracking when possible.

**Action / impact loop:** Issue brief → user fact interview → draft/checklist → official filing/manual receipt → downstream tracking → conservative outcome labels: received, entered into record, addressed, partially addressed, rejected with reason, status changed, not found, or still pending.

**Business / funding model:** Bundle into paid vertical products; license to civic orgs/associations; possibly foundation support for public-interest comment quality. Standalone consumer subscription is weak.

**Key risks:** AI-laundered astroturf; hallucinated citations; misleading causality claims; user disappointment when no impact is visible.

**Mitigations:** Source-grounded drafting; user attestation; similarity checks; sometimes advise “do not submit” or “join a consensus packet”; never say “your comment caused this.”

**Candid verdict:** Essential portfolio module. It is the clearest answer to “my effort should not be wasted,” but it needs a live issue source to create demand.

---

## 6. Watershed Watch — permit and docket radar for regional environmental groups

**Tagline:** “A watch area, a deadline feed, and campaign packets for the environmental decisions your volunteers keep missing.”

**Target user:** Staffed watershed alliances, land trusts, conservation nonprofits, regional environmental coalitions, and their volunteer leaders.

**Specific problem:** Small environmental groups miss or scramble around environmental reviews, wetland/stormwater permits, rezoning near floodplains, federal/state environmental dockets, and local board votes. Their scarce volunteer effort gets spent finding notices instead of producing timely, persuasive evidence.

**Solution:** Define a watch area by watershed/open-space polygon or jurisdiction. Monitor a limited set of federal/state environmental dockets and local agenda/permit sources for that region. Convert matches into deadline cards, evidence prompts, volunteer assignments, consensus packets, and outcome receipts.

**Why this is a gap / not duplicate:** Existing policy tools are too expensive or lobbyist-oriented; government participation portals are project-specific; land-use trackers rarely combine geography, environmental mission, action quality, and outcome tracking for small groups.

**What it builds on:** Federal Register/Regulations.gov, Mirrulations/spicy-regs, Open States/Plural for state legislation where relevant, Legistar/City Scrapers for local hearings, GIS watershed boundaries, RuleBox classification, Pol.is-style consensus, MAPLE archive/digest patterns.

**MVP scope:** One region, one anchor organization/funder, limited source list. Start with federal/state environmental dockets plus Legistar local actions; add parcel/permit feeds only when the local source is proven reliable.

**Action / impact loop:** Watch-area alert → group assigns evidence gathering → consensus-backed comments/testimony → hearing/vote/final-action tracking → campaign report showing what was filed, what changed, and where no effect is observable.

**Business / funding model:** Foundation-backed regional pilot, land-trust/water-board sponsorship, organizational subscriptions for staffed groups, subsidized volunteer access.

**Key risks:** Volunteer groups have low budgets; local environmental permit data is fragmented; alert volume can burn people out; activist echo chambers can reduce credibility.

**Mitigations:** Anchor funder first; prioritize high-stakes open windows; source-link everything; use consensus/evidence prompts; be honest about null outcomes.

**Candid verdict:** Strong civic impact and funder fit, but not a scalable consumer startup wedge. Best as a regional, grant-backed proof of impact.

---

## Portfolio logic

The recommended build order is:

1. **Start with a high-data-confidence vertical**: ScopeWatch or CodeRed, depending on whether the goal is payer clarity or local civic impact.
2. **Build DocketClock as shared infrastructure only as needed**: federal deadline reliability first.
3. **Embed Comment Workshop / Closed the Loop early** so users can see their action was received and whether institutions responded.
4. **Pilot Lot Line or Watershed Watch only with qualified data/funding**, not as a national land-use platform.

The biggest strategic mistake would be building a broad “civic engagement platform.” The portfolio should instead produce a sequence of narrow, consequential products where a user can say: “This affects me, the deadline is real, I can submit something useful, and I will hear what happened.”
