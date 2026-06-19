/**
 * Persist a reconciliation result into the DERIVED projections (0003) — and the entry point that reads
 * the Observation chain, runs the pure engine, and writes the result.
 *
 * ATOMICITY: the read (SELECT) + version-bump decision + participation_windows upsert + conflict_records
 * upsert + retirement UPDATE all run inside a SINGLE `sql.begin` transaction, so the projection and the
 * proof feed move together. A crash mid-sequence rolls the whole unit back rather than leaving the window
 * updated while the conflict feed is inconsistent.
 *
 * participation_windows is a re-derivable projection, so persisting is an UPSERT on ocd_id (NOT an
 * append). The ONE value we refuse to mutate silently is resolved_close_utc: when a re-derivation moves
 * the operative close, we BUMP `version` and APPEND a ChangeHistoryEntry (the PRIOR close + the prior
 * current_observation_ids + changed_at) to change_history — superseded deadlines live forever, exactly
 * as the contract intends. An unchanged close is an idempotent no-op refresh.
 *
 * conflict_records is INSERT-on-detection, deduped on the natural key (ocd_id, observation_a_id,
 * observation_b_id) per 0003 — re-running reconcile on the same disagreeing pair is an idempotent no-op
 * (it does NOT duplicate the row and does NOT bump the original detected_at). Stale/resolved conflicts
 * are RETIRED via a nullable resolved_at: when a re-derivation is no longer CONFLICTING, all still-open
 * rows for the ocd_id are stamped resolved_at=now; when it IS conflicting, the current pair is upserted
 * live (resolved_at=NULL) and any OTHER still-open (superseded) pair for the ocd_id is retired. The
 * proof feed publishes only live conflicts (resolved_at IS NULL).
 */
import type { Sql } from "../db/client.js";
import type { ChangeHistoryEntry, ParticipationWindow } from "@yokel/contracts";
import type { ReconcileResult } from "./reconcile.js";
import { RECONCILER_VERSION, reconcile } from "./reconcile.js";
import {
  chainAmbiguousPairs,
  chainReconcile,
  isAmendment,
  type ChainCandidate,
  type ChainConflict,
} from "./chain.js";
import { extractFr } from "./extract.js";
import type { Adjudicator } from "../adjudicator/port.js";
import { selectAdjudicator } from "../adjudicator/select.js";
import {
  adjudicateAmbiguousPairs,
  chainMaxEscalations,
} from "./chain-adjudicate.js";

export interface PersistResult {
  inserted: boolean; // true if this was a first-time insert of the window
  versionBumped: boolean; // true if resolved_close_utc changed and version advanced
}

interface StoredWindowRow {
  resolved_close_utc: string | null;
  version: number;
  change_history: ChangeHistoryEntry[];
  current_observation_ids: string[];
}

/** Compare two nullable close instants for equality (normalize via Date so offset/Z forms match). */
function sameClose(a: string | null, b: string | null): boolean {
  if (a === null || b === null) return a === b;
  const da = new Date(a).getTime();
  const db = new Date(b).getTime();
  return da === db;
}

export async function persistReconciliation(
  sql: Sql,
  result: ReconcileResult,
  now: Date = new Date(),
): Promise<PersistResult> {
  const { window, conflict } = result;

  // ATOMIC: the read-decide-version-bump and ALL writes (window upsert + conflict upsert/retirement)
  // run inside ONE transaction so the projection and the proof feed move together. A crash mid-sequence
  // can no longer leave the window updated while the conflict feed is stale/inconsistent — postgres.js
  // rolls the whole `begin` block back on any throw. `tx` is the transaction-scoped sql; every statement
  // below uses it (not the outer `sql`).
  return sql.begin(async (tx) => {
    // Read the currently-stored projection (if any) to decide insert-vs-update + version bump.
    const [stored] = await tx<StoredWindowRow[]>`
      select resolved_close_utc, version, change_history, current_observation_ids
      from participation_windows
      where ocd_id = ${window.ocd_id}
    `;

    let version = window.version;
    let changeHistory = window.change_history;
    let versionBumped = false;
    const inserted = !stored;

    if (stored) {
      const storedClose = stored.resolved_close_utc
        ? new Date(stored.resolved_close_utc).toISOString()
        : null;
      if (!sameClose(storedClose, window.resolved_close_utc)) {
        // The operative close moved — bump version + append the PRIOR close to change_history.
        version = stored.version + 1;
        const priorEntry: ChangeHistoryEntry = {
          version: stored.version,
          resolved_close_utc: storedClose,
          observation_ids: stored.current_observation_ids ?? [],
          changed_at: now.toISOString(),
        };
        changeHistory = [...(stored.change_history ?? []), priorEntry];
        versionBumped = true;
      } else {
        // Unchanged close: keep the stored version + history (idempotent refresh of the projection).
        version = stored.version;
        changeHistory = stored.change_history ?? [];
      }
    }

    const toPersist: ParticipationWindow = {
      ...window,
      version,
      change_history: changeHistory,
    };

    await tx`
      insert into participation_windows (
        ocd_id, fr_document_number, regs_document_id, regs_object_id, docket_id, rin,
        window_type, resolved_close_utc, resolved_close_display,
        raw_fr_close_date, raw_regs_close_datetime,
        confidence, conflict_flags, status, submission_url, govinfo_url, tags,
        version, current_observation_ids, provenance, change_history,
        reconciler_version, derived_at
      ) values (
        ${toPersist.ocd_id}, ${toPersist.fr_document_number}, ${toPersist.regs_document_id},
        ${toPersist.regs_object_id}, ${tx.json(toPersist.docket_id)}, ${toPersist.rin},
        ${toPersist.window_type}, ${toPersist.resolved_close_utc}, ${toPersist.resolved_close_display},
        ${toPersist.raw_fr_close_date}, ${toPersist.raw_regs_close_datetime},
        ${toPersist.confidence}, ${tx.json(toPersist.conflict_flags)}, ${toPersist.status},
        ${toPersist.submission_url}, ${toPersist.govinfo_url}, ${tx.json(toPersist.tags)},
        ${toPersist.version}, ${tx.json(toPersist.current_observation_ids)},
        ${tx.json(toPersist.provenance)}, ${tx.json(toPersist.change_history)},
        ${RECONCILER_VERSION}, ${now.toISOString()}
      )
      on conflict (ocd_id) do update set
        fr_document_number = excluded.fr_document_number,
        regs_document_id   = excluded.regs_document_id,
        regs_object_id     = excluded.regs_object_id,
        docket_id          = excluded.docket_id,
        rin                = excluded.rin,
        window_type        = excluded.window_type,
        resolved_close_utc = excluded.resolved_close_utc,
        resolved_close_display = excluded.resolved_close_display,
        raw_fr_close_date  = excluded.raw_fr_close_date,
        raw_regs_close_datetime = excluded.raw_regs_close_datetime,
        confidence         = excluded.confidence,
        conflict_flags     = excluded.conflict_flags,
        status             = excluded.status,
        submission_url     = excluded.submission_url,
        govinfo_url        = excluded.govinfo_url,
        tags               = excluded.tags,
        version            = excluded.version,
        current_observation_ids = excluded.current_observation_ids,
        provenance         = excluded.provenance,
        change_history     = excluded.change_history,
        reconciler_version = excluded.reconciler_version,
        derived_at         = excluded.derived_at
    `;

    // conflict_records — insert-on-detection, deduped on the disagreeing-pair natural key, with stale/
    // resolved-conflict RETIREMENT so the GET /conflicts proof feed never publishes dead conflicts.
    if (conflict) {
      // Current window is CONFLICTING. Upsert the current pair as LIVE (resolved_at = NULL); re-detecting
      // the SAME pair must NOT duplicate it and must NOT bump its original detected_at (idempotent
      // refresh of the metadata only — detected_at is the FIRST-detection stamp).
      // NULL-vs-'' SEAM (see 0006 header): the contract carries ocd_id_b as nullable (null for a
      // cross_source conflict — there is no side-B window), but the DB column is NOT NULL DEFAULT '' so
      // the widened unique key dedups cross_source rows (all share ''). Map contract null → DB ''.
      // reconcile emits only cross_source today, so conflict_scope is 'cross_source', ocd_id_b is '',
      // govinfo_url_b is null — but we read the fields off the ConflictRecord (defaults) so the seam is
      // already correct the moment a later slice begins emitting cross_window.
      const ocdIdB = conflict.ocd_id_b ?? "";
      await tx`
        insert into conflict_records (
          ocd_id, observation_a_id, observation_b_id, source_a, source_b,
          conflict_flags, govinfo_url, detected_at, resolved_at,
          conflict_scope, ocd_id_b, govinfo_url_b
        ) values (
          ${conflict.ocd_id}, ${conflict.observation_a_id}, ${conflict.observation_b_id},
          ${conflict.source_a}, ${conflict.source_b}, ${tx.json(conflict.conflict_flags)},
          ${conflict.govinfo_url}, ${conflict.detected_at}, ${null},
          ${conflict.conflict_scope}, ${ocdIdB}, ${conflict.govinfo_url_b}
        )
        on conflict (ocd_id, observation_a_id, observation_b_id, ocd_id_b) do update set
          conflict_flags = excluded.conflict_flags,
          govinfo_url    = excluded.govinfo_url,
          govinfo_url_b  = excluded.govinfo_url_b,
          resolved_at    = null
      `;
      // Retire every OTHER still-open conflict row for this ocd_id — a superseded pair (a newer
      // conflicting pair replaced it) must not linger live in the proof feed.
      //
      // SCOPED TO cross_source (#31 seam): a single-window FR↔Regs reconcile must NEVER collaterally
      // retire a cross_window/chain row that merely happens to name this ocd_id as side A. Such a row is
      // owned by a different (cross-window) detection pass, not by this FR↔Regs reconcile. This predicate
      // is a no-op today (no cross_window rows are emitted yet) but is the correct seam for the next slice.
      await tx`
        update conflict_records
          set resolved_at = ${now.toISOString()}
        where ocd_id = ${conflict.ocd_id}
          and resolved_at is null
          and conflict_scope = 'cross_source'
          and not (
            observation_a_id = ${conflict.observation_a_id}
            and observation_b_id = ${conflict.observation_b_id}
          )
      `;
    } else {
      // Current window is NOT conflicting — the conflict (if any) is RESOLVED. Retire ALL still-open
      // cross_source conflict rows for this ocd_id so the proof feed stops publishing a dead conflict.
      // SCOPED TO cross_source for the same reason as the supersede sweep above: a not-conflicting FR↔Regs
      // re-derivation must not retire a future cross_window row that shares this ocd_id as side A.
      await tx`
        update conflict_records
          set resolved_at = ${now.toISOString()}
        where ocd_id = ${window.ocd_id}
          and resolved_at is null
          and conflict_scope = 'cross_source'
      `;
    }

    return { inserted, versionBumped };
  });
}

export interface ReconcileOcdIdResult extends ReconcileResult {
  persist: PersistResult;
}

/**
 * Read every Observation for an ocd_id from the log, run the pure engine, persist the projection.
 * The single DB-aware orchestration point; the rulebook itself stays pure + deterministic.
 */
export async function reconcileOcdId(
  sql: Sql,
  ocdId: string,
  now: Date = new Date(),
): Promise<ReconcileOcdIdResult> {
  const rows = await sql<
    {
      observation_id: string;
      ocd_id: string;
      source: "federal_register" | "regulations_gov" | "govinfo";
      fr_document_number: string | null;
      regs_document_id: string | null;
      regs_object_id: string | null;
      payload_hash: string;
      fetched_at: Date;
      parser_version: string;
      raw_dates_text: string | null;
      is_extension: boolean;
      is_correction: boolean;
      is_withdrawal: boolean;
      is_reopening: boolean;
      raw: unknown;
    }[]
  >`
    select observation_id, ocd_id, source, fr_document_number, regs_document_id, regs_object_id,
           payload_hash, fetched_at, parser_version, raw_dates_text,
           is_extension, is_correction, is_withdrawal, is_reopening, raw
    from observations
    where ocd_id = ${ocdId}
    order by fetched_at asc
  `;

  if (rows.length === 0)
    throw new Error(`reconcileOcdId: no observations for ocd_id "${ocdId}"`);

  const observations = rows.map((r) => ({
    ...r,
    // postgres.js returns timestamptz as a Date; the contract carries an ISO string.
    fetched_at:
      r.fetched_at instanceof Date ? r.fetched_at.toISOString() : r.fetched_at,
  }));

  const result = reconcile(observations, now);
  const persist = await persistReconciliation(sql, result, now);
  return { ...result, persist };
}

// ─────────────────────────────────────────────────────────────────────────────────────────────────
// CROSS-WINDOW (chain) pass — #31 Slice 3. The DB-aware sibling of persistReconciliation/reconcileOcdId,
// but for the cross_window engine (chain.ts). Unlike the per-ocd_id cross_source reconcile, the chain
// pass is a FULL SWEEP: it reads ALL windows-joined-to-their-FR-observation, computes the complete live
// cross_window set in one pure call, then UPSERTs the live set and retires every stale cross_window row.
// ─────────────────────────────────────────────────────────────────────────────────────────────────

export interface ChainPersistResult {
  /** cross_window rows live after this sweep (upserted with resolved_at = null). */
  conflictsLive: number;
  /** still-open cross_window rows retired (resolved_at stamped) because they left the live set. */
  retired: number;
}

/**
 * Stable composite key over a cross_window pair (used by the not-in-live-set retirement sweep). The SQL
 * retirement query rebuilds this SAME key by string concatenation, so the two must agree exactly.
 *
 * SEPARATOR INVARIANT: `|` is a safe delimiter because NEITHER component can contain it — an OcdId is
 * pinned by the contract regex (no `|`; verified by the adversary) and observation ids are UUIDs. If a
 * future id format ever admitted `|`, two distinct tuples could collapse to one key and a stale row could
 * silently fail to retire; at that point switch to a composite-column compare
 * (`(ocd_id, ocd_id_b, observation_a_id, observation_b_id) = ANY(VALUES …)`) which needs no delimiter.
 */
function pairKey(c: {
  ocd_id: string;
  ocd_id_b: string;
  observation_a_id: string;
  observation_b_id: string;
}): string {
  return `${c.ocd_id}|${c.ocd_id_b}|${c.observation_a_id}|${c.observation_b_id}`;
}

/**
 * persistChainConflicts — UPSERT the freshly-computed live cross_window set, then RETIRE every still-open
 * cross_window row whose pair is NOT in that live set. ATOMIC: the whole sweep runs in ONE transaction so
 * the upsert and retirement move together (a crash mid-sweep rolls back rather than leaving the feed in a
 * half-retired state). Mirrors persistReconciliation's atomicity discipline.
 *
 * SCOPE ISOLATION (the load-bearing #31 invariant): every statement is scoped to
 * `conflict_scope = 'cross_window'`. This pass NEVER touches a cross_source row — symmetric to Slice 1
 * scoping the per-ocd_id sweeps to cross_source. So a chain sweep can never collaterally retire a live
 * FR↔Regs conflict that merely shares an ocd_id on one side, and the cross_source reconcile can never
 * retire a chain conflict.
 *
 * RETIREMENT (the part Slice 1 did NOT do): because the chain pass is a full sweep each cycle, a global
 * retire of stale cross_window rows is correct. If the live set is empty, retire ALL open cross_window
 * rows; else retire open cross_window rows whose composite pair key is not among the live tuples. PG18
 * array binding uses `any(${arr}::text[])` (bare array + cast) — never sql.array().
 */
export async function persistChainConflicts(
  sql: Sql,
  conflicts: ChainConflict[],
  now: Date = new Date(),
): Promise<ChainPersistResult> {
  const nowIso = now.toISOString();
  return sql.begin(async (tx) => {
    // UPSERT each live cross_window conflict. detected_at is PRESERVED on re-detection (absent from the DO
    // UPDATE SET); resolved_at is reset to null so a previously-retired-then-relinked pair revives.
    //
    // ARBITER SAFETY: the `on conflict` key omits conflict_scope yet can never overwrite a cross_source row.
    // A cross_window row always carries a non-empty ocd_id_b (B's distinct window), while a cross_source row
    // carries the '' sentinel — and the contract superRefine FORBIDS a cross_source ConflictRecord from
    // having a non-empty ocd_id_b (it would fail .parse before reaching persist). So the 4-tuple keys of the
    // two scopes are structurally disjoint on ocd_id_b; this insert can only ever match another cross_window
    // row. (If the cross_source path ever emitted a non-empty ocd_id_b the index would need conflict_scope.)
    for (const c of conflicts) {
      await tx`
        insert into conflict_records (
          ocd_id, observation_a_id, observation_b_id, source_a, source_b,
          conflict_flags, govinfo_url, detected_at, resolved_at,
          conflict_scope, ocd_id_b, govinfo_url_b
        ) values (
          ${c.ocd_id}, ${c.observation_a_id}, ${c.observation_b_id},
          ${c.source_a}, ${c.source_b}, ${tx.json(c.conflict_flags)},
          ${c.govinfo_url}, ${c.detected_at}, ${null},
          ${c.conflict_scope}, ${c.ocd_id_b}, ${c.govinfo_url_b}
        )
        on conflict (ocd_id, observation_a_id, observation_b_id, ocd_id_b) do update set
          conflict_flags = excluded.conflict_flags,
          govinfo_url    = excluded.govinfo_url,
          govinfo_url_b  = excluded.govinfo_url_b,
          resolved_at    = null
      `;
    }

    // RETIRE stale cross_window rows — strictly scoped to conflict_scope='cross_window'.
    let retired = 0;
    if (conflicts.length === 0) {
      // Empty live set ⇒ every open cross_window row is stale.
      const rows = await tx`
        update conflict_records
          set resolved_at = ${nowIso}
        where conflict_scope = 'cross_window'
          and resolved_at is null
        returning conflict_id
      `;
      retired = rows.length;
    } else {
      // Retire open cross_window rows whose composite pair key is NOT among the live tuples. The composite
      // key (ocd_id|ocd_id_b|observation_a_id|observation_b_id) is rebuilt in SQL and compared against the
      // live keys via NOT (key = any(${arr}::text[])) — PG18-safe bare-array binding + cast.
      const liveKeys = conflicts.map(pairKey);
      const rows = await tx`
        update conflict_records
          set resolved_at = ${nowIso}
        where conflict_scope = 'cross_window'
          and resolved_at is null
          and not (
            ocd_id || '|' || ocd_id_b || '|' || observation_a_id || '|' || observation_b_id
            = any(${liveKeys}::text[])
          )
        returning conflict_id
      `;
      retired = rows.length;
    }

    return { conflictsLive: conflicts.length, retired };
  });
}

export interface ChainReconcileOnceResult extends ChainPersistResult {
  /** total windows-with-an-FR-observation read as candidates. */
  candidates: number;
  /** how many candidates carry an amendment signal (extension/correction/withdrawal). */
  amendments: number;
  /** CONFIDENT (A,B) links the deterministic engine emitted (rules 1–5). */
  linked: number;
  /** ambiguous pairs surfaced (structural rules pass, rule-2 corroboration fails) — the escalation set. */
  ambiguous: number;
  /** ambiguous pairs whose verdict was applied from the cache this cycle (free replays — no LLM call). */
  cacheHits: number;
  /** FRESH LLM calls made this cycle (cache misses that had budget). ≤ cap. A throw still counts. */
  llmCalls: number;
  /** affirmed pairs promoted to a cross_window link (each carries `llm_corroborated`). */
  llmLinked: number;
  /** uncached pairs DEFERRED this cycle because the per-cycle fresh-call budget was exhausted. */
  deferred: number;
}

/** Optional knobs for chainReconcileOnce — both default to the prod-safe path (null adapter, env cap). */
export interface ChainReconcileOnceOptions {
  /**
   * The adjudicator to escalate ambiguous pairs to. DEFAULTS to selectAdjudicator() — which is
   * NullAdjudicator (abstain) until the integrator provisions a key (Slice 3c), so prod is a NO-OP and
   * the persisted set is byte-identical to the confident-only set. Tests inject a spy / NullAdjudicator.
   */
  adjudicator?: Adjudicator;
  /** Per-cycle escalation cap. Defaults to chainMaxEscalations() (env CHAIN_MAX_ESCALATIONS_PER_CYCLE / 25). */
  cap?: number;
}

/**
 * chainReconcileOnce — read the candidate set (every participation_window joined to its LATEST
 * federal_register observation, so the amendment flags + DATES text reflect the current FR doc), build
 * ChainCandidate[], run the pure chain engine, and persist. The single DB-aware orchestration point; the
 * rulebook (chain.ts) stays pure + deterministic.
 *
 * Candidate join: a window contributes a candidate only when it HAS a federal_register observation (the
 * chain conflict is FR-doc ↔ FR-doc). We pick the LATEST FR observation per ocd_id by fetched_at. is_*
 * flags + raw come straight off that observation row; publication_date / docket_ids / rin / dates_text are
 * extracted from the FR raw payload (extractFr) — the same projection reconcile.ts uses, so the chain pass
 * sees identical structured fields.
 */
export async function chainReconcileOnce(
  sql: Sql,
  now: Date = new Date(),
  options: ChainReconcileOnceOptions = {},
): Promise<ChainReconcileOnceResult> {
  const adjudicator = options.adjudicator ?? selectAdjudicator();
  const cap = options.cap ?? chainMaxEscalations();
  // LATEST federal_register observation per window, joined to the window's status + resolved close +
  // govinfo anchor. distinct on (w.ocd_id) ordered by fetched_at desc gives the freshest FR doc.
  // INVARIANT (N1): this read THROWS on any DB failure (postgres.js rejects), so it can NEVER silently
  // return [] and trip the retire-all-cross_window path below. The empty live set only retires-all on a
  // GENUINELY empty candidate set (no FR-backed windows), never on a transient DB error.
  const rows = await sql<
    {
      ocd_id: string;
      fr_observation_id: string;
      is_extension: boolean;
      is_correction: boolean;
      is_withdrawal: boolean;
      is_reopening: boolean;
      raw: unknown;
      status: string;
      resolved_close_utc: Date | string | null;
      govinfo_url: string | null;
    }[]
  >`
    select distinct on (w.ocd_id)
      w.ocd_id,
      o.observation_id as fr_observation_id,
      o.is_extension, o.is_correction, o.is_withdrawal, o.is_reopening, o.raw,
      w.status, w.resolved_close_utc, w.govinfo_url
    from participation_windows w
    join observations o
      on o.ocd_id = w.ocd_id and o.source = 'federal_register'
    order by w.ocd_id, o.fetched_at desc, o.observation_id desc
  `;

  const candidates: ChainCandidate[] = rows.map((r) => {
    const fr = extractFr(r.raw);
    return {
      ocd_id: r.ocd_id,
      fr_observation_id: r.fr_observation_id,
      fr_document_number: fr.documentNumber,
      docket_ids: fr.docketIds,
      rin: fr.rin,
      rins: fr.rins,
      is_extension: r.is_extension,
      is_correction: r.is_correction,
      is_withdrawal: r.is_withdrawal,
      is_reopening: r.is_reopening,
      title: fr.title,
      publication_date: fr.publicationDate,
      govinfo_url: r.govinfo_url,
      dates_text: fr.datesText,
      status: r.status,
      resolved_close_utc:
        r.resolved_close_utc instanceof Date
          ? r.resolved_close_utc.toISOString()
          : r.resolved_close_utc,
    };
  });

  // Count amendments by the SAME predicate the engine links on (single source of truth — see chain.ts).
  const amendments = candidates.filter(isAmendment).length;

  // CONFIDENT links — the deterministic engine (rules 1–5). Byte-identical to today's output. Under the
  // null adapter the merged set below equals exactly this (Invariant 1).
  const confident = chainReconcile(candidates, now);

  // AMBIGUOUS tail — pairs the confident path UNDER-LINKS (structural rules pass, rule-2 corroboration
  // fails). Escalate them to the adjudicator; only an `affirm` promotes a pair to a cross_window link
  // (carrying `llm_corroborated`). A null adapter / outage / reject / uncertain → no promotion (worst case
  // is today's confident-only output). Errors are isolated per-pair inside adjudicateAmbiguousPairs.
  const ambiguousPairs = chainAmbiguousPairs(candidates, now);
  const adjudicated = await adjudicateAmbiguousPairs(
    sql,
    adjudicator,
    ambiguousPairs,
    now,
    cap,
  );

  // MERGE confident + LLM-affirmed, then RE-SORT with the SAME total order the engine uses so the persisted
  // set is stable regardless of which links were LLM-promoted. (A confident and a promoted pair can never
  // collide on the 4-tuple key: an ambiguous pair fails rule 2, so it is never also a confident link.)
  const merged = [...confident, ...adjudicated.links].sort(
    (x, y) =>
      x.ocd_id.localeCompare(y.ocd_id) ||
      x.ocd_id_b.localeCompare(y.ocd_id_b) ||
      x.observation_a_id.localeCompare(y.observation_a_id) ||
      x.observation_b_id.localeCompare(y.observation_b_id),
  );

  const persisted = await persistChainConflicts(sql, merged, now);

  return {
    candidates: candidates.length,
    amendments,
    linked: confident.length,
    ambiguous: adjudicated.ambiguous,
    cacheHits: adjudicated.cacheHits,
    llmCalls: adjudicated.llmCalls,
    llmLinked: adjudicated.llmLinked,
    deferred: adjudicated.deferred,
    ...persisted,
  };
}
