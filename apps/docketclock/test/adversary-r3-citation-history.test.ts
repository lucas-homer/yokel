/** R3: a later citation collision must never revive a superseded human verdict. Drops the public schema of DATABASE_URL — point it at a throwaway DB. */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import type { Observation } from "@yokel/contracts";
import { createClient } from "../src/db/client.js";
import { runMigrations } from "../src/db/migrate.js";
import { reconcileOcdId } from "../src/reconcile/persist.js";
import { resolveWindow, reviewQueue, reviewShow } from "../src/review/core.js";
import { govinfoSweepOnce } from "../src/sources/govinfo.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

if (!process.env.DATABASE_URL) {
  console.log(
    "SKIP adversary-r3-citation-history.test.ts — DATABASE_URL not set",
  );
  process.exit(0);
}

const FIX = join(
  dirname(fileURLToPath(import.meta.url)),
  "fixtures",
  "fr-amendments",
);
const stored = JSON.parse(
  readFileSync(join(FIX, "stored", "observations.json"), "utf8"),
) as Observation[];
const A = "ocd-participation-window/federal/2026-18531";
const B = "ocd-participation-window/federal/2026-19710";
const NOW = new Date("2026-10-27T12:00:00Z");

const sql = createClient();
async function insert(o: Observation) {
  await sql`
    insert into observations
      (observation_id, ocd_id, source, fr_document_number, regs_document_id, regs_object_id,
       payload_hash, fetched_at, parser_version, raw_dates_text,
       is_extension, is_correction, is_withdrawal, is_reopening, raw)
    values
      (${o.observation_id}, ${o.ocd_id}, ${o.source}, ${o.fr_document_number},
       ${o.regs_document_id}, ${o.regs_object_id}, ${o.payload_hash}, ${o.fetched_at},
       ${o.parser_version}, ${o.raw_dates_text}, ${o.is_extension}, ${o.is_correction},
       ${o.is_withdrawal}, ${o.is_reopening}, ${sql.json(o.raw as never)})
  `;
}
const hashesOf = async (ocdId: string) =>
  (await reviewShow(sql, ocdId, { now: NOW })).sources.map(
    (s) => s.payload_hash,
  );

try {
  await sql.unsafe(
    "drop schema if exists public cascade; create schema public;",
  );
  await runMigrations(sql);
  const aFr = stored.find(
    (x) => x.ocd_id === A && x.source === "federal_register",
  )!;
  await insert(aFr);
  await reconcileOcdId(sql, A, new Date("2026-09-20T00:00:00Z"));
  const pin = await resolveWindow(
    sql,
    {
      ocdId: A,
      kind: "pin_close",
      close: "2026-10-13",
      note: "original only",
      operator: "test",
      expect: await hashesOf(A),
    },
    new Date("2026-09-20T12:00:00Z"),
  );
  assert("setup pin honored", pin.honored === true);
  await insert(
    stored.find((x) => x.ocd_id === B && x.source === "federal_register")!,
  );
  await govinfoSweepOnce(sql, NOW, {
    fetchHtml: async (_p, doc) =>
      doc === "2026-19710"
        ? readFileSync(join(FIX, "govinfo", `${doc}.htm`), "utf8")
        : null,
    sleep: async () => {},
  });
  const before = await reviewShow(sql, A, { now: NOW });
  assert("setup extension supersedes pin", before.honored === null);
  // An unrelated newly discovered document shares A's citation, invalidating ONLY the current link.
  await insert({
    ...aFr,
    observation_id: "eeeeeeee-0000-4000-8000-000000000003",
    ocd_id: "ocd-participation-window/federal/2026-29999",
    fr_document_number: "2026-29999",
    payload_hash: "f".repeat(64),
    fetched_at: "2026-10-28T00:00:00.000Z",
    raw: {
      ...(aFr.raw as object),
      document_number: "2026-29999",
      title: "Unrelated notice",
      docket_ids: [],
      regulation_id_numbers: [],
    },
  } as Observation);
  const after = await reviewShow(sql, A, {
    now: new Date("2026-10-28T12:00:00Z"),
  });
  assert(
    "R3 citation collision must not revive a superseded pin",
    after.honored === null,
    JSON.stringify(after.honored),
  );
} finally {
  await sql.end();
}
console.log(out.join("\n"));
process.exit(failures ? 1 : 0);
