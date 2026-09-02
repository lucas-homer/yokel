/**
 * ObservationCandidate — the shape a source adapter produces and the ingest path inserts: the full
 * Observation contract MINUS observation_id (the DB mints that via gen_random_uuid()). Defined once so
 * every adapter (FR, Regs.gov, …) maps into the identical, contract-validated shape.
 */
import {
  ObservationFields,
  observationRawInvariant,
  type Observation,
} from "@yokel/contracts";

export type ObservationCandidate = Omit<Observation, "observation_id">;

/**
 * The Observation schema minus the DB-generated id — what a candidate must validate against.
 * Derived from ObservationFields (the plain object shape) because zod 3's .omit does not exist on
 * a refined schema — so the source-discriminated typed-raw invariant (human_review raw must parse
 * as HumanReviewVerdict; machine-source raw stays unknown) must be RE-COMPOSED here explicitly.
 * Dropping the superRefine would silently reopen the freeform-raw hole the contract closes.
 */
export const ObservationCandidateSchema = ObservationFields.omit({
  observation_id: true,
}).superRefine(observationRawInvariant);
