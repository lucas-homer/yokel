/**
 * D3 — Extension/correction/reopening volume & deny-list false positives
 *
 * Q: How many genuine extension/correction/reopening/withdrawal notices per day, and how noisy is
 *    the keyword detector (the BLM "land-withdrawal extension" trap)?
 * Gates: whether the human-review console is a ~20-min/day chore or a part-time staffing line; and
 *    whether the LLM chain-classifier is load-bearing from day 1.
 *
 * Method (see § D3): over Mirrulations/spicy-regs Parquet via DuckDB httpfs:
 *   - count title ~ '(extension|reopen|correction|withdraw)' over a recent 90-day window
 *   - hand-label a 50-row sample: does each actually MOVE a comment deadline? precision = movers/50
 *   - project daily genuine-mover volume
 *
 * Decision rule:
 *   precision >= ~0.7 -> deterministic deny-list + keywords enough for v1; LLM adjudicates the rest.
 *   precision <  ~0.5 -> LLM chain-classifier is load-bearing from day 1; tighten deny-list.
 *   genuine movers > ~15/day -> review console is a staffed line (flag it).
 *
 * Output: out/D3_extension_volume.md (+ the 50-row labeled sheet)
 */
async function main() {
  throw new Error("D3 not implemented — see method above and docs/plans/week1-validation-spikes.md");
}
main();
