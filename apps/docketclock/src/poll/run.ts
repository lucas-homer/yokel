/**
 * run.ts — the THIN scheduler around pollRegsOnce (NOT the testable core). Self-loads the repo-root
 * .env (like the smokes), then calls pollRegsOnce with the real deps on a fixed interval (default 15
 * min, per docs/architecture/docketclock.md "1. Discover"), logging each PollSummary.
 *
 * Deliberately tiny: where this actually runs (pg_cron / a Node cron / a worker on the Mac Mini) is ops
 * and out of scope. The poll CORE is fully deterministic/injectable; only this entrypoint touches the
 * live network and the wall clock. Guarded by regsApiKey() so a misconfig fails loudly before the loop.
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

  async function tick(): Promise<void> {
    try {
      const summary = await pollRegsOnce(sql);
      console.log(
        `[${new Date().toISOString()}] poll:`,
        JSON.stringify(summary),
      );
    } catch (err) {
      // A whole-cycle failure (e.g. DB down) must not kill the scheduler — log and retry next interval.
      console.error(`[${new Date().toISOString()}] poll cycle failed:`, err);
    }
  }

  await tick();
  setInterval(() => void tick(), INTERVAL_MS);
}

main().catch((err) => {
  console.error("poll scheduler failed to start:", err);
  process.exit(1);
});
