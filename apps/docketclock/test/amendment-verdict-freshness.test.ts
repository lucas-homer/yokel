/**
 * amendment-verdict-freshness.test.ts — round-1 finding #1 (BLOCKER) through the real DB paths
 * (ADR 0016 §7). THROWAWAY Postgres (drops + recreates the public schema).
 *
 * Real data (the recorded production log): Census 2026-18481, pinned to its original Oct 13 close on
 * Oct 1 by a reviewer who had only the original notice; extension 2026-20328 (shared docket + RIN, Nov 2)
 * is fetched Oct 3. Since v2.4 the linked extension is an INPUT to 18481's derivation, so it is new
 * evidence for 18481's verdict:
 *   • reconcileOcdId: the pin is no longer honored — the window derives from sources with the amended
 *     FR side (and lands in the review queue as CONFLICTING against the not-yet-moved portal);
 *   • `review show`: honored null; its sources list the linked amendment's FR row (an --expect hash);
 *   • a re-review bound to those hashes succeeds and is honored; the amendment's later GovInfo copy
 *     (same Nov 2) does not un-honor it — but a write whose --expect predates that copy is refused.
 *
 * Run: DATABASE_URL=postgres://… pnpm --filter @yokel/docketclock exec tsx test/amendment-verdict-freshness.test.ts
 */
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
    "SKIP amendment-verdict-freshness.test.ts — DATABASE_URL not set",
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
const A = "ocd-participation-window/federal/2026-18481";
const B = "ocd-participation-window/federal/2026-20328";
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
  // 18481 as of Oct 1: its FR row and the Regs rows fetched before the pin (portal still Oct 13 ET).
  for (const o of stored.filter(
    (x) => x.ocd_id === A && x.fetched_at < "2026-10-01",
  ))
    await insert(o);
  await reconcileOcdId(sql, A, new Date("2026-10-01T06:00:00Z"));

  // The Oct 1 review: pin the original's own Oct 13 close, bound to what was live.
  const pin1 = await resolveWindow(
    sql,
    {
      ocdId: A,
      kind: "pin_close",
      close: "2026-10-13",
      note: "reviewed the original notice (no extension yet)",
      operator: "test",
      expect: await hashesOf(A),
    },
    new Date("2026-10-01T12:00:00Z"),
  );
  assert(
    "setup: the Oct 1 pin is written and honored",
    pin1.inserted && pin1.honored === true,
  );

  // Oct 3: the extension lands (the FR keyword poller's ingest), then 18481 is re-derived.
  for (const o of stored.filter(
    (x) => x.ocd_id === B && x.source === "federal_register",
  ))
    await insert(o);
  const r = await reconcileOcdId(sql, A, NOW);
  assert(
    "#1 reconcileOcdId: the pin that predates the linked extension is NOT honored any more",
    !r.window.conflict_flags.includes("human_resolved") &&
      r.window.conflict_flags.includes("fr_close_amended"),
    `${r.window.confidence} ${JSON.stringify(r.window.conflict_flags)}`,
  );
  assert(
    "#1 … the window is re-derived from sources: CONFLICTING (FR Nov 2 vs the portal's Oct 13) — back in the queue",
    r.window.confidence === "conflicting" &&
      (await reviewQueue(sql)).some((q) => q.ocd_id === A),
  );
  const show = await reviewShow(sql, A, { now: NOW });
  const bFr = stored.find(
    (x) => x.ocd_id === B && x.source === "federal_register",
  )!;
  assert(
    "#1 review show: no honored verdict; the linked amendment's FR row is listed as evidence (--expect)",
    show.honored === null &&
      show.sources.some(
        (s) => s.amendment_window === B && s.payload_hash === bFr.payload_hash,
      ),
    JSON.stringify(show.sources.map((s) => [s.source, s.amendment_window])),
  );

  // The re-review, bound to the evidence INCLUDING the amendment.
  const expectNow = await hashesOf(A);
  const pin2 = await resolveWindow(
    sql,
    {
      ocdId: A,
      kind: "pin_close",
      close: "2026-11-02",
      note: "re-reviewed with the Census extension",
      operator: "test",
      expect: expectNow,
    },
    new Date("2026-10-26T12:00:00Z"),
  );
  assert(
    "#1 a re-review with --expect = show's hashes (amendment included) succeeds and is honored",
    pin2.inserted &&
      pin2.honored === true &&
      pin2.reviewedHashes.includes(bFr.payload_hash),
    JSON.stringify(pin2.reviewedHashes.length),
  );

  // Oct 27: the GovInfo sweep fetches the extension's published text (same Nov 2).
  await govinfoSweepOnce(sql, NOW, {
    fetchHtml: async (_p, doc) =>
      doc === "2026-20328"
        ? readFileSync(join(FIX, "govinfo", "2026-20328.htm"), "utf8")
        : null,
    sleep: async () => {},
  });
  const r2 = await reconcileOcdId(sql, A, NOW);
  assert(
    "#1 the amendment's later GovInfo copy (same Nov 2) does not un-honor the re-review",
    r2.window.conflict_flags.includes("human_resolved") &&
      r2.window.confidence === "high",
    `${r2.window.confidence} ${JSON.stringify(r2.window.conflict_flags)}`,
  );
  let refused = "";
  try {
    await resolveWindow(
      sql,
      {
        ocdId: A,
        kind: "pin_close",
        close: "2026-11-02",
        note: "stale expectation",
        operator: "test",
        expect: expectNow,
      },
      new Date("2026-10-27T13:00:00Z"),
    );
  } catch (err) {
    refused = err instanceof Error ? err.message : String(err);
  }
  assert(
    "#1 --expect taken BEFORE the amendment's GovInfo copy landed is refused (the copy is evidence for this window)",
    /--expect mismatch/.test(refused) &&
      /amendment 2026-20328 govinfo/.test(refused),
    refused.slice(0, 200),
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
