/**
 * cycle-lock.ts — a Postgres advisory lock that makes "one poll cycle at a time" hold ACROSS processes.
 *
 * WHY: the ingest/reconcile path is single-writer (see the CONCURRENCY(single-writer) notes in
 * src/ingest/observe.ts and src/reconcile/persist.ts — there is no per-ocd_id lock). Today that holds
 * because exactly one long-lived poller process runs a self-rescheduling loop (src/poll/run.ts). Once a
 * cycle can be started from OUTSIDE that loop — a scheduled trigger that runs one cycle and exits (the
 * planned Cloudflare Cron → Container path), a manual `--once` run beside the live poller, or two pollers
 * during a cutover — two cycles could overlap and race the latest-hash dedupe and the projection upsert.
 * The lock closes that gap in the database itself, whatever starts the cycle.
 *
 * HOW: `pg_try_advisory_lock` is SESSION-scoped, so the lock and its unlock must run on the SAME
 * connection. We reserve one connection from the pool for the whole cycle (postgres.js `sql.reserve()`),
 * take the lock there without waiting, run the cycle on the normal pool, then unlock and release. If the
 * process dies mid-cycle the session ends and Postgres drops the lock on its own — no stale lock to clear.
 * A busy lock returns `{ acquired: false }` instead of waiting: a cycle that finds another one running
 * should skip, not queue behind it (the next trigger will pick the work up).
 */
import type { Sql } from "../db/client.js";

/**
 * The advisory-lock key for the poll cycle. Arbitrary but FIXED: every process that runs a cycle must use
 * the same value. 0x646b636c is ASCII "dkcl" (DocketClock), chosen to be recognisable in pg_locks.
 */
export const POLL_CYCLE_LOCK_KEY = 0x646b636c;

export type CycleLockResult<T> =
  | { acquired: true; value: T }
  | { acquired: false };

/**
 * Run `fn` only if no other session holds the poll-cycle lock. Returns `{ acquired: false }` without
 * running `fn` when the lock is held elsewhere. The lock is released (and the reserved connection
 * returned) whether `fn` resolves or throws; an error from `fn` propagates to the caller.
 */
export async function withCycleLock<T>(
  sql: Sql,
  fn: () => Promise<T>,
  key: number = POLL_CYCLE_LOCK_KEY,
): Promise<CycleLockResult<T>> {
  const conn = await sql.reserve();
  try {
    const [row] = await conn<{ locked: boolean }[]>`
      select pg_try_advisory_lock(${key}::bigint) as locked
    `;
    if (!row?.locked) return { acquired: false };
    try {
      return { acquired: true, value: await fn() };
    } finally {
      await conn`select pg_advisory_unlock(${key}::bigint)`;
    }
  } finally {
    conn.release();
  }
}
