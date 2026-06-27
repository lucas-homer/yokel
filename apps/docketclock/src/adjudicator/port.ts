/**
 * adjudicator/port.ts — the provider-NEUTRAL adjudicator interface (the seam Slice 3 implements with a
 * real LLM). NO @anthropic/@google SDK import anywhere in this subsystem; the only concrete adapters in
 * this slice are NullAdjudicator (abstain) and the test SPY. The deterministic RuleBox evaluator
 * (rulebox/index.ts) NEVER touches this — it stays pure + synchronous on the parse hot path. Adjudication
 * is out-of-band, async, with its own DB cache; a later slice invokes it from the poller/reconcile layer.
 */
import type { AdjudicationInput, AdjudicationVerdict } from "@yokel/contracts";
import type { LlmTracer } from "./tracer.js";

export interface Adjudicator {
  /**
   * Provenance fragment recorded on the cache row as `${id}@${rulebook_version}` (e.g. "null:abstain",
   * later "gemini:gemini-2.5-flash"). It identifies WHICH engine produced a verdict AND is HALF the cache
   * key: the `adjudications` cache is keyed by (content_hash, adjudicator_id) (migration 0009), so each
   * engine's verdict is cached independently — a non-deciding adapter ("null:abstain@<rb>") can never
   * shadow a real one, and a provider/model swap re-adjudicates (replay determinism is per-adjudicator).
   */
  readonly id: string;
  /** Answer the ambiguous question. May throw/time out — the caller degrades to the deterministic path. */
  adjudicate(input: AdjudicationInput): Promise<AdjudicationVerdict>;
  /**
   * OPTIONAL observability side channel (PR-C2). When an adjudicator makes real LLM calls it records each as
   * a `generation` here; the chain orchestrator reads it off the adjudicator to open a per-cycle trace,
   * record cache hits, and flush(). This does NOT change the verdict contract — it is injected at
   * construction (select.ts) and defaults to a NoopTracer. Adapters that never call an LLM (NullAdjudicator)
   * leave it undefined; the orchestrator falls back to a no-op tracer.
   */
  readonly tracer?: LlmTracer;
}
