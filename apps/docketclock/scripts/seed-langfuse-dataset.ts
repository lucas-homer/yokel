/**
 * seed-langfuse-dataset.ts — seed a Langfuse EVAL dataset of representative adjudication inputs (Slice C,
 * PR-C3). The `adjudications` table holds the model's OWN past inputs + verdicts but NO ground truth, so we
 * seed each historical verdict as a *provisional* expectedOutput for a human to confirm/correct in Slice D —
 * NOT as a gold label. The script writes ONLY to Langfuse; it never mutates our Postgres.
 *
 * WHAT IT DOES
 *   1. Read every `adjudications` row (cache + replay log).
 *   2. Drop non-deciding rows: a `null:*` adjudicator only ever abstains (`uncertain`), which is no eval
 *      signal. (Override with SEED_INCLUDE_NULL=1.)
 *   3. Dedupe by content_hash (one item per distinct input).
 *   4. STRATIFY by input.kind (notice|chain) × verdict.classification (affirm|reject|uncertain) and cap
 *      SEED_CAP rows per stratum, so the common case can't dominate the set.
 *   5. Upsert each as a Langfuse dataset item: input = the canonical AdjudicationInput, expectedOutput =
 *      the historical verdict, metadata = { content_hash, adjudicator_id, rulebook_version, kind,
 *      classification, provisional: true }. The item id IS the content_hash, so re-running UPSERTS (no
 *      duplicates).
 *
 * STABILITY across cache GROWTH. Selection is OLDEST-first (`created_at asc`, with a content_hash
 * tie-breaker so order is total/deterministic). The adjudications cache is append-only, so once a stratum
 * reaches SEED_CAP the selected set is FIXED: newer rows land at the tail and are never reached, so a
 * re-run after the cache has grown re-selects the SAME items → a true no-op, and the dataset stays capped
 * at SEED_CAP per stratum (it does not accumulate). Raising SEED_CAP and re-running grows the dataset
 * MONOTONICALLY (the next-oldest rows are appended; existing items keep their ids). This deliberately gives
 * Slice D a STABLE corpus to label rather than a window that chases the newest rows. (Langfuse v2's public
 * API exposes no dataset-item delete/prune, so stable selection is the ONLY way to keep the corpus bounded
 * and reproducible — a newest-N window would accumulate past the cap and could never be reconciled.)
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
import { Langfuse } from "langfuse";
import {
  AdjudicationInput,
  AdjudicationVerdict,
  type AdjudicationClassification,
} from "@yokel/contracts";
import { createClient } from "../src/db/client.js";

// Load the repo-root .env (scripts/ → 2 levels up) BEFORE reading env, mirroring the smoke/entrypoints.
process.loadEnvFile(new URL("../../../.env", import.meta.url));

const DATASET_NAME = (process.env.DATASET_NAME || "docketclock-adjudications").trim();
const SEED_CAP = (() => {
  const n = Number(process.env.SEED_CAP);
  return Number.isFinite(n) && n > 0 ? Math.floor(n) : 25;
})();
const INCLUDE_NULL = process.env.SEED_INCLUDE_NULL === "1";
const DRY_RUN = process.argv.includes("--dry-run");

/** One adjudications row as Postgres returns it (input/verdict are jsonb → already-parsed objects). */
interface AdjudicationRow {
  content_hash: string;
  input: unknown;
  verdict: unknown;
  adjudicator_id: string;
  created_at: Date;
}

/** A validated, selectable candidate item. */
interface Candidate {
  contentHash: string;
  adjudicatorId: string;
  input: AdjudicationInput;
  verdict: AdjudicationVerdict;
  kind: AdjudicationInput["kind"];
  classification: AdjudicationClassification;
}

const KINDS = ["notice", "chain"] as const;
const CLASSES = ["affirm", "reject", "uncertain"] as const;
const stratumKey = (k: string, c: string): string => `${k}/${c}`;

async function main(): Promise<void> {
  const sql = createClient();
  try {
    // OLDEST-first, with content_hash as a TOTAL-ORDER tie-breaker (created_at is `default now()` and not
    // unique — a batch/backfill can stamp many rows with the identical instant, leaving SQL row order
    // undefined). Oldest-first over an append-only table makes per-stratum capping a FIXED "oldest N", so
    // the selection — and thus the seeded dataset — is stable and reproducible across reruns even as the
    // cache grows. See the STABILITY note in the header.
    const rows = (await sql<AdjudicationRow[]>`
      select content_hash, input, verdict, adjudicator_id, created_at
      from adjudications
      order by created_at asc, content_hash asc
    `) as unknown as AdjudicationRow[];
    console.log(`read ${rows.length} adjudications row(s)`);

    // Validate + filter, deduped by content_hash (first wins = the oldest deciding verdict given the ORDER
    // BY). The null-skip is a `continue` that never occupies the slot, so a `null:*` abstention can neither
    // shadow nor evict a real verdict for the same input regardless of ordering.
    const byHash = new Map<string, Candidate>();
    let skippedNull = 0;
    let skippedInvalid = 0;
    for (const row of rows) {
      if (byHash.has(row.content_hash)) continue; // already kept a deciding verdict for this input
      // `|| ""` guards against a NULL adjudicator_id throwing here (outside the parse try/catch); the schema
      // marks it NOT NULL, but a deciding verdict missing its provenance is unusable anyway → treat as skip.
      if (!INCLUDE_NULL && (row.adjudicator_id || "").startsWith("null:")) {
        skippedNull++;
        continue;
      }
      let input: AdjudicationInput;
      let verdict: AdjudicationVerdict;
      try {
        input = AdjudicationInput.parse(row.input);
        verdict = AdjudicationVerdict.parse(row.verdict);
      } catch {
        skippedInvalid++; // a row that no longer matches the frozen contract is not a usable eval item
        continue;
      }
      byHash.set(row.content_hash, {
        contentHash: row.content_hash,
        adjudicatorId: row.adjudicator_id,
        input,
        verdict,
        kind: input.kind,
        classification: verdict.classification,
      });
    }
    if (skippedNull) console.log(`skipped ${skippedNull} null:* abstention row(s) (SEED_INCLUDE_NULL=1 to keep)`);
    if (skippedInvalid) console.log(`skipped ${skippedInvalid} row(s) that failed contract validation`);

    // Stratify by kind × classification, cap per stratum (stable: candidates are already oldest-first).
    const strata = new Map<string, Candidate[]>();
    for (const cand of byHash.values()) {
      const key = stratumKey(cand.kind, cand.classification);
      const bucket = strata.get(key) ?? [];
      if (bucket.length < SEED_CAP) bucket.push(cand);
      strata.set(key, bucket);
    }

    // Report the stratification plan across the full grid (so empty strata are visible).
    console.log(`\nstratification (cap ${SEED_CAP}/stratum):`);
    const selected: Candidate[] = [];
    for (const k of KINDS) {
      for (const c of CLASSES) {
        const bucket = strata.get(stratumKey(k, c)) ?? [];
        console.log(`  ${stratumKey(k, c).padEnd(18)} ${bucket.length}`);
        selected.push(...bucket);
      }
    }
    console.log(`\nselected ${selected.length} item(s) for dataset "${DATASET_NAME}"`);

    if (DRY_RUN) {
      console.log("--dry-run: no Langfuse writes.");
      return;
    }
    if (selected.length === 0) {
      console.log("nothing to seed (no deciding adjudications yet); dataset left untouched.");
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

    // Upsert the dataset (idempotent on name), then upsert each item (idempotent on id = content_hash).
    await langfuse.createDataset({
      name: DATASET_NAME,
      description:
        "DocketClock adjudication inputs seeded from the adjudications cache. expectedOutput is the " +
        "model's own historical verdict — PROVISIONAL, pending human labeling in Slice D.",
      metadata: { source: "adjudications-cache", provisional: true },
    });

    let written = 0;
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
      written++;
    }
    await langfuse.shutdownAsync();
    console.log(`upserted ${written} dataset item(s) into "${DATASET_NAME}".`);
  } finally {
    await sql.end({ timeout: 5 });
  }
}

main().catch((err) => {
  console.error("seed failed:", err);
  process.exit(1);
});
