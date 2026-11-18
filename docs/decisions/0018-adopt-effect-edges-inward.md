# 0018. Adopt Effect 4, from the edges inward

- Status: Accepted
- Date: 2026-11-15
- First slice: `apps/docketclock/src/sources/http.ts` (the shared HTTP retry layer).

## Context

DocketClock already does by hand what the [Effect](https://effect.website) library does as a type
system: injectable ports (`FetchLike`, `Adjudicator`, `LlmTracer`, `Sql`), failure modes spelled out in
comments ("retry network/429/5xx, never another 4xx"), per-pass and per-document isolation, and a
self-rescheduling poll loop that must never overlap itself. The trickiest of these, the retry loop in
`sources/http.ts`, carried its own AbortController, timer, body reader with cancel, and Retry-After
arithmetic, and has needed several review rounds to get right (memory: fetch-retry-scope-gotcha;
round-1 finding 6).

Effect 4.0 shipped stable on 2026-09-30 (4.1.4 is current), with a much smaller runtime than 3.x.
Alchemy v2, which now deploys DocketClock to Cloudflare (ADR 0019), is itself written in Effect and requires
`effect ^4.1.4`.

## Decision

Adopt Effect 4 incrementally, from the leaves of the call graph inward:

1. HTTP retry layer (this change).
2. Config (env reads behind `Config.String` / `Config.Redacted`).
3. Services and Layers for the existing ports.
4. The poll scheduler (`poll/run.ts`).
5. Pass internals, one at a time.

Rules for every step:

- **Promise boundary.** A migrated module keeps its existing Promise-returning exports (via
  `Effect.runPromise`) and rethrows the same errors as before, so no caller changes in the same PR.
  Effect-native exports sit beside them for later steps.
- **Whole modules.** Never half a file in Effect.
- **Sequential writers.** No `concurrency` option on any pass that writes; the single-writer invariant
  (see `poll/run.ts`) is unchanged.
- **Pin `effect` to an exact version.** Most published examples are 3.x, and 4.x renamed core APIs
  (`Effect.catch`, `Effect.result`, `Context.Service`, `Config.String`).
- **Out of scope:** `packages/contracts` (Zod), the pure reconcile core and rulebox, and Fastify.

## Consequences

- The retry scope in `http.ts` is now one predicate over tagged errors (`isRetriable`), the timeout is
  `Effect.timeoutOrElse` around one attempt (interruption aborts the send and cancels the body read),
  and back-off is an exponential `Schedule` that takes a capped Retry-After when the failure has one.
- One behaviour difference: a retriable 429/5xx now has its (timeout-bounded) error body read on
  every attempt, rather than only on the last one, so every `HttpStatusError` carries its body.
- A timeout now surfaces as `"<METHOD> <url> aborted: timed out after <n>ms"` instead of whatever the
  transport threw on abort. Callers that match `/abort/i` are unaffected.
- `effect` is a new runtime dependency of `@yokel/docketclock`.

## Update, 2026-11-18: observability joins the track

Slices 2 and 3 move the cycle lock and the poll scheduler to Effect and add tracing. Effect 4's
built-in OTLP exporter (`effect/observability/Otlp`) sends one span per cycle and one per pass to any
OTLP endpoint (Grafana Cloud is the plan). It is off unless `OTEL_EXPORTER_OTLP_ENDPOINT` is set, and
it flushes before a run-once container exits. Spans only nest inside Effect code, so HTTP, SQL and
adjudicator spans arrive as later slices move the passes themselves into Effect. Log levels are fixed
separately in pino (`log.ts` writes the level name), with no Effect involved.
