# Feasibility lens — civic-tech idea portfolio

Source reviewed: `civic-tech-prior-art-scan.html` and `civic-tech-idea-foundry-input.json`.

## Executive take

The strongest technical wedge is **federal comment-period intelligence plus guided action**, not local land-use ingestion. Mirrulations, spicy-regs, Federal Register, and Regulations.gov already give a high-leverage data substrate. Local zoning, permits, and council workflows are still attractive but carry the classic civic-tech trap: each city/source is a custom integration with permanent breakage.

The portfolio should be staged as follows:

1. Start with a narrow federal/regulatory product where deadlines and submission receipts are obtainable.
2. Add vertical relevance rules and guided comments.
3. Only then expand into local/state sources, one jurisdiction cluster at a time, with explicit per-source maintenance budgets.

## Top 7 ranked by buildability and data leverage

### 1. RuleRadar for Small Operators

**Why it ranks highest:** Best combination of reusable data and clear paying/user wedge. A federal-first MVP can lean on Federal Register freshness, Mirrulations history, spicy-regs/Parquet querying, and Regulations.gov submission. The vertical profile model also avoids the impossible “all civic issues for everyone” relevance problem.

**Feasibility notes:**
- Data availability: strong for federal dockets; mixed for state rules.
- Ingestion burden: moderate if federal-only; high if state/local included.
- Entity resolution: user profile-to-docket matching, not messy parcel/person resolution.
- Legal/API: must respect Regulations.gov submission requirements, anti-spam expectations, and receipt handling.
- COGS: manageable if classification compiles to rules/cached labels rather than per-user LLM scans.

### 2. DocketClock

**Why it ranks high:** The “deadline as a first-class object” API is the cleanest reusable infrastructure. Federal deadlines are already present in source data; the hard work is normalization, freshness, and reliable alert semantics.

**Feasibility notes:**
- Data availability: strong federally, weak for state/local.
- Ingestion burden: low-to-medium for federal; high for state registers and local hearings.
- Entity resolution: mostly docket/document IDs and canonical URLs; geo becomes hard only when local/state scope is added.
- Legal/API: API redistribution and SLA need care; agency-side dashboard implies procurement and accessibility/security burden.
- COGS: low for deadline polling/indexing; higher if bundled with clustering and verification.

### 3. Comment Workshop

**Why it ranks high:** Can be built as an action layer on top of an existing feed before solving every monitoring source. It directly addresses the “form-letter flood gets discounted” problem and produces a tangible user outcome.

**Feasibility notes:**
- Data availability: depends on DocketClock/RuleRadar-like discovery or a curated docket list.
- Ingestion burden: low if federal-only.
- Entity resolution: address/district verification is optional for federal comments but useful for trust; identity proofing can be tiered.
- Legal/API: highest care area is avoiding automated spam, deceptive comments, or mass AI-generated submissions.
- COGS: LLM interview/drafting can be expensive; control via templates, cached issue briefs, and per-comment limits.

### 4. Closed the Loop

**Why it ranks high:** Strong retention layer and can start with federal rulemakings where final rules and response-to-comments exist. It does not require owning all upstream discovery if it attaches to actions already taken.

**Feasibility notes:**
- Data availability: good for federal final rules; uneven for local minutes and dispositions.
- Ingestion burden: moderate for federal, high for local.
- Entity resolution: hard join is semantic, not identifier-based: connecting a user’s argument to agency response text.
- Legal/API: low for read-only tracking; higher if storing sensitive submitted comments and identity metadata.
- COGS: semantic diffing over long documents can get expensive; batch by docket and cache per-issue findings.

### 5. Consensus Comment

**Why it ranks here:** The Pol.is-style deliberation room is technically buildable and can attach to a federal docket or known hearing. It has less raw-data burden than land-use monitors, but it needs distribution and careful submission design.

**Feasibility notes:**
- Data availability: good if attached to known federal dockets; weaker for local agenda items.
- Ingestion burden: low for federal, medium for Legistar cities.
- Entity resolution: participant deduplication and signer verification are the core challenge.
- Legal/API: must avoid implying consensus is an official representative sample; submission packet format must be acceptable to agencies/clerks.
- COGS: Pol.is-style clustering is manageable at small group scale; LLM seeding/summarization should be cached per docket.

### 6. ScopeWatch

**Why it ranks here:** The federal CMS/HHS slice is very buildable and valuable. The full concept becomes much harder once it adds state Medicaid bulletins and scope-of-practice boards.

**Feasibility notes:**
- Data availability: strong for CMS/HHS federal rulemaking; fragmented for state boards and Medicaid notices.
- Ingestion burden: medium federal; high state-by-state.
- Entity resolution: specialty/state/payer-mix-to-rule matching is nuanced but more tractable than parcel matching.
- Legal/API: avoid legal/compliance advice claims; product must frame outputs as informational.
- COGS: domain-specific summarization needs expert QA initially.

### 7. CodeRed

**Why it makes the top 7 despite risk:** The vertical is concrete, and Legistar gives a plausible large-city starting point for ordinances/agendas. It is more buildable than parcel-level land-use products if MVP scope is “restaurant-relevant council/committee items in Legistar cities,” not permits across every locality.

**Feasibility notes:**
- Data availability: decent for Legistar jurisdictions; poor for health departments, fee schedules, PDF notices, and non-Legistar cities.
- Ingestion burden: medium for Legistar-only; high once county health/licensing sources are included.
- Entity resolution: business address to jurisdictions/districts is tractable; issue relevance is vocabulary-heavy.
- Legal/API: local testimony routing varies; no universal submission API.
- COGS: classification over agendas is manageable; per-city source maintenance is the main cost.

## Hardest technical unknown for each curated idea

| Idea | Hardest technical unknown |
|---|---|
| Lot Line | Whether enough cities expose zoning/variance/development cases with reliable geometry, hearing dates, and status to support address-radius alerts without bespoke per-city GIS work. |
| Block Whip | Whether the system can verify “affected parcel/resident inside notice radius” well enough to be trusted without creating a costly postal/identity operation. |
| Permit Pulse | Whether raw permit/license feeds can be normalized into resident-meaningful categories and action windows; most permits have no obvious comment lever. |
| ParcelWatch | Whether a reusable city onboarding playbook exists for Accela/Socrata/ArcGIS/Legistar/parcel joins, or whether every city remains a custom integration. |
| RuleRadar | Whether vertical relevance rules can achieve high precision without expert analysts reviewing every docket. False positives will kill trust. |
| ScopeWatch | Whether state-level clinical scope, Medicaid, board, and payer notices can be ingested cheaply enough after the federal CMS slice. |
| CodeRed | Whether “restaurant-relevant local action” can be identified from agenda/PDF language consistently across cities without maintaining local synonym lists forever. |
| Watershed Watch | Whether watch-area geometry can be joined to local land-use/environmental review actions across enough jurisdictions to make alerts timely and complete. |
| Statehouse RuleWatch | Whether 50 administrative registers can be scraped with reliable deadline extraction and update semantics at a maintenance cost a consumer/foundation product can bear. |
| Consensus Comment | Whether official recipients will accept a structured consensus packet as more valuable than individual comments, and how to submit it cleanly across channels. |
| Comment Workshop | Whether AI-assisted drafting can remain genuinely individualized and compliant rather than becoming exactly the mass-AI-comment pattern agencies discount. |
| Closed the Loop | Whether semantic attribution from a user’s comment to final agency response can be accurate enough to avoid misleading “your comment mattered” claims. |
| DocketClock | Whether the cross-jurisdiction model can represent deadlines/status/timezones/submission endpoints consistently once it leaves federal Regulations.gov data. |

## Recommended MVP scopes for the strongest ideas

### MVP A: RuleRadar, federal-first, one vertical

**Scope:** Pick one regulated small-operator vertical, such as independent restaurants/food service or small trucking operators. Cover only federal dockets for the first release.

**Build:**
- Poll Federal Register and Regulations.gov for newly opened/comment-closing dockets.
- Backfill and enrich using Mirrulations/spicy-regs.
- Create a small taxonomy of vertical attributes.
- Classify dockets into `relevant / maybe / irrelevant` with human review during beta.
- Send deadline alerts and plain-language “why this matters” cards.
- Offer guided comment drafting, but require user review and explicit submission.

**Do not include yet:** state rules, local ordinances, automated submission at scale, or impact attribution.

### MVP B: DocketClock, federal deadline API only

**Scope:** A reliable federal comment-period deadline feed with REST/CSV/ICS/webhook output.

**Build:**
- Canonical object: docket/document ID, title, agency, open/close dates, timezone confidence, status, source URL, submission URL, last-seen timestamp.
- Alerts: closing in 30/14/7/2 days and newly opened.
- Include explicit confidence fields for missing/ambiguous deadlines.

**Do not include yet:** state registers, local hearings, B2G clerk dashboard, resident verification, or Pol.is clustering.

### MVP C: Comment Workshop attached to curated dockets

**Scope:** A guided comment tool for a curated queue of open federal dockets.

**Build:**
- Use prewritten issue briefs and source excerpts per docket.
- Interview the user for personal facts and impacts.
- Run similarity checks against prior generated comments in your own archive.
- Produce a draft plus a checklist explaining what makes it substantive.
- Store receipt/tracking number if submitted through supported channels.

**Do not include yet:** general civic habit feed, every topic under the sun, or claims that the comment will receive legal weight.

### MVP D: Closed the Loop for comments filed through your product

**Scope:** Only track items where the user submitted through RuleRadar/Comment Workshop and where the final rule is published federally.

**Build:**
- Store the user’s main claims as structured bullets at submission time.
- Watch Federal Register final-rule publication.
- Compare final rule and response-to-comments sections to those stored bullets.
- Return conservative labels: `addressed`, `partially addressed`, `not found`, `still pending`.

**Do not include yet:** local vote attribution, state regs, or strong causal language like “your comment caused this.”

## Ideas to downgrade because of per-city/per-source maintenance traps

### Downgrade hard: Statehouse RuleWatch

A national state-rulemaking layer is valuable but operationally brutal. Open States explicitly does not solve regulations. Each administrative register has different formats, deadline conventions, update cadence, PDFs/RSS/HTML, and submission channels. This is closer to building “Open States for rulemaking” than a normal product feature.

**Safer path:** start with 2-3 states and one topic domain; treat the scraper set as the product, not a side quest.

### Downgrade hard: ParcelWatch

The idea correctly identifies whitespace, but it is almost entirely in the hardest ingestion category from the prior-art scan: Accela/Socrata/ArcGIS/parcel GIS plus Legistar. Parcel geometry, zoning case IDs, hearing status, parcel centroids, and permit semantics vary by city.

**Safer path:** one city, one or two well-documented datasets, no promise of national API coverage.

### Downgrade hard: Permit Pulse

Raw permit feeds are plentiful but actionability is sparse. The product risks sending a digest of noisy by-right permits where residents have no lever. The “open action window” is the hard part, not the permit feed.

**Safer path:** start with a digest for a single city/neighborhood and explicitly label most items as informational, not actionable.

### Downgrade hard: Lot Line

The address-radius concept is compelling, but statutory notice radius is not the same as available digital data. The MVP depends on city-specific zoning case geometry, reliable hearing dates, and legal-radius rules. Missing geometry or stale case status breaks the core promise.

**Safer path:** launch only where the planning dataset is known clean; accept manual city qualification.

### Downgrade hard: Watershed Watch

This compounds every hard source: federal environmental dockets, state legislation, local land-use, permits, environmental review, and watershed geometry. It is strategically rich but too broad for an MVP.

**Safer path:** begin as a federal/state environmental docket watcher for one watershed group, then add local land-use only after proving demand.

### Downgrade moderate: Block Whip

Block Whip should not be built before Lot Line/ParcelWatch data exists. Its organizing flow is feasible, but its legitimacy depends on accurate affected-parcel lists and verification.

**Safer path:** use manually created campaigns for known cases first; automate parcel-radius discovery later.

### Downgrade moderate: CodeRed

CodeRed is top-7 only with a Legistar-only scope. The full version crosses council agendas, health departments, license boards, fee schedules, and local PDFs. That is a maintenance trap if sold city-by-city at low ARPU.

**Safer path:** Legistar cities, one business type, no health-board long tail until there is revenue.

## Shadow-path checks to require before implementation

For each product, the implementer should design these paths up front:

- **Happy path:** source has a fresh item, deadline, submission endpoint, and user profile match.
- **Nil path:** source has no deadline, no geometry, no endpoint, or no jurisdiction match.
- **Empty path:** user has zero matching items this week; product must say “nothing needs you” rather than invent relevance.
- **Error path:** upstream API fails, rate limits, silently changes schema, or publishes a corrected/withdrawn item.

The current ideas usually describe the happy path. The MVP specs above should make nil/empty/error states explicit, because civic alert products lose trust faster from one false urgent alert than from ten quiet weeks.

## Bottom line recommendation

Build the first company/product around **federal deadline discovery + vertical relevance + high-quality guided comments**, using Mirrulations/spicy-regs/Federal Register/Regulations.gov as leverage. Treat local land-use and state-rulemaking as later, funded expansions with explicit source-maintenance budgets, not as day-one proof points.
