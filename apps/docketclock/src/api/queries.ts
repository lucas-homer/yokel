/**
 * queries.ts — the Delivery API DB read layer (NO HTTP). Pure functions over a `Sql` handle that read
 * the DERIVED projections (participation_windows / conflict_records, 0003) + the append-only log
 * (observations, 0001) and return CONTRACT-VALIDATED objects.
 *
 * The load-bearing discipline: EVERY row is parsed through its @yokel/contracts schema before it leaves
 * this layer (ParticipationWindow / ConflictRecord / Observation). So the API can NEVER emit a
 * non-contract shape, and a mapping bug (e.g. a postgres.js Date leaking where the contract wants an ISO
 * string, or a jsonb column not parsed to its array/object shape) fails LOUD here at the boundary rather
 * than shipping a malformed response. The HTTP layer (server.ts) re-asserts the same schemas on
 * serialization via fastify-type-provider-zod, so spec ⇄ response ⇄ DB read all agree on ONE definition.
 *
 * Timestamp/jsonb handling mirrors reconcile/persist.ts + reconcileOcdId: postgres.js returns timestamptz
 * as a JS Date — we normalize to a UTC ISO string (the contract carries ISO strings, e.g.
 * resolved_close_utc / fetched_at / detected_at); jsonb columns (docket_id, conflict_flags, tags,
 * provenance, change_history, current_observation_ids, raw) come back already parsed by postgres.js.
 *
 * NOT built here (DEFERRED — see the build task / PR): the `agency` window filter (participation_windows
 * has no agency column; agency would need a reconcile-time projection off the FR payload — a follow-up,
 * not a docket-prefix hack), tags filtering, FTS `?q=`, GET /accuracy. Only filters backed by real
 * columns are implemented: confidence / status / docket_id / closes_before / closes_after for windows,
 * ocd_id for conflicts.
 */
import {
  ConflictRecord,
  Observation,
  ParticipationWindow,
} from "@yokel/contracts";
import type { Sql } from "../db/client.js";

/** Default page size + the hard cap (the architecture's paginated list contract). */
export const DEFAULT_LIMIT = 50;
export const MAX_LIMIT = 200;

/** Clamp a requested limit into [0, MAX_LIMIT], defaulting an absent one to DEFAULT_LIMIT. */
function clampLimit(limit: number | undefined): number {
  if (limit === undefined) return DEFAULT_LIMIT;
  if (limit < 0) return 0;
  return Math.min(limit, MAX_LIMIT);
}

function clampOffset(offset: number | undefined): number {
  if (offset === undefined || offset < 0) return 0;
  return offset;
}

/** timestamptz → UTC ISO string (the contract shape). postgres.js hands these back as JS Date. */
function isoOrNull(v: Date | string | null): string | null {
  if (v === null) return null;
  return v instanceof Date ? v.toISOString() : new Date(v).toISOString();
}

// ── windows ───────────────────────────────────────────────────────────────────────────────────────

export interface WindowFilters {
  confidence?: string;
  status?: string;
  /** Matches when the jsonb docket_id array CONTAINS this id. */
  docketId?: string;
  /**
   * resolved_close_utc < this instant (NULL closes are excluded from a closes_* filter). Accepts a JS
   * Date (postgres.js binds it directly) or an ISO string. A validated value only — the route schema
   * coerces+validates client input (z.coerce.date) so an Invalid Date can never reach the SQL bind.
   */
  closesBefore?: Date | string;
  /** resolved_close_utc > this instant (NULL closes are excluded from a closes_* filter). */
  closesAfter?: Date | string;
  limit?: number;
  offset?: number;
}

interface WindowRow {
  ocd_id: string;
  fr_document_number: string | null;
  regs_document_id: string | null;
  regs_object_id: string | null;
  docket_id: string[];
  rin: string | null;
  window_type: string;
  resolved_close_utc: Date | null;
  resolved_close_display: string | null;
  raw_fr_close_date: string | null;
  raw_regs_close_datetime: string | null;
  confidence: string;
  conflict_flags: string[];
  status: string;
  submission_url: string | null;
  govinfo_url: string | null;
  tags: string[];
  version: number;
  current_observation_ids: string[];
  provenance: unknown;
  change_history: unknown[];
}

/** Map a participation_windows DB row to the contract shape, then PARSE it (fail loud on a mapping bug). */
function toWindow(r: WindowRow): ParticipationWindow {
  // FAIL-LOUD BY DESIGN: a contract-invalid row throws here (and 500s the list). That's acceptable
  // because our reconcile path runs ParticipationWindow.parse BEFORE persisting, so a poison row can't
  // be written through OUR pipeline. A row-level skip-and-log is a future hardening only if external
  // writers ever touch this projection directly.
  return ParticipationWindow.parse({
    ocd_id: r.ocd_id,
    fr_document_number: r.fr_document_number,
    regs_document_id: r.regs_document_id,
    regs_object_id: r.regs_object_id,
    docket_id: r.docket_id,
    rin: r.rin,
    window_type: r.window_type,
    resolved_close_utc: isoOrNull(r.resolved_close_utc),
    resolved_close_display: r.resolved_close_display,
    raw_fr_close_date: r.raw_fr_close_date,
    raw_regs_close_datetime: r.raw_regs_close_datetime,
    confidence: r.confidence,
    conflict_flags: r.conflict_flags,
    status: r.status,
    submission_url: r.submission_url,
    govinfo_url: r.govinfo_url,
    tags: r.tags,
    version: r.version,
    current_observation_ids: r.current_observation_ids,
    provenance: r.provenance,
    change_history: r.change_history,
  });
}

/**
 * listWindows — paginated, filterable window list + total count for the SAME filter (page-independent).
 *
 * Order: resolved_close_utc asc NULLS LAST, then ocd_id — a stable total order so paging never drops or
 * repeats a row (two windows with the same close, or two NULL-close windows, still page deterministically
 * by ocd_id). The filter predicates are composed once and reused for the count, so `total` reflects the
 * filtered-but-unpaged set (what the Pagination contract promises a client for computing remaining pages).
 */
export async function listWindows(
  sql: Sql,
  filters: WindowFilters = {},
): Promise<{
  rows: ParticipationWindow[];
  total: number;
  limit: number;
  offset: number;
}> {
  const limit = clampLimit(filters.limit);
  const offset = clampOffset(filters.offset);

  // Build the shared WHERE fragment from only the provided filters. postgres.js composes fragments with
  // sql`` interpolation; an empty fragment (sql``) is a no-op so the base query stays valid.
  const conds = [];
  if (filters.confidence !== undefined)
    conds.push(sql`confidence = ${filters.confidence}`);
  if (filters.status !== undefined) conds.push(sql`status = ${filters.status}`);
  if (filters.docketId !== undefined)
    // jsonb containment: the docket_id array contains the requested id.
    conds.push(sql`docket_id @> ${sql.json([filters.docketId])}`);
  if (filters.closesBefore !== undefined)
    // NULL closes are excluded from a closes_* filter (a NULL `<` comparison is already NULL/false, so
    // the IS NOT NULL guard is belt-and-braces + documents the intent).
    conds.push(
      sql`resolved_close_utc is not null and resolved_close_utc < ${filters.closesBefore}`,
    );
  if (filters.closesAfter !== undefined)
    conds.push(
      sql`resolved_close_utc is not null and resolved_close_utc > ${filters.closesAfter}`,
    );

  let where = sql``;
  conds.forEach((c, i) => {
    where = i === 0 ? sql`where ${c}` : sql`${where} and ${c}`;
  });

  const [countRow] = await sql<{ count: string }[]>`
    select count(*)::text as count from participation_windows ${where}
  `;
  const total = Number(countRow!.count);

  const rows = await sql<WindowRow[]>`
    select ocd_id, fr_document_number, regs_document_id, regs_object_id, docket_id, rin,
           window_type, resolved_close_utc, resolved_close_display,
           raw_fr_close_date, raw_regs_close_datetime,
           confidence, conflict_flags, status, submission_url, govinfo_url, tags,
           version, current_observation_ids, provenance, change_history
    from participation_windows
    ${where}
    order by resolved_close_utc asc nulls last, ocd_id asc
    limit ${limit} offset ${offset}
  `;

  // limit/offset are the EFFECTIVE (clamped) values actually applied — the route stamps THESE into the
  // Pagination block so a client computing ceil(total/limit) sees the honest page the server served (a
  // requested limit=10000 reports 200, not 10000), and a negative input can never reach the contract.
  return { rows: rows.map(toWindow), total, limit, offset };
}

/** getWindow — one window by ocd_id (the exact public key), contract-parsed, or null if absent. */
export async function getWindow(
  sql: Sql,
  ocdId: string,
): Promise<ParticipationWindow | null> {
  const rows = await sql<WindowRow[]>`
    select ocd_id, fr_document_number, regs_document_id, regs_object_id, docket_id, rin,
           window_type, resolved_close_utc, resolved_close_display,
           raw_fr_close_date, raw_regs_close_datetime,
           confidence, conflict_flags, status, submission_url, govinfo_url, tags,
           version, current_observation_ids, provenance, change_history
    from participation_windows
    where ocd_id = ${ocdId}
  `;
  const r = rows[0];
  return r ? toWindow(r) : null;
}

interface ObservationRow {
  observation_id: string;
  ocd_id: string;
  source: string;
  fr_document_number: string | null;
  regs_document_id: string | null;
  regs_object_id: string | null;
  payload_hash: string;
  fetched_at: Date | string;
  parser_version: string;
  raw_dates_text: string | null;
  is_extension: boolean;
  is_correction: boolean;
  is_withdrawal: boolean;
  raw: unknown;
}

/**
 * getWindowObservations — every observation feeding an ocd_id, newest fetched_at first, each parsed
 * through the Observation contract. The log keys observations by ocd_id directly (observations.ocd_id —
 * the primary derived window; the M:N observation_targets fan-out is for an extension touching N windows),
 * so a `where ocd_id = …` read returns the chain for this window. Empty if the ocd_id has no log rows.
 */
export async function getWindowObservations(
  sql: Sql,
  ocdId: string,
): Promise<Observation[]> {
  const rows = await sql<ObservationRow[]>`
    select observation_id, ocd_id, source, fr_document_number, regs_document_id, regs_object_id,
           payload_hash, fetched_at, parser_version, raw_dates_text,
           is_extension, is_correction, is_withdrawal, raw
    from observations
    where ocd_id = ${ocdId}
    order by fetched_at desc, observation_id desc
  `;
  return rows.map((r) =>
    Observation.parse({
      ...r,
      // contract carries an ISO string; postgres.js hands timestamptz back as a Date.
      fetched_at: isoOrNull(r.fetched_at)!,
    }),
  );
}

// ── conflicts (the published proof feed) ────────────────────────────────────────────────────────────

export interface ConflictFilters {
  ocdId?: string;
  limit?: number;
  offset?: number;
}

interface ConflictRow {
  ocd_id: string;
  observation_a_id: string;
  observation_b_id: string;
  source_a: string;
  source_b: string;
  conflict_flags: string[];
  govinfo_url: string | null;
  detected_at: Date | string;
  // #31 cross-window fields. ocd_id_b is NOT NULL at the DB level (DEFAULT '' = "no side B"), so it is
  // never null HERE; the '' sentinel is mapped back to the contract's null on read (see toConflict).
  conflict_scope: string;
  ocd_id_b: string;
  govinfo_url_b: string | null;
  // NOTE: resolved_at is deliberately NOT selected — it is the server-side retirement marker, NOT part
  // of the contract ConflictRecord. The feed publishes only LIVE conflicts (resolved_at IS NULL).
}

/**
 * listConflicts — the GET /conflicts proof feed: ONLY LIVE conflicts (resolved_at IS NULL), newest
 * detected_at first. resolved_at is NEVER selected/returned (it is not a contract field — see persist.ts
 * + the 0003 column comment). Each row is mapped to the ConflictRecord contract shape and parsed.
 */
export async function listConflicts(
  sql: Sql,
  filters: ConflictFilters = {},
): Promise<{
  rows: ConflictRecord[];
  total: number;
  limit: number;
  offset: number;
}> {
  const limit = clampLimit(filters.limit);
  const offset = clampOffset(filters.offset);

  // The proof feed is LIVE-only — resolved_at IS NULL is non-negotiable (never surface a dead conflict).
  let where = sql`where resolved_at is null`;
  if (filters.ocdId === "") {
    // EMPTY filter (#31 adversary B1): match NOTHING. cross_source rows carry the ocd_id_b='' sentinel,
    // so an either-side OR with '' would leak the ENTIRE cross_source feed as a foreign, scoped-looking
    // result (the forbidden "fake certainty"). An empty scope request names no window — `ocd_id = ''`
    // matches nothing (no real row has an empty ocd_id), preserving pre-Slice-1's honest total=0.
    where = sql`${where} and ocd_id = ''`;
  } else if (filters.ocdId !== undefined) {
    // EITHER-SIDE match (#31): a window must find conflicts where it is side A OR side B (the amendment
    // wants the chain conflict it is the second party to). The empty case is handled above, so here the
    // id is a real (non-empty) OcdId and the ocd_id_b='' sentinel on cross_source rows never matches it.
    where = sql`${where} and (ocd_id = ${filters.ocdId} or ocd_id_b = ${filters.ocdId})`;
  }

  const [countRow] = await sql<{ count: string }[]>`
    select count(*)::text as count from conflict_records ${where}
  `;
  const total = Number(countRow!.count);

  const rows = await sql<ConflictRow[]>`
    select ocd_id, observation_a_id, observation_b_id, source_a, source_b,
           conflict_flags, govinfo_url, detected_at,
           conflict_scope, ocd_id_b, govinfo_url_b
    from conflict_records
    ${where}
    order by detected_at desc, ocd_id asc
    limit ${limit} offset ${offset}
  `;

  // FAIL-LOUD BY DESIGN (see toWindow): reconcile validates before persisting, so a poison conflict row
  // can't be written through our pipeline; a row-level skip-and-log is future hardening for external writers.
  const mapped = rows.map((r) =>
    ConflictRecord.parse({
      ocd_id: r.ocd_id,
      observation_a_id: r.observation_a_id,
      observation_b_id: r.observation_b_id,
      source_a: r.source_a,
      source_b: r.source_b,
      conflict_flags: r.conflict_flags,
      govinfo_url: r.govinfo_url,
      detected_at: isoOrNull(r.detected_at)!,
      // #31 NULL-vs-'' SEAM (see 0006 header): DB ocd_id_b '' (the "no side B" sentinel) maps back to the
      // contract's null. A non-'' value is a real cross_window side-B window. The superRefine then holds:
      // cross_source ⇒ ocd_id_b null; cross_window ⇒ ocd_id_b present and distinct from ocd_id.
      conflict_scope: r.conflict_scope,
      ocd_id_b: r.ocd_id_b === "" ? null : r.ocd_id_b,
      govinfo_url_b: r.govinfo_url_b,
    }),
  );

  // Effective (clamped) limit/offset — the route stamps THESE into Pagination (single source of truth).
  return { rows: mapped, total, limit, offset };
}
