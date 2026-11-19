/**
 * poller.ts — the Poll Worker. A Cron Trigger fires `scheduled`, which asks ONE container-backed Durable
 * Object ("poller") to run ONE poll cycle in the existing DocketClock image (`src/poll/run.ts --once`).
 * The container exits when the cycle ends, so it is billed only while a cycle runs.
 *
 * Overlap is guarded twice:
 *   1. Here: a single DO instance, and `runCycle` skips when its container is still running.
 *   2. In the database: the poll-cycle advisory lock (apps/docketclock/src/poll/cycle-lock.ts) skips a cycle
 *      that finds another one in flight, whoever started it (e.g. the Mac mini poller during cutover).
 *
 * DATABASE_URL must be Neon's DIRECT (non-pooled) URI: the advisory lock is session-scoped, and pgbouncer in
 * transaction mode would hand the lock and its unlock to different server sessions.
 */
import { Container, getContainer } from "@cloudflare/containers";

export interface PollerEnv {
  POLLER: DurableObjectNamespace<PollerContainer>;
  DATABASE_URL: string;
  REGS_API_KEY: string;
  CLOUDFLARE_ACCOUNT_ID: string;
  CLOUDFLARE_AI_TOKEN: string;
  LOG_LEVEL?: string;
  /** Optional OTLP trace export (apps/docketclock/src/telemetry.ts); both unset = off. */
  OTEL_EXPORTER_OTLP_ENDPOINT?: string;
  OTEL_EXPORTER_OTLP_HEADERS?: string;
  /** Cloud alerts (apps/docketclock/src/alerts/). Each unset = that part off. */
  DOCKETCLOCK_API_URL?: string;
  HEALTHCHECKS_PING_KEY?: string;
  NTFY_URL?: string;
}

/** The DO instance name. Fixed, so every cron fire reaches the same container. */
const INSTANCE = "poller";

export class PollerContainer extends Container<PollerEnv> {
  // A cycle has no inbound requests to renew the activity timer, so `sleepAfter` is the hard cap on one
  // cycle's wall time. The 15-minute schedule skips fires while a cycle is still running (see runCycle).
  override sleepAfter = "45m";
  override enableInternet = true;

  /** Start one cycle unless one is already running. Returns what happened, for the Worker's log line. */
  async runCycle(): Promise<"started" | "already-running"> {
    if (this.ctx.container?.running) return "already-running";
    const e = this.env;
    await this.start({
      enableInternet: true,
      // Apply pending migrations first (idempotent: schema_migrations), then run exactly one cycle. tsx is
      // called directly, not via `pnpm exec`: corepack would download pnpm on every cold start.
      entrypoint: [
        "sh",
        "-c",
        "node_modules/.bin/tsx src/db/migrate.ts && exec node_modules/.bin/tsx src/poll/run.ts --once",
      ],
      envVars: {
        NODE_ENV: "production",
        LOG_LEVEL: e.LOG_LEVEL ?? "info",
        DATABASE_URL: e.DATABASE_URL,
        REGS_API_KEY: e.REGS_API_KEY,
        CLOUDFLARE_ACCOUNT_ID: e.CLOUDFLARE_ACCOUNT_ID,
        CLOUDFLARE_AI_TOKEN: e.CLOUDFLARE_AI_TOKEN,
        DOCKETCLOCK_API_URL: e.DOCKETCLOCK_API_URL ?? "",
        HEALTHCHECKS_PING_KEY: e.HEALTHCHECKS_PING_KEY ?? "",
        NTFY_URL: e.NTFY_URL ?? "",
        ...(e.OTEL_EXPORTER_OTLP_ENDPOINT
          ? {
              OTEL_EXPORTER_OTLP_ENDPOINT: e.OTEL_EXPORTER_OTLP_ENDPOINT,
              OTEL_EXPORTER_OTLP_HEADERS: e.OTEL_EXPORTER_OTLP_HEADERS ?? "",
              OTEL_SERVICE_NAME: "docketclock-poller",
            }
          : {}),
      },
    });
    return "started";
  }

  override onStop(params: { exitCode?: number; reason?: string }): void {
    const ok = params.exitCode === 0;
    console[ok ? "log" : "error"](
      JSON.stringify({ msg: "poll cycle container stopped", ...params }),
    );
  }

  override onError(error: unknown): unknown {
    console.error(
      JSON.stringify({
        msg: "poll cycle container error",
        error: String(error),
      }),
    );
    throw error;
  }
}

export default {
  async scheduled(
    controller: ScheduledController,
    env: PollerEnv,
    _ctx: ExecutionContext,
  ): Promise<void> {
    const outcome = await getContainer(env.POLLER, INSTANCE).runCycle();
    console.log(
      JSON.stringify({
        msg: "poll cron fired",
        cron: controller.cron,
        scheduledTime: new Date(controller.scheduledTime).toISOString(),
        outcome,
      }),
    );
  },

  // No public surface: the poller is driven only by its Cron Trigger.
  async fetch(): Promise<Response> {
    return new Response("not found", { status: 404 });
  },
} satisfies ExportedHandler<PollerEnv>;
