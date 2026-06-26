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

// Load the repo-root .env BEFORE importing anything that reads env at module-evaluation time — notably the
// logger, whose level is locked in from LOG_LEVEL the moment log.ts is first imported. A static `import`
// evaluates (and would build the logger) before this file's body runs, so the env-touching modules are
// imported DYNAMICALLY below, AFTER the env is loaded — this is what lets LOG_LEVEL in .env take effect in
// local dev. In k8s LOG_LEVEL is a real pod env var, so it works there regardless.
const envPath = fileURLToPath(new URL("../../../../.env", import.meta.url));
if (existsSync(envPath)) process.loadEnvFile(envPath);

const { createClient } = await import("../db/client.js");
const { componentLogger } = await import("../log.js");
const { buildServer } = await import("./server.js");

const log = componentLogger("api");

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
  log.error({ err }, "API server failed to start");
  process.exit(1);
});
