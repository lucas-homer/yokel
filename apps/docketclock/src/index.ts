/**
 * DocketClock — the reconciled federal comment-deadline substrate.
 *
 * STUB. Do not build out until the Week-1 spikes pass (esp. D1 frDocNum join hit-rate, which
 * decides the reconciliation join strategy). See:
 *   - docs/architecture/docketclock.md   (the design)
 *   - docs/plans/week1-validation-spikes.md  (the gate)
 *
 * Build order (from the architecture build sequence):
 *   1. Validate (spikes)  2. Spine (Postgres: append-only Observation log + trigger)
 *   3. Reconcile (RuleBox confidence engine)  4. Public contract (Fastify REST + OpenAPI)
 *   5. Review console  6. Follow-up + AccuracyRecord
 */
import type { ParticipationWindow } from "@yokel/contracts";

export function placeholder(): ParticipationWindow | null {
  // TODO: nothing here yet — the substrate is gated behind the Week-1 validation spikes.
  return null;
}
