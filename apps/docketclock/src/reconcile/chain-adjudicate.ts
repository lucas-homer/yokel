/**
 * chain-adjudicate.ts — the ASYNC escalation orchestration that wires the LLM adjudicator into the
 * CROSS-WINDOW (chain) reconcile pass (#31 Slice 3b). This is the FIRST slice where the LLM can change a
 * classification, so the safety invariants are non-negotiable and live HERE (chain.ts stays pure):
 *
 *   CONSERVATIVE ENVELOPE — only an `affirm` verdict promotes an ambiguous pair to a cross_window link.
 *   `reject` / `uncertain` / ANY thrown error → NO link (today's conservative behavior). The worst case
 *   for an LLM outage is byte-identical to the deterministic-only output — an outage can NEVER break the
 *   chain pass or fabricate a link.
 *
 *   NULL-ADAPTER NO-OP — under the null adapter (prod until the integrator provisions a key) we SHORT-
 *   CIRCUIT before consulting: nothing is promoted AND nothing is written to the adjudications cache. This
 *   is load-bearing — caching the null adapter's `uncertain` (keyed by content_hash, which excludes the
 *   adjudicator id) would permanently shadow the real provider's later adjudication of the same pair. So
 *   the persisted set is byte-identical to today's confident-only set AND the cache stays pristine for 3c.
 *
 *   HONESTY — every promoted link carries the `llm_corroborated` ConflictFlag ALONGSIDE its deterministic
 *   type flag(s), so the feed never presents an LLM-judged link as deterministically certain.
 *
 *   BOUNDED + OBSERVABLE — the per-cycle cap bounds FRESH LLM CALLS (cache misses), NOT pairs considered.
 *   A cache HIT is a free replay that does NOT spend the budget, so already-decided pairs are re-applied
 *   every cycle UNCAPPED while the budget advances to the next batch of genuinely-new pairs. surfaced /
 *   cacheHits / llmCalls / deferred / linked counts are logged and returned. No silent truncation.
 *
 *   NO STARVATION (the cap×cache fix) — the OLD loop did `slice(0, cap)` on the deterministically-SORTED
 *   pair list and consulted each, so every cycle it re-considered the SAME first `cap` pairs by sort order.
 *   After cycle 1 those were cache hits (free) yet STILL consumed the slice budget, so when surfaced > cap
 *   the pairs beyond the cap were NEVER adjudicated — permanently starved. The fix: PEEK the cache first
 *   (a SELECT, no call). A hit applies the stored verdict for free; a miss spends one unit of budget on a
 *   real consult (or DEFERS if the budget is gone). So cycle 1 spends `cap` calls on the first `cap`
 *   uncached pairs; next cycle those are free hits and the budget advances to the next uncached batch — the
 *   backlog DRAINS over cycles, steady-state ~0 calls/cycle (all cached) plus genuinely-new pairs.
 *
 *   CACHED / REPLAY — peek + consult key IDENTICALLY (same content_hash): a given (A, B) is adjudicated
 *   once (a fresh consult), then replayed for free on every later cycle via the peek.
 *
 *   PER-PAIR ERROR ISOLATION — each fresh consult is wrapped in try/catch. A throw (gemini down / timeout /
 *   malformed) is logged and the pair SKIPPED (no link); the cycle continues. The throw STILL spent its
 *   budget unit (a fresh-call ATTEMPT consumes budget whether it returns or throws), so a flapping provider
 *   is not hammered across the entire surfaced set in a single cycle.
 */
import type { AdjudicationVerdict } from "@yokel/contracts";
import { RULEBOOK_VERSION } from "../rulebox/index.js";
import {
  consultAdjudicator,
  peekAdjudication,
} from "../adjudicator/consult.js";
import { NULL_ADJUDICATOR_ID } from "../adjudicator/null-adjudicator.js";
import type { Adjudicator } from "../adjudicator/port.js";
import type { Sql } from "../db/client.js";
import {
  buildChainConflict,
  classify,
  type AmbiguousPair,
  type ChainConflict,
} from "./chain.js";

/**
 * CHAIN_DEFAULT_MAX_ESCALATIONS — the per-cycle cap default (overridable via
 * CHAIN_MAX_ESCALATIONS_PER_CYCLE). It bounds FRESH LLM CALLS (cache misses) per cycle, NOT pairs
 * considered — a cache hit is a free replay that never spends this budget. 25 is a deliberately small,
 * observable default: it bounds per-cycle LLM cost + latency while comfortably covering the routine
 * ambiguous tail; an uncached backlog larger than the cap drains over cycles (no starvation). llmCalls /
 * deferred are logged, so a budget bite is visible, not silent.
 */
export const CHAIN_DEFAULT_MAX_ESCALATIONS = 25;

/** Resolve the per-cycle FRESH-CALL cap from env (sane positive-integer default). */
export function chainMaxEscalations(
  env: NodeJS.ProcessEnv = process.env,
): number {
  const raw = Number(env.CHAIN_MAX_ESCALATIONS_PER_CYCLE);
  return Number.isInteger(raw) && raw > 0 ? raw : CHAIN_DEFAULT_MAX_ESCALATIONS;
}

export interface ChainAdjudicateResult {
  /** total ambiguous pairs surfaced by the pure engine (the escalation candidate set). */
  ambiguous: number;
  /** pairs whose verdict was applied from the cache this cycle (peek HIT — free, no LLM call, no budget). */
  cacheHits: number;
  /** FRESH LLM calls made this cycle (cache misses that had budget). ≤ cap. A throw still counts (budget spent). */
  llmCalls: number;
  /** uncached pairs SKIPPED this cycle because the fresh-call budget was exhausted (surface again next cycle). */
  deferred: number;
  /** affirmed pairs promoted to a cross_window link (carry llm_corroborated) — from cache hits + fresh calls. */
  llmLinked: number;
  /** the promoted links — to be MERGED with the confident set and persisted. */
  links: ChainConflict[];
}

/**
 * adjudicateAmbiguousPairs — iterate the ambiguous pairs in their existing deterministic sort order and,
 * for EACH, first PEEK the verdict cache (a SELECT, no LLM call):
 *   • Cache HIT  → apply the stored verdict for FREE (no call, no budget). An `affirm` still promotes the
 *                  link, so already-decided pairs keep their links every cycle, UNCAPPED.
 *   • Cache MISS → only if fresh-call budget remains, make the real consult (which persists), spending one
 *                  unit of budget. If the budget is exhausted, DEFER the pair (no verdict this cycle; it
 *                  surfaces again next cycle). A fresh-call ATTEMPT spends budget whether it returns OR
 *                  throws (per-pair try/catch isolates a throw → log + skip + no link, but budget is spent).
 * Returns the pairs it AFFIRMED, promoted to cross_window ChainConflicts (each carrying classify(b) flags
 * PLUS `llm_corroborated`). Pure-ish: the ONLY side effects are the cache reads/writes inside
 * peekAdjudication / consultAdjudicator and console logging. Never throws on a per-pair failure.
 *
 * MULTI_TARGET CHOICE (documented): a promoted link is built with multiTarget=FALSE — it carries its type
 * flag(s) + `llm_corroborated` and does NOT retro-add `multi_target_notice` to itself OR to any confident
 * link. Under-flagging is the safe direction (consistent with "over-linking is worse"): the deterministic
 * multi_target computation stays byte-identical under the null adapter (Invariant 1), and an LLM-judged
 * link is never dressed up with a deterministic multi-target claim it didn't earn.
 */
export async function adjudicateAmbiguousPairs(
  sql: Sql,
  adjudicator: Adjudicator,
  ambiguousPairs: AmbiguousPair[],
  now: Date,
  cap: number,
): Promise<ChainAdjudicateResult> {
  const ambiguous = ambiguousPairs.length;

  // NULL-ADAPTER SHORT-CIRCUIT: an always-abstaining adjudicator would only ever return `uncertain`, and
  // consulting it would persist that `uncertain` into the content-hash cache — permanently shadowing the
  // real provider's later adjudication of the same pair (the key excludes adjudicator_id). So when no real
  // provider is configured we do ZERO consults and ZERO cache writes: a true no-op that keeps the cache
  // pristine for Slice 3c. Ambiguous pairs are still counted/surfaced; nothing is escalated or linked.
  if (adjudicator.id === NULL_ADJUDICATOR_ID) {
    if (ambiguous > 0) {
      console.info(
        `[chain-adjudicate] surfaced=${ambiguous} but no real adjudicator configured (null:abstain) — skipping escalation`,
      );
    }
    return {
      ambiguous,
      cacheHits: 0,
      llmCalls: 0,
      deferred: 0,
      llmLinked: 0,
      links: [],
    };
  }

  // Budget = max fresh LLM CALLS this cycle (cache misses). Floor a botched/negative cap to 0 (defense in
  // depth: even if a caller bypasses chainMaxEscalations and passes a negative, we never escalate-everything).
  let callBudget = Math.max(0, cap);

  const links: ChainConflict[] = [];
  let cacheHits = 0;
  let llmCalls = 0;
  let deferred = 0;

  // Iterate in the EXISTING deterministic sort order (determinism preserved). For each pair: peek first.
  for (const { a, b } of ambiguousPairs) {
    // For an ambiguous pair, by DEFINITION: shared_docket=true, shared_rin=false, explicit_reference=false
    // (those are exactly the rule-2 signals that failed; the structural rules 1/3/4 passed).
    const input = {
      kind: "chain" as const,
      rulebook_version: RULEBOOK_VERSION,
      a_title: a.title ?? "",
      a_dates_text: a.dates_text,
      a_publication_date: a.publication_date,
      b_title: b.title ?? "",
      b_dates_text: b.dates_text,
      b_publication_date: b.publication_date,
      shared_docket: true,
      shared_rin: false,
      explicit_reference: false,
    };

    // PEEK the cache first — a SELECT, never an LLM call. A peek-and-consult key IDENTICALLY (same hash).
    const cached = await peekAdjudication(sql, input);

    let verdict: AdjudicationVerdict;
    if (cached) {
      // CACHE HIT — apply the stored verdict for FREE. Does NOT consume the fresh-call budget, so ALL
      // previously-decided pairs are covered every cycle, uncapped. (This is the anti-starvation core: a
      // pair adjudicated last cycle is replayed here without spending budget, freeing it for new pairs.)
      cacheHits++;
      verdict = cached;
    } else {
      // CACHE MISS — needs a real call. Only spend it if the budget remains; else DEFER (no verdict this
      // cycle; the pair surfaces again next cycle and gets adjudicated once the cap-many ahead of it cache).
      if (callBudget <= 0) {
        deferred++;
        continue;
      }
      // A fresh-call ATTEMPT spends budget whether it returns OR throws — so a flapping provider is not
      // hammered across the whole surfaced set in one cycle. Decrement BEFORE awaiting.
      callBudget--;
      llmCalls++;
      try {
        ({ verdict } = await consultAdjudicator(sql, adjudicator, input));
      } catch (err) {
        // PER-PAIR ERROR ISOLATION: a thrown adjudication (down/timeout/malformed) is logged and SKIPPED
        // (no link). One bad call must not abort the cycle or the other pairs — worst case is today's
        // output. The budget unit was already spent above (deliberate — see the flapping-provider note).
        console.warn(
          `[chain-adjudicate] consult failed for ${a.ocd_id} → ${b.ocd_id}; skipping (no link): ${
            err instanceof Error ? err.message : String(err)
          }`,
        );
        continue;
      }
    }

    // CONSERVATIVE ENVELOPE: ONLY affirm adds a link. reject / uncertain → no link (cache hit OR fresh).
    if (verdict.classification !== "affirm") continue;

    const flags = [...classify(b, false), "llm_corroborated" as const];
    links.push(buildChainConflict(a, b, flags, now));
  }

  // Only log when something actually happened — poll/run.ts already logs the per-cycle chain summary, so
  // an unconditional line here would just add steady-state noise on every (mostly-empty) reconcile.
  if (ambiguous > 0) {
    console.info(
      `[chain-adjudicate] surfaced=${ambiguous} cacheHits=${cacheHits} llmCalls=${llmCalls} deferred=${deferred} llmLinked=${links.length} (cap=${cap})`,
    );
  }

  return {
    ambiguous,
    cacheHits,
    llmCalls,
    deferred,
    llmLinked: links.length,
    links,
  };
}
