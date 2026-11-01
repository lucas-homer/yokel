/**
 * review-fingerprint-db.test.ts — `review show` fingerprints through the real ingest → show path
 * (src/review/core.ts reviewShow), so the fingerprint the shadow ledger records is computed from what
 * the observation log actually stores (envelope + raw), not from a hand-built object.
 *
 *   • A Regs re-fetch that only bumps modifyDate is a NEW observation with a NEW payload hash (the
 *     log dedupes on the hash) but the SAME fingerprint; the FR row is untouched.
 *   • A Regs re-fetch that moves commentEndDate (time of day only) changes the fingerprint.
 *   • Every --expect hash `show` lists still equals the stored payload hash (the write binding is
 *     unchanged), and no fingerprint equals a hash.
 *
 * Requires a throwaway Postgres:  DATABASE_URL=postgres://... pnpm --filter @yokel/docketclock test
 */
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { createClient } from "../src/db/client.js";
import { runMigrations } from "../src/db/migrate.js";
import { parseFrObservation } from "../src/sources/federal-register.js";
import { parseRegsObservation } from "../src/sources/regulations-gov.js";
import { ingestObservation } from "../src/ingest/observe.js";
import { reconcileOcdId } from "../src/reconcile/persist.js";
import { reviewShow } from "../src/review/core.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

const HERE = dirname(fileURLToPath(import.meta.url));
const frFixture = JSON.parse(
  await readFile(join(HERE, "fixtures", "fr-2025-02910.json"), "utf8"),
) as Record<string, unknown>;
const regsFixture = JSON.parse(
  await readFile(
    join(HERE, "fixtures", "regs-FAA-2025-5396-0001.json"),
    "utf8",
  ),
) as {
  data: { id: string; attributes: Record<string, unknown> };
};
const OCD = "ocd-participation-window/federal/2025-02910";
const NOW = new Date("2026-09-02T00:00:00Z");
const regs = (attrs: Record<string, unknown>) => {
  const r = JSON.parse(JSON.stringify(regsFixture)) as typeof regsFixture;
  Object.assign(r.data.attributes, {
    frDocNum: "2025-02910",
    commentEndDate: "2026-09-21T03:59:59Z",
    withdrawn: false,
    openForComment: true,
    modifyDate: "2026-09-01T09:00:00Z",
    ...attrs,
  });
  return r;
};

const sql = createClient();
try {
  await sql.unsafe(
    "drop schema if exists public cascade; create schema public;",
  );
  await runMigrations(sql);
  await ingestObservation(sql, {
    ...parseFrObservation({ ...frFixture, comments_close_on: "2026-09-15" }),
    fetched_at: "2026-09-01T00:00:00.000Z",
  });
  await ingestObservation(sql, {
    ...parseRegsObservation(regs({})),
    fetched_at: "2026-09-01T01:00:00.000Z",
  });
  await reconcileOcdId(sql, OCD, NOW);

  const bySource = (s: Awaited<ReturnType<typeof reviewShow>>, src: string) =>
    s.sources.find((x) => x.source === src)!;
  const d0 = await reviewShow(sql, OCD, { blind: true });
  const fr0 = bySource(d0, "federal_register"),
    rg0 = bySource(d0, "regulations_gov");
  assert(
    "SHOW: every source carries an fp1 fingerprint",
    d0.sources.every((x) => /^fp1:[0-9a-f]{64}$/.test(x.fingerprint)),
    JSON.stringify(d0.sources.map((x) => x.fingerprint)),
  );

  // Day 2: Regulations.gov re-serves the same document with only modifyDate bumped.
  const r1 = await ingestObservation(sql, {
    ...parseRegsObservation(regs({ modifyDate: "2026-09-02T09:00:36Z" })),
    fetched_at: "2026-09-02T01:00:00.000Z",
  });
  assert(
    "INGEST: the modifyDate-only re-fetch is a new observation (new payload hash)",
    r1.inserted === true,
  );
  const d1 = await reviewShow(sql, OCD, { blind: true });
  const fr1 = bySource(d1, "federal_register"),
    rg1 = bySource(d1, "regulations_gov");
  assert(
    "DRIFT: the Regs payload hash moved",
    rg1.payload_hash !== rg0.payload_hash,
  );
  assert(
    "DRIFT: the Regs fingerprint did not",
    rg1.fingerprint === rg0.fingerprint,
    `${rg0.fingerprint} vs ${rg1.fingerprint}`,
  );
  assert(
    "DRIFT: the FR hash and fingerprint are untouched",
    fr1.payload_hash === fr0.payload_hash &&
      fr1.fingerprint === fr0.fingerprint,
  );

  // Day 3: the portal close moves by time of day only (same Eastern calendar date).
  await ingestObservation(sql, {
    ...parseRegsObservation(
      regs({
        modifyDate: "2026-09-03T09:00:00Z",
        commentEndDate: "2026-09-21T03:00:00Z",
      }),
    ),
    fetched_at: "2026-09-03T01:00:00.000Z",
  });
  const d2 = await reviewShow(sql, OCD, { blind: true });
  const rg2 = bySource(d2, "regulations_gov");
  assert(
    "CHANGE: a time-of-day move of commentEndDate changes the fingerprint",
    rg2.fingerprint !== rg1.fingerprint,
  );

  // The write binding is unchanged: the hashes `show` lists are the stored payload hashes.
  const stored = await sql<{ source: string; payload_hash: string }[]>`
    select distinct on (source) source, payload_hash from observations
    where ocd_id = ${OCD} and source in ('federal_register', 'regulations_gov')
    order by source, fetched_at desc`;
  const want = new Set(stored.map((r) => r.payload_hash));
  assert(
    "EXPECT: show's hashes are exactly the latest stored payload hashes",
    d2.sources.length === want.size &&
      d2.sources.every((x) => want.has(x.payload_hash)),
  );
  assert(
    "EXPECT: no fingerprint equals a payload hash",
    d2.sources.every(
      (x) => !want.has(x.fingerprint) && !want.has(x.fingerprint.slice(4)),
    ),
  );

  // Non-blind show computes the same fingerprints (the ledger may record either view).
  const d2open = await reviewShow(sql, OCD);
  assert(
    "BLIND: blind and non-blind show agree on fingerprints",
    JSON.stringify(d2open.sources.map((x) => x.fingerprint).sort()) ===
      JSON.stringify(d2.sources.map((x) => x.fingerprint).sort()),
  );
} finally {
  await sql.end();
}

console.log("review-fingerprint-db.test.ts");
console.log(out.join("\n"));
if (failures > 0) {
  console.error(`\n${failures} failure(s)`);
  process.exit(1);
}
console.log(`\nall ${out.length} passed`);
