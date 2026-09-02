/**
 * status-refresh.ts — the per-cycle status refresh pass (#107): re-derive every window that claims to be
 * OPEN even though its resolved close has passed, so `status` flips closed within one poll interval of
 * the close passing instead of waiting for a new observation that a settled notice may never produce.
 *
 * WHY THIS PASS EXISTS. Re-derivation is otherwise event-driven — only a fresh observation for an ocd_id
 * re-runs the engine. `status` is derived against the clock at derivation time, so an open window whose
 * close later passes stays frozen "open" forever (~2/day were accruing when measured 2026-09-01; the #106
 * sweep incidentally corrected 348 that were stuck in v1 rows). Same failure class as the #106 display
 * tail — a projection frozen at derivation time — but recurring, hence a poll-cycle pass, not a one-shot.
 *
 * THE RULEBOOK DECIDES, NOT THE PREDICATE. The scan predicate (`status='open' and close < now`) also
 * matches windows the engine DELIBERATELY keeps open past their close — Regulations.gov's authoritative
 * openForComment=true wins over a passed date (the late-comment semantic, see the status rule in
 * reconcile.ts). Those re-derive right back to `open` (counted as `stillOpen`) and will re-match every
 * cycle: ~a hundred cheap idempotent re-derives per cycle is the price of keeping the open/closed
 * decision in exactly one place. If that churn ever matters, narrow the predicate — never fork the rule.
 *
 * SINGLE-WRITER: runs inside the sequential poll cycle (after chain, before verify — so a window flipped
 * closed here is snapshot-eligible for the SAME cycle's verification pass), never concurrent with the
 * other writers. versionBumped should be ~0 every cycle — a status flip never moves the close — so a
 * non-zero count is surfaced in the summary for loud logging/alerting, same audit posture as #106.
 */
import type { Sql } from "../db/client.js";
import { rederiveOcdIds } from "./rederive.js";

export interface StatusRefreshSummary {
  /** open windows with a passed close found this cycle (candidates re-derived). */
  scanned: number;
  /** flipped open → closed by this pass. */
  closed: number;
  /** re-derived back to open (the deliberate Regs-openForComment class) — expected steady-state churn. */
  stillOpen: number;
  /** re-derived to any other status (withdrawn/unknown) — rare, driven by the same rulebook. */
  otherStatus: number;
  /** re-derivations that MOVED the operative close. Expected 0 — audit loudly when not. */
  versionBumped: number;
  /** re-derivations that threw (isolated per-row; the row stays as it was for the next cycle). */
  failed: number;
}

/** Re-derive every stale-open window (status='open', close in the past) through the real engine. */
export async function refreshStaleOpenWindows(
  sql: Sql,
  now: Date = new Date(),
): Promise<StatusRefreshSummary> {
  const stale = await sql<{ ocd_id: string }[]>`
    select ocd_id from participation_windows
    where status = 'open'
      and resolved_close_utc is not null
      and resolved_close_utc < ${now.toISOString()}
    order by ocd_id
  `;

  const rows = await rederiveOcdIds(
    sql,
    stale.map((r) => r.ocd_id),
    now,
  );

  const summary: StatusRefreshSummary = {
    scanned: rows.length,
    closed: 0,
    stillOpen: 0,
    otherStatus: 0,
    versionBumped: 0,
    failed: 0,
  };
  for (const r of rows) {
    if (r.error !== null) summary.failed++;
    else if (r.status === "closed") summary.closed++;
    else if (r.status === "open") summary.stillOpen++;
    else summary.otherStatus++;
    if (r.versionBumped) summary.versionBumped++;
  }
  return summary;
}
