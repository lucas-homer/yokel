/**
 * adjudicator/tracer.ts — the provider-NEUTRAL LLM tracing seam (PR-C2, observability slice C). Tracing is
 * a SIDE CHANNEL: it NEVER changes a verdict, NEVER touches the `adjudications` cache, and the Adjudicator
 * port's `adjudicate(): Promise<AdjudicationVerdict>` return type stays FROZEN. An `LlmTracer` is injected at
 * construction (select.ts) so the adjudicator/orchestrator depend only on THIS interface, never on Langfuse.
 *
 * DEFAULT = NoopTracer (a true no-op). When `LANGFUSE_*` env is unset, the no-op is injected, no `langfuse`
 * client is constructed, and existing behavior is byte-for-byte unchanged. The Langfuse-backed impl lives in
 * langfuse-tracer.ts and is selected ONLY when all of LANGFUSE_HOST/PUBLIC_KEY/SECRET_KEY are present.
 *
 * TRACE SHAPE (locked, see plans/observability-llm.md): one trace per chain-adjudicate cycle; each REAL LLM
 * call is a `generation` (model, input, output, token usage, latency); a cache HIT is a cheap `span` tagged
 * cached. The Gemini API key (and LANGFUSE_SECRET_KEY) NEVER enter a trace — only public FR notice text does.
 *
 * NO PII: adjudication inputs are public Federal Register notice text.
 */

/** Token usage surfaced from a provider response (Gemini `usageMetadata`). Any field may be absent. */
export interface LlmTokenUsage {
  /** input/prompt tokens (Gemini promptTokenCount). */
  input?: number;
  /** output/completion tokens (Gemini candidatesTokenCount). */
  output?: number;
  /** total tokens (Gemini totalTokenCount). */
  total?: number;
}

/** One REAL LLM call → a Langfuse `generation`. The adjudicator derives most fields from its input. */
export interface LlmGenerationRecord {
  /** the model id, e.g. "gemini-2.5-flash". */
  model: string;
  /** the adjudication input (public FR notice text) — NEVER the API key. */
  input: unknown;
  /** the raw/parsed model output (the verdict). */
  output: unknown;
  /** the parsed verdict (classification + rationale). */
  verdict: { classification: string; rationale: string };
  /** token usage, when the response carried `usageMetadata`. */
  usage?: LlmTokenUsage;
  /** wall-clock latency of the provider round-trip, ms. */
  latencyMs: number;
  /** sha256 cache key half — cross-references the `adjudications` DB row. */
  contentHash: string;
  /** provenance `${adjudicator.id}@${rulebook_version}` — the other cache-key half. */
  adjudicatorId: string;
  /** the rulebook version the input was framed against. */
  rulebookVersion: string;
  /** which question shape was asked. */
  kind: "notice" | "chain";
  /** the chain pair's source OCD-id, when adjudicating a chain pair. */
  fromOcdId?: string;
  /** the chain pair's target OCD-id, when adjudicating a chain pair. */
  toOcdId?: string;
}

/** A cache HIT → a cheap `cached` span (no model/usage/latency — nothing was called). */
export interface LlmCacheHitRecord {
  contentHash: string;
  adjudicatorId: string;
  rulebookVersion: string;
  kind: "notice" | "chain";
  /** the cached verdict's classification (affirm|reject|uncertain). */
  classification: string;
  fromOcdId?: string;
  toOcdId?: string;
}

/** Per-cycle trace context — what the orchestrator knows when it opens the per-cycle trace. */
export interface CycleContext {
  kind: "chain" | "notice";
  /** ambiguous pairs surfaced this cycle. */
  surfaced?: number;
  /** the per-cycle fresh-call cap. */
  cap?: number;
}

/**
 * LlmTracer — the injected side channel. All record* methods are FIRE-AND-FORGET (void): a tracer must never
 * throw into the adjudication path. Only flush()/shutdown() are async (they drive the SDK's batched send).
 */
export interface LlmTracer {
  /** Open the per-cycle trace. Subsequent generations/cache-hits attach to it until flush(). */
  startCycle(ctx: CycleContext): void;
  /**
   * Set the active chain pair so the NEXT generation recorded by the adjudicator (which does not itself know
   * the OCD-ids) carries from/to. Pass null to clear. A no-op concern for non-chain flows.
   */
  setActivePair(pair: { fromOcdId?: string; toOcdId?: string } | null): void;
  /** Record one REAL LLM call as a generation. */
  recordGeneration(gen: LlmGenerationRecord): void;
  /** Record a cache HIT as a cheap cached span. */
  recordCacheHit(hit: LlmCacheHitRecord): void;
  /** Flush buffered events (called per cycle and on shutdown) and close the current cycle trace. */
  flush(): Promise<void>;
  /** Release SDK resources on process shutdown (best-effort; never throws). */
  shutdown(): Promise<void>;
}

/**
 * NoopTracer — the DEFAULT. Every method is inert; flush()/shutdown() resolve immediately. Injected whenever
 * LANGFUSE_* is unset, so the adjudicator path is byte-for-byte the pre-instrumentation behavior.
 */
export class NoopTracer implements LlmTracer {
  startCycle(_ctx: CycleContext): void {}
  setActivePair(_pair: { fromOcdId?: string; toOcdId?: string } | null): void {}
  recordGeneration(_gen: LlmGenerationRecord): void {}
  recordCacheHit(_hit: LlmCacheHitRecord): void {}
  async flush(): Promise<void> {}
  async shutdown(): Promise<void> {}
}

/** Shared inert singleton — the default tracer when none is injected. */
export const NOOP_TRACER: LlmTracer = new NoopTracer();

/**
 * composeTracers — fan one adjudicator's tracing out to SEVERAL sinks (e.g. metrics + Langfuse). Each method
 * is invoked on every member; flush()/shutdown() await all in parallel. Pure no-ops (NOOP_TRACER) are dropped
 * so a single real sink is returned unwrapped and an all-noop compose collapses back to NOOP_TRACER. Members
 * are expected to be individually safe (the MetricsTracer self-guards; the Langfuse tracer is safeTracer-
 * wrapped by selectTracer), so composing them keeps the never-throw-into-the-path invariant.
 */
export function composeTracers(...tracers: LlmTracer[]): LlmTracer {
  const active = tracers.filter((t) => t !== NOOP_TRACER);
  if (active.length === 0) return NOOP_TRACER;
  if (active.length === 1) return active[0]!;
  return {
    startCycle(ctx) {
      for (const t of active) t.startCycle(ctx);
    },
    setActivePair(pair) {
      for (const t of active) t.setActivePair(pair);
    },
    recordGeneration(gen) {
      for (const t of active) t.recordGeneration(gen);
    },
    recordCacheHit(hit) {
      for (const t of active) t.recordCacheHit(hit);
    },
    async flush() {
      await Promise.all(active.map((t) => t.flush()));
    },
    async shutdown() {
      await Promise.all(active.map((t) => t.shutdown()));
    },
  };
}

/**
 * safeTracer — wrap a tracer so EVERY method swallows its own errors at the boundary. The shipped
 * LangfuseTracer already self-guards, but this makes the side-channel invariant STRUCTURAL: no tracer impl
 * (present or FUTURE/partial) can throw into the deterministic adjudication/reconcile path or abort a chain
 * cycle (which would suppress that cycle's confident cross_window links too). select.ts wraps with this.
 */
export function safeTracer(inner: LlmTracer): LlmTracer {
  return {
    startCycle(ctx) {
      try {
        inner.startCycle(ctx);
      } catch {
        /* side channel — never throw into the path. */
      }
    },
    setActivePair(pair) {
      try {
        inner.setActivePair(pair);
      } catch {
        /* side channel. */
      }
    },
    recordGeneration(gen) {
      try {
        inner.recordGeneration(gen);
      } catch {
        /* side channel. */
      }
    },
    recordCacheHit(hit) {
      try {
        inner.recordCacheHit(hit);
      } catch {
        /* side channel. */
      }
    },
    async flush() {
      try {
        await inner.flush();
      } catch {
        /* side channel. */
      }
    },
    async shutdown() {
      try {
        await inner.shutdown();
      } catch {
        /* side channel. */
      }
    },
  };
}
