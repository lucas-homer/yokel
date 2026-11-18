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
 * HEARTBEAT: while the cycle runs, the lock session runs back-to-back `pg_sleep(heartbeatMs)` queries
 * (default 5s), so Postgres always shows one ACTIVE backend. Neon scales the compute to zero after 5
 * minutes of inactivity, and a cycle's passes spend minutes in HTTP and LLM calls between short queries.
 * On 2026-11-18 the compute suspended mid-cycle twice: at 16:06 every connection was cut and the final
 * unlock on a dead reserved connection crashed the process; at 17:06 it suspended again even with a
 * `select 1` every 60s, so short, spaced-out queries do not count as activity. The heartbeat keeps the
 * compute awake only while a cycle holds the lock; between cycles it still scales to zero. A failed
 * heartbeat is reported via `onHeartbeatError`, never thrown. If the session dies anyway, the lock went
 * with it: the next query reconnects, the final unlock finds nothing to release, and that loss is
 * reported through the same callback.
 *
 * EFFECT (ADR 0018, slice 2): `cycleLock` is the Effect-native form; `withCycleLock` is the Promise
 * wrapper existing callers and tests use. The shape is `Effect.acquireUseRelease`: ACQUIRE starts the
 * keep-busy heartbeat as its own fiber, USE runs the cycle, RELEASE interrupts the heartbeat and unlocks.
 * Release runs whether the cycle succeeds, fails or is interrupted (a SIGTERM drain), which replaces the
 * hand-rolled `stopping` flag + `finally`. On a one-connection client postgres.js queues the unlock behind
 * any in-flight `pg_sleep`, so interrupting the heartbeat mid-sleep cannot reorder the two.
 */
import { Data, Effect, Fiber } from "effect";
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
 * Run a cycle only if no other session holds the poll-cycle lock. `{ acquired: false }` without running it
 * when the lock is held elsewhere. The lock is released whether the cycle succeeds or fails; its error
 * propagates to the caller. `session` must be a one-connection client (`createSessionClient`), so the
 * lock, heartbeats and unlock all share one Postgres session.
 */
export interface CycleLockOptions {
  key?: number;
  /** Length of each back-to-back `pg_sleep` on the lock session while the cycle runs, and the pause after
   *  a failed one. Default 5s. */
  heartbeatMs?: number;
  /** Called when a heartbeat or the final unlock fails, or the lock was lost (the cycle is not interrupted). */
  onHeartbeatError?: (err: unknown) => void;
}

export const DEFAULT_HEARTBEAT_MS = 5_000;

/** A failed query on the lock session (or a misused client), carrying the original error. */
export class LockSessionError extends Data.TaggedError("LockSessionError")<{
  readonly cause: unknown;
}> {}

const onSession = <A>(query: () => PromiseLike<A>) =>
  Effect.tryPromise({
    try: () => query(),
    catch: (cause) => new LockSessionError({ cause }),
  });

/**
 * The Effect form. Fails (with the driver's error) only if TAKING the lock fails; heartbeat and unlock
 * problems go to `onHeartbeatError` and never fail the cycle.
 */
export const cycleLock = <A, E, R>(
  session: Sql,
  cycle: Effect.Effect<A, E, R>,
  opts: CycleLockOptions = {},
): Effect.Effect<CycleLockResult<A>, E | LockSessionError, R> =>
  Effect.gen(function* () {
    if (session.options.max !== 1) {
      return yield* new LockSessionError({
        cause: new Error(
          "withCycleLock needs a one-connection client (createSessionClient); a pool could unlock on another session",
        ),
      });
    }
    const key = opts.key ?? POLL_CYCLE_LOCK_KEY;
    const heartbeatMs = opts.heartbeatMs ?? DEFAULT_HEARTBEAT_MS;
    const onError = opts.onHeartbeatError ?? (() => {});
    const report = (err: unknown) => Effect.sync(() => onError(err));

    const [row] = yield* onSession(
      () => session<{ locked: boolean }[]>`
        select pg_try_advisory_lock(${key}::bigint) as locked
      `,
    );
    if (!row?.locked) return { acquired: false } as const;

    // Keep the lock session ACTIVE (not merely connected) for the whole cycle: back-to-back
    // `pg_sleep(heartbeatMs)` queries. A short `select 1` every minute did NOT stop Neon suspending the
    // compute mid-cycle (2026-11-18 17:06): its idle detector evidently samples for active backends, and a
    // 1 ms query is almost never seen. A backend that is always mid-query is. On error (the compute
    // restarted under us) report, wait one interval and go again: the one-connection client reconnects.
    const keepBusy = onSession(
      () => session`select pg_sleep(${heartbeatMs / 1000})`,
    ).pipe(
      Effect.catch((err) =>
        report(err.cause).pipe(Effect.andThen(Effect.sleep(heartbeatMs))),
      ),
      Effect.forever,
      Effect.interruptible,
    );

    const unlock = onSession(
      () => session<{ unlocked: boolean }[]>`
        select pg_advisory_unlock(${key}::bigint) as unlocked
      `,
    ).pipe(
      // false = this session no longer holds the lock: the original session died mid-cycle (Postgres
      // dropped its lock) and the client reconnected. Nothing to release, but the overlap guard lapsed.
      Effect.flatMap(([u]) =>
        u?.unlocked
          ? Effect.void
          : report(
              new Error(
                "poll-cycle lock was lost mid-cycle (its session ended)",
              ),
            ),
      ),
      Effect.catch((err) => report(err.cause)),
    );

    return yield* Effect.acquireUseRelease(
      Effect.forkDetach(keepBusy),
      () => Effect.map(cycle, (value) => ({ acquired: true, value }) as const),
      (heartbeat) => Fiber.interrupt(heartbeat).pipe(Effect.andThen(unlock)),
    );
  });

/** The Promise form: `fn` is the cycle. Same contract as `cycleLock`. */
export async function withCycleLock<T>(
  session: Sql,
  fn: () => Promise<T>,
  opts: CycleLockOptions = {},
): Promise<CycleLockResult<T>> {
  return Effect.runPromise(
    cycleLock(
      session,
      Effect.tryPromise({ try: () => fn(), catch: (cause) => cause }),
      opts,
    ).pipe(
      // Rethrow what the caller saw before: the driver's error, or the cycle's own.
      Effect.catch((err) =>
        Effect.die(err instanceof LockSessionError ? err.cause : err),
      ),
    ),
  );
}
