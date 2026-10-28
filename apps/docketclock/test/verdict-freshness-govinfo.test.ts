/**
 * verdict-freshness-govinfo.test.ts — the 2026-10-27 replay regression (ADR 0016, reconcile-v2.4):
 * a `govinfo` observation landing on a window's OWN chain after its human verdict must not supersede
 * the verdict. THROWAWAY Postgres (drops + recreates the public schema).
 *
 * Real data (test/fixtures/fr-amendments/stored/human-resolved.json, dumped read-only from the replay
 * database): 2026-18297 (open, FDA; pin_close 2026-11-09, then a metadata-only Regs refresh) and
 * 2026-15026 (closed, BOEM; pin_close 2026-08-22 over a junk 1900-01-01 portal close). Both are
 * amendment-flagged, so the GovInfo sweep fetches their published text — onto their own chains. On
 * the replay the v2.3 rule ("every newer non-human observation is evidence") dropped both pins (and
 * ten more): 18297 fell to CONFLICTING while open, 15026 to a 1900 close.
 *
 * Proves, with the sweep doing the append exactly as in production:
 *   • reconcileOcdId: HIGH + pinned + human_resolved before the sweep AND after it (no version bump);
 *   • the review core: `show` reports the verdict honored before and after; its `sources` (the
 *     --expect set) are FR + Regs only and the govinfo row is listed under `context`; a resolve with
 *     --expect = those hashes succeeds and records no govinfo hash; the queue does not list them;
 *   • a newer FR observation still un-honors the verdict through the same DB path.
 *
 * Run: DATABASE_URL=postgres://… pnpm --filter @yokel/docketclock exec tsx test/verdict-freshness-govinfo.test.ts
 */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import type { Observation } from "@yokel/contracts";
import { createClient } from "../src/db/client.js";
import { runMigrations } from "../src/db/migrate.js";
import { ingestObservation } from "../src/ingest/observe.js";
import { reconcileOcdId } from "../src/reconcile/persist.js";
import { resolveWindow, reviewQueue, reviewShow } from "../src/review/core.js";
import { govinfoSweepOnce } from "../src/sources/govinfo.js";
import { parseFrObservation } from "../src/sources/federal-register.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

if (!process.env.DATABASE_URL) {
  console.log("SKIP verdict-freshness-govinfo.test.ts — DATABASE_URL not set");
  process.exit(0);
}

const hr = JSON.parse(
  readFileSync(
    join(
      dirname(fileURLToPath(import.meta.url)),
      "fixtures",
      "fr-amendments",
      "stored",
      "human-resolved.json",
    ),
    "utf8",
  ),
) as Observation[];
const ocd = (doc: string) => `ocd-participation-window/federal/${doc}`;
const NOW = new Date("2026-10-27T12:00:00Z");
const DOCS = ["2026-18297", "2026-15026"];
const govRow = (doc: string) =>
  hr.find((o) => o.ocd_id === ocd(doc) && o.source === "govinfo")!;

const sql = createClient();
interface W {
  confidence: string;
  conflict_flags: string[];
  resolved_close_utc: Date | null;
  version: number;
  status: string;
}
const win = async (doc: string) =>
  (
    await sql<W[]>`
      select confidence, conflict_flags, resolved_close_utc, version, status
      from participation_windows where ocd_id = ${ocd(doc)}
    `
  )[0]!;

try {
  await sql.unsafe(
    "drop schema if exists public cascade; create schema public;",
  );
  await runMigrations(sql);
  // Everything EXCEPT the govinfo rows, verbatim (same ids): the state before the sweep ran.
  for (const o of hr.filter((x) => x.source !== "govinfo")) {
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
  const before = new Map<string, W>();
  for (const doc of DOCS) {
    await reconcileOcdId(sql, ocd(doc), NOW);
    const w = await win(doc);
    before.set(doc, w);
    assert(
      `${doc} before the sweep: HIGH, pinned, human_resolved`,
      w.confidence === "high" && w.conflict_flags.includes("human_resolved"),
      `${w.confidence} ${JSON.stringify(w.conflict_flags)}`,
    );
    const s = await reviewShow(sql, ocd(doc), { now: NOW });
    assert(
      `${doc} before: review show reports the pin honored`,
      s.honored?.kind === "pin_close",
    );
  }

  // The GovInfo sweep, exactly as in production: it fetches the published text of these
  // amendment-flagged documents (the replay's real pages) and re-derives each window.
  const sweep = await govinfoSweepOnce(sql, NOW, {
    fetchHtml: async (_pub, doc) => (govRow(doc).raw as { html: string }).html,
    sleep: async () => {},
  });
  assert(
    "sweep: both windows' published text lands on their own chains",
    sweep.ingested === 2 && sweep.failed === 0,
    JSON.stringify(sweep),
  );
  const govCount = await sql`
    select 1 from observations where source = 'govinfo'
      and ocd_id = any(${DOCS.map(ocd)}::text[])
      and fetched_at > (select max(fetched_at) from observations o2
                        where o2.source = 'human_review' and o2.ocd_id = observations.ocd_id)
  `;
  assert(
    "sweep: each govinfo row is NEWER than the window's verdict (the regression's precondition)",
    govCount.length === 2,
  );

  for (const doc of DOCS) {
    const r = await reconcileOcdId(sql, ocd(doc), NOW);
    const w = await win(doc);
    const b = before.get(doc)!;
    assert(
      `${doc} after the sweep (reconcileOcdId): still HIGH + human_resolved, same close, no version bump`,
      w.confidence === "high" &&
        w.conflict_flags.includes("human_resolved") &&
        w.resolved_close_utc?.getTime() === b.resolved_close_utc?.getTime() &&
        w.version === b.version &&
        w.status === b.status &&
        !r.persist.versionBumped,
      `${w.confidence} ${JSON.stringify(w.conflict_flags)} ${w.resolved_close_utc?.toISOString()} v${w.version}`,
    );
    const s = await reviewShow(sql, ocd(doc), { now: NOW });
    assert(
      `${doc} after: review show still reports the pin honored`,
      s.honored?.kind === "pin_close" && s.honored.parked === false,
      JSON.stringify(s.honored),
    );
    assert(
      `${doc} after: show's sources (the --expect set) are FR + Regs only; govinfo is context`,
      s.sources
        .map((x) => x.source)
        .sort()
        .join() === "federal_register,regulations_gov" &&
        s.context.length === 1 &&
        s.context[0]!.source === "govinfo",
      JSON.stringify(s.sources.map((x) => x.source)),
    );
  }
  assert(
    "the open window (18297) is not in the review queue",
    !(await reviewQueue(sql)).some((q) => q.ocd_id === ocd("2026-18297")),
  );

  // A resolve bound to exactly the hashes `show` lists succeeds and records no govinfo hash.
  const s18297 = await reviewShow(sql, ocd("2026-18297"), { now: NOW });
  const res = await resolveWindow(
    sql,
    {
      ocdId: ocd("2026-18297"),
      kind: "pin_close",
      close: "2026-11-09",
      note: "re-confirmed after the published text landed (regression test)",
      operator: "test",
      expect: s18297.sources.map((x) => x.payload_hash),
    },
    new Date("2026-10-27T13:00:00Z"),
  );
  const govHash = govRow("2026-18297").payload_hash;
  const [stored] = await sql<{ payload_hash: string }[]>`
    select payload_hash from observations where source = 'govinfo' and ocd_id = ${ocd("2026-18297")}
  `;
  assert(
    "resolve with --expect = show's hashes succeeds; reviewed_payload_hashes exclude govinfo",
    res.inserted &&
      res.honored === true &&
      res.reviewedHashes.length === 2 &&
      !res.reviewedHashes.includes(stored!.payload_hash) &&
      !res.reviewedHashes.includes(govHash),
    JSON.stringify(res.reviewedHashes),
  );

  // Real new evidence still un-honors through the same DB path: a newer FR payload for 15026.
  const fr15026 = hr.filter(
    (o) => o.ocd_id === ocd("2026-15026") && o.source === "federal_register",
  )[0]!;
  await ingestObservation(sql, {
    ...parseFrObservation({
      ...(fr15026.raw as Record<string, unknown>),
      comments_close_on: "2026-09-30",
    }),
    fetched_at: "2026-10-27T14:00:00.000Z",
  });
  await reconcileOcdId(sql, ocd("2026-15026"), NOW);
  const s15026 = await reviewShow(sql, ocd("2026-15026"), { now: NOW });
  const w15026 = await win("2026-15026");
  assert(
    "a newer FR observation still supersedes the 15026 pin (derivation returns to the sources)",
    s15026.honored === null &&
      !w15026.conflict_flags.includes("human_resolved"),
    `${w15026.confidence} ${JSON.stringify(w15026.conflict_flags)}`,
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
