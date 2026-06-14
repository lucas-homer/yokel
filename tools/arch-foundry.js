export const meta = {
  name: 'docketclock-watershed-arch-foundry',
  description: 'Design DocketClock architecture (vs Codex plan) and Watershed Watch architecture on top of it, via competing architects + adversarial critique + Opus synthesis',
  phases: [
    { title: 'DocketClock design', detail: '3 architects propose competing DocketClock architectures' },
    { title: 'DocketClock review', detail: 'adversarial critique of each proposal' },
    { title: 'DocketClock synthesis', detail: 'Opus lead-architect synthesizes final design + Codex ledger' },
    { title: 'Watershed fit', detail: 'should Watershed Watch build on DocketClock at all?' },
    { title: 'Watershed design', detail: 'thin-client vs thick-vertical architecture proposals' },
    { title: 'Watershed review', detail: 'adversarial critique of each' },
    { title: 'Watershed synthesis', detail: 'Opus synthesizes final Watershed Watch architecture' },
  ],
}

const FOUNDATION = `
PRODUCT CONTEXT (civic-tech project "Yokel"):
- Original consumer thesis: help BUSY NON-EXPERTS (people too busy with work/family to be experts) (1) MONITOR public comment periods, hearings, proposed rules, legislation across public health / urban planning / development / land use / zoning, and (2) take MEANINGFUL ACTION (submit comments, organize, lobby) and SEE IMPACT.
- Strategic frame that emerged: a layered "house" — DocketClock = the reusable deadline/participation-window SUBSTRATE (build first); vertical/consumer WEDGES sit on top (e.g. Watershed Watch for conservation groups); an ACTION layer (consensus/organize) on top of that. Distribution should be CHANNEL-LED (trusted intermediaries: coalitions, associations, land trusts), not direct-to-consumer.

DOCKETCLOCK — what it is (from our own seasoned dossier):
- NOT just "show me rules." The unit of trust is a public-comment DEADLINE exposed as a TRUSTWORTHY, queryable object. Net-new value = RECONCILIATION + CONFIDENCE + PROVENANCE, not discovery (single-source deadline alerts already exist).
- Core problem: the OPERATIVE deadline can be silently changed by a SEPARATE extension/reopening/correction/withdrawal notice that does not update every related record. Federal Register publishes date-only comments_close_on; Regulations.gov publishes timezone-stamped commentEndDate + status flags (openForComment, withinCommentPeriod, allowLateComments, withdrawn). They agree on routine notices and CONFLICT on the high-stakes extended/reopened/corrected/timezone-split minority — exactly where a missed window has legal consequences.
- Differentiator: an explicit CONFIDENCE/CONFLICT flag that SURFACES disagreement instead of hiding it behind one silent "truth" field. "Do not publish fake certainty" — unknown/stale/conflicting are first-class states; suppress or downgrade alerts when confidence drops.
- Federal-first ONLY. State/local is the unmaintainable trap (no normalized cross-state rulemaking API; Legistar has NO comment-deadline field). Refuse state/local until a paying customer funds a specific jurisdiction tranche.
- Buyers (B2B picks-and-shovels): law-firm KM/current-awareness teams, regulatory-affairs teams (life sciences, food, chemicals, energy, transport, finance) who own deadline verification and carry liability; secondary: reg-intelligence vendors, newsletters, trade associations, AI-agent builders wanting a redistributable deadline substrate. (This is an honest pivot away from the consumer thesis at the substrate layer — but it is the funded core a later consumer/vertical layer sits on.)

VERIFIED ASSETS DocketClock builds on:
- Federal Register API (free, keyless): comments_close_on, DATES text, docket_ids, regulations_dot_gov_info, document_number/frDocNum.
- Regulations.gov v4 API (1,000 req/hr key limit): commentStartDate/commentEndDate, openForComment, withinCommentPeriod, allowLateComments, withdrawn, frDocNum, objectId. ~1,000 documents open for comment at any time.
- govinfo official PDF/text: legal-reliance backstop; link every record so DocketClock disclaims being legal authority.
- Mirrulations S3 mirror + mirrulations-search Postgres schema: full free historical corpus on AWS Open Data (comment-window fields shipped). Use as labeled EVAL set for the conflict classifier. (Does NOT reduce ongoing freshness cost — classifier asset, not "expensive part done.")
- spicy-regs Parquet/DuckDB + MCP: SQL-query the historical corpus to mine extension/correction/withdrawal edge cases and regression-test reconciliation rules; path to an MCP interface for AI-agent buyers.
- Open Civic Data (OCD) standard + stable OCD-IDs: normalize each resolved deadline as an OCD Event so downstream builders get a clean joinable substrate.
- RuleBox pattern (mySociety): LLM generates classification rules that run on cheap deterministic infra; costly LLM only adjudicates ambiguous extension-chain cases.
- MAPLE patterns: Firestore/Cloud Functions + self-hosted Typesense indexer + separate LLM enrichment service + follow->event->feed->digest notification engine + versioned public archive.
- Known real divergence example: FR record 2018-27875 FR date 2019-03-14 vs embedded Regs.gov 2019-03-15.

CODEX'S DOCKETCLOCK ARCHITECTURE (the plan to react to — keep as much or as little as judgment dictates):
- Canonical object: ParticipationWindow (docket ID, title, agency, window type, open/close times, timezone, submission URL, provenance, confidence, status, change history). "The unit of trust."
- Pipeline: Discover (new/changed notices) -> Normalize (canonical windows) -> Verify (source, confidence, conflicts) -> Publish (API, RSS, ICS, CSV, webhooks) -> Follow up (closed, extended, final-linked).
- 6 components: (1) Source adapters (FR API, Regulations.gov v4, Mirrulations/history, GovInfo/eCFR later); (2) Immutable event log (every observation: payload hash, fetched_at, source URL, parser version, extracted candidates — makes deadline changes auditable); (3) Normalizer (entity resolution ties notices/dockets/agencies/CFR parts/comment URLs/corrections/reopenings into one canonical window graph); (4) Confidence engine (rules -> high/medium/low/stale/conflicting based on source agreement, date-parse certainty, freshness, status semantics); (5) Human review console (only uncertain/high-impact: conflicting deadlines, changed close dates, ambiguous tz/date text, reopened dockets, user corrections); (6) Registry + API (Postgres canonical objects; search index; delivery workers emit webhooks/RSS/ICS/CSV/bulk snapshots).
- Suggested MVP stack: TypeScript workers + API; Postgres (JSONB raw observations + version history); Temporal/BullMQ/Cloud Tasks queue; Postgres FTS first then OpenSearch; Zod/JSON Schema + public OpenAPI; small admin + design-partner watchlist UI.
- Trust model: show uncertainty; unknown/stale/conflicting first-class; a bad deadline is worse than no alert -> suppress/downgrade alerts when confidence drops.
- Expansion rule: do NOT expand to state/local until a funded source cluster exists.
- Named downstream users: pharmacy desks, childcare associations, journalists, advocacy orgs, civic apps, legal/policy shops.

WATERSHED WATCH — our seasoned dossier (the vertical wedge to evaluate in Part B):
- A basin-scoped environmental DEADLINE-AND-ACTION radar for small volunteer conservation groups (watershed alliances, Waterkeeper affiliates, land trusts, friends-of-the-creek). They have passion but no policy staff, miss short windows, file weak duplicate comments, burn out because they can't see impact.
- User picks their basin from the USGS Watershed Boundary Dataset (WBD / HUC-8/12) via The National Map ArcGIS REST (free national geo primitive — no bespoke boundary drawing); system resolves intersecting states/counties.
- Geo-bearing, deadline-bearing stream: EPA EIS database (searchable by state, fixed 45-day-draft / 30-day-final comment clock) + Regulations.gov dockets + Federal Register + Open States v3 (state env legislation). RuleBox-style LLM rules scope docket text to the basin/HUC/named water bodies.
- Each hit becomes a first-class alertable deadline object with lead-time reminders; plain-language brief; structured-evidence comment composer that files to Regulations.gov; honest procedural receipts (filed-on-time, comment counts, draft-to-final diffs — NEVER causal "you changed this").
- Local long tail handled by members (NoticeNail photo-of-posted-notice, geocode parcel) — labeled "community signal, not comprehensive monitoring." DEFERRED past MVP. Pol.is consensus reserved for genuinely contested multi-faction fights.
- Business model channel-led: foundation/EJ grants fund free Tier-1 for volunteers; paid org seats to staffed land trusts/coalitions (the distribution channel); a sideways DocketClock confidence feed licensed to nonprofits/newsrooms.
- HONEST RESIDUAL RISK (from our own critique): Watershed Watch may be "just DocketClock + a Waterkeeper-branded skin"; the vertical must prove it earns distribution/funding the bare registry can't. The most emotionally-charged fights (local floodplain rezoning) are exactly the ones Tier-1 can LEAST reliably surface, so the wedge may feel underwhelming vs the mission.
- First partner candidate: Chesapeake Bay watershed via a Waterkeeper affiliate / Chesapeake Bay Foundation chapter (dense federal/state EIS+permit activity, organized funded coalition, multi-state HUC exercises cross-jurisdiction logic); smaller alt: SF Bay via Baykeeper.

USER'S NETWORK NOTE (Part B): the user has personal-network access to people in the Watershed Watch user persona, so go DEEPER on this one and treat real design-partner access as a genuine asset.
`

const DESIGN_PROPOSAL = {
  type: 'object',
  properties: {
    stance: { type: 'string' },
    thesis: { type: 'string' },
    canonical_model: {
      type: 'array',
      items: { type: 'object', properties: { object: { type: 'string' }, key_fields: { type: 'string' }, why: { type: 'string' } }, required: ['object', 'key_fields', 'why'] },
    },
    pipeline_stages: { type: 'array', items: { type: 'object', properties: { stage: { type: 'string' }, what: { type: 'string' }, tech: { type: 'string' } }, required: ['stage', 'what'] } },
    components: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, responsibility: { type: 'string' }, tech: { type: 'string' } }, required: ['name', 'responsibility'] } },
    data_sources: { type: 'array', items: { type: 'object', properties: { source: { type: 'string' }, role: { type: 'string' }, gotchas: { type: 'string' } }, required: ['source', 'role'] } },
    confidence_model: { type: 'string' },
    delivery: { type: 'array', items: { type: 'string' } },
    tech_stack: { type: 'array', items: { type: 'object', properties: { layer: { type: 'string' }, choice: { type: 'string' }, why: { type: 'string' } }, required: ['layer', 'choice'] } },
    mvp_scope: { type: 'string' },
    deferred: { type: 'array', items: { type: 'string' } },
    codex_steal: { type: 'array', items: { type: 'string' } },
    codex_drop: { type: 'array', items: { type: 'object', properties: { item: { type: 'string' }, why: { type: 'string' } }, required: ['item', 'why'] } },
    key_risks: { type: 'array', items: { type: 'object', properties: { risk: { type: 'string' }, mitigation: { type: 'string' } }, required: ['risk', 'mitigation'] } },
    open_questions: { type: 'array', items: { type: 'string' } },
  },
  required: ['stance', 'thesis', 'canonical_model', 'pipeline_stages', 'components', 'data_sources', 'confidence_model', 'tech_stack', 'mvp_scope', 'codex_steal', 'codex_drop', 'key_risks'],
}

const CRITIQUE = {
  type: 'object',
  properties: {
    target: { type: 'string' },
    strengths: { type: 'array', items: { type: 'string' } },
    weaknesses: { type: 'array', items: { type: 'object', properties: { issue: { type: 'string' }, severity: { type: 'string', enum: ['low', 'medium', 'high', 'fatal'] }, why: { type: 'string' } }, required: ['issue', 'severity', 'why'] } },
    missing: { type: 'array', items: { type: 'string' } },
    verdict: { type: 'string' },
    score: { type: 'number' },
  },
  required: ['target', 'strengths', 'weaknesses', 'verdict', 'score'],
}

const DC_SYNTH = {
  type: 'object',
  properties: {
    title: { type: 'string' },
    one_liner: { type: 'string' },
    architecture_thesis: { type: 'string' },
    canonical_object: { type: 'object', properties: { name: { type: 'string' }, key_fields: { type: 'array', items: { type: 'object', properties: { field: { type: 'string' }, desc: { type: 'string' } }, required: ['field', 'desc'] } }, design_notes: { type: 'string' } }, required: ['name', 'key_fields', 'design_notes'] },
    pipeline: { type: 'array', items: { type: 'object', properties: { stage: { type: 'string' }, what: { type: 'string' }, detail: { type: 'string' } }, required: ['stage', 'what', 'detail'] } },
    components: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, responsibility: { type: 'string' }, tech: { type: 'string' }, notes: { type: 'string' } }, required: ['name', 'responsibility'] } },
    data_sources: { type: 'array', items: { type: 'object', properties: { source: { type: 'string' }, role: { type: 'string' }, gotchas: { type: 'string' } }, required: ['source', 'role'] } },
    confidence_model: { type: 'object', properties: { states: { type: 'array', items: { type: 'object', properties: { state: { type: 'string' }, meaning: { type: 'string' }, alert_behavior: { type: 'string' } }, required: ['state', 'meaning', 'alert_behavior'] } }, how_computed: { type: 'string' } }, required: ['states', 'how_computed'] },
    delivery_surfaces: { type: 'array', items: { type: 'object', properties: { surface: { type: 'string' }, detail: { type: 'string' } }, required: ['surface', 'detail'] } },
    tech_stack: { type: 'array', items: { type: 'object', properties: { layer: { type: 'string' }, choice: { type: 'string' }, why: { type: 'string' } }, required: ['layer', 'choice', 'why'] } },
    mvp_boundary: { type: 'object', properties: { in_scope: { type: 'array', items: { type: 'string' } }, deferred: { type: 'array', items: { type: 'string' } }, first_customer: { type: 'string' } }, required: ['in_scope', 'deferred', 'first_customer'] },
    codex_ledger: { type: 'object', properties: {
      kept: { type: 'array', items: { type: 'object', properties: { item: { type: 'string' }, why: { type: 'string' } }, required: ['item', 'why'] } },
      changed: { type: 'array', items: { type: 'object', properties: { item: { type: 'string' }, from: { type: 'string' }, to: { type: 'string' }, why: { type: 'string' } }, required: ['item', 'to', 'why'] } },
      rejected: { type: 'array', items: { type: 'object', properties: { item: { type: 'string' }, why: { type: 'string' } }, required: ['item', 'why'] } },
    }, required: ['kept', 'changed', 'rejected'] },
    divergences_from_prior_dossier: { type: 'array', items: { type: 'string' } },
    build_sequence: { type: 'array', items: { type: 'object', properties: { milestone: { type: 'string' }, deliverable: { type: 'string' } }, required: ['milestone', 'deliverable'] } },
    top_risks: { type: 'array', items: { type: 'object', properties: { risk: { type: 'string' }, mitigation: { type: 'string' } }, required: ['risk', 'mitigation'] } },
    open_questions: { type: 'array', items: { type: 'string' } },
  },
  required: ['title', 'one_liner', 'architecture_thesis', 'canonical_object', 'pipeline', 'components', 'data_sources', 'confidence_model', 'delivery_surfaces', 'tech_stack', 'mvp_boundary', 'codex_ledger', 'build_sequence', 'top_risks'],
}

const FIT = {
  type: 'object',
  properties: {
    builds_on_docketclock: { type: 'string', enum: ['yes-fully', 'yes-partially', 'no'] },
    rationale: { type: 'string' },
    is_land_use_wedge: { type: 'boolean' },
    wedge_reasoning: { type: 'string' },
    layer_boundary: { type: 'object', properties: { docketclock_provides: { type: 'array', items: { type: 'string' } }, watershed_adds: { type: 'array', items: { type: 'string' } } }, required: ['docketclock_provides', 'watershed_adds'] },
    requirements_on_docketclock: { type: 'array', items: { type: 'string' } },
    counterfactual_if_standalone: { type: 'string' },
    risks: { type: 'array', items: { type: 'string' } },
  },
  required: ['builds_on_docketclock', 'rationale', 'is_land_use_wedge', 'wedge_reasoning', 'layer_boundary', 'requirements_on_docketclock', 'counterfactual_if_standalone', 'risks'],
}

const WW_PROPOSAL = {
  type: 'object',
  properties: {
    stance: { type: 'string' },
    thesis: { type: 'string' },
    relationship_to_docketclock: { type: 'string' },
    components: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, responsibility: { type: 'string' }, tech: { type: 'string' } }, required: ['name', 'responsibility'] } },
    geo_scoping: { type: 'string' },
    data_sources: { type: 'array', items: { type: 'object', properties: { source: { type: 'string' }, role: { type: 'string' }, gotchas: { type: 'string' } }, required: ['source', 'role'] } },
    action_loop: { type: 'array', items: { type: 'object', properties: { step: { type: 'string' }, what: { type: 'string' } }, required: ['step', 'what'] } },
    coverage_tiers: { type: 'array', items: { type: 'object', properties: { tier: { type: 'string' }, what: { type: 'string' }, labeling: { type: 'string' } }, required: ['tier', 'what'] } },
    tech_stack: { type: 'array', items: { type: 'object', properties: { layer: { type: 'string' }, choice: { type: 'string' }, why: { type: 'string' } }, required: ['layer', 'choice'] } },
    mvp_scope: { type: 'string' },
    deferred: { type: 'array', items: { type: 'string' } },
    key_risks: { type: 'array', items: { type: 'object', properties: { risk: { type: 'string' }, mitigation: { type: 'string' } }, required: ['risk', 'mitigation'] } },
  },
  required: ['stance', 'thesis', 'relationship_to_docketclock', 'components', 'geo_scoping', 'data_sources', 'action_loop', 'coverage_tiers', 'tech_stack', 'mvp_scope', 'key_risks'],
}

const WW_SYNTH = {
  type: 'object',
  properties: {
    title: { type: 'string' },
    one_liner: { type: 'string' },
    architecture_thesis: { type: 'string' },
    relationship_to_docketclock: { type: 'string' },
    components: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, responsibility: { type: 'string' }, tech: { type: 'string' }, notes: { type: 'string' } }, required: ['name', 'responsibility'] } },
    geo_scoping: { type: 'object', properties: { primitive: { type: 'string' }, how: { type: 'string' }, gotchas: { type: 'string' } }, required: ['primitive', 'how'] },
    data_sources: { type: 'array', items: { type: 'object', properties: { source: { type: 'string' }, role: { type: 'string' }, gotchas: { type: 'string' } }, required: ['source', 'role'] } },
    action_loop: { type: 'array', items: { type: 'object', properties: { step: { type: 'string' }, what: { type: 'string' } }, required: ['step', 'what'] } },
    coverage_tiers: { type: 'array', items: { type: 'object', properties: { tier: { type: 'string' }, what: { type: 'string' }, labeling: { type: 'string' } }, required: ['tier', 'what'] } },
    tech_stack: { type: 'array', items: { type: 'object', properties: { layer: { type: 'string' }, choice: { type: 'string' }, why: { type: 'string' } }, required: ['layer', 'choice', 'why'] } },
    mvp_boundary: { type: 'object', properties: { in_scope: { type: 'array', items: { type: 'string' } }, deferred: { type: 'array', items: { type: 'string' } }, first_partner: { type: 'string' } }, required: ['in_scope', 'deferred', 'first_partner'] },
    build_sequence: { type: 'array', items: { type: 'object', properties: { milestone: { type: 'string' }, deliverable: { type: 'string' } }, required: ['milestone', 'deliverable'] } },
    top_risks: { type: 'array', items: { type: 'object', properties: { risk: { type: 'string' }, mitigation: { type: 'string' } }, required: ['risk', 'mitigation'] } },
    open_questions: { type: 'array', items: { type: 'string' } },
  },
  required: ['title', 'one_liner', 'architecture_thesis', 'relationship_to_docketclock', 'components', 'geo_scoping', 'data_sources', 'action_loop', 'coverage_tiers', 'tech_stack', 'mvp_boundary', 'build_sequence', 'top_risks'],
}

// ---------- PART A: DocketClock ----------
phase('DocketClock design')

const A_STANCES = [
  { key: 'pragmatist', brief: 'SHIP-FAST PRAGMATIST. Optimize for the fastest path to a paying design partner. Cut every component not strictly required to deliver a trustworthy federal comment-deadline feed to the first customer. Prefer boring managed infra. Be willing to defer the immutable event log, OpenSearch, and the human-review console if a leaner version gets to revenue faster. Challenge whether the full reconciliation engine is needed for v1 or whether a thinner conflict-flag heuristic suffices.' },
  { key: 'trust', brief: 'TRUST & PROVENANCE MAXIMALIST. The product IS the confidence/conflict track record. Treat the immutable event log, provenance, the confidence engine, and a published accuracy record as the core moat, not optional. Design so that "do not publish fake certainty" is enforced architecturally (alerts gated on confidence). Optimize for auditability and the "conflicts this week" proof feed from day one.' },
  { key: 'substrate', brief: 'SUBSTRATE / EXTENSIBILITY ARCHITECT. Design DocketClock explicitly as the reusable primitive that vertical wedges (Watershed Watch, pharmacy/childcare radars) and AI agents sit on. Get the public contract and the layer boundary right: OCD-normalized output, stable OCD-IDs, clean REST/webhook/MCP surfaces, multi-tenant watchlists, and hooks (e.g. geo/agency/CFR tagging) that verticals need WITHOUT DocketClock itself becoming vertical-specific. Optimize for "a vertical can be built on this in a weekend."' },
]

const proposePrompt = (s) => `${FOUNDATION}

You are a senior systems architect. Propose a complete DocketClock technical architecture from THIS stance:
${s.brief}

React directly to Codex's architecture above — for each major Codex decision (ParticipationWindow object, 5-stage pipeline, the 6 components, the MVP stack, the trust model, the expansion rule) decide whether to KEEP, CHANGE, or DROP it, and populate codex_steal (what you keep) and codex_drop (what you reject/replace, with why). Be concrete and cite the verified assets (FR fields, Regs.gov flags, Mirrulations, spicy-regs, OCD-IDs, RuleBox) where relevant. Be opinionated from your stance — do not hedge into a generic middle. Return the structured proposal.`

const aResults = await pipeline(
  A_STANCES,
  (s) => agent(proposePrompt(s), { label: `dc-propose:${s.key}`, phase: 'DocketClock design', model: 'sonnet', schema: DESIGN_PROPOSAL }),
  (prop, s) => prop ? agent(
    `${FOUNDATION}

Adversarially review this DocketClock architecture proposal (stance: ${s.key}). Be a skeptical staff engineer + a skeptical buyer. Find real weaknesses: where will this fail to ingest correctly, mis-reconcile, over- or under-build, cost too much to operate, or fail to win the first customer? Judge whether its keep/drop calls on Codex are sound. Score 1-10 on architectural soundness for THIS product. Proposal JSON:
${JSON.stringify(prop)}`,
    { label: `dc-critique:${s.key}`, phase: 'DocketClock review', model: 'sonnet', schema: CRITIQUE }
  ).then((c) => ({ stance: s.key, proposal: prop, critique: c })) : null,
)

const dcClean = aResults.filter(Boolean)
log(`DocketClock: ${dcClean.length}/3 proposals reviewed`)

phase('DocketClock synthesis')
const dcArch = await agent(
  `${FOUNDATION}

You are the LEAD ARCHITECT. Three architects proposed competing DocketClock architectures (pragmatist / trust-maximalist / substrate) and each was adversarially critiqued. Synthesize the SINGLE best DocketClock architecture we should actually build — not an average, but a decisive design that takes the strongest idea from each stance and answers the critiques.

Hard requirements:
- Be decisive and concrete (real components, real tech, real FR/Regs.gov fields, real OCD-IDs).
- Populate codex_ledger fully: what we KEPT from Codex's plan, what we CHANGED (from -> to), what we REJECTED, each with why. The user explicitly wants to know how much of Codex's plan we incorporated and why.
- Note divergences_from_prior_dossier (our own earlier DocketClock dossier).
- mvp_boundary must be ruthless: federal-only, smallest credible v1, named first customer.
- build_sequence = ordered milestones.
- The architecture must leave a clean SUBSTRATE boundary so Watershed Watch (a vertical wedge) can sit on top — but do not let that gold-plate the MVP.

Proposals + critiques JSON:
${JSON.stringify(dcClean)}`,
  { label: 'dc-synthesis', phase: 'DocketClock synthesis', schema: DC_SYNTH },
)

// ---------- PART B: Watershed Watch ----------
phase('Watershed fit')
const fit = await agent(
  `${FOUNDATION}

We have now synthesized the DocketClock architecture (below). Decide HONESTLY whether Watershed Watch should build on DocketClock at all — "no" or "yes-partially" are fully acceptable answers if that is the truth. Specifically resolve:
1. builds_on_docketclock: yes-fully / yes-partially / no, with rationale.
2. is_land_use_wedge: is Watershed Watch a genuine example of the "land-use/vertical wedge on top of DocketClock" pattern? (Our own dossier flags the risk that it is "just DocketClock + a Waterkeeper skin" — confront that directly.)
3. layer_boundary: what DocketClock provides vs what Watershed Watch must add itself (geo-scoping to a HUC basin, the EPA EIS source, the action/receipt loop, coalition channel, member-reported local layer).
4. requirements_on_docketclock: what Watershed Watch NEEDS DocketClock to expose (e.g. geo/agency tags, per-document windows, webhook filters) — i.e. does the vertical's existence change the substrate's design?
5. counterfactual_if_standalone: when/why would building Watershed Watch standalone (not on DocketClock) be the better call?
Remember: the user has real design-partner access in this persona, so adoption is more reachable than usual.

DocketClock architecture JSON:
${JSON.stringify(dcArch)}`,
  { label: 'ww-fit', phase: 'Watershed fit', schema: FIT },
)

phase('Watershed design')
const B_STANCES = [
  { key: 'thin', brief: 'THIN CLIENT ON DOCKETCLOCK. Watershed Watch is mostly a geo-filter + plain-language brief + action/receipt UI + coalition channel ON TOP of DocketClock\'s feed, with minimal new backend. Push as much as possible down into DocketClock (treat it as the data plane). Optimize for shipping with one design partner fast. Be honest about what DocketClock cannot give you (EPA EIS geo, basin scoping, local long tail) and how thin you can really be.' },
  { key: 'thick', brief: 'THICK VERTICAL WITH SELECTIVE REUSE. Watershed Watch owns the EPA EIS ingestion, HUC/WBD geo-scoping, basin relevance classification, the member-reported local layer, and the action/receipt loop as ITS OWN service; DocketClock is one normalized source among several (federal reconciliation), not the whole backend. Optimize for the vertical earning its own defensible IP (tuned basin relevance + coalition channel + honest receipts) so it is NOT just a skin.' },
]

const wwProposePrompt = (s) => `${FOUNDATION}

DocketClock architecture (synthesized) and the fit-analysis are below. Propose the Watershed Watch architecture from THIS stance:
${s.brief}

Be concrete: USGS WBD/HUC via The National Map ArcGIS REST for geo; EPA EIS (45/30 clock) + Regulations.gov + Federal Register + Open States as sources; RuleBox-style basin relevance; the monitor->act->see-impact loop with honest procedural receipts (no causal claims); clearly-labeled coverage tiers (Tier-1 automated reliable / Tier-2 community-reported / Tier-3 best-effort). Respect what the fit-analysis says DocketClock provides vs what Watershed Watch must add. First design partner: a Waterkeeper/Chesapeake/Baykeeper-type coalition the user can actually reach.

DocketClock arch JSON:
${JSON.stringify(dcArch)}

Fit-analysis JSON:
${JSON.stringify(fit)}`

const bResults = await pipeline(
  B_STANCES,
  (s) => agent(wwProposePrompt(s), { label: `ww-propose:${s.key}`, phase: 'Watershed design', model: 'sonnet', schema: WW_PROPOSAL }),
  (prop, s) => prop ? agent(
    `${FOUNDATION}

Adversarially review this Watershed Watch architecture (stance: ${s.key}). Be a skeptical engineer AND a skeptical watershed-group director who will actually use it. Where does basin relevance classification fail (the BLM extension/correction trap, false positives)? Is the value real vs "DocketClock + a skin"? Will a volunteer group adopt and retain it given Tier-1 can't surface the local floodplain fights they care most about? Is the action/receipt loop honest and credible? Score 1-10. Proposal JSON:
${JSON.stringify(prop)}`,
    { label: `ww-critique:${s.key}`, phase: 'Watershed review', model: 'sonnet', schema: CRITIQUE }
  ).then((c) => ({ stance: s.key, proposal: prop, critique: c })) : null,
)

const wwClean = bResults.filter(Boolean)
log(`Watershed: ${wwClean.length}/2 proposals reviewed`)

phase('Watershed synthesis')
const wwArch = await agent(
  `${FOUNDATION}

You are the LEAD ARCHITECT. Two Watershed Watch architectures (thin-client-on-DocketClock vs thick-vertical) were proposed and critiqued, and we have a fit-analysis. Synthesize the SINGLE best Watershed Watch architecture, taking the right layer boundary with DocketClock (per the fit-analysis) and answering the "just a skin" critique head-on.

Hard requirements:
- relationship_to_docketclock must be explicit and concrete (what it consumes from DocketClock, what it owns).
- geo_scoping: USGS WBD/HUC via The National Map ArcGIS REST, with real gotchas.
- action_loop: the full monitor->act->see-impact with HONEST procedural receipts only.
- coverage_tiers: clearly labeled, no fake coverage promises.
- mvp_boundary: ruthless; named first design partner the user can reach; defer NoticeNail + Pol.is.
- build_sequence ordered.
- Make the case (or honestly fail to) that this earns distribution/funding the bare registry cannot.

DocketClock arch JSON:
${JSON.stringify(dcArch)}

Fit-analysis JSON:
${JSON.stringify(fit)}

Watershed proposals + critiques JSON:
${JSON.stringify(wwClean)}`,
  { label: 'ww-synthesis', phase: 'Watershed synthesis', schema: WW_SYNTH },
)

return {
  docketclock: { architecture: dcArch, proposals: dcClean },
  watershed: { fit, architecture: wwArch, proposals: wwClean },
}
