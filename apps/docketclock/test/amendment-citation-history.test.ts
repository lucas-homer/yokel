/**
 * amendment-citation-history.test.ts — round-3 finding 1 (ADR 0016 §7): citation uniqueness is counted
 * PER TIMELINE STATE, and the arrival of any document carrying A's citation is a timeline boundary.
 * THROWAWAY Postgres (drops + recreates the public schema). Companion to the reviewer's
 * adversary-r3-citation-history.test.ts (collision AFTER the extension → the superseded pin stays
 * superseded); this file pins the other order and the mechanics:
 *
 *   • collision BEFORE the extension: in every state after it the citation is shared, so USDA 19710 never
 *     links to 18531 by citation — the derivation never changes and the Sep 20 pin stays HONORED (per-state
 *     counting is exact, not merely conservative);
 *   • the timeline carries the collision's arrival as a boundary, with the count it implies.
 *
 * Run: DATABASE_URL=postgres://… pnpm --filter @yokel/docketclock exec tsx test/amendment-citation-history.test.ts
 */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import type { Observation } from "@yokel/contracts";
import { createClient } from "../src/db/client.js";
import { runMigrations } from "../src/db/migrate.js";
import {
  loadAmendmentInputs,
  reconcileOcdId,
} from "../src/reconcile/persist.js";
import { resolveWindow, reviewShow } from "../src/review/core.js";
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
  console.log("SKIP amendment-citation-history.test.ts — DATABASE_URL not set");
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
      expect: (await reviewShow(sql, A, { now: NOW })).sources.map(
        (s) => s.payload_hash,
      ),
    },
    new Date("2026-09-20T12:00:00Z"),
  );
  assert("setup: the Sep 20 pin is honored", pin.honored === true);

  // Sep 21 — BEFORE the extension: an unrelated document sharing 18531's citation (91 FR 57828).
  await insert({
    ...aFr,
    observation_id: "eeeeeeee-0000-4000-8000-000000000031",
    ocd_id: "ocd-participation-window/federal/2026-29998",
    fr_document_number: "2026-29998",
    payload_hash: "c".repeat(64),
    fetched_at: "2026-09-21T00:00:00.000Z",
    raw: {
      ...(aFr.raw as object),
      document_number: "2026-29998",
      title: "Unrelated notice",
      docket_ids: [],
      regulation_id_numbers: [],
    },
  } as Observation);
  // Sep 25 / Oct 27 — the extension and its published text (which carries the citation).
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

  const loaded = await loadAmendmentInputs(sql, A);
  assert(
    "the citation is shared in every state with the extension → never linked; the outcome is none",
    loaded.outcome.kind === "none" &&
      (loaded.inputs?.timeline ?? []).every((s) => s.amendments.length === 0),
    JSON.stringify(
      loaded.inputs?.timeline?.map((s) => [s.at, s.amendments.length]),
    ),
  );
  assert(
    "the collision's arrival (Sep 21) is a timeline boundary",
    (loaded.inputs?.timeline ?? []).some(
      (s) => s.at === "2026-09-21T00:00:00.000Z",
    ),
    JSON.stringify(loaded.inputs?.timeline?.map((s) => s.at)),
  );
  const show = await reviewShow(sql, A, { now: NOW });
  const r = await reconcileOcdId(sql, A, NOW);
  assert(
    "the derivation never changed since the verdict → the pin stays honored",
    show.honored !== null &&
      r.window.conflict_flags.includes("human_resolved") &&
      !r.window.conflict_flags.includes("fr_close_amended"),
    `${r.window.confidence} ${JSON.stringify(r.window.conflict_flags)}`,
  );
} finally {
  await sql.end();
}

console.log(out.join("\n"));
console.log(
  failures === 0
    ? `\nALL ${out.length} EXPECTATIONS MET`
    : `\n${failures} EXPECTATION(S) UNMET`,
);
process.exit(failures === 0 ? 0 : 1);
