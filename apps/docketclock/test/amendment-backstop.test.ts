/**
 * amendment-backstop.test.ts — the §8 backstop (ADR 0016) through the real DB path. THROWAWAY Postgres
 * (drops + recreates the public schema).
 *
 * Real data: USDA 2026-18531 (portal close Nov 2 ET) and its extension 2026-19710, whose own FR
 * comments_close_on is the implausible 2026-09-11. A synthetic published DATES text that parses to a
 * WRONG-but-plausible Nov 9 has no corroboration (the portal says Nov 2; B's FR value is bad), so:
 *   • the resolver still reads Nov 9 (loadAmendmentEvidence: amended) — the parser is not the gate;
 *   • reconcileOcdId persists a window BYTE-IDENTICAL to the derivation without any amendment;
 * and once the real published text lands (Nov 2), the portal corroborates it and the window amends (HIGH).
 *
 * Run: DATABASE_URL=postgres://… pnpm --filter @yokel/docketclock exec tsx test/amendment-backstop.test.ts
 */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { isDeepStrictEqual } from "node:util";
import type { Observation } from "@yokel/contracts";
import { createClient } from "../src/db/client.js";
import { runMigrations } from "../src/db/migrate.js";
import { ingestObservation } from "../src/ingest/observe.js";
import {
  loadAmendmentEvidence,
  loadObservations,
  reconcileOcdId,
} from "../src/reconcile/persist.js";
import { reconcile } from "../src/reconcile/reconcile.js";
import { parseGovinfoObservation } from "../src/sources/govinfo.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

if (!process.env.DATABASE_URL) {
  console.log("SKIP amendment-backstop.test.ts — DATABASE_URL not set");
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
const govinfo = (html: string, fetchedAt: string) => ({
  ...parseGovinfoObservation({
    frDocNum: "2026-19710",
    publicationDate: "2026-09-25",
    url: "https://www.govinfo.gov/content/pkg/FR-2026-09-25/html/2026-19710.htm",
    html,
    isCorrection: false,
  }),
  fetched_at: fetchedAt,
});
/** The window as persisted, minus the persistence-only fields the pure engine never sets. */
async function persisted(): Promise<Record<string, unknown>> {
  const [w] = await sql<Record<string, unknown>[]>`
    select confidence, conflict_flags, resolved_close_utc, resolved_close_display, raw_fr_close_date,
           status, current_observation_ids, provenance
    from participation_windows where ocd_id = ${A}
  `;
  return {
    ...w,
    resolved_close_utc:
      (w!.resolved_close_utc as Date | null)?.toISOString() ?? null,
  };
}

try {
  await sql.unsafe(
    "drop schema if exists public cascade; create schema public;",
  );
  await runMigrations(sql);
  for (const o of stored.filter((x) => x.ocd_id === A || x.ocd_id === B))
    await insert(o);

  // A wrong-but-plausible published DATES: "November 9" — nothing corroborates it.
  await ingestObservation(
    sql,
    govinfo(
      "<pre>DATES: The comment period for the document originally published on September 11, 2026, (91 FR 57828) is extended. Comments must be submitted on or before November 9, 2026.\nADDRESSES: x</pre>",
      "2026-10-26T00:00:00.000Z",
    ),
  );
  const read = await loadAmendmentEvidence(sql, A);
  assert(
    "the resolver reads the (wrong) Nov 9 — the parser is not the gate",
    read.kind === "amended" && read.date === "2026-11-09",
    JSON.stringify(read).slice(0, 160),
  );
  const r = await reconcileOcdId(sql, A, NOW);
  const pure = reconcile(await loadObservations(sql, A), NOW).window;
  const w = await persisted();
  assert(
    "§8: uncorroborated (portal Nov 2, B's FR value 09-11 implausible) → the persisted window is BYTE-IDENTICAL to no amendment",
    isDeepStrictEqual(
      {
        confidence: r.window.confidence,
        conflict_flags: r.window.conflict_flags,
        resolved_close_utc: r.window.resolved_close_utc,
        resolved_close_display: r.window.resolved_close_display,
        raw_fr_close_date: r.window.raw_fr_close_date,
        status: r.window.status,
        current_observation_ids: r.window.current_observation_ids,
        provenance: r.window.provenance,
      },
      {
        confidence: pure.confidence,
        conflict_flags: pure.conflict_flags,
        resolved_close_utc: pure.resolved_close_utc,
        resolved_close_display: pure.resolved_close_display,
        raw_fr_close_date: pure.raw_fr_close_date,
        status: pure.status,
        current_observation_ids: pure.current_observation_ids,
        provenance: pure.provenance,
      },
    ) &&
      w.confidence === pure.confidence &&
      JSON.stringify(w.conflict_flags) ===
        JSON.stringify(pure.conflict_flags) &&
      !pure.conflict_flags.includes("fr_close_amended"),
    `${r.window.confidence} ${JSON.stringify(r.window.conflict_flags)}`,
  );

  // The real published text (Nov 2) lands: the portal (Nov 2 ET) corroborates it → amended, HIGH.
  await ingestObservation(
    sql,
    govinfo(
      readFileSync(join(FIX, "govinfo", "2026-19710.htm"), "utf8"),
      "2026-10-27T06:00:00.000Z",
    ),
  );
  const r2 = await reconcileOcdId(sql, A, NOW);
  assert(
    "the real text (Nov 2) is corroborated by the portal → HIGH + fr_close_amended",
    r2.window.confidence === "high" &&
      r2.window.conflict_flags.includes("fr_close_amended"),
    `${r2.window.confidence} ${JSON.stringify(r2.window.conflict_flags)}`,
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
