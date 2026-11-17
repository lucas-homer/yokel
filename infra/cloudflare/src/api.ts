/**
 * api.ts — the API Worker. Forwards every request to the existing Fastify API (src/api/run.ts) running in a
 * container from the same DocketClock image. The container starts on the first request and sleeps after
 * `sleepAfter` without traffic, so an idle API costs nothing.
 */
import { Container, getContainer } from "@cloudflare/containers";

export interface ApiEnv {
  API: DurableObjectNamespace<ApiContainer>;
  DATABASE_URL: string;
  DOCKETCLOCK_API_KEYS: string;
  LOG_LEVEL?: string;
}

export class ApiContainer extends Container<ApiEnv> {
  override defaultPort = 8080; // the image's PORT
  override sleepAfter = "10m";
  override enableInternet = true;

  constructor(ctx: DurableObjectState<{}>, env: ApiEnv) {
    super(ctx, env);
    // tsx directly, not the image's `pnpm exec tsx` CMD: corepack would download pnpm on every cold start.
    this.entrypoint = ["node_modules/.bin/tsx", "src/api/run.ts"];
    this.envVars = {
      NODE_ENV: "production",
      PORT: "8080",
      LOG_LEVEL: env.LOG_LEVEL ?? "info",
      DATABASE_URL: env.DATABASE_URL,
      DOCKETCLOCK_API_KEYS: env.DOCKETCLOCK_API_KEYS,
    };
  }
}

export default {
  async fetch(request: Request, env: ApiEnv): Promise<Response> {
    return getContainer(env.API, "api").fetch(request);
  },
} satisfies ExportedHandler<ApiEnv>;
