/**
 * W2 — EPA EIS database machine-readability  (first anti-skin pillar)
 *
 * Q: Does the EPA EIS database expose a documented machine-readable endpoint / bulk download, or is
 *    ingestion a scraper?
 * Gates: durability of the EIS adapter — the #1 thing DocketClock can't give Watershed Watch.
 *
 * Method (see § W2):
 *   1. Inspect the EPA EIS search app network traffic for a JSON/REST backend; check for a documented
 *      API, an EPA Envirofacts dataset, or a CSV/Excel bulk export.
 *   2. If only HTML: assess scrape stability; check whether the Federal Register EIS-notice stream
 *      can serve as a spine/cross-check for draft/final EIS dates.
 *   3. Pull a 1-month sample; confirm extraction of title, state(s), draft/final, comment dates, link.
 *
 * Decision rule:
 *   documented endpoint/bulk -> GO, EIS adapter is durable.
 *   scraper only -> still GO, but ship the adapter BEHIND an interface with FR EIS-notices as
 *                   fallback/cross-check; budget scraper maintenance; note fragility.
 *
 * Output: out/W2_eis_source.md (+ 1-month extracted sample)
 */
async function main() {
  throw new Error("W2 not implemented — see method above and docs/plans/week1-validation-spikes.md");
}
main();
