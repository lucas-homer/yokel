/**
 * D1 — frDocNum join hit-rate  (MASTER GATE)
 *
 * Q: On the live corpus, what fraction of comment-open documents join FR <-> Regulations.gov on
 *    frDocNum / document_number?
 * Gates: the entire reconciliation join strategy.
 *
 * Method (see docs/plans/week1-validation-spikes.md § D1):
 *   1. FR open set (keyless): GET federalregister.gov/api/v1/documents.json
 *      ?conditions[comment_date][gte]=<today> with fields document_number, comments_close_on,
 *      docket_ids, regulations_dot_gov_info, type, action, title  -> data/fr_open.json
 *   2. Regs.gov open set (REGS_KEY, paged, <=1000/hr): GET api.regulations.gov/v4/documents
 *      filter on commentEndDate>=today (VERIFY exact param against the live OpenAPI) -> data/regs_open_*.json
 *   3. DuckDB LEFT JOIN regs_open.frDocNum = fr_open.document_number; compute hit_pct.
 *   4. For misses, measure fallback join on docket_id-array overlap + RIN.
 *
 * Decision rule:
 *   hit_pct >= 60%  -> GO with frDocNum primary key.
 *   hit_pct <  60%  -> PIVOT to Regs.gov-primary + docket_id/RIN fallback; FR-only records get
 *                      confidence=medium, conflict_reason="no_cross_source_join".
 *
 * Output: out/D1_join_rate.md  (regs_open / joined / hit_pct + fallback rate)
 */
async function main() {
  throw new Error("D1 not implemented — see method above and docs/plans/week1-validation-spikes.md");
}
main();
