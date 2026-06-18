/**
 * observation-log.test.ts — proves the Spine's trust primitive holds at the DB level.
 *
 * The whole product's legal defensibility rests on the observation log being append-only by EXCEPTION,
 * not convention. This runs the real migration against a real Postgres and attacks it: every UPDATE,
 * DELETE, and TRUNCATE on the log must be rejected by the database itself. It also proves the M:N
 * fan-out (one notice -> many windows), the payload-hash dedupe lookup, and that a stored row validates
 * against the frozen @yokel/contracts Observation schema.
 *
 * Requires a throwaway Postgres:  DATABASE_URL=postgres://... pnpm --filter @yokel/docketclock test
 * Run: pnpm --filter @yokel/docketclock test
 */
import { Observation, makeOcdId } from "@yokel/contracts";
import { createClient } from "../src/db/client.js";
import { runMigrations } from "../src/db/migrate.js";

let failures = 0;
const log: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  log.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}
/** Assert that a DB operation is rejected by the append-only guard (not silently allowed). */
async function rejects(name: string, op: () => Promise<unknown>) {
  try {
    await op();
    assert(name, false, "operation SUCCEEDED — the log was mutated!");
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    assert(name, /append-only/.test(msg), msg);
  }
}

const sql = createClient();

try {
  // Fresh schema each run (DROP is DDL — not blocked by the row-level append-only trigger).
  await sql.unsafe(
    "drop schema if exists public cascade; create schema public;",
  );
  const applied = await runMigrations(sql);
  assert(
    "migration applies cleanly",
    applied.includes("0001_observation_log.sql"),
    applied.join(", "),
  );
  // Re-running is a no-op (idempotent).
  const second = await runMigrations(sql);
  assert(
    "migration is idempotent (re-run applies nothing)",
    second.length === 0,
  );

  // ── INSERT — the append path works, and the row round-trips through the frozen contract ──────────
  const ocdId = makeOcdId({ frDocNum: "2025-02910" });
  const [row] = await sql`
    insert into observations
      (ocd_id, source, fr_document_number, payload_hash, parser_version, raw_dates_text,
       is_extension, is_correction, is_withdrawal, is_reopening, raw)
    values
      (${ocdId}, 'federal_register', '2025-02910', ${"a".repeat(64)}, 'p1',
       'Comments due March 15, 2025', true, false, false, false, ${sql.json({ doc: "2025-02910" })})
    returning *
  `;
  assert(
    "insert returns a row with a generated observation_id",
    !!row && !!row.observation_id,
  );

  const parsed = Observation.safeParse({
    observation_id: row!.observation_id,
    ocd_id: row!.ocd_id,
    source: row!.source,
    fr_document_number: row!.fr_document_number,
    regs_document_id: row!.regs_document_id,
    regs_object_id: row!.regs_object_id,
    payload_hash: row!.payload_hash,
    fetched_at: (row!.fetched_at as Date).toISOString(),
    parser_version: row!.parser_version,
    raw_dates_text: row!.raw_dates_text,
    is_extension: row!.is_extension,
    is_correction: row!.is_correction,
    is_withdrawal: row!.is_withdrawal,
    is_reopening: row!.is_reopening,
    raw: row!.raw,
  });
  assert(
    "stored row validates against the frozen Observation schema",
    parsed.success,
    parsed.success ? "" : JSON.stringify(parsed.error.issues),
  );

  const id = row!.observation_id as string;

  // ── THE ATTACK — every mutation of the log must be rejected by the database ──────────────────────
  await rejects(
    "UPDATE on observations is rejected by exception",
    () =>
      sql`update observations set payload_hash = ${"b".repeat(64)} where observation_id = ${id}`,
  );
  await rejects(
    "DELETE on observations is rejected by exception",
    () => sql`delete from observations where observation_id = ${id}`,
  );
  // TRUNCATE bypasses row-level DELETE triggers — the explicit statement-level guard must catch it.
  await rejects(
    "TRUNCATE on observations is rejected by exception",
    () => sql`truncate observations cascade`,
  );

  // The row is still there and unchanged after the failed attacks.
  const [still] =
    await sql`select payload_hash from observations where observation_id = ${id}`;
  assert(
    "row survives the attacks unchanged",
    still?.payload_hash === "a".repeat(64),
  );

  // ── M:N fan-out — ONE observation contributes to TWO distinct windows (EPA 2025-02910) ───────────
  const ocdB = makeOcdId({ regsObjectId: "0900006484abcd01" });
  await sql`insert into observation_targets (observation_id, ocd_id) values (${id}, ${ocdId}), (${id}, ${ocdB})`;
  const targets =
    await sql`select ocd_id from observation_targets where observation_id = ${id} order by ocd_id`;
  assert(
    "one observation fans out to two distinct ocd_ids (M:N)",
    targets.length === 2 && targets[0]!.ocd_id !== targets[1]!.ocd_id,
    targets.map((t) => t.ocd_id).join(" , "),
  );
  await rejects(
    "DELETE on observation_targets is rejected by exception",
    () => sql`delete from observation_targets where observation_id = ${id}`,
  );

  // ── DEDUPE — the "latest for (source, document_id)" lookup the ingestion path keys off ────────────
  await sql`
    insert into observations
      (ocd_id, source, fr_document_number, payload_hash, parser_version, is_extension, is_correction, is_withdrawal, raw)
    values
      (${ocdId}, 'federal_register', '2025-02910', ${"c".repeat(64)}, 'p1', true, false, false, ${sql.json({})})
  `;
  const [latest] = await sql`
    select payload_hash from observations
    where source = 'federal_register' and fr_document_number = '2025-02910'
    order by fetched_at desc limit 1
  `;
  assert(
    "dedupe lookup returns the most-recent payload_hash for (source, document_id)",
    latest?.payload_hash === "c".repeat(64),
    String(latest?.payload_hash),
  );
} finally {
  await sql.end();
}

console.log("\n=== observation-log results ===");
console.log(log.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
