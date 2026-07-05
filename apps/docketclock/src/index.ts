/**
 * DocketClock — the reconciled federal comment-deadline substrate.
 *
 * LEGACY PLACEHOLDER. This file is not a real entrypoint: the Helm chart (and the Dockerfile
 * default CMD) run the workloads directly —
 *   - src/api/run.ts     (delivery API)
 *   - src/poll/run.ts    (poller)
 *   - src/db/migrate.ts  (migrate Job)
 *
 * See docs/architecture/docketclock.md for the design and apps/docketclock/README.md for the
 * current component map.
 */
import type { ParticipationWindow } from "@yokel/contracts";

export function placeholder(): ParticipationWindow | null {
  return null;
}
