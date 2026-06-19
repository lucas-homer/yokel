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
 * string — an always-abstaining adjudicator must NOT be consulted through the cache, because persisting
 * its `uncertain` verdict (keyed by content_hash, which excludes adjudicator_id) would permanently
 * shadow a later real provider's adjudication of the same input.
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
