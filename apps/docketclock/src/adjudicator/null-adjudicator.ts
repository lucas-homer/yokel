/**
 * adjudicator/null-adjudicator.ts — the deterministic ABSTAIN adapter. For ANY input it returns
 * `uncertain` (the contract's explicit abstain value), so the caller degrades to the deterministic
 * conservative path rather than acting on a fabricated answer. This is also the CI/test double: it needs
 * no provider configured and no network. id = "null:abstain". NO SDK import — provider-neutral by design.
 */
import type { AdjudicationInput, AdjudicationVerdict } from "@yokel/contracts";
import type { Adjudicator } from "./port.js";

export class NullAdjudicator implements Adjudicator {
  readonly id = "null:abstain";

  async adjudicate(_input: AdjudicationInput): Promise<AdjudicationVerdict> {
    return {
      classification: "uncertain",
      rationale:
        "null adapter, no provider configured; caller degrades to the deterministic conservative path",
    };
  }
}
