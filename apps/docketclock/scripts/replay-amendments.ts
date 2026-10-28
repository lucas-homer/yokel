/** Offline replay against ONLY the two disposable amendment databases.
 * --export-only takes an as-dumped snapshot, without migrations or derivation.
 * Run from apps/docketclock: DATABASE_URL=... pnpm exec tsx scripts/replay-amendments.ts
 *   --mode before|after --now 2026-10-27T19:24:50Z --out /tmp/amend-replay/out/before.json
 */
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname } from "node:path";
import { parseArgs } from "node:util";
import { createClient } from "../src/db/client.js";
import { runMigrations } from "../src/db/migrate.js";
import {
  reconcileOcdId,
  chainReconcileOnce,
} from "../src/reconcile/persist.js";
import type { Adjudicator } from "../src/adjudicator/port.js";

const { values } = parseArgs({
  options: {
    mode: { type: "string" },
    now: { type: "string" },
    out: { type: "string" },
    "export-only": { type: "boolean", default: false },
    "sweep-options": { type: "string", default: '{"cap":10000}' },
  },
});
if (
  !values.mode ||
  !["before", "after"].includes(values.mode) ||
  !values.now ||
  !values.out
)
  throw new Error(
    "Required: --mode before|after --now ISO_DATE --out FILE [--export-only]",
  );
const now = new Date(values.now);
if (!Number.isFinite(now.getTime())) throw new Error("Invalid --now");
const url = new URL(process.env.DATABASE_URL ?? "");
const expected = `dc_replay_${values.mode}`;
if (
  decodeURIComponent(url.pathname.slice(1)) !== expected ||
  !["127.0.0.1", "localhost"].includes(url.hostname) ||
  url.port !== "5434"
)
  throw new Error(`Replay requires localhost:5434/${expected}`);
// Even the before-run refuses outbound HTTP. DB traffic uses postgres.js, not fetch.
const blockedUrls: string[] = [];
const missingDocs = new Set<string>();
const servedDocs = new Set<string>();
const previousFetch = globalThis.fetch;
globalThis.fetch = async (input, init) => {
  const requestUrl =
    typeof input === "string"
      ? input
      : input instanceof URL
        ? input.href
        : input.url;
  const match =
    /^https:\/\/www\.govinfo\.gov\/content\/pkg\/FR-(\d{4}-\d{2}-\d{2})\/html\/([A-Za-z0-9-]+)\.htm$/.exec(
      requestUrl,
    );
  const method =
    init?.method ?? (input instanceof Request ? input.method : "GET");
  if (values.mode !== "after" || !match || method.toUpperCase() !== "GET") {
    blockedUrls.push(requestUrl);
    throw new Error(`Replay forbids fetch: ${method} ${requestUrl}`);
  }
  const doc = match[2]!;
  try {
    const body = await readFile(`/tmp/amend-replay/govinfo/${doc}.htm`, "utf8");
    servedDocs.add(doc);
    return new Response(body, {
      status: 200,
      headers: { "content-type": "text/html; charset=utf-8" },
    });
  } catch (err) {
    if ((err as NodeJS.ErrnoException).code !== "ENOENT") throw err;
    missingDocs.add(doc);
    return new Response("Not in offline replay corpus", { status: 404 });
  }
};
const sql = createClient(url.href);
const meta: Record<string, unknown> = {
  mode: values.mode,
  now: now.toISOString(),
  export_only: values["export-only"],
};
try {
  const [identity] =
    await sql`select current_database() as db, version() as version`;
  meta.database = identity;
  if (!values["export-only"]) {
    meta.migrations = await runMigrations(sql);
    const [{ count: initialGovinfo }] =
      await sql`select count(*)::int as count from observations where source = 'govinfo'`;
    if (values.mode === "after") {
      // Dynamic import keeps this same harness runnable on unmodified HEAD.
      const modulePath = "../src/sources/govinfo.js";
      const mod = await import(modulePath);
      if (typeof mod.govinfoSweepOnce !== "function")
        throw new Error("govinfoSweepOnce export missing");
      const options = JSON.parse(values["sweep-options"]!);
      meta.sweep_options = options;
      const passes: unknown[] = [];
      let previous = initialGovinfo;
      for (let pass = 0; ; pass++) {
        if (pass >= 1000)
          throw new Error("GovInfo sweep failed to converge after 1000 passes");
        const result = await mod.govinfoSweepOnce(sql, now, options);
        const [{ count }] =
          await sql`select count(*)::int as count from observations where source = 'govinfo'`;
        passes.push({ result, appended: count - previous });
        if (count === previous) break;
        previous = count;
      }
      meta.sweep_passes = passes;
    }
    const [{ count: finalGovinfo }] =
      await sql`select count(*)::int as count from observations where source = 'govinfo'`;
    meta.govinfo_observations_appended = finalGovinfo - initialGovinfo;
    const ids =
      await sql`select ocd_id from participation_windows order by ocd_id`;
    for (const { ocd_id } of ids) await reconcileOcdId(sql, ocd_id, now);
    meta.windows_rederived = ids.length;
    let cacheMissAttempts = 0;
    const adjudicator: Adjudicator = {
      // consult/peek append @rulebook_version themselves.
      id: "gemini:gemini-2.5-flash",
      async adjudicate() {
        cacheMissAttempts++;
        throw new Error("CACHE REPLAY ONLY: fresh adjudication forbidden");
      },
    };
    // Zero fresh budget still peeks EVERY cached pair, without noisy misses or invented verdicts.
    meta.chain = await chainReconcileOnce(sql, now, { adjudicator, cap: 0 });
    meta.cache_miss_consult_attempts = cacheMissAttempts;
    if (cacheMissAttempts) throw new Error("Cache-only invariant violated");
    const sides =
      await sql`select distinct ocd_id from conflict_records where resolved_at is null and conflict_scope = 'cross_window' order by ocd_id`;
    for (const { ocd_id } of sides) await reconcileOcdId(sql, ocd_id, now);
    meta.chain_side_a_rederived = sides.length;
    if (blockedUrls.length)
      throw new Error(`Unexpected fetches: ${JSON.stringify(blockedUrls)}`);
  }
  const windows = await sql`
    select ocd_id, status, confidence, resolved_close_utc, resolved_close_display,
           raw_fr_close_date, raw_regs_close_datetime, conflict_flags, current_observation_ids
    from participation_windows order by ocd_id`;
  const conflicts = await sql`
    select ocd_id, ocd_id_b, conflict_scope, conflict_flags
    from conflict_records where resolved_at is null
    order by ocd_id, ocd_id_b, conflict_scope, conflict_flags::text`;
  const review_queue = windows
    .filter((w) => ["conflicting", "stale"].includes(w.confidence))
    .map((w) => w.ocd_id);
  const countBy = (field: string) =>
    Object.fromEntries(
      [...new Set(windows.map((w) => w[field]))]
        .sort()
        .map((value) => [
          value,
          windows.filter((w) => w[field] === value).length,
        ]),
    );
  const counts = {
    windows: windows.length,
    observations: (await sql`select count(*)::int as n from observations`)[0]!
      .n,
    govinfo_observations: (
      await sql`select count(*)::int as n from observations where source = 'govinfo'`
    )[0]!.n,
    adjudications: (await sql`select count(*)::int as n from adjudications`)[0]!
      .n,
    live_conflicts: conflicts.length,
    cross_window: conflicts.filter((c) => c.conflict_scope === "cross_window")
      .length,
    review_queue: review_queue.length,
    confidence: countBy("confidence"),
    status: countBy("status"),
  };
  meta.missing_govinfo_docs = [...missingDocs].sort();
  meta.served_govinfo_docs = [...servedDocs].sort();
  await mkdir(dirname(values.out), { recursive: true });
  await writeFile(
    values.out,
    JSON.stringify(
      { meta, counts, windows, conflicts, review_queue },
      null,
      2,
    ) + "\n",
  );
  console.log(JSON.stringify({ out: values.out, counts, meta }, null, 2));
} finally {
  globalThis.fetch = previousFetch;
  await sql.end();
}
