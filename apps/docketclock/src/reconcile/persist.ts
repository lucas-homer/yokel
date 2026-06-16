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
      await tx`
        insert into conflict_records (
          ocd_id, observation_a_id, observation_b_id, source_a, source_b,
          conflict_flags, govinfo_url, detected_at, resolved_at
        ) values (
          ${conflict.ocd_id}, ${conflict.observation_a_id}, ${conflict.observation_b_id},
          ${conflict.source_a}, ${conflict.source_b}, ${tx.json(conflict.conflict_flags)},
          ${conflict.govinfo_url}, ${conflict.detected_at}, ${null}
        )
        on conflict (ocd_id, observation_a_id, observation_b_id) do update set
          conflict_flags = excluded.conflict_flags,
          govinfo_url    = excluded.govinfo_url,
          resolved_at    = null
      `;
      // Retire every OTHER still-open conflict row for this ocd_id — a superseded pair (a newer
      // conflicting pair replaced it) must not linger live in the proof feed.
      await tx`
        update conflict_records
          set resolved_at = ${now.toISOString()}
        where ocd_id = ${conflict.ocd_id}
          and resolved_at is null
          and not (
            observation_a_id = ${conflict.observation_a_id}
            and observation_b_id = ${conflict.observation_b_id}
          )
      `;
    } else {
      // Current window is NOT conflicting — the conflict (if any) is RESOLVED. Retire ALL still-open
      // conflict rows for this ocd_id so the proof feed stops publishing a dead conflict.
      await tx`
        update conflict_records
          set resolved_at = ${now.toISOString()}
        where ocd_id = ${window.ocd_id}
          and resolved_at is null
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
      raw: unknown;
    }[]
  >`
    select observation_id, ocd_id, source, fr_document_number, regs_document_id, regs_object_id,
           payload_hash, fetched_at, parser_version, raw_dates_text,
           is_extension, is_correction, is_withdrawal, raw
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
