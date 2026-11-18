/**
 * alchemy.run.ts — DocketClock on Cloudflare + Neon (phase 1 of the move off the Mac mini).
 *
 *   Neon Project (Postgres 18) ──DATABASE_URL──▶ Poll Worker ──Cron──▶ PollerContainer (one cycle, then exit)
 *                              └─DATABASE_URL──▶ API Worker  ──fetch─▶ ApiContainer   (sleeps when idle)
 *
 * Both containers run the EXISTING image (apps/docketclock/Dockerfile, built from the repo root), so the
 * Node code is unchanged. The poller's Cron Trigger is OFF unless DOCKETCLOCK_POLL_CRON is set: phase 1
 * stands the stack up beside the Mac mini without a second writer, and cutover turns the schedule on.
 *
 * Credentials (never in this file): CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID (CI) or the Alchemy
 * profile (local), and NEON_API_KEY. App secrets are read at deploy time from the environment
 * (repo-root .env locally, GitHub Actions secrets in CI) and bound as Worker secrets. See README.md.
 */
import * as Cloudflare from "@alchemy.run/cloudflare";
import * as Neon from "@alchemy.run/neon";
import * as Alchemy from "alchemy";
import * as Config from "effect/Config";
import * as Effect from "effect/Effect";
import * as Layer from "effect/Layer";

import type { ApiContainer } from "./src/api.ts";
import type { PollerContainer } from "./src/poller.ts";

/** Repo root: the Docker build context the image already expects (see apps/docketclock/Dockerfile). */
const REPO_ROOT = `${import.meta.dirname}/../..`;
// Alchemy realPaths `dockerfile` against the cwd (infra/cloudflare), not `context`,
// despite its docs, so pass an absolute path.
const DOCKERFILE = `${REPO_ROOT}/apps/docketclock/Dockerfile`;

const secret = (name: string) => Config.Redacted(name);

// Workers Logs + automatic traces for every invocation (cron, fetch, Durable Object calls). Volume is tiny
// (96 cron runs a day plus API traffic), so sample everything. Logs and traces are kept 7 days.
const OBSERVABILITY = {
  enabled: true,
  headSamplingRate: 1,
  logs: { enabled: true, invocationLogs: true, headSamplingRate: 1 },
  traces: { enabled: true, headSamplingRate: 1 },
} as const;

export default Alchemy.Stack(
  "DocketClock",
  {
    providers: Layer.mergeAll(Cloudflare.providers(), Neon.providers()),
    state: Cloudflare.state(),
  },
  Effect.gen(function* () {
    // Optional knobs, read from the deploy environment.
    const pollCron = yield* Config.String("DOCKETCLOCK_POLL_CRON").pipe(
      Config.withDefault(""),
    );
    const apiDomain = yield* Config.String("DOCKETCLOCK_API_DOMAIN").pipe(
      Config.withDefault(""),
    );

    const db = yield* Neon.Project("Db", {
      name: "docketclock",
      region: "aws-us-west-2",
      pgVersion: 18,
      databaseName: "docketclock",
      roleName: "docketclock",
      // Neon free plan caps history retention at 6h; the 24h default is rejected.
      historyRetentionSeconds: 21600,
    });

    const poller = yield* Cloudflare.Worker("Poller", {
      main: `${import.meta.dirname}/src/poller.ts`,
      observability: OBSERVABILITY,
      // Empty list = no Cron Triggers (also removes any left from an earlier deploy).
      crons: pollCron ? [pollCron] : [],
      env: {
        POLLER: Cloudflare.Container<PollerContainer>("PollerContainer", {
          className: "PollerContainer",
          context: REPO_ROOT,
          dockerfile: DOCKERFILE,
          // Ship container stdout (the app's pino NDJSON) into Workers Logs.
          observability: { logs: { enabled: true } },
          // Run near Neon (aws-us-west-2). Unpinned, the first cycle landed in IAD and every query crossed
          // the country (8.5-minute cycle).
          constraints: { regions: ["WNAM"] },
          instanceType: "basic", // 1/4 vCPU, 1 GiB: tsx + the full pass set does not fit "lite" (256 MiB)
          maxInstances: 1,
        }),
        // DIRECT, not pooled: the poll-cycle advisory lock is session-scoped (see src/poller.ts).
        DATABASE_URL: db.connectionUri,
        REGS_API_KEY: secret("REGS_API_KEY"),
        ADJUDICATOR: yield* Config.String("ADJUDICATOR").pipe(
          Config.withDefault("gemini"),
        ),
        GEMINI_API_KEY: secret("GEMINI_API_KEY"),
      },
    });

    const api = yield* Cloudflare.Worker("Api", {
      main: `${import.meta.dirname}/src/api.ts`,
      observability: OBSERVABILITY,
      // workers.dev until the docketclock.app zone is on the account (then set DOCKETCLOCK_API_DOMAIN).
      domain: apiDomain || undefined,
      env: {
        API: Cloudflare.Container<ApiContainer>("ApiContainer", {
          className: "ApiContainer",
          context: REPO_ROOT,
          dockerfile: DOCKERFILE,
          observability: { logs: { enabled: true } },
          // Run near Neon (aws-us-west-2). Unpinned, the first cycle landed in IAD and every query crossed
          // the country (8.5-minute cycle).
          constraints: { regions: ["WNAM"] },
          instanceType: "basic",
          maxInstances: 2,
        }),
        DATABASE_URL: db.connectionUri,
        DOCKETCLOCK_API_KEYS: secret("DOCKETCLOCK_API_KEYS"),
      },
    });

    return {
      apiUrl: api.url,
      pollerWorker: poller.workerName,
      pollCron: pollCron || "off",
      neonProjectId: db.projectId,
    };
  }),
);
