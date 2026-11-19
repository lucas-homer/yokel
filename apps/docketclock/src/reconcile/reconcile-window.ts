/**
 * reconcile-window.ts — derive one window as an Effect program (ADR 0018, slice 5b).
 *
 * reconcileOcdId is the single path every write takes to derive a window (FR/Regs ingest, the status
 * refresh, the amended-originals re-derive, the rederive sweep, the review write). As an Effect each step
 * is a child span of `reconcile.window`, so a slow pass shows which step and which window cost the time:
 *
 *   SELECT observations             the window's whole observation chain
 *   reconcile.amendment_inputs      the linked FR amendments (persist.ts loadAmendmentInputs; its own
 *                                   queries are child spans: corpus stamp, corpus rebuild, latest FR row,
 *                                   citation arrivals)
 *   reconcile.core                  the pure rulebook (reconcile.ts)
 *   TRANSACTION reconciliation      persistReconciliation: projection + conflict feed, atomically
 *
 * Failure model: any step's failure is a `WindowFailure` naming the step, carrying the error that step
 * threw as `cause`. The Promise export `reconcileOcdId` (re-exported from persist.ts) rejects with that
 * same `cause`, so its callers and tests see exactly the errors they saw before.
 */
import { Data, Effect } from "effect";
import { withAmbient, runAmbient } from "../ambient.js";
import type { Sql } from "../db/client.js";
import { dbQuery } from "../db/effect.js";
import {
  loadAmendmentInputs,
  loadObservations,
  persistReconciliation,
  reconcileOptionsOf,
  type ReconcileOcdIdResult,
} from "./persist.js";
import { reconcile } from "./reconcile.js";

export class WindowFailure extends Data.TaggedError("WindowFailure")<{
  readonly ocd_id: string;
  /** the step that failed: its span name */
  readonly step: string;
  /** what that step threw; the Promise form rejects with exactly this */
  readonly cause: unknown;
}> {
  override get message(): string {
    return this.cause instanceof Error
      ? this.cause.message
      : String(this.cause);
  }
}

/** Derive and persist one window. */
export const reconcileWindow = (
  sql: Sql,
  ocdId: string,
  now: Date = new Date(),
): Effect.Effect<ReconcileOcdIdResult, WindowFailure> => {
  const failed = (step: string) => (cause: unknown) =>
    new WindowFailure({ ocd_id: ocdId, step, cause });
  return Effect.gen(function* () {
    const observations = yield* dbQuery(
      "SELECT observations",
      () => loadObservations(sql, ocdId),
      (rows) => ({ "db.response.returned_rows": rows.length }),
    ).pipe(Effect.mapError((e) => failed(e.query)(e.cause)));
    if (observations.length === 0)
      return yield* Effect.fail(
        failed("SELECT observations")(
          new Error(`reconcileOcdId: no observations for ocd_id "${ocdId}"`),
        ),
      );

    const amendment = yield* withAmbient(() =>
      loadAmendmentInputs(sql, ocdId),
    ).pipe(
      Effect.tap((a) =>
        Effect.annotateCurrentSpan(
          "docketclock.amendment.outcome",
          a.outcome.kind,
        ),
      ),
      Effect.withSpan("reconcile.amendment_inputs"),
      Effect.mapError(failed("reconcile.amendment_inputs")),
    );

    const result = yield* Effect.try({
      try: () => reconcile(observations, now, reconcileOptionsOf(amendment)),
      catch: failed("reconcile.core"),
    }).pipe(
      Effect.tap((r) =>
        Effect.annotateCurrentSpan(
          "docketclock.window.status",
          r.window.status,
        ),
      ),
      Effect.withSpan("reconcile.core"),
    );

    const persist = yield* dbQuery(
      "TRANSACTION reconciliation",
      () => persistReconciliation(sql, result, now),
      (p) => ({
        "docketclock.window.inserted": p.inserted,
        "docketclock.window.version_bumped": p.versionBumped,
      }),
    ).pipe(Effect.mapError((e) => failed(e.query)(e.cause)));

    return { ...result, persist };
  }).pipe(
    Effect.tapError((e) =>
      Effect.annotateCurrentSpan("docketclock.failed_step", e.step),
    ),
    Effect.withSpan("reconcile.window", {
      attributes: { "docketclock.ocd_id": ocdId },
    }),
  );
};

/**
 * Read every Observation for an ocd_id from the log, resolve its linked FR amendments
 * (loadAmendmentEvidence, reconcile-v2.4), run the pure engine, persist the projection. The single
 * DB-aware orchestration point; the rulebook itself stays pure + deterministic. Every write path that
 * derives a window — FR/Regs ingest, the rederive sweep, the status refresh, the review write — comes
 * through here, so they all pass the SAME amendment outcome. Rejects with the failing step's own error.
 */
export function reconcileOcdId(
  sql: Sql,
  ocdId: string,
  now: Date = new Date(),
): Promise<ReconcileOcdIdResult> {
  return runAmbient(
    reconcileWindow(sql, ocdId, now).pipe(
      Effect.catch((e) => Effect.die(e.cause)),
    ),
  );
}
