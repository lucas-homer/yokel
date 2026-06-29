/**
 * export-gold-template.ts — emit the GOLD-LABEL template for the chain-adjudicator eval (Slice D, PR-D1).
 * Reads the `adjudications` cache and runs the SAME pure selection as the Langfuse seed
 * (selectDatasetItems, oldest-first + capped + stratified), so the gold corpus holds EXACTLY the same items
 * (content_hashes) as the `docketclock-adjudications` Langfuse dataset. Writes a template with each `gold`
 * left null for a human to fill.
 *
 * SAFE: read-only on Postgres; writes only `eval/chain-gold.template.json`. It NEVER touches
 * `eval/chain-gold.json` (the hand-labeled corpus) — copy the template there and fill in `gold` by hand.
 * Re-running just refreshes the template as the cache grows; existing labels are never clobbered.
 *
 * Each template entry: { content_hash, gold: null, note: "", model_verdict (reference only), input }. The
 * full AdjudicationInput is embedded so a labeler has everything (titles, dates, shared docket/RIN/explicit
 * reference) without any external lookup, and so the eval runner is later self-contained.
 *
 * Run:  DATABASE_URL=… pnpm --filter @yokel/docketclock export:gold-template
 *       …                                                       export:gold-template --dry-run
 */
import { existsSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { createClient } from "../src/db/client.js";
import {
  selectDatasetItems,
  type AdjudicationRow,
} from "../src/adjudicator/eval-dataset.js";

const envPath = fileURLToPath(new URL("../../../.env", import.meta.url));
if (existsSync(envPath)) process.loadEnvFile(envPath);

const SEED_CAP = (() => {
  const n = Number(process.env.SEED_CAP);
  return Number.isFinite(n) && n > 0 ? Math.floor(n) : 25;
})();
const INCLUDE_NULL = process.env.SEED_INCLUDE_NULL === "1";
const DRY_RUN = process.argv.includes("--dry-run");

// apps/docketclock/eval/chain-gold.template.json (scripts/ → ../eval/).
const TEMPLATE_PATH = fileURLToPath(
  new URL("../eval/chain-gold.template.json", import.meta.url),
);

async function main(): Promise<void> {
  const sql = createClient();
  try {
    const rows: AdjudicationRow[] = await sql<AdjudicationRow[]>`
      select content_hash, input, verdict, adjudicator_id, created_at
      from adjudications
      order by created_at asc, content_hash asc
    `;
    console.log(`read ${rows.length} adjudications row(s)`);

    const { selected, grid, skippedNull, skippedInvalid } = selectDatasetItems(
      rows,
      { cap: SEED_CAP, includeNull: INCLUDE_NULL },
    );
    if (skippedNull)
      console.log(`skipped ${skippedNull} null:* abstention row(s)`);
    if (skippedInvalid)
      console.log(`skipped ${skippedInvalid} row(s) that failed validation`);
    console.log(`\nstratification (cap ${SEED_CAP}/stratum):`);
    for (const cell of grid) {
      console.log(
        `  ${`${cell.kind}/${cell.classification}`.padEnd(18)} ${cell.count}`,
      );
    }

    // gold left null on purpose — a human fills it. model_verdict is reference only.
    const template = selected.map((cand) => ({
      content_hash: cand.contentHash,
      gold: null as null,
      note: "",
      model_verdict: cand.verdict,
      input: cand.input,
    }));
    console.log(`\nselected ${template.length} item(s) for the gold template`);

    if (DRY_RUN) {
      console.log("--dry-run: no file written.");
      return;
    }
    writeFileSync(TEMPLATE_PATH, JSON.stringify(template, null, 2) + "\n");
    console.log(`wrote ${TEMPLATE_PATH}`);
    console.log(
      "next: copy it to eval/chain-gold.json and set each `gold` to affirm|reject|uncertain.",
    );
  } finally {
    await sql.end({ timeout: 5 });
  }
}

main().catch((err) => {
  console.error("export failed:", err);
  process.exit(1);
});
