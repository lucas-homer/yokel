/**
 * run.ts — the THIN scheduler around the UNIFIED single-writer poll cycle (NOT the testable core).
 * Self-loads the repo-root .env (like the smokes), then on a fixed interval (default 15 min, per
 * docs/architecture/docketclock.md "1. Discover") runs, SEQUENTIALLY in ONE process:
 *
 *   1. pollFrOnce  — FR open-comment discovery (FIRST), then
 *   2. pollRegsOnce — Regs.gov differential + re-poll pass,
 *
 * logging BOTH summaries (labelled `fr:` and `regs:`).
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
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { createClient } from "../db/client.js";
import { regsApiKey } from "../sources/regulations-gov.js";
import { pollFrOnce } from "./fr-poll.js";
import { pollRegsOnce } from "./poll.js";

const envPath = fileURLToPath(new URL("../../../../.env", import.meta.url));
if (existsSync(envPath)) process.loadEnvFile(envPath);

const INTERVAL_MS = Number(process.env.POLL_INTERVAL_MS) || 15 * 60_000;

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
        console.log(`[${new Date().toISOString()}] fr:`, JSON.stringify(fr));
      } catch (err) {
        console.error(`[${new Date().toISOString()}] fr poll failed:`, err);
      }
      try {
        const regs = await pollRegsOnce(sql);
        console.log(
          `[${new Date().toISOString()}] regs:`,
          JSON.stringify(regs),
        );
      } catch (err) {
        console.error(`[${new Date().toISOString()}] regs poll failed:`, err);
      }
    } catch (err) {
      // Belt-and-braces: anything outside the two passes (should be nothing) must not kill the scheduler.
      console.error(`[${new Date().toISOString()}] poll cycle failed:`, err);
    } finally {
      running = false;
      // Queue the NEXT cycle only now that this one has settled — self-rescheduling, never overlapping.
      if (!stopping) timer = setTimeout(() => void tick(), INTERVAL_MS);
    }
  }

  // Drain on shutdown: stop scheduling, wait for any in-flight cycle, close the pool, exit cleanly.
  async function shutdown(signal: string): Promise<void> {
    if (stopping) return;
    stopping = true;
    console.log(
      `[${new Date().toISOString()}] ${signal} — draining poll scheduler…`,
    );
    if (timer) clearTimeout(timer);
    // Wait out an in-flight cycle (bounded poll — no unbounded work), then release the pool.
    while (running) await new Promise((r) => setTimeout(r, 100));
    await sql.end({ timeout: 5 });
    process.exit(0);
  }
  process.on("SIGTERM", () => void shutdown("SIGTERM"));
  process.on("SIGINT", () => void shutdown("SIGINT"));

  await tick();
}

main().catch((err) => {
  console.error("poll scheduler failed to start:", err);
  process.exit(1);
});
