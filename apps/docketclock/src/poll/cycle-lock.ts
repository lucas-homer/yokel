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
 * connection. The caller passes a dedicated ONE-connection client (db/client.ts `createSessionClient`);
 * we take the lock there without waiting, the cycle runs on the normal pool, then we unlock. If the
 * process dies mid-cycle the session ends and Postgres drops the lock on its own — no stale lock to clear.
 * (Not `sql.reserve()`: postgres.js crashes the process on a query to a reserved connection whose socket
 * has closed — exactly what happened in the incident below. A max:1 client reconnects instead.)
 * A busy lock returns `{ acquired: false }` instead of waiting: a cycle that finds another one running
 * should skip, not queue behind it (the next trigger will pick the work up).
 *
 * HEARTBEAT: while the cycle runs we send `select 1` on the reserved connection every `heartbeatMs`
 * (default 60s). Neon scales the compute to zero after 5 minutes WITHOUT QUERIES — idle open connections do
 * not count — and a cycle can spend longer than that in pure HTTP work (the GovInfo sweep). On 2026-11-18
 * the compute suspended mid-cycle, every connection was cut, chain reconcile failed with EPIPE and the
 * final unlock on the dead reserved connection crashed the process. The heartbeat keeps the compute awake only while a cycle holds the
 * lock; between cycles it still sleeps. A failed heartbeat is reported via `onHeartbeatError`, never thrown.
 * If the session dies anyway, the lock went with it: the next query reconnects, the final unlock finds
 * nothing to release, and that loss is reported through the same callback.
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
 * running `fn` when the lock is held elsewhere. The lock is released whether `fn` resolves or throws; an
 * error from `fn` propagates to the caller. `session` must be a one-connection client
 * (`createSessionClient`), so the lock, heartbeats and unlock all share one Postgres session.
 */
export interface CycleLockOptions {
  key?: number;
  /** Interval between keep-alive queries on the lock connection while `fn` runs. Default 60s. */
  heartbeatMs?: number;
  /** Called when a heartbeat or the final unlock fails, or the lock was lost (the cycle is not interrupted). */
  onHeartbeatError?: (err: unknown) => void;
}

export const DEFAULT_HEARTBEAT_MS = 60_000;

export async function withCycleLock<T>(
  session: Sql,
  fn: () => Promise<T>,
  opts: CycleLockOptions = {},
): Promise<CycleLockResult<T>> {
  if (session.options.max !== 1) {
    throw new Error(
      "withCycleLock needs a one-connection client (createSessionClient); a pool could unlock on another session",
    );
  }
  const key = opts.key ?? POLL_CYCLE_LOCK_KEY;
  const heartbeatMs = opts.heartbeatMs ?? DEFAULT_HEARTBEAT_MS;
  const onError = opts.onHeartbeatError ?? (() => {});
  const [row] = await session<{ locked: boolean }[]>`
    select pg_try_advisory_lock(${key}::bigint) as locked
  `;
  if (!row?.locked) return { acquired: false };

  // One heartbeat in flight at a time; the unlock waits for it so the two never interleave.
  let inFlight: Promise<void> = Promise.resolve();
  let beating = false;
  const timer = setInterval(() => {
    if (beating) return;
    beating = true;
    inFlight = session`select 1`
      .then(() => undefined)
      .catch(onError)
      .finally(() => {
        beating = false;
      });
  }, heartbeatMs);
  timer.unref?.();
  try {
    return { acquired: true, value: await fn() };
  } finally {
    clearInterval(timer);
    await inFlight;
    try {
      const [u] = await session<{ unlocked: boolean }[]>`
        select pg_advisory_unlock(${key}::bigint) as unlocked
      `;
      // false = this session no longer holds the lock: the original session died mid-cycle (Postgres
      // dropped its lock) and the client reconnected. Nothing to release, but the overlap guard lapsed.
      if (!u?.unlocked) {
        onError(
          new Error("poll-cycle lock was lost mid-cycle (its session ended)"),
        );
      }
    } catch (err) {
      onError(err);
    }
  }
}
