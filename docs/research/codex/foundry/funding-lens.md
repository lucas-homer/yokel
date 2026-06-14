# Funding / Business-Model Lens — Civic-Tech Idea Foundry

## Method

Scored each curated idea on four sustainability lenses, 1–5 each:

- **Grant/foundation lens:** mission fit, measurable public benefit, low trust conflict.
- **B2G SaaS lens:** clear government buyer, budget line, workflow pain, procurement feasibility.
- **Prosumer/SMB subscription lens:** acute individual/business pain, willingness to pay, low-touch distribution.
- **Open-data infra lens:** reusable data/API moat, developer/org demand, open-core compatibility.

Overall sustainability favors ideas with a payer who benefits *without* distorting public trust. Pure consumer civic subscriptions scored lower unless the user faces material financial/compliance risk.

## Top 7 ranked by sustainability

| Rank | Idea | Ensemble read | Likely payer + pricing/funding model | Biggest go-to-market obstacle | Best posture |
|---:|---|---|---|---|---|
| 1 | **DocketClock — open Comment-Period Deadline API** | Best blend of infra moat + B2G cross-subsidy. Agencies need verified, deduplicated input; builders need deadline feeds. | **Primary:** city/county clerks, planning departments, state/federal public-affairs offices. **Secondary:** civic orgs/devs using API. Free public schema/API tier; paid webhooks/SLA/volume at ~$99–$999/mo for orgs; clerk dashboard ~$10k–$75k/yr by jurisdiction size. | Procurement and trust: governments must believe the platform is neutral, not a mobilization weapon. Needs first 2–3 agency pilots. | **Open-core + B2G SaaS.** Keep deadline data/open schema public; sell workflow, verification, exports, SLA. |
| 2 | **ParcelWatch — open zoning/land-use change feed keyed to address** | Strongest infrastructure business in land use. Many downstream payers rebuild this; open-core reduces trust concerns. | **Primary:** local-news orgs, neighborhood associations, advocacy groups, proptech/real-estate apps, legal/planning firms. Per-city data/API subscription: ~$250–$2,000/mo; enterprise/proptech contracts $25k–$150k/yr; open one reference city/schema. | Data operations: Accela/Socrata/ArcGIS/Legistar variability and permanent scraper maintenance. Coverage claims must stay narrow and credible. | **Open-core / B2B2C infra.** Consumer apps can ride on top, but sell the normalized feed first. |
| 3 | **ScopeWatch — regulatory radar for independent clinicians** | Highest prosumer/SMB willingness to pay: rules affect revenue, scope, compliance risk. Less dependent on civic altruism. | **Primary:** solo/small practices, practice managers, specialty associations. Subscription $29–$99/provider/mo or $199–$499/practice/mo; association bundles $10k–$100k/yr. | Distribution into fragmented clinician practices; must avoid being perceived as legal advice. Needs narrow specialty/state wedge. | **Prosumer/SMB subscription.** Add association channel; not consumer-first. |
| 4 | **CodeRed — ordinance/licensing radar for restaurants/food-service** | Acute local regulatory pain, clear SMB buyer, chamber/association channels. Local data messy but Legistar unlock helps. | **Primary:** independent restaurants/food trucks; local restaurant associations/chambers. $19–$79/location/mo; association/chamber bundle $5k–$50k/yr per city; sponsored free tier possible. | Low-margin SMB churn and hard city-by-city onboarding; must prove alerts save money/time quickly. | **B2B2C via associations/chambers, with SMB subscription.** |
| 5 | **Watershed Watch — permit radar for environmental groups** | Excellent foundation fit and mission trust. Revenue likely program/grant + group SaaS, not pure subscription scale. | **Primary:** watershed groups, land trusts, regional foundations, water boards. Foundation grants $100k–$500k for regional pilots; org subscriptions $50–$300/mo; regional dashboard $10k–$75k/yr. | Volunteer groups have low budgets; success depends on anchor funder/region and demonstrable impact loop. | **Foundation-backed B2B2C.** Sell/serve groups, not individual residents. |
| 6 | **RuleRadar for Small Operators** | Good SMB pain across regulated verticals, but must verticalize hard. Horizontal version is too vague to sell. | **Primary:** small operators in one vertical first; trade associations as channel. $19–$99/mo/operator; association bundle $10k–$100k/yr; premium drafting/compliance archive. | Picking a wedge with both rule volume and reachable distribution; avoiding generic “reg alerts” competition. | **Prosumer/SMB subscription, association-led.** |
| 7 | **Statehouse RuleWatch** | Big public-interest gap and defensible corpus, but 50-state scraping is expensive and direct consumer payment is weak. | **Primary:** advocacy orgs, local nonprofits, foundations, possibly newsrooms. Open dataset grant $250k–$1M; paid alerts/API $100–$1,000/mo/org; custom state/topic monitoring $10k–$75k/yr. | Building/maintaining 50 idiosyncratic state-register pipelines before revenue; must start with a topic/state cluster. | **Foundation-backed open-data infra / open-core.** |

## Ensemble scores for all 13 curated ideas

| Idea | Grant / foundation | B2G SaaS | Prosumer / SMB | Open-data infra | Sustainability notes |
|---|---:|---:|---:|---:|---|
| DocketClock | 5 | 5 | 2 | 5 | Best two-sided model; public/open layer protects trust while B2G funds operations. |
| ParcelWatch | 4 | 2 | 3 | 5 | Strong reusable data product; sell to orgs/apps rather than homeowners first. |
| ScopeWatch | 2 | 1 | 5 | 3 | Strong payer pain; civic upside secondary to compliance/revenue protection. |
| CodeRed | 3 | 2 | 4 | 3 | Good local SMB wedge; channel through chambers/associations. |
| Watershed Watch | 5 | 3 | 2 | 4 | Foundation/regional-board fit; low direct ARPU. |
| RuleRadar for Small Operators | 3 | 1 | 4 | 3 | Sustainable only if narrowed by vertical and sold through trusted associations. |
| Statehouse RuleWatch | 5 | 2 | 1 | 4 | High public value, weak consumer payment; grant/open-data path. |
| Permit Pulse | 3 | 1 | 2 | 3 | Useful, but neighborhood-association budgets are thin; better as ParcelWatch/Lot Line feature. |
| Lot Line | 3 | 1 | 2 | 2 | Consumer appeal, but episodic willingness to pay and NIMBY/trust risk. Could be freemium on ParcelWatch. |
| Consensus Comment | 4 | 3 | 1 | 2 | B2G dashboard plausible, but agency-buyer model may chill activist trust. Better as module. |
| Closed the Loop | 4 | 2 | 1 | 3 | Valuable retention/impact primitive, weak standalone payer. Bundle into action products. |
| Block Whip | 3 | 1 | 1 | 1 | Powerful organizing, but episodic, trust-sensitive, and easily framed as NIMBY mobilization. |
| Comment Workshop | 3 | 1 | 1 | 1 | Public benefit high; consumer subscription weak and AI-comment trust risk high. Feature, not company. |

## Revenue/trust takeaways

1. **Infrastructure beats pure consumer civic engagement.** Prior art shows volunteer action tools often go dormant; durable models look like mySociety/SocietyWorks or Open States/Plural: open public-good layer plus paid institutional workflow/API.
2. **SMB subscriptions work only where regulation hits the wallet.** Clinicians, restaurants, and tightly defined operators can pay because missed rules create revenue/compliance pain. Ordinary residents usually will not pay enough to sustain coverage.
3. **B2G can fund access, but neutrality must be explicit.** If governments pay, open schemas, auditable ranking, clear privacy rules, and nonexclusive public feeds are essential to avoid “the clerk controls who gets heard.”
4. **Foundation money fits corpus creation and underserved groups.** Statehouse RuleWatch and Watershed Watch are credible grant-funded pilots, especially with measurable outputs: comments filed, hearings attended, outcomes tracked.
5. **Consumer-first is riskiest for land-use organizing.** Lot Line/Block Whip have strong user pull, but monetization can bias toward affluent homeowners and anti-development mobilization. Best treated as free/low-cost applications atop a neutral open data layer.
