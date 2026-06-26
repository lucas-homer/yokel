/**
 * log.ts — the ONE configured pino root logger for the DocketClock app (PR-A1, observability slice A).
 *
 * Replaces the ad-hoc `console.*` on the hot paths (poller + API) with a single structured logger so
 * every line is NDJSON on stdout — exactly what Grafana Alloy → Loki parse natively. In-cluster stdout is
 * non-TTY, so there is DELIBERATELY no pino-pretty / no transport here: JSON straight to fd 1, dependency-
 * light, no worker thread. Pretty-printing (if ever wanted) is a `pino-pretty | ` pipe at the dev shell,
 * never baked into the process.
 *
 * LEVEL is read ONCE from LOG_LEVEL (default "info"), so a chatty `log.debug(...)` is free in prod (below
 * threshold → not serialized) yet flips on with `LOG_LEVEL=debug` without a code change.
 *
 * COMPONENT TAGGING: each subsystem logs through `componentLogger(name)` — a child binding a `component`
 * field (poller | api | reconcile | adjudicator) — so a Loki query can slice by subsystem
 * (`{...} | json | component="poller"`). The API passes its child as Fastify's `loggerInstance`, so every
 * request line is tagged too.
 *
 * TESTABILITY: `buildLogger` takes an optional level + destination so the unit test can construct an
 * IDENTICALLY-configured logger over a capture stream (no assertions against the global stdout). The same
 * `componentLogger` the app uses is exercised against that injected base — the function under test is real,
 * only its sink is swapped.
 */
import pino, { type DestinationStream, type Logger } from "pino";

/** The default level when LOG_LEVEL is unset/empty — normal progress visible, debug chatter suppressed. */
const DEFAULT_LEVEL = "info";

export interface BuildLoggerOptions {
  /** Explicit level override; falls back to LOG_LEVEL (empty/whitespace ignored), then DEFAULT_LEVEL. */
  level?: string;
  /** Where lines are written. Defaults to stdout (fd 1). Tests inject a capture stream for hermeticity. */
  destination?: DestinationStream;
}

/**
 * Build a configured pino logger: NDJSON, level from (opts.level ?? LOG_LEVEL ?? "info"), to stdout unless
 * a destination is injected. This is the single source of logger configuration — `rootLogger` is just its
 * default-argument call, and the test builds another over a capture stream to assert the same contract.
 *
 * LOG_LEVEL is trimmed and an empty value is treated as UNSET (falls through to the default) — `??` alone
 * would pass `LOG_LEVEL=""` (common when an env var is templated but left blank) straight to pino, which
 * rejects it as an unknown level and throws at construction. `||` over the trimmed value avoids that.
 */
export function buildLogger(opts: BuildLoggerOptions = {}): Logger {
  const envLevel = process.env.LOG_LEVEL?.trim();
  const level = opts.level ?? (envLevel || DEFAULT_LEVEL);
  return opts.destination ? pino({ level }, opts.destination) : pino({ level });
}

/** The process-wide root logger. Every subsystem child descends from this (one config, one stdout sink). */
export const rootLogger: Logger = buildLogger();

/**
 * A child logger tagged with a `component` field — the standard handle each subsystem logs through. `base`
 * defaults to the shared root; tests pass a capture-stream-backed base so they exercise the REAL function
 * without touching global stdout.
 */
export function componentLogger(
  component: string,
  base: Logger = rootLogger,
): Logger {
  return base.child({ component });
}
