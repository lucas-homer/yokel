/**
 * run.ts — the THIN scheduler around the UNIFIED single-writer poll cycle (NOT the testable core).
 * Self-loads the repo-root .env (like the smokes), then on a fixed interval (default 15 min, per
 * docs/architecture/docketclock.md "1. Discover") runs, SEQUENTIALLY in ONE process:
 *
 *   1. pollFrOnce  — FR open-comment discovery (FIRST), then
 *   2. pollRegsOnce — Regs.gov differential + re-poll pass, then
 *   3. chainReconcileOnce — the cross_window (chain) reconcile sweep (#31),
 *
 * logging ALL THREE summaries (labelled `fr:`, `regs:`, `chain:`).
 *
 * WHY CHAIN RUNS LAST (a derive-over-derived pass): the chain pass reads the participation_windows +
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
 * SCHEDULING: a self-rescheduling setTimeout (NOT setInterval), so the next cycle is queued only AFTER
 * the current one settles. A cycle that runs longer than the interval can therefore never overlap itself
 * — overlapping runs would race the cursor and violate the single-writer assumption above. SHUTDOWN:
 * SIGTERM/SIGINT drain — stop scheduling, let an in-flight cycle finish, close the pool, then exit
 * cleanly (so a container restart never kills a mid-poll write).
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

const { createClient } = await import("../db/client.js");
const { componentLogger } = await import("../log.js");
const { regsApiKey } = await import("../sources/regulations-gov.js");
const { chainReconcileOnce } = await import("../reconcile/persist.js");
const { pollFrOnce } = await import("./fr-poll.js");
const { pollRegsOnce } = await import("./poll.js");

const log = componentLogger("poller");

const INTERVAL_MS = Number(process.env.POLL_INTERVAL_MS) || 15 * 60_000;

// LIVENESS (#25): the poller serves no HTTP, so Kubernetes can't probe an endpoint. Instead the loop
// rewrites this heartbeat file at the end of EVERY settled cycle; the poller Deployment's exec
// livenessProbe restarts the pod once the file ages past ~2x the poll interval (a hung/zombie loop stops
// updating it). OPT-IN: only k8s sets POLLER_HEARTBEAT_FILE — a bare `tsx run.ts` (local/dev/smoke) sets
// nothing and writes no file. A write failure is logged, never thrown: it must not crash the loop, and
// if writes keep failing the probe will (correctly) trip a restart on its own.
const HEARTBEAT_FILE = process.env.POLLER_HEARTBEAT_FILE ?? "";

function writeHeartbeat(): void {
  if (!HEARTBEAT_FILE) return;
  try {
    writeFileSync(HEARTBEAT_FILE, `${new Date().toISOString()}\n`);
  } catch (err) {
    log.error({ err, file: HEARTBEAT_FILE }, "heartbeat write failed");
  }
}

async function main(): Promise<void> {
  regsApiKey(); // fail loudly on a missing key before we enter the loop
  const sql = createClient();

  let timer: NodeJS.Timeout | null = null;
  let running = false; // re-entrancy guard (belt-and-braces alongside the self-reschedule)
  let stopping = false;

  async function tick(): Promise<void> {
    if (running) return; // never overlap a still-running cycle
    running = true;
    try {
      // SEQUENTIAL single-writer cycle: FR discovery FIRST (so its regs_document_id handoff is visible
      // to the SAME cycle's Regs re-poll pass), then the Regs differential + re-poll pass.
      //
      // ISOLATED PASSES (fix B2): the two passes are independently try/caught so an FR-side failure
      // (e.g. FR returns an HTTP 400 / is down) is logged but DOES NOT starve the Regs withdrawal-
      // detection pass that cycle, and vice-versa. Each summary is logged independently.
      try {
        const fr = await pollFrOnce(sql);
        log.info({ summary: fr }, "fr poll cycle");
      } catch (err) {
        log.error({ err }, "fr poll failed");
      }
      try {
        const regs = await pollRegsOnce(sql);
        log.info({ summary: regs }, "regs poll cycle");
      } catch (err) {
        log.error({ err }, "regs poll failed");
      }
      // 3rd pass — cross_window (chain) reconcile sweep. Runs LAST (derive-over-derived; see header) and
      // is INDEPENDENTLY try/caught so a chain failure cannot affect the FR/Regs passes (and vice-versa).
      try {
        const chain = await chainReconcileOnce(sql);
        log.info({ summary: chain }, "chain reconcile cycle");
      } catch (err) {
        log.error({ err }, "chain reconcile failed");
      }
    } catch (err) {
      // Belt-and-braces: anything outside the two passes (should be nothing) must not kill the scheduler.
      log.error({ err }, "poll cycle failed");
    } finally {
      running = false;
      // Mark this cycle SETTLED (liveness #25). Written here in `finally`, not on full success: a pass-
      // level failure (FR down, Regs 4xx) is already isolated above and must NOT restart the pod — the
      // loop is still healthily cycling. Only a loop that never reaches this point (hung inside a pass,
      // awaiting forever) lets the file go stale and earns a restart.
      writeHeartbeat();
      // Queue the NEXT cycle only now that this one has settled — self-rescheduling, never overlapping.
      if (!stopping) timer = setTimeout(() => void tick(), INTERVAL_MS);
    }
  }

  // Drain on shutdown: stop scheduling, wait for any in-flight cycle, close the pool, exit cleanly.
  async function shutdown(signal: string): Promise<void> {
    if (stopping) return;
    stopping = true;
    log.info({ signal }, "draining poll scheduler");
    if (timer) clearTimeout(timer);
    // Wait out an in-flight cycle (bounded poll — no unbounded work), then release the pool.
    while (running) await new Promise((r) => setTimeout(r, 100));
    await sql.end({ timeout: 5 });
    process.exit(0);
  }
  process.on("SIGTERM", () => void shutdown("SIGTERM"));
  process.on("SIGINT", () => void shutdown("SIGINT"));

  // Seed the heartbeat at startup so the file exists the instant the container is up — the first cycle
  // may run longer than the probe's initialDelay, and an absent file reads as "not alive" (restart).
  writeHeartbeat();
  await tick();
}

main().catch((err) => {
  log.error({ err }, "poll scheduler failed to start");
  process.exit(1);
});
