/**
 * Watershed Watch — basin-scoped environmental deadline-and-action radar (the first vertical wedge).
 *
 * STUB. Thick vertical, SELECTIVE reuse of DocketClock (fit verdict: yes-partially).
 * RENTS from DocketClock: reconciled federal windows, confidence/conflict model, OCD-IDs, govinfo_url.
 * OWNS (the anti-skin IP): EPA EIS adapter + 45/30 clock + EIS-vs-FR extension reconciliation,
 *   USGS WBD/HUC geo-recall, the monitor→act→receipt loop, coverage-tier labeling.
 *
 * See:
 *   - docs/architecture/watershed-watch.md  (the design + fit analysis)
 *   - docs/plans/week1-validation-spikes.md  (W1 POST /comments, W2 EIS source, W3 value density)
 *
 * Gating: build only after a STAFFED Chesapeake partner commits. Standalone contingency exists if
 * the partner window opens before DocketClock has its first B2B customer — but never fork the
 * @yokel/contracts schema, only the deployment.
 */
export function placeholder(): null {
  // TODO: gated behind a committed design partner + the Week-1 spikes (esp. W3 value density).
  return null;
}
