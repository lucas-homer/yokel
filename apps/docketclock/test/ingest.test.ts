/**
 * ingest.test.ts — proves the FR -> ingest vertical slice writes THROUGH the append-only log correctly.
 *
 * The slice's job: map a real FR document into an Observation candidate that satisfies the frozen
 * @yokel/contracts shape, then append it ONCE per distinct payload. The load-bearing behaviors:
 *   - first ingest appends a row (+ its primary observation_target);
 *   - re-ingesting the IDENTICAL payload is a payload-hash dedupe SKIP (still exactly one row);
 *   - a MUTATED payload (different hash, same fr_document_number) appends a SECOND row;
 *   - the parsed candidate validates against the Observation contract.
 *
 * Deterministic: it loads a captured FR fixture from disk and NEVER hits the network. Requires a
 * throwaway Postgres:  DATABASE_URL=postgres://... pnpm --filter @yokel/docketclock test
 */
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { Observation } from "@yokel/contracts";
import { createClient } from "../src/db/client.js";
import { runMigrations } from "../src/db/migrate.js";
import {
  parseFrObservation,
  payloadHash,
} from "../src/sources/federal-register.js";
import { ingestObservation } from "../src/ingest/observe.js";

let failures = 0;
const log: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  log.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

async function countRows(s: ReturnType<typeof createClient>): Promise<string> {
  const rows = await s<{ count: string }[]>`
    select count(*)::text as count from observations
    where fr_document_number = '2025-02910'
  `;
  return rows[0]!.count;
}

const HERE = dirname(fileURLToPath(import.meta.url));
const fixtureRaw = JSON.parse(
  await readFile(join(HERE, "fixtures", "fr-2025-02910.json"), "utf8"),
) as Record<string, unknown>;

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

  // ── PARSE — the FR document maps into a candidate that validates against the frozen contract ──────
  const candidate = parseFrObservation(fixtureRaw);
  assert(
    "candidate.source is federal_register",
    candidate.source === "federal_register",
    candidate.source,
  );
  assert(
    "candidate.fr_document_number is the FR doc number",
    candidate.fr_document_number === "2025-02910",
    String(candidate.fr_document_number),
  );
  assert(
    "candidate.regs_document_id is the Regs.gov document id from regulations_dot_gov_info",
    candidate.regs_document_id === "EPA-HQ-OW-2024-0454-0022",
    String(candidate.regs_document_id),
  );
  assert(
    "candidate.regs_object_id stays null (FR does not expose the Regs objectId)",
    candidate.regs_object_id === null,
    String(candidate.regs_object_id),
  );
  assert(
    "candidate.raw_dates_text retained verbatim",
    candidate.raw_dates_text === (fixtureRaw.dates as string) &&
      candidate.raw_dates_text!.startsWith("The comment periods"),
    String(candidate.raw_dates_text).slice(0, 40),
  );
  assert(
    "candidate.is_extension true (action says extension of comment periods)",
    candidate.is_extension === true,
  );
  assert(
    "candidate.payload_hash is a sha256 hex digest",
    /^[a-f0-9]{64}$/.test(candidate.payload_hash),
    candidate.payload_hash,
  );
  assert(
    "candidate.ocd_id is the federal scheme for this frDocNum",
    candidate.ocd_id === "ocd-participation-window/federal/2025-02910",
    candidate.ocd_id,
  );

  // The candidate validates against the frozen Observation schema once given a placeholder id.
  const contractCheck = Observation.safeParse({
    observation_id: "00000000-0000-0000-0000-000000000000",
    ...candidate,
  });
  assert(
    "candidate validates against the frozen Observation contract",
    contractCheck.success,
    contractCheck.success ? "" : JSON.stringify(contractCheck.error.issues),
  );

  // ── FIRST INGEST — appends a row + its primary target ─────────────────────────────────────────────
  const first = await ingestObservation(sql, candidate);
  assert("first ingest inserts", first.inserted === true);
  assert(
    "first ingest returns a generated observation_id",
    typeof first.observationId === "string" && first.observationId.length > 0,
    String(first.observationId),
  );
  assert(
    "first ingest returns the ocd_id",
    first.ocdId === candidate.ocd_id,
    first.ocdId,
  );

  const afterFirst = await countRows(sql);
  assert(
    "exactly one observation row after first ingest",
    afterFirst === "1",
    afterFirst,
  );

  // The primary observation_target is present for this ocd_id.
  const targets = await sql<{ ocd_id: string }[]>`
    select ocd_id from observation_targets where observation_id = ${first.observationId!}
  `;
  assert(
    "observation_targets has the primary ocd_id",
    targets.length === 1 && targets[0]!.ocd_id === candidate.ocd_id,
    targets.map((t) => t.ocd_id).join(", "),
  );

  // ── RE-INGEST SAME PAYLOAD — payload-hash dedupe SKIP ─────────────────────────────────────────────
  const samePayloadCandidate = parseFrObservation(fixtureRaw); // fresh fetched_at, identical hash
  assert(
    "re-parsed candidate has the same payload_hash (hash is canonical, not time-based)",
    samePayloadCandidate.payload_hash === candidate.payload_hash,
  );
  const second = await ingestObservation(sql, samePayloadCandidate);
  assert(
    "re-ingest of identical payload is a dedupe skip",
    second.inserted === false,
  );
  assert(
    "dedupe skip returns null observationId",
    second.observationId === null,
  );
  const afterDupe = await countRows(sql);
  assert(
    "still exactly one row after re-ingesting the same payload",
    afterDupe === "1",
    afterDupe,
  );

  // ── MUTATED PAYLOAD — different hash, same fr_document_number => appends a SECOND row ──────────────
  const mutatedRaw = { ...fixtureRaw, dates: "Comments now due May 30, 2025." };
  const mutated = parseFrObservation(mutatedRaw);
  assert(
    "mutated payload yields a DIFFERENT payload_hash",
    mutated.payload_hash !== candidate.payload_hash &&
      mutated.payload_hash === payloadHash(mutatedRaw),
  );
  const third = await ingestObservation(sql, mutated);
  assert("mutated payload inserts a new row", third.inserted === true);
  const afterMutate = await countRows(sql);
  assert(
    "exactly two rows after the mutated payload",
    afterMutate === "2",
    afterMutate,
  );

  // The dedupe lookup now keys off the LATEST (mutated) hash — re-ingesting the mutated payload skips.
  const fourth = await ingestObservation(sql, parseFrObservation(mutatedRaw));
  assert(
    "re-ingesting the latest (mutated) payload is a dedupe skip",
    fourth.inserted === false,
  );
  const afterMutateDupe = await countRows(sql);
  assert(
    "still exactly two rows after re-ingesting the latest payload",
    afterMutateDupe === "2",
    afterMutateDupe,
  );
} finally {
  await sql.end();
}

console.log("\n=== ingest results ===");
console.log(log.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
