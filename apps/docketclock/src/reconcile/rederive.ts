/**
 * rederive.ts — the shared re-derivation loop: push a list of ocd_ids through the sanctioned path
 * (reconcileOcdId → pure engine → persistReconciliation) with per-row failure isolation.
 *
 * Extracted from the #106 one-shot (src/db/rederive-stale-windows.ts) so every "the projection is
 * stale, re-derive it" consumer shares ONE implementation of the loop discipline:
 *   - the version-bump sweep (rederive-stale-windows.ts — stale reconciler_version), and
 *   - the per-cycle status refresh (status-refresh.ts — open windows whose close has passed, #107).
 *
 * FAILURE ISOLATION: one bad row (e.g. a projection row whose observations were never logged) must not
 * abort the rest — each failure is captured on its row (`error` set, `status` null) and the loop
 * continues. `now` is passed through unchanged so a caller can pin one clock for a whole sweep.
 */
import type { WindowStatus } from "@yokel/contracts";
import type { Sql } from "../db/client.js";
import { reconcileOcdId } from "./persist.js";

export interface RederivedRow {
  ocd_id: string;
  /** the freshly-derived window status; null when the re-derivation failed. */
  status: WindowStatus | null;
  /** true when the re-derivation MOVED the operative close (audit these — see persist.ts). */
  versionBumped: boolean;
  /** the failure message when reconcileOcdId threw; null on success. */
  error: string | null;
}

/** Re-derive each ocd_id in order, one transaction per row, isolating per-row failures. */
export async function rederiveOcdIds(
  sql: Sql,
  ocdIds: readonly string[],
  now: Date = new Date(),
): Promise<RederivedRow[]> {
  const rows: RederivedRow[] = [];
  for (const ocd_id of ocdIds) {
    try {
      const r = await reconcileOcdId(sql, ocd_id, now);
      rows.push({
        ocd_id,
        status: r.window.status,
        versionBumped: r.persist.versionBumped,
        error: null,
      });
    } catch (err) {
      rows.push({
        ocd_id,
        status: null,
        versionBumped: false,
        error: err instanceof Error ? err.message : String(err),
      });
    }
  }
  return rows;
}
