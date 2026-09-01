/**
 * rederive-stale-windows.ts — one-shot sweep: re-derive every participation_window whose
 * reconciler_version differs from the CURRENT engine version, through the sanctioned path
 * (reconcileOcdId → pure engine → persistReconciliation).
 *
 * WHY A SWEEP (not waiting for the poller). Re-derivation is otherwise event-driven — a window is only
 * re-reconciled when a NEW observation arrives for its ocd_id. A rulebook fix that changes the derived
 * projection (e.g. reconcile-v1.1's dated FR-only display) therefore reaches only windows that happen to
 * receive fresh observations; settled windows keep the old projection forever. This sweep closes that
 * tail. It exists for every future version bump too (reconcile-v2 is already reserved for Slice R).
 *
 * SAFE BY CONSTRUCTION. participation_windows is a re-derivable projection, so this is a refresh, not a
 * mutation of source data: the observation log is read-only here, persistReconciliation's own transaction
 * + version-bump discipline applies unchanged (an unchanged close is an idempotent no-op refresh; a moved
 * close bumps `version` and appends change_history exactly as a live re-derivation would), and the
 * conflict proof feed moves atomically with each window. No trigger is disabled; nothing is fabricated.
 *
 * FAILURE ISOLATION: one bad window (e.g. a projection row whose observations were never logged) must not
 * abort the sweep — failures are caught per-ocd_id and reported at the end. IDEMPOTENT: a completed sweep
 * leaves nothing stale, so a re-run scans 0 rows.
 *
 * Run (in-cluster, using the deployed image + its DATABASE_URL — via tsx, NOT `node dist/`: the image
 * consumes @yokel/contracts as TypeScript source, see the Dockerfile header):
 *   kubectl -n docketclock exec deploy/docketclock-poller -- pnpm exec tsx src/db/rederive-stale-windows.ts
 * or locally: DATABASE_URL=... pnpm --filter @yokel/docketclock tsx src/db/rederive-stale-windows.ts
 */
import { pathToFileURL } from "node:url";
import { createClient, type Sql } from "./client.js";
import { RECONCILER_VERSION } from "../reconcile/reconcile.js";
import { reconcileOcdId } from "../reconcile/persist.js";

export interface RederiveResult {
  scanned: number; // stale windows found (reconciler_version ≠ current)
  rederived: number; // successfully re-derived through reconcileOcdId
  versionBumped: number; // re-derivations where the operative close MOVED (audit these!)
  failed: number; // windows whose re-derivation threw (listed in `failures`)
  failures: { ocd_id: string; error: string }[];
}

/**
 * Re-derive every window stamped with a non-current reconciler_version. `now` is fixed once per sweep so
 * the run is internally consistent (open/closed status, change_history stamps).
 */
export async function rederiveStaleWindows(
  sql: Sql,
  now: Date = new Date(),
): Promise<RederiveResult> {
  const stale = await sql<{ ocd_id: string }[]>`
    select ocd_id from participation_windows
    where reconciler_version is distinct from ${RECONCILER_VERSION}
    order by ocd_id
  `;

  let rederived = 0;
  let versionBumped = 0;
  const failures: { ocd_id: string; error: string }[] = [];

  for (const { ocd_id } of stale) {
    try {
      const r = await reconcileOcdId(sql, ocd_id, now);
      rederived++;
      if (r.persist.versionBumped) versionBumped++;
    } catch (err) {
      failures.push({
        ocd_id,
        error: err instanceof Error ? err.message : String(err),
      });
    }
  }

  return {
    scanned: stale.length,
    rederived,
    versionBumped,
    failed: failures.length,
    failures,
  };
}

// CLI entrypoint — only when run directly, not when imported by tests.
const invokedPath = process.argv[1];
if (invokedPath && import.meta.url === pathToFileURL(invokedPath).href) {
  const sql = createClient();
  try {
    const result = await rederiveStaleWindows(sql);
    console.log(
      `✅ rederive sweep (${RECONCILER_VERSION}): scanned ${result.scanned}, ` +
        `rederived ${result.rederived}, versionBumped ${result.versionBumped}, failed ${result.failed}`,
    );
    for (const f of result.failures) {
      console.error(`  ✗ ${f.ocd_id}: ${f.error}`);
    }
    process.exitCode = result.failed === 0 ? 0 : 1;
  } finally {
    await sql.end();
  }
}
