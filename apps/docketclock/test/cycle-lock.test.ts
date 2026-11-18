/**
 * cycle-lock.test.ts — proves the cross-process poll-cycle lock (src/poll/cycle-lock.ts):
 *   - a free lock runs the cycle and returns its value;
 *   - a lock held by ANOTHER session skips the cycle without running it;
 *   - two cycles started at once never overlap (exactly one runs);
 *   - the lock is released after the cycle resolves AND after it throws (the error still propagates);
 *   - a session that dies while holding the lock frees it (Postgres drops session locks on disconnect);
 *   - the heartbeat keeps the lock session busy during a long cycle (Neon scale-to-zero);
 *   - the lock session dying mid-cycle neither throws nor loses the cycle's result.
 *
 * Matches dead-letter.test.ts style: hand-rolled assert, out[] accumulator, failures counter, process.exit;
 * needs a THROWAWAY Postgres:
 *   DATABASE_URL=postgres://... pnpm --filter @yokel/docketclock test
 *
 * No migrations needed: advisory locks live in pg_locks, not in any table.
 */
import { createClient, createSessionClient } from "../src/db/client.js";
import { POLL_CYCLE_LOCK_KEY, withCycleLock } from "../src/poll/cycle-lock.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

const sql = createClient();
// A SEPARATE client = a separate Postgres session, standing in for a second poller process.
const other = createClient();
// The lock sessions each "process" passes to withCycleLock (one connection each).
const lockA = createSessionClient();
const lockB = createSessionClient();

async function lockHeldAnywhere(): Promise<boolean> {
  const [row] = await sql<{ n: number }[]>`
    select count(*)::int as n from pg_locks
    where locktype = 'advisory' and objid = ${POLL_CYCLE_LOCK_KEY} and granted
  `;
  return (row?.n ?? 0) > 0;
}

try {
  // ── free lock: the cycle runs and its value comes back ───────────────────────────────────────────
  {
    let ran = false;
    const r = await withCycleLock(lockA, async () => {
      ran = true;
      return 42;
    });
    assert(
      "free lock → cycle runs and returns its value",
      ran && r.acquired && r.value === 42,
      JSON.stringify(r),
    );
    assert(
      "free lock → released after the cycle resolves",
      !(await lockHeldAnywhere()),
    );
  }

  // ── held by another session: skip without running ──────────────────────────────────────────────
  {
    const held = await other.reserve();
    await held`select pg_advisory_lock(${POLL_CYCLE_LOCK_KEY}::bigint)`;
    assert(
      "pg_locks probe sees a held lock (so the 'released' checks are not vacuous)",
      await lockHeldAnywhere(),
    );
    let ran = false;
    const r = await withCycleLock(lockA, async () => {
      ran = true;
    });
    assert(
      "lock held by another session → acquired:false",
      !r.acquired,
      JSON.stringify(r),
    );
    assert("lock held by another session → cycle did NOT run", !ran);
    await held`select pg_advisory_unlock(${POLL_CYCLE_LOCK_KEY}::bigint)`;
    held.release();
  }

  // ── two cycles started together: exactly one runs, and they never overlap ─────────────────────────
  {
    let active = 0;
    let maxActive = 0;
    let runs = 0;
    const slowCycle = async () => {
      active++;
      runs++;
      maxActive = Math.max(maxActive, active);
      await new Promise((r) => setTimeout(r, 300));
      active--;
    };
    const [a, b] = await Promise.all([
      withCycleLock(lockA, slowCycle),
      withCycleLock(lockB, slowCycle),
    ]);
    const acquired = [a, b].filter((r) => r.acquired).length;
    assert(
      "concurrent cycles → exactly one acquires the lock",
      acquired === 1 && runs === 1,
      `acquired=${acquired} runs=${runs}`,
    );
    assert("concurrent cycles → never overlap", maxActive === 1);
    assert(
      "concurrent cycles → lock released afterwards",
      !(await lockHeldAnywhere()),
    );
  }

  // ── a throwing cycle: the error propagates and the lock is still released ───────────────────────
  {
    let caught: unknown = null;
    try {
      await withCycleLock(lockA, async () => {
        throw new Error("pass blew up");
      });
    } catch (err) {
      caught = err;
    }
    assert(
      "throwing cycle → error propagates to the caller",
      caught instanceof Error && caught.message === "pass blew up",
    );
    assert("throwing cycle → lock released", !(await lockHeldAnywhere()));
    const r = await withCycleLock(lockB, async () => "next");
    assert(
      "throwing cycle → the next cycle (another session) can run",
      r.acquired && r.value === "next",
    );
  }

  // ── a session that dies holding the lock frees it ───────────────────────────────────────────────
  {
    const doomed = createClient();
    const conn = await doomed.reserve();
    await conn`select pg_advisory_lock(${POLL_CYCLE_LOCK_KEY}::bigint)`;
    const whileHeld = await withCycleLock(lockA, async () => "x");
    await doomed.end({ timeout: 1 }); // the "process" dies: its session ends
    const after = await withCycleLock(lockA, async () => "y");
    assert("dead session → lock was held before it died", !whileHeld.acquired);
    assert(
      "dead session → lock freed once its session ended",
      after.acquired && after.value === "y",
      JSON.stringify(after),
    );
  }
  // ── a pool is refused: lock and unlock could land on different sessions ─────────────────────────────
  {
    let caught: unknown = null;
    try {
      await withCycleLock(sql, async () => "x");
    } catch (err) {
      caught = err;
    }
    assert(
      "pool client → refused",
      caught instanceof Error && /one-connection/.test(caught.message),
    );
    assert("pool client → no lock left held", !(await lockHeldAnywhere()));
  }

  // ── heartbeat: a long cycle keeps its lock session busy (so Neon never sees it idle) ────────────────
  {
    const holderPid = async () => {
      const [row] = await other<{ pid: number }[]>`
        select pid from pg_locks
        where locktype = 'advisory' and objid = ${POLL_CYCLE_LOCK_KEY} and granted
      `;
      return row?.pid;
    };
    let seen: { query: string; state: string } | undefined;
    const r = await withCycleLock(
      lockA,
      async () => {
        await new Promise((res) => setTimeout(res, 300));
        const pid = await holderPid();
        const [row] = await other<{ query: string; state: string }[]>`
          select query, state
          from pg_stat_activity where pid = ${pid ?? -1}
        `;
        seen = row;
        return "beat";
      },
      { heartbeatMs: 50 },
    );
    assert(
      "heartbeat → cycle still acquired and returned",
      r.acquired && r.value === "beat",
    );
    assert(
      "heartbeat → lock session is ACTIVE in pg_sleep during the cycle",
      !!seen && seen.state === "active" && /pg_sleep/.test(seen.query),
      JSON.stringify(seen),
    );
    assert("heartbeat → lock released afterwards", !(await lockHeldAnywhere()));
  }

  // ── the lock session dies mid-cycle (Neon suspend): the cycle's result stands, no throw on unlock ─────
  {
    const errors: unknown[] = [];
    let caught: unknown = null;
    let r: Awaited<ReturnType<typeof withCycleLock<string>>> | undefined;
    try {
      r = await withCycleLock(
        lockA,
        async () => {
          const [row] = await other<{ pid: number }[]>`
            select pid from pg_locks
            where locktype = 'advisory' and objid = ${POLL_CYCLE_LOCK_KEY} and granted
          `;
          await other`select pg_terminate_backend(${row!.pid})`;
          await new Promise((res) => setTimeout(res, 200));
          return "survived";
        },
        { heartbeatMs: 50, onHeartbeatError: (e) => errors.push(e) },
      );
    } catch (err) {
      caught = err;
    }
    assert(
      "dead lock session → withCycleLock does not throw",
      caught === null,
      String(caught),
    );
    assert(
      "dead lock session → cycle value returned",
      !!r?.acquired && r.value === "survived",
      JSON.stringify(r),
    );
    assert(
      "dead lock session → lock loss reported via onHeartbeatError",
      errors.some(
        (e) => e instanceof Error && /lost mid-cycle/.test(e.message),
      ),
      errors.map((e) => String(e)).join(" | "),
    );
    assert(
      "dead lock session → lock not left held",
      !(await lockHeldAnywhere()),
    );
    const next = await withCycleLock(lockA, async () => "after");
    assert(
      "dead lock session → pool still usable",
      next.acquired && next.value === "after",
    );
  }
} catch (err) {
  failures++;
  out.push(`  FAIL  unexpected error — ${(err as Error).stack ?? err}`);
} finally {
  await sql.end({ timeout: 5 });
  await other.end({ timeout: 5 });
  await lockA.end({ timeout: 5 });
  await lockB.end({ timeout: 5 });
}

console.log("cycle-lock.test.ts");
console.log(out.join("\n"));
console.log(failures === 0 ? "ALL PASS" : `${failures} FAILURE(S)`);
process.exit(failures === 0 ? 0 : 1);
