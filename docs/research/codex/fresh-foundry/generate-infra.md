# Fresh civic-tech infrastructure ideas

Lens: **open data, protocols, and picks-and-shovels infrastructure** for products that already have demand: associations, civic orgs, newsrooms, vertical rule-radar tools, and resident-action apps. These are not generic “civic data platforms”; each exists to make downstream tools monitor, route action, or prove impact better.

## 1. CommentWindow Registry — SLA-backed deadline objects for public participation

### Buyer / user
- **Primary buyer:** vertical civic/rule-intelligence products such as ScopeWatch, Watershed Watch, CodeRed-style SMB alerting tools, associations, and issue advocacy platforms.
- **Daily users:** product engineers, civic-data teams, newsroom data desks, and policy analysts who need trustworthy “what is open and closing soon?” feeds.

### Data, protocols, and repos to build on
- **Federal Register API** for official notices and comment periods.
- **Regulations.gov v4 API** for docket/document/comment endpoints and fresh status checks.
- **Mirrulations** (`mirrulations/mirrulations`, `mirrulations-search`) for historical backfill and schema hints.
- **Open Civic Data concepts** for stable jurisdiction/source identifiers, but extend with a first-class `CommentWindow` object.
- Outputs: REST, CSV, bulk Parquet, webhook, RSS/Atom, and **ICS calendar feeds**.

### Action loop enabled
Downstream tool subscribes to “closing in 14/7/2 days” events → alerts affected users → user submits comment/testimony through that tool → registry later emits “closed / extended / reopened / withdrawn / final-rule-linked” updates so the tool can follow up.

### Why not duplicate
- Regulations.gov and Federal Register are portals/APIs, not a normalized, confidence-scored deadline product.
- Mirrulations is a mirror, not an alerting SLA or canonical deadline API.
- Open States/OCD do not model public-comment windows as first-class objects.

### MVP
- Federal-only: Regulations.gov + Federal Register.
- Canonical fields: source IDs, title, agency, open/close datetime, timezone, submission URL, source provenance, status, confidence, last seen, superseding/extension links.
- 20 design partners get API keys, webhooks, and source-provenance dashboards.
- Explicitly exclude state/local scraping until one vertical customer funds a source cluster.

### Funding path
Free public bulk data with attribution; paid API volume, webhooks, historical snapshots, uptime SLA, customer-specific watchlists, and “deadline verification” support for associations/newsrooms.

### Fatal risk
A single wrong high-stakes deadline destroys trust. The product only works if provenance, confidence, diffing, and human escalation are treated as core features rather than documentation.

---

## 2. Civic RouteMap — address-to-action endpoint and eligibility resolver

### Buyer / user
- **Primary buyer:** action tools, associations, local-news civic desks, legal-aid/civic-help products, and vertical products that need to route users to the right official, docket, hearing, or clerk.
- **Daily users:** engineers who currently rebuild brittle address → district → official/contact/submission routing for every app.

### Data, protocols, and repos to build on
- **Census TIGER/Line**, Census Geocoder, and local GIS boundaries.
- **Open States / Plural API** and OCD IDs for jurisdictions, people, organizations, bills, and events.
- **Legistar OData** for city/county bodies, agenda items, files, sponsors, votes, and actions.
- **mySociety MapIt / WriteToThem pattern** as the reference UX abstraction.
- Optional local layers: ArcGIS FeatureServer, Socrata, Accela, parcel/notice-radius data where qualified.
- Protocol: embeddable `GET /route?address=&issue_type=&source_id=` returning eligible bodies, officials, submission endpoints, verification requirements, and confidence.

### Action loop enabled
A downstream tool asks “who can this person validly contact or comment to?” → RouteMap returns the correct docket/hearing/official endpoints and verification tier → user submits through the tool → RouteMap stores only a non-sensitive routing receipt so later outcome updates can be matched without exposing the address.

### Why not duplicate
- MapIt is strong prior art but not US-wide action-endpoint infrastructure.
- Open States answers representation, not local hearing/docket eligibility or submission endpoints.
- Legistar exposes data per client, but not resident address routing, notice-radius eligibility, or cross-city normalized action metadata.

### MVP
- Two states plus five Legistar cities with good boundary data.
- Support three action types only: contact representative, testify/comment on Legistar agenda item, and comment on federal docket.
- Return confidence and “do not know” states rather than guessing.
- No national permit/zoning promise in v1.

### Funding path
Developer API subscriptions for civic products; association bundles; sponsored “city packs” funded by local newsrooms, foundations, or chambers; enterprise support for organizations that need routing audits.

### Fatal risk
Boundary/contact data rots constantly, especially locally. If updates cannot be automated and audited cheaply, the service becomes a manual civic address book with SaaS margins but data-broker maintenance costs.

---

## 3. Comment Receipt & Outcome Graph — impact tracking API for civic-action tools

### Buyer / user
- **Primary buyer:** civic-action platforms, associations, public-interest law/policy shops, foundations funding participation campaigns, and government engagement teams that want cleaner feedback loops.
- **Daily users:** campaign/product teams who need to tell participants “received, considered, changed, rejected, or still pending” without overstating causality.

### Data, protocols, and repos to build on
- **Regulations.gov** comment/document APIs and tracking numbers where available.
- **Federal Register** final rules and agency response-to-comments text.
- **Legistar OData** actions, votes, minutes, attachments, and file status.
- **MAPLE** archive/notification concepts.
- **Decidim Accountability** pattern, but not AGPL code.
- **Pol.is-style clustering concepts** for grouping comment themes, not mass-paraphrasing.
- Protocol: append-only `ActionReceipt`, `Claim`, `OutcomeEvent`, and `ResponseMatch` objects with source links and confidence labels.

### Action loop enabled
Tool files or records a user action → receives a portable receipt ID → graph watches the official record → clusters user claims against agency/council responses, amendments, votes, continuances, or final rules → downstream tool sends honest follow-up: “your comment is in the record,” “this theme was addressed,” “the item passed unchanged,” etc.

### Why not duplicate
- Resistbot/5 Calls optimize action volume, not durable official-record outcome tracking.
- Regulations.gov stores comments but does not provide participant-centered impact receipts.
- Decidim has accountability inside government-run deployments; it is not a cross-source API for independent tools.

### MVP
- Federal Regulations.gov dockets plus one Legistar city.
- Receipt import API for downstream tools; manual receipt upload fallback.
- Outcome labels limited to conservative states: received, entered into record, final action published, theme addressed, theme not found, vote/result changed, pending, unknown.
- Human-reviewed matching for first 50 campaigns.

### Funding path
Usage-based API for action platforms and associations; foundation grants for public-interest pilots; paid evaluation reports for funders who need participation-quality and outcome metrics.

### Fatal risk
Attribution overclaim. If the product implies “your comment caused this change” when evidence only supports “this theme appeared in the response,” it will lose credibility with agencies, funders, and users.

---

## 4. Civic SourceOps — monitoring, CI, and incident response for civic-data pipelines

### Buyer / user
- **Primary buyer:** teams running civic tools on fragile public data: brigades, local-news data desks, associations, small civic startups, and foundations supporting shared civic infrastructure.
- **Daily users:** maintainers of City Scrapers-style spiders, Legistar/Socrata/ArcGIS integrations, Open States-derived workflows, and docket monitors.

### Data, protocols, and repos to build on
- **City Scrapers** patterns: one source adapter, normalized events, diffing, cancelled/vanished detection, Sentry-style alerts.
- **Open States scrapers** and OCD schema validation ideas.
- **Legistar OData**, Socrata APIs, ArcGIS FeatureServer, Federal Register, Regulations.gov.
- GitHub Actions, issue templates, JSON Schema, OpenTelemetry-style health events.
- Protocol: each source adapter emits `SourceHealth`, `SchemaDiff`, `FreshnessLag`, `RecordChurn`, and `ConfidenceRegression` events.

### Action loop enabled
A downstream tool depends on a source → SourceOps detects stale data, schema drift, missing deadlines, unusual record churn, or broken submission URLs → maintainers get a reproducible failing fixture and severity → tool can suppress/label affected alerts → after repair, users receive corrected or delayed-action notices instead of silent false negatives.

### Why not duplicate
- Sentry/Datadog monitor software errors, not civic-data correctness.
- City Scrapers has patterns for scraping and diffing, but not a reusable source-health product across civic stacks.
- Open States maintains its own scrapers; most smaller tools cannot afford that operational discipline.

### MVP
- Hosted checks for 30 high-value sources: Federal Register, Regulations.gov, 10 Legistar clients, 10 Socrata/ArcGIS feeds, and selected City Scrapers-style sources.
- Drop-in SDK for adapters plus GitHub Action that validates fixtures and emits health events.
- Public status pages per source; private alerts for paying teams.
- No promise to fix every scraper; start with detection, fixtures, and escalation.

### Funding path
Paid monitoring seats for civic startups/associations/newsrooms; foundation-funded public status layer; maintenance retainers for high-value source packs; “source certification” for tools that need funder or customer trust.

### Fatal risk
Maintainers may not pay for reliability until after failures hurt them. The wedge needs customers with real liability or revenue exposure, such as associations, rule-radar products, or newsrooms publishing deadline alerts.
