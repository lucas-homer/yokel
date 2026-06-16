/**
 * poll.smoke.ts — a one-shot LIVE proof of the differential poll loop (NOT a gated test; it hits the
 * network and needs a key + a DB). Self-loads the repo-root .env, runs migrations to guarantee the
 * poll_cursor table exists, then runs ONE pollRegsOnce against the real Regs.gov v4 API with the real
 * deps and prints the resulting PollSummary.
 *
 * Gated by REGS_API_KEY (and DATABASE_URL). Run:
 *   DATABASE_URL=postgres://... pnpm --filter @yokel/docketclock smoke:poll
 */
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { createClient } from "../db/client.js";
import { runMigrations } from "../db/migrate.js";
import { regsApiKey } from "../sources/regulations-gov.js";
import { pollRegsOnce } from "./poll.js";

const envPath = fileURLToPath(new URL("../../../../.env", import.meta.url));
if (existsSync(envPath)) process.loadEnvFile(envPath);

async function main(): Promise<void> {
  regsApiKey(); // fail loudly on a missing key
  const sql = createClient();
  try {
    await runMigrations(sql);
    console.log(
      "running one live poll cycle against the real Regs.gov v4 API…",
    );
    const summary = await pollRegsOnce(sql);
    console.log("\n=== PollSummary ===");
    console.log(JSON.stringify(summary, null, 2));
  } finally {
    await sql.end();
  }
}

main().catch((err) => {
  console.error("smoke:poll failed:", err);
  process.exit(1);
});
