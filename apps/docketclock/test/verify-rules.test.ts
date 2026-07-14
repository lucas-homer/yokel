/**
 * verify-rules.test.ts — the PURE verification rules (slice V, PR-V1): select.ts's horizon state
 * machine + verdict.ts's as-of-close judgment. No DB, no network, no wall clock — everything is
 * injected, matching the reconcile.test.ts style (hand-rolled assert, out[] accumulator, process.exit).
 *
 * Covers the plan's pinned fixture chains (plans/verification-accuracy.md §PR-V1.3):
 *   • late-correction        → was_correct=false, the correction observation named as evidence;
 *   • revealed-withdrawal    → was_correct=false, the withdrawal observation named;
 *   • linked-extension       → pre-close extension never reaches the verdict (superseded window is
 *                              NOT wrong) — expressed here as "no post-close observations → correct";
 *   • deferred-re-poll       → NO verdict before a confirmed check: awaiting_check past the horizon,
 *                              due_verdict only once a post-close check lands;
 *   • lapse                  → past the 14d cap with zero checks → due_lapsed → basis
 *                              unverified_lapsed with was_correct=null (never correctness-by-default);
 * plus the reopening-is-not-a-contradiction rule, the missed-extension rule, the unexplained-movement
 * rule, and contract-refinement compliance of every produced verdict shape.
 */
import { AccuracyRecord, AccuracyVerdict } from "@yokel/contracts";
import {
  classifyHorizon,
  DEFAULT_HORIZON_POLICY,
  type HorizonPolicy,
} from "../src/verify/select.js";
import {
  computeVerdict,
  type PostCloseObservation,
  type VerdictInput,
} from "../src/verify/verdict.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

const DAY = 24 * 3_600_000;
const CLOSE = "2026-07-01T04:00:00.000Z"; // the published close under judgment
const closeMs = Date.parse(CLOSE);
const at = (offsetDays: number) => new Date(closeMs + offsetDays * DAY);
const iso = (offsetDays: number) => at(offsetDays).toISOString();

function obs(
  id: string,
  offsetDays: number,
  flags: Partial<
    Pick<
      PostCloseObservation,
      "is_extension" | "is_correction" | "is_withdrawal" | "is_reopening"
    >
  > = {},
): PostCloseObservation {
  return {
    observation_id: id,
    fetched_at: iso(offsetDays),
    is_extension: false,
    is_correction: false,
    is_withdrawal: false,
    is_reopening: false,
    ...flags,
  };
}

function input(over: Partial<VerdictInput> = {}): VerdictInput {
  return {
    publishedCloseUtc: CLOSE,
    currentCloseUtc: CLOSE,
    currentStatus: "closed",
    observationsSinceClose: [],
    lapsed: false,
    ...over,
  };
}

// ── select.ts — the horizon state machine ───────────────────────────────────────────────────────────

out.push("classifyHorizon:");
{
  const facts = (checkedAtDays: number | null) => ({
    publishedCloseUtc: CLOSE,
    confirmedCheckAt: checkedAtDays === null ? null : iso(checkedAtDays),
  });

  assert(
    "close in the future → not_due",
    classifyHorizon(facts(null), at(-1)) === "not_due",
  );
  assert(
    "exactly at close → not_due (nothing post-close yet)",
    classifyHorizon(facts(null), at(0)) === "not_due",
  );
  assert(
    "day 3, no check → in_horizon",
    classifyHorizon(facts(null), at(3)) === "in_horizon",
  );
  assert(
    "day 3, check landed → STILL in_horizon (a day-6 contradiction may still land; verdict waits for horizon exit)",
    classifyHorizon(facts(2), at(3)) === "in_horizon",
  );
  assert(
    "day 8, check landed day 2 → due_verdict",
    classifyHorizon(facts(2), at(8)) === "due_verdict",
  );
  assert(
    "DEFERRED-RE-POLL: day 8, NO check → awaiting_check (horizon EXTENDS; no verdict before a confirmed check)",
    classifyHorizon(facts(null), at(8)) === "awaiting_check",
  );
  assert(
    "day 10, check finally lands day 9 → due_verdict (extension resolved by the late check)",
    classifyHorizon(facts(9), at(10)) === "due_verdict",
  );
  assert(
    "LAPSE: day 15, NO check ever → due_lapsed (past the 14d cap)",
    classifyHorizon(facts(null), at(15)) === "due_lapsed",
  );
  assert(
    "day 15, check landed day 13 → due_verdict (a check anywhere inside the cap beats the lapse)",
    classifyHorizon(facts(13), at(15)) === "due_verdict",
  );
  assert(
    "PRE-close check is NO check: day 8 with a day -1 'check' → awaiting_check (proves nothing about the close)",
    classifyHorizon(facts(-1), at(8)) === "awaiting_check",
  );
  assert(
    "at-close check is NO check (strictly-after rule): day 8, check at day 0 → awaiting_check",
    classifyHorizon(facts(0), at(8)) === "awaiting_check",
  );

  const tight: HorizonPolicy = { horizonMs: 1 * DAY, capMs: 2 * DAY };
  assert(
    "policy is injectable: 1d horizon / 2d cap → day 1.5 no check = awaiting_check, day 2.5 = due_lapsed",
    classifyHorizon(facts(null), at(1.5), tight) === "awaiting_check" &&
      classifyHorizon(facts(null), at(2.5), tight) === "due_lapsed",
  );
  assert(
    "default policy is 7d/14d",
    DEFAULT_HORIZON_POLICY.horizonMs === 7 * DAY &&
      DEFAULT_HORIZON_POLICY.capMs === 14 * DAY,
  );
}

// ── verdict.ts — the as-of-close judgment ───────────────────────────────────────────────────────────

out.push("computeVerdict:");
{
  // LINKED-EXTENSION (the plan's pinned no-contradiction case): an extension linked BEFORE close means
  // the chain already re-derived the window pre-close — its observations are pre-close, so the
  // post-close set is EMPTY and the published (already-extended) close stands. Correct.
  const linkedExtension = computeVerdict(input());
  assert(
    "linked-extension / clean close → was_correct=true, basis post_close_repoll, no evidence ids",
    linkedExtension.was_correct === true &&
      linkedExtension.basis === "post_close_repoll" &&
      linkedExtension.contradicting_observation_ids.length === 0,
  );

  // A post-close check that landed a fresh-but-identical payload: observation exists, nothing moved.
  const uneventfulRepoll = computeVerdict(
    input({ observationsSinceClose: [obs("o-same", 2)] }),
  );
  assert(
    "post-close re-poll with an unchanged close → correct (an unflagged observation alone is not a contradiction)",
    uneventfulRepoll.was_correct === true &&
      uneventfulRepoll.basis === "post_close_repoll",
  );

  // LATE-CORRECTION: a correction lands day 2 and the reconciled close moved. The claim was wrong at
  // close time; the correction observation is the evidence.
  const lateCorrection = computeVerdict(
    input({
      currentCloseUtc: iso(10),
      observationsSinceClose: [obs("o-corr", 2, { is_correction: true })],
    }),
  );
  assert(
    "LATE-CORRECTION → was_correct=false, basis late_amendment, correction id named",
    lateCorrection.was_correct === false &&
      lateCorrection.basis === "late_amendment" &&
      lateCorrection.contradicting_observation_ids.join(",") === "o-corr",
  );

  // A correction that did NOT move the close (typo fix elsewhere in the notice) is not a contradiction.
  const harmlessCorrection = computeVerdict(
    input({
      observationsSinceClose: [obs("o-corr2", 2, { is_correction: true })],
    }),
  );
  assert(
    "correction that moved NOTHING → correct (the published close was and stays the operative value)",
    harmlessCorrection.was_correct === true,
  );

  // REVEALED-WITHDRAWAL: we learn post-close the action was withdrawn — contradiction even though the
  // reconciled close never moved.
  const revealedWithdrawal = computeVerdict(
    input({
      observationsSinceClose: [obs("o-wd", 3, { is_withdrawal: true })],
    }),
  );
  assert(
    "REVEALED-WITHDRAWAL → was_correct=false, withdrawal id named, even with an unmoved close",
    revealedWithdrawal.was_correct === false &&
      revealedWithdrawal.basis === "late_amendment" &&
      revealedWithdrawal.contradicting_observation_ids.join(",") === "o-wd",
  );

  // MISSED EXTENSION: an extension observed only post-close moved the close LATER — the period was in
  // fact still open at the close we published.
  const missedExtension = computeVerdict(
    input({
      currentCloseUtc: iso(20),
      observationsSinceClose: [obs("o-ext", 1, { is_extension: true })],
    }),
  );
  assert(
    "missed extension (post-close, close moved later) → was_correct=false, extension id named",
    missedExtension.was_correct === false &&
      missedExtension.contradicting_observation_ids.join(",") === "o-ext",
  );

  // REOPENING IS NOT A CONTRADICTION: a previously-closed period re-opened after a gap is a FRESH
  // reliance window — the original close was right when published, even though the close moved later.
  const reopening = computeVerdict(
    input({
      currentCloseUtc: iso(30),
      currentStatus: "reopened",
      observationsSinceClose: [obs("o-re", 5, { is_reopening: true })],
    }),
  );
  assert(
    "reopening (flag + status) → was_correct=true despite the moved close",
    reopening.was_correct === true && reopening.basis === "post_close_repoll",
  );

  const reopeningFlagOnly = computeVerdict(
    input({
      currentCloseUtc: iso(30),
      currentStatus: "open", // projection already re-derived to the fresh period
      observationsSinceClose: [obs("o-re2", 5, { is_reopening: true })],
    }),
  );
  assert(
    "reopening by FLAG alone (status already re-derived past 'reopened') → still correct",
    reopeningFlagOnly.was_correct === true,
  );

  // UNEXPLAINED MOVEMENT: the close moved post-close with no flagged notice and no reopening — a
  // changed source payload re-derived a different close. Never correctness-by-default: it's a miss,
  // attributed to the full post-close set.
  const unexplained = computeVerdict(
    input({
      currentCloseUtc: iso(-5), // the "real" close turned out EARLIER than we published
      observationsSinceClose: [obs("o-a", 1), obs("o-b", 2)],
    }),
  );
  assert(
    "unexplained post-close close movement → was_correct=false, ALL post-close ids attributed",
    unexplained.was_correct === false &&
      unexplained.contradicting_observation_ids.join(",") === "o-a,o-b",
  );

  // Close ABSTAINED post-close (current null — e.g. flipped to conflicting-with-null): moved ⇒ miss.
  const abstained = computeVerdict(
    input({ currentCloseUtc: null, observationsSinceClose: [obs("o-x", 2)] }),
  );
  assert(
    "close moved to NULL (post-close abstention) → treated as movement → miss",
    abstained.was_correct === false,
  );

  // Offset-vs-Z spelling of the SAME instant must not read as movement.
  const spelledDifferently = computeVerdict(
    input({
      currentCloseUtc: "2026-07-01T00:00:00.000-04:00", // == CLOSE (2026-07-01T04:00Z)
      observationsSinceClose: [obs("o-s", 2)],
    }),
  );
  assert(
    "same instant spelled with an offset ≠ movement (millisecond equality, not string equality)",
    spelledDifferently.was_correct === true,
  );

  // LAPSE: was_correct=null + basis unverified_lapsed + no ids — the plan's honest abstention.
  const lapsed = computeVerdict(
    input({
      lapsed: true,
      // even with contradicting-looking observations in hand the lapse path must NOT judge: lapsed
      // means classifyHorizon saw ZERO confirmed checks, so these can't exist in practice — but the
      // pure function must still be total and honest on the input.
      observationsSinceClose: [],
    }),
  );
  assert(
    "LAPSE → was_correct=null, basis unverified_lapsed, empty evidence",
    lapsed.was_correct === null &&
      lapsed.basis === "unverified_lapsed" &&
      lapsed.contradicting_observation_ids.length === 0,
  );

  // Every verdict this function can produce must satisfy the 0.9.0 contract refinements.
  for (const [name, v] of [
    ["linked-extension", linkedExtension],
    ["late-correction", lateCorrection],
    ["revealed-withdrawal", revealedWithdrawal],
    ["missed-extension", missedExtension],
    ["reopening", reopening],
    ["unexplained-movement", unexplained],
    ["lapse", lapsed],
  ] as const) {
    assert(
      `verdict shape "${name}" parses under the AccuracyVerdict contract refinements`,
      AccuracyVerdict.safeParse(v).success,
    );
  }

  // And a full assembled record round-trips the AccuracyRecord contract (the run.ts write boundary).
  const full = AccuracyRecord.safeParse({
    ocd_id: "ocd-participation-window/federal/2026-11111",
    window_version: 3,
    confidence_at_close: "high",
    published_close_utc: CLOSE,
    published_close_display: "11:59 p.m. ET",
    verdict: lateCorrection,
    horizon: { closed_at_utc: CLOSE, verified_at_utc: iso(8) },
  });
  assert(
    "full AccuracyRecord (miss) parses under the 0.9.0 contract",
    full.success,
  );
}

console.log(out.join("\n"));
if (failures > 0) {
  console.error(`\n${failures} FAILURE(S)`);
  process.exit(1);
}
console.log("\nALL EXPECTATIONS MET");
