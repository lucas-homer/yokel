/**
 * regs.test.ts — proves the Regs.gov v4 -> ingest slice + the differential-polling primitives.
 *
 * Deterministic: loads a captured real v4 detail fixture (regs-FAA-2025-5396-0001.json) and NEVER hits
 * the network. The DB section requires a throwaway Postgres:
 *   DATABASE_URL=postgres://... pnpm --filter @yokel/docketclock test
 *
 * Load-bearing behaviors:
 *   - parseRegsObservation maps the real v4 shape (data.id -> regs_document_id, objectId, frDocNum) and
 *     mints the OCD-ID from frDocNum so a Regs row shares its FR counterpart's ocd_id;
 *   - the OCD-ID falls back to regs:{objectId} when frDocNum is absent, and throws when neither exists;
 *   - withdrawn=true forces is_withdrawal;
 *   - easternCursorLowerBound applies the 6h overlap and renders Eastern wall-clock (the silent-miss guard);
 *   - dedupeByDocumentId keeps the latest lastModifiedDate;
 *   - regsListUrl builds the withinCommentPeriod + cursor query;
 *   - ingest dedupes a Regs payload by (source, regs_document_id), appending on a mutated payload.
 */
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { Observation } from "@yokel/contracts";
import { createClient } from "../src/db/client.js";
import { runMigrations } from "../src/db/migrate.js";
import {
  parseRegsObservation,
  easternCursorLowerBound,
  formatEastern,
  dedupeByDocumentId,
  regsListUrl,
} from "../src/sources/regulations-gov.js";
import { payloadHash } from "../src/sources/payload.js";
import { ingestObservation } from "../src/ingest/observe.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}
async function rejects(name: string, op: () => unknown, re: RegExp) {
  try {
    await op();
    assert(name, false, "did not throw");
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    assert(name, re.test(msg), msg);
  }
}

const HERE = dirname(fileURLToPath(import.meta.url));
const fixture = JSON.parse(
  await readFile(
    join(HERE, "fixtures", "regs-FAA-2025-5396-0001.json"),
    "utf8",
  ),
) as { data: { id: string; attributes: Record<string, unknown> } };

// ── PARSE — real v4 detail maps into a contract-valid candidate ─────────────────────────────────────
const cand = parseRegsObservation(fixture);
assert(
  "source is regulations_gov",
  cand.source === "regulations_gov",
  cand.source,
);
assert(
  "regs_document_id is the JSON:API data.id (documentId)",
  cand.regs_document_id === "FAA-2025-5396-0001",
  String(cand.regs_document_id),
);
assert(
  "regs_object_id is attributes.objectId",
  cand.regs_object_id === "09000064b90ee693",
  String(cand.regs_object_id),
);
assert(
  "fr_document_number is attributes.frDocNum",
  cand.fr_document_number === "2025-23266",
  String(cand.fr_document_number),
);
assert(
  "ocd_id is minted from frDocNum (shares the FR observation's id)",
  cand.ocd_id === "ocd-participation-window/federal/2025-23266",
  cand.ocd_id,
);
assert(
  "raw_dates_text is null (Regs has no verbatim DATES blob)",
  cand.raw_dates_text === null,
);
assert(
  "is_withdrawal false (withdrawn:false, no keyword)",
  cand.is_withdrawal === false,
);
assert(
  "payload_hash is a sha256 hex",
  /^[a-f0-9]{64}$/.test(cand.payload_hash),
  cand.payload_hash,
);
const contract = Observation.safeParse({
  observation_id: "00000000-0000-0000-0000-000000000000",
  ...cand,
});
assert(
  "candidate validates against the frozen Observation contract",
  contract.success,
  contract.success ? "" : JSON.stringify(contract.error.issues),
);

// ── OCD-ID fallback + minting guards ────────────────────────────────────────────────────────────────
const noFr = {
  data: {
    id: "EPA-XYZ-0001",
    attributes: { objectId: "0900abcd", title: "Notice", withdrawn: false },
  },
};
assert(
  "absent frDocNum falls back to regs:{objectId}",
  parseRegsObservation(noFr).ocd_id ===
    "ocd-participation-window/federal/regs:0900abcd",
  parseRegsObservation(noFr).ocd_id,
);
await rejects(
  "throws when neither frDocNum nor objectId present",
  () =>
    parseRegsObservation({
      data: { id: "X-1", attributes: { title: "Notice" } },
    }),
  /neither frDocNum nor objectId/,
);
await rejects(
  "throws when the data envelope is missing",
  () => parseRegsObservation({ foo: "bar" }),
  /missing data envelope/,
);

// withdrawn:true forces is_withdrawal even with a benign title.
const withdrawnDoc = {
  data: {
    id: "EPA-W-1",
    attributes: {
      frDocNum: "2025-00001",
      title: "Routine Notice",
      withdrawn: true,
    },
  },
};
assert(
  "withdrawn:true => is_withdrawal true",
  parseRegsObservation(withdrawnDoc).is_withdrawal === true,
);

// ── CURSOR OVERLAP — the Eastern-filter / UTC-response silent-miss guard ─────────────────────────────
// EDT (summer): 2025-06-15T10:00:00Z minus 6h = 04:00Z = 00:00 Eastern (UTC-4).
assert(
  "easternCursorLowerBound applies 6h overlap (EDT, lands on midnight)",
  easternCursorLowerBound("2025-06-15T10:00:00Z") === "2025-06-15 00:00:00",
  easternCursorLowerBound("2025-06-15T10:00:00Z"),
);
// EST (winter): 2025-01-15T10:00:00Z minus 6h = 04:00Z = previous-day 23:00 Eastern (UTC-5).
assert(
  "easternCursorLowerBound is DST-correct (EST crosses the day boundary)",
  easternCursorLowerBound("2025-01-15T10:00:00Z") === "2025-01-14 23:00:00",
  easternCursorLowerBound("2025-01-15T10:00:00Z"),
);
// overlap=0 vs default 6 differ by exactly six hours.
assert(
  "overlap is applied (0h vs 6h differ by six hours of wall-clock)",
  formatEastern(new Date("2025-06-15T10:00:00Z")) === "2025-06-15 06:00:00" &&
    easternCursorLowerBound("2025-06-15T10:00:00Z", 0) ===
      "2025-06-15 06:00:00",
);
await rejects(
  "easternCursorLowerBound throws on an invalid cursor",
  () => easternCursorLowerBound("not-a-date"),
  /invalid cursor/,
);

// ── DEDUPE by documentId — keep the latest lastModifiedDate ──────────────────────────────────────────
const deduped = dedupeByDocumentId([
  { documentId: "A", lastModifiedDate: "2025-06-01T00:00:00Z" },
  { documentId: "A", lastModifiedDate: "2025-06-02T00:00:00Z" },
  { documentId: "B", lastModifiedDate: "2025-06-01T00:00:00Z" },
]);
assert(
  "dedupeByDocumentId collapses to unique ids",
  deduped.length === 2,
  String(deduped.length),
);
assert(
  "dedupeByDocumentId keeps the latest lastModifiedDate for a dup",
  deduped.find((d) => d.documentId === "A")?.lastModifiedDate ===
    "2025-06-02T00:00:00Z",
);

// ── LIST URL — withinCommentPeriod + cursor lower bound ──────────────────────────────────────────────
const withCursor = new URL(
  regsListUrl({
    sinceUtcIso: "2025-06-15T10:00:00Z",
    base: "https://api.example/v4",
  }),
);
assert(
  "regsListUrl sets filter[withinCommentPeriod]=true",
  withCursor.searchParams.get("filter[withinCommentPeriod]") === "true",
);
assert(
  "regsListUrl sets the Eastern cursor lower bound",
  withCursor.searchParams.get("filter[lastModifiedDate][ge]") ===
    "2025-06-15 00:00:00",
  String(withCursor.searchParams.get("filter[lastModifiedDate][ge]")),
);
assert(
  "regsListUrl sorts by lastModifiedDate",
  withCursor.searchParams.get("sort") === "lastModifiedDate",
);
const noCursor = new URL(regsListUrl({ base: "https://api.example/v4" }));
assert(
  "regsListUrl omits the cursor filter when no sinceUtcIso",
  noCursor.searchParams.get("filter[lastModifiedDate][ge]") === null,
);

// ── DB INGEST — dedupe by (source, regs_document_id); migration 0002 + index ─────────────────────────
const sql = createClient();
try {
  await sql.unsafe(
    "drop schema if exists public cascade; create schema public;",
  );
  const applied = await runMigrations(sql);
  assert(
    "migration 0002 applies (regs doc index)",
    applied.includes("0002_regs_doc_index.sql"),
    applied.join(", "),
  );
  const [idx] = await sql<{ indexname: string }[]>`
    select indexname from pg_indexes where indexname = 'observations_regs_doc_idx'
  `;
  assert(
    "observations_regs_doc_idx exists",
    !!idx,
    idx?.indexname ?? "missing",
  );

  const countRows = async () =>
    (
      await sql<{ count: string }[]>`
        select count(*)::text as count from observations where regs_document_id = 'FAA-2025-5396-0001'
      `
    )[0]!.count;

  const first = await ingestObservation(sql, cand);
  assert("first Regs ingest inserts", first.inserted === true);
  assert("one row after first ingest", (await countRows()) === "1");

  const second = await ingestObservation(sql, parseRegsObservation(fixture));
  assert("identical Regs payload is a dedupe skip", second.inserted === false);
  assert("still one row after re-ingest", (await countRows()) === "1");

  // Mutated payload (same regs_document_id, different hash) appends a second row.
  const mutatedRaw = JSON.parse(JSON.stringify(fixture)) as typeof fixture;
  mutatedRaw.data.attributes.commentEndDate = "2026-07-01T03:59:59Z";
  const mutated = parseRegsObservation(mutatedRaw);
  assert(
    "mutated Regs payload yields a different hash",
    mutated.payload_hash !== cand.payload_hash &&
      mutated.payload_hash === payloadHash(mutatedRaw),
  );
  const third = await ingestObservation(sql, mutated);
  assert("mutated Regs payload appends a new row", third.inserted === true);
  assert("two rows after the mutated payload", (await countRows()) === "2");
} finally {
  await sql.end();
}

console.log("\n=== regs results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
