/**
 * seed-langfuse-dataset.ts — seed a Langfuse EVAL dataset of representative adjudication inputs (Slice C,
 * PR-C3). The `adjudications` table holds the model's OWN past inputs + verdicts but NO ground truth, so we
 * seed each historical verdict as a *provisional* expectedOutput for a human to confirm/correct in Slice D —
 * NOT as a gold label. The script writes ONLY to Langfuse; it never mutates our Postgres.
 *
 * This file owns the I/O (read `adjudications`, upsert into Langfuse, logging, --dry-run). The SELECTION
 * decisions — dedup, null-skip, contract validation, stratification, capping — live in the pure, unit-tested
 * `selectDatasetItems()` (src/adjudicator/eval-dataset.ts); see its header for the invariants.
 *
 * WHAT IT DOES
 *   1. Read every `adjudications` row, OLDEST-first (`created_at asc, content_hash asc` — see below).
 *   2. selectDatasetItems(): drop `null:*` abstentions (no eval signal), dedupe by content_hash, validate
 *      against the frozen contract, stratify by kind × classification, cap SEED_CAP per stratum.
 *   3. Upsert each as a Langfuse dataset item: input = the canonical AdjudicationInput, expectedOutput =
 *      the historical verdict, metadata = { content_hash, adjudicator_id, rulebook_version, kind,
 *      classification, provisional: true }. The item id IS the content_hash, so re-running UPSERTS (no
 *      duplicates).
 *
 * STABILITY across cache GROWTH. The SELECT is OLDEST-first with a content_hash tie-breaker (created_at is
 * `default now()` and not unique — a batch/backfill can stamp many rows with the identical instant, leaving
 * SQL row order undefined). Over the append-only cache that makes per-stratum capping a FIXED "oldest N":
 * once a stratum reaches SEED_CAP the selected set is FIXED (newer rows land at the tail and are never
 * reached), so a re-run after the cache has grown re-selects the SAME items → a true no-op, and the dataset
 * stays capped at SEED_CAP per stratum. Raising SEED_CAP and re-running grows the dataset MONOTONICALLY.
 * (Langfuse v2's public API exposes no dataset-item delete/prune, so stable selection is the ONLY way to
 * keep the corpus bounded and reproducible — a newest-N window would accumulate past the cap unreconcilably.)
 *
 * CONFIG (env / .env)
 *   DATABASE_URL            — the docketclock Postgres (port-forward the CNPG `-app` secret's URL locally).
 *   LANGFUSE_HOST           — http://localhost:3001 with `task langfuse`, or the in-cluster svc URL.
 *   LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY
 *   DATASET_NAME            — default "docketclock-adjudications". NOTE: item ids (= content_hash) cannot be
 *                             reused across datasets (Langfuse constraint); use one name per logical corpus.
 *   SEED_CAP                — max items per (kind × classification) stratum; default 25.
 *   SEED_INCLUDE_NULL=1     — also seed null:* abstentions (default: skip them).
 *
 * Run:  pnpm --filter @yokel/docketclock seed:langfuse-dataset            # writes to Langfuse
 *       pnpm --filter @yokel/docketclock seed:langfuse-dataset --dry-run  # prints the plan, writes nothing
 */
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { Langfuse } from "langfuse";
import { createClient } from "../src/db/client.js";
import {
  selectDatasetItems,
  type AdjudicationRow,
} from "../src/adjudicator/eval-dataset.js";

// Load the repo-root .env (scripts/ → 2 levels up) BEFORE reading env, mirroring the smoke/entrypoints.
// GUARDED: skip if absent so a shell/CI that exports the vars directly still runs (unconditional
// loadEnvFile throws ERR_MISSING_DOTENV_FILE on a fresh checkout).
const envPath = fileURLToPath(new URL("../../../.env", import.meta.url));
if (existsSync(envPath)) process.loadEnvFile(envPath);

const DATASET_NAME = (
  process.env.DATASET_NAME || "docketclock-adjudications"
).trim();
const SEED_CAP = (() => {
  const n = Number(process.env.SEED_CAP);
  return Number.isFinite(n) && n > 0 ? Math.floor(n) : 25;
})();
const INCLUDE_NULL = process.env.SEED_INCLUDE_NULL === "1";
const DRY_RUN = process.argv.includes("--dry-run");

async function main(): Promise<void> {
  const sql = createClient();
  try {
    // OLDEST-first with a content_hash tie-breaker for a total, reproducible order (see the STABILITY note).
    const rows = (await sql<AdjudicationRow[]>`
      select content_hash, input, verdict, adjudicator_id, created_at
      from adjudications
      order by created_at asc, content_hash asc
    `) as unknown as AdjudicationRow[];
    console.log(`read ${rows.length} adjudications row(s)`);

    const result = selectDatasetItems(rows, {
      cap: SEED_CAP,
      includeNull: INCLUDE_NULL,
    });
    if (result.skippedNull)
      console.log(
        `skipped ${result.skippedNull} null:* abstention row(s) (SEED_INCLUDE_NULL=1 to keep)`,
      );
    if (result.skippedInvalid)
      console.log(
        `skipped ${result.skippedInvalid} row(s) that failed contract validation`,
      );

    // Report the stratification plan across the full contract-derived grid (empty strata included).
    console.log(`\nstratification (cap ${SEED_CAP}/stratum):`);
    for (const cell of result.grid) {
      console.log(
        `  ${`${cell.kind}/${cell.classification}`.padEnd(18)} ${cell.count}`,
      );
    }
    const selected = result.selected;
    console.log(
      `\nselected ${selected.length} item(s) for dataset "${DATASET_NAME}"`,
    );

    if (DRY_RUN) {
      console.log("--dry-run: no Langfuse writes.");
      return;
    }
    if (selected.length === 0) {
      console.log(
        "nothing to seed (no deciding adjudications yet); dataset left untouched.",
      );
      return;
    }

    const host = (process.env.LANGFUSE_HOST || "").trim();
    const publicKey = (process.env.LANGFUSE_PUBLIC_KEY || "").trim();
    const secretKey = (process.env.LANGFUSE_SECRET_KEY || "").trim();
    if (!host || !publicKey || !secretKey) {
      throw new Error(
        "LANGFUSE_HOST / LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY must all be set to seed the dataset",
      );
    }
    const langfuse = new Langfuse({ publicKey, secretKey, baseUrl: host });

    // Upsert the dataset, then each item. createDataset/createDatasetItem are documented by the SDK as
    // upserts (on name / on id) — re-running overwrites in place, never duplicates. (The name-idempotency is
    // an SDK behavior, not a guarantee we control; a future SDK major could change it.)
    await langfuse.createDataset({
      name: DATASET_NAME,
      description:
        "DocketClock adjudication inputs seeded from the adjudications cache. expectedOutput is the " +
        "model's own historical verdict — PROVISIONAL, pending human labeling in Slice D.",
      metadata: { source: "adjudications-cache", provisional: true },
    });

    for (const cand of selected) {
      await langfuse.createDatasetItem({
        datasetName: DATASET_NAME,
        id: cand.contentHash, // upsert key — re-running this script overwrites, never duplicates.
        input: cand.input,
        expectedOutput: cand.verdict,
        metadata: {
          content_hash: cand.contentHash,
          adjudicator_id: cand.adjudicatorId,
          rulebook_version: cand.input.rulebook_version,
          kind: cand.kind,
          classification: cand.classification,
          provisional: true, // NOT a gold label — a human confirms/corrects this in Slice D.
        },
        status: "ACTIVE",
      });
    }
    await langfuse.shutdownAsync();
    console.log(
      `upserted ${selected.length} dataset item(s) into "${DATASET_NAME}".`,
    );
  } finally {
    await sql.end({ timeout: 5 });
  }
}

main().catch((err) => {
  console.error("seed failed:", err);
  process.exit(1);
});
