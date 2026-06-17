/**
 * run.ts — the THIN Delivery API entrypoint (NOT the testable core; buildServer is). Self-loads the
 * repo-root .env (like the smokes / poll/run.ts) so DOCKETCLOCK_API_KEYS + DATABASE_URL load, opens the
 * Postgres pool, builds the server, and binds it. Where this runs (a Node process on the Mac Mini, a
 * container in-cluster) is ops and out of scope — buildServer is fully injectable and never .listen()s
 * itself, so tests drive it via app.inject without a port.
 *
 * SHUTDOWN mirrors poll/run.ts: SIGTERM/SIGINT close the HTTP server (drain in-flight requests) THEN end
 * the SQL pool, so a container restart never severs a mid-request DB read.
 *
 * Run: DATABASE_URL=... DOCKETCLOCK_API_KEYS=key1,key2 pnpm --filter @yokel/docketclock api
 */
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { createClient } from "../db/client.js";
import { buildServer } from "./server.js";

const envPath = fileURLToPath(new URL("../../../../.env", import.meta.url));
if (existsSync(envPath)) process.loadEnvFile(envPath);

async function main(): Promise<void> {
  const sql = createClient();
  const app = buildServer(sql, { logger: true });

  let stopping = false;
  async function shutdown(signal: string): Promise<void> {
    if (stopping) return;
    stopping = true;
    app.log.info(`${signal} — draining the API server…`);
    await app.close(); // stop accepting + drain in-flight requests
    await sql.end({ timeout: 5 });
    process.exit(0);
  }
  process.on("SIGTERM", () => void shutdown("SIGTERM"));
  process.on("SIGINT", () => void shutdown("SIGINT"));

  const port = Number(process.env.PORT) || 8080;
  await app.listen({ port, host: "0.0.0.0" });
}

main().catch((err) => {
  console.error("API server failed to start:", err);
  process.exit(1);
});
