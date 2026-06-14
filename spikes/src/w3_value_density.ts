/**
 * W3 — In-basin value density  (BUSINESS KILL-SHOT)
 *
 * Q: For one real Chesapeake HUC-8 subbasin, how many NOVEL (previously-unknown-to-the-org) in-basin
 *    Tier-1 windows appear per quarter, split EIS vs Regs.gov?
 * Gates: if it's 2-3/quarter, the paid-seat thesis is dead regardless of architecture quality.
 *
 * Method (see § W3):
 *   1. Resolve a HUC-8 (e.g. Choptank 02060005) to polygon + counties + named water bodies via
 *      The National Map WBD ArcGIS REST:
 *      hydro.nationalmap.gov/arcgis/rest/services/wbd/MapServer/<layer>/query?where=huc8='02060005'&f=json
 *   2. Over the last 4 quarters of Mirrulations/spicy-regs + an EIS sample, count federal docket +
 *      EIS records plausibly in-basin (manual + keyword — an ESTIMATE, not the production classifier).
 *   3. Split EIS vs Regs.gov-rulemaking, per quarter.
 *
 * Decision rule:
 *   >~ a handful of novel in-basin Tier-1 windows/quarter, EIS a meaningful share -> GO.
 *   ~2-3/quarter or EIS share ~0 -> STOP; reconsider basin, scope, or whether WW is a product.
 *
 * Output: out/W3_value_density.md
 */
async function main() {
  throw new Error("W3 not implemented — see method above and docs/plans/week1-validation-spikes.md");
}
main();
