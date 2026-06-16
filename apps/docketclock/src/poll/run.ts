/**
 * run.ts — the THIN scheduler around pollRegsOnce (NOT the testable core). Self-loads the repo-root
 * .env (like the smokes), then calls pollRegsOnce with the real deps on a fixed interval (default 15
 * min, per docs/architecture/docketclock.md "1. Discover"), logging each PollSummary.
 *
 * Deliberately tiny: where this actually runs (pg_cron / a Node cron / a worker on the Mac Mini) is ops
 * and out of scope. The poll CORE is fully deterministic/injectable; only this entrypoint touches the
 * live network and the wall clock. Guarded by regsApiKey() so a misconfig fails loudly before the loop.
 *
 * SCHEDULING: a self-rescheduling setTimeout (NOT setInterval), so the next cycle is queued only AFTER
 * the current one settles. A poll that runs longer than the interval can therefore never overlap itself
 * — overlapping pollRegsOnce runs would race the cursor and violate the single-writer assumption the
 * ingest/reconcile path relies on. SHUTDOWN: SIGTERM/SIGINT drain — stop scheduling, let an in-flight
 * cycle finish, close the pool, then exit cleanly (so a container restart never kills a mid-poll write).
 *
 * Run: DATABASE_URL=... pnpm --filter @yokel/docketclock tsx src/poll/run.ts
 */
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { createClient } from "../db/client.js";
import { regsApiKey } from "../sources/regulations-gov.js";
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
      const summary = await pollRegsOnce(sql);
      console.log(
        `[${new Date().toISOString()}] poll:`,
        JSON.stringify(summary),
      );
    } catch (err) {
      // A whole-cycle failure (e.g. DB down) must not kill the scheduler — log and retry next interval.
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
