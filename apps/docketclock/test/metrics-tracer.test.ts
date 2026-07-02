/**
 * metrics-tracer.test.ts — PR-B1 (observability slice B): the LlmTracer that feeds Prometheus. Proves the
 * tracer maps a generation/cache-hit onto the metrics registry, that its lifecycle methods are inert no-ops,
 * and that it NEVER throws into the adjudication path (side-channel invariant). Runs in its own process, so
 * the registry counters start at zero. Repo test style: hand-rolled assert + out[] + process.exit.
 */
import {
  MetricsTracer,
  getMetricsTracer,
} from "../src/adjudicator/metrics-tracer.js";
import { registry } from "../src/metrics.js";
import type {
  LlmGenerationRecord,
  LlmCacheHitRecord,
} from "../src/adjudicator/tracer.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

interface SampleValue {
  value: number;
  labels: Record<string, string | number>;
  metricName?: string;
}
type Snap = Array<{ name: string; values: SampleValue[] }>;
/** prom-client v15 metric.get() is async — snapshot the whole registry, then query synchronously. */
async function snap(): Promise<Snap> {
  return (await registry.getMetricsAsJSON()) as unknown as Snap;
}
function val(s: Snap, name: string, labels: Record<string, string>): number {
  const metric = s.find((m) => m.name === name);
  if (!metric) return 0;
  const keys = Object.keys(labels);
  const hit = metric.values.find(
    (v) =>
      v.metricName === undefined &&
      keys.every((k) => String(v.labels[k]) === labels[k]),
  );
  return hit ? hit.value : 0;
}

const gen: LlmGenerationRecord = {
  model: "gemini-2.5-flash",
  input: { kind: "chain" },
  output: { classification: "affirm", rationale: "x" },
  verdict: { classification: "affirm", rationale: "x" },
  usage: { input: 100, output: 10, total: 110 },
  latencyMs: 500,
  contentHash: "h",
  adjudicatorId: "gemini:gemini-2.5-flash@rb1",
  rulebookVersion: "rb1",
  kind: "chain",
};
const hit: LlmCacheHitRecord = {
  contentHash: "h",
  adjudicatorId: "gemini:gemini-2.5-flash@rb1",
  rulebookVersion: "rb1",
  kind: "chain",
  classification: "reject",
};

// 1. getMetricsTracer returns a MetricsTracer singleton.
{
  const a = getMetricsTracer();
  const b = getMetricsTracer();
  assert(
    "getMetricsTracer returns a stable MetricsTracer singleton",
    a instanceof MetricsTracer && a === b,
  );
}

// 2. recordGeneration maps onto the LLM metrics (calls/tokens/latency).
{
  const t = new MetricsTracer();
  t.recordGeneration(gen);
  const s = await snap();
  assert(
    "recordGeneration → llm_calls_total{model,verdict=affirm} = 1",
    val(s, "docketclock_llm_calls_total", {
      model: "gemini-2.5-flash",
      verdict: "affirm",
    }) === 1,
  );
  assert(
    "recordGeneration → llm_tokens_total{input} = 100 and {output} = 10",
    val(s, "docketclock_llm_tokens_total", {
      model: "gemini-2.5-flash",
      kind: "input",
    }) === 100 &&
      val(s, "docketclock_llm_tokens_total", {
        model: "gemini-2.5-flash",
        kind: "output",
      }) === 10,
  );
}

// 3. recordCacheHit maps onto llm_cache_hits_total{kind}.
{
  const t = new MetricsTracer();
  t.recordCacheHit(hit);
  assert(
    "recordCacheHit → llm_cache_hits_total{chain} = 1",
    val(await snap(), "docketclock_llm_cache_hits_total", { kind: "chain" }) ===
      1,
  );
}

// 4. missing usage is tolerated (no NaN token increments, no throw).
{
  const t = new MetricsTracer();
  let threw = false;
  try {
    t.recordGeneration({ ...gen, usage: undefined });
  } catch {
    threw = true;
  }
  assert("recordGeneration with no usage does not throw", !threw);
  assert(
    "no-usage generation still counts the call (now 2)",
    val(await snap(), "docketclock_llm_calls_total", {
      model: "gemini-2.5-flash",
      verdict: "affirm",
    }) === 2,
  );
}

// 5. lifecycle methods are inert no-ops and nothing throws.
{
  const t = new MetricsTracer();
  let threw = false;
  try {
    t.startCycle({ kind: "chain" });
    t.setActivePair({ fromOcdId: "a", toOcdId: "b" });
    t.setActivePair(null);
    await t.flush();
    await t.shutdown();
  } catch {
    threw = true;
  }
  assert("startCycle/setActivePair/flush/shutdown are inert no-ops", !threw);
}

console.log("\n=== metrics-tracer results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
