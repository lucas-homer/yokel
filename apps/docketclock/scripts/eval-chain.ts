/**
 * eval-chain.ts — run the chain adjudicator over the human gold corpus and score it (Slice D, PR-D2).
 * `pnpm --filter @yokel/docketclock eval:chain [--min-accuracy <x>] [--limit <n>]`.
 *
 * CORE (always runs, Langfuse-independent): loadGold() → adjudicate(input) per item → scoreEval() → print
 * the binary "amends?" headline + the 3×3 confusion matrix. Needs only ADJUDICATOR=gemini + GEMINI_API_KEY.
 * This is exactly what the nightly/on-merge CI gate runs (no Langfuse, no Postgres).
 *
 *   • CACHE-BYPASSED: we call adjudicator.adjudicate(input) DIRECTLY, never consultAdjudicator — the eval
 *     must measure the LIVE model, not replay the adjudications cache.
 *   • The adjudicator is built with LANGFUSE_* stripped from its env, so its OWN injected tracer is a no-op;
 *     the EVAL owns all Langfuse interaction (the dataset run below), avoiding duplicate/standalone traces.
 *
 * LANGFUSE ENRICHMENT (optional, all-or-nothing on LANGFUSE_*): push a dataset RUN over the Slice C dataset
 * `docketclock-adjudications` — a trace per item linked to the run, with `amends_match` / `exact_match`
 * scores — so the accuracy shows up in the Langfuse experiments view. Absent LANGFUSE_* ⇒ skipped cleanly.
 *
 * GATE: `--min-accuracy <x>` exits non-zero when the binary amends-accuracy < x, computed over the FULL
 * item set so errored adjudications count as failures (a run that couldn't complete can't go falsely green).
 * Default: no gate.
 */
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { Langfuse } from "langfuse";
import type { AdjudicationVerdict } from "@yokel/contracts";
import { selectAdjudicator } from "../src/adjudicator/select.js";
import { loadGold, type GoldEntry } from "../src/adjudicator/eval-gold.js";
import { scoreEval, type EvalResult } from "../src/adjudicator/eval-score.js";

const envPath = fileURLToPath(new URL("../../../.env", import.meta.url));
if (existsSync(envPath)) process.loadEnvFile(envPath);

const GOLD_PATH = fileURLToPath(
  new URL("../eval/chain-gold.json", import.meta.url),
);
const DATASET_NAME = (
  process.env.DATASET_NAME || "docketclock-adjudications"
).trim();

function numArg(flag: string): number | undefined {
  const i = process.argv.indexOf(flag);
  if (i === -1 || i + 1 >= process.argv.length) return undefined;
  const n = Number(process.argv[i + 1]);
  return Number.isFinite(n) ? n : undefined;
}
const MIN_ACCURACY = numArg("--min-accuracy");
const LIMIT = numArg("--limit");

const amendsCorrect = (gold: string, pred: string): boolean =>
  (gold === "affirm") === (pred === "affirm");

async function main(): Promise<void> {
  const gold = loadGold(GOLD_PATH);
  const entries = LIMIT && LIMIT > 0 ? gold.slice(0, LIMIT) : gold;
  console.log(
    `loaded ${gold.length} gold item(s)${LIMIT ? `, using ${entries.length}` : ""}`,
  );

  // Build the adjudicator WITHOUT a Langfuse tracer (strip LANGFUSE_* from its env): the eval owns Langfuse.
  const adjudicator = selectAdjudicator({
    ...process.env,
    LANGFUSE_HOST: "",
    LANGFUSE_PUBLIC_KEY: "",
    LANGFUSE_SECRET_KEY: "",
  });
  console.log(`adjudicator.id = ${adjudicator.id}`);
  if (adjudicator.id.startsWith("null:")) {
    throw new Error(
      "selectAdjudicator() returned the null adjudicator — set ADJUDICATOR=gemini and a real GEMINI_API_KEY",
    );
  }

  // Run the live model over each item (cache-bypassed). A thrown call is logged + counted, not fabricated.
  const scored: EvalResult[] = [];
  const predictions: Array<{ entry: GoldEntry; verdict: AdjudicationVerdict }> =
    [];
  let errors = 0;
  for (let i = 0; i < entries.length; i++) {
    const entry = entries[i]!;
    try {
      const verdict = await adjudicator.adjudicate(entry.input);
      scored.push({
        contentHash: entry.content_hash,
        kind: entry.input.kind,
        gold: entry.gold,
        predicted: verdict.classification,
      });
      predictions.push({ entry, verdict });
    } catch (err) {
      errors++;
      console.error(
        `  ! item ${i + 1}/${entries.length} (${entry.content_hash.slice(0, 10)}) adjudicate failed: ${
          err instanceof Error ? err.message : String(err)
        }`,
      );
    }
    if ((i + 1) % 10 === 0) console.log(`  …${i + 1}/${entries.length}`);
  }

  const summary = scoreEval(scored);
  const pct = (x: number): string => `${(x * 100).toFixed(1)}%`;
  const c = summary.amendsConfusion;
  console.log(`\n=== eval: chain adjudicator vs gold ===`);
  console.log(
    `scored ${summary.n}/${entries.length}${errors ? `  (${errors} errored)` : ""}`,
  );
  console.log(`\nPRIMARY — amends? (affirm vs not):`);
  console.log(`  accuracy   ${pct(summary.amendsAccuracy)}`);
  console.log(
    `  precision  ${pct(summary.precision)}   recall ${pct(summary.recall)}   F1 ${summary.f1.toFixed(3)}`,
  );
  console.log(
    `  confusion  TP ${c.tp}  FP ${c.fp}  FN ${c.fn}  TN ${c.tn}   (FP = fabricated link, the worst error)`,
  );
  console.log(`\nSECONDARY — exact 3-way: ${pct(summary.exactAccuracy)}`);
  console.log(`  gold\\pred      affirm  reject  uncertain`);
  for (const g of Object.keys(summary.confusion)) {
    const row = summary.confusion[g]!;
    console.log(
      `  ${g.padEnd(12)} ${String(row["affirm"] ?? 0).padStart(6)}  ${String(row["reject"] ?? 0).padStart(6)}  ${String(row["uncertain"] ?? 0).padStart(9)}`,
    );
  }

  await pushLangfuseRun(adjudicator.id, predictions);

  if (MIN_ACCURACY !== undefined) {
    // Gate over the FULL set: an errored adjudication counts as a FAILURE, not a silent drop — so a CI run
    // that couldn't complete (provider down, key revoked, etc.) can't go falsely green on the survivors.
    // Equals the printed amendsAccuracy when errors === 0; otherwise it's diluted by the errored items, so
    // a transient blip still passes on a healthy corpus but a broadly-broken run correctly fails.
    const gateAccuracy =
      entries.length === 0 ? 0 : (c.tp + c.tn) / entries.length;
    const detail =
      errors > 0
        ? `${pct(gateAccuracy)} over ${entries.length} (incl. ${errors} errored as failures)`
        : pct(gateAccuracy);
    if (gateAccuracy < MIN_ACCURACY) {
      console.error(
        `\nGATE FAILED: amends accuracy ${detail} < threshold ${pct(MIN_ACCURACY)}`,
      );
      process.exit(1);
    }
    console.log(
      `\nGATE PASSED: amends accuracy ${detail} ≥ ${pct(MIN_ACCURACY)}`,
    );
  }
}

/** Optional Langfuse dataset-run enrichment — all-or-nothing on LANGFUSE_*; never affects the gate/exit. */
async function pushLangfuseRun(
  adjudicatorId: string,
  predictions: Array<{ entry: GoldEntry; verdict: AdjudicationVerdict }>,
): Promise<void> {
  const host = (process.env.LANGFUSE_HOST || "").trim();
  const publicKey = (process.env.LANGFUSE_PUBLIC_KEY || "").trim();
  const secretKey = (process.env.LANGFUSE_SECRET_KEY || "").trim();
  if (!host || !publicKey || !secretKey) {
    console.log("\nLangfuse push skipped (LANGFUSE_* not all set).");
    return;
  }
  // run id: prefer a CI commit sha, else a wall-clock stamp (read from env so this stays deterministic-ish).
  const stamp =
    (process.env.GITHUB_SHA || "").slice(0, 7) || new Date().toISOString();
  const runName = `${adjudicatorId}@${stamp}`;
  try {
    const langfuse = new Langfuse({ publicKey, secretKey, baseUrl: host });
    const dataset = await langfuse.getDataset(DATASET_NAME);
    const itemByHash = new Map(dataset.items.map((it) => [it.id, it]));
    let linked = 0;
    for (const { entry, verdict } of predictions) {
      const aCorrect = amendsCorrect(entry.gold, verdict.classification);
      const eCorrect = verdict.classification === entry.gold;
      const trace = langfuse.trace({
        name: "eval-chain",
        input: entry.input,
        output: verdict,
        tags: ["docketclock", "eval", "chain"],
        metadata: {
          content_hash: entry.content_hash,
          gold: entry.gold,
          predicted: verdict.classification,
          amends_correct: aCorrect,
          exact_correct: eCorrect,
          run: runName,
        },
      });
      const item = itemByHash.get(entry.content_hash);
      if (item) {
        await item.link(trace, runName, { metadata: { gold: entry.gold } });
        linked++;
      }
      trace.score({
        name: "amends_match",
        value: aCorrect ? 1 : 0,
        comment: `gold=${entry.gold} pred=${verdict.classification}`,
      });
      trace.score({ name: "exact_match", value: eCorrect ? 1 : 0 });
    }
    await langfuse.flushAsync();
    await langfuse.shutdownAsync();
    console.log(
      `\nLangfuse run "${runName}": linked ${linked}/${predictions.length} item(s) to dataset "${DATASET_NAME}".`,
    );
  } catch (err) {
    // best-effort: the enrichment must never fail the eval/gate.
    console.error(
      `\nLangfuse push failed (non-fatal): ${err instanceof Error ? err.message : String(err)}`,
    );
  }
}

main().catch((err) => {
  console.error("eval failed:", err);
  process.exit(1);
});
