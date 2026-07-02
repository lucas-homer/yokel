/**
 * server.ts — buildServer(sql, opts?): the Delivery API read surface as a Fastify 5 instance.
 *
 * The accumulated read model, over HTTP: participation windows + the live conflict proof feed, with
 * API-key auth, a Zod→OpenAPI 3.1 spec published at /openapi.json, and the contract response envelope
 * (disclaimer + api_version + request_id) on EVERY response. The instance is returned WITHOUT .listen()
 * so tests drive it via app.inject (no real port/network) and run.ts owns the actual bind.
 *
 * ONE SOURCE OF TRUTH FOR SHAPES — fastify-type-provider-zod's validatorCompiler/serializerCompiler make
 * the SAME Zod schemas drive request validation AND response serialization, and @fastify/swagger's
 * jsonSchemaTransform converts those exact schemas into the published OpenAPI document. So the spec a
 * buyer inspects and the bytes we actually emit can never diverge (the plan's hard requirement). The
 * response schemas are the contract envelope factories apiItemEnvelope / apiListEnvelope, so even the
 * envelope is contract-driven, not hand-rolled.
 *
 * OCD-IDs CONTAIN SLASHES (ocd-participation-window/federal/2025-23266), which break a Fastify `:id`
 * param, so the detail route captures the id as a trailing WILDCARD (`/v1/windows/*`, read via
 * req.params['*']) and validates it with OcdId.safeParse.
 *
 * AUTH fails CLOSED: data routes require x-api-key ∈ the configured set; if NO keys are configured the
 * server 401s every data request and warns at startup (a misconfigured deploy must never serve open).
 * /healthz, /openapi.json and the swagger machinery are PUBLIC.
 *
 * DEFERRED (note, do NOT build here): webhooks/outbox, watchlist CRUD, GET /accuracy, RSS/ICS/CSV, FTS
 * ?q= search, MCP, and the `agency` window filter (no agency column — a reconcile-time projection
 * follow-up, not a docket-prefix hack). See queries.ts + the PR.
 */
import { randomUUID } from "node:crypto";
import fastifySwagger from "@fastify/swagger";
import {
  apiItemEnvelope,
  apiListEnvelope,
  API_VERSION,
  ConflictRecord,
  DISCLAIMER,
  Observation,
  OcdId,
  ParticipationWindow,
} from "@yokel/contracts";
import type {
  FastifyBaseLogger,
  FastifyError,
  FastifyInstance,
  FastifyReply,
  FastifyRequest,
} from "fastify";
import Fastify from "fastify";
import {
  jsonSchemaTransform,
  serializerCompiler,
  validatorCompiler,
  type ZodTypeProvider,
} from "fastify-type-provider-zod";
import { z } from "zod";
import type { Sql } from "../db/client.js";
import { componentLogger } from "../log.js";
import {
  observeHttp,
  setDbUp,
  renderMetrics,
  metricsContentType,
} from "../metrics.js";
import { itemEnvelope, listEnvelope } from "./envelope.js";
import {
  listConflicts,
  listWindows,
  getWindow,
  getWindowObservations,
} from "./queries.js";

export interface BuildServerOptions {
  /** The accepted API keys. Falls back to DOCKETCLOCK_API_KEYS (comma-separated) when omitted. */
  apiKeys?: string[];
  /**
   * Fastify logger toggle (off by default so tests stay quiet). When true, the configured pino instance
   * (tagged component=api, the shared root logger's child) is attached via Fastify 5's `loggerInstance`;
   * when false/omitted Fastify gets `logger: false` and stays SILENT — the test default is preserved.
   */
  logger?: boolean;
}

/** Parse DOCKETCLOCK_API_KEYS (comma-separated, whitespace-trimmed, empties dropped). */
function apiKeysFromEnv(): string[] {
  const raw = process.env.DOCKETCLOCK_API_KEYS ?? "";
  return raw
    .split(",")
    .map((k) => k.trim())
    .filter((k) => k.length > 0);
}

// ── response schemas (contract-driven) ──────────────────────────────────────────────────────────────
// The window DETAIL shape composes the FROZEN ParticipationWindow with its observations — built in the
// API layer by EXTENDING the contract schema (never modifying the contract). ParticipationWindow is a
// ZodEffects (superRefine), so reach through `.innerType()` to .extend(), then carry the field forward.
const WindowDetail = (
  ParticipationWindow as unknown as z.ZodEffects<z.ZodObject<z.ZodRawShape>>
)
  .innerType()
  .extend({ observations: z.array(Observation) });

const WindowListResponse = apiListEnvelope(ParticipationWindow);
const WindowDetailResponse = apiItemEnvelope(WindowDetail);
const ConflictListResponse = apiListEnvelope(ConflictRecord);

const HealthResponse = z.object({
  status: z.literal("ok"),
  db: z.enum(["ok", "down"]),
});

// /readyz is the READINESS surface (vs /healthz = liveness): it returns 503 when the DB ping fails, so
// Kubernetes pulls a DB-less pod out of the Service rotation instead of routing traffic into 500s.
const ReadyResponse = z.object({
  status: z.enum(["ok", "unavailable"]),
  db: z.enum(["ok", "down"]),
});

// The enveloped error shape (400/401/404/500) — also published in the spec so a buyer sees it. EVERY
// response carries the trio (disclaimer + api_version + request_id), errors included — the architecture
// invariant is non-negotiable, so the disclaimer is in the schema AND every error send below.
const ErrorResponse = z.object({
  error: z.object({ code: z.string(), message: z.string() }),
  disclaimer: z.string(),
  api_version: z.string(),
  request_id: z.string(),
});

// limit/offset: coerce + reject an explicit negative at the boundary (clean 400, not a 500). The
// clampLimit/clampOffset in queries.ts stays as defense-in-depth. `?limit=abc` → NaN fails .int() → 400.
const PageLimit = z.coerce.number().int().nonnegative().optional();
const PageOffset = z.coerce.number().int().nonnegative().optional();

const WindowListQuery = z.object({
  confidence: z.string().optional(),
  status: z.string().optional(),
  docket_id: z.string().optional(),
  // z.coerce.date ACCEPTS date-only (2026-06-16) and full ISO, REJECTS banana / 2026-13-99 / "" → a
  // clean 400 at the validator, so an Invalid Date can never be interpolated into the timestamptz bind.
  closes_before: z.coerce.date().optional(),
  closes_after: z.coerce.date().optional(),
  limit: PageLimit,
  offset: PageOffset,
});

const ConflictListQuery = z.object({
  ocd_id: z.string().optional(),
  limit: PageLimit,
  offset: PageOffset,
});

/**
 * The per-request id. Fastify's `req.id` (set by genReqId below to a UUID) IS the request_id — one id
 * shared by the envelope, the x-request-id header, AND Fastify's own log lines, so all three correlate
 * for support/tracing (we deliberately do NOT mint a second UUID).
 */
function requestId(req: FastifyRequest): string {
  return req.id;
}

export function buildServer(
  sql: Sql,
  opts: BuildServerOptions = {},
): FastifyInstance {
  // Fastify 5 takes a CONFIGURED logger via `loggerInstance` (NOT `logger:` — that option only accepts a
  // boolean or pino OPTIONS, never an instance). Preserve the silent-test escape hatch: with logger off
  // (the default) we pass `logger: false` so Fastify never constructs a logger; only when explicitly on do
  // we attach our pino child (component=api), so every request line is structured + tagged.
  // Cast the pino child to FastifyBaseLogger: a pino Logger satisfies it structurally, but passing the
  // concrete pino type would over-narrow Fastify's logger generic (pino's Logger requires msgPrefix),
  // making the returned instance not assignable to the declared FastifyInstance return type.
  const loggerOpt = opts.logger
    ? { loggerInstance: componentLogger("api") as FastifyBaseLogger }
    : { logger: false as const };
  const app = Fastify({
    ...loggerOpt,
    // genReqId mints req.id as a UUID — and that SAME id is reused for the envelope + x-request-id
    // header (see requestId()/the onRequest hook), so logs and responses share one correlatable id.
    genReqId: () => randomUUID(),
  }).withTypeProvider<ZodTypeProvider>();

  // Zod drives BOTH validation and serialization — the SAME schemas the spec is generated from.
  app.setValidatorCompiler(validatorCompiler);
  app.setSerializerCompiler(serializerCompiler);

  const apiKeys = opts.apiKeys ?? apiKeysFromEnv();
  if (apiKeys.length === 0) {
    // Fail CLOSED: with no keys configured every data request 401s. Warn loudly so a misconfigured
    // deploy is obvious rather than silently serving (or silently refusing) the design-partner surface.
    app.log.warn(
      "DocketClock API: NO API keys configured (opts.apiKeys / DOCKETCLOCK_API_KEYS empty) — " +
        "all data routes will 401 (failing CLOSED). Set DOCKETCLOCK_API_KEYS to serve.",
    );
  }
  const keySet = new Set(apiKeys);

  // @fastify/swagger + jsonSchemaTransform: the published OpenAPI 3.1 doc is generated from the Zod
  // schemas attached to each route — NOT a hand-rolled spec.
  void app.register(fastifySwagger, {
    openapi: {
      openapi: "3.1.0",
      info: { title: "DocketClock API", version: API_VERSION },
    },
    transform: jsonSchemaTransform,
  });

  // ── request_id + x-request-id header (every response) ──────────────────────────────────────────────
  app.addHook("onRequest", async (req, reply) => {
    // Echo the request's id (genReqId UUID) so the client sees the SAME id our envelope + logs use.
    reply.header("x-request-id", req.id);
  });

  // ── HTTP metrics (every response) ──────────────────────────────────────────────────────────────────
  // Label by the ROUTE PATTERN (req.routeOptions.url), never the raw path, so `/v1/windows/*` is one series
  // rather than one per OCD-id (unbounded cardinality). Skip the probe/metrics routes — self-scrape noise.
  const METRICS_SKIP = new Set(["/metrics", "/healthz", "/readyz"]);
  app.addHook("onResponse", async (req, reply) => {
    const route = req.routeOptions?.url;
    if (!route || METRICS_SKIP.has(route)) return;
    observeHttp({
      method: req.method,
      route,
      status: reply.statusCode,
      seconds: reply.elapsedTime / 1000,
    });
  });

  // ── enveloped error handler (never leak a stack trace in the body) ─────────────────────────────────
  app.setErrorHandler((err: FastifyError, req, reply) => {
    const id = requestId(req);
    // Zod validation failures arrive with a 400 + a `validation` array (set by validatorCompiler).
    const statusCode =
      typeof err.statusCode === "number" && err.statusCode >= 400
        ? err.statusCode
        : 500;
    const isValidation =
      statusCode === 400 ||
      (err as { validation?: unknown }).validation !== undefined;
    const code =
      statusCode === 400 || isValidation
        ? "bad_request"
        : statusCode === 401
          ? "unauthorized"
          : statusCode === 404
            ? "not_found"
            : "internal_error";
    // A 500 must not leak internals; everything else carries the (safe) message.
    const message = statusCode >= 500 ? "internal server error" : err.message;
    if (statusCode >= 500) req.log.error({ err }, "unhandled API error");
    void reply.status(statusCode).send({
      error: { code, message },
      disclaimer: DISCLAIMER,
      api_version: API_VERSION,
      request_id: id,
    });
  });

  // 404 (unmatched route) → enveloped, not Fastify's default.
  app.setNotFoundHandler((req, reply) => {
    void reply.status(404).send({
      error: { code: "not_found", message: "route not found" },
      disclaimer: DISCLAIMER,
      api_version: API_VERSION,
      request_id: requestId(req),
    });
  });

  // ── auth: x-api-key ∈ keySet on every DATA route (public routes opt out below) ─────────────────────
  function requireApiKey(req: FastifyRequest, reply: FastifyReply): boolean {
    const provided = req.headers["x-api-key"];
    const key = Array.isArray(provided) ? provided[0] : provided;
    if (!key || !keySet.has(key)) {
      void reply.status(401).send({
        error: {
          code: "unauthorized",
          message: "a valid x-api-key header is required",
        },
        disclaimer: DISCLAIMER,
        api_version: API_VERSION,
        request_id: requestId(req),
      });
      return false;
    }
    return true;
  }

  // ── PUBLIC: health ─────────────────────────────────────────────────────────────────────────────────
  app.get(
    "/healthz",
    // logLevel:'silent' suppresses this route's per-request log lines — the liveness probe hits /healthz
    // every few seconds and would otherwise drown the log. /readyz (below) keeps default logging.
    { logLevel: "silent", schema: { response: { 200: HealthResponse } } },
    async () => {
      // A cheap DB ping — keep it fast; a down DB still returns 200 with db:"down" (liveness, not readiness).
      let db: "ok" | "down" = "ok";
      try {
        await sql`select 1`;
      } catch {
        db = "down";
      }
      setDbUp(db === "ok");
      return { status: "ok" as const, db };
    },
  );

  // ── PUBLIC: readiness ────────────────────────────────────────────────────────────────────────────
  // Unlike /healthz, this FAILS (503) when the DB is unreachable — the readinessProbe targets it so a
  // pod that can't reach Postgres is taken out of the Service rotation rather than serving 500s.
  app.get(
    "/readyz",
    { schema: { response: { 200: ReadyResponse, 503: ReadyResponse } } },
    async (_req, reply) => {
      let db: "ok" | "down" = "ok";
      try {
        await sql`select 1`;
      } catch {
        db = "down";
      }
      setDbUp(db === "ok");
      void reply.code(db === "ok" ? 200 : 503);
      return {
        status: db === "ok" ? ("ok" as const) : ("unavailable" as const),
        db,
      };
    },
  );

  // ── PUBLIC: the generated OpenAPI 3.1 document ─────────────────────────────────────────────────────
  app.get("/openapi.json", { schema: { hide: true } }, async (_req, reply) => {
    void reply.header("content-type", "application/json");
    return app.swagger();
  });

  // ── PUBLIC: Prometheus metrics ─────────────────────────────────────────────────────────────────────
  // Unauthenticated (scraped in-cluster, never via Ingress), silent (scrape frequency would drown logs),
  // and envelope-bypassed (raw prom text, like /openapi.json) — NOT the Zod contract envelope.
  app.get(
    "/metrics",
    { logLevel: "silent", schema: { hide: true } },
    async (_req, reply) => {
      void reply.header("content-type", metricsContentType);
      return renderMetrics();
    },
  );

  // ── DATA routes (auth required) ────────────────────────────────────────────────────────────────────
  void app.register(async (api) => {
    // Gate every route in this scope on the API key.
    api.addHook("onRequest", async (req, reply) => {
      if (!requireApiKey(req, reply)) return reply; // short-circuit (reply already sent)
    });

    // GET /v1/windows — paginated, filterable list.
    api.get(
      "/v1/windows",
      {
        schema: {
          querystring: WindowListQuery,
          response: {
            200: WindowListResponse,
            400: ErrorResponse,
            401: ErrorResponse,
            500: ErrorResponse,
          },
        },
      },
      async (req) => {
        const q = req.query as z.infer<typeof WindowListQuery>;
        // q.closes_* are validated Date | undefined (coerce.date); hand them to the filter as ISO so an
        // Invalid Date can never reach the SQL bind.
        const {
          rows,
          total,
          limit: effLimit,
          offset: effOffset,
        } = await listWindows(sql, {
          confidence: q.confidence,
          status: q.status,
          docketId: q.docket_id,
          closesBefore: q.closes_before?.toISOString(),
          closesAfter: q.closes_after?.toISOString(),
          limit: q.limit,
          offset: q.offset,
        });
        // Stamp the EFFECTIVE (clamped) page the server actually served — never the requested values.
        return listEnvelope(
          rows,
          { limit: effLimit, offset: effOffset, total },
          requestId(req),
        );
      },
    );

    // GET /v1/windows/* — the OCD-ID (with slashes) is a trailing WILDCARD, not a :id param.
    api.get(
      "/v1/windows/*",
      {
        schema: {
          response: {
            200: WindowDetailResponse,
            400: ErrorResponse,
            404: ErrorResponse,
            401: ErrorResponse,
            500: ErrorResponse,
          },
        },
      },
      async (req, reply) => {
        const raw = (req.params as Record<string, string>)["*"] ?? "";
        const parsed = OcdId.safeParse(raw);
        if (!parsed.success) {
          return reply.status(400).send({
            error: { code: "bad_request", message: "malformed ocd_id" },
            disclaimer: DISCLAIMER,
            api_version: API_VERSION,
            request_id: requestId(req),
          });
        }
        const window = await getWindow(sql, parsed.data);
        if (!window) {
          return reply.status(404).send({
            error: { code: "not_found", message: "no window for that ocd_id" },
            disclaimer: DISCLAIMER,
            api_version: API_VERSION,
            request_id: requestId(req),
          });
        }
        const observations = await getWindowObservations(sql, parsed.data);
        return itemEnvelope({ ...window, observations }, requestId(req));
      },
    );

    // GET /v1/conflicts — the LIVE proof feed (resolved conflicts never surface).
    api.get(
      "/v1/conflicts",
      {
        schema: {
          querystring: ConflictListQuery,
          response: {
            200: ConflictListResponse,
            400: ErrorResponse,
            401: ErrorResponse,
            500: ErrorResponse,
          },
        },
      },
      async (req) => {
        const q = req.query as z.infer<typeof ConflictListQuery>;
        const {
          rows,
          total,
          limit: effLimit,
          offset: effOffset,
        } = await listConflicts(sql, {
          ocdId: q.ocd_id,
          limit: q.limit,
          offset: q.offset,
        });
        // Stamp the EFFECTIVE (clamped) page the server actually served — never the requested values.
        return listEnvelope(
          rows,
          { limit: effLimit, offset: effOffset, total },
          requestId(req),
        );
      },
    );
  });

  // The swagger plugin builds the doc lazily on the first app.swagger() call (the /openapi.json route),
  // which runs only after app.ready() — no onReady hook needed (and one would race the ready sequence).
  return app;
}
