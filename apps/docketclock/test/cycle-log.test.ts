/**
 * cycle-log.test.ts — the durable per-cycle record (src/poll/cycle-log.ts, migrations/0014_poll_cycles.sql):
 *   - scalarSummary keeps only finite numbers and booleans;
 *   - cycleOutcome: failed > skipped > any failed pass > ok;
 *   - recordPollCycle writes one row with its duration, outcome, trace id and passes array;
 *   - the outcome check constraint rejects an unknown outcome.
 *
 * Matches dead-letter.test.ts style; needs a THROWAWAY Postgres (the schema is dropped and re-migrated):
 *   DATABASE_URL=postgres://... pnpm --filter @yokel/docketclock test
 */
import { createClient } from "../src/db/client.js";
import { runMigrations } from "../src/db/migrate.js";
import {
  cycleOutcome,
  recordPollCycle,
  scalarSummary,
  type PassRecord,
} from "../src/poll/cycle-log.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

const sql = createClient();

try {
  await sql.unsafe(
    "drop schema if exists public cascade; create schema public;",
  );
  const applied = await runMigrations(sql);
  assert(
    "migration 0014_poll_cycles applies",
    applied.includes("0014_poll_cycles.sql"),
  );

  // ── scalarSummary ────────────────────────────────────────────────────────────────────────────────
  {
    const s = scalarSummary({
      fetched: 3,
      changed: 0,
      truncated: false,
      nan: Number.NaN,
      inf: Number.POSITIVE_INFINITY,
      label: "x",
      nested: { a: 1 },
      list: [1, 2],
      nothing: null,
    });
    assert(
      "scalarSummary keeps finite numbers and booleans only",
      JSON.stringify(s) ===
        JSON.stringify({ fetched: 3, changed: 0, truncated: false }),
      JSON.stringify(s),
    );
    assert(
      "scalarSummary of a non-object is empty",
      Object.keys(scalarSummary(undefined)).length === 0 &&
        Object.keys(scalarSummary(7)).length === 0,
    );
  }

  // ── cycleOutcome ─────────────────────────────────────────────────────────────────────────────────
  {
    const okPass: PassRecord = { name: "fr", ok: true, ms: 5, summary: {} };
    const badPass: PassRecord = {
      name: "regs",
      ok: false,
      ms: 7,
      summary: {},
      error: "boom",
    };
    assert(
      "all passes ok -> ok",
      cycleOutcome({ failed: false, skipped: false, passes: [okPass] }) ===
        "ok",
    );
    assert(
      "a failed pass -> pass_failed",
      cycleOutcome({
        failed: false,
        skipped: false,
        passes: [okPass, badPass],
      }) === "pass_failed",
    );
    assert(
      "skipped wins over passes",
      cycleOutcome({ failed: false, skipped: true, passes: [badPass] }) ===
        "skipped",
    );
    assert(
      "failed wins over everything",
      cycleOutcome({ failed: true, skipped: true, passes: [badPass] }) ===
        "failed",
    );
  }

  // ── recordPollCycle ──────────────────────────────────────────────────────────────────────────────
  {
    const startedAt = new Date("2026-11-18T22:00:00.000Z");
    const finishedAt = new Date("2026-11-18T22:01:30.250Z");
    const passes: PassRecord[] = [
      {
        name: "fr",
        ok: true,
        ms: 1200,
        summary: { fetched: 4, truncated: false },
      },
      {
        name: "regs",
        ok: false,
        ms: 300,
        summary: {},
        error: "429 Too Many Requests",
      },
    ];
    await recordPollCycle(sql, {
      startedAt,
      finishedAt,
      outcome: "pass_failed",
      runOnce: true,
      traceId: "abc123",
      passes,
    });
    const rows = await sql<
      {
        started_at: Date;
        duration_ms: number;
        outcome: string;
        run_once: boolean;
        trace_id: string | null;
        passes: PassRecord[];
      }[]
    >`select started_at, duration_ms, outcome, run_once, trace_id, passes from poll_cycles`;
    assert("one row written", rows.length === 1, `got ${rows.length}`);
    const r = rows[0]!;
    assert(
      "started_at round-trips",
      r.started_at.getTime() === startedAt.getTime(),
    );
    assert(
      "duration_ms is finished - started",
      r.duration_ms === 90_250,
      String(r.duration_ms),
    );
    assert(
      "outcome and run_once stored",
      r.outcome === "pass_failed" && r.run_once === true,
    );
    assert("trace_id stored", r.trace_id === "abc123");
    assert(
      "passes stored as a JSON array in order",
      Array.isArray(r.passes) &&
        r.passes.map((p) => p.name).join(",") === "fr,regs" &&
        r.passes[0]!.summary.fetched === 4 &&
        r.passes[1]!.error === "429 Too Many Requests",
      JSON.stringify(r.passes),
    );
    // Per-pass trends are plain SQL over the array.
    const [trend] = await sql<{ fetched: number }[]>`
      select sum((p->'summary'->>'fetched')::int)::int as fetched
      from poll_cycles, jsonb_array_elements(passes) p
      where p->>'name' = 'fr'
    `;
    assert(
      "per-pass summary is queryable",
      trend?.fetched === 4,
      JSON.stringify(trend),
    );

    await recordPollCycle(sql, {
      startedAt,
      finishedAt: startedAt,
      outcome: "skipped",
      runOnce: false,
      traceId: null,
      passes: [],
    });
    const [skipped] = await sql<{ n: number }[]>`
      select count(*)::int as n from poll_cycles
      where outcome = 'skipped' and trace_id is null and passes = '[]'::jsonb and duration_ms = 0
    `;
    assert("a skipped cycle with no trace is stored", skipped?.n === 1);
  }

  // ── the outcome check constraint ─────────────────────────────────────────────────────────────────
  {
    let rejected = false;
    try {
      await recordPollCycle(sql, {
        startedAt: new Date(),
        finishedAt: new Date(),
        outcome: "bogus" as never,
        runOnce: false,
        traceId: null,
        passes: [],
      });
    } catch {
      rejected = true;
    }
    assert("an unknown outcome is rejected", rejected);
  }
} catch (err) {
  failures++;
  out.push(`  FAIL  unexpected error — ${String(err)}`);
} finally {
  await sql.end({ timeout: 5 });
}

console.log(`cycle-log.test.ts\n${out.join("\n")}`);
console.log(failures === 0 ? "ALL PASS" : `${failures} FAILURE(S)`);
process.exit(failures === 0 ? 0 : 1);
