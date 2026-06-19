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
 *   BOUNDED + OBSERVABLE — escalations are CAPPED per cycle (configurable); surfaced / escalated / capped
 *   / linked counts are logged and returned. No silent truncation.
 *
 *   CACHED / REPLAY — every consult goes through consultAdjudicator (content-hash cache): a given (A, B)
 *   is adjudicated once, then replayed.
 *
 *   PER-PAIR ERROR ISOLATION — each consult is wrapped in try/catch. A throw (gemini down / timeout /
 *   malformed) is logged and the pair SKIPPED (no link); the cycle continues with the remaining pairs.
 */
import { RULEBOOK_VERSION } from "../rulebox/index.js";
import { consultAdjudicator } from "../adjudicator/consult.js";
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
 * CHAIN_DEFAULT_MAX_ESCALATIONS — the per-cycle escalation cap default (overridable via
 * CHAIN_MAX_ESCALATIONS_PER_CYCLE). 25 is a deliberately small, observable default: it bounds per-cycle
 * LLM calls (cost + latency) while comfortably covering the routine ambiguous tail. Surfaced-vs-escalated
 * is logged, so a cap bite is visible, not silent.
 */
export const CHAIN_DEFAULT_MAX_ESCALATIONS = 25;

/** Resolve the per-cycle escalation cap from env (sane positive-integer default). */
export function chainMaxEscalations(
  env: NodeJS.ProcessEnv = process.env,
): number {
  const raw = Number(env.CHAIN_MAX_ESCALATIONS_PER_CYCLE);
  return Number.isInteger(raw) && raw > 0 ? raw : CHAIN_DEFAULT_MAX_ESCALATIONS;
}

export interface ChainAdjudicateResult {
  /** total ambiguous pairs surfaced by the pure engine (the escalation candidate set). */
  ambiguous: number;
  /** how many were actually CONSULTED (== min(ambiguous, cap)). */
  escalated: number;
  /** how many were dropped by the cap (surfaced but not consulted). */
  escalationsCapped: number;
  /** affirmed pairs promoted to a cross_window link (carry llm_corroborated). */
  llmLinked: number;
  /** the promoted links — to be MERGED with the confident set and persisted. */
  links: ChainConflict[];
}

/**
 * adjudicateAmbiguousPairs — consult the adjudicator over the (capped) ambiguous pair set and return the
 * pairs it AFFIRMED, promoted to cross_window ChainConflicts (each carrying classify(b) flags PLUS
 * `llm_corroborated`). Pure-ish: the ONLY side effects are the cache reads/writes inside consultAdjudicator
 * and console logging. Never throws on a per-pair adjudication failure (isolated + skipped).
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
      escalated: 0,
      escalationsCapped: 0,
      llmLinked: 0,
      links: [],
    };
  }

  const toEscalate = ambiguousPairs.slice(0, Math.max(0, cap));
  const escalated = toEscalate.length;
  const escalationsCapped = ambiguous - escalated;

  if (escalationsCapped > 0) {
    console.warn(
      `[chain-adjudicate] cap hit: surfaced=${ambiguous} escalated=${escalated} capped=${escalationsCapped} (cap=${cap})`,
    );
  }

  const links: ChainConflict[] = [];
  for (const { a, b } of toEscalate) {
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

    let verdict;
    try {
      ({ verdict } = await consultAdjudicator(sql, adjudicator, input));
    } catch (err) {
      // PER-PAIR ERROR ISOLATION: a thrown adjudication (down/timeout/malformed) is logged and SKIPPED
      // (no link). One bad call must not abort the cycle or the other pairs — worst case is today's output.
      console.warn(
        `[chain-adjudicate] consult failed for ${a.ocd_id} → ${b.ocd_id}; skipping (no link): ${
          err instanceof Error ? err.message : String(err)
        }`,
      );
      continue;
    }

    // CONSERVATIVE ENVELOPE: ONLY affirm adds a link. reject / uncertain → no link.
    if (verdict.classification !== "affirm") continue;

    const flags = [...classify(b, false), "llm_corroborated" as const];
    links.push(buildChainConflict(a, b, flags, now));
  }

  // Only log when something actually happened — poll/run.ts already logs the per-cycle chain summary, so
  // an unconditional line here would just add steady-state noise on every (mostly-empty) reconcile.
  if (ambiguous > 0) {
    console.info(
      `[chain-adjudicate] surfaced=${ambiguous} escalated=${escalated} capped=${escalationsCapped} llmLinked=${links.length}`,
    );
  }

  return {
    ambiguous,
    escalated,
    escalationsCapped,
    llmLinked: links.length,
    links,
  };
}
