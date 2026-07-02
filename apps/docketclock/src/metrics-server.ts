/**
 * metrics-server.ts — a minimal HTTP `/metrics` listener for the POLLER (Observability Slice B, PR-B1).
 *
 * The API process exposes metrics on its Fastify server; the poller process runs no HTTP server, so it can't
 * otherwise be scraped. This is that endpoint: a bare node:http server that serves the same process registry
 * (src/metrics.ts) as Prometheus text. Listens on METRICS_PORT (default 9464 — the OpenMetrics convention),
 * bound to 0.0.0.0 so an in-cluster Prometheus can reach it. Only GET /metrics (and /) return the registry;
 * everything else 404s. A render error never crashes the poller.
 */
import { createServer, type Server } from "node:http";
import { componentLogger } from "./log.js";
import { renderMetrics, metricsContentType } from "./metrics.js";

const log = componentLogger("metrics");
const DEFAULT_PORT = 9464;

export function startMetricsServer(
  port: number = Number(process.env.METRICS_PORT) || DEFAULT_PORT,
): Server {
  const server = createServer((req, res) => {
    if (req.method === "GET" && (req.url === "/metrics" || req.url === "/")) {
      renderMetrics()
        .then((body) => {
          res.writeHead(200, { "content-type": metricsContentType });
          res.end(body);
        })
        .catch((err) => {
          log.error({ err }, "metrics render failed");
          res.writeHead(500);
          res.end();
        });
      return;
    }
    res.writeHead(404);
    res.end();
  });
  // A listen/port error must be logged, not thrown into the process (the poll loop keeps running without it).
  server.on("error", (err) => log.error({ err, port }, "metrics server error"));
  server.listen(port, "0.0.0.0", () =>
    log.info({ port }, "metrics server listening"),
  );
  return server;
}
