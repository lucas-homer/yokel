# DocketClock — Architecture

> **Canonical, agent-readable.** Generated from `arch-foundry-result.json` by `tools/gen_arch_md.py`.
> Do not hand-edit; edit the source or regenerate. Pretty version:
> `docs/research/docketclock-watershed-architecture.html`.
>
> Provenance: 13-agent foundry — 3 competing architects (pragmatist / trust-maximalist /
> substrate) → adversarial critique → Opus synthesis. Proposal soundness scores: pragmatist 7/10, trust 7.5/10, substrate 6.5/10.

## DocketClock: The Reconciled Federal Comment-Deadline Substrate

A federal-only, observation-log-backed reconciliation engine that exposes every public-comment deadline as a stable, provenance-bearing object with an honest confidence/conflict flag — sold as a B2B picks-and-shovels API/webhook to regulatory-affairs and law-firm KM desks, and architected so verticals like Watershed Watch rent it via a tag/enrichment contract without forking the core.

## Architecture thesis

The unit of trust is a public-comment deadline whose net-new value is reconciliation + confidence + provenance, not discovery. The decisive design treats the append-only Observation log as the spine (trust-maximalist) and the ParticipationWindow as a derived, versioned projection — never a silently-mutated truth field — but it ruthlessly defers everything that does not move the first paying B2B contract (pragmatist). The substrate is made rentable by stable OCD-IDs plus a tag/enrichment contract that lets verticals scope without touching core reconciliation (substrate stance). Three critique-killing decisions are non-negotiable from day one: (1) conflict detection compares both source dates normalized to America/New_York before flagging — the known FR-2018-27875 one-calendar-day gap is a timezone artifact, NOT a conflict, so a naive >24h-in-UTC threshold would flood the CONFLICTING bucket and destroy the product's only differentiator; (2) when confidence drops to CONFLICTING/STALE we SUPPRESS the closing-soon alert AND simultaneously FIRE a conflict notification with both source rows attached — silence is a liability for deadline-liable buyers, so suppression is never silence; (3) a Week-1 frDocNum-join-hit-rate measurement is a hard go/no-go gate with a named contingency (pivot to Regs.gov-primary with docket_id/RIN fallback) before any pipeline code is written. The MVP is the reconciliation engine + the public contract; the UI is a thin internal review console, nothing more. Federal-only is a literal 'thou shalt not' until a paying customer funds a specific jurisdiction tranche.

## What we kept / changed / rejected from Codex's plan

The substrate was reconciled against a competing "Codex" DocketClock architecture. Verdict:
kept 9, changed 7, rejected 5.

### Kept
- **ParticipationWindow as the canonical unit of trust (name + concept)** — The deadline-as-first-class-object-with-provenance/confidence/change-history IS the product. Correct and retained verbatim in name.
- **Immutable event/observation log with payload hash, fetched_at, source URL, parser version, extracted candidates** — Exactly right — the audit spine that makes deadline changes legally defensible. We strengthen it (DB-trigger-enforced append-only) rather than weaken it.
- **Trust model: unknown/stale/conflicting first-class; suppress/downgrade alerts when confidence drops; a bad deadline is worse than no alert** — This is the differentiator against every single-source tracker. Non-negotiable.
- **RuleBox pattern: deterministic rules run cheap forever, LLM only adjudicates ambiguous extension chains** — Correct cost structure; applied to chain classification + the BLM-style keyword deny-list.
- **Confidence engine producing HIGH/MEDIUM/LOW/STALE/CONFLICTING from source agreement, parse certainty, freshness, status semantics** — Right primitive; we add UNKNOWN and a structured explanation object and pin the Eastern-date comparison.
- **Human review console scoped ONLY to uncertain/high-impact records** — Correct scope; we make it internal-operator-only and resolve via human_review observations to preserve the audit chain.
- **Registry + API emitting webhooks/RSS/ICS/CSV/bulk; OCD Events for downstream joinability** — Correct delivery surface and the substrate joinability promise (OCD-IDs as the cross-system key for Watershed Watch).
- **Federal-first expansion rule: no state/local until a funded source cluster + paying customer** — State/local has no normalized cross-state rulemaking API (Legistar has no comment-deadline field). Enforced as a literal thou-shalt-not in the adapter registry.
- **Suggested stack: TypeScript workers/API, Postgres (JSONB raw + versions), Zod/JSON Schema + public OpenAPI, Postgres FTS first** — All correct; we firm 'FTS first' into a hard deferral of OpenSearch and concretize Fastify.

### Changed
- **Canonical window's relationship to the event log**: _Mutable canonical window is primary; event log is audit trail_ → **Observation log is PRIMARY/append-only; ParticipationWindow is a derived, versioned projection re-computed on every reconcile** — Mutating the window silently discards prior deadline values — exactly what 'do not publish fake certainty' forbids. Inversion enforces the trust invariant structurally (trust-maximalist).
- **Normalizer**: _Monolithic entity-resolution graph tying notices/dockets/agencies/CFR-parts/comment-URLs/corrections/reopenings into one canonical graph_ → **Three smaller pieces: observation-insert notice-type flags + Reconciliation Engine (deadline resolution) + Enrichment hooks (CFR/agency/HUC tags)** — The monolith is premature abstraction that blocks vertical extension. Decomposition is what makes the substrate rentable without forking core (substrate).
- **Queue/scheduler**: _Temporal / BullMQ / Cloud Tasks_ → **Postgres outbox + cron at MVP** — Both are weeks of ops for zero buyer-visible feature at ~1,000 windows / ~100 subscriptions. Postgres is the queue until durable workflows or 10k+ subscriptions justify BullMQ/Temporal (pragmatist).
- **Search**: _Postgres FTS first then OpenSearch_ → **Postgres FTS, OpenSearch HARD-deferred until a measured bottleneck** — ~1,000 open windows is trivially within FTS; OpenSearch is real ops burden with no MVP payoff.
- **Timezone handling**: _Single operative close (implicitly UTC-normalized)_ → **resolved_close_utc (nullable) + separate verbatim resolved_close_display; conflict comparison normalized to America/New_York** — The NPS Alaska '11:59 ET / 7:59 AK' case is legally distinct from any single UTC stamp; the FR-2018-27875 1-UTC-day gap is an Eastern-same-date artifact, NOT a conflict. Eastern comparison prevents flooding CONFLICTING with false positives — the single fatal-flaw fix.
- **Conflict handling**: _Internal review trigger / one silent truth field_ → **ConflictRecord as a first-class PUBLISHED proof feed (GET /conflicts, Atom) with conflict-dual-fire on alerts** — Publishing conflicts is the credibility moat no competitor offers; dual-fire ensures suppression is never silence for deadline-liable buyers.
- **Admin + design-partner watchlist UI bundled with the registry**: _One small admin + design-partner UI component_ → **Internal-operator review console SEPARATE from the public registry/API; design partners get API+webhooks only** — Mixing creates a surface where an admin action mutates canonical data and lets partners approve resolutions — a trust liability.

### Rejected
- **Naming downstream consumer personas (pharmacy desks, childcare associations, journalists, advocacy orgs) inside the substrate architecture** — Bleeds vertical concerns into core and pressures pharmacy/childcare-specific fields onto the canonical object. The funded B2B buyers are reg-affairs + law-firm KM (liability-bearing); consumer/civic personas are a later distribution layer handled via the tag/enrichment contract, not core fields.
- **Mirrulations as a freshness/'expensive-part-done' source** — Product context explicitly flags this as wrong — Mirrulations always lags live Regs.gov; it is an offline eval/seed asset only, never a live pipeline.
- **Multi-API-key pool to beat the Regs.gov 1,000 req/hr limit** — Splitting one use-case across keys is rate-limit circumvention that risks ToS revocation — existential. Correct path is a GSA rate-increase application (granted case-by-case) plus differential polling within budget.
- **Shipping MCP in the core MVP sprint** — The three named design partners are not AI-agent buyers; MCP is operational surface area before its buyer segment is validated. Contract pre-shaped, build deferred to a committed AI-agent buyer.
- **Email digest delivery as a built v1 feature** — Webhook -> Zapier/Make handles email free; building templates/unsubscribe/SPF/DKIM/bounce is a week for nothing a design partner needs.

## Canonical object — ParticipationWindow (derived projection over an append-only Observation log)

ParticipationWindow is KEPT from Codex but DEMOTED from mutable source-of-truth to a derived view re-computed from the Observation log on every reconcile (trust-maximalist inversion). A single FR notice can extend multiple dockets with different new deadlines (EPA two-actions 2025-02910), so observations relate to windows MANY-TO-MANY via an observation_targets join table — one extension observation writes updates to N windows. resolved_close_utc separated from raw per-source values (substrate) and from resolved_close_display (timezone preservation) is the core data-modeling answer to three documented edge cases at once.

| Field | Meaning |
| --- | --- |
| ocd_id (PK) | Stable Open Civic Data ID: ocd-participation-window/federal/{frDocNum} (or regs:{regsObjectId} when FR doc number is absent). Generated once at first observation, never changes across extensions. This is the join key verticals (Watershed Watch) and AI agents use across systems — NOT an internal Postgres UUID. |
| fr_document_number / regs_document_id / regs_object_id / docket_id / rin | All identifiers carried explicitly. frDocNum is the primary FR<->Regs.gov reconciliation key; docket_id array overlap and RIN are fallbacks per ACUS finding that agencies omit/misconfigure identifiers. regs_object_id (not documentId) is the comment-association key. |
| window_type | enum: comment \| hearing \| information_collection \| eis_draft \| eis_final \| other. Typed so EIS-clock verticals can layer on without core changes. |
| resolved_close_utc (nullable) | The OPERATIVE deadline after reconciling the extension/correction/reopening chain — what consumers display. NULL is allowed and honest when confidence is CONFLICTING/UNKNOWN; never coerce a guess. |
| resolved_close_display | Verbatim legal-language string preserving timezone/channel semantics, e.g. '11:59 p.m. ET / 7:59 p.m. Alaska time' (NPS Alaska case). Separate from resolved_close_utc so collapsing to UTC never silently drops submission-channel meaning. |
| raw_fr_close_date / raw_regs_close_datetime | The unreconciled per-source parsed values, retained for transparency. FR comments_close_on is date-only; Regs.gov commentEndDate is ISO-8601 with offset. Both kept so the API can show the delta the engine reconciled. |
| confidence | enum: high \| medium \| low \| conflicting \| stale \| unknown. First-class, always present in every response, never suppressed. |
| conflict_flags | typed array: fr_regs_date_mismatch \| tz_normalization_only \| extension_chain_unresolved \| correction_pending \| withdrawn_vs_open \| null_end_date_open_status \| late_comment_ambiguous \| multi_target_notice \| keyword_false_positive. Array (not boolean) so consumers handle each failure mode distinctly. |
| status | enum: open \| closed \| extended \| reopened \| withdrawn \| finalized \| unknown. |
| submission_url / govinfo_url | submission_url to file; govinfo_url is the legal-reliance backstop link (govinfo.gov/content/pkg/FR-{date}/html/{frDocNum}.htm) embedded in EVERY response + the disclaimer anchor. |
| tags | array populated by enrichment hooks (agency slug, CFR parts, geo_huc_8/12, keyword_topics), OPAQUE to core reconciliation. This is the extensibility seam: Watershed Watch writes huc_8: tags; DocketClock core never knows what a HUC is. |
| provenance / current_observation_ids / change_history / version | provenance summarizes which observations agreed/conflicted; current_observation_ids points into the immutable log; change_history is an append-only array of prior resolved_close_utc values with observation refs; version is a monotonic integer. |

## Pipeline

1. **0. Validate (pre-architecture gate)** — Measure frDocNum join hit-rate and empirical FR-vs-Regs.gov conflict rate against the live ~1,000 open windows + Mirrulations history BEFORE writing pipeline code.
2. **1. Discover** — Poll FR API (keyless) every 15 min for documents with comments_close_on in the future OR action/title containing extension/correction/reopening/withdrawal keywords; poll Regs.gov v4 filter[withinCommentPeriod]=true with a lastModifiedDate change-cursor.
3. **2. Observe (immutable log)** — SHA-256 hash every raw payload; append one Observation row (DB trigger rejects UPDATE/DELETE); skip if hash matches latest for that (source,document_id). Parse is_extension/is_correction/is_withdrawal flags and verbatim raw_dates_text at insert.
4. **3. Reconcile (confidence engine)** — On new observations, load the full chain, run the deterministic JSON rulebook to produce resolved_close_utc, confidence, conflict_flags, status; write/append a ParticipationWindow version.
5. **4. Enrich (tag population)** — After reconciliation, pluggable enrichment workers write tags within a tenant's allowed_tag_namespaces WITHOUT touching the reconciled deadline.
6. **5. Publish + gate** — Expose windows via REST/RSS/ICS/CSV/webhooks; gate alert eligibility HERE, not in delivery.
7. **6. Verify + follow-up** — After resolved_close_utc passes, re-poll 7 days for late withdrawal/correction/extension; write an AccuracyRecord (published vs actual close); emit window.finalized when a linked final rule appears.

- _0. Validate (pre-architecture gate)_: Hard go/no-go: if frDocNum joins <60% of records, the product pivots to Regs.gov-primary with docket_id-array-overlap + RIN fallback as the join, and FR-only records carry confidence=medium with conflict_reason='no_cross_source_join'. The conflict-rate number decides whether the 'conflicts this week' feed is a marquee feature or a quiet field. One DuckDB query over spicy-regs/Mirrulations Parquet produces a defensible estimate in hours.
- _1. Discover_: Regs.gov differential polling: fetch the withinCommentPeriod list (cheap), then fetch document detail only where lastModifiedDate advanced. CRITICAL: lastModifiedDate filter is Eastern while response timestamps are UTC — apply a 6-hour cursor-overlap and dedupe by documentId to avoid the documented silent-miss trap. Stay inside 1,000 req/hr on ONE key; apply to GSA for a rate increase in Week 1 (NOT multi-key, which is a ToS-revocation risk).
- _2. Observe (immutable log)_: Append-only is enforced at the DB level, not by convention — the audit trail IS the trust primitive. Notice-type flags are set with regex BUT routed through a deny-list (RuleBox) to suppress the BLM 'land-withdrawal extension' keyword false-positive (2023-27468); genuinely ambiguous titles escalate to a single Haiku call, not the hot path.
- _3. Reconcile (confidence engine)_: THE fix: compare FR comments_close_on and Regs.gov commentEndDate by normalizing BOTH to America/New_York calendar date. Same Eastern date => agree (flag tz_normalization_only if UTC strings differ). Differ by >0 Eastern days OR an unresolved extension/correction in the chain => CONFLICTING. commentEndDate null but openForComment=true => LOW. withdrawn vs open => CONFLICTING. Non-monotonic chains (a correction moving a date EARLIER) force re-evaluation, not blind 'latest wins'. LLM adjudicates only chain classification when the rulebook returns AMBIGUOUS. Regression-test every rulebook change against spicy-regs historical chains in CI.
- _4. Enrich (tag population)_: Built-in: OCD agency-slug normalization, CFR-part extraction. Vertical (separate deployment calling the enrichment API): Watershed Watch resolves USGS WBD HUC-8/12 codes and writes huc_8:/huc_12: tags. This is the layer boundary enforced by data contract — the substrate never imports WBD. Built-in CFR/agency enrichment ships BEFORE design-partner onboarding so tag-based filtering isn't empty on day one.
- _5. Publish + gate_: Only HIGH/MEDIUM windows trigger closing-soon push. For CONFLICTING/STALE: SUPPRESS closing-soon AND simultaneously FIRE a 'conflict'/'needs-verification' notification carrying both source observations + govinfo_url — suppression is never silence. Document-level subscriptions: a docket_id watch fans out to ALL documents in that docket. Every response carries the disclaimer envelope and a request_id.
- _6. Verify + follow-up_: AccuracyRecord feeds a track-record metric used in sales ('% of HIGH-confidence deadlines correct, trailing 90d'), but the public-facing accuracy dashboard is design-partner-gated during calibration and only goes fully public above a credibility threshold (e.g. 95% HIGH). Every was_correct=false becomes a labeled regression test.

## Components

| Component | Responsibility | Tech |
| --- | --- | --- |
| Source Adapters | Thin stateless fetchers, one per source, returning raw payload + metadata only (no parsing/normalization downstream). FR API (keyless), Regs.gov v4 (keyed, differential lastModifiedDate cursor), GovInfo (URL resolver only — no PDF ingestion), Mirrulations/spicy-regs (OFFLINE eval/seed only, never a live freshness source). | TypeScript + Zod raw-payload validation at the boundary; node-postgres; cursor state in Postgres. |
| Immutable Observation Log | Append-only store of every raw observation with payload_hash, fetched_at, parser_version, verbatim raw_dates_text, notice-type flags. The audit spine — full replay can re-derive all windows and conflicts from observations alone. | Postgres, table-level BEFORE UPDATE/DELETE trigger raising exception; JSONB raw payload; partition by fetched_at month; index (fr_document_number, source, fetched_at DESC) and (regs_object_id, source, fetched_at DESC). |
| Reconciliation / Confidence Engine | Deterministic versioned JSON rulebook (RuleBox) reading the observation chain to produce resolved_close_utc, confidence, conflict_flags, status. Eastern-date comparison; non-monotonic chain handling; Haiku only for AMBIGUOUS chain classification. | TypeScript; JSON rulebook + Zod rule schema; DuckDB-over-spicy-regs regression suite in CI; Anthropic Haiku fallback (<5% of records, ~50 calls/day at launch). |
| Enrichment API + Hook Registry | Post-reconcile hooks write tags within allowed_tag_namespaces; built-in (agency slug, CFR part) and tenant/vertical (HUC, keyword topics). Core never reads tags for reconciliation. No deadline overrides via this API — corrections route through the review console as a human_review observation to preserve the audit chain. | Fastify sub-router; tenant-API-key auth; namespace middleware; Postgres JSONB tags + GIN index. |
| Registry + Delivery API | Public REST (OpenAPI 3.1): GET /windows (filter agency/confidence/status/tags/closes_before-after), GET /windows/{ocd_id} (+observations), GET /conflicts (proof feed), GET /accuracy (gated), watchlist CRUD. Webhook fan-out (HMAC-signed, Postgres outbox, document-level docket fan-out, conflict-dual-fire, retry-then-visible-undelivered). RSS/ICS/CSV. MCP server (search_windows, get_window, list_observations) deferred but contract pre-shaped. | Fastify; Zod->OpenAPI 3.1; Postgres outbox polled every 60s (NO Temporal/BullMQ-Redis at MVP — Postgres is the queue); HMAC-SHA256; ical.js; Postgres FTS (tsvector). |
| Internal Review Console | Thin internal-operator-only surface (NOT design-partner-facing) showing CONFLICTING/LOW/PENDING_REVIEW windows with side-by-side source values, DATES text, chain members, govinfo link. Reviewer resolves by INSERTING a human_review observation (never mutating the window directly); the reconciler re-derives. | Retool-over-Postgres at MVP (30-min setup) OR a minimal Next.js /admin route with Clerk auth. A built console is a paid feature only when a customer asks to self-resolve. |

## Confidence model

A deterministic, VERSIONED RuleBox rulebook runs in the reconcile stage; every confidence assignment carries a structured explanation (rules_fired, source_agreement, parse_path, staleness, conflict_ids) returned in the API. Confidence is NEVER ML-scored and NEVER LLM-scored — the LLM only classifies AMBIGUOUS extension/correction chains. The cardinal rule: a bad deadline is worse than no alert, so confidence drops suppress confident pushes — but suppression always pairs with an honest conflict/needs-verification signal, never silence. Operational HIGH is defined as measurable parameters (Eastern-date source agreement, freshness SLA by time-to-close, empty extension-chain lookback), not a marketing label, because buyers carry deadline liability.

| State | Meaning | Alert behavior |
| --- | --- | --- |
| HIGH | FR and Regs.gov agree on the close date when BOTH normalized to America/New_York; openForComment consistent; no unresolved extension/correction/withdrawal in the chain; freshest observation within the dynamic-freshness window for this window's time-to-close. | Eligible for closing-soon push and all delivery. |
| MEDIUM | One source present with no contradiction, OR sources agree but one observation is moderately stale, OR allowLateComments=true creates a formal-close-vs-practical-close ambiguity. | Eligible for push; allowLateComments ambiguity surfaced in payload. |
| LOW | commentEndDate null but openForComment=true; or only date-only FR value with no timezone resolution; or chain plausible but unverified. | Appears in API; not pushed as a confident deadline; surfaced in review console. |
| CONFLICTING | FR vs Regs.gov differ by >=1 Eastern calendar day; OR withdrawn=true conflicts with openForComment=true; OR an unresolved extension/correction chain. The marquee differentiator — the one case existing single-source tools give NO signal for. A 1-UTC-day gap that is the SAME Eastern date is flagged tz_normalization_only at MEDIUM, never CONFLICTING. | Closing-soon SUPPRESSED AND a conflict/needs-verification notification SIMULTANEOUSLY FIRED with both source observations + govinfo_url. Published to the GET /conflicts proof feed within 15 min. |
| STALE | No fresh observation within the dynamic threshold: 4h for windows closing within 72h, scaling to 48h for windows 30+ days out. | Push suppressed unless subscriber explicitly opts into low-confidence; flagged in console. |
| UNKNOWN | Both structured deadline fields missing; resolved_close_utc = NULL. | Published honestly; never pushed; never coerced to a guessed date. |

## Data sources

| Source | Role | Gotchas |
| --- | --- | --- |
| Federal Register API (federalregister.gov/api/v1) | Discovery spine + legal-publication anchor. Fields: document_number, comments_close_on (date-only), dates (verbatim DATES text — legally authoritative language), comment_url, docket_ids, regulations_dot_gov_info, regulation_id_number_info (RIN), correction_of/corrections, action, title. | Unofficial XML rendition — NOT legal notice (attach govinfo_url). comments_close_on is date-only with NO timezone; the FR-2018-27875 one-day gap vs Regs.gov is a normalization artifact, not a conflict. correction_of/corrections unreliable (2024-03267 null despite being a correction) — also parse action/title. Extension notices are SEPARATE documents that do NOT update the original's date; the extension doc itself may have commentEndDate=null/openForComment=false (2025-03547). Field semantics under-documented (GitHub issue #9). |
| Regulations.gov v4 API (api.regulations.gov / api.data.gov) | Operational status authority. Fields: commentEndDate (ISO-8601+offset, preferred for resolved_close_utc), openForComment, withinCommentPeriod, allowLateComments, withdrawn, frDocNum (primary join key), objectId (comment-association key), docketId, lastModifiedDate (change cursor). | 1,000 req/hr GET key; commenting sub-API 50/min & 500/hr (irrelevant — read-only MVP, but don't conflate). Pagination hard cap 20 pages x 250 = 5,000/query; lastModifiedDate paging is GSA-beta and may be removed — file for bulk/limit increase early. lastModifiedDate filter is Eastern, responses UTC (6h cursor-overlap + dedupe). objectId != documentId for comments. commentEndDate can be null while openForComment=true. Agency-configurable submitter fields appear/disappear. |
| GovInfo (api.govinfo.gov) | Legal-reliance backstop link only. Embed govinfo_url in every window/response/alert as the disclaimer anchor. NO PDF/text ingestion in MVP. | Public URL pattern (content/pkg/FR-{date}/html/{frDocNum}.htm) needs no API call. Flag for review if URL resolution fails (rare). |
| Mirrulations S3 + mirrulations-search Postgres / spicy-regs Parquet+DuckDB | OFFLINE eval + bootstrap ONLY. Seed historical observations, build the labeled conflict/chain regression suite, run rulebook regression tests in CI, mine extension/correction/withdrawal edge cases. Path to a future MCP/DuckDB SQL surface for AI-agent buyers. | Does NOT reduce ongoing freshness cost — never a live feed. Noisy (ACUS/GAO data-quality findings) — treat as eval set, not clean training set. Static snapshot; refresh periodically. |
| USGS Watershed Boundary Dataset (WBD) via The National Map ArcGIS REST | VERTICAL-ONLY (Watershed Watch enrichment), NOT a DocketClock core source. The Watershed Watch enrichment worker resolves HUC-8/12 and writes tags via the enrichment API. | Substrate stays agnostic — core never imports/queries WBD. Geo recall (whether a docket mentions a basin) is Watershed Watch's problem, not the substrate's; document this boundary explicitly. |

## Delivery surfaces

- **REST API (OpenAPI 3.1, spec-first)** — GET /windows (filter agency/docket/confidence/status/tags/closes_before-after, paginated), GET /windows/{ocd_id} (full provenance + observations), GET /conflicts (proof feed), GET /accuracy (design-partner-gated during calibration). Zod-generated spec published at /openapi.json so buyers inspect before purchase. Every response carries disclaimer + api_version + request_id.
- **Webhooks (HMAC-signed, Postgres outbox)** — Per-watchlist, document-level fan-out (a docket_id watch hits all its documents). notify_on: open | closing_soon | conflict | changed | closed | needs_verification. Conflict-dual-fire enforced. 3 retries + exponential backoff, then delivered=false surfaced via GET /events so no push silently vanishes.
- **RSS/Atom + ICS + CSV/JSONL** — RSS per agency/watchlist + a first-class /conflicts Atom feed (the public honesty signal). ICS for calendar embed. CSV/JSONL bulk snapshots. RSS/ICS/CSV are v1.1 (after REST + webhooks validated by design partners) to hold MVP scope.
- **MCP server (deferred, contract pre-shaped)** — search_windows / get_window / list_observations / subscribe_watchlist, with confidence + conflict_flags mandatory in every structured response and a tool description instructing agents to surface them before acting. Built only when an AI-agent buyer commits — the three named design partners are NOT MCP buyers, so shipping it in the core MVP sprint is rejected.
- **Internal review console** — Operator-only (Retool/Next.js). Design partners get API + webhooks, never console access; their corrections become support tickets -> human_review observations.

## MVP boundary

**In scope (v1):**
- Federal-only: all Regs.gov documents with openForComment=true or commentEndDate within the next 90 days, plus FR extension/correction/withdrawal notices
- Append-only Observation log (DB-trigger-enforced) + FR and Regs.gov v4 adapters with Eastern-aware differential polling
- Reconciliation rulebook covering the documented patterns: Eastern-date mismatch, extension chain, null-end-date-open-status, withdrawn-vs-open, multi-target notice, non-monotonic correction; regression-tested against spicy-regs
- ParticipationWindow as a derived versioned projection with stable OCD-IDs, resolved_close_utc + resolved_close_display, typed conflict_flags
- REST API + OpenAPI 3.1 spec + API-key auth (the design-partner deliverable)
- Webhooks (HMAC, Postgres outbox, document-level fan-out, conflict-dual-fire, undelivered visibility)
- GET /conflicts proof feed; AccuracyRecord verification job (dashboard design-partner-gated)
- Built-in agency-slug + CFR-part enrichment writing tags (ships before onboarding so tag filtering isn't empty)
- Internal-only review console (Retool); govinfo_url + disclaimer on every record
- Week-1 frDocNum hit-rate + conflict-rate measurement as a go/no-go gate; Week-1 GSA rate-increase application

**Deferred:**
- RSS/ICS/CSV bulk delivery (v1.1, after REST+webhooks validated)
- MCP server (until a named AI-agent buyer commits)
- Enrichment API for THIRD-PARTY/vertical tag namespaces (built-in enrichment ships; the open tenant-writable hook registry follows when Watershed Watch commits)
- Watershed Watch geo-enrichment worker, USGS WBD, Open States v3, EIS clock (vertical builds ON TOP)
- OpenSearch (hard-deferred — Postgres FTS handles <10k windows indefinitely)
- Temporal / BullMQ-Redis (Postgres outbox suffices)
- GovInfo full-text PDF ingestion (link-only)
- Email digests (webhook -> Zapier handles it)
- State/local sources (literal thou-shalt-not until a funded jurisdiction tranche)
- Pol.is consensus, comment submission/action layer, final-rule causal impact (vertical action layer, not substrate)
- SOC 2 / enterprise procurement (Year-2, after first 3 paying contracts)

**First customer:** Two boutique/mid law-firm current-awareness (KM) teams + one life-sciences regulatory-affairs team where the buyer is also the technical evaluator (credit-card MSA, no 6-month IT procurement). Design-partner rate $500-$2k/mo WITH an explicit escalation clause to standard pricing ($10k-$50k/yr range the comps justify: RegAlytics $1.8k/mo single seat, AgencyIQ $25k-$75k/yr) after 90 days so the pilot price is not a permanent anchor. Success metric: design partners find >=3 real extension/correction/withdrawal conflicts existing single-source tools missed. Watershed Watch (Chesapeake via a Waterkeeper/CBF chapter) is a FAST-FOLLOW vertical pilot leveraging the user's network access — pursued only when a chapter commits to a pilot contract, never before the substrate has its first B2B customer.

## Tech stack

| Layer | Choice | Why |
| --- | --- | --- |
| Language/runtime | TypeScript (Node 22 LTS) | Zod schema-first gives runtime validation + OpenAPI in one pass; B2B buyers' first ask is the API spec. REST sources + join/rule logic suit TS; type system catches frDocNum-vs-fr_doc_num field-casing bugs across sources. |
| Database | Postgres 16 (JSONB + tsvector), self-managed or hardened-Supabase | The whole infra: append-only observation log (DB trigger), canonical store, queue (outbox), FTS, pg_trgm fuzzy fallback. ~1,000 open windows is trivially within Postgres FTS. If on Supabase, lock down roles/Studio to protect the immutable observations table. |
| Queue/scheduler | Postgres outbox + pg_cron/Node cron at MVP | At ~1,000 windows + ~100 subscriptions the outbox never exceeds a few thousand rows. Temporal and BullMQ-on-Redis are both REJECTED for MVP as weeks of ops for zero buyer-visible feature; revisit BullMQ/Temporal only when durable long-running chain workflows or 10k+ subscriptions demand it. |
| API framework | Fastify + Zod-to-OpenAPI | Fastest Zod-schema -> running OpenAPI 3.1 endpoint; schema-based serialization keeps published spec and actual responses from diverging — critical when confidence/provenance are contract, not optional. |
| Reconciliation engine | JSON RuleBox + Zod, Haiku fallback | Deterministic, versioned, explainable; regression-tested in CI against spicy-regs. LLM reserved for AMBIGUOUS chain classification + deny-list misses only (<$1/day). |
| Eval/regression | DuckDB over spicy-regs/Mirrulations Parquet | No infra; runs in CI; the pre-architecture conflict-rate + join-hit-rate measurement and every rulebook regression test live here. |
| Admin/review | Retool-over-Postgres (or minimal Next.js + Clerk) | Internal founder tool, not a built system at MVP; the human-review console in its correct v1 form. |
| Hosting | Render or Fly.io (API + workers), managed Postgres | Zero-ops containers: web API + background poller + outbox worker from one repo. No Kubernetes/Lambda. ~$25-50/mo covers the design-partner phase. |
| Selective LLM | Claude Haiku via Anthropic API | Chain-classification + extension-keyword disambiguation only, structured JSON, ~50 calls/day at launch. Never in the deadline-resolution or confidence-scoring hot path. |

## Build sequence (~12 weeks)

1. **Week 1 — Validate + de-risk (gate)** — DuckDB measurement over live APIs + Mirrulations/spicy-regs of (a) frDocNum join hit-rate and (b) empirical FR-vs-Regs.gov Eastern-date conflict rate, written up as the first sales-evidence 'Conflict Rate Report'. GO/NO-GO decision on join strategy. GSA rate-increase + bulk-access application filed.
2. **Week 2-3 — Spine** — Postgres schema (Observation append-only + trigger, ParticipationWindow, observation_targets M:N, Watchlist, Tenant, outbox). FR + Regs.gov adapters with Eastern-aware differential polling + 6h cursor overlap + dedupe. Payload-hash idempotent observation ingestion. OCD-ID generation validated as stable.
3. **Week 4-5 — Reconciliation + confidence** — JSON RuleBox covering all documented patterns with Eastern-date comparison, non-monotonic chains, deny-list keyword guard, >30-day-jump PENDING_REVIEW guard. CI regression suite over spicy-regs chains. Confidence + typed conflict_flags + resolved_close_utc/display + explanation object. Haiku chain-adjudication fallback.
4. **Week 6-7 — Public contract** — Fastify REST API (GET /windows, /windows/{ocd_id}+observations, /conflicts) + Zod-generated OpenAPI 3.1 at /openapi.json + API-key auth + per-tenant rate limiting. HMAC webhook outbox worker with document-level fan-out, conflict-dual-fire, undelivered visibility. govinfo_url + disclaimer on every record. Built-in agency/CFR enrichment writing tags.
5. **Week 8 — Review + onboarding** — Internal Retool review console (CONFLICTING/LOW/PENDING_REVIEW, side-by-side, human_review-observation resolution, dynamic staleness queue). Onboard 2 law-firm KM teams + 1 reg-affairs team on the live API/webhooks with the OpenAPI spec and a demo watchlist; collect conflict-copy and payload-shape feedback.
6. **Week 9-10 — Follow-up + proof** — Post-close verification worker + AccuracyRecord; window.finalized linkage; dynamic STALE detection + low-confidence suppression with dual-fire validated end-to-end. Design-partner-gated accuracy dashboard. Every was_correct=false becomes a regression test.
7. **Week 11-12 — Convert + v1.1 seam** — First paid contract signed with escalation clause. RSS/ICS/CSV delivery (v1.1). Iterate on real workflow needs (Slack-via-Zapier, calendar embed, read-only Postgres). Tenant-writable enrichment hook registry stubbed for the Watershed Watch fast-follow if a Chesapeake chapter commits.

## Top risks

| Risk | Mitigation |
| --- | --- |
| FR-vs-Regs.gov reconciliation flags routine timezone-normalization 1-day gaps as CONFLICTING, flooding the bucket and destroying the only differentiator (the fatal flaw across two proposals). | Compare both dates normalized to America/New_York calendar date, not UTC. Same Eastern date => agree (tz_normalization_only at MEDIUM if UTC strings differ); only a true Eastern-day difference or unresolved chain => CONFLICTING. Validated against FR-2018-27875 in the Week-1 report and the CI regression suite. |
| frDocNum join fails for a large fraction of records (ACUS: agencies omit/misconfigure identifiers), collapsing the reconciliation value prop and leaving a dark zone with no cross-source signal. | Week-1 hit-rate measurement is a hard go/no-go gate. Fallback join on docket_id array overlap (Postgres &&) + RIN; unjoined records carry confidence=medium, conflict_reason='no_cross_source_join', never dropped. Below 60% => documented pivot to Regs.gov-primary; pg_trgm title fuzzy-match as last resort. Track join-failure as a daily metric. |
| Confidence drop silently suppresses a closing-soon alert for a deadline-liable buyer who then misses the window — silence is worse than a wrong alert. | Conflict-dual-fire: suppression NEVER means silence. CONFLICTING/STALE suppress closing-soon AND simultaneously fire a needs-verification notification with both source observations + govinfo_url. Permanent webhook failure surfaces via GET /events. Every payload disclaims legal authority and links the authoritative govinfo source. |
| One FR notice extends multiple dockets with different deadlines (EPA 2025-02910) or a chain is non-monotonic (correction moving a date earlier); a 1:1 or 'latest-wins' model silently leaves the second window stale. | observation_targets M:N join writes N window updates from one notice; the reconciler re-evaluates the whole chain on each new observation rather than blind latest-wins; a >30-day resolved-date jump forces PENDING_REVIEW. All three patterns are CI regression tests mined from spicy-regs. |
| Regs.gov rate limit / lastModifiedDate-beta pagination is hit or removed; or a multi-key workaround triggers ToS revocation — existential loss of the operational status source. | Differential polling (list cheaply, fetch detail only on lastModifiedDate change) stays well inside 1,000 req/hr at ~1,000 windows. File a GSA rate-increase + bulk-access request in Week 1 (NOT multi-key). Eastern/UTC cursor handled with a 6h overlap + documentId dedupe to prevent silent misses. |
| Watershed Watch is dismissed as 'just DocketClock with a Waterkeeper skin' and gold-plates the MVP, or the substrate leaks vertical (HUC) concerns into core. | Hard layer boundary: core is HUC-agnostic; verticals scope via stable OCD-IDs + the tag/enrichment contract (separate deployment calling the enrichment API). Watershed Watch is a funded FAST-FOLLOW pursued only on a committed Chesapeake/Waterkeeper pilot, leveraging the user's real design-partner network — never before the first B2B contract, and it earns distribution by adding geo-recall + plain-language briefs the bare registry can't, not by re-skinning it. |

## Divergences from the earlier dossier

- Prior dossier framed DocketClock primarily as a reconciliation/confidence engine; this architecture makes the append-only Observation log the PRIMARY data model and the ParticipationWindow a derived projection — a structural commitment the dossier implied but did not pin.
- The dossier left OCD-IDs as a 'normalize downstream' nicety; here they are the PRIMARY public key and the explicit substrate-rental seam (verticals join on OCD-IDs, never internal UUIDs), with a concrete federal namespace scheme.
- The dossier did not specify the timezone-comparison rule; this design makes Eastern-date normalization (not UTC) the load-bearing fix that keeps CONFLICTING meaningful, and separates resolved_close_utc from a verbatim resolved_close_display.
- The dossier's confidence model listed states but not behavior; here suppression is explicitly paired with conflict-dual-fire so a confidence drop never produces silence — a sharper, liability-aware reading of 'a bad deadline is worse than no alert'.
- The dossier suggested Temporal/BullMQ as the queue; this architecture rejects both for MVP in favor of a Postgres outbox, and hard-defers OpenSearch — a more ruthless MVP than the dossier's stack implied.
- The dossier treated the design-partner watchlist UI as part of the registry; here the internal review console is strictly separated from the public surface, and corrections flow as human_review observations to preserve the audit chain.
- The dossier named broad downstream consumer personas at the substrate layer; this design explicitly removes them from core and routes all vertical/persona scoping through the tag/enrichment contract, keeping the canonical object persona-agnostic.
- Added net-new objects the dossier did not enumerate: ConflictRecord (published proof feed), AccuracyRecord (track-record), and the observation_targets M:N join for one-notice-extends-many-dockets — each answering a documented edge case (EPA 2025-02910, BLM 2023-27468, FR 2025-03547).

## Open questions (answer in Week-1 spikes)

- What is the empirical Eastern-date conflict rate across the live ~1,000 open windows? It decides whether GET /conflicts is a marquee feature or a quiet field, and whether the product story is 'alerts' or 'conflict intelligence'. Must be answered in Week 1 before pipeline code.
- Does frDocNum join at >60% hit-rate on the live corpus, or is docket_id/RIN the primary key in practice? Determines the entire reconciliation join strategy (Week-1 go/no-go).
- What is the daily volume of genuine extension/correction/reopening notices (vs deny-list false positives)? Determines whether the review console is a 20-min/day task or a part-time staffing line, and the real maintenance burden of the keyword classifier.
- Do the first design partners need per-agency notification SLAs (e.g. 'FDA change within X hours') or is the polling cadence acceptable as-is? Determines whether near-close polling must tighten.
- Will a Chesapeake-region Waterkeeper/CBF chapter commit to a paid Watershed Watch pilot, given the user's network access — and is that pilot viable before or only after the first B2B substrate contract? Gates whether the enrichment hook registry + WBD geo-enrichment is a fast-follow or stays fully deferred.
- Does GSA grant the rate-increase/bulk-access request, and on what timeline? If lastModifiedDate beta pagination is removed before a permanent bulk solution ships, the historical-backfill and chain-evidence paths need a fallback.
