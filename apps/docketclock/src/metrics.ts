/**
 * metrics.ts — the Prometheus metrics registry + typed recorders (Observability Slice B, PR-B1).
 *
 * ONE `prom-client` Registry per process (default Node process/GC/heap metrics + the app series below).
 * Pull-based: the API process exposes it on Fastify `/metrics` (src/api/server.ts); the poller process —
 * which runs no HTTP server — exposes it on a tiny standalone listener (src/metrics-server.ts). The two are
 * SEPARATE processes with SEPARATE registries, scraped as separate targets: HTTP + db_up live on the API
 * series, poll/chain/LLM live on the poller series. Prometheus distinguishes them by the target's job/pod
 * labels.
 *
 * All recorders are FIRE-AND-FORGET and cheap in-memory ops. LLM token/latency are fed via the injected
 * `MetricsTracer` (src/adjudicator/metrics-tracer.ts) so they are emitted whether or not Langfuse is
 * configured — closing the Slice C gap where usage/latency reached ONLY the Langfuse tracer (dropped to a
 * no-op when LANGFUSE_* is unset).
 *
 * Recorders take the poll/chain SUMMARY objects the cycle already computes; the type-only imports are erased
 * at build (no runtime coupling to the poll/reconcile modules).
 */
import {
  Registry,
  collectDefaultMetrics,
  Counter,
  Gauge,
  Histogram,
} from "prom-client";
import type { FrPollSummary } from "./poll/fr-poll.js";
import type { PollSummary } from "./poll/poll.js";
import type { ChainReconcileOnceResult } from "./reconcile/persist.js";

/** The single process-wide registry. `/metrics` renders THIS. */
export const registry = new Registry();
collectDefaultMetrics({ register: registry });

export const metricsContentType = registry.contentType;
/** Render the current registry as the Prometheus text exposition format. */
export function renderMetrics(): Promise<string> {
  return registry.metrics();
}

// ── HTTP (API process) ─────────────────────────────────────────────────────────────────────────────
const httpRequests = new Counter({
  name: "docketclock_http_requests_total",
  help: "HTTP requests handled, by route/method/status.",
  labelNames: ["method", "route", "status"],
  registers: [registry],
});
const httpDuration = new Histogram({
  name: "docketclock_http_request_duration_seconds",
  help: "HTTP request duration in seconds, by route/method/status.",
  labelNames: ["method", "route", "status"],
  buckets: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5],
  registers: [registry],
});
export function observeHttp(o: {
  method: string;
  route: string;
  status: number;
  seconds: number;
}): void {
  const labels = { method: o.method, route: o.route, status: String(o.status) };
  httpRequests.inc(labels);
  httpDuration.observe(labels, o.seconds);
}

const dbUp = new Gauge({
  name: "docketclock_db_up",
  help: "1 if the last DB ping (/healthz, /readyz) succeeded, else 0.",
  registers: [registry],
});
export function setDbUp(up: boolean): void {
  dbUp.set(up ? 1 : 0);
}

// ── Poller ─────────────────────────────────────────────────────────────────────────────────────────
const pollItems = new Counter({
  name: "docketclock_poll_items_total",
  help: "Items processed by the poll passes, by source and outcome.",
  labelNames: ["source", "outcome"],
  registers: [registry],
});
const pollPages = new Counter({
  name: "docketclock_poll_pages_fetched_total",
  help: "List pages fetched by the poll passes, by source.",
  labelNames: ["source"],
  registers: [registry],
});
const pollTruncated = new Gauge({
  name: "docketclock_poll_truncated",
  help: "1 if the last cycle for <source> stopped truncated (coverage incomplete), else 0.",
  labelNames: ["source"],
  registers: [registry],
});
const pollPassFailures = new Counter({
  name: "docketclock_poll_pass_failures_total",
  help: "Cumulative poll passes that threw and were isolated (since process start), by pass.",
  labelNames: ["pass"],
  registers: [registry],
});
const pollCycleDuration = new Histogram({
  name: "docketclock_poll_cycle_duration_seconds",
  help: "Wall-clock duration of a full settled poll cycle (fr + regs + chain + verify).",
  buckets: [0.5, 1, 2, 5, 10, 30, 60, 120, 300],
  registers: [registry],
});
const pollerHeartbeat = new Gauge({
  name: "docketclock_poller_last_heartbeat_seconds",
  help: "Unix time (seconds) the poller last settled a cycle. Liveness/stall signal.",
  registers: [registry],
});

export function recordFrPoll(s: FrPollSummary): void {
  pollItems.inc({ source: "fr", outcome: "listed" }, s.listed);
  pollItems.inc({ source: "fr", outcome: "fetched" }, s.fetched);
  pollItems.inc({ source: "fr", outcome: "ingested" }, s.ingested);
  pollItems.inc({ source: "fr", outcome: "skipped" }, s.skipped);
  pollItems.inc({ source: "fr", outcome: "dead_lettered" }, s.deadLettered);
  pollItems.inc({ source: "fr", outcome: "recovered" }, s.recovered);
  pollPages.inc({ source: "fr" }, s.pagesFetched);
  pollTruncated.set({ source: "fr" }, s.truncated ? 1 : 0);
}
export function recordRegsPoll(s: PollSummary): void {
  pollItems.inc({ source: "regs", outcome: "listed" }, s.listed);
  pollItems.inc({ source: "regs", outcome: "ingested" }, s.ingested);
  pollItems.inc({ source: "regs", outcome: "deduped" }, s.deduped);
  pollItems.inc({ source: "regs", outcome: "repolled" }, s.repolled);
  pollItems.inc(
    { source: "regs", outcome: "repoll_deferred" },
    s.repollDeferred,
  );
  pollItems.inc({ source: "regs", outcome: "transitions" }, s.transitions);
  pollItems.inc({ source: "regs", outcome: "dead_lettered" }, s.deadLettered);
  pollItems.inc({ source: "regs", outcome: "recovered" }, s.recovered);
  pollPages.inc({ source: "regs" }, s.pagesFetched);
  pollTruncated.set({ source: "regs" }, s.truncated ? 1 : 0);
}
export function recordPollPassFailure(
  pass: "fr" | "regs" | "chain" | "verify",
): void {
  pollPassFailures.inc({ pass });
}
export function observePollCycle(seconds: number): void {
  pollCycleDuration.observe(seconds);
}
export function setHeartbeat(unixSeconds: number): void {
  pollerHeartbeat.set(unixSeconds);
}

// ── Chain adjudication cycle (fed by chainReconcileOnce's return) ─────────────────────────────────────
const chainCandidates = new Gauge({
  name: "docketclock_chain_candidates",
  help: "Windows-with-an-FR-observation read as candidates in the last chain cycle.",
  registers: [registry],
});
const chainAmendments = new Gauge({
  name: "docketclock_chain_amendments",
  help: "Candidates carrying an amendment signal in the last chain cycle.",
  registers: [registry],
});
const chainConflictsLive = new Gauge({
  name: "docketclock_chain_conflicts_live",
  help: "Live cross_window conflict records after the last chain cycle.",
  registers: [registry],
});
const chainConfidentLinks = new Counter({
  name: "docketclock_chain_confident_links_total",
  help: "Confident (A,B) links the deterministic engine emitted (rules 1-5).",
  registers: [registry],
});
const chainAmbiguous = new Counter({
  name: "docketclock_chain_ambiguous_total",
  help: "Ambiguous pairs surfaced to the adjudicator (the escalation set).",
  registers: [registry],
});
const chainCacheHits = new Counter({
  name: "docketclock_chain_cache_hits_total",
  help: "Ambiguous pairs whose verdict was replayed from the adjudications cache (no LLM call).",
  registers: [registry],
});
const chainLlmCalls = new Counter({
  name: "docketclock_chain_llm_calls_total",
  help: "Fresh LLM calls made by the chain cycle (cache misses within budget). A throw still counts.",
  registers: [registry],
});
const chainLlmLinked = new Counter({
  name: "docketclock_chain_llm_linked_total",
  help: "Affirmed pairs the adjudicator promoted to a cross_window link.",
  registers: [registry],
});
const chainDeferred = new Counter({
  name: "docketclock_chain_deferred_total",
  help: "Uncached pairs deferred because the per-cycle fresh-call budget was exhausted.",
  registers: [registry],
});
const chainRetired = new Counter({
  name: "docketclock_chain_retired_total",
  help: "Open cross_window conflict records retired (no longer a live pair) by the chain cycle.",
  registers: [registry],
});
export function recordChainCycle(s: ChainReconcileOnceResult): void {
  chainCandidates.set(s.candidates);
  chainAmendments.set(s.amendments);
  chainConflictsLive.set(s.conflictsLive);
  chainConfidentLinks.inc(s.linked);
  chainAmbiguous.inc(s.ambiguous);
  chainCacheHits.inc(s.cacheHits);
  chainLlmCalls.inc(s.llmCalls);
  chainLlmLinked.inc(s.llmLinked);
  chainDeferred.inc(s.deferred);
  chainRetired.inc(s.retired);
}

// ── Post-close verification (stage 4, slice V) ────────────────────────────────────────────────────────
const accuracyChecks = new Counter({
  name: "docketclock_accuracy_checks_total",
  help: "Per-cycle verification evaluations of watched windows, by result (snapshotted | in_horizon | awaiting_check | verdict | lapsed).",
  labelNames: ["result"],
  registers: [registry],
});
const accuracyRecords = new Counter({
  name: "docketclock_accuracy_records_total",
  help: "FINAL AccuracyRecords written, by verdict (was_correct true|false). Lapsed abstentions count on docketclock_accuracy_unverified_total instead.",
  labelNames: ["was_correct"],
  registers: [registry],
});
const accuracyUnverified = new Counter({
  name: "docketclock_accuracy_unverified_total",
  help: "unverified_lapsed records written — windows whose 14d verification cap passed with ZERO confirmed post-close checks. The re-poll starvation signal.",
  registers: [registry],
});
const accuracyHighRatio = new Gauge({
  name: "docketclock_accuracy_high_correct_ratio_90d",
  help: "Share of HIGH-at-close windows judged was_correct=true, trailing 90d by close date, EXCLUDING unverified_lapsed. NaN when there is no sample (never a fake 0 or 1).",
  registers: [registry],
});
export function recordVerifyCycle(s: {
  snapshotted: number;
  inHorizon: number;
  awaitingCheck: number;
  verdictsCorrect: number;
  verdictsIncorrect: number;
  lapsed: number;
}): void {
  accuracyChecks.inc({ result: "snapshotted" }, s.snapshotted);
  accuracyChecks.inc({ result: "in_horizon" }, s.inHorizon);
  accuracyChecks.inc({ result: "awaiting_check" }, s.awaitingCheck);
  accuracyChecks.inc(
    { result: "verdict" },
    s.verdictsCorrect + s.verdictsIncorrect,
  );
  accuracyChecks.inc({ result: "lapsed" }, s.lapsed);
  accuracyRecords.inc({ was_correct: "true" }, s.verdictsCorrect);
  accuracyRecords.inc({ was_correct: "false" }, s.verdictsIncorrect);
  accuracyUnverified.inc(s.lapsed);
}
/** Set the headline gauge from the per-cycle SQL rollup. null (no sample) exports NaN — an absent
 *  baseline must never read as 0% (a page) or 100% (fake perfection), and NaN satisfies no threshold. */
export function setAccuracyHighRatio(ratio: number | null): void {
  accuracyHighRatio.set(ratio ?? NaN);
}

// ── LLM per-call (fed by MetricsTracer, independent of Langfuse) ──────────────────────────────────────
const llmTokens = new Counter({
  name: "docketclock_llm_tokens_total",
  help: "LLM tokens consumed, by model and kind (input|output).",
  labelNames: ["model", "kind"],
  registers: [registry],
});
const llmLatency = new Histogram({
  name: "docketclock_llm_call_latency_seconds",
  help: "Latency of a real LLM provider round-trip, by model.",
  labelNames: ["model"],
  buckets: [0.1, 0.25, 0.5, 1, 2, 4, 8, 15, 30],
  registers: [registry],
});
const llmCalls = new Counter({
  name: "docketclock_llm_calls_total",
  help: "Real LLM calls, by model and resulting verdict classification.",
  labelNames: ["model", "verdict"],
  registers: [registry],
});
const llmCacheHits = new Counter({
  name: "docketclock_llm_cache_hits_total",
  help: "Adjudication cache hits observed by the tracer, by question kind (notice|chain).",
  labelNames: ["kind"],
  registers: [registry],
});
export function recordLlmGeneration(o: {
  model: string;
  verdict: string;
  latencyMs: number;
  input?: number;
  output?: number;
}): void {
  llmCalls.inc({ model: o.model, verdict: o.verdict });
  llmLatency.observe({ model: o.model }, o.latencyMs / 1000);
  if (typeof o.input === "number")
    llmTokens.inc({ model: o.model, kind: "input" }, o.input);
  if (typeof o.output === "number")
    llmTokens.inc({ model: o.model, kind: "output" }, o.output);
}
export function recordLlmCacheHit(kind: "notice" | "chain"): void {
  llmCacheHits.inc({ kind });
}
