/**
 * rederive.ts — the shared re-derivation loop: push a list of ocd_ids through the sanctioned path
 * (reconcileWindow → pure engine → persistReconciliation) with per-row failure isolation.
 *
 * Extracted from the #106 one-shot (src/db/rederive-stale-windows.ts) so every "the projection is
 * stale, re-derive it" consumer shares ONE implementation of the loop discipline:
 *   - the version-bump sweep (rederive-stale-windows.ts — stale reconciler_version),
 *   - the per-cycle status refresh (status-refresh.ts — open windows whose close has passed, #107), and
 *   - the per-cycle amended-originals re-derive (rederiveChainOriginals below, reconcile-v2.4).
 *
 * FAILURE ISOLATION: one bad row (e.g. a projection row whose observations were never logged) must not
 * abort the rest — each failure is captured on its row (`error` set, `status` null) and the loop
 * continues. `now` is passed through unchanged so a caller can pin one clock for a whole sweep.
 *
 * EFFECT (ADR 0018 slice 5b): the loops are Effect programs, so each window is a `reconcile.window` child
 * span of the caller's span (see reconcile-window.ts). The Promise exports keep their signatures.
 */
import type { WindowStatus } from "@yokel/contracts";
import { Effect } from "effect";
import { runAmbient } from "../ambient.js";
import type { Sql } from "../db/client.js";
import { dbQuery, type SqlError } from "../db/effect.js";
import type { ChainOriginalsRederiveResult } from "./persist.js";
import { reconcileWindow } from "./reconcile-window.js";

export interface RederivedRow {
  ocd_id: string;
  /** the freshly-derived window status; null when the re-derivation failed. */
  status: WindowStatus | null;
  /** true when the re-derivation MOVED the operative close (audit these — see persist.ts). */
  versionBumped: boolean;
  /** the failure message when the re-derivation failed; null on success. */
  error: string | null;
}

/** Re-derive each ocd_id in order, one transaction per row, isolating per-row failures. Never fails. */
export const rederiveWindows = (
  sql: Sql,
  ocdIds: readonly string[],
  now: Date = new Date(),
): Effect.Effect<RederivedRow[]> =>
  Effect.forEach(ocdIds, (ocd_id) =>
    reconcileWindow(sql, ocd_id, now).pipe(
      Effect.map(
        (r): RederivedRow => ({
          ocd_id,
          status: r.window.status,
          versionBumped: r.persist.versionBumped,
          error: null,
        }),
      ),
      Effect.catch((e) =>
        Effect.succeed<RederivedRow>({
          ocd_id,
          status: null,
          versionBumped: false,
          error: e.message,
        }),
      ),
    ),
  );

/** Promise form of rederiveWindows. */
export function rederiveOcdIds(
  sql: Sql,
  ocdIds: readonly string[],
  now: Date = new Date(),
): Promise<RederivedRow[]> {
  return runAmbient(rederiveWindows(sql, ocdIds, now));
}

/**
 * amendedOriginals — the reconcile-v2.4 trigger (ADR 0016): re-derive every side-A window of the live
 * CONFIDENT cross_window set, so an amendment that arrived (or whose GovInfo text arrived) this cycle
 * moves its original in the SAME cycle instead of waiting for the original's next Regs poll. Runs after
 * the chain pass. LLM-affirmed links (llm_corroborated) are skipped — they never move a date, so
 * re-deriving their originals would be pure churn. Idempotent: an unchanged derivation is a no-op refresh
 * (persistReconciliation's own version discipline). Per-window failures are isolated (counted); a failed
 * read of the originals fails the pass.
 */
export const amendedOriginals = (
  sql: Sql,
  now: Date = new Date(),
): Effect.Effect<ChainOriginalsRederiveResult, SqlError> =>
  Effect.gen(function* () {
    const rows = yield* dbQuery(
      "SELECT chain originals",
      () => sql<{ ocd_id: string }[]>`
        select distinct ocd_id from conflict_records
        where conflict_scope = 'cross_window'
          and resolved_at is null
          and not (conflict_flags @> '["llm_corroborated"]'::jsonb)
        order by ocd_id
      `,
      (rows) => ({ "db.response.returned_rows": rows.length }),
    );
    const derived = yield* rederiveWindows(
      sql,
      rows.map((r) => r.ocd_id),
      now,
    );
    return {
      scanned: rows.length,
      versionBumped: derived.filter((r) => r.versionBumped).length,
      failed: derived.filter((r) => r.error !== null).length,
    };
  });

/** Promise form of amendedOriginals; rejects with the driver's own error, as before. */
export function rederiveChainOriginals(
  sql: Sql,
  now: Date = new Date(),
): Promise<ChainOriginalsRederiveResult> {
  return runAmbient(
    amendedOriginals(sql, now).pipe(Effect.catch((e) => Effect.die(e.cause))),
  );
}
