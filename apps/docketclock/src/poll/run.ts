/**
 * run.ts — the THIN scheduler around the UNIFIED single-writer poll cycle (NOT the testable core).
 * Self-loads the repo-root .env (like the smokes), then on a fixed interval (default 15 min, per
 * docs/architecture/docketclock.md "1. Discover") runs, SEQUENTIALLY in ONE process:
 *
 *   1. pollFrOnce  — FR open-comment discovery (FIRST), then
 *   2. pollRegsOnce — Regs.gov differential + re-poll pass, then
 *   2b. govinfoSweepOnce — the published GovInfo text of recent FR amendment documents (ADR 0016):
 *      append-only, capped per cycle; BEFORE the chain pass so the text is there to link and resolve on,
 *   3. chainReconcileOnce — the cross_window (chain) reconcile sweep (#31), then
 *   3b. rederiveChainOriginals — re-derive the side-A windows of the confident links (reconcile-v2.4)
 *      so an amendment that arrived this cycle moves its original in the SAME cycle, then
 *   4. refreshStaleOpenWindows — the status refresh (#107): re-derive open windows whose close has
 *      passed, so status flips closed within one cycle instead of waiting for an observation a settled
 *      notice may never produce. Runs BEFORE verify so a window flipped closed here is snapshot-eligible
 *      for the SAME cycle's verification pass. Then
 *   5. verifyOnce — the post-close verification pass (slice V, PR-V1), then
 *   6. reviewQueueStats — queue observability (Slice R, PR-R4): READ-ONLY depth + rot-age gauges
 *      feeding the review-queue-stale alert. Last because it reads the projections/conflicts every
 *      earlier pass may have just changed this cycle.
 *
 * logging ALL SIX summaries (log messages: "fr poll cycle", "regs poll cycle", "chain reconcile
 * cycle", "status refresh cycle", "verify cycle", "review queue stats").
 *
 * WHY VERIFY RUNS LAST (slice V): the verify pass reads the projections + observations the first
 * four passes just wrote — it snapshots newly-closed windows and judges windows whose horizon the
 * cycle's fresh checks may just have satisfied. Its watch rows feed BACK into pass 2's re-poll set
 * (closed-in-horizon windows stay checked) starting the NEXT cycle — deferrable by design, budgeted
 * like every other re-poll. Same single-writer discipline: it UPSERTs watch rows and INSERTs final
 * accuracy_records, so it must never overlap another writer.
 *
 * WHY CHAIN RUNS AFTER FR+REGS (a derive-over-derived pass): the chain pass reads the participation_windows +
 * federal_register observations the FR and Regs passes just wrote — it derives cross_window conflicts
 * over the windows the first two passes produced. Running it AFTER both means an amendment notice and the
 * original it amends, if both were (re)discovered this cycle, are linked in the SAME cycle. It is a full
 * sweep over the projection and, like the other passes, MUST be single-writer (it UPSERTs/retires
 * conflict_records) — which the sequential, non-overlapping scheduler already guarantees.
 *
 * WHY FR-FIRST + SEQUENTIAL (single-writer invariant): there is exactly ONE poller process. The
 * ingest/reconcile path is NOT concurrency-safe — there is no per-ocd_id lock (see the
 * CONCURRENCY(single-writer) notes in src/ingest/observe.ts and src/reconcile/persist.ts), so two
 * concurrent writers would race the latest-hash dedupe and the projection upsert. We avoid that by
 * staying single-process and running the two passes back-to-back, never overlapping. FR runs FIRST so
 * an FR-discovered window (which carries a regs_document_id but no regulations_gov observation yet) is
 * picked up by the SAME cycle's Regs re-poll pass — fetching the Regs counterpart and lifting the pair
 * toward HIGH/CONFLICTING in one cycle.
 *
 * Deliberately tiny: where this actually runs (pg_cron / a Node cron / a worker on the Mac Mini) is ops
 * and out of scope. Both poll CORES are fully deterministic/injectable; only this entrypoint touches the
 * live network and the wall clock. Guarded by regsApiKey() so a misconfig fails loudly before the loop
 * (the Regs pass needs the key; FR is KEYLESS and needs none).
 *
 * EFFECT (ADR 0018, slice 3): the scheduler is an Effect program.
 *   - SCHEDULING: `Effect.repeat(Schedule.spaced(INTERVAL))` — the next cycle starts INTERVAL after the
 *     current one SETTLES, so a cycle that runs longer than the interval can never overlap itself
 *     (overlapping runs would race the cursor and violate the single-writer assumption above).
 *   - SHUTDOWN: SIGTERM/SIGINT interrupt the program. A cycle is `uninterruptible`, so an in-flight cycle
 *     finishes first; then every resource (pool, lock session, /metrics server, LLM tracer) is closed by
 *     its own `acquireRelease` finalizer, in reverse order of opening — so a container restart never kills
 *     a mid-poll write.
 *   - TRACING: one span per cycle (`poll.cycle`) and one per pass (`poll.pass.<name>`), with each pass's
 *     summary counts as span attributes. Exported over OTLP when OTEL_EXPORTER_OTLP_ENDPOINT is set
 *     (src/telemetry.ts); flushed before exit, so run-once cycles are not lost.
 *
 * Run: DATABASE_URL=... pnpm --filter @yokel/docketclock tsx src/poll/run.ts
 */
import { existsSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

// Load the repo-root .env BEFORE importing anything that reads env at module-evaluation time — notably the
// logger (LOG_LEVEL is locked in when log.ts is first imported) and the poll-core modules, each of which
// binds a module-scope componentLogger. A static `import` evaluates before this file's body runs, so every
// env/logger-touching module is imported DYNAMICALLY below, AFTER the env is loaded — this is what lets
// LOG_LEVEL in .env take effect in local dev. In k8s LOG_LEVEL is a real pod env var, so it works anyway.
const envPath = fileURLToPath(new URL("../../../../.env", import.meta.url));
if (existsSync(envPath)) process.loadEnvFile(envPath);

const { createClient, createSessionClient } = await import("../db/client.js");
const { componentLogger } = await import("../log.js");
const { regsApiKey } = await import("../sources/regulations-gov.js");
const { chainReconcileOnce, rederiveChainOriginals } =
  await import("../reconcile/persist.js");
const { govinfoSweepOnce } = await import("../sources/govinfo.js");
const { refreshStaleOpenWindows } =
  await import("../reconcile/status-refresh.js");
const { reviewQueueStats } = await import("../review/core.js");
const { selectAdjudicator } = await import("../adjudicator/select.js");
const { pollFrOnce } = await import("./fr-poll.js");
const { pollRegsOnce } = await import("./poll.js");
const { verifyOnce, highCorrectRatio90d } = await import("../verify/run.js");
const {
  recordFrPoll,
  recordRegsPoll,
  recordChainCycle,
  recordStatusRefresh,
  recordVerifyCycle,
  recordReviewQueue,
  setAccuracyHighRatio,
  recordPollPassFailure,
  observePollCycle,
  setHeartbeat,
} = await import("../metrics.js");
const { startMetricsServer } = await import("../metrics-server.js");
const { cycleLock } = await import("./cycle-lock.js");
const { telemetryLayer } = await import("../telemetry.js");
const { Cause, Effect, Schedule } = await import("effect");

const log = componentLogger("poller");

const INTERVAL_MS = Number(process.env.POLL_INTERVAL_MS) || 15 * 60_000;

// RUN-ONCE MODE: `run.ts --once` (or POLL_ONCE=1) runs exactly ONE cycle, then drains and exits — no
// loop, no /metrics server. This is the entrypoint for a scheduler that lives OUTSIDE the process (the
// planned Cloudflare Cron Trigger → Container path, or a k8s CronJob). Exit code: 0 when the cycle ran
// (pass-level failures are isolated and logged, as in the loop) or was skipped because another cycle holds
// the lock; 1 only when the cycle itself could not run (e.g. the database is unreachable).
const ONCE = process.argv.includes("--once") || process.env.POLL_ONCE === "1";

// LIVENESS (#25): the poller serves no HTTP, so Kubernetes can't probe an endpoint. Instead the loop
// rewrites this heartbeat file at the end of EVERY settled cycle; the poller Deployment's exec
// livenessProbe restarts the pod once the file ages past ~2x the poll interval (a hung/zombie loop stops
// updating it). OPT-IN: only k8s sets POLLER_HEARTBEAT_FILE — a bare `tsx run.ts` (local/dev/smoke) sets
// nothing and writes no file. A write failure is logged, never thrown: it must not crash the loop, and
// if writes keep failing the probe will (correctly) trip a restart on its own.
const HEARTBEAT_FILE = process.env.POLLER_HEARTBEAT_FILE ?? "";

function writeHeartbeat(): void {
  // Metrics gauge is always set (a settled-cycle liveness signal Prometheus can alert on), independent of
  // the k8s heartbeat FILE — which is opt-in via POLLER_HEARTBEAT_FILE and drives the exec livenessProbe.
  setHeartbeat(Date.now() / 1000);
  if (!HEARTBEAT_FILE) return;
  try {
    writeFileSync(HEARTBEAT_FILE, `${new Date().toISOString()}\n`);
  } catch (err) {
    log.error({ err, file: HEARTBEAT_FILE }, "heartbeat write failed");
  }
}

type Summary = Record<string, unknown>;

/** Put a pass summary's top-level numbers and booleans on the current span, as `summary.<field>`. */
const annotateSummary = (summary: unknown) =>
  Effect.sync(() =>
    summary && typeof summary === "object"
      ? Object.entries(summary as Summary).filter(
          ([, v]) => typeof v === "number" || typeof v === "boolean",
        )
      : [],
  ).pipe(
    Effect.flatMap((fields) =>
      Effect.forEach(fields, ([k, v]) =>
        Effect.annotateCurrentSpan(`summary.${k}`, v),
      ),
    ),
  );

/**
 * One ISOLATED pass: run it in its own span, record its result, and turn a failure into a metric + error
 * log so it can never starve the passes after it (fix B2). The span ends with the failure's status before
 * the failure is swallowed, so a failed pass still shows red in a trace.
 */
const pass = <A>(
  name: string,
  failureLabel: Parameters<typeof recordPollPassFailure>[0],
  failureMessage: string,
  run: () => Promise<A>,
  done: (result: A) => void | Promise<void>,
) =>
  Effect.tryPromise({ try: run, catch: (cause) => cause }).pipe(
    Effect.tap((result) => annotateSummary(result)),
    // `done` (logging, metrics, follow-up reads) can fail too; that is a pass failure like any other.
    Effect.tap((result) =>
      Effect.tryPromise({
        try: async () => done(result),
        catch: (cause) => cause,
      }),
    ),
    Effect.withSpan(`poll.pass.${name}`),
    Effect.asVoid,
    Effect.catch((err) =>
      Effect.sync(() => {
        recordPollPassFailure(failureLabel);
        log.error({ err }, failureMessage);
      }),
    ),
  );

const program = Effect.gen(function* () {
  regsApiKey(); // fail loudly on a missing key before we enter the loop

  // Resources, each closed by its own finalizer when the program ends (reverse order of opening).
  const sql = yield* Effect.acquireRelease(
    Effect.sync(() => createClient()),
    (c) => Effect.promise(() => c.end({ timeout: 5 })),
  );
  // The cycle lock lives on its own one-connection session (cycle-lock.ts explains why not sql.reserve()).
  const lockSession = yield* Effect.acquireRelease(
    Effect.sync(() => createSessionClient()),
    (c) => Effect.promise(() => c.end({ timeout: 5 })),
  );
  // Expose /metrics so an in-cluster Prometheus can scrape the poller (which serves no other HTTP). Not in
  // run-once mode: a process that exits after one cycle is never scraped, and binding the port could
  // collide with a live poller on the same host. Bound the drain: close() alone waits for open sockets, so
  // a keep-alive scrape could hang past the grace period; terminate connections first (Node >= 18).
  if (!ONCE) {
    yield* Effect.acquireRelease(
      Effect.sync(() => startMetricsServer()),
      (server) =>
        Effect.callback<void>((resume) => {
          server.closeAllConnections();
          server.close(() => resume(Effect.void));
        }),
    );
  }
  // Construct the adjudicator ONCE (not per cycle) so its observability tracer — and, when Langfuse is
  // configured, the long-lived Langfuse client — is reused across cycles and flushed on shutdown (best-
  // effort; shutdown() swallows its own errors). No CLOUDFLARE_AI_TOKEN (or ADJUDICATOR=off) → NullAdjudicator.
  const adjudicator = yield* Effect.acquireRelease(
    Effect.sync(() => selectAdjudicator()),
    (a) => Effect.promise(async () => a.tracer?.shutdown()),
  );

  // SEQUENTIAL single-writer cycle: FR discovery FIRST (so its regs_document_id handoff is visible to the
  // SAME cycle's Regs re-poll pass), then the rest in the order the header explains. Every pass is
  // isolated (see `pass`), and `Effect.gen` runs them one after another — never add `concurrency` here.
  const passes = Effect.gen(function* () {
    yield* pass(
      "fr",
      "fr",
      "fr poll failed",
      () => pollFrOnce(sql),
      (fr) => {
        log.info({ summary: fr }, "fr poll cycle");
        recordFrPoll(fr);
      },
    );
    yield* pass(
      "regs",
      "regs",
      "regs poll failed",
      () => pollRegsOnce(sql),
      (regs) => {
        log.info({ summary: regs }, "regs poll cycle");
        recordRegsPoll(regs);
      },
    );
    // 2b — GovInfo text for FR amendment documents (ADR 0016): after FR ingest, before the chain pass.
    yield* pass(
      "govinfo",
      "govinfo",
      "govinfo sweep failed",
      () => govinfoSweepOnce(sql, new Date()),
      (govinfo) => log.info({ summary: govinfo }, "govinfo sweep cycle"),
    );
    // 3 — cross_window (chain) reconcile sweep (derive-over-derived; see header).
    yield* pass(
      "chain",
      "chain",
      "chain reconcile failed",
      () => chainReconcileOnce(sql, new Date(), { adjudicator }),
      (chain) => {
        log.info({ summary: chain }, "chain reconcile cycle");
        recordChainCycle(chain);
      },
    );
    // 3b — reconcile-v2.4: re-derive the originals of the confident links. A moved close is logged loudly.
    yield* pass(
      "amended_originals",
      "amended_originals",
      "amended originals re-derive failed",
      () => rederiveChainOriginals(sql, new Date()),
      (originals) => {
        if (originals.versionBumped > 0) {
          log.warn({ summary: originals }, "amended originals MOVED a close");
        } else {
          log.info({ summary: originals }, "amended originals cycle");
        }
      },
    );
    // 4 — status refresh (#107), BEFORE verify. A status flip must never move the close: log it loudly.
    yield* pass(
      "status_refresh",
      "status_refresh",
      "status refresh failed",
      () => refreshStaleOpenWindows(sql),
      (refresh) => {
        if (refresh.versionBumped > 0) {
          log.warn({ summary: refresh }, "status refresh MOVED a close");
        } else {
          log.info({ summary: refresh }, "status refresh cycle");
        }
        recordStatusRefresh(refresh);
      },
    );
    // 5 — post-close verification (slice V); the headline gauge is recomputed from SQL each cycle.
    yield* pass(
      "verify",
      "verify",
      "verify pass failed",
      () => verifyOnce(sql),
      async (verify) => {
        log.info({ summary: verify }, "verify cycle");
        recordVerifyCycle(verify);
        const { ratio, sample } = await highCorrectRatio90d(sql);
        setAccuracyHighRatio(ratio, sample);
        log.debug({ ratio, sample }, "accuracy high-ratio 90d rollup");
      },
    );
    // 6 — review-queue observability (Slice R, PR-R4). READ-ONLY; last, it reads what every pass wrote.
    yield* pass(
      "queue_stats",
      "queue_stats",
      "review queue stats failed",
      () => reviewQueueStats(sql),
      (queue) => {
        log.info({ summary: queue }, "review queue stats");
        recordReviewQueue(queue);
      },
    );
  });

  let cycleFailed = false; // set when a cycle could not run at all (run-once mode exits 1 on it)

  // One cycle under the CROSS-PROCESS SINGLE WRITER lock (cycle-lock.ts). A busy lock SKIPS the cycle
  // rather than queueing behind it — the next scheduled cycle picks the work up.
  const tick = Effect.gen(function* () {
    const cycleStart = Date.now();
    const outcome = yield* cycleLock(lockSession, passes, {
      // Neon scales to zero after 5 minutes without activity; keep it awake while this cycle runs.
      onHeartbeatError: (err) => log.warn({ err }, "cycle lock session error"),
    }).pipe(
      Effect.tap((o) => Effect.annotateCurrentSpan("skipped", !o.acquired)),
      Effect.withSpan("poll.cycle", { attributes: { once: ONCE } }),
      // Anything outside the isolated passes (taking the lock, a lost DB connection) must not kill the
      // scheduler. In run-once mode it is the one failure that sets a non-zero exit code.
      Effect.catch((err) =>
        Effect.sync(() => {
          cycleFailed = true;
          log.error({ err }, "poll cycle failed");
          return null;
        }),
      ),
    );
    if (outcome && !outcome.acquired) {
      log.warn("poll cycle skipped: another process holds the poll-cycle lock");
    }
    // A skipped cycle did no work, so it must not drag the cycle-duration histogram toward zero.
    if (!outcome || outcome.acquired) {
      observePollCycle((Date.now() - cycleStart) / 1000);
    }
    // Mark this cycle SETTLED (liveness #25) — even after a pass-level failure, which is isolated and must
    // not restart the pod. Only a loop that never gets here (hung inside a pass) lets the file go stale.
    writeHeartbeat();
  }).pipe(
    // A started cycle always finishes: a SIGTERM waits for it (then the finalizers drain everything).
    Effect.uninterruptible,
  );

  // Seed the heartbeat at startup so the file exists the instant the container is up — the first cycle
  // may run longer than the probe's initialDelay, and an absent file reads as "not alive" (restart).
  writeHeartbeat();
  if (ONCE) {
    yield* tick;
  } else {
    yield* Effect.repeat(tick, Schedule.spaced(INTERVAL_MS));
  }
  return cycleFailed ? 1 : 0;
}).pipe(Effect.scoped, Effect.provide(telemetryLayer("docketclock-poller")));

// SIGTERM/SIGINT interrupt the program (see SHUTDOWN in the header). Signals are handled once each; a
// second signal does nothing extra, the drain is already under way.
const interrupt = new AbortController();
for (const signal of ["SIGTERM", "SIGINT"] as const) {
  process.once(signal, () => {
    log.info({ signal }, "draining poll scheduler");
    interrupt.abort();
  });
}

const exit = await Effect.runPromiseExit(program, { signal: interrupt.signal });
if (exit._tag === "Success") {
  process.exit(exit.value);
} else if (interrupt.signal.aborted) {
  process.exit(0); // drained on a signal
} else {
  log.error({ err: Cause.squash(exit.cause) }, "poll scheduler failed");
  process.exit(1);
}
