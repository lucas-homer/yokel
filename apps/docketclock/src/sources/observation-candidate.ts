/**
 * ObservationCandidate — the shape a source adapter produces and the ingest path inserts: the full
 * Observation contract MINUS observation_id (the DB mints that via gen_random_uuid()). Defined once so
 * every adapter (FR, Regs.gov, …) maps into the identical, contract-validated shape.
 */
import { Observation } from "@yokel/contracts";

export type ObservationCandidate = Omit<Observation, "observation_id">;

/** The Observation schema minus the DB-generated id — what a candidate must validate against. */
export const ObservationCandidateSchema = Observation.omit({
  observation_id: true,
});
