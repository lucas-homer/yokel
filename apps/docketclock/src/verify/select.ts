/**
 * select.ts — the PURE horizon state machine for post-close verification (slice V, PR-V1).
 *
 * Given one window's verification facts and the clock, classify where it sits in the verification
 * horizon (plans/verification-accuracy.md, "Decisions locked"):
 *
 *   • The horizon is 7 days past the published close (the architecture's "re-poll 7 days past close").
 *     While inside it, the window's source docs stay in the budgeted re-poll set and NO verdict is
 *     written — a contradiction may still land on day 6.
 *   • A verdict REQUIRES a confirmed check — never correctness-by-default. If the window exits the 7d
 *     horizon with ZERO successful post-close checks of its sources (budget pressure deferred every
 *     re-poll), the horizon EXTENDS until one lands…
 *   • …hard-capped at 14 days past close. A window that lapses the cap without a single confirmed
 *     check is due an `unverified_lapsed` record — EXCLUDED from the headline gauge and counted on
 *     the starvation metric, so re-poll starvation is visible instead of silently blended into
 *     "correct".
 *
 * PURE + deterministic: the clock and every fact are injected; SQL lives in run.ts. The caller
 * guarantees `confirmedCheckAt` is a POST-close instant (a successful source check BEFORE close says
 * nothing about the close's correctness), and that windows already carrying a final AccuracyRecord
 * are never passed in.
 */

export interface HorizonPolicy {
  /** Verification horizon past the published close. Default 7 days. */
  horizonMs: number;
  /** Hard cap on horizon extension when no confirmed check lands. Default 14 days. */
  capMs: number;
}

export const DEFAULT_HORIZON_POLICY: HorizonPolicy = {
  horizonMs: 7 * 24 * 3_600_000,
  capMs: 14 * 24 * 3_600_000,
};

export type HorizonState =
  /** The published close hasn't passed — not verification work at all. */
  | "not_due"
  /** Inside close+horizon: keep the window's sources in the re-poll set; no verdict yet. */
  | "in_horizon"
  /** Past close+horizon with ZERO confirmed post-close checks: the horizon EXTENDS (keep re-polling). */
  | "awaiting_check"
  /** Past close+horizon AND ≥1 confirmed post-close check landed: write the FINAL verdict now. */
  | "due_verdict"
  /** Past close+cap with ZERO confirmed checks ever: write `unverified_lapsed` (starvation, visible). */
  | "due_lapsed";

export interface HorizonFacts {
  /** The published close under judgment (the verification_watch snapshot value), UTC ISO. */
  publishedCloseUtc: string;
  /**
   * The latest CONFIRMED POST-CLOSE check of the window's sources, or null if none has landed.
   * "Confirmed check" = a successful source fetch strictly AFTER the published close: a regs
   * re-poll detail fetch (regs_poll_watch.last_checked_at — it advances even on a dedupe-skip),
   * or ANY post-close observation landing for the window (an observation IS a successful fetch).
   */
  confirmedCheckAt: string | null;
}

export function classifyHorizon(
  facts: HorizonFacts,
  now: Date,
  policy: HorizonPolicy = DEFAULT_HORIZON_POLICY,
): HorizonState {
  const close = new Date(facts.publishedCloseUtc).getTime();
  const t = now.getTime();
  if (t <= close) return "not_due";

  // A pre-close (or exactly-at-close) check proves nothing about the close's correctness — treat it
  // as no check. Defensive: the caller should already pass only post-close instants.
  const checked =
    facts.confirmedCheckAt !== null &&
    new Date(facts.confirmedCheckAt).getTime() > close;

  if (t <= close + policy.horizonMs) return "in_horizon";
  if (checked) return "due_verdict";
  if (t <= close + policy.capMs) return "awaiting_check";
  return "due_lapsed";
}
