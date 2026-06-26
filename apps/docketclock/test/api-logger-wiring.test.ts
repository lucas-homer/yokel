/**
 * api-logger-wiring.test.ts — covers the Fastify `logger:true` branch (PR-A1).
 *
 * The sibling api.test.ts only exercises buildServer with `logger` OMITTED (silent default). The
 * `logger:true` branch — which attaches the real pino `loggerInstance` (component=api) and relies on the
 * `/healthz` route's `logLevel:"silent"` — is NEVER run there. This test runs that real branch and proves:
 *
 *   (1) loggerInstance attaches at runtime (not just typecheck): /readyz emits a structured request/response
 *       log line tagged component=api.
 *   (2) `logLevel:"silent"` on /healthz suppresses its request log line but does NOT change the RESPONSE:
 *       /healthz still returns 200 with {status:"ok"}.
 *   (3) /readyz still 503s on a dead DB AND still logs.
 *
 * MECHANISM: pino writes to fd 1 via SonicBoom, bypassing process.stdout.write — so we can't monkeypatch
 * in-process. Instead this file re-execs ITSELF as a `--worker`: the worker builds the real server with
 * logger:true and injects the routes; its stdout (the pino NDJSON) is captured by the parent over a pipe.
 */
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { buildServer } from "../src/api/server.js";
import { createClient } from "../src/db/client.js";

const SELF = fileURLToPath(import.meta.url);

// ── WORKER ────────────────────────────────────────────────────────────────────────────────────────────
if (process.argv.includes("--worker")) {
  const sql = createClient();
  // A client pointed at a dead port → `select 1` throws → /readyz 503 (same trick api.test.ts uses).
  const deadSql = createClient(
    "postgres://postgres:postgres@127.0.0.1:1/docketclock",
  );
  const app = buildServer(sql, { apiKeys: ["k"], logger: true });
  const deadApp = buildServer(deadSql, { apiKeys: ["k"], logger: true });

  const health = await app.inject({ method: "GET", url: "/healthz" });
  const ready = await app.inject({ method: "GET", url: "/readyz" });
  const ready503 = await deadApp.inject({ method: "GET", url: "/readyz" });

  // Marker line the parent parses for response correctness (distinct from pino's own JSON lines).
  process.stdout.write(
    "\n__MARKER__" +
      JSON.stringify({
        healthStatus: health.statusCode,
        healthBody: health.json(),
        readyStatus: ready.statusCode,
        ready503Status: ready503.statusCode,
        ready503Body: ready503.json(),
      }) +
      "\n",
  );
  // Flush pino + exit cleanly.
  await app.close();
  await deadApp.close();
  await sql.end({ timeout: 1 });
  await deadSql.end({ timeout: 1 });
  process.exit(0);
}

// ── PARENT ────────────────────────────────────────────────────────────────────────────────────────────
let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = ""): void {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

const res = spawnSync("pnpm", ["exec", "tsx", SELF, "--worker"], {
  cwd: fileURLToPath(new URL("..", import.meta.url)),
  env: process.env,
  encoding: "utf8",
});

const stdout = res.stdout ?? "";
const markerLine = stdout.split("\n").find((l) => l.startsWith("__MARKER__"));
if (!markerLine) {
  console.error("worker produced no marker; stderr:\n", res.stderr);
  console.error("stdout:\n", stdout);
  process.exit(1);
}
const marker = JSON.parse(markerLine.slice("__MARKER__".length)) as {
  healthStatus: number;
  healthBody: { status: string; db: string };
  readyStatus: number;
  ready503Status: number;
  ready503Body: { status: string; db: string };
};

// Parse the pino NDJSON lines the worker emitted (everything that is valid JSON with a numeric level).
type LogLine = {
  level?: number;
  component?: string;
  req?: { url?: string };
  msg?: string;
};
const logLines: LogLine[] = stdout
  .split("\n")
  .filter((l) => l.trim().startsWith("{"))
  .map((l) => {
    try {
      return JSON.parse(l) as LogLine;
    } catch {
      return {} as LogLine;
    }
  })
  .filter((o) => typeof o.level === "number");

const urlsLogged = logLines
  .map((l) => l.req?.url)
  .filter((u): u is string => typeof u === "string");

// (2) response NOT suppressed by logLevel:silent
assert(
  "/healthz still returns 200 with logLevel:silent",
  marker.healthStatus === 200 && marker.healthBody.status === "ok",
  JSON.stringify(marker.healthBody),
);
// (1)+(3) readyz logs + 503s on dead DB
assert(
  "/readyz returns 200 when DB up",
  marker.readyStatus === 200,
  String(marker.readyStatus),
);
assert(
  "/readyz returns 503 + status:unavailable on dead DB (response intact under real logger)",
  marker.ready503Status === 503 && marker.ready503Body.status === "unavailable",
  JSON.stringify(marker.ready503Body),
);
// (1) loggerInstance actually attached — at least one structured line tagged component=api
assert(
  "request logs are structured and tagged component=api",
  logLines.some((l) => l.component === "api"),
  `componentsSeen=${JSON.stringify([...new Set(logLines.map((l) => l.component))])}`,
);
// (2) /healthz request line suppressed; (1) /readyz request line present
assert(
  "/healthz produced NO request log line (logLevel:silent)",
  !urlsLogged.includes("/healthz"),
  `urlsLogged=${JSON.stringify(urlsLogged)}`,
);
assert(
  "/readyz DID produce a request log line (default level)",
  urlsLogged.includes("/readyz"),
  `urlsLogged=${JSON.stringify(urlsLogged)}`,
);

console.log("\n=== api-logger-wiring results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL PASS" : `${failures} FAILED`} (${out.length} assertions)`,
);
process.exit(failures === 0 ? 0 : 1);
