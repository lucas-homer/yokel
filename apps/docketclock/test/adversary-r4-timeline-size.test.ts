/** Read-only measurement: explicitly point DATABASE_URL at dc_review_prod. */
import { createClient } from "../src/db/client.js";
import { loadAmendmentInputs } from "../src/reconcile/persist.js";
import { amendmentChangedSince } from "../src/reconcile/amendment.js";
const sql = createClient();
try {
  const ids =
    await sql`select distinct ocd_id from observations where source = 'federal_register' order by ocd_id`;
  const results: { id: string; states: number; entries: number; ms: number }[] =
    [];
  const start = performance.now();
  let reversions = 0;
  for (const row of ids) {
    const t = performance.now();
    const loaded = await loadAmendmentInputs(sql, row.ocd_id);
    const timeline = loaded.inputs?.timeline ?? [];
    if (timeline.length) {
      results.push({
        id: row.ocd_id,
        states: timeline.length,
        entries: timeline.reduce((n, s) => n + s.amendments.length, 0),
        ms: performance.now() - t,
      });
      // A verdict just before any history must not survive any transient material amendment.
      if (
        loaded.inputs &&
        loaded.outcome.kind !== "amended" &&
        amendmentChangedSince(0, loaded.outcome, loaded.inputs)
      )
        reversions++;
    }
  }
  results.sort((a, b) => b.states - a.states);
  console.log(
    JSON.stringify(
      {
        originals: ids.length,
        withTimeline: results.length,
        totalStates: results.reduce((n, r) => n + r.states, 0),
        totalEntries: results.reduce((n, r) => n + r.entries, 0),
        maxEntries: Math.max(...results.map((r) => r.entries)),
        elapsedMs: performance.now() - start,
        reversionsDetected: reversions,
        top: results.slice(0, 10),
      },
      null,
      2,
    ),
  );
} finally {
  await sql.end();
}
