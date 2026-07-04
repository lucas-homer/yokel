/**
 * metrics.test.ts — PR-B1 (observability slice B): the Prometheus registry + recorders, proven with NO
 * network. Pins that each recorder moves the right series/labels and that the registry renders the prom text
 * exposition format. Repo test style: hand-rolled assert, out[] accumulator, failures counter, process.exit.
 */
import {
  registry,
  renderMetrics,
  metricsContentType,
  observeHttp,
  setDbUp,
  recordFrPoll,
  recordRegsPoll,
  recordChainCycle,
  recordPollPassFailure,
  observePollCycle,
  setHeartbeat,
  recordLlmGeneration,
  recordLlmCacheHit,
} from "../src/metrics.js";

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
/** Read one plain (non-histogram-aggregate) sample value by name + exact label match (0 if absent). */
function val(
  s: Snap,
  name: string,
  labels: Record<string, string> = {},
): number {
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
/** Read a histogram aggregate line (e.g. <name>_count) by label match. */
function agg(
  s: Snap,
  name: string,
  suffix: "count" | "sum",
  labels: Record<string, string> = {},
): number {
  const metric = s.find((m) => m.name === name);
  if (!metric) return NaN;
  const keys = Object.keys(labels);
  const hit = metric.values.find(
    (v) =>
      v.metricName === `${name}_${suffix}` &&
      keys.every((k) => String(v.labels[k]) === labels[k]),
  );
  return hit ? hit.value : NaN;
}

// 1. HTTP counter + histogram.
{
  observeHttp({
    method: "GET",
    route: "/v1/windows",
    status: 200,
    seconds: 0.02,
  });
  observeHttp({
    method: "GET",
    route: "/v1/windows",
    status: 200,
    seconds: 0.05,
  });
  const s = await snap();
  assert(
    "observeHttp increments http_requests_total{route,method,status}",
    val(s, "docketclock_http_requests_total", {
      method: "GET",
      route: "/v1/windows",
      status: "200",
    }) === 2,
  );
  assert(
    "http_request_duration_seconds observes 2 samples for the route",
    agg(s, "docketclock_http_request_duration_seconds", "count", {
      route: "/v1/windows",
    }) === 2,
  );
}

// 2. db_up gauge flips.
{
  setDbUp(true);
  assert(
    "setDbUp(true) → db_up 1",
    val(await snap(), "docketclock_db_up") === 1,
  );
  setDbUp(false);
  assert(
    "setDbUp(false) → db_up 0",
    val(await snap(), "docketclock_db_up") === 0,
  );
}

// 3. FR + Regs poll summaries map to poll_items_total{source,outcome}.
{
  recordFrPoll({
    listed: 5,
    keywordListed: 1,
    fetched: 3,
    ingested: 2,
    skipped: 1,
    pagesFetched: 2,
    truncated: true,
    deadLettered: 0,
    deadLetterRetried: 0,
    recovered: 4,
  });
  recordRegsPoll({
    listed: 7,
    ingested: 3,
    deduped: 2,
    repolled: 1,
    repollDeferred: 2,
    transitions: 1,
    cursorAdvancedTo: null,
    pagesFetched: 1,
    truncated: false,
    deadLettered: 1,
    deadLetterRetried: 0,
    recovered: 0,
  });
  const s = await snap();
  assert(
    "recordFrPoll: poll_items_total{fr,listed} = 5",
    val(s, "docketclock_poll_items_total", {
      source: "fr",
      outcome: "listed",
    }) === 5,
  );
  assert(
    "recordFrPoll: poll_items_total{fr,recovered} = 4",
    val(s, "docketclock_poll_items_total", {
      source: "fr",
      outcome: "recovered",
    }) === 4,
  );
  assert(
    "recordFrPoll: poll_truncated{fr} = 1",
    val(s, "docketclock_poll_truncated", { source: "fr" }) === 1,
  );
  assert(
    "recordRegsPoll: poll_items_total{regs,listed} = 7",
    val(s, "docketclock_poll_items_total", {
      source: "regs",
      outcome: "listed",
    }) === 7,
  );
  assert(
    "recordRegsPoll: poll_items_total{regs,dead_lettered} = 1",
    val(s, "docketclock_poll_items_total", {
      source: "regs",
      outcome: "dead_lettered",
    }) === 1,
  );
  assert(
    "recordRegsPoll: poll_items_total{regs,repoll_deferred} = 2 (budget-deferred re-polls surfaced)",
    val(s, "docketclock_poll_items_total", {
      source: "regs",
      outcome: "repoll_deferred",
    }) === 2,
  );
}

// 4. chain cycle: gauges snapshot, counters accumulate.
{
  recordChainCycle({
    candidates: 40,
    amendments: 6,
    linked: 3,
    ambiguous: 5,
    cacheHits: 2,
    llmCalls: 3,
    llmLinked: 2,
    deferred: 1,
    conflictsLive: 9,
    retired: 0,
  });
  const s1 = await snap();
  assert(
    "recordChainCycle: candidates gauge = 40",
    val(s1, "docketclock_chain_candidates") === 40,
  );
  assert(
    "recordChainCycle: llm_calls_total counter = 3",
    val(s1, "docketclock_chain_llm_calls_total") === 3,
  );
  assert(
    "recordChainCycle: llm_linked_total counter = 2",
    val(s1, "docketclock_chain_llm_linked_total") === 2,
  );
  // a second cycle accumulates the counter but overwrites the gauge
  recordChainCycle({
    candidates: 41,
    amendments: 0,
    linked: 0,
    ambiguous: 0,
    cacheHits: 0,
    llmCalls: 4,
    llmLinked: 0,
    deferred: 0,
    conflictsLive: 9,
    retired: 0,
  });
  const s2 = await snap();
  assert(
    "chain gauge overwrites (candidates = 41), counter accumulates (llm_calls = 7)",
    val(s2, "docketclock_chain_candidates") === 41 &&
      val(s2, "docketclock_chain_llm_calls_total") === 7,
  );
}

// 5. pass failures + cycle histogram + heartbeat.
{
  recordPollPassFailure("fr");
  recordPollPassFailure("fr");
  recordPollPassFailure("chain");
  observePollCycle(1.5);
  setHeartbeat(1_700_000_000);
  const s = await snap();
  assert(
    "recordPollPassFailure: fr=2, chain=1",
    val(s, "docketclock_poll_pass_failures_total", { pass: "fr" }) === 2 &&
      val(s, "docketclock_poll_pass_failures_total", { pass: "chain" }) === 1,
  );
  assert(
    "observePollCycle records a sample",
    agg(s, "docketclock_poll_cycle_duration_seconds", "count") === 1,
  );
  assert(
    "setHeartbeat sets the gauge",
    val(s, "docketclock_poller_last_heartbeat_seconds") === 1_700_000_000,
  );
}

// 6. LLM recorders (the MetricsTracer feeds these).
{
  recordLlmGeneration({
    model: "gemini-2.5-flash",
    verdict: "affirm",
    latencyMs: 800,
    input: 120,
    output: 8,
  });
  recordLlmCacheHit("chain");
  const s = await snap();
  assert(
    "recordLlmGeneration: calls_total{model,verdict} = 1",
    val(s, "docketclock_llm_calls_total", {
      model: "gemini-2.5-flash",
      verdict: "affirm",
    }) === 1,
  );
  assert(
    "recordLlmGeneration: tokens_total{input} = 120",
    val(s, "docketclock_llm_tokens_total", {
      model: "gemini-2.5-flash",
      kind: "input",
    }) === 120,
  );
  assert(
    "recordLlmCacheHit: cache_hits_total{chain} = 1",
    val(s, "docketclock_llm_cache_hits_total", { kind: "chain" }) === 1,
  );
}

// 7. renderMetrics produces prom text with content type + default Node metrics.
{
  const text = await renderMetrics();
  assert(
    "metricsContentType is the prom text format",
    metricsContentType.includes("text/plain"),
    metricsContentType,
  );
  assert(
    "renderMetrics includes an app series and default Node metrics",
    text.includes("docketclock_http_requests_total") &&
      /process_cpu|nodejs_/.test(text),
  );
}

console.log("\n=== metrics results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
