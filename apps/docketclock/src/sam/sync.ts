/**
 * The SAM.gov pass: sync the Federal Hierarchy (agency tree) and Contract Opportunities into the
 * append-only sam_observations log and its two projections (federal_orgs, contract_deadlines).
 * docs/plans/sam-gov.md has the design; migrations/0015_sam_gov.sql the tables.
 *
 * Shape of one source's sync (the same state machine for both, in sam_sync_state):
 *   backfill  page through everything once (FH: all orgs; Opportunities: every notice whose response
 *             deadline falls in the next year), one page per budgeted request, resuming at the stored
 *             offset across cycles and days.
 *   delta     once a day (at most every DELTA_EVERY_MS), page through what changed since the last window
 *             (FH: updateddatefrom; Opportunities: postedFrom; an amendment re-posts the notice).
 *
 * Budget: every request first takes one unit from sam_request_budget (SAM_DAILY_REQUEST_CAP per UTC day).
 * No unit, no request. A 429 marks the day exhausted, and the pass ends quietly: running out of a daily
 * quota is the normal state of a 10/day key, not a failure (so it never pages anyone). FH goes first: it
 * is small, and opportunities resolve their agency against it.
 *
 * Single writer: runs inside the poll cycle's lock like every other pass.
 */
import type { Sql, SqlHandle } from "../db/client.js";
import { payloadHash } from "../sources/payload.js";
import { easternCalendarDate } from "../reconcile/eastern-date.js";
import {
  FH_PAGE_SIZE,
  OPP_PAGE_SIZE,
  SAM_DAILY_REQUEST_CAP,
  SAM_PARSER_VERSION,
  SamRequestError,
  addDays,
  federalOrgSubjectId,
  fhOrgsUrl,
  noticeUrl,
  opportunitiesUrl,
  opportunitySubjectId,
  pageOf,
  parseOpportunity,
  parseOrg,
  samApiKey,
  samGetJson,
  type ParsedOpportunity,
  type ParsedOrg,
} from "../sources/sam-gov.js";

/** A delta window runs at most this often (the data updates daily; the budget is per day). */
export const DELTA_EVERY_MS = 20 * 60 * 60 * 1000;

type SamSource = "sam_federal_hierarchy" | "sam_opportunities";

export interface SamSyncSummary {
  skippedNoKey: boolean;
  budgetExhausted: boolean;
  requests: number;
  orgsSeen: number;
  orgsInserted: number;
  opportunitiesSeen: number;
  opportunitiesInserted: number;
  deadlinesChanged: number;
  fhBackfillDone: boolean;
  opportunitiesBackfillDone: boolean;
}

export interface SamSyncDeps {
  /** injectable for tests; defaults to the real (budget-blind) GET */
  get?: (url: string) => Promise<unknown>;
  apiKey?: string | null;
}

// ── budget ──────────────────────────────────────────────────────────────────────────────────────────

const utcDay = (now: Date) => now.toISOString().slice(0, 10);

/** Take one request from today's budget. False when the cap is reached or the day is marked exhausted. */
export async function takeRequest(
  sql: SqlHandle,
  now: Date,
  cap = SAM_DAILY_REQUEST_CAP,
): Promise<boolean> {
  const rows = await sql`
    insert into sam_request_budget as b (day, requests) values (${utcDay(now)}, 1)
    on conflict (day) do update set requests = b.requests + 1
      where b.requests < ${cap} and b.exhausted_at is null
    returning requests
  `;
  return rows.length > 0;
}

export async function markExhausted(sql: SqlHandle, now: Date): Promise<void> {
  await sql`
    insert into sam_request_budget as b (day, requests, exhausted_at) values (${utcDay(now)}, 0, ${now})
    on conflict (day) do update set exhausted_at = coalesce(b.exhausted_at, ${now})
  `;
}

// ── log + projections ───────────────────────────────────────────────────────────────────────────────

/** Append a payload unless its hash equals the latest one for this entity (an unchanged re-fetch). */
export async function ingestSamObservation(
  tx: SqlHandle,
  o: {
    source: SamSource;
    entityId: string;
    subjectId: string;
    raw: unknown;
    sourceModifiedAt: Date | null;
    fetchedAt: Date;
  },
): Promise<{ inserted: boolean; observationId: string }> {
  const hash = payloadHash(o.raw);
  const [latest] = await tx<{ observation_id: string; payload_hash: string }[]>`
    select observation_id, payload_hash from sam_observations
    where source = ${o.source} and entity_id = ${o.entityId}
    order by fetched_at desc limit 1
  `;
  if (latest && latest.payload_hash === hash) {
    return { inserted: false, observationId: latest.observation_id };
  }
  const [row] = await tx<{ observation_id: string }[]>`
    insert into sam_observations
      (source, entity_id, subject_id, payload_hash, fetched_at, source_modified_at, parser_version, raw)
    values
      (${o.source}, ${o.entityId}, ${o.subjectId}, ${hash}, ${o.fetchedAt}, ${o.sourceModifiedAt},
       ${SAM_PARSER_VERSION}, ${tx.json(o.raw as never)})
    returning observation_id
  `;
  return { inserted: true, observationId: row!.observation_id };
}

export async function upsertFederalOrg(
  tx: SqlHandle,
  org: ParsedOrg,
  observationId: string,
  now: Date,
): Promise<void> {
  await tx`
    insert into federal_orgs
      (fhorgid, subject_id, name, org_type, status, parent_fhorgid, agency_code, cgac,
       source_created_at, source_updated_at, observation_id, first_seen_at, last_seen_at)
    values
      (${org.fhorgid}, ${federalOrgSubjectId(org.fhorgid)}, ${org.name}, ${org.orgType}, ${org.status},
       ${org.parentFhorgid}, ${org.agencyCode}, ${org.cgac}, ${org.createdAt}, ${org.updatedAt},
       ${observationId}, ${now}, ${now})
    on conflict (fhorgid) do update set
      name = excluded.name, org_type = excluded.org_type, status = excluded.status,
      parent_fhorgid = excluded.parent_fhorgid, agency_code = excluded.agency_code, cgac = excluded.cgac,
      source_created_at = excluded.source_created_at, source_updated_at = excluded.source_updated_at,
      observation_id = excluded.observation_id, last_seen_at = excluded.last_seen_at
  `;
}

/**
 * The agency a notice belongs to, from its fullParentPathCode ("047.4732.47QTCA" = department.subtier.
 * office): the sub-tier whose agency code is the second segment, else the department matching the first
 * (by agency code or CGAC). Null when FH has neither yet; a later re-sync of the notice fills it in.
 */
export async function resolveAgency(
  tx: SqlHandle,
  pathCode: string | null,
): Promise<string | null> {
  if (!pathCode) return null;
  const [dept, sub] = pathCode.split(".");
  if (sub) {
    const [r] = await tx<{ fhorgid: string }[]>`
      select fhorgid from federal_orgs
      where agency_code = ${sub} and org_type ilike 'sub-tier%'
      order by (status = 'ACTIVE') desc nulls last, fhorgid limit 1
    `;
    if (r) return r.fhorgid;
  }
  if (dept) {
    const [r] = await tx<{ fhorgid: string }[]>`
      select fhorgid from federal_orgs
      where parent_fhorgid is null and (agency_code = ${dept} or ${dept} = any (cgac))
      order by (status = 'ACTIVE') desc nulls last, fhorgid limit 1
    `;
    if (r) return r.fhorgid;
  }
  return null;
}

/** Upsert a notice's current state. Returns true when its response deadline (raw text) changed. */
export async function upsertContractDeadline(
  tx: SqlHandle,
  opp: ParsedOpportunity,
  observationId: string,
  now: Date,
): Promise<boolean> {
  const agency = await resolveAgency(tx, opp.fullParentPathCode);
  const [prev] = await tx<{ response_deadline_raw: string | null }[]>`
    select response_deadline_raw from contract_deadlines where notice_id = ${opp.noticeId}
  `;
  const changed =
    prev !== undefined &&
    prev.response_deadline_raw !== opp.responseDeadlineRaw;
  await tx`
    insert into contract_deadlines
      (notice_id, subject_id, title, solicitation_number, notice_type, base_type, active, posted_at,
       response_deadline, response_deadline_raw, archive_date, full_parent_path_code,
       full_parent_path_name, agency_fhorgid, naics_code, set_aside_code, source_url, observation_id,
       deadline_changed_at, first_seen_at, last_seen_at)
    values
      (${opp.noticeId}, ${opportunitySubjectId(opp.noticeId)}, ${opp.title}, ${opp.solicitationNumber},
       ${opp.type}, ${opp.baseType}, ${opp.active}, ${opp.postedAt}, ${opp.responseDeadline},
       ${opp.responseDeadlineRaw}, ${opp.archiveDate}, ${opp.fullParentPathCode},
       ${opp.fullParentPathName}, ${agency}, ${opp.naicsCode}, ${opp.setAsideCode},
       ${noticeUrl(opp.noticeId)}, ${observationId}, ${null}, ${now}, ${now})
    on conflict (notice_id) do update set
      title = excluded.title, solicitation_number = excluded.solicitation_number,
      notice_type = excluded.notice_type, base_type = excluded.base_type, active = excluded.active,
      posted_at = excluded.posted_at, response_deadline = excluded.response_deadline,
      response_deadline_raw = excluded.response_deadline_raw, archive_date = excluded.archive_date,
      full_parent_path_code = excluded.full_parent_path_code,
      full_parent_path_name = excluded.full_parent_path_name,
      agency_fhorgid = coalesce(excluded.agency_fhorgid, contract_deadlines.agency_fhorgid),
      naics_code = excluded.naics_code, set_aside_code = excluded.set_aside_code,
      observation_id = excluded.observation_id,
      deadline_changed_at = case when ${changed}::boolean then ${now}::timestamptz
        else contract_deadlines.deadline_changed_at end,
      last_seen_at = excluded.last_seen_at
  `;
  return changed;
}

// ── the per-source state machine ────────────────────────────────────────────────────────────────────

interface SyncState {
  phase: "backfill" | "delta";
  page_offset: number;
  window_from: string | null;
  window_to: string | null;
  last_completed_at: Date | null;
}

interface SourceSpec {
  source: SamSource;
  pageSize: number;
  listKey: "orglist" | "opportunitiesData";
  /** the backfill window, fixed when the backfill starts so offsets stay stable across days */
  backfillWindow: (today: string) => { from: string; to: string };
  url: (apiKey: string, s: SyncState) => string;
  /** ingest one item in the page's transaction; null = unparseable (skipped) */
  ingest: (
    tx: SqlHandle,
    item: unknown,
    now: Date,
  ) => Promise<{ inserted: boolean; deadlineChanged: boolean } | null>;
}

const asDate = (v: unknown): string | null =>
  v === null || v === undefined
    ? null
    : v instanceof Date
      ? v.toISOString().slice(0, 10)
      : String(v).slice(0, 10);

async function readState(
  sql: SqlHandle,
  source: SamSource,
): Promise<SyncState | null> {
  const [r] = await sql<
    {
      phase: "backfill" | "delta";
      page_offset: number;
      window_from: unknown;
      window_to: unknown;
      last_completed_at: Date | null;
    }[]
  >`
    select phase, page_offset, window_from, window_to, last_completed_at
    from sam_sync_state where source = ${source}
  `;
  return r
    ? {
        ...r,
        window_from: asDate(r.window_from),
        window_to: asDate(r.window_to),
      }
    : null;
}

async function writeState(
  sql: SqlHandle,
  source: SamSource,
  s: SyncState,
): Promise<void> {
  await sql`
    insert into sam_sync_state
      (source, phase, page_offset, window_from, window_to, last_completed_at, updated_at)
    values
      (${source}, ${s.phase}, ${s.page_offset}, ${s.window_from}, ${s.window_to},
       ${s.last_completed_at}, now())
    on conflict (source) do update set
      phase = excluded.phase, page_offset = excluded.page_offset, window_from = excluded.window_from,
      window_to = excluded.window_to, last_completed_at = excluded.last_completed_at,
      updated_at = now()
  `;
}

const FH: SourceSpec = {
  source: "sam_federal_hierarchy",
  pageSize: FH_PAGE_SIZE,
  listKey: "orglist",
  backfillWindow: (today) => ({ from: today, to: today }),
  url: (apiKey, s) =>
    s.phase === "backfill"
      ? fhOrgsUrl({ apiKey, offset: s.page_offset })
      : fhOrgsUrl({
          apiKey,
          offset: s.page_offset,
          updatedFrom: s.window_from ?? undefined,
          updatedTo: s.window_to ?? undefined,
        }),
  ingest: async (tx, item, now) => {
    const org = parseOrg(item);
    if (!org) return null;
    const r = await ingestSamObservation(tx, {
      source: "sam_federal_hierarchy",
      entityId: org.fhorgid,
      subjectId: federalOrgSubjectId(org.fhorgid),
      raw: item,
      sourceModifiedAt: org.updatedAt,
      fetchedAt: now,
    });
    await upsertFederalOrg(tx, org, r.observationId, now);
    return { inserted: r.inserted, deadlineChanged: false };
  },
};

const OPPORTUNITIES: SourceSpec = {
  source: "sam_opportunities",
  pageSize: OPP_PAGE_SIZE,
  listKey: "opportunitiesData",
  // Everything still open: response deadline from today through the API's 1-year window maximum.
  backfillWindow: (today) => ({ from: today, to: addDays(today, 364) }),
  url: (apiKey, s) =>
    opportunitiesUrl({
      apiKey,
      offset: s.page_offset,
      by: s.phase === "backfill" ? "deadline" : "posted",
      from: s.window_from!,
      to: s.window_to!,
    }),
  ingest: async (tx, item, now) => {
    const opp = parseOpportunity(item);
    if (!opp) return null;
    const r = await ingestSamObservation(tx, {
      source: "sam_opportunities",
      entityId: opp.noticeId,
      subjectId: opportunitySubjectId(opp.noticeId),
      raw: item,
      sourceModifiedAt: opp.postedAt,
      fetchedAt: now,
    });
    // An unchanged re-fetch still refreshes last_seen_at (the projection's "still listed" signal).
    const changed = await upsertContractDeadline(tx, opp, r.observationId, now);
    return { inserted: r.inserted, deadlineChanged: changed };
  },
};

interface SourceRun {
  requests: number;
  seen: number;
  inserted: number;
  deadlinesChanged: number;
  budgetExhausted: boolean;
  backfillDone: boolean;
}

async function runSource(
  sql: Sql,
  spec: SourceSpec,
  apiKey: string,
  get: (url: string) => Promise<unknown>,
  now: Date,
): Promise<SourceRun> {
  const run: SourceRun = {
    requests: 0,
    seen: 0,
    inserted: 0,
    deadlinesChanged: 0,
    budgetExhausted: false,
    backfillDone: false,
  };
  // SAM dates are Eastern calendar days.
  const today = easternCalendarDate(now);
  let state = await readState(sql, spec.source);
  if (!state) {
    const w = spec.backfillWindow(today);
    state = {
      phase: "backfill",
      page_offset: 0,
      window_from: w.from,
      window_to: w.to,
      last_completed_at: null,
    };
    await writeState(sql, spec.source, state);
  }
  if (state.phase === "delta") {
    run.backfillDone = true;
    const fresh =
      state.last_completed_at &&
      now.getTime() - new Date(state.last_completed_at).getTime() <
        DELTA_EVERY_MS;
    // A window still in progress (offset > 0) keeps going regardless of freshness.
    if (fresh && state.page_offset === 0) return run;
    if (state.page_offset === 0) state = { ...state, window_to: today };
  }

  for (;;) {
    if (!(await takeRequest(sql, now))) {
      run.budgetExhausted = true;
      return run;
    }
    run.requests++;
    let body: unknown;
    try {
      body = await get(spec.url(apiKey, state));
    } catch (err) {
      if (err instanceof SamRequestError && err.status === 429) {
        await markExhausted(sql, now);
        run.budgetExhausted = true;
        return run;
      }
      throw err;
    }
    const { items, total } = pageOf(body, spec.listKey);
    const current: SyncState = state;
    const next = await sql.begin(async (tx) => {
      for (const item of items) {
        const r = await spec.ingest(tx, item, now);
        if (!r) continue;
        run.seen++;
        if (r.inserted) run.inserted++;
        if (r.deadlineChanged) run.deadlinesChanged++;
      }
      const offset = current.page_offset + items.length;
      const done =
        items.length < spec.pageSize || (total !== null && offset >= total);
      const s: SyncState = done
        ? {
            phase: "delta",
            page_offset: 0,
            // The next delta window starts where this one (or the backfill) ended: overlap one day so a
            // partial day is re-read; the hash dedupe makes the overlap free.
            window_from:
              current.phase === "backfill" ? today : current.window_to,
            window_to: null,
            last_completed_at: now,
          }
        : { ...current, page_offset: offset };
      await writeState(tx, spec.source, s);
      return s;
    });
    state = next;
    if (state.phase === "delta" && state.page_offset === 0) {
      run.backfillDone = true;
      return run;
    }
  }
}

/** One SAM pass: FH then Opportunities, within today's request budget. No key = skipped, not failed. */
export async function samSyncOnce(
  sql: Sql,
  now: Date,
  deps: SamSyncDeps = {},
): Promise<SamSyncSummary> {
  const apiKey = deps.apiKey === undefined ? samApiKey() : deps.apiKey;
  const summary: SamSyncSummary = {
    skippedNoKey: apiKey === null,
    budgetExhausted: false,
    requests: 0,
    orgsSeen: 0,
    orgsInserted: 0,
    opportunitiesSeen: 0,
    opportunitiesInserted: 0,
    deadlinesChanged: 0,
    fhBackfillDone: false,
    opportunitiesBackfillDone: false,
  };
  if (!apiKey) return summary;
  const get = deps.get ?? samGetJson;

  const fh = await runSource(sql, FH, apiKey, get, now);
  summary.requests += fh.requests;
  summary.orgsSeen = fh.seen;
  summary.orgsInserted = fh.inserted;
  summary.fhBackfillDone = fh.backfillDone;
  if (fh.budgetExhausted) {
    summary.budgetExhausted = true;
    return summary;
  }
  const opp = await runSource(sql, OPPORTUNITIES, apiKey, get, now);
  summary.requests += opp.requests;
  summary.opportunitiesSeen = opp.seen;
  summary.opportunitiesInserted = opp.inserted;
  summary.deadlinesChanged = opp.deadlinesChanged;
  summary.opportunitiesBackfillDone = opp.backfillDone;
  summary.budgetExhausted = opp.budgetExhausted;
  return summary;
}
