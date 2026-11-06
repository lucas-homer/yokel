/** Shared, read-only Phase 0 delivery reads. Call all reads for one answer inside withMcpRead.
 * Canonical records are validated before leaving this boundary; no reconciliation is performed.
 */
import type postgres from "postgres";
import {
  ConflictRecord,
  Observation,
  OcdId,
  ParticipationWindow,
  makeOcdId,
} from "@yokel/contracts";
import type { Sql, SqlHandle } from "../db/client.js";

export type McpReadTx = postgres.TransactionSql;
export type McpReadErrorCode =
  | "invalid_input"
  | "ambiguous_identifier"
  | "result_too_large";
export class McpReadError extends Error {
  constructor(
    public readonly code: McpReadErrorCode,
    message: string,
    public readonly candidateOcdIds: string[] = [],
  ) {
    super(message);
    this.name = "McpReadError";
  }
}

// Intentionally pinned independently of OcdId: future contract state support must not widen v1.
const FEDERAL =
  "^ocd-participation-window/federal/(regs:[A-Za-z0-9]+|[A-Za-z0-9][A-Za-z0-9-]*)$";
function federalId(id: string): boolean {
  return /^ocd-participation-window\/federal\/(?:regs:[A-Za-z0-9]+|[A-Za-z0-9][A-Za-z0-9-]*)(?![\s\S])/.test(
    id,
  );
}
function requireFederal(id: string): void {
  if (!federalId(id) || !OcdId.safeParse(id).success)
    throw new McpReadError(
      "invalid_input",
      "A federal window identifier is required.",
    );
}

export async function withMcpRead<T>(
  sql: Sql,
  callback: (tx: McpReadTx) => Promise<T>,
): Promise<T> {
  // SET LOCAL cannot escape the transaction or contaminate a pooled connection.
  return sql.begin<T>(
    "isolation level repeatable read read only",
    async (tx) => {
      await tx`set local statement_timeout = '2s'`;
      const deadline = performance.now() + 5000;
      // Do not use PG's connection-killing transaction_timeout: postgres.js 3.4.9
      // can race its deferred socket write after the server disconnects. Instead,
      // each awaited tagged query gets the smaller of 2s and the remaining budget.
      // SQL fragments are not awaited and must stay lazy for postgres.js composition.
      const bounded = new Proxy(tx, {
        apply(target, thisArg, args) {
          const query = Reflect.apply(target, thisArg, args);
          if (!query || typeof query.then !== "function") return query;
          return new Proxy(query, {
            get(pending, property, receiver) {
              if (property !== "then")
                return Reflect.get(pending, property, receiver);
              return (
                resolve: (value: unknown) => unknown,
                reject: (error: unknown) => unknown,
              ) =>
                (async () => {
                  const remaining = Math.floor(deadline - performance.now());
                  if (remaining <= 0)
                    throw Object.assign(
                      new Error("MCP read deadline exceeded"),
                      { code: "MCP_READ_TIMEOUT" },
                    );
                  await tx`select set_config('statement_timeout', ${String(Math.min(2000, remaining))}, true)`;
                  return await pending;
                })().then(resolve, reject);
            },
          });
        },
      });
      const result = await callback(bounded);
      if (performance.now() > deadline)
        throw Object.assign(new Error("MCP read deadline exceeded"), {
          code: "MCP_READ_TIMEOUT",
        });
      return result;
    },
  ) as Promise<T>;
}

type DbRow = Record<string, unknown>;
function iso(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  return value instanceof Date
    ? value.toISOString()
    : new Date(String(value)).toISOString();
}
function windowFrom(row: DbRow): ParticipationWindow {
  return ParticipationWindow.parse({
    ...row,
    resolved_close_utc: iso(row.resolved_close_utc),
  });
}
function observationFrom(row: DbRow): Observation {
  return Observation.parse({ ...row, fetched_at: iso(row.fetched_at) });
}
function conflictFrom(row: DbRow): ConflictRecord {
  return ConflictRecord.parse({
    ...row,
    ocd_id_b: row.ocd_id_b === "" ? null : row.ocd_id_b,
    detected_at: iso(row.detected_at),
  });
}

export interface McpPage {
  limit?: number;
  offset?: number;
}
export interface McpPageResult<T> {
  rows: T[];
  total: number;
  limit: number;
  offset: number;
}
export interface McpWindowPage extends McpPageResult<ParticipationWindow> {
  metadataMissingCount: number;
  unknownCloseCount: number;
  disputedCloseCount: number;
}
function page(input: McpPage): { limit: number; offset: number } {
  const limit = input.limit ?? 10,
    offset = input.offset ?? 0;
  if (
    !Number.isInteger(limit) ||
    limit < 1 ||
    limit > 20 ||
    !Number.isInteger(offset) ||
    offset < 0 ||
    offset > 1000
  )
    throw new McpReadError(
      "invalid_input",
      "Page limit must be 1–20 and offset 0–1000.",
    );
  return { limit, offset };
}

export async function resolveWindow(
  tx: SqlHandle,
  id: string,
): Promise<ParticipationWindow | null> {
  if (id.startsWith("ocd-participation-window/")) {
    requireFederal(id);
    const rows =
      await tx`select * from participation_windows where ocd_id = ${id} and ocd_id ~ ${FEDERAL}`;
    return rows[0] ? windowFrom(rows[0]) : null;
  }
  try {
    makeOcdId({ frDocNum: id });
  } catch {
    throw new McpReadError(
      "invalid_input",
      "A federal OCD-ID or FR document number is required.",
    );
  }
  const rows = await tx`
    select * from participation_windows where fr_document_number = ${id} and ocd_id ~ ${FEDERAL}
    order by ocd_id asc limit 21
  `;
  if (rows.length > 1)
    throw new McpReadError(
      "ambiguous_identifier",
      "The FR document number matches multiple stored windows.",
      rows.slice(0, 20).map((r) => String(r.ocd_id)),
    );
  return rows[0] ? windowFrom(rows[0]) : null;
}

export interface WindowMetadata {
  title: string | null;
  agencySlugs: string[];
  observationIds: string[];
}
/** SQL counterpart of extractFr's defensive object/nonempty-string extraction. Select LATEST first:
 * malformed latest raw becomes missing metadata, never an invitation to resurrect an older title.
 */
function metadataJoin(tx: SqlHandle) {
  return tx`left join lateral (
    select observation_id, raw from observations o
    where o.ocd_id = w.ocd_id and o.source = 'federal_register' and o.ocd_id ~ ${FEDERAL}
    order by o.fetched_at desc, o.observation_id desc limit 1
  ) latest_fr on true
  left join lateral (
    select case when jsonb_typeof(latest_fr.raw) = 'object'
      and jsonb_typeof(latest_fr.raw->'title') = 'string' and length(latest_fr.raw->>'title') > 0
      then latest_fr.raw->>'title' else null end as title,
    array(select distinct a->>'slug' from jsonb_array_elements(
      case when jsonb_typeof(latest_fr.raw->'agencies') = 'array' then latest_fr.raw->'agencies' else '[]'::jsonb end
    ) a where jsonb_typeof(a) = 'object' and jsonb_typeof(a->'slug') = 'string'
      and length(a->>'slug') > 0 order by a->>'slug') as agency_slugs
  ) metadata on true`;
}
export async function getWindowMetadata(
  tx: SqlHandle,
  ocdId: string,
): Promise<WindowMetadata> {
  requireFederal(ocdId);
  const [row] = await tx`
    select metadata.title, metadata.agency_slugs, latest_fr.observation_id
    from participation_windows w ${metadataJoin(tx)} where w.ocd_id = ${ocdId} and w.ocd_id ~ ${FEDERAL}
  `;
  return {
    title: row?.title ?? null,
    agencySlugs: row?.agency_slugs ?? [],
    observationIds: row?.observation_id ? [row.observation_id] : [],
  };
}

/** Names intentionally match the public candidate inputs without importing the candidate schemas. */
export interface McpWindowFilters extends McpPage {
  agency?: string;
  docket_id?: string;
  rin?: string;
  keyword?: string;
  status?: ParticipationWindow["status"];
  confidence?: ParticipationWindow["confidence"];
  window_type?: ParticipationWindow["window_type"];
  closes_after?: string;
  closes_before?: string;
  close_mode?: "any" | "known" | "unknown";
}
export async function listMcpWindows(
  tx: SqlHandle,
  filters: McpWindowFilters = {},
): Promise<McpWindowPage> {
  const { limit, offset } = page(filters);
  const mode = filters.close_mode ?? "any";
  const after = filters.closes_after,
    before = filters.closes_before;
  if (
    !["any", "known", "unknown"].includes(mode) ||
    (after !== undefined && !Number.isFinite(Date.parse(after))) ||
    (before !== undefined && !Number.isFinite(Date.parse(before))) ||
    (after !== undefined &&
      before !== undefined &&
      Date.parse(after) >= Date.parse(before)) ||
    (mode === "unknown" && (after !== undefined || before !== undefined))
  )
    throw new McpReadError(
      "invalid_input",
      "Invalid closing bounds or close mode.",
    );
  let base = tx`w.ocd_id ~ ${FEDERAL} and w.window_type = ${filters.window_type ?? "comment"}`;
  if (filters.status !== undefined)
    base = tx`${base} and w.status = ${filters.status}`;
  if (filters.confidence !== undefined)
    base = tx`${base} and w.confidence = ${filters.confidence}`;
  if (filters.docket_id !== undefined)
    base = tx`${base} and w.docket_id @> ${tx.json([filters.docket_id])}`;
  if (filters.rin !== undefined) base = tx`${base} and w.rin = ${filters.rin}`;
  let dated = tx`true`;
  if (after !== undefined)
    dated = tx`${dated} and w.resolved_close_utc > ${after}`;
  if (before !== undefined)
    dated = tx`${dated} and w.resolved_close_utc < ${before}`;
  if (mode === "known")
    dated = tx`${dated} and w.resolved_close_utc is not null`;
  if (mode === "unknown") dated = tx`${dated} and w.resolved_close_utc is null`;
  let metadata = tx`true`;
  if (filters.agency !== undefined)
    metadata = tx`${metadata} and ${filters.agency} = any(metadata.agency_slugs)`;
  if (filters.keyword !== undefined) {
    // strpos means literal substring: % and _ are not caller-controlled LIKE wildcards.
    const keyword = filters.keyword.toLowerCase();
    metadata = tx`${metadata} and (
      strpos(lower(coalesce(metadata.title, '')), ${keyword}) > 0 or
      strpos(lower(w.ocd_id), ${keyword}) > 0 or
      strpos(lower(coalesce(w.fr_document_number, '')), ${keyword}) > 0 or
      strpos(lower(coalesce(w.regs_document_id, '')), ${keyword}) > 0 or
      strpos(lower(coalesce(w.regs_object_id, '')), ${keyword}) > 0 or
      strpos(lower(coalesce(w.rin, '')), ${keyword}) > 0 or
      exists (select 1 from jsonb_array_elements_text(w.docket_id) d(value) where strpos(lower(d.value), ${keyword}) > 0)
    )`;
  }
  const [counts] = await tx`
    select count(*) filter (where ${dated} and ${metadata})::int as total,
      count(*) filter (where ${dated} and (metadata.title is null or cardinality(metadata.agency_slugs) = 0))::int as missing,
      count(*) filter (where ${metadata} and w.resolved_close_utc is null)::int as unknown,
      count(*) filter (where ${dated} and ${metadata} and w.resolved_close_utc is not null and w.confidence = 'conflicting')::int as disputed
    from participation_windows w ${metadataJoin(tx)} where ${base}
  `;
  const rows = await tx`
    select w.* from participation_windows w ${metadataJoin(tx)} where ${base} and ${dated} and ${metadata}
    order by w.resolved_close_utc asc nulls last, w.ocd_id asc limit ${limit} offset ${offset}
  `;
  return {
    rows: rows.map(windowFrom),
    total: Number(counts!.total),
    limit,
    offset,
    metadataMissingCount: Number(counts!.missing),
    unknownCloseCount: Number(counts!.unknown),
    disputedCloseCount: Number(counts!.disputed),
  };
}

export interface McpConflictFilters extends McpPage {
  ocd_id?: string;
}
/** Missing side evidence remains a visible conflict; existing nonfederal evidence fails closed. */
function publicConflict(tx: SqlHandle) {
  return tx`c.resolved_at is null and c.ocd_id ~ ${FEDERAL} and (c.ocd_id_b = '' or c.ocd_id_b ~ ${FEDERAL})
    and not exists (select 1 from observations private_side
      where private_side.observation_id in (c.observation_a_id, c.observation_b_id)
        and not (private_side.ocd_id ~ ${FEDERAL}))`;
}
export async function listMcpConflicts(
  tx: SqlHandle,
  filters: McpConflictFilters = {},
): Promise<McpPageResult<ConflictRecord>> {
  const { limit, offset } = page(filters);
  let where = publicConflict(tx);
  if (filters.ocd_id !== undefined) {
    requireFederal(filters.ocd_id);
    where = tx`${where} and (c.ocd_id = ${filters.ocd_id} or c.ocd_id_b = ${filters.ocd_id})`;
  }
  const [count] =
    await tx`select count(*)::int as total from conflict_records c where ${where}`;
  const rows = await tx`select c.* from conflict_records c where ${where}
    order by c.detected_at desc, c.ocd_id asc, c.ocd_id_b asc,
      c.observation_a_id asc, c.observation_b_id asc, c.conflict_scope asc limit ${limit} offset ${offset}`;
  return {
    rows: rows.map(conflictFrom),
    total: Number(count!.total),
    limit,
    offset,
  };
}

export type EvidenceRelationship =
  | "primary"
  | "target"
  | "current"
  | "agreeing"
  | "conflicting"
  | "history"
  | "conflict_side";
export interface McpEvidenceRow {
  observation: Observation;
  relationship: EvidenceRelationship[];
}
/** Expansion is one hop from the requested window, not transitive traversal of another window. */
function evidenceRelations(tx: SqlHandle, ocdId: string) {
  return tx`with scope as (select * from participation_windows where ocd_id = ${ocdId} and ocd_id ~ ${FEDERAL}),
    refs as (
      select o.observation_id, 'primary'::text as relationship from observations o, scope s where o.ocd_id = s.ocd_id
      union all select t.observation_id, 'target' from observation_targets t, scope s where t.ocd_id = s.ocd_id
      union all select jsonb_array_elements_text(s.current_observation_ids), 'current' from scope s
      union all select jsonb_array_elements_text(s.provenance->'agreeing_observation_ids'), 'agreeing' from scope s
      union all select jsonb_array_elements_text(s.provenance->'conflicting_observation_ids'), 'conflicting' from scope s
      union all select jsonb_array_elements_text(h->'observation_ids'), 'history' from scope s,
        lateral jsonb_array_elements(s.change_history) h
      union all select side.id, 'conflict_side' from conflict_records c, scope s,
        lateral (values (c.observation_a_id), (c.observation_b_id)) side(id)
        where ${publicConflict(tx)} and (c.ocd_id = s.ocd_id or c.ocd_id_b = s.ocd_id)
    ), related as (select observation_id, array_agg(distinct relationship order by relationship) as relationship
      from refs group by observation_id)`;
}
export async function getEvidencePage(
  tx: SqlHandle,
  ocdId: string,
  options: McpPage & { evidenceAsOf?: string } = {},
): Promise<McpPageResult<McpEvidenceRow>> {
  requireFederal(ocdId);
  const { limit, offset } = page(options);
  if (
    options.evidenceAsOf !== undefined &&
    !Number.isFinite(Date.parse(options.evidenceAsOf))
  )
    throw new McpReadError("invalid_input", "Invalid evidence timestamp.");
  // Validate the complete projection before consuming its structured reference arrays.
  await resolveWindow(tx, ocdId);
  const boundary =
    options.evidenceAsOf === undefined
      ? tx`true`
      : tx`o.fetched_at <= ${options.evidenceAsOf}`;
  const [count] = await tx`${evidenceRelations(tx, ocdId)}
    select count(*)::int as total from related r join observations o using (observation_id)
    where o.ocd_id ~ ${FEDERAL} and ${boundary}`;
  const rows = await tx`${evidenceRelations(tx, ocdId)}
    select o.*, r.relationship from related r join observations o using (observation_id)
    where o.ocd_id ~ ${FEDERAL} and ${boundary}
    order by o.fetched_at desc, o.observation_id desc limit ${limit} offset ${offset}`;
  return {
    rows: rows.map(
      (r): McpEvidenceRow => ({
        observation: observationFrom(r),
        relationship: r.relationship,
      }),
    ),
    total: Number(count!.total),
    limit,
    offset,
  };
}
export async function readEvidenceByIds(
  tx: SqlHandle,
  ocdId: string,
  ids: string[],
): Promise<Observation[]> {
  requireFederal(ocdId);
  if (ids.length > 1000)
    throw new McpReadError(
      "result_too_large",
      "At most 1000 evidence IDs may be read.",
    );
  if (ids.length === 0) return [];
  await resolveWindow(tx, ocdId);
  const rows = await tx`${evidenceRelations(tx, ocdId)}
    select o.* from related r join observations o using (observation_id)
    where o.ocd_id ~ ${FEDERAL} and o.observation_id = any(${tx.array([...new Set(ids)])}::text[])
    order by o.fetched_at desc, o.observation_id desc`;
  return rows.map(observationFrom);
}
export async function getEngineObservations(
  tx: SqlHandle,
  ocdId: string,
): Promise<Observation[]> {
  requireFederal(ocdId);
  const rows =
    await tx`select * from observations where ocd_id = ${ocdId} and ocd_id ~ ${FEDERAL}
    order by fetched_at asc, observation_id asc limit 1001`;
  if (rows.length > 1000)
    throw new McpReadError(
      "result_too_large",
      "The complete engine observation chain exceeds 1000 rows.",
    );
  return rows.map(observationFrom);
}
export async function getProjectionStamp(
  tx: SqlHandle,
  id: string,
): Promise<{ derivedAt: string | null; reconcilerVersion: string | null }> {
  const window = await resolveWindow(tx, id);
  if (!window) return { derivedAt: null, reconcilerVersion: null };
  const [row] =
    await tx`select derived_at, reconciler_version from participation_windows
    where ocd_id = ${window.ocd_id} and ocd_id ~ ${FEDERAL}`;
  return {
    derivedAt: iso(row?.derived_at),
    reconcilerVersion: row?.reconciler_version ?? null,
  };
}
