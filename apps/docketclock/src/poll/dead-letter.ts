/**
 * Bounded-retry / dead-letter persistence (issue #21). Reads/writes the per-(source, document) failure
 * ledger in `poll_dead_letter` (0005). Like cursor.ts this is MUTABLE OPERATIONAL STATE, NOT the
 * append-only spine: the observation log alone re-derives every window, so this ledger is a pure
 * resilience optimization (it bounds how long a permanently-failing doc may wedge a poller before it is
 * dead-lettered and drained on a slow sweep). It can be dropped/reset with zero loss of the audit trail,
 * and therefore — exactly like cursor.ts — these are plain UPSERT/DELETE operations, NOT appends.
 *
 * SOURCE-AGNOSTIC: both pollers share these helpers, keyed by (source, document_key). `document_key` is
 * the natural per-source id — regs_document_id for Regs, fr_document_number for FR.
 *
 * CONSECUTIVE-FAILURE semantics (see 0005): `attempts` counts CONSECUTIVE failures. ANY success clears
 * the row (clearDeadLetter), so a recovered doc resets to zero. dead_lettered_at is set ONCE when the
 * threshold is first crossed and never moves later.
 *
 * NEWLY-DEAD-LETTERED (the #21 follow-up fix): recordFailure also reports `newlyDeadLettered` — true ONLY
 * on the single call that transitions dead_lettered_at from NULL → set (the doc crossed the threshold on
 * THIS very call). Callers gate the loud DEAD-LETTER alert + summary.deadLettered++ on this, NOT on the
 * level-triggered `deadLettered` (>= threshold), which stays true on every SUBSEQUENT failure of an
 * already-dead-lettered doc and would otherwise re-fire the alert + re-count it every cycle (cry-wolf).
 *
 * NOTE(no array params): every query here is keyed by SCALAR source/document_key, so none needs an array
 * param — deliberately, to sidestep the PG18 cold-connection `sql.array(...)` Parse-time trap documented
 * in fr-poll.ts. If a future query ever needs an array, pass a bare JS array with an explicit `::text[]`
 * cast, NOT sql.array().
 */
import type { Sql } from "../db/client.js";

const MAX_ERROR_LEN = 500; // truncate last_error so a giant stack/payload can't bloat the ledger row

function truncateError(msg: string | undefined): string | null {
  if (msg === undefined || msg === null) return null;
  return msg.length > MAX_ERROR_LEN ? msg.slice(0, MAX_ERROR_LEN) : msg;
}

/**
 * Record ONE failed attempt for (source, key). Upserts: attempts += 1, last_failed_at = now,
 * last_error = errorMsg (truncated), first_failed_at = coalesce(existing, now). When the NEW attempts
 * count reaches `threshold`, set dead_lettered_at = coalesce(existing, now) — IDEMPOTENT: once set it
 * never moves later (so "how long dead-lettered" is stable across re-failures). Returns the new attempts
 * count, whether the doc is now (at-or-past-threshold) dead-lettered, and whether THIS call is the one that
 * crossed the threshold (newlyDeadLettered — for the loud-alert gate).
 *
 * newlyDeadLettered is detected via the PRE-update dead_lettered_at: a `prior` CTE captures the existing
 * value BEFORE the upsert, and newlyDeadLettered = (old_dl was NULL) && (the returned dead_lettered_at is
 * now set). Scalar-keyed throughout (no array params) — PG18-safe, per the module note.
 */
export async function recordFailure(
  sql: Sql,
  source: string,
  key: string,
  errorMsg: string | undefined,
  now: Date,
  threshold: number,
): Promise<{
  attempts: number;
  deadLettered: boolean;
  newlyDeadLettered: boolean;
}> {
  const err = truncateError(errorMsg);
  const nowIso = now.toISOString();
  const [row] = await sql<
    { attempts: number; dead_lettered_at: Date | null; old_dl: Date | null }[]
  >`
    with prior as (
      select dead_lettered_at as old_dl
      from poll_dead_letter
      where source = ${source} and document_key = ${key}
    )
    insert into poll_dead_letter (
      source, document_key, attempts, first_failed_at, last_failed_at, last_error,
      dead_lettered_at, updated_at
    )
    values (
      ${source}, ${key}, 1, ${nowIso}, ${nowIso}, ${err},
      case when 1 >= ${threshold} then ${nowIso}::timestamptz else null end, now()
    )
    on conflict (source, document_key) do update set
      attempts        = poll_dead_letter.attempts + 1,
      last_failed_at  = ${nowIso},
      last_error      = ${err},
      -- first_failed_at stays as the original (coalesce keeps the existing non-null value).
      first_failed_at = coalesce(poll_dead_letter.first_failed_at, ${nowIso}),
      -- dead_lettered_at: set ONCE when the (post-increment) attempts cross the threshold; never moved.
      dead_lettered_at = case
        when poll_dead_letter.dead_lettered_at is not null then poll_dead_letter.dead_lettered_at
        when poll_dead_letter.attempts + 1 >= ${threshold} then ${nowIso}::timestamptz
        else null
      end,
      updated_at = now()
    returning attempts, dead_lettered_at, (select old_dl from prior) as old_dl
  `;
  const attempts = row!.attempts;
  // newlyDeadLettered: the PRE-update value was NULL and the post-update value is now set → THIS call
  // crossed the threshold. On a fresh insert (no prior row) old_dl is NULL, so a threshold==1 first
  // failure correctly reports newlyDeadLettered=true.
  const newlyDeadLettered =
    row!.old_dl === null && row!.dead_lettered_at !== null;
  return { attempts, deadLettered: attempts >= threshold, newlyDeadLettered };
}

/**
 * Clear (DELETE) the ledger row for (source, key) on ANY success — a normal ingest OR a successful retry.
 * Consecutive-failure semantics: a recovered doc resets cleanly. Returns true if a row actually existed
 * (so callers can count a "recovered" doc only when it had been failing), false if there was nothing to
 * clear (the common, hot-path case where the doc was never failing).
 */
export async function clearDeadLetter(
  sql: Sql,
  source: string,
  key: string,
): Promise<boolean> {
  const rows = await sql`
    delete from poll_dead_letter
    where source = ${source} and document_key = ${key}
    returning document_key
  `;
  return rows.length > 0;
}

/**
 * The dead-lettered docs DUE for a slow-drain retry: dead_lettered_at is set AND we have not re-attempted
 * them recently. The throttle uses the SAME coalesce-to-eligible idiom as the regs_poll_watch re-poll
 * sweep: coalesce(last_retry_at, dead_lettered_at) < retryStaleBefore — a never-retried dead-letter
 * coalesces to its dead_lettered_at (so it becomes due once dead_lettered_at is older than the cutoff),
 * and after each retry attempt last_retry_at advances, so it is not re-attempted again until it goes
 * stale again. This keeps the drain SLOW (it must never become a hot retry loop).
 */
export async function selectDeadLetteredForRetry(
  sql: Sql,
  source: string,
  retryStaleBefore: Date,
): Promise<{ document_key: string }[]> {
  return sql<{ document_key: string }[]>`
    select document_key
    from poll_dead_letter
    where source = ${source}
      and dead_lettered_at is not null
      and coalesce(last_retry_at, dead_lettered_at) < ${retryStaleBefore.toISOString()}
    order by document_key
  `;
}

/**
 * Record a FAILED slow-drain retry of an already-dead-lettered doc: bump last_retry_at = now (advancing
 * the drain throttle so it is not re-attempted until stale again), last_failed_at = now, attempts += 1,
 * last_error = errorMsg. A SUCCESSFUL retry calls clearDeadLetter instead, so this only ever runs on a
 * still-failing dead-letter and never moves dead_lettered_at (the doc was already dead-lettered).
 */
export async function markRetryAttempt(
  sql: Sql,
  source: string,
  key: string,
  now: Date,
  errorMsg?: string,
): Promise<void> {
  const err = truncateError(errorMsg);
  const nowIso = now.toISOString();
  await sql`
    update poll_dead_letter set
      last_retry_at  = ${nowIso},
      last_failed_at = ${nowIso},
      attempts       = attempts + 1,
      last_error     = ${err},
      updated_at     = now()
    where source = ${source} and document_key = ${key}
  `;
}

/**
 * The set of currently DEAD-LETTERED document_keys for `source` (dead_lettered_at not null). Used by
 * pollFrOnce to SKIP re-fetching dead-lettered docs on the hot differential path (they are drained only
 * by the slow retry sweep). Docs still in bounded retry (dead_lettered_at null) are NOT in this set — FR
 * still re-fetches those every cycle, which is the correct transient-failure behavior.
 */
export async function deadLetteredKeys(
  sql: Sql,
  source: string,
): Promise<Set<string>> {
  const rows = await sql<{ document_key: string }[]>`
    select document_key
    from poll_dead_letter
    where source = ${source} and dead_lettered_at is not null
  `;
  return new Set(rows.map((r) => r.document_key));
}
