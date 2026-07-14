/**
 * verdict.ts — the PURE verdict rules for post-close verification (slice V, PR-V1).
 *
 * `was_correct` judges the claim AS OF CLOSE TIME (plans/verification-accuracy.md, "Decisions
 * locked"): correct ⇔ no post-close observation contradicts the published close — no late correction
 * moving the date, no revealed withdrawal, no missed extension showing the period was actually still
 * open at the close we published. An extension linked BEFORE close does NOT make the superseded
 * window wrong (its observations are pre-close, so they never reach this function — the chain already
 * re-derived the window and the verdict attaches to the window VERSION live at close). A REOPENING is
 * NOT a contradiction: a previously-closed period re-opened after a gap is a FRESH reliance window —
 * the original close was right when published.
 *
 * The contradiction rules, in order (each names its evidence — a miss must cite observation ids):
 *   1. `is_withdrawal` post-close → REVEALED WITHDRAWAL. We learn after close that the action was
 *      withdrawn; the close we published was not the operative deadline.
 *   2. `is_correction` post-close AND the close moved → LATE CORRECTION moving the date.
 *   3. `is_extension` post-close AND the close moved LATER → a MISSED extension: the period was in
 *      fact still open at our published close (had we seen the extension in time, the chain would
 *      have re-derived pre-close, as in the linked-extension case above).
 *   4. The close MOVED with no reopening to explain it → contradiction even without a flagged notice
 *      (e.g. a re-poll landed a changed source payload that re-derived a different close). Never
 *      correctness-by-default: an unexplained post-close date movement is a miss, attributed to every
 *      post-close observation (causation isn't attributable from the pure inputs; the full post-close
 *      set IS the evidence trail).
 *
 * Basis semantics: what the verdict RESTS ON.
 *   • correct  → `post_close_repoll` (≥1 confirmed post-close check landed and nothing contradicts —
 *     the caller only asks for a verdict once classifyHorizon returned due_verdict).
 *   • incorrect → `late_amendment` (the post-close evidence above).
 *   • lapsed   → `unverified_lapsed`, was_correct NULL — the horizon lapsed with ZERO confirmed
 *     checks; true would inflate the headline number, false would smear it. NULL is the only honest
 *     value; lapsed records are excluded from the gauge and counted on the starvation metric.
 *   • `manual` is RESERVED for operator adjudications — never produced by this function.
 *
 * PURE + deterministic: no clock, no SQL. run.ts assembles the inputs.
 */
import type { AccuracyBasis } from "@yokel/contracts";

export interface PostCloseObservation {
  observation_id: string;
  fetched_at: string; // UTC ISO, strictly after the published close (caller filters)
  is_extension: boolean;
  is_correction: boolean;
  is_withdrawal: boolean;
  is_reopening: boolean;
}

export interface VerdictInput {
  /** The close claim under judgment (the verification_watch snapshot value), UTC ISO. */
  publishedCloseUtc: string;
  /** The projection's close AFTER all post-close re-derivations (null if it abstained since). */
  currentCloseUtc: string | null;
  /** The projection's CURRENT status — 'reopened' explains a later close without a contradiction. */
  currentStatus: string;
  /** Every observation for the window fetched strictly AFTER the published close. */
  observationsSinceClose: PostCloseObservation[];
  /** classifyHorizon returned due_lapsed: zero confirmed checks by the hard cap. */
  lapsed: boolean;
}

export interface Verdict {
  was_correct: boolean | null;
  basis: AccuracyBasis;
  contradicting_observation_ids: string[];
}

/** Millisecond-equality of two instants carried as ISO strings (offset/Z spelling must not matter). */
function sameInstant(a: string, b: string | null): boolean {
  if (b === null) return false;
  return new Date(a).getTime() === new Date(b).getTime();
}

export function computeVerdict(input: VerdictInput): Verdict {
  if (input.lapsed) {
    return {
      was_correct: null,
      basis: "unverified_lapsed",
      contradicting_observation_ids: [],
    };
  }

  const closeMoved = !sameInstant(
    input.publishedCloseUtc,
    input.currentCloseUtc,
  );
  const movedLater =
    input.currentCloseUtc !== null &&
    new Date(input.currentCloseUtc).getTime() >
      new Date(input.publishedCloseUtc).getTime();
  // A reopening (flag or already-flipped status) explains a post-close date movement WITHOUT making
  // the original close wrong — a fresh reliance window after a gap, per the locked decision.
  const reopened =
    input.currentStatus === "reopened" ||
    input.observationsSinceClose.some((o) => o.is_reopening);

  const contradicting = new Set<string>();
  for (const o of input.observationsSinceClose) {
    // Rule 1 — revealed withdrawal.
    if (o.is_withdrawal) contradicting.add(o.observation_id);
    // Rule 2 — late correction that moved the date.
    if (o.is_correction && closeMoved) contradicting.add(o.observation_id);
    // Rule 3 — missed extension: the period was still open at our published close. A reopening is
    // the legitimate later-close path and is handled by `reopened` below, not here — the flags are
    // distinct by design (0.5.0: is_reopening is a true peer of is_extension).
    if (o.is_extension && movedLater && !o.is_reopening)
      contradicting.add(o.observation_id);
  }

  // Rule 4 — unexplained post-close close movement (no flagged notice, not a reopening): a changed
  // source payload re-derived a different close. Attribute the full post-close set (see header).
  if (
    contradicting.size === 0 &&
    closeMoved &&
    !reopened &&
    input.observationsSinceClose.length > 0
  ) {
    for (const o of input.observationsSinceClose)
      contradicting.add(o.observation_id);
  }

  if (contradicting.size > 0) {
    return {
      was_correct: false,
      basis: "late_amendment",
      contradicting_observation_ids: [...contradicting].sort(),
    };
  }

  return {
    was_correct: true,
    basis: "post_close_repoll",
    contradicting_observation_ids: [],
  };
}
