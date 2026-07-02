/**
 * adjudicator/metrics-tracer.ts — an `LlmTracer` impl that feeds Prometheus (Observability Slice B, PR-B1).
 *
 * Slice C surfaced token usage + latency on every real LLM call, but ONLY to the Langfuse tracer — dropped
 * to a no-op whenever LANGFUSE_* is unset. This tracer emits the SAME signal to the process metrics registry
 * (src/metrics.ts), so `docketclock_llm_*` series populate regardless of Langfuse. It is composed WITH the
 * Langfuse-or-noop tracer in select.ts (`composeTracers`), so metrics are an always-on side channel while the
 * Langfuse push stays all-or-nothing.
 *
 * SIDE CHANNEL: like every LlmTracer, the record* methods are fire-and-forget and self-guarded — a metrics
 * failure must never throw into the deterministic adjudication/reconcile path. startCycle/setActivePair/
 * flush/shutdown are no-ops (there is nothing to batch or release; prom-client is synchronous in-memory).
 */
import {
  type LlmTracer,
  type LlmGenerationRecord,
  type LlmCacheHitRecord,
  type CycleContext,
} from "./tracer.js";
import { recordLlmGeneration, recordLlmCacheHit } from "../metrics.js";

export class MetricsTracer implements LlmTracer {
  startCycle(_ctx: CycleContext): void {}
  setActivePair(_pair: { fromOcdId?: string; toOcdId?: string } | null): void {}

  recordGeneration(gen: LlmGenerationRecord): void {
    try {
      recordLlmGeneration({
        model: gen.model,
        verdict: gen.verdict.classification,
        latencyMs: gen.latencyMs,
        input: gen.usage?.input,
        output: gen.usage?.output,
      });
    } catch {
      /* side channel — never throw into the adjudication path. */
    }
  }

  recordCacheHit(hit: LlmCacheHitRecord): void {
    try {
      recordLlmCacheHit(hit.kind);
    } catch {
      /* side channel. */
    }
  }

  async flush(): Promise<void> {}
  async shutdown(): Promise<void> {}
}

/** Process-wide singleton — one MetricsTracer feeding the one registry. */
let singleton: MetricsTracer | null = null;
export function getMetricsTracer(): MetricsTracer {
  return (singleton ??= new MetricsTracer());
}
