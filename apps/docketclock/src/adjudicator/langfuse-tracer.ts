/**
 * adjudicator/langfuse-tracer.ts — the Langfuse-backed LlmTracer (PR-C2). Selected ONLY when all of
 * LANGFUSE_HOST / LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY are present (see select.ts); otherwise the
 * NoopTracer is injected and THIS module's `Langfuse` client is never constructed.
 *
 * Uses the low-level `langfuse@^3` client (NOT the OpenAI/LangChain wrappers — our Gemini call is a raw
 * fetch). Trace shape (locked): one `trace` per chain-adjudicate cycle; each REAL LLM call is a `generation`
 * (model, input, output, token usage as TOKENS, latency); a cache HIT is a cheap closed `span` tagged
 * cached. Every observation is tagged with content_hash / adjudicator_id / rulebook_version / kind and the
 * pair's OCD-ids, so a trace cross-references the `adjudications` DB row and the structured logs.
 *
 * SAFETY: tracing is best-effort and a SIDE CHANNEL. Every record* method swallows its own errors — a
 * Langfuse hiccup must NEVER throw into the adjudication path or change a verdict. The Gemini API key and
 * LANGFUSE_SECRET_KEY NEVER enter a trace body (only public FR notice text + derived metadata do); the
 * client holds the secret internally and signs requests, but nothing secret is ever attached to an event.
 *
 * The SDK batches in the background; the poller is long-lived, so we flush() per cycle and shutdown() on
 * process exit (so the last cycle's events are not lost).
 */
import { Langfuse } from "langfuse";
import {
  type CycleContext,
  type LlmCacheHitRecord,
  type LlmGenerationRecord,
  type LlmTracer,
} from "./tracer.js";

/**
 * The minimal structural surface of the langfuse client we depend on. Declaring it loosely (a) keeps this
 * module from leaking SDK types across the codebase and (b) lets tests inject a fake client with ZERO
 * network — the real `new Langfuse(...)` is structurally compatible and assigned via a localized cast.
 */
export interface LangfuseTraceLike {
  generation(body: Record<string, unknown>): {
    end(body: Record<string, unknown>): unknown;
  };
  span(body: Record<string, unknown>): unknown;
  event(body: Record<string, unknown>): unknown;
}
export interface LangfuseClientLike {
  trace(body: Record<string, unknown>): LangfuseTraceLike;
  flushAsync(): Promise<void>;
  shutdownAsync(): Promise<void>;
}

export interface LangfuseTracerOptions {
  /** LANGFUSE_HOST — the Langfuse server base URL (in-cluster default http://langfuse.langfuse.svc:3000). */
  host: string;
  /** LANGFUSE_PUBLIC_KEY. */
  publicKey: string;
  /** LANGFUSE_SECRET_KEY — held by the client, NEVER attached to a trace. */
  secretKey: string;
  /** optional release tag for the trace (e.g. a git sha). */
  release?: string;
  /** injectable client for tests; defaults to a real `new Langfuse(...)`. */
  client?: LangfuseClientLike;
}

export class LangfuseTracer implements LlmTracer {
  private readonly client: LangfuseClientLike;
  private readonly release: string | undefined;
  /** the open per-cycle trace; generations/cache-hits attach here until flush(). */
  private currentTrace: LangfuseTraceLike | null = null;
  /** the chain pair being adjudicated — supplies OCD-ids to a generation the adjudicator can't name. */
  private activePair: { fromOcdId?: string; toOcdId?: string } | null = null;

  constructor(opts: LangfuseTracerOptions) {
    this.release = opts.release;
    this.client =
      opts.client ??
      (new Langfuse({
        publicKey: opts.publicKey,
        secretKey: opts.secretKey,
        baseUrl: opts.host,
      }) as unknown as LangfuseClientLike);
  }

  startCycle(ctx: CycleContext): void {
    try {
      this.activePair = null;
      this.currentTrace = this.client.trace({
        name: "chain-adjudicate-cycle",
        tags: ["docketclock", "adjudicator", ctx.kind],
        metadata: {
          kind: ctx.kind,
          surfaced: ctx.surfaced,
          cap: ctx.cap,
        },
        ...(this.release ? { release: this.release } : {}),
      });
    } catch {
      // best-effort: a tracing failure must never break the cycle.
      this.currentTrace = null;
    }
  }

  setActivePair(pair: { fromOcdId?: string; toOcdId?: string } | null): void {
    this.activePair = pair;
  }

  /** The trace generations/spans attach to: the open cycle trace, or a fresh standalone trace (e.g. a
   * notice-kind adjudication run outside a chain cycle, or a direct adjudicate() call). */
  private parent(kind: "notice" | "chain"): LangfuseTraceLike | null {
    if (this.currentTrace) return this.currentTrace;
    try {
      return this.client.trace({
        name: `adjudicate-${kind}`,
        tags: ["docketclock", "adjudicator", kind],
        ...(this.release ? { release: this.release } : {}),
      });
    } catch {
      return null;
    }
  }

  recordGeneration(gen: LlmGenerationRecord): void {
    try {
      const trace = this.parent(gen.kind);
      if (!trace) return;
      const fromOcdId = gen.fromOcdId ?? this.activePair?.fromOcdId;
      const toOcdId = gen.toOcdId ?? this.activePair?.toOcdId;
      const generation = trace.generation({
        name: `adjudicate:${gen.kind}`,
        model: gen.model,
        // input is the public AdjudicationInput — NEVER the API key.
        input: gen.input,
        metadata: {
          content_hash: gen.contentHash,
          adjudicator_id: gen.adjudicatorId,
          rulebook_version: gen.rulebookVersion,
          kind: gen.kind,
          classification: gen.verdict.classification,
          latency_ms: gen.latencyMs,
          cached: false,
          ...(fromOcdId ? { from_ocd_id: fromOcdId } : {}),
          ...(toOcdId ? { to_ocd_id: toOcdId } : {}),
        },
      });
      generation.end({
        output: gen.output,
        ...(gen.usage
          ? {
              usage: {
                input: gen.usage.input,
                output: gen.usage.output,
                total: gen.usage.total,
                unit: "TOKENS",
              },
            }
          : {}),
      });
    } catch {
      // best-effort: never throw into the adjudication path.
    }
  }

  recordCacheHit(hit: LlmCacheHitRecord): void {
    try {
      const trace = this.parent(hit.kind);
      if (!trace) return;
      const now = new Date();
      // A cheap CLOSED span (startTime === endTime) — a cache hit did no work, so there is nothing to time.
      trace.span({
        name: `adjudicate-cache-hit:${hit.kind}`,
        startTime: now,
        endTime: now,
        metadata: {
          content_hash: hit.contentHash,
          adjudicator_id: hit.adjudicatorId,
          rulebook_version: hit.rulebookVersion,
          kind: hit.kind,
          classification: hit.classification,
          cached: true,
          ...(hit.fromOcdId ? { from_ocd_id: hit.fromOcdId } : {}),
          ...(hit.toOcdId ? { to_ocd_id: hit.toOcdId } : {}),
        },
      });
    } catch {
      // best-effort.
    }
  }

  async flush(): Promise<void> {
    // Close the cycle and push buffered events. Swallow errors — a flush failure must not break the cycle
    // log that calls us (tracing is a side channel).
    this.currentTrace = null;
    this.activePair = null;
    try {
      await this.client.flushAsync();
    } catch {
      // best-effort.
    }
  }

  async shutdown(): Promise<void> {
    try {
      await this.client.shutdownAsync();
    } catch {
      // best-effort.
    }
  }
}
