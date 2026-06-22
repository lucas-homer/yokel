/**
 * adjudicator/null-adjudicator.ts — the deterministic ABSTAIN adapter. For ANY input it returns
 * `uncertain` (the contract's explicit abstain value), so the caller degrades to the deterministic
 * conservative path rather than acting on a fabricated answer. This is also the CI/test double: it needs
 * no provider configured and no network. id = "null:abstain". NO SDK import — provider-neutral by design.
 */
import type { AdjudicationInput, AdjudicationVerdict } from "@yokel/contracts";
import type { Adjudicator } from "./port.js";

/**
 * The null adapter's id. Exported so callers can detect the always-abstain sentinel WITHOUT a magic
 * string and short-circuit it. Since the cache is keyed by (content_hash, adjudicator_id) (migration
 * 0009), a persisted `null:abstain` row can NO LONGER shadow a real provider — its row lives under a
 * different key. The short-circuit is retained purely as waste-avoidance: consulting an always-abstaining
 * adapter would burn a DB round-trip to write a useless `uncertain` row that nothing will ever replay.
 */
export const NULL_ADJUDICATOR_ID = "null:abstain";

export class NullAdjudicator implements Adjudicator {
  readonly id = NULL_ADJUDICATOR_ID;

  async adjudicate(_input: AdjudicationInput): Promise<AdjudicationVerdict> {
    return {
      classification: "uncertain",
      rationale:
        "null adapter, no provider configured; caller degrades to the deterministic conservative path",
    };
  }
}
