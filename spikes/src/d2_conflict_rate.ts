/**
 * D2 — FR <-> Regs.gov Eastern-date conflict rate
 *
 * Q: How often do FR comments_close_on and Regs.gov commentEndDate disagree when BOTH normalized to
 *    America/New_York calendar date? And how many are tz-only false positives a naive UTC compare
 *    would have mis-flagged?
 * Gates: product positioning — "conflict intelligence" vs "reliable alerts". Validates the
 *    load-bearing Eastern-date rule.
 *
 * Method (see § D2): over the D1 join, in DuckDB:
 *   - fr_eastern_date   = CAST(comments_close_on AS DATE)
 *   - regs_eastern_date = CAST(timezone('America/New_York', commentEndDate::TIMESTAMPTZ) AS DATE)
 *   - true_conflicts     = fr_eastern_date <> regs_eastern_date
 *   - tz_false_positives = differ in UTC but SAME eastern date
 *   Hand-verify ~10 true_conflicts are real (extension/correction), not parse bugs.
 *
 * Decision rule (no kill — positioning input):
 *   conflict_pct >~ 3-5%  -> lead with conflict intelligence; /conflicts is marquee.
 *   conflict_pct <~ 1%    -> lead with reliable alerts + audit log; conflicts is a quiet feature.
 *   tz_false_positives > 0 CONFIRMS the Eastern-normalization rule is necessary.
 *
 * Output: out/D2_conflict_rate.md
 */
async function main() {
  throw new Error("D2 not implemented — see method above and docs/plans/week1-validation-spikes.md");
}
main();
