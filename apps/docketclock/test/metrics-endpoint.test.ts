/**
 * metrics-endpoint.test.ts — PR-B1 (observability slice B): the actual HTTP SURFACES that expose metrics,
 * which the pure-registry unit tests can't reach. Covers both:
 *   • the Fastify `/metrics` route + the onResponse HTTP hook (via app.inject — NO DB: the counted route
 *     401s before any query, and /metrics/probe routes never touch sql), and
 *   • the poller's standalone node:http listener (start → fetch /metrics + a 404 → drain).
 * Repo test style: hand-rolled assert + out[] + process.exit.
 */
import { buildServer } from "../src/api/server.js";
import { startMetricsServer } from "../src/metrics-server.js";
import type { Sql } from "../src/db/client.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

// A stub Sql: the routes exercised here (/metrics + an auth-rejected data route) never touch the DB, so no
// real connection is needed. buildServer does not query at construction.
const sql = {} as unknown as Sql;

// ── Fastify /metrics route + onResponse hook ─────────────────────────────────────────────────────────
{
  const app = buildServer(sql, { apiKeys: ["k"] });
  await app.ready();

  const m1 = await app.inject({ method: "GET", url: "/metrics" });
  assert(
    "GET /metrics → 200 with prom content-type",
    m1.statusCode === 200 &&
      (m1.headers["content-type"] ?? "").toString().includes("text/plain"),
    `${m1.statusCode} ${m1.headers["content-type"]}`,
  );
  assert(
    "GET /metrics body renders an app series",
    m1.body.includes("docketclock_"),
  );

  // An auth-failing data request (no x-api-key) 401s WITHOUT hitting the DB — and the onResponse hook counts
  // it by route pattern.
  const w = await app.inject({ method: "GET", url: "/v1/windows" });
  assert("GET /v1/windows without key → 401", w.statusCode === 401);

  const m2 = await app.inject({ method: "GET", url: "/metrics" });
  assert(
    "onResponse hook counted the data route: http_requests_total{route=/v1/windows,status=401}",
    /docketclock_http_requests_total\{[^}]*route="\/v1\/windows"[^}]*status="401"[^}]*\}\s+1/.test(
      m2.body,
    ),
  );
  assert(
    "/metrics route is NOT self-counted (excluded from the hook)",
    !/docketclock_http_requests_total\{[^}]*route="\/metrics"/.test(m2.body),
  );

  await app.close();
}

// ── Poller standalone metrics listener ───────────────────────────────────────────────────────────────
{
  const PORT = 9531;
  const server = startMetricsServer(PORT);
  await new Promise<void>((resolve) => {
    if (server.listening) resolve();
    else server.once("listening", () => resolve());
  });

  const ok = await fetch(`http://localhost:${PORT}/metrics`);
  const body = await ok.text();
  assert(
    "poller GET /metrics → 200 + prom content-type + app series",
    ok.status === 200 &&
      (ok.headers.get("content-type") ?? "").includes("text/plain") &&
      body.includes("docketclock_"),
    `${ok.status}`,
  );

  const nf = await fetch(`http://localhost:${PORT}/nope`);
  assert("poller non-/metrics path → 404", nf.status === 404);

  server.closeAllConnections();
  await new Promise<void>((resolve) => server.close(() => resolve()));
}

console.log("\n=== metrics-endpoint results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
