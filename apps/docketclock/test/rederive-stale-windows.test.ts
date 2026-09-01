/**
 * rederive-stale-windows.test.ts — the stale-projection re-derive sweep (src/db/rederive-stale-windows.ts).
 *
 * Proves the load-bearing properties:
 *   • SELECTIVE — only windows whose reconciler_version differs from the current RECONCILER_VERSION are
 *     scanned; a current row is left completely untouched (same derived_at).
 *   • REAL RE-DERIVATION — a v1-stamped FR-only row with the v1 DATELESS display is re-derived through
 *     the actual engine: the display regains its calendar date and the row is re-stamped to the current
 *     version. This is the exact production tail the sweep exists to close (reconcile-v1.1, PR #104).
 *   • NO SPURIOUS VERSION BUMP — an unchanged operative close is an idempotent refresh: `version` stays
 *     put and change_history stays empty (superseded-close history is never polluted by a display fix).
 *   • FAILURE ISOLATION — an orphan projection row (no observations in the log) is reported in
 *     `failures` without aborting the rest of the sweep, and stays stale for the next run.
 *   • IDEMPOTENT — once nothing is stale, a re-run scans 0.
 *
 * Requires a throwaway Postgres:  DATABASE_URL=postgres://... pnpm --filter @yokel/docketclock test
 */
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { createClient } from "../src/db/client.js";
import { runMigrations } from "../src/db/migrate.js";
import { parseFrObservation } from "../src/sources/federal-register.js";
import { ingestObservation } from "../src/ingest/observe.js";
import { RECONCILER_VERSION } from "../src/reconcile/reconcile.js";
import { reconcileOcdId } from "../src/reconcile/persist.js";
import { rederiveStaleWindows } from "../src/db/rederive-stale-windows.js";

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

const NOW = new Date("2026-06-01T00:00:00Z"); // fixed clock for deterministic stamps

// The v1 display string exactly as production v1 rows carry it (dateless — the bug v1.1 fixed).
const V1_DATELESS_DISPLAY = "11:59 p.m. ET (inferred from FR date-only value)";

const sql = createClient();
try {
  await sql.unsafe(
    "drop schema if exists public cascade; create schema public;",
  );
  await runMigrations(sql);

  // ── seed window A: FR-only date-only close, then hand-regress it to the v1 state ────────────────────
  const frRawA = { ...frFixture, comments_close_on: "2026-09-10" };
  await ingestObservation(sql, parseFrObservation(frRawA));
  const OCD_A = "ocd-participation-window/federal/2025-02910";
  await reconcileOcdId(sql, OCD_A, NOW);
  await sql`
    update participation_windows
    set reconciler_version = 'reconcile-v1', resolved_close_display = ${V1_DATELESS_DISPLAY}
    where ocd_id = ${OCD_A}
  `;

  // ── seed window B: identical shape but already stamped with the CURRENT version ─────────────────────
  const frRawB = {
    ...frFixture,
    document_number: "2025-77777",
    comments_close_on: "2026-10-01",
  };
  await ingestObservation(sql, parseFrObservation(frRawB));
  const OCD_B = "ocd-participation-window/federal/2025-77777";
  await reconcileOcdId(sql, OCD_B, NOW);
  const [bBefore] = await sql<{ derived_at: Date }[]>`
    select derived_at from participation_windows where ocd_id = ${OCD_B}
  `;

  // ── sweep #1: A re-derived, B untouched ─────────────────────────────────────────────────────────────
  const SWEEP_NOW = new Date("2026-06-02T00:00:00Z");
  const res1 = await rederiveStaleWindows(sql, SWEEP_NOW);
  assert(
    "SELECTIVE: sweep scans exactly the 1 stale window",
    res1.scanned === 1 && res1.rederived === 1 && res1.failed === 0,
    JSON.stringify(res1),
  );

  const [a] = await sql<
    {
      resolved_close_display: string;
      reconciler_version: string;
      version: number;
      change_history: unknown[];
    }[]
  >`
    select resolved_close_display, reconciler_version, version, change_history
    from participation_windows where ocd_id = ${OCD_A}
  `;
  assert(
    "RE-DERIVED: v1 dateless display regains its calendar date",
    a!.resolved_close_display ===
      "closes 2026-09-10 at 11:59 p.m. ET (inferred from FR date-only value)",
    a!.resolved_close_display,
  );
  assert(
    "RE-DERIVED: row re-stamped with the current RECONCILER_VERSION",
    a!.reconciler_version === RECONCILER_VERSION,
    a!.reconciler_version,
  );
  assert(
    "NO SPURIOUS BUMP: unchanged close keeps version 0 + empty change_history",
    a!.version === 0 &&
      Array.isArray(a!.change_history) &&
      a!.change_history.length === 0 &&
      res1.versionBumped === 0,
    `version=${a!.version} history=${a!.change_history.length} bumped=${res1.versionBumped}`,
  );

  const [bAfter] = await sql<{ derived_at: Date }[]>`
    select derived_at from participation_windows where ocd_id = ${OCD_B}
  `;
  assert(
    "SELECTIVE: current-version window B is untouched (derived_at unchanged)",
    bAfter!.derived_at.getTime() === bBefore!.derived_at.getTime(),
    `${bBefore!.derived_at.toISOString()} → ${bAfter!.derived_at.toISOString()}`,
  );

  // ── idempotent: nothing stale left, second run scans 0 ──────────────────────────────────────────────
  const res2 = await rederiveStaleWindows(sql, SWEEP_NOW);
  assert(
    "IDEMPOTENT: second sweep scans 0",
    res2.scanned === 0 && res2.rederived === 0 && res2.failed === 0,
    JSON.stringify(res2),
  );

  // ── failure isolation: an orphan stale row (no observations) fails alone, sweep completes ───────────
  const OCD_C = "ocd-participation-window/federal/ORPHAN-0001";
  await sql`
    insert into participation_windows (ocd_id, window_type, confidence, status, reconciler_version)
    values (${OCD_C}, 'comment_period', 'unknown', 'open', 'reconcile-v1')
  `;
  // Regress A again so the sweep has one good + one bad row in the same pass.
  await sql`
    update participation_windows set reconciler_version = 'reconcile-v1' where ocd_id = ${OCD_A}
  `;
  const res3 = await rederiveStaleWindows(sql, SWEEP_NOW);
  assert(
    "ISOLATION: good row re-derives while the orphan fails",
    res3.scanned === 2 && res3.rederived === 1 && res3.failed === 1,
    JSON.stringify(res3),
  );
  assert(
    "ISOLATION: the failure names the orphan and its cause",
    res3.failures.length === 1 &&
      res3.failures[0]!.ocd_id === OCD_C &&
      /no observations/.test(res3.failures[0]!.error),
    JSON.stringify(res3.failures),
  );
  const [c] = await sql<{ reconciler_version: string }[]>`
    select reconciler_version from participation_windows where ocd_id = ${OCD_C}
  `;
  assert(
    "ISOLATION: the failed orphan STAYS stale (visible to the next run)",
    c!.reconciler_version === "reconcile-v1",
    c!.reconciler_version,
  );
} finally {
  await sql.end();
}

console.log("\n=== rederive-stale-windows results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
