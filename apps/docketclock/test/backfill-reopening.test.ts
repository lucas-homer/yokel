/**
 * backfill-reopening.test.ts — the #O4 dev re-derive backfill (src/db/backfill-reopening-flag.ts).
 *
 * Proves the load-bearing properties:
 *   • SPLIT CORRECTNESS — an old v1 reopening row (is_extension=true, is_reopening=false) is re-derived to
 *     is_extension=FALSE / is_reopening=TRUE, and re-stamped parser_version fr-v2.
 *   • NO DRIFT (Regs withdrawn-OR) — a Regs row with attributes.withdrawn=true re-derives is_withdrawal=TRUE
 *     even with a benign title, because the backfill uses regsNoticeFlags (the SAME function the adapter
 *     uses), which folds in the authoritative withdrawn flag.
 *   • APPEND-ONLY GUARD RESTORED — after the backfill (which disables the trigger inside its transaction),
 *     a direct UPDATE on observations is STILL rejected. The guard can never be left off.
 *   • IDEMPOTENT — a second run updates nothing.
 *
 * Requires a throwaway Postgres:  DATABASE_URL=postgres://... pnpm --filter @yokel/docketclock test
 */
import { makeOcdId } from "@yokel/contracts";
import { createClient } from "../src/db/client.js";
import { runMigrations } from "../src/db/migrate.js";
import { backfillReopeningFlag } from "../src/db/backfill-reopening-flag.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

const sql = createClient();
const h = (c: string) => c.repeat(64); // a valid sha256-shaped payload_hash

try {
  await runMigrations(sql);

  // An OLD (v1) FR reopening row: under the pre-split parser a reopening was folded into is_extension.
  const reopenOcd = makeOcdId({ frDocNum: "O4-REOPEN-0001" });
  const [reopenRow] = await sql<{ observation_id: string }[]>`
    insert into observations
      (ocd_id, source, fr_document_number, payload_hash, parser_version, raw_dates_text,
       is_extension, is_correction, is_withdrawal, is_reopening, raw)
    values
      (${reopenOcd}, 'federal_register', 'O4-REOPEN-0001', ${h("a")}, 'fr-v1',
       null, true, false, false, false,
       ${sql.json({ title: "Reopening of the Comment Period", type: "Notice", action: "Reopening" })})
    returning observation_id
  `;
  const reopenId = reopenRow!.observation_id;

  // An OLD (v1) Regs row whose AUTHORITATIVE withdrawn=true was (hypothetically) missed — benign title.
  const wdOcd = makeOcdId({ frDocNum: "O4-REGS-WD-0001" });
  const [wdRow] = await sql<{ observation_id: string }[]>`
    insert into observations
      (ocd_id, source, fr_document_number, payload_hash, parser_version, raw_dates_text,
       is_extension, is_correction, is_withdrawal, is_reopening, raw)
    values
      (${wdOcd}, 'regulations_gov', 'O4-REGS-WD-0001', ${h("b")}, 'regs-v1',
       null, false, false, false, false,
       ${sql.json({ data: { attributes: { title: "Some Ordinary Notice", documentType: "Notice", withdrawn: true } } })})
    returning observation_id
  `;
  const wdId = wdRow!.observation_id;

  // ── run the backfill ──────────────────────────────────────────────────────────────────────────────
  const res1 = await backfillReopeningFlag(sql);
  assert(
    "backfill returns a result with scanned >= 2",
    res1.scanned >= 2,
    JSON.stringify(res1),
  );

  const [reopen] = await sql<
    {
      is_extension: boolean;
      is_reopening: boolean;
      parser_version: string;
    }[]
  >`select is_extension, is_reopening, parser_version from observations where observation_id = ${reopenId}`;
  assert(
    "SPLIT: reopening row → is_reopening=true, is_extension=false",
    reopen!.is_reopening === true && reopen!.is_extension === false,
    `reopen=${reopen!.is_reopening} ext=${reopen!.is_extension}`,
  );
  assert(
    "SPLIT: reopening row re-stamped parser_version fr-v2",
    reopen!.parser_version === "fr-v2",
    reopen!.parser_version,
  );

  const [wd] = await sql<{ is_withdrawal: boolean; parser_version: string }[]>`
    select is_withdrawal, parser_version from observations where observation_id = ${wdId}`;
  assert(
    "NO DRIFT: Regs withdrawn=true re-derives is_withdrawal=true (regsNoticeFlags withdrawn-OR)",
    wd!.is_withdrawal === true,
    String(wd!.is_withdrawal),
  );
  assert(
    "NO DRIFT: Regs row re-stamped parser_version regs-v2",
    wd!.parser_version === "regs-v2",
    wd!.parser_version,
  );

  // ── the append-only guard must be RESTORED after the backfill ───────────────────────────────────────
  let updateRejected = false;
  try {
    await sql`update observations set is_extension = false where observation_id = ${reopenId}`;
  } catch {
    updateRejected = true;
  }
  assert(
    "GUARD RESTORED: a direct UPDATE on observations is still rejected after the backfill",
    updateRejected,
  );

  // ── idempotent: a second run changes nothing ────────────────────────────────────────────────────────
  const res2 = await backfillReopeningFlag(sql);
  assert(
    "IDEMPOTENT: second backfill run updates 0 rows",
    res2.updated === 0,
    JSON.stringify(res2),
  );
} finally {
  await sql.end();
}

console.log("\n=== backfill-reopening results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
