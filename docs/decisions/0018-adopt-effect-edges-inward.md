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

## Update, 2026-11-18: the adjudicator and HTTP spans (slice 4)

`ChatCompletionsAdjudicator` is an Effect program. The portability ladder is one `Effect.catchTag` on
`HttpStatusError`, and an unusable answer is a tagged `BadCompletion`; `adjudicate()` keeps its Promise
port and throws the same errors. Each LLM call is one OpenTelemetry GenAI span (`chat <model>`) with token
usage, finish reason, verdict and the knobs the ladder dropped, and every HTTP attempt in `http.ts` is a
client span (`GET`/`POST`, status code, resend count, URL without its query string).

Most passes are still Promise code, so `src/ambient.ts` bridges them: `run.ts` runs each pass
`withAmbient`, and Effect code inside it (`http.ts`, the adjudicator) runs `runAmbient`, which reuses the
pass's span and tracer from an AsyncLocalStorage. The bridge goes away once the passes are Effect code.

Langfuse stays as it is: it is configured only on the Mac mini and in the eval workflow, and the cloud
poller sends its LLM spans to the same OTLP endpoint as everything else.

## Update, 2026-11-18: the first pass moves inward (slice 5a, chain)

The chain pass is the first pass written as an Effect program (`src/reconcile/chain-pass.ts`, with
`chain-adjudicate.ts`). `run.ts` runs it directly, while the other passes still go through `withAmbient`.
Its steps are child spans of `poll.pass.chain`: `SELECT chain candidates`, `chain.core`,
`chain.adjudicate` (one `SELECT adjudication cache` per peek, one `chain.adjudicate.consult` per fresh
call) and `TRANSACTION chain conflicts`. `src/db/effect.ts` lifts one postgres.js query or transaction
into Effect as `dbQuery(name, run)`, with a typed `SqlError` and a database client span. The client itself
is unchanged. `chainReconcileOnce` and `adjudicateAmbiguousPairs` keep their Promise signatures (the first
is re-exported from `persist.ts`) and reject with the driver's own error.

Motivation: production traces show the chain pass at about 63 of 142 seconds per cycle, with no LLM
calls and nothing inside it to say why. The step spans answer that before any optimisation is attempted.

Outcome: the step spans put 48 of those seconds in `chain.core`, the pure rulebook walking every
(amendment, candidate) pair. Indexing the candidates on the three keys a link needs (#169) brought it to
about 2 seconds, and the chain pass to about 18.

## Update, 2026-11-18: window derivation, status refresh and amended originals (slice 5b)

`reconcileOcdId`, the one path every write takes to derive a window, is an Effect program
(`src/reconcile/reconcile-window.ts`, re-exported from `persist.ts`). Each derivation is a
`reconcile.window` span with the window's ocd_id, and its steps are child spans: `SELECT observations`,
`reconcile.amendment_inputs` (with the amendment loader's own queries inside it), `reconcile.core` and
`TRANSACTION reconciliation`. A failure is a `WindowFailure` naming the step, and the Promise form rejects
with the error that step threw, as before.

The status refresh (`statusRefresh`) and amended originals (`amendedOriginals`, moved to `rederive.ts`)
passes are Effect programs that `run.ts` runs directly, built on the shared `rederiveWindows` loop. The
amendment loader in `persist.ts` is still Promise code; its queries go through `ambientQuery`, which is
`dbQuery` run with `runAmbient`, so they nest under the caller's span and reject with the driver's error.

Motivation: those two passes take about 30 and 22 seconds per cycle, for 168 and 94 windows. The spans
show which step of a window's derivation costs that time.
