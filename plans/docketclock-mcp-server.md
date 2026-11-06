# DocketClock MCP server — reconciled deadlines for agents

> Status: **APPROVED APPROACH**, 2026-10-20; Phase 0 implementation authorized by the operator.
> Originally specified 2026-10-19; revised 2026-10-20 after cross-provider review.
> Baseline inspected: `24a4fce`, contracts **0.11.0**, reconciler `reconcile-v2.3`.
> Rebased 2026-11-06 onto `59e5968`, contracts **0.12.0**, reconciler `reconcile-v2.4`. The ADR moved
> from 0017 to 0018 because multi-deadline notices took that number.
> Decision: [ADR 0018](../docs/decisions/0018-docketclock-mcp-server.md).
> No server, contract changes, infrastructure, client registrations or deployments are created
> by this document. Numbers below are proposed budgets and acceptance thresholds, not measurements.
> Authorization: begin the gated implementation, including the lightweight-AS spike after
> Phase 0 passes. Commit/push/PR actions still require a separate user request in this thread.
> Phase 0's measured operator/client gate is not passed merely by approving the approach.

## 1. Commitment, users and jobs

The operator is the named initial AI-agent buyer and pilot owner for this slice: DocketClock
through their Claude and Codex clients. This request satisfies the architectural commitment to
specify the deferred MCP seam; it does not claim a paying external customer or authorize a
production launch. Phase 0 must demonstrate value before the remote service is built.

The product is reconciliation, confidence and provenance. It answers “what can I responsibly
say about this participation window?” using existing observations and projections. It is not
a replacement Federal Register search engine, an agent that adjudicates deadlines, or a way
to submit comments.

Three callers:

- **End user through an agent:** asks “which EPA comment periods close this month, how certain
  are those dates, and where do I submit?” Needs a small, cited answer with uncertainty visible.
- **Agent builder:** needs stable OCD-IDs, bounded schemas, predictable pagination and OAuth
  interoperability, without scraping notice HTML or reverse-engineering review authority.
- **Operator:** inspects the same public answers and evidence from their preferred client.
  Being the operator grants no additional MCP authority; review writes remain in the CLI.

Acceptance questions (each becomes a Phase 0 evaluation case):

1. Which stored EPA comment windows are open and scheduled to close in an explicit date range?
2. Which matching windows have unknown/disputed dates and therefore cannot safely be put on
   that closing calendar?
3. What is the current operative close for this FR notice or OCD-ID, including its original
   display wording, version, status and official source?
4. Why is its confidence high, medium, low, conflicting, stale or unknown?
5. What do the disagreeing sources say, and is this a cross-source or cross-window conflict?
6. Has the close changed, and which observation references support the recorded changes?
7. Did a human or an autonomous agent resolve it; is that verdict still honored, superseded,
   or an escalation that asserts no deadline?
8. Where does the stored submission link lead, and what is unknown about submission channels?
9. For a docket, RIN or title phrase, which reconciled windows and live conflicts deserve
   inspection, including amendments stored under another OCD-ID?

“This month” is resolved by the calling agent into explicit boundaries and a timezone, shown
to the user. The server never infers a date range from natural-language intent.

## 2. Baseline and required read-model work

Read in order: `AGENTS.md`, `docs/architecture/docketclock.md`, contracts, API, ADRs
0001/0008/0009/0013/0015, and `plans/review-autopilot.md`. The architecture's historical
managed-Postgres, Node 22/PG16 and API-billed Claude sketches are superseded by the repository
conventions and this request. Use Node 24, pinned PG18, Helm, Argo, Vault/ESO and the Mini.
No new LLM call is part of this server, including advisory classification.

### What exists

- `apps/docketclock/src/api/queries.ts`: contract-validated `listWindows`, `getWindow`,
  `getWindowObservations`, `listConflicts`, independent of HTTP.
- Windows filter by confidence, status, exact docket membership and strict `<` / `>` UTC
  closing bounds. Default list limit 50, cap 200; limit/offset/total envelopes.
- Conflicts are **live only**, `resolved_at IS NULL`, matched on either OCD-ID side.
  `ConflictRecord` itself has flags but **no confidence field**.
- REST `/v1/windows`, `/v1/windows/*`, `/v1/conflicts`; API-key authentication fails closed.
  `api/envelope.ts` stamps the shared `DISCLAIMER`, `API_VERSION` and request ID.
- `ParticipationWindow` has no title or agency field. It includes RIN, docket IDs, status,
  both raw close fields, resolved close/display, nullable submission/GovInfo links, version,
  provenance, observation references and change history.
- Review authority lives in `HumanReviewVerdict.reviewer`; executor is `operator`.
  `selectHonoredVerdict` in `reconcile/reconcile.ts` owns honoring semantics. `escalate`
  is freshness-only, is absent from current observation IDs and stamps neither resolution flag.
- Existing Prometheus registry, Pino logs, Alloy/Loki, provisioned Grafana alerts and ntfy.
  Loki currently retains 72 hours; Prometheus retains seven days.

### Gaps that are prerequisites, not assumed endpoints

1. **Agency/title/keyword/RIN filters:** agency and FTS are explicitly deferred in the API;
   RIN exists in the projection but is not a query filter. Add a shared delivery query module
   consumed by REST and MCP. Start with a SQL view joining each window to its latest stored,
   valid FR metadata for title/agency and the projected RIN/docket fields. Parse stored
   payloads through the existing source extraction conventions; record metadata observation
   IDs and missing fields. No docket-prefix inference of agency. A latest malformed payload
   means missing metadata, not a silent fallback to an older “current” title.
2. **Search:** Phase 0 first uses bounded title/identifier matching over that view; measure
   before adding a persisted tsvector/GIN index. If needed, that index is a rebuildable
   Postgres delivery projection, shared with REST, never a second deadline store. No search
   engine, full-document ingestion or LLM query parser.
3. **Evidence:** current `getWindowObservations` is unbounded and selects only
   `observations.ocd_id`. It does not follow `observation_targets`, current/provenance/history
   references or both conflict sides. Add bounded reads that preserve those relationship
   types and deduplicate by observation ID. A target association must not be misrepresented
   as evidence the reconciler actually used. Current `loadObservations` also uses primary
   OCD-ID only: honor verdicts using that exact engine chain, not the expanded evidence set.
4. **Explanation:** `Provenance` is only two ID arrays; a structured rules-fired/freshness
   explanation is still deferred. Do not fabricate it from confidence. Initially explain
   carried fields, source values, flags and verdicts; return `not_recorded` for a causal trace
   that was not stored. Existing DB timestamps/version stamps may be exposed through a
   reviewed DTO; they are not already contract fields.
5. **Bounded serialization and consistency:** REST detail attaches all raw observations.
   Do not proxy that response wholesale into agent context. Validate full source records,
   then produce the explicitly bounded DTOs below. Existing list count and rows use separate
   statements; add a shared repeatable-read transaction for each multi-query answer.
6. **Release boundary:** today `OcdId` is federal-only; future state additions must not widen
   MCP accidentally. Every MCP read (including search, counts, citations, both conflict sides
   and evidence references) uses a federal-only public read boundary before pagination.
   ADR 0013's state gates are necessary but not sufficient to add state MCP support: v1 still
   excludes it, and a later explicit contract/release decision is required.

Do not fix unrelated API behavior as part of the prototype. New filters/read DTOs should be
shared modules with REST parity probes; existing REST defaults and envelopes stay compatible.
The `.innerType().extend(...)` idiom in current REST detail loses Zod refinements at that
schema boundary; copy no such pattern without reapplying invariants.

## 3. Deployment and ownership

Recommend a **separate `docketclock-mcp` Deployment in `charts/docketclock`**, using the same
app image with an `src/mcp/run-http.ts` entrypoint and shared delivery modules. One replica
initially; internal Service; only MCP and discovery paths exposed publicly. A second small
`docketclock-auth` process hosts the authorization library if the local-AS spike passes.
The AS is a separate security role even if packaged in the same image.

An `/mcp` route on the existing API would save one Node process and pool. It also puts public
OAuth/transport parsing and agent-generated load in the API-key service's failure domain,
and risks inheriting its broader DB credentials/secrets. Separate processes make read grants,
rate limits, rollback and the absence of poller/review credentials testable. Reconsider
co-location only if measured RSS exceeds the budget, with the same role separation.

MCP is a resource server. It never authenticates an OAuth bearer token by calling the REST API
with a shared operator key. It never imports review CLI commands, calls reconciliation
persistence or initiates source refreshes. Pure, shared honoring logic may be used for
explanation; it does not rederive or persist the published deadline.

Proposed implementation ownership:

| Owner                           | Files/seam                                                                             |
| ------------------------------- | -------------------------------------------------------------------------------------- |
| Contract-keeper                 | All `packages/contracts` changes, schema/probe fixtures, minor version and freeze note |
| Delivery builder                | Shared queries/DTO mapping, metadata view, bounded evidence, REST parity tests         |
| MCP builder                     | `apps/docketclock/src/mcp/`, stdio/HTTP adapters, text renderer, MCP conformance tests |
| Auth/platform builder           | AS adapter/login/consent, DB roles, Helm/ESO, tunnel and observability                 |
| Independent reviewer/integrator | Trust invariants, OAuth attack cases, client probes and integrated gates               |

These are implementation roles, not work dispatched or authorized by this planning document.

## 4. Proposed contracts and six v1 tools

Submit a change request to the contract-keeper for the **next free minor version**.
0.12.0 shipped with ADR 0016, and `plans/review-learning-loop.md` PR-L1 also proposes a
minor; the keeper assigns the MCP version after resolving that sequencing. During Phase 0, candidate DTOs can live in the app
under keeper review; freeze them in the shared package only at the Phase 0 go gate. Remove
those temporary definitions when adopting the exports; no production schema fork.
Additive only: retain existing enums, ID scheme, `ParticipationWindow`, `Observation`,
`ConflictRecord` and REST envelopes; keep `API_VERSION = "v1"`. Add MCP input/output DTOs,
bounded evidence schemas, transport-neutral delivery metadata and their JSON Schemas. Replace
the MCP deferred-header note with the named commitment and freeze the new seam. A package
minor version, the MCP tool schema version (`mcp-v1`), and negotiated MCP protocol revision
are three different things.

The sketches below specify the proposed Zod shapes, not implemented exports. Use the existing
`Confidence`, `ConflictFlag`, `WindowStatus`, `WindowType`, `OcdId`, `Pagination`,
`ChangeHistoryEntry`, `PayloadHash`, `HumanReviewVerdict` and envelope factories. Strict input
objects reject unsupported fields; do not silently ignore a caller's filter.

### Input schemas

```ts
const Page = z.object({
  limit: z.number().int().min(1).max(20).default(10),
  offset: z.number().int().min(0).max(1000).default(0),
});
const Instant = z.string().datetime({ offset: true });
const IdInput = z.object({ id: z.string().min(1).max(256) }).strict();
// id: validate as OcdId OR a federal FR document number.
// Validate FR shorthand with makeOcdId({ frDocNum }), then look up the existing window.
// Never mint/rekey a stored window or concatenate arbitrary paths in the read surface.

const ListWindowsInput = Page.extend({
  agency: z.string().min(1).max(120).optional(), // exact FR agency slug
  docket_id: z.string().min(1).max(160).optional(),
  rin: z.string().min(1).max(80).optional(),
  keyword: z.string().min(1).max(200).optional(),
  status: WindowStatus.optional(),
  confidence: Confidence.optional(),
  window_type: WindowType.default("comment"),
  closes_after: Instant.optional(), // exclusive, matching REST
  closes_before: Instant.optional(), // exclusive, matching REST
  close_mode: z.enum(["any", "known", "unknown"]).default("any"),
}).strict();
// refine: after < before; unknown cannot combine with closing bounds.

const SearchInput = z
  .object({
    query: z.string().trim().min(1).max(500),
  })
  .strict();
const FetchInput = IdInput;
const ListConflictsInput = Page.extend({
  ocd_id: OcdId.optional(), // either side
}).strict();
const ExplainWindowInput = Page.extend({
  id: z.string().min(1).max(256),
  section: z
    .enum(["summary", "observations", "verdicts", "history", "references"])
    .default("summary"),
  expected_version: z.number().int().nonnegative().optional(),
  evidence_as_of: Instant.optional(),
})
  .strict()
  .superRefine((input, ctx) => {
    if (
      input.offset > 0 &&
      (input.expected_version === undefined ||
        input.evidence_as_of === undefined)
    ) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Follow-up pages require expected_version and evidence_as_of",
      });
    }
    if (input.section === "summary" && input.offset !== 0) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "The summary section has no offset pagination",
      });
    }
  });
const SubmissionInfoInput = IdInput;
```

For FR shorthand, query exact `fr_document_number` and return the stored OCD-ID, including a
stable `regs:` fallback ID if it was minted before an FR identity was known. Zero matches is
`not_found`; more than one is `ambiguous_identifier` with bounded candidate OCD-IDs, never
an arbitrary first match. Exact OCD-ID input always looks up that identity unchanged.

`list_windows` filters are conjunctive. `status=open` means the stored enum, not “all actionable”
or “accepts submissions right now.” Agents can explicitly query `reopened`/`extended`; no
default confidence filter drops uncertain windows. `close_mode=unknown` selects null operative
closes, not `confidence=unknown` alone (conflicting windows can also have null closes).
Any closing bound excludes null closes and returns the companion count described below.
Timestamp strings require offsets; date-only input fails clearly. The exclusive bounds are
shown in `applied_filters`; the agent must not quietly call them inclusive.

### Bounded shared output schemas

Proposed schema composition:

```ts
const Trust = z.object({
  confidence: Confidence,
  conflict_flags: z.array(ConflictFlag),
});
const DeliveryMeta = Trust.extend({
  tool_schema_version: z.literal("mcp-v1"),
  read_at: Instant,
  confidence_scope: z.enum(["window", "collection_no_aggregate", "no_record"]),
  warnings: z.array(z.string().max(300)).max(10),
});
const Coverage = z.object({
  jurisdiction: z.literal("federal"),
  corpus: z.literal("stored_docketclock_windows"),
  completeness: z.literal("not_asserted"),
  metadata_missing_count: z.number().int().nonnegative(),
  unknown_close_count: z.number().int().nonnegative(),
  // Count of other filters' matches with a null operative close, ignoring date bounds.
  disputed_close_count: z.number().int().nonnegative(),
  // Non-null conflicting closes matching all applied filters, including date bounds.
  unresolved_close_followup: z.boolean(),
});
const Excerpt = z.object({
  text: z.string().max(2000).nullable(),
  truncated: z.boolean(),
  original_characters: z.number().int().nonnegative(),
});
const PageExcerpt = Excerpt.extend({
  text: z.string().max(400).nullable(),
});
const EvidenceSummary = z.object({
  observation_id: z.string(),
  ocd_id: OcdId,
  source: ObservationFields.shape.source,
  payload_hash: PayloadHash,
  fetched_at: ObservationFields.shape.fetched_at,
  parser_version: ObservationFields.shape.parser_version,
  raw_dates_excerpt: PageExcerpt,
  source_url: z.string().url().nullable(),
  relationship: z.array(
    z.enum([
      "primary",
      "target",
      "current",
      "agreeing",
      "conflicting",
      "history",
      "conflict_side",
    ]),
  ),
});
// Parsed from the canonical Observation first. This is a distinct public summary, never a
// truncated object pretending to be an intact Observation; arbitrary raw is excluded.
```

`WindowSummary` is a proposed contract-owned bounded derivation of `ParticipationWindow`:
all its fields **except** `change_history`, `current_observation_ids` and `provenance`. Those
three move to paginated explanation sections. Add `title: PageExcerpt`, `agency_slugs: string[]`
(max 20), `metadata_observation_ids: string[]` (max 2), and
`evidence_counts: {current, agreeing, conflicting, history}` (nonnegative integers).
Validate the full canonical window before mapping. Define the output Zod object from its
field schemas, reapplying the close/confidence and timezone refinements; do not rely on
JSON Schema to express Zod cross-field checks. The keeper may factor shared refinements
without changing the acceptance of any existing serialized window.

Full unbounded identifier/tag arrays or excessively long canonical scalar fields can still
exceed the byte budget: never truncate a deadline, conflict flag, ID or display string.
Return `result_too_large` with an official citation and a narrower evidence operation when
an indivisible record exceeds the cap. Measure such cases in Phase 0 rather than assuming
the summary is always small.

`VerdictSummary` derives from validated `HumanReviewVerdict` and adds its observation ID,
hash and fetched timestamp. It carries `kind`, optional `pinned_close_date`, `reviewer`,
`note: PageExcerpt`, `operator: string | null`, `operator_redacted: boolean`,
`reviewed_payload_hash_count`, `honoring: honored | superseded | not_honored | unknown`,
and `effect: derives | parked | none | unknown`.
`honored` means selected by the engine's pure honoring rule, not necessarily a resolution:
an honored `escalate` has `effect=parked` and asserts nothing; an honored non-escalate has
`effect=derives`. `superseded` means a later verdict in the engine's timestamp/ID ordering
exists; `not_honored` means the latest verdict was invalidated by source evidence. Both have
`effect=none`. Missing/unreadable chain evidence yields `honoring=unknown, effect=unknown`.
The references section pages the reviewed hashes. Public executor labels require an
operator-approved alias; never expose login/email details by default. Redacted notes are
marked in a separate `redacted: boolean`; their exact original payload hash is retained.
The meaning of `reviewer` is never redacted or guessed from `operator`.

`ExplainSummary` carries `window: WindowSummary`, stored source close values, provenance
counts, `honored_verdict: VerdictSummary | null`, `honoring_as_of: Instant`,
`projection_alignment: confirmed | unknown`, `causal_trace: not_recorded`, and
`explanation_limits: string[]`. Honoring is computed by the shared pure selector on its
complete engine chain. If the required chain cannot be read inside the time/size budget,
return `honoring=unknown` / a warning rather than evaluate a truncated chain. This computed
honoring fact is separate from the stored projection's resolution flags: newer observations
can exist before the next reconciliation. `projection_alignment` refers only to review
overlay alignment, not proof of the entire deadline derivation. It is `confirmed` only when
the stored `reconciler_version` matches the selector version, `derived_at` is at least the
latest engine-chain `fetched_at`, and either (a) the honored non-escalate observation ID is
in `current_observation_ids` with the reviewer-matched resolution flag and not the other
resolution flag, or (b) there is no honored non-escalate overlay and neither resolution flag
is present. Otherwise return `unknown`; never choose a replacement close. These two existing
operational DB columns enter the proposed DTO as nullable `derived_at: Instant` and
`reconciler_version: string`; unavailable values cannot establish alignment.

### Tool catalog and output mapping

All six tools declare read-only, non-destructive, idempotent annotations using the pinned
SDK's supported names (VERIFY-P). These are client hints, not an authorization mechanism.

| Tool                  | Output Zod composition                                                                                                                                             | Purpose and limits                                                                                                                                                              |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `list_windows`        | `apiListEnvelope(WindowSummary).extend({delivery: DeliveryMeta, coverage: Coverage, applied_filters: ListWindowsInput, next_offset: z.number().int().nullable()})` | Structured exploration; default 10/max 20, max offset 1000. Counts are for stored data, never total federal coverage.                                                           |
| `search`              | `z.object({results: z.array(SearchHit).max(10), meta: SearchMeta}).merge(EnvelopeMeta)`                                                                            | Research-client facade; deterministic title/identifier search over the same query layer. Exact shape details below.                                                             |
| `fetch`               | `z.object({id: OcdId, title: z.string(), text: z.string(), url: z.string().url(), metadata: FetchMeta}).merge(EnvelopeMeta)`                                       | Get a window by OCD-ID or FR shorthand; returns normalized OCD-ID. `FetchMeta = {data: WindowSummary, delivery: DeliveryMeta}`. Text includes submission and evidence pointers. |
| `list_conflicts`      | `apiListEnvelope(ConflictEvidence).extend({delivery: DeliveryMeta, next_offset: z.number().int().nullable()})`                                                     | Live feed only. `ConflictEvidence = {record: ConflictRecord, side_a: WindowSummary, side_b: WindowSummary.nullable(), evidence_a: EvidenceResult, evidence_b: EvidenceResult}`. |
| `explain_window`      | `apiItemEnvelope(ExplainSection).extend({delivery: DeliveryMeta, evidence_as_of: Instant})`                                                                        | `ExplainSection` is a discriminated union on `section`, described below. No raw payload export or invented rules trace.                                                         |
| `get_submission_info` | `apiItemEnvelope(SubmissionInfo).extend({delivery: DeliveryMeta})`                                                                                                 | `SubmissionInfo = {window: WindowSummary, submission_url: nullable URL, govinfo_url: nullable URL, availability: stored_link                                                    | unavailable, channel_details: not_modeled, checked_live: false}`. No form filling or URL fetch. |

`SearchHit = {id: OcdId, title: string, url: URL, trust: Trust}`.
`SearchMeta = {delivery: DeliveryMeta, coverage: Coverage, pagination: Pagination,
next_query: string | null}`. Both facades carry the exact `EnvelopeMeta` constants/ID at
the root. These names are proposed contract exports. Search/fetch are adapters over the same
DTOs, not independent sources. Mandatory safety metadata extends the research shapes;
acceptance of those additive fields must pass a real research-client test before claiming
ChatGPT deep-research support (VERIFY-C). Do not remove disclaimer/confidence to pass that test.

`EvidenceResult = z.union([EvidenceSummary, z.object({missing: z.literal(true),
observation_id: z.string(), reason: z.enum(["not_found", "unreadable"])})])`.
Refine `ConflictEvidence` so cross-window scope requires `side_b` with the matching distinct
OCD-ID, and cross-source scope requires `side_b=null`; each side's evidence identity must
match its record reference. Missing evidence retains the conflict and both window identities,
with an explicit per-item warning, so one broken reference does not make an entire page
unreadable. Invalid canonical windows/conflict records still fail closed as data errors.

`ExplainSection` always includes `window: WindowSummary` and one of:

- `section=summary`: `{summary: ExplainSummary}`; no list pagination.
- `section=observations`: `{items: EvidenceSummary[], pagination: Pagination, next_offset}`.
- `section=verdicts`: `{items: VerdictSummary[], pagination: Pagination, next_offset}`.
- `section=history`: `{items: ChangeHistoryEntry[], pagination: Pagination, next_offset}`.
- `section=references`: `{items: Reference[], pagination: Pagination, next_offset}`, where
  `Reference = {kind: current | agreeing | conflicting | reviewed_hash,
observation_id: string | null, payload_hash: PayloadHash | null,
verdict_observation_id: string | null}` with a refinement enforcing the appropriate identity.

History is the existing sequence of prior closes and observation refs; it does not promise
historical display wording or every past full window snapshot. Missing referenced evidence
is reported explicitly. A list returns the typed missing-evidence member above;
`explain_window` returns `evidence_unavailable` when required evidence for that requested
explanation cannot be recovered, retaining a safe window summary when it fits.
References are evidence handles,
not new public window IDs. Scope every handle to the requested federal window relationship;
there is no arbitrary “read observation UUID” tool.

### Research facade semantics

Keep tool names `search` and `fetch`, because the research integration uses those names;
they are not a universal Claude/Codex requirement. [OpenAI's MCP documentation](https://developers.openai.com/api/docs/mcp)
was checked by the research child on 2026-10-19; exact runtime compatibility remains VERIFY-C.
`search` consumes `{query}` and `fetch` consumes `{id}`. Outputs are supplied both as
`structuredContent` and one JSON-encoded text content block, with the root `disclaimer`
serialized first. Do not add a second prose block. Tool `outputSchema` describes
the full result, including error alternatives; no schema may claim only successful responses.

`search.query` is a documented deterministic grammar, not natural-language interpretation:
plain words match title/identifiers; optional `agency:`, `docket:`, `rin:`, `status:`,
`confidence:`, `type:`, `after:`, `before:`, `close:`, `offset:` map exactly to `list_windows`.
Quoted phrases are supported; unknown operators or invalid values fail. Defaults match
`list_windows`, page size fixed at 10. Emit `next_query` with the same normalized filters and
next offset. A caller supplying “EPA this month” as plain words gets lexical results, not an
inferred agency/date query; the tool description teaches the conversion.

Prefer a stored safe GovInfo URL for citations, then a validated official FR/Regs document
URL derived from observed identity (never an invented submission link). Search hits require a
usable citation URL; rows lacking one remain accessible through `list_windows`. A `search` page containing one
returns `citation_unavailable` rather than dropping it, because a dropped row would falsify totals. `fetch` with no usable URL returns `citation_unavailable` with its enveloped
window metadata. Do not invent a public DocketClock HTML page or cite the authenticated MCP
endpoint as though it were a readable notice.

### Confidence, abstention, disclaimer and errors

- Every data answer contains exact `DISCLAIMER`, `API_VERSION`, server-minted `request_id`,
  confidence and flags. Per-window trust is copied byte-for-byte from the validated projection.
  Collection metadata uses `confidence=unknown`, `confidence_scope=collection_no_aggregate`,
  and the union of returned flags: that is explicitly **no aggregate confidence rating**.
  Empty collections retain the same metadata and `total=0`.
- High/medium/low/stale require a non-null close. Unknown forces null. Conflicting may retain
  a non-null disputed value: preserve it and label it disputed, never present it as settled.
  Preserve `resolved_close_display`, including channel/timezone wording. Never raise
  confidence, turn stale into unknown, or erase `tz_normalization_only`, `llm_corroborated`,
  `human_resolved` or `agent_resolved`.
- `delivery.warnings` and the text renderer explicitly label unknown/conflicting/stale
  results as requiring verification. These are successful MCP results (`isError=false`).
  A null submission URL is likewise a successful `availability=unavailable`.
- Date-filtered answers include `unknown_close_count` over matching non-date predicates and
  `unresolved_close_followup=true` when nonzero. The rendered answer requests a companion
  `close_mode=unknown` query. Those rows cannot be claimed to close inside the requested range.
  This count ignores `close_mode` too, so a `known` query still warns about omitted nulls.
  `disputed_close_count` separately counts non-null `confidence=conflicting` rows satisfying
  every applied filter including the date bounds. Job 2 combines the null-close companion
  query with `confidence=conflicting` under the original bounds; a null-only query is insufficient.
- `metadata_missing_count` counts rows matching status/confidence/type/docket/RIN/date/close-mode
  predicates, before agency/keyword predicates, whose metadata lacks title or agency. It is
  labeled a broader candidate-population count, not a count of missing EPA matches.
  Agency vocabulary is FR `agencies[].slug`; Regs-only windows have no FR agency metadata
  in v1 and count as missing even if the raw payload has a Regs `agencyId`. Do not equate
  those vocabularies without a reviewed mapping and provenance.
- Tool failures use a proposed `McpToolError = EnvelopeMeta + Trust +
{error: {code, message, retryable, retry_after_seconds?: number},
confidence_scope: no_record | window, window?: WindowSummary}`.
  Codes: `invalid_input`, `not_found`, `ambiguous_identifier`, `unsupported_filter`, `stale_read`,
  `result_too_large`, `evidence_unavailable`, `citation_unavailable`, `rate_limited`,
  `temporarily_unavailable`, `internal_error`. No record means `confidence=unknown`,
  `conflict_flags=[]`; an attached window keeps its own trust. No stack traces or reflected secrets.
- Tool execution failures use `isError=true`. Unknown tool/malformed JSON-RPC and transport
  authentication errors use the protocol's own error layer (VERIFY-P), not fake tool success.
  Include the disclaimer in application error content where permitted; do not corrupt OAuth
  discovery, JWKS, challenge headers, protocol errors or Prometheus with REST wrappers.

All tools use one JSON text block mirroring structured content, serializing the exact root
disclaimer first and trust fields before evidence where the schema permits. JSON object order
is not an enforcement mechanism. `fetch.text` is the deterministic human-readable summary:
disclaimer, status/close/confidence/flags, version, source timestamps, citations and submission
link, then untrusted excerpts. Search hits also put a short confidence label in the title so
clients that display only titles keep a warning. Phase 0 measures this rendering; it must not
grow a third copy outside the total byte budget. Instructions ask agents to carry the
disclaimer and uncertainty into their user answer.
The server cannot force a downstream model or UI to do so: measure actual rendered answers
in the client gate and withhold compatibility claims when the client drops material caveats.

### Pagination and consistency

Use the shared `Pagination` shape. Per response, count/rows/window/evidence use one short
read-only repeatable-read transaction. A timestamp is an observation boundary, not a magical
database snapshot. Separate offset pages are **not** a stable snapshot across reconciliations.
Expose `read_at`; clients deduplicate OCD-IDs and must restart on changed versions when comparing
pages. Do not promise exhaustive bulk export.

Order windows by close ascending/nulls last, OCD-ID; conflicts by detected time descending,
then both OCD-IDs, both observation IDs and scope (the current order alone has ties);
observations/verdicts by fetched time then ID descending; history by version; references by
kind then ID/hash. Page limits and actual returned counts must agree. When the byte cap
reduces a page, `next_offset = offset + returned_count`, never the originally requested limit.
If zero items fit, return `result_too_large`, not an infinite empty-page loop.

For explanation, return `evidence_as_of` on page one, constrain subsequent evidence reads to
that boundary, and require `expected_version` on follow-up pages. Changed window version
returns `stale_read` and asks for a restart. Same-version late inserts are still possible:
the response disclaims a historical transaction snapshot; retries deduplicate observation IDs.
Do not hold database transactions open between client calls.

### Resources, prompts and exclusions

Tools carry all essentials because client support varies. Optional static resources for the
disclaimer, confidence glossary and query grammar may be added only after a client demonstrates
use; they are not required to interpret a result. No prompts in v1: a curated prompt would not
enforce trust and would add a second client-dependent interface.

Out of scope: review/verdict writes, adjudication, source refresh, subscriptions/webhooks,
comment submission, agent scheduling, state data, arbitrary URLs/SQL, full raw observation
export, bulk export and cached conversational answers. No LLM SDK/key is mounted in MCP/auth.

## 5. Transport and OAuth

### Evidence status and version choice

The primary had no network access. A bounded Claude Sonnet 5.5 research child checked official
pages on **2026-10-19**. These are research findings, not interoperability tests. Every external
requirement below is tagged by a gate:

- **VERIFY-P:** re-read and pin current protocol/RFC/SDK docs at implementation, save the
  selected dated revision and exact SDK version, then run protocol tests.
- **VERIFY-C:** test the actual installed client/version/account and record behavior.
- **VERIFY-V:** verify vendor configuration, support, limits and pricing before adopting it.

The child reports a **2026-07-28** MCP revision whose Streamable HTTP is request-scoped POST,
without the older initialization/session/GET stream model. Its linked authorization overview
is a **draft** URL; do not treat the draft and a dated revision as interchangeable.
[Dated transport](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http),
[registration](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/client-registration),
[AS discovery](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/authorization-server-discovery),
[security](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/security-considerations),
[draft authorization overview](https://modelcontextprotocol.io/specification/draft/basic/authorization).
The Fable review independently fetched the dated transport/registration pages and Anthropic's
connector-authentication page on 2026-10-20. They still require implementation-time VERIFY-P/C:
documented availability is not evidence that the chosen SDK or client implements that revision.
Anthropic's page links the older 2025-11-25 authorization spec; test that revision first as
a compatibility candidate, but do not infer the client's wire protocol from that link.

Therefore do **not** hardcode an old `initialize`/SSE-session server or blindly target the newest
revision. Phase 0 records CLI revisions; Phase 1 records claude.ai's revision and pins a tested
SDK. Prefer stateless request handling. Support only the minimal tested revision set using the
SDK's supported negotiation, with older initialization compatibility if required. No custom
protocol fork or silent fallback to unauthenticated legacy SSE. If a supported older mode needs
sessions, bind them to subject/client, validate auth on every request, cap/expire them, and never
use session IDs as authentication.

VERIFY-P includes version/header/body agreement, supported methods (including GET/DELETE
differences by revision), JSON/SSE response negotiation, origin checks and invalid-version
errors. Research reports newer `Mcp-Method`/`Mcp-Name` headers; emit/require them only per the
selected revision. Validate present Origin against exact allowed origins; absent Origin is
normal for native/server clients and does not bypass bearer validation. Limit trusted proxy
hops and validate Host; use configured public URLs, never attacker-supplied forwarded headers.

### Resource-server contract

Illustrative hostnames, **not provisioned**:

```text
Canonical resource:  https://mcp.<owned-domain>/mcp
Resource metadata:   https://mcp.<owned-domain>/.well-known/oauth-protected-resource/mcp
Issuer:              https://auth.<owned-domain>
AS discovery:        https://auth.<owned-domain>/.well-known/oauth-authorization-server
```

OAuth 2.1 authorization-code flow with PKCE **S256**, including public/native clients, is the
design requirement; exact current OAuth draft and MCP binding are VERIFY-P. No implicit or
password grant, and no shared bearer API key as the remote-user experience.

- Publish unauthenticated RFC 9728 protected-resource metadata, advertising the canonical
  resource, one selected issuer and `docketclock:read`. A 401 challenge includes the metadata
  URL. RFC 8414 or OIDC AS discovery advertises endpoints, PKCE, grants, supported client
  authentication, registration capabilities and JWKS. Paths/metadata keys are VERIFY-P.
- Require RFC 8707 `resource` on authorization and token exchanges; the access token audience
  must bind to the exact canonical resource. Check signature, allowed algorithm, issuer,
  audience, expiry/not-before (bounded clock skew), scope and authorized client binding.
  For the proposed JWT profile require `typ=at+jwt` plus RFC 9068 claims and audience checks
  (VERIFY-P/V); a `typ` value alone does not prove the token is valid or authorized.
  Reject ID tokens, tokens for REST/other MCP servers and unrecognized issuers. Do not follow
  a token's arbitrary `jku`/issuer URL. Cache JWKS with bounded refresh; fail closed for unknown
  keys. Never pass a user's token to FR, Regs, the AS as an upstream credential, or another tool.
- One scope `docketclock:read` covers all six public-data tools; no review/admin/write scope.
  `offline_access`, if needed, is an AS grant concern and does not grant additional data rights.
  Return 401 for missing/invalid tokens, 403 for insufficient scope (VERIFY-P challenge syntax).
- Proposed access lifetime 10 minutes, refresh absolute lifetime seven days, refresh rotation
  and replay-family revocation. Persist grants/rotating tokens in Postgres using the selected
  library's supported adapter semantics; test concurrent refresh and atomic code consumption.
  Use hashed opaque secrets where supported. AS data is writable auth state, never civic data.
- Consent names the client, redirect destination, read scope and public-data nature. A client
  registration is not a person and does not authorize access. Bind grants to a real signed-in
  pilot user. Disable public signup for the pilot; an operator provisions invited accounts.
- Exact HTTPS redirect matching, no wildcards. Register native loopback URIs separately per
  host/path as the trusted client metadata declares them. Apply port-agnostic matching to
  registered `127.0.0.1`/`[::1]` loopback URIs; for the tested Claude Code profile also allow
  the documented port exception for its separately registered `localhost` URI. That localhost
  rule is a bounded client-compatibility policy, not a claim about RFC 8252's IP-literal rule.
  Never treat different hosts or paths as equivalent. Test both hosts and negative sibling
  paths/subdomains; do not broaden the exception to arbitrary HTTP redirect URIs.
  Validate state, single-use codes, PKCE and issuer response binding (RFC 9207; VERIFY-P).

### Client identity and registration

Support pre-registration and a bounded RFC 7591 DCR compatibility path where a measured
client requires it. The current research reports a preference for **Client ID Metadata
Documents (CIMD)** and deprecation of DCR in the newer revision; verify before configuring
either. Anthropic's authentication page, rechecked in review, describes selecting CIMD only
when the AS advertises both `client_id_metadata_document_supported=true` and `none` in
`token_endpoint_auth_methods_supported`; otherwise it uses DCR. It uses the first advertised
issuer and expects PRM `resource` to equal the MCP URL exactly. Keep these in the real-client
test, not just metadata snapshots. Advertise only working capabilities. DCR cannot require a bootstrap credential that
the chosen connector cannot send.

Pilot policy: public registration is permitted only for known client metadata/redirect
profiles, at most 100 active registrations, 5 registration attempts/IP/hour, and a daily
global cap of 50 new registrations. Unused registrations expire after seven days. No
client-supplied display name becomes a trusted identity or metrics label. Capture the AS
client identifier in the token or a verified AS mapping; rate-limit by issuer+subject+client,
also by subject and globally so repeated DCR registrations do not multiply capacity.

If CIMD is selected, allowlisted HTTPS document origins initially; fetch with a 2-second
deadline, 16 KiB cap, no redirects, public-IP/DNS-rebinding checks and no private, loopback,
link-local or metadata-service addresses. Cache validated documents with bounded TTL;
revalidate changed redirect metadata before consent. This AS fetch is the only proposed
client-supplied network fetch; it is separate from read-only MCP tools. Full open registration
is deferred pending measured demand and an abuse review.

### Authorization-server options and recommendation

| Option                                                                                | Benefits                                                                                                             | Costs, risks and adoption gate                                                                                                                                                                                                                                                           |
| ------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Lightweight `oidc-provider` library in a separate Node auth process, Postgres adapter | Same language/DB/Helm lifecycle; own issuer/domain; low incremental RAM; no per-user subscription tariff             | We own login, consent, adapter correctness, rotation/revocation, patching and recovery. Research reports DCR/resource indicators/PKCE support, but CIMD experimental; Node 24 and persistence behavior need VERIFY-V.                                                                    |
| Hosted Auth0 using an owned custom issuer domain if available                         | Managed login, recovery and security operations; essentially no local AS RAM; cloud migration does not move AS state | Recurring fee/plan restrictions, external outage and identity-data processor, tenant/config lock-in. DCR/CIMD and RFC 8707-to-audience mapping must be proven with the real connector, not assumed from generic OAuth support. Custom-domain pricing and exportability require VERIFY-V. |
| Full self-hosted IdP, e.g. Keycloak                                                   | Rich identity/admin features                                                                                         | Additional service/operational and RAM burden without a measured multi-user need. Not recommended for this pilot. No deployment or sizing claim made.                                                                                                                                    |

**Recommend the lightweight library for an invite-only operator pilot, conditional on the
Phase 1a security/interoperability gate.** Cap the spike at two implementation days; do not
build an OAuth engine. Use a maintained login component with a single invited account,
password hashing and TOTP (or an already available passkey component after verification),
CSRF protection, secure HttpOnly SameSite cookies, login throttling and operator-controlled
recovery. No hand-rolled cryptography or shipping library example login screens. No email
delivery service is needed for this pilot. If that complete slice cannot pass within the
budget, stop and cost a hosted AS; it is a valid no-go, not a reason to weaken login.

[oidc-provider upstream](https://github.com/panva/node-oidc-provider) and
[Auth0 MCP registration guidance](https://auth0.com/ai/docs/mcp/guides/registering-your-mcp-client-application/dynamic-client-registration)
were inspected by the child; current versions, adapter APIs, supported audience profile and
[pricing](https://auth0.com/pricing) remain VERIFY-V. No Auth0 quote or free-tier promise is
asserted here. Do not add a third-party IdP, Redis or another platform service by default.

On a cloud move, retain resource/issuer hostnames, signing keys and Postgres grant state to
avoid reconnecting clients. Moving from local AS to hosted AS is more than changing DNS:
issuer/client/grant incompatibilities may require re-registration and fresh consent.
The reviewed registration spec binds pre-registered/DCR credentials to their issuer;
CIMD client IDs may be portable, but existing grants/tokens are not thereby portable. Plan
that migration explicitly; never accept two unrelated issuers indefinitely as a shortcut.

### Client compatibility matrix

Documentation observations are from the research child, not tests by this primary.

| Client                             | Intended path                                             | Research observation and remaining gate                                                                                                                                                                                                                                                                                                                                               |
| ---------------------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Claude Code                        | stdio in Phase 0; remote HTTP/OAuth in Phase 2            | Docs describe HTTP, OAuth discovery/registration and local stdio. Test exact installed CLI, loopback URI, PKCE, refresh, output rendering and negotiated revision. [Docs](https://code.claude.com/docs/en/mcp). VERIFY-C.                                                                                                                                                             |
| Codex CLI                          | stdio in Phase 0; remote OAuth in Phase 2                 | Docs describe Streamable HTTP and `codex mcp login`; child reports CIMD/DCR selection. Confirm flags against installed `--help`, callbacks and revision. [Docs entrypoint](https://developers.openai.com/codex/mcp). VERIFY-C.                                                                                                                                                        |
| claude.ai custom connector         | First remote pilot, Phase 1                               | Connects from Anthropic's cloud, so localhost/Tailscale-only is insufficient. Research reports callback `https://claude.ai/api/mcp/auth_callback`, first advertised issuer, S256, CIMD or DCR. Confirm account entitlements, actual callback, timeouts and refresh before registration. [Authentication](https://www.claude.com/docs/connectors/building/authentication). VERIFY-C/V. |
| Claude Desktop                     | Remote custom connector in Phase 2; optional local stdio  | Distinguish the cloud-backed remote connector from local stdio configuration. Verify installed app/account; no assumption that Desktop OAuth redirects equal local CLI redirects. [Support](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp). VERIFY-C.                                                                           |
| Codex app                          | Shared remote configuration, tested separately in Phase 2 | CLI success does not prove app credential storage, consent UI or output rendering. Verify app version/settings and token reuse. VERIFY-C.                                                                                                                                                                                                                                             |
| ChatGPT research/company knowledge | Compatibility target, not launch prerequisite             | `search`/`fetch` facade as above. Test additive envelope fields and citation/rendering behavior; do not imply these names are required by ordinary Codex MCP. VERIFY-C.                                                                                                                                                                                                               |

## 6. Public exposure and cloud migration

The only cluster today is k3d on the Mini, behind NAT. No cloud cluster exists; provider
choice remains deferred and GCP-leaning.

Recommend a **named Cloudflare Tunnel with stable owned HTTPS hostnames**, conditional on
VERIFY-V. The tunnel makes outbound connections from the Mini/cluster; no router port opening.
Map only the MCP/discovery and AS login/consent/token/JWKS/registration routes. Do not expose
metrics, health diagnostics, Postgres, Vault, Kubernetes, review CLI or the existing REST
service by wildcard routing. Avoid another interactive access-login wall on protocol endpoints:
the MCP OAuth flow is the access boundary, and a connector cannot navigate an arbitrary
Cloudflare Access challenge.

[Cloudflare's tunnel documentation](https://developers.cloudflare.com/tunnel/) supports
public-hostname routing, according to the child. Stable named-hostname setup, DNS ownership
requirements, pricing, body limits, SSE buffering/idle timeouts, TLS-to-origin and Origin/Host
forwarding remain VERIFY-V. Use no ephemeral quick-tunnel URL in registered OAuth metadata.
Require an authenticated tunnel to the intended origin and a verified secure origin hop.

**T3 Connect is an unverified alternative**, not assumed to support arbitrary public OAuth
MCP. The research found no official guarantee for custom hostnames, transparent OAuth discovery,
all client callbacks or generic streaming. Do not rule it out categorically; accept it only
after those same tests and a documented operational owner. Otherwise use the tunnel candidate
above. Tailscale-only, local port-forwarding and desktop-local stdio cannot serve claude.ai.

Discovery endpoints and issuer/token URLs must be reachable by both remote clients and the
user's browser. Callback URLs belong to clients; resource/issuer URLs belong to DocketClock.
Changing the tunnel hostname changes metadata, token audience and often registrations/consent.
Keep the external hostnames independent of the origin so a future cloud ingress cutover can
retain them. Verify fresh authorization and token refresh after both DNS and origin switches.

Cloud phase uses existing Terraform/Helm/Argo seams: managed-control-plane Kubernetes,
CNPG PG18, Vault cloud KMS seal, ESO Kubernetes auth, cloud ingress/TLS and tested backups.
Do not apply `values-cloud.yaml` as it stands: its PG image override is empty with a stale
16.x TODO. Phase 3 must pin the same supported PG18 image as base/CI before any rendering
can count as a deployment gate.

## 7. Safety, abuse and audit

### Read-only means enforceable

Create a dedicated Postgres login with SELECT only on the approved federal delivery views
and required evidence relations, no ownership, schema CREATE, DML, dangerous function EXECUTE
or role-switch capability. Use read-only transactions and a 2-second statement timeout as
additional guards. Grant schema USAGE explicitly and test negative writes, including through
functions/views. Auth has a separate DB/schema and role with no civic-data grants. Do not give
MCP the poller's `docketclock-pg-app` credential or its external-secret bundle.

An optional audit writer has INSERT-only permission on its own audit table; no UPDATE/DELETE
or civic write rights. Maintenance retention uses a separate job role. “Read-only MCP” refers
to civic data and tool authority; authentication, quotas and audit necessarily write their
own operational state. These are not review/ingestion write surfaces.

A stolen client token can read the same scoped public federal data and consume its quota.
It cannot resolve conflicts, alter deadlines, access state pilot rows, retrieve secrets,
submit comments or trigger LLM/source work. It can still scrape within bounds: cap rates and
revoke the grant/client. With local JWT validation, revoking refresh prevents renewal but a
valid access token lasts up to ten minutes unless the resource server's denylist is updated.
Maintain a small subject/client/grant denylist with at most 60-second cache for pilot emergency
revocation. Broad exposure remains blocked if the AS cannot provide the necessary grant binding.

### Treat evidence as data

Titles, DATES text, source URLs and review notes may carry prompt injections. Return plain
text in labeled untrusted evidence fields, never instructions, HTML, executable Markdown,
embedded remote images or tool definitions sourced from a notice. Deterministic templates
distinguish service instructions from quoted data. Strip active markup for display, retain
raw originals only in the observation log, and mark excerpts/redaction. Do not concatenate
evidence into a system prompt. Source facts never authorize another tool call.

Allow only http/https links for display; no `javascript:`, `data:`, `file:`, credential-bearing
URLs or local addresses. Allowlisted official domains are citation candidates; submission
links can legitimately be agency-specific, so a different host is labeled and reviewed rather
than replaced with a guessed Regulations.gov URL. No automatic URL fetching follows.
Adversarial tests must include instructions hidden in titles, DATES text and verdict notes.

### Size, rate and execution budgets

Proposed defaults: request body 16 KiB; final serialized MCP result **48 KiB including both
structured and text copies**; list/embedded title/notice/note excerpts at most **400 characters**
each, with up to 2,000 only for a measured single-item rendering that still fits; 20
items/page, 10 for search; max offset 1,000. Total tool deadline 5 seconds, query 2 seconds;
DB pool max 4 for MCP. Abort timed-out queries; never keep filling the result after cancellation.
Reject unbounded sort, arbitrary regex, raw SQL and arbitrary URL inputs.

Pilot quotas: 30 tool calls/minute per subject+client (burst 10), 60/minute per subject,
300/minute global and 4 concurrent calls/client, 16 global. Edge IP limits protect unauthenticated
requests but do not stand in for client identity behind shared NAT. One replica may use bounded
in-process token buckets; restart resets are documented and covered by global edge limits.
Before multiple replicas, use short Postgres bucket updates with contention tests; no Redis.
HTTP 429 and safe retry hints for transport limits, typed tool errors for execution limits.
Auth/login/registration endpoints have separate quotas so data throttling does not prevent
revocation or token refresh.

### Logging and retention

One Pino completion event per attempted tool call: server request ID, validated tool name,
protocol revision, bounded client class, issuer ID, keyed hashes of subject/client/grant,
start time, duration, outcome, row count, result bytes, schema version and rate-limit decision.
Log normalized filter **names**, never raw queries or prompt text. If an operator requests
diagnostic correlation, enable a short-lived keyed argument digest rather than argument values.
Do not log Authorization/cookie headers, codes, tokens, callback query strings, raw payloads,
notes or full URLs. Apply redaction at proxy, AS and application layers.

Pino → existing Alloy → Loki, **72-hour** retention. A compact `mcp_tool_audit` Postgres table
retains the same minimal completion metadata **30 days**, indexed by time and request ID.
Estimate ~1 KiB/call including indexes: 10,000 calls/day is roughly 300 MiB/30 days, to measure.
Admission failure to append an audit attempt returns temporarily unavailable before querying
data; completion-record failures are logged and metered. Explicitly document that a crash
may leave an attempt without completion. Daily batched retention cleanup; operational table is
not the immutable civic observation log. Backups may retain removed rows for their configured
recovery window; document that retention tail. No new log service or Langfuse integration.

## 8. Operations and resource budget

Proposed chart keys: `mcp.enabled` (workload, default false), `mcp.public.enabled` (public
route, default false), command, replicas, resources, pool size,
public resource URL, issuer, allowed origins, tool/rate/size limits, audit retention;
`mcpAuth.enabled` (default false), issuer, client profiles, registration mode, resources;
separate secret references. Render disabled workloads to nothing.

Add templates for MCP Deployment/Service and its narrowly routed ingress, auth
Deployment/Service where selected, separate ExternalSecrets, and migration-managed DB roles/
views/auth/audit tables. Mount only the role-specific credentials. CNPG manages DB-role
credentials through its supported mechanism (verify before implementation); external signing,
cookie, hashing and tunnel secrets flow Vault → ESO with distinct paths such as
`docketclock/mcp-auth` and `docketclock/mcp-tunnel`. Never append optional keys to the current
all-or-nothing `docketclock-external` secret. No signing keys in Helm values or git.

Keep current and previous public verification keys during rotation for the maximum access-token
lifetime plus skew; private keys remain AS-only. Rehearse ESO propagation/process reload.
An AS snapshot restore can resurrect spent codes/refresh tokens: on auth-state recovery,
invalidate active grants and require new consent unless replay safety is independently proven.
Preserve observation data and its backup discipline.

Liveness is process-only; readiness checks DB/role access and usable validation configuration.
Temporary AS unavailability need not evict an MCP pod that can verify existing tokens with
cached keys, but login/refresh fails closed. Metrics/probes are internal, with scrape annotations
matching `charts/docketclock/templates/deployment.yaml`.

Extend `src/metrics.ts` with bounded series:

- `docketclock_mcp_tool_calls_total{tool,client_class,outcome}`; classes are a configured small
  allowlist (`claude_ai`, `claude_code`, `claude_desktop`, `codex_cli`, `codex_app`, `other`),
  not user-supplied names, subjects or raw DCR IDs. Exact per-client identity belongs in audit.
- `docketclock_mcp_tool_duration_seconds{tool,outcome}`, result-byte histogram,
  `docketclock_mcp_auth_failures_total{reason}`, rate-limit counters and audit-write failures.
- Explicit gauges for enabled/ready state, DB pool use, inflight calls and cached-key age.
  Unknown tools and unknown clients collapse to bounded labels.

Add two provisioned Grafana rules in `infra/argocd/apps/platform-grafana.yaml`, existing
Prometheus datasource/ntfy routing and one-minute evaluation:

1. `mcp-unavailable`: use kube-state-metrics' desired replicas for `docketclock-mcp` as the
   independent enable signal. Alert when desired replicas are positive and available replicas
   are zero or the MCP scrape is missing/failed, for 5 minutes. The PromQL must retain the
   desired-deployment series when the healthy/scrape series is absent (an `unless`/join, not
   a conjunction that disappears with the missing metric). `noDataState: OK`,
   `execErrState: Error`, severity warning, `cadence=daily`. Disabled workloads render to
   nothing and must not page; loss of kube-state-metrics/Prometheus itself remains covered
   by existing platform/dead-man checks. Drill both disabled and enabled-with-missing-scrape
   cases. The Argo-managed Grafana rule does not assume access to app-chart Helm values.
2. `mcp-errors`: at least 20 calls/10 minutes and more than 5% server/timeout/audit failures,
   sustained 10 minutes. Exclude abstentions, invalid input and ordinary auth denials.
   `noDataState: OK` (idle is healthy), `execErrState: Error`, severity warning.
   Auth failures/429s get dashboard panels first; add an abuse alert only after observing
   normal connector retry behavior. Verify fire and resolve through the existing drill path.

Local dev: on the **Mini only**, `cd infra && task dev-up`, then the established Tilt loop.
Add MCP/auth resources and localhost port-forwards to `Tiltfile`; source sync already covers
the app and contracts. Local commands may use `tsx watch`, production plain `tsx`; migrations
stay one-shot. Platform/tunnel desired state is GitOps through Argo; Tilt overrides app
workloads during development as already documented. Authoring on the Air is text-only.
No installs, node_modules, database or build here.

### Incremental budget (estimates, not observations or vendor quotes)

| Component                                 | Proposed request / memory ceiling                                          | Recurring cash assumption / decision                                                                 |
| ----------------------------------------- | -------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| MCP Node/tsx process                      | 50m CPU, 192 MiB / 512 MiB                                                 | Existing Mini; no LLM charges                                                                        |
| Lightweight AS process                    | 50m CPU, 192 MiB / 512 MiB                                                 | Library license reported MIT; engineering and security maintenance are real costs                    |
| Tunnel agent                              | 25m CPU, 64 MiB / 128 MiB                                                  | VERIFY-V plan and domain fees; do not assume free                                                    |
| Existing Postgres incremental working set | Budget 256 MiB; four MCP connections plus separately capped AS/audit pools | Existing CNPG; audit disk starts with a 500 MiB budget and measured retention                        |
| Total local design ceiling                | About **1.4 GiB**, target steady-state **under 800 MiB** added RSS         | Leaves roughly 3.6–4.6 GiB of the stated free RAM at the ceiling; verify under poller load           |
| Hosted AS alternative                     | Removes up to 512 MiB local ceiling                                        | Obtain current quote for invited users, DCR/CIMD, custom domain, MFA and logs before selection       |
| Cloud phase                               | Size from Phase 2 measurements, including HA and PG18                      | No current cluster or price quote; estimate full cluster/LB/storage/backups separately, not just MCP |

Do not spend the remaining RAM on an IdP/search/queue by implication. CPU acceptance: sustained
incremental use below one core at pilot load and no more than 10% regression in poller/API
latency against the same baseline; investigate instead of merely raising limits.

## 9. Test strategy and phased implementation

All runtime/build checks occur on the Mini or CI. Every phase records dataset timestamps,
client versions, selected protocol/SDK versions, test transcripts, RAM/latency measurements
and a go/no-go memo. A no-go leaves the preceding working phase available.

### Phase 0 — local value and contract tracer bullet

Deliver in small slices:

1. Keeper-reviewed candidate DTOs/probes, shared bounded read adapter and one stdio `fetch`
   path over stored read models. Stdio logs only to stderr; stdout is protocol-only.
2. All six tools, first with exact IDs/dockets/status; then the shared metadata view and
   deterministic agency/title/RIN queries needed for the EPA question. Prototype query code
   remains replaceable. No HTTP, OAuth, tunnel or new daemon yet.
3. On the Mini, invoke stdio from Claude Code and Codex CLI using a dedicated read-only DB
   role; a local process may connect through the established loopback DB port-forward.
   No need to distribute DB credentials to remote buyers. Desktop stdio is optional.
4. Fix a 20-case corpus before evaluating: all nine jobs, all six confidence states,
   null and non-null conflicts, timezone-only agreement, cross-window/side-B and multi-target
   evidence, human/agent/superseded/escalated verdicts, missing submission link, malicious
   notice text and at least one metadata-missing case. Historical fixture agreement is not
   independent legal truth; operator checks current examples against primary notices.

**Verify:** contract probes reject illegal confidence/close combinations; canonical fields
match REST for the same version; finite paging/counts and error envelopes work; DML fails
using the actual MCP DB role; state fixtures cannot escape any path. Run existing contracts
and API tests plus new focused read/MCP tests, then each CLI over the same corpus twice.

**Go:** at least 18/20 jobs useful to the operator in each CLI run; 100% preservation of
confidence/flags/disclaimer/citations in tool output; zero invented operative closes or
hidden conflicts in rendered answers. At least three cases demonstrate reconciliation/
provenance value over a single-source response. Tool p95 under one second at local pilot
load (network/model time measured separately), memory within the draft budget.

At **go**, the keeper freezes the proven DTOs into the next available shared-contract minor
and consumers switch to those exports before Phase 1. This freeze must pass the same probes.

**No-go:** ordinary search alone provides the value, or unsafe summaries persist after one
bounded tool-description/renderer revision. Record failure and stop remote work.

**Rollback:** remove local client entry; disable prototype entrypoint; leave additive contract
exports/views inert if already frozen; unfrozen candidate shapes can be discarded.
No observation/projection rollback or re-derivation is needed.

### Phase 1a — protocol/auth choice, before public exposure

Pin a tested MCP SDK/revision based on Phase 0 plus documented remote requirements. Timebox
the lightweight AS proof to two implementation days. Build the complete login→consent→PKCE
code→audience-bound access token→refresh rotation→revoke vertical slice with a throwaway
public client. Test Postgres adapter atomicity/restart persistence and recovery behavior.
Compare one hosted AS using the same resource/client requirements if the local slice fails;
obtain price/plan details instead of implementing a compatibility proxy around a bad fit.

**Verify:** wrong/missing S256, wrong verifier, reused code, wrong redirect/issuer/audience,
expired token, ID token, missing scope, refreshed-token replay, DCR churn, CIMD SSRF and
cross-client grant misuse all fail safely. Test key rotation, cold restart and callback-port
rules. Record actual metadata documents and sanitized challenge headers.

**Go:** zero auth negative-test bypasses, complete login/recovery story and AS p95 under
two seconds excluding human input; total local design meets RAM budget. Select AS and
record the protocol/client compatibility set in a short decision update.

**No-go/rollback:** keep stdio only; disable/delete throwaway registrations and grants,
remove auth exposure/config, retain no live signing credentials in a prototype. Do not
quietly switch to shared tokens, API-billed Claude or an unbudgeted IdP.

### Phase 1b — one remote claude.ai connector on k3d

Implement HTTP adapter/resource-server validation, dedicated deployment/roles, essential
limits/audit and a stable tunnel. Basic security is a prerequisite here, not postponed to
“hardening.” Run `mcp.enabled=true, mcp.public.enabled=false` for internal/loopback tests.
After Phase 1a passes, enable the narrow public route for the HTTPS throwaway-client probe;
only after it passes enroll the operator's claude.ai connector with one invited user.

**Verify:** MCP conformance smoke against pinned revision, discovery over the real HTTPS
hostname, browser consent, first call, pagination/abstention, access expiry+refresh, revocation
and a reconnect after MCP/AS/tunnel restarts. Confirm unauthenticated endpoints expose only
necessary metadata, every public data call is authorized, and metrics/DB/admin routes stay
unreachable. Check SSE/JSON response caps/timeouts and spoofed Host/Origin handling.

**Go:** complete all nine jobs with correct user-visible caveats, three fresh authorization
runs and three expiry/refresh cycles, zero cross-resource token acceptance, zero state leaks,
24-hour local soak with no OOM or poller/API regression above the stated threshold.

**Rollback:** set `mcp.public.enabled=false` and disable the tunnel route immediately; set
`mcp.enabled=false` to remove the workload when diagnosis no longer needs it. Revoke pilot grants and remove
the connector. Preserve issuer/resource domain ownership for a later attempt. REST, poller,
observation log and review CLI continue unchanged.

### Phase 2 — compatible, observable, bounded remote v1

Add tested remote Claude Code, Claude Desktop, Codex CLI and Codex app profiles one at a time;
test ChatGPT research facade only if the operator wants that product. Finish dashboards,
both alert drills, durable audit cleanup, key/credential rotation and measured quota tuning.
Exercise malformed requests, adversarial notice content, changed projection/evidence during
paging, dead/slow DB, issuer outage, tunnel loss and connector retries. Test search missing
metadata and source citation failures rather than accepting silent filtering.

**Verify:** `pnpm --filter @yokel/contracts typecheck`, app typecheck, contract probes,
existing API tests, MCP SDK client/conformance smoke and auth attack suite on Mini/CI;
`pnpm lint`; local/cloud `helm template`, existing Argo validation and secret-isolation
checks. Proposed new scripts get named during implementation; no existing MCP script is implied.

**Go:** all intended client matrix rows have dated passes, at least 100 recorded tool calls
across seven days with zero trust/authorization failures; a 30-minute load exercise at
10 concurrent calls respects quotas, p95 under two seconds and the 48 KiB cap. Alert fire/
resolve, revoked-token denial within the documented bounds, 30-day audit cleanup in a
time-shifted fixture, backup/recovery invalidation and memory budgets all pass.

**Rollback:** remove a failing client profile or disable MCP public access; revert app/chart
version through the normal release path. Keep additive schema/views and auth/audit tables
until retention/recovery obligations expire. Never delete or mutate civic observations.

### Phase 3 — cloud only after measured availability need

Trigger: the operator commits to serving additional users or records Mini availability as
the limiting factor. No speculative cloud procurement. Choose provider, full-cluster cost
ceiling and owner; fix the cloud overlay PG18 pin; provision through Terraform/Argo with
Vault KMS, ESO, ingress/TLS, backups and appropriate CNPG topology.

Move the same image/read-model code and stable resource/issuer domains. Preserve token keys/
auth state only with a controlled single-writer cutover; no independent cloned AS instances
issuing/redeeming the same grants against diverging databases. When uncertain, revoke grants
and require consent again. Scale MCP only after shared rate-limit tests.

**Verify/go:** restore drill, pinned PG18/CI parity, source/observation integrity, all remote
client login/refresh/revoke tests, staged DNS cutover, 48-hour cloud soak, measured cost within
approved cap and operator acceptance of uptime. No universal cloud-price estimate substitutes.

**Rollback:** drain/disable cloud endpoint; restore DNS/tunnel to the Mini only if DB/auth
state is authoritative there. If state diverged, revoke/reconsent after restoring the chosen
authoritative backup; do not blindly switch DNS to stale grants or an old civic snapshot.

## 10. Operator decisions and outstanding verification

Before the Phase 0 value gate: confirm the pilot owner and evaluation questions; choose which
real cases the operator will judge independently. No paid customer claim is required.
Before Phase 1 exposure: choose the owned domain, invited users, who maintains login/recovery,
and whether the two-day lightweight-AS budget or a priced hosted-AS offer is preferred.
Before Phase 2: decide whether ChatGPT research compatibility is a release goal and approve
public executor aliases/note redaction and the 30-day minimal audit retention.
Cloud provider and spending cap remain a Phase 3 decision.

Still unverified beyond the local SDK smoke below: client/SDK revision compatibility, exact client callback/registration
behavior and account availability; OAuth library Node 24/Postgres/CIMD support; hosted AS
audience mapping, custom-domain pricing and export; tunnel DNS/streaming/limits/cost; T3
Connect suitability; production memory/query cost, data coverage and end-user caveat retention.
The research child supplied documentation evidence; the implementation measurements below
are synthetic local checks, not those remote or operator gates.

## 11. Phase 0 implementation record — 2026-10-20

**Prototype implemented; value/release gate remains pending.** The entrypoint is
[`apps/docketclock/src/mcp/run-stdio.ts`](../apps/docketclock/src/mcp/run-stdio.ts);
the six-tool service and app-local candidate schemas live beside it. Bounded shared read
queries live in [`src/api/mcp-queries.ts`](../apps/docketclock/src/api/mcp-queries.ts).
No shared contract source/version, HTTP route, OAuth server, chart, public exposure or live
cluster data was changed. No commit, push or PR was authorized or performed.

The prototype requires explicit `MCP_DATABASE_URL` and rejects owner/poller credentials.
It checks the four-table SELECT-only role, uses repeatable-read/read-only transactions,
caps concurrency at four and response bytes at 48 KiB including both JSON copies. Logs go
to stderr and contain tool/outcome/duration, not arguments, source payloads or credentials.
Unavailable required explanation evidence returns `evidence_unavailable`; references/history
are checked against federal-eligible observations before pagination. Conflict tools retain
their separate per-item missing-evidence behavior. Review notes/executors are redacted,
including legacy review text copied into DATES.

Dependencies are pinned to MCP server/client **2.3.1** and Zod-to-JSON-Schema **3.25.2**.
Frozen contracts continue using Zod 3; published SDK schemas use the supported JSON-schema
adapter, with authoritative Zod validation at the service boundary. The actual SDK stdio
smoke negotiated **2025-11-25**. This does not establish Claude/Codex compatibility or prove
the newer transport revision works; keep those client probes open.

Validation ran on the verified Mac Mini M4, Node **24.14.1**, pnpm **10.23.0**, PostgreSQL
**18.3** in the existing test-only container. Disposable databases were named
`docketclock_mcp_test_phase0` and `docketclock_mcp_test_regression`. No live k3d database
was used. Dependencies were installed after the planning-only turn, once Mini identity
and implementation authorization were established.

- Existing contract probes and REST API integration tests passed.
- Candidate schemas: 26 probes. Shared reads: 17 database checks, including future-state
  fixtures, both conflict sides, metadata gaps, full-chain limits and snapshot consistency.
- Service and SDK tests cover errors, abstentions, citations, note redaction, bounded paging,
  protocol-only stdout, the JSON mirror, unknown tools and concurrency.
- Actual stdio subprocess plus actual SELECT-only role: the fixed **20 synthetic cases**
  passed, with follow-ups/errors bringing the smoke to **30 calls**. This is mechanical
  correctness evidence, not 20 operator usefulness scores.
- A measured run negotiated 2025-11-25, had sequential local **p95 198.2 ms**, and server
  **RSS 157.6 MiB after the corpus**. These are one small synthetic run and a memory snapshot,
  not peak RAM, production capacity or a load-test result. Earlier local p95 was 78.1 ms;
  retain the run variation rather than selecting the fastest measurement.
- Explicit role tests proved owner rejection, unrelated-table denial, DML denial even in a
  requested read-write transaction, statement timeout and recovery after the whole-read budget.
  PostgreSQL `transaction_timeout` exposed a postgres.js 3.4.9 socket-close race; the prototype
  instead applies a shrinking statement timeout (2 seconds maximum within a 5-second read
  budget). Startup/connect time is separate. The scoped adapter supports the tagged reads
  used here; it is not a general SQL sandbox or permission to add arbitrary query execution.

Use [`docs/runbooks/mcp-phase0.md`](../docs/runbooks/mcp-phase0.md) for the fixed corpus,
private client registration and four scored runs. Pure MCP probes are included in the normal
app test script; destructive DB checks require explicit disposable test URLs and never fall
back to `DATABASE_URL`.

**Rebase and review, 2026-11-06.** The code was written against `reconcile-v2.3` and rebased onto
`reconcile-v2.4` and contracts 0.12.0. Fable's implementation review then found that honoring ignored
linked FR amendments and that `raw_fr_close_date` read as the current FR value on `fr_close_amended`
windows. Honoring now also receives the engine's amendment inputs, and those windows label the
original value as superseded. The corpus gained case 21 for this, so the fixed corpus is **21 cases**.
Collections now withhold one unsafe stored link instead of failing the page, and search keywords
reject control characters so continuations always round-trip. The latency, memory and call-count
figures above predate this rebase. The cost of the amendment read on real data is not measured.

**Remaining gates:** Claude Code and Codex CLI actual rendering/negotiation and the four
operator-scored 21-case runs; current real-notice checks; contract-keeper freeze only after the go decision.
The installed clients are Claude Code **2.1.301** and Codex CLI **0.163.0**. Their help confirms
temporary-config controls, but no successful model-driven client evaluation is claimed.
Remote OAuth, tunnel exposure and vendor/cloud checks remain Phase 1+ work.

## Review log

- **Implementation review (2026-11-06, Claude Fable 5.1, high):** read-only review of the rebased
  branch after the 2026-10-20 attempt hit a rate limit. Verdict: mergeable as a local prototype after
  two P1 fixes. Accepted and fixed: amendment-aware honoring, `fr_close_amended` labelling, unsafe links
  in collections, keyword continuation, the misleading reduced-page warning, and integration assertions
  that matched any window. Documented instead of changed: the 16 KiB stdio frame limit and the
  `citation_unavailable` search behavior. Left open: `agency_slugs.max(20)` may reject a document with
  more than 20 agencies, and GovInfo evidence rows carry no source URL.

- **Operator approval (2026-10-20):** approved the approach and authorized proceeding after
  discussion of the lightweight OAuth library, owned login/consent/persistence responsibilities,
  two-day security/compatibility spike and hosted-AS fallback. Phase 0 starts first.
- **Research round 1 (2026-10-19, Claude Sonnet 5.5, medium, `claudeAgent`):** read-only
  official-document research. Reported the newer 2026-07-28 transport and CIMD preference,
  client differences, experimental local-library support and unresolved vendor pricing.
  Accepted the need for version/client probes; did not accept a blanket localhost/127.0.0.1
  equivalence rule or categorical rejection of T3 Connect without official evidence.
  Subscription authentication was confirmed (`authMethod: claude.ai`, no
  `ANTHROPIC_API_KEY` override). Task suffix: `docketclock-mcp-research-20261019-r1`.
- **Spec review round 1 (2026-10-20, Claude Fable 5.1, high, `claudeAgent`):** read-only
  repo correctness/security review plus independent fetches of the dated transport,
  registration and Anthropic auth pages. Verdict: ready for Phase 0 after two P1 text fixes
  and P2 clarifications; no architectural blocker. Both P1s accepted: distinguish the
  documented localhost port exception from RFC loopback-IP rules, and correct ADR 0016's
  reservation to `plans/review-learning-loop.md`, which also claims contract 0.12.0.
  Accepted P2s: one JSON text copy and explicit disclaimer placement; escalation effect/
  honoring definitions; bounded review-overlay alignment; per-item missing conflict evidence
  and side-B refinements; disputed-close counts and precise metadata populations; smaller
  page excerpts and follow-up input refinements; self-gating Grafana availability alert;
  JWT access-token type checks; separate workload/public-route flags; issuer-migration
  caveats; contract freeze after the value gate. Added recorded CIMD/client observations.
  Did not pin 2025-11-25 solely because a vendor page links it: real-client negotiation
  remains the gate. Did not accept missing `resource` silently or switch to opaque-token
  introspection without a measured client/library need; the explicit-resource, audience-bound
  JWT profile and bounded grant denylist remain the proposed design. A required exception
  must be documented and retested, not inferred. Primary checked the changed rules against
  contracts and repository evidence; this is not a second reviewer pass.
  Task suffix: `docketclock-mcp-review-20261020-r1`.
- **Initial planning document validation (2026-10-20, primary):** both new files passed whitespace checks,
  local-link existence checks and balanced Markdown fences. Dependencies are absent in this
  checkout at that point, so `pnpm lint`/Prettier was not run and nothing was installed in
  that planning-only turn. Only the two planning files had changed then.
- **Phase 0 implementation (2026-10-20):** keeper/schema and read-adapter tasks used Codex
  GPT-6.1 Sol/high; SDK/dependency setup used Claude Sonnet 5.5/medium; tool-service work used
  Claude Opus 5.5/high; evaluation fixtures used Codex GPT-6.1 Sol/medium. Primary integrated
  transport, role checks, timeouts, tests and documentation. The Opus task hit a provider
  rate limit after writing code/tests; primary completed validation and fixes.
- **Implementation review round 1, blocked (2026-10-20, Claude Fable 5.1/high,
  `claudeAgent`, suffix `mcp-phase0-integrated-review-r1`):** task failed with
  `Claude API rate limit reached. Try again later.` No review verdict was produced.
  This is the subscription provider's returned error wording, not a switch to API billing.
  The earlier Fable **spec** review remains valid; it is not an implementation sign-off.
- **Supplementary implementation review round 1 (2026-10-20, Codex GPT-6 Astra/high,
  suffix `mcp-phase0-codex-review-r1`):** read-only review of the integrated prototype,
  including Claude-authored service code. Two P2s accepted: excluded state handles could
  escape via history/references, and missing referenced observations could yield an empty
  successful evidence page. Primary added federal eligibility/completeness checks before
  those sections paginate and regression probes; unavailable evidence now abstains explicitly.
  This is not a completed Fable review or a second reviewer pass over the fixes.
- **Final primary validation (2026-10-20):** 26 schema probes, 35 service probes and SDK
  smoke passed; all-workspace `pnpm typecheck`, `pnpm lint` and `git diff --check` passed.
  The 17 PostgreSQL read checks and permissions/timeouts suite passed. After both review
  fixes, all 20 actual-stdio corpus cases passed again (30 calls; 2025-11-25; p95 **119.5 ms**;
  post-corpus RSS **156.6 MiB**). Existing contract and REST API checks passed earlier in
  this implementation round. No full historical application-suite or model-driven CLI
  evaluation is claimed. All work remains uncommitted.
