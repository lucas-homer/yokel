/**
 * eval-models.ts — run the chain gold corpus against SEVERAL models through Cloudflare AI Gateway and print
 * one comparison table. `pnpm --filter @yokel/docketclock eval:models --models a,b,c [--concurrency 4]
 * [--limit n] [--out results.json]`. Models may also come from EVAL_MODELS (comma-separated).
 *
 * Needs CLOUDFLARE_ACCOUNT_ID + CLOUDFLARE_AI_TOKEN (see select.ts cloudflareAdjudicator). Cache-bypassed
 * like eval-chain.ts: every item is a live call, so each model costs ~50 small requests.
 *
 * Scoring reuses scoreEval (binary amends? accuracy is the headline; FP = a fabricated link, the worst
 * error). Errored items count as FAILURES in "acc (all)" so a model that can't answer isn't flattered.
 * No gate: this is for choosing a model, not for CI pass/fail. Cost: read it from the gateway's logs.
 */
import { appendFileSync, existsSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { cloudflareAdjudicator } from "../src/adjudicator/select.js";
import { loadGold, type GoldEntry } from "../src/adjudicator/eval-gold.js";
import { scoreEval, type EvalResult } from "../src/adjudicator/eval-score.js";
import {
  NOOP_TRACER,
  type LlmGenerationRecord,
  type LlmTracer,
} from "../src/adjudicator/tracer.js";

const envPath = fileURLToPath(new URL("../../../.env", import.meta.url));
if (existsSync(envPath)) process.loadEnvFile(envPath);

const GOLD_PATH = fileURLToPath(
  new URL("../eval/chain-gold.json", import.meta.url),
);

function arg(flag: string): string | undefined {
  const i = process.argv.indexOf(flag);
  return i === -1 || i + 1 >= process.argv.length
    ? undefined
    : process.argv[i + 1];
}
const LIMIT = Number(arg("--limit")) || undefined;
const CONCURRENCY = Math.max(1, Number(arg("--concurrency")) || 4);
const OUT = arg("--out");
const MODELS = (arg("--models") || process.env.EVAL_MODELS || "")
  .split(",")
  .map((m) => m.trim())
  .filter(Boolean);

interface ModelRow {
  model: string;
  n: number;
  scored: number;
  errors: number;
  accAll: number;
  accScored: number;
  exact: number;
  fp: number;
  fn: number;
  p50ms: number;
  p95ms: number;
  inTokens: number;
  outTokens: number;
  firstError?: string;
  misses: Array<{ hash: string; gold: string; predicted: string }>;
}

function pctl(xs: number[], p: number): number {
  if (xs.length === 0) return 0;
  const s = [...xs].sort((a, b) => a - b);
  return s[Math.min(s.length - 1, Math.floor((p / 100) * s.length))]!;
}

async function runModel(
  model: string,
  entries: GoldEntry[],
): Promise<ModelRow> {
  const gens: LlmGenerationRecord[] = [];
  // NOOP_TRACER is a class instance, so delegate explicitly rather than spreading (spread drops methods).
  const tracer: LlmTracer = {
    startCycle: (c) => NOOP_TRACER.startCycle(c),
    setActivePair: (p) => NOOP_TRACER.setActivePair(p),
    recordGeneration: (g) => void gens.push(g),
    recordCacheHit: (h) => NOOP_TRACER.recordCacheHit(h),
    flush: () => NOOP_TRACER.flush(),
    shutdown: () => NOOP_TRACER.shutdown(),
  };
  const env = {
    ...process.env,
    LANGFUSE_HOST: "",
    LANGFUSE_PUBLIC_KEY: "",
    LANGFUSE_SECRET_KEY: "",
  };
  const adjudicator = cloudflareAdjudicator(env, { model, tracer });
  if (!adjudicator)
    throw new Error("set CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_AI_TOKEN");

  const scored: EvalResult[] = [];
  let errors = 0;
  let firstError: string | undefined;
  let next = 0;
  const worker = async () => {
    for (;;) {
      const i = next++;
      if (i >= entries.length) return;
      const e = entries[i]!;
      try {
        const v = await adjudicator.adjudicate(e.input);
        scored.push({
          contentHash: e.content_hash,
          kind: e.input.kind,
          gold: e.gold,
          predicted: v.classification,
        });
      } catch (err) {
        errors++;
        firstError ??= (err instanceof Error ? err.message : String(err)).slice(
          0,
          300,
        );
      }
    }
  };
  await Promise.all(Array.from({ length: CONCURRENCY }, worker));

  const s = scoreEval(scored);
  const lat = gens.map((g) => g.latencyMs);
  const amends = (c: string) => c === "affirm";
  return {
    model,
    n: entries.length,
    scored: s.n,
    errors,
    accAll: entries.length
      ? (s.amendsConfusion.tp + s.amendsConfusion.tn) / entries.length
      : 0,
    accScored: s.amendsAccuracy,
    exact: s.exactAccuracy,
    fp: s.amendsConfusion.fp,
    fn: s.amendsConfusion.fn,
    p50ms: pctl(lat, 50),
    p95ms: pctl(lat, 95),
    inTokens: gens.reduce((a, g) => a + (g.usage?.input ?? 0), 0),
    outTokens: gens.reduce((a, g) => a + (g.usage?.output ?? 0), 0),
    ...(firstError ? { firstError } : {}),
    misses: scored
      .filter((r) => amends(r.gold) !== amends(r.predicted))
      .map((r) => ({
        hash: r.contentHash.slice(0, 10),
        gold: r.gold,
        predicted: r.predicted,
      })),
  };
}

function table(rows: ModelRow[]): string {
  const pct = (x: number) => `${(x * 100).toFixed(1)}%`;
  const lines = [
    "| model | amends acc (all) | errors | FP | FN | exact 3-way | p50 ms | p95 ms | tokens in/out |",
    "|---|---|---|---|---|---|---|---|---|",
    ...rows.map(
      (r) =>
        `| ${r.model} | ${pct(r.accAll)} | ${r.errors}/${r.n} | ${r.fp} | ${r.fn} | ${pct(r.exact)} | ${r.p50ms} | ${r.p95ms} | ${r.inTokens}/${r.outTokens} |`,
    ),
  ];
  const errs = rows
    .filter((r) => r.firstError)
    .map((r) => `- **${r.model}** first error: \`${r.firstError}\``);
  return [...lines, ...(errs.length ? ["", ...errs] : [])].join("\n");
}

async function main(): Promise<void> {
  if (MODELS.length === 0)
    throw new Error("pass --models a,b,c or set EVAL_MODELS");
  const gold = loadGold(GOLD_PATH);
  const entries = LIMIT && LIMIT > 0 ? gold.slice(0, LIMIT) : gold;
  console.log(
    `${entries.length} gold items × ${MODELS.length} models, concurrency ${CONCURRENCY}`,
  );

  const rows: ModelRow[] = [];
  for (const model of MODELS) {
    const t0 = Date.now();
    const row = await runModel(model, entries);
    rows.push(row);
    console.log(
      `  ${model}: acc ${(row.accAll * 100).toFixed(1)}%  errors ${row.errors}  FP ${row.fp}  (${Math.round((Date.now() - t0) / 1000)}s)`,
    );
  }
  rows.sort((a, b) => b.accAll - a.accAll || a.fp - b.fp || a.p50ms - b.p50ms);
  const md = table(rows);
  console.log(`\n${md}\n`);
  for (const r of rows) {
    if (r.misses.length)
      console.log(
        `misses ${r.model}: ${r.misses.map((m) => `${m.hash}(${m.gold}→${m.predicted})`).join(" ")}`,
      );
  }
  if (process.env.GITHUB_STEP_SUMMARY)
    appendFileSync(
      process.env.GITHUB_STEP_SUMMARY,
      `## Model comparison\n\n${md}\n`,
    );
  if (OUT)
    writeFileSync(
      OUT,
      JSON.stringify(
        { at: new Date().toISOString(), items: entries.length, rows },
        null,
        2,
      ),
    );
}

main().catch((err) => {
  console.error("eval:models failed:", err);
  process.exit(1);
});
