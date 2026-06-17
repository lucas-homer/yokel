/**
 * dead-letter.test.ts — proves the source-agnostic bounded-retry / dead-letter ledger module (issue #21):
 * recordFailure (increments, flips deadLettered AT the threshold, idempotent dead_lettered_at,
 * first_failed_at pinned, last_error truncated), clearDeadLetter (deletes + returns existed-boolean),
 * selectDeadLetteredForRetry (the coalesce(last_retry_at, dead_lettered_at) drain throttle), markRetryAttempt,
 * and deadLetteredKeys.
 *
 * Matches poll.test.ts style: hand-rolled assert, out[] accumulator, failures counter, process.exit; a DB
 * section guarded by a THROWAWAY Postgres:
 *   DATABASE_URL=postgres://... pnpm --filter @yokel/docketclock test
 *
 * These are pure DB unit tests on the ledger module — no poller, no network, no fakes needed.
 */
import { createClient } from "../src/db/client.js";
import { runMigrations } from "../src/db/migrate.js";
import {
  recordFailure,
  clearDeadLetter,
  selectDeadLetteredForRetry,
  markRetryAttempt,
  deadLetteredKeys,
} from "../src/poll/dead-letter.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

const REGS = "regulations_gov";
const FR = "federal_register";
const NOW = new Date("2026-06-01T00:00:00Z");

const sql = createClient();
try {
  await sql.unsafe(
    "drop schema if exists public cascade; create schema public;",
  );
  const applied = await runMigrations(sql);
  assert(
    "migration 0005 applies (poll_dead_letter)",
    applied.includes("0005_poll_dead_letter.sql"),
    applied.join(", "),
  );
  const [tbl] = await sql<{ tablename: string }[]>`
    select tablename from pg_tables where tablename = 'poll_dead_letter'
  `;
  assert("poll_dead_letter table exists", !!tbl, tbl?.tablename ?? "missing");

  // ── recordFailure: increments + flips deadLettered AT the threshold ────────────────────────────────
  {
    const KEY = "DOC-COUNT-1";
    const threshold = 3;
    const r1 = await recordFailure(sql, REGS, KEY, "boom1", NOW, threshold);
    assert(
      "recordFailure: first failure → attempts=1, not dead-lettered (< threshold)",
      r1.attempts === 1 && r1.deadLettered === false,
      `attempts=${r1.attempts} dl=${r1.deadLettered}`,
    );
    const r2 = await recordFailure(
      sql,
      REGS,
      KEY,
      "boom2",
      new Date(NOW.getTime() + 1000),
      threshold,
    );
    assert(
      "recordFailure: second failure → attempts=2, still not dead-lettered",
      r2.attempts === 2 && r2.deadLettered === false,
      `attempts=${r2.attempts} dl=${r2.deadLettered}`,
    );
    assert(
      "recordFailure: a sub-threshold failure is NOT newlyDeadLettered",
      r2.newlyDeadLettered === false,
      String(r2.newlyDeadLettered),
    );
    const r3 = await recordFailure(
      sql,
      REGS,
      KEY,
      "boom3",
      new Date(NOW.getTime() + 2000),
      threshold,
    );
    assert(
      "recordFailure: third failure AT threshold → attempts=3, deadLettered=true",
      r3.attempts === 3 && r3.deadLettered === true,
      `attempts=${r3.attempts} dl=${r3.deadLettered}`,
    );
    assert(
      "recordFailure: the THRESHOLD-CROSSING call reports newlyDeadLettered=true (NULL→set)",
      r3.newlyDeadLettered === true,
      String(r3.newlyDeadLettered),
    );
    const [row] = await sql<
      {
        attempts: number;
        first_failed_at: Date;
        dead_lettered_at: Date | null;
        last_error: string | null;
      }[]
    >`
      select attempts, first_failed_at, dead_lettered_at, last_error
      from poll_dead_letter where source = ${REGS} and document_key = ${KEY}
    `;
    assert(
      "recordFailure: dead_lettered_at is SET once the threshold is crossed",
      row!.dead_lettered_at !== null,
      String(row!.dead_lettered_at),
    );
    assert(
      "recordFailure: first_failed_at is PINNED to the first failure (not the latest)",
      row!.first_failed_at.toISOString() === NOW.toISOString(),
      row!.first_failed_at.toISOString(),
    );
    assert(
      "recordFailure: last_error reflects the latest failure",
      row!.last_error === "boom3",
      String(row!.last_error),
    );

    // IDEMPOTENT dead_lettered_at: a fourth failure must NOT move dead_lettered_at later.
    const dlAt = row!.dead_lettered_at!.toISOString();
    const r4 = await recordFailure(
      sql,
      REGS,
      KEY,
      "boom4",
      new Date(NOW.getTime() + 9_999_999),
      threshold,
    );
    const [row4] = await sql<{ dead_lettered_at: Date }[]>`
      select dead_lettered_at from poll_dead_letter where source = ${REGS} and document_key = ${KEY}
    `;
    assert(
      "recordFailure: dead_lettered_at is IDEMPOTENT (a later failure never moves it)",
      row4!.dead_lettered_at.toISOString() === dlAt,
      `${dlAt} -> ${row4!.dead_lettered_at.toISOString()}`,
    );
    assert(
      "recordFailure: attempts keep climbing past the threshold (still deadLettered)",
      r4.attempts === 4 && r4.deadLettered === true,
      `attempts=${r4.attempts}`,
    );
    assert(
      "recordFailure: a SUBSEQUENT failure of an already-dead-lettered doc is NOT newlyDeadLettered (no re-fire)",
      r4.newlyDeadLettered === false,
      String(r4.newlyDeadLettered),
    );
  }

  // ── newlyDeadLettered on a threshold==1 FIRST failure (fresh insert, no prior row) ──────────────────
  {
    const KEY = "DOC-NEWLY-1";
    const r1 = await recordFailure(sql, REGS, KEY, "boom", NOW, 1);
    assert(
      "recordFailure: a threshold=1 first failure (fresh insert) reports newlyDeadLettered=true",
      r1.newlyDeadLettered === true && r1.deadLettered === true,
      `newly=${r1.newlyDeadLettered} dl=${r1.deadLettered}`,
    );
    const r2 = await recordFailure(sql, REGS, KEY, "boom", NOW, 1);
    assert(
      "recordFailure: the next failure of that same doc is NOT newlyDeadLettered",
      r2.newlyDeadLettered === false,
      String(r2.newlyDeadLettered),
    );
  }

  // ── last_error truncation (~500 chars) ──────────────────────────────────────────────────────────────
  {
    const KEY = "DOC-LONGERR";
    const huge = "x".repeat(2000);
    await recordFailure(sql, REGS, KEY, huge, NOW, 5);
    const [row] = await sql<{ last_error: string }[]>`
      select last_error from poll_dead_letter where source = ${REGS} and document_key = ${KEY}
    `;
    assert(
      "recordFailure: last_error is truncated to ~500 chars",
      row!.last_error.length === 500,
      String(row!.last_error.length),
    );
  }

  // ── clearDeadLetter: deletes + returns existed-boolean ──────────────────────────────────────────────
  {
    const KEY = "DOC-CLEAR";
    await recordFailure(sql, REGS, KEY, "boom", NOW, 5);
    const existed = await clearDeadLetter(sql, REGS, KEY);
    assert(
      "clearDeadLetter: returns true when a row existed (it was failing)",
      existed === true,
    );
    const [gone] = await sql<{ count: string }[]>`
      select count(*)::text as count from poll_dead_letter where source = ${REGS} and document_key = ${KEY}
    `;
    assert(
      "clearDeadLetter: the row is DELETED (consecutive-failure reset)",
      gone!.count === "0",
      gone!.count,
    );
    const notExisted = await clearDeadLetter(sql, REGS, KEY);
    assert(
      "clearDeadLetter: returns false when there was nothing to clear (hot-path no-op)",
      notExisted === false,
    );
  }

  // ── consecutive-failure reset: clear then fail again starts from 1 ──────────────────────────────────
  {
    const KEY = "DOC-RESET";
    await recordFailure(sql, REGS, KEY, "a", NOW, 5);
    await recordFailure(sql, REGS, KEY, "b", NOW, 5); // attempts=2
    await clearDeadLetter(sql, REGS, KEY); // recovered → reset
    const again = await recordFailure(sql, REGS, KEY, "c", NOW, 5);
    assert(
      "CONSECUTIVE: after a clear, the next failure starts counting from 1 again",
      again.attempts === 1,
      String(again.attempts),
    );
  }

  // ── selectDeadLetteredForRetry: honors the coalesce(last_retry_at, dead_lettered_at) throttle ───────
  {
    await sql`delete from poll_dead_letter`;
    const threshold = 1; // 1 failure dead-letters immediately, so dead_lettered_at = the failure time
    // Dead-lettered LONG ago (eligible) vs just now (not yet due).
    const oldKey = "DOC-OLD-DL";
    const freshKey = "DOC-FRESH-DL";
    const longAgo = new Date(NOW.getTime() - 10 * 3_600_000); // 10h before NOW
    await recordFailure(sql, REGS, oldKey, "boom", longAgo, threshold);
    await recordFailure(sql, REGS, freshKey, "boom", NOW, threshold);

    // A still-in-bounded-retry row (NOT dead-lettered) must NEVER be selected.
    const brKey = "DOC-BOUNDED";
    await recordFailure(sql, REGS, brKey, "boom", longAgo, 99); // threshold 99 → never dead-lettered

    const cutoff = new Date(NOW.getTime() - 6 * 3_600_000); // due if dead-lettered > 6h ago
    const due = await selectDeadLetteredForRetry(sql, REGS, cutoff);
    const dueKeys = new Set(due.map((r) => r.document_key));
    assert(
      "selectDeadLetteredForRetry: a doc dead-lettered LONG ago (> cutoff) IS due",
      dueKeys.has(oldKey),
      [...dueKeys].join(","),
    );
    assert(
      "selectDeadLetteredForRetry: a doc dead-lettered just now (< cutoff) is NOT due (throttle)",
      !dueKeys.has(freshKey),
      [...dueKeys].join(","),
    );
    assert(
      "selectDeadLetteredForRetry: a still-in-bounded-retry doc (dead_lettered_at NULL) is NEVER due",
      !dueKeys.has(brKey),
      [...dueKeys].join(","),
    );

    // markRetryAttempt advances last_retry_at → the once-due doc is no longer due (coalesce uses last_retry_at).
    await markRetryAttempt(sql, REGS, oldKey, NOW, "still broken");
    const due2 = await selectDeadLetteredForRetry(sql, REGS, cutoff);
    assert(
      "markRetryAttempt: a re-attempted doc is NO LONGER due (last_retry_at advanced past the cutoff)",
      !due2.some((r) => r.document_key === oldKey),
      due2.map((r) => r.document_key).join(","),
    );
    const [bumped] = await sql<{ attempts: number }[]>`
      select attempts from poll_dead_letter where source = ${REGS} and document_key = ${oldKey}
    `;
    assert(
      "markRetryAttempt: a failed retry bumps attempts (was 1 → 2)",
      bumped!.attempts === 2,
      String(bumped!.attempts),
    );
  }

  // ── deadLetteredKeys: only dead-lettered rows, scoped per source ────────────────────────────────────
  {
    await sql`delete from poll_dead_letter`;
    await recordFailure(sql, REGS, "REGS-DL", "boom", NOW, 1); // dead-lettered
    await recordFailure(sql, REGS, "REGS-BR", "boom", NOW, 99); // bounded retry only
    await recordFailure(sql, FR, "FR-DL", "boom", NOW, 1); // dead-lettered, OTHER source
    const regsKeys = await deadLetteredKeys(sql, REGS);
    const frKeys = await deadLetteredKeys(sql, FR);
    assert(
      "deadLetteredKeys: includes the dead-lettered regs key",
      regsKeys.has("REGS-DL"),
      [...regsKeys].join(","),
    );
    assert(
      "deadLetteredKeys: EXCLUDES a still-in-bounded-retry key (not dead-lettered)",
      !regsKeys.has("REGS-BR"),
      [...regsKeys].join(","),
    );
    assert(
      "deadLetteredKeys: is SOURCE-SCOPED (FR's dead-letter not in the regs set, and vice versa)",
      !regsKeys.has("FR-DL") && frKeys.has("FR-DL") && !frKeys.has("REGS-DL"),
      `regs=[${[...regsKeys]}] fr=[${[...frKeys]}]`,
    );
  }
} finally {
  await sql.end();
}

console.log("\n=== dead-letter results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
