/**
 * Shared source-adapter HTTP — a single request-with-retry used by every source adapter (and the Gemini
 * adjudicator), so the load-bearing RETRY SCOPE lives in exactly one place (memory: fetch-retry-scope-gotcha).
 *
 * Written in Effect (ADR 0018). The rules are unchanged from the hand-rolled loop this replaced:
 *   - RETRIED: network/abort failures of the send, a transient body-read failure, a per-attempt timeout,
 *     429 and 5xx (honoring a server Retry-After, capped at MAX_RETRY_AFTER_MS).
 *   - NOT RETRIED: any other 4xx (fails fast with the status in the message), a malformed (non-JSON) body.
 *   - The per-attempt timeout bounds the WHOLE attempt — send AND body read — never the backoff sleep.
 *
 * How the Effect version encodes them:
 *   - Every failure is a TAGGED error (NetworkError, BodyReadError, RequestTimeout, HttpStatusError,
 *     MalformedBody). What retries is ONE predicate over those tags (`isRetriable`) — the retry scope is a
 *     type, not careful try/catch placement.
 *   - `Effect.timeoutOrElse` around one attempt interrupts it when the clock runs out. Interruption aborts
 *     the AbortSignal `Effect.tryPromise` hands to the send and to the body read, and the body read
 *     cancels its stream reader on abort — so a server that sends headers then stalls the body can't hang
 *     the single-writer poll cycle, even if its stream ignores the signal (round-1 review, finding 6).
 *   - `Effect.retry` with an exponential `Schedule` (500ms · 2^n, capped 30s) whose delay is swapped for the
 *     capped Retry-After when the failure carries one. `times` is the retry budget.
 *
 * BOUNDARY: the three exported functions keep their Promise signatures (callers are unchanged). They run
 * the Effect with `Effect.runPromise` and rethrow the SAME error a caller saw before: the transport's own
 * error for a network failure, the SyntaxError for a malformed body, an Error carrying the status for a
 * non-OK response. Effect-native callers can use `httpGetJson` / `httpGetText` / `httpPostJson` instead
 * and get the typed `HttpError` union.
 */
import { Data, Duration, Effect, Schedule } from "effect";

/**
 * Ceiling for a server-provided Retry-After sleep. regulations.gov answers a burst over its ~1,000 req/hr
 * quota with a 429 + a LARGE Retry-After (often the seconds remaining to the top of the hour — minutes).
 * Honored verbatim, a single retry could sleep for many minutes, freezing the whole sequential poll cycle;
 * with the poller's 2x-interval liveness probe (30m) a long enough sleep drifts toward a mid-fetch pod
 * restart, and even short of that it silently wedges withdrawal detection. We still HONOR Retry-After (back
 * off politely rather than hammering) but CAP the wait: 60s rides out a transient 429 while staying well
 * under any per-pass timeout, and a source still limited after the cap just fails the pass (isolated,
 * retried next cycle) instead of stalling it. The per-cycle re-poll budget (poll.ts) is the upstream fix
 * that keeps us from tripping the 429 in the first place; this cap bounds the blast radius when we do.
 */
export const MAX_RETRY_AFTER_MS = 60_000;

/** Exponential back-off ceiling when no Retry-After applies. */
const MAX_BACKOFF_MS = 30_000;

/** A usable Retry-After (seconds → ms, capped), or undefined when absent / zero / negative / non-numeric. */
function retryAfterMs(res: Response): number | undefined {
  const retryAfter = Number(res.headers.get("retry-after"));
  return Number.isFinite(retryAfter) && retryAfter > 0
    ? Math.min(retryAfter * 1000, MAX_RETRY_AFTER_MS)
    : undefined;
}

/**
 * Back-off for a retriable 429/5xx: HONOR Retry-After when present (capped at MAX_RETRY_AFTER_MS), else
 * exponential (500ms · 2^attempt, itself capped at 30s). Exported for direct unit testing of the cap —
 * the load-bearing branch (memory: fetch-retry-scope-gotcha). The retry Schedule below computes the same
 * delay from the error it is retrying.
 */
export const retriableBackoffMs = (res: Response, attempt: number): number =>
  retryAfterMs(res) ?? Math.min(MAX_BACKOFF_MS, 500 * 2 ** attempt);

/**
 * A `fetch`-like function. Defaults to the global `fetch`, but is injectable so callers (and tests)
 * can substitute a transport with zero network. Mirrors the parts of `fetch` we depend on.
 */
export type FetchLike = (url: string, init: RequestInit) => Promise<Response>;

export interface FetchOpts {
  /** retries on network errors / 429 / 5xx only (default 4). 4xx never retries. */
  retries?: number;
  timeoutMs?: number;
  /** extra request headers (e.g. an X-Api-Key for keyed sources). Accept: application/json is added. */
  headers?: Record<string, string>;
}

export interface PostOpts extends FetchOpts {
  /**
   * Injectable transport (a `fetch`-like function). Defaults to the global `fetch` so production runs
   * over the real network; tests pass a spy so no network/key is needed.
   */
  transport?: FetchLike;
}

// ── The failure modes, as values ────────────────────────────────────────────────────────────────────

/** The send itself failed (DNS, connection reset, the transport rejected). Retriable. */
export class NetworkError extends Data.TaggedError("NetworkError")<{
  readonly cause: unknown;
}> {}

/** The status was OK but reading the body broke mid-stream. Retriable. */
export class BodyReadError extends Data.TaggedError("BodyReadError")<{
  readonly cause: unknown;
}> {}

/** One attempt (send + body) ran past its timeout and was interrupted. Retriable. */
export class RequestTimeout extends Data.TaggedError("RequestTimeout")<{
  readonly method: string;
  readonly url: string;
  readonly timeoutMs: number;
}> {
  override get message(): string {
    return `${this.method} ${this.url} aborted: timed out after ${this.timeoutMs}ms`;
  }
}

/** A non-OK status. Retriable only for 429 and 5xx; any other 4xx fails fast. */
export class HttpStatusError extends Data.TaggedError("HttpStatusError")<{
  readonly method: string;
  readonly url: string;
  readonly status: number;
  readonly statusText: string;
  readonly body: string;
  /** the server's Retry-After, already capped at MAX_RETRY_AFTER_MS; undefined when absent/unusable */
  readonly retryAfterMs: number | undefined;
}> {
  get retriable(): boolean {
    return this.status === 429 || this.status >= 500;
  }
  override get message(): string {
    return `${this.method} ${this.url} -> ${this.status} ${this.statusText}${this.body ? `: ${this.body.slice(0, 300)}` : ""}`;
  }
}

/** The body arrived whole but isn't what we asked for (e.g. not JSON). Never retried. */
export class MalformedBody extends Data.TaggedError("MalformedBody")<{
  readonly cause: unknown;
}> {}

export type HttpError =
  | NetworkError
  | BodyReadError
  | RequestTimeout
  | HttpStatusError
  | MalformedBody;

/** THE retry scope: one predicate over the error tags (memory: fetch-retry-scope-gotcha). */
const isRetriable = (e: HttpError): boolean => {
  switch (e._tag) {
    case "NetworkError":
    case "BodyReadError":
    case "RequestTimeout":
      return true;
    case "HttpStatusError":
      return e.retriable;
    case "MalformedBody":
      return false;
  }
};

/**
 * The retry delays: 500ms, 1s, 2s, … (exponential, capped at 30s). When the failure being retried is a
 * status error carrying a Retry-After, that (capped) value replaces the exponential delay.
 */
const backoff = Schedule.exponential("500 millis").pipe(
  Schedule.modifyDelay(({ input, duration }) =>
    Effect.succeed(
      (input as HttpError | undefined)?._tag === "HttpStatusError" &&
        (input as HttpStatusError).retryAfterMs !== undefined
        ? Duration.millis((input as HttpStatusError).retryAfterMs!)
        : Duration.min(duration, Duration.millis(MAX_BACKOFF_MS)),
    ),
  ),
);

// ── One attempt ─────────────────────────────────────────────────────────────────────────────────────

/**
 * Drain a body as text, cancelling the stream when `signal` aborts. Our own reader (not res.text()): a
 * body that ignores the abort can still be CANCELLED through the reader we hold — res.text() would lock
 * the stream and make it uncancellable.
 */
async function drain(res: Response, signal: AbortSignal): Promise<string> {
  const body = res.body;
  if (!body) return "";
  const reader = body.getReader();
  const onAbort = () => void reader.cancel().catch(() => {});
  if (signal.aborted) onAbort();
  else signal.addEventListener("abort", onAbort, { once: true });
  try {
    const chunks: Uint8Array[] = [];
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      chunks.push(value);
    }
    return new TextDecoder().decode(Buffer.concat(chunks));
  } finally {
    signal.removeEventListener("abort", onAbort);
  }
}

/** Read the body under the attempt: an interruption (the timeout) aborts `signal`, which cancels it. */
const readBody = (res: Response) =>
  Effect.tryPromise({
    try: (signal) => drain(res, signal),
    catch: (cause) => new BodyReadError({ cause }),
  });

interface RequestSpec<T> {
  method: "GET" | "POST";
  url: string;
  send: (signal: AbortSignal) => Promise<Response>;
  /** turn an OK body into the result; a throw here is a MalformedBody (never retried) */
  parse: (body: string) => T;
  retries: number;
  timeoutMs: number;
  /** a 404 becomes this value instead of a failure (GovInfo's "not published yet") */
  notFound?: { value: T };
}

/** Send once, check the status, read the body — all bounded by one timeout. */
const attempt = <T>(spec: RequestSpec<T>): Effect.Effect<T, HttpError> =>
  Effect.gen(function* () {
    const res = yield* Effect.tryPromise({
      try: (signal) => spec.send(signal),
      catch: (cause) => new NetworkError({ cause }),
    });

    if (res.ok) {
      const text = yield* readBody(res);
      return yield* Effect.try({
        try: () => spec.parse(text),
        catch: (cause) => new MalformedBody({ cause }),
      });
    }
    if (res.status === 404 && spec.notFound) {
      yield* readBody(res).pipe(Effect.ignore);
      return spec.notFound.value;
    }
    const body = yield* readBody(res).pipe(Effect.orElseSucceed(() => ""));
    return yield* new HttpStatusError({
      method: spec.method,
      url: spec.url,
      status: res.status,
      statusText: res.statusText,
      body,
      retryAfterMs: retryAfterMs(res),
    });
  }).pipe(
    Effect.timeoutOrElse({
      duration: Duration.millis(spec.timeoutMs),
      orElse: () =>
        Effect.fail(
          new RequestTimeout({
            method: spec.method,
            url: spec.url,
            timeoutMs: spec.timeoutMs,
          }),
        ),
    }),
  );

/** The ONE retry loop behind every adapter request: an attempt, retried per the scope above. */
const request = <T>(spec: RequestSpec<T>): Effect.Effect<T, HttpError> =>
  attempt(spec).pipe(
    Effect.retry({
      schedule: backoff,
      times: spec.retries,
      while: isRetriable,
    }),
  );

// ── Effect-native API ───────────────────────────────────────────────────────────────────────────────

const parseJson = (text: string): unknown => JSON.parse(text) as unknown;

/** GET a URL as JSON. Fails with a typed HttpError. */
export const httpGetJson = (
  url: string,
  opts: FetchOpts = {},
): Effect.Effect<unknown, HttpError> => {
  const { retries = 4, timeoutMs = 30_000, headers = {} } = opts;
  return request({
    method: "GET",
    url,
    // `fetch` is looked up per call (not captured at import) so a stubbed globalThis.fetch is honored.
    send: (signal) =>
      fetch(url, {
        headers: { Accept: "application/json", ...headers },
        signal,
      }),
    parse: parseJson,
    retries,
    timeoutMs,
  });
};

/** GET a URL as TEXT. With `notFoundAsNull`, a 404 succeeds with null. Fails with a typed HttpError. */
export const httpGetText = (
  url: string,
  opts: FetchOpts & { accept?: string; notFoundAsNull?: boolean } = {},
): Effect.Effect<string | null, HttpError> => {
  const {
    retries = 4,
    timeoutMs = 30_000,
    headers = {},
    accept = "text/html",
    notFoundAsNull = false,
  } = opts;
  return request<string | null>({
    method: "GET",
    url,
    send: (signal) =>
      fetch(url, { headers: { Accept: accept, ...headers }, signal }),
    parse: (text) => text,
    retries,
    timeoutMs,
    ...(notFoundAsNull ? { notFound: { value: null } } : {}),
  });
};

/** POST a JSON body and read JSON back. Fails with a typed HttpError. */
export const httpPostJson = (
  url: string,
  body: unknown,
  opts: PostOpts = {},
): Effect.Effect<unknown, HttpError> => {
  const {
    retries = 4,
    timeoutMs = 30_000,
    headers = {},
    transport = (u, init) => fetch(u, init),
  } = opts;
  const payload = JSON.stringify(body);
  return request({
    method: "POST",
    url,
    send: (signal) =>
      transport(url, {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          ...headers,
        },
        body: payload,
        signal,
      }),
    parse: parseJson,
    retries,
    timeoutMs,
  });
};

// ── Promise boundary (what existing callers use) ────────────────────────────────────────────────────

/**
 * The error a Promise caller sees — the same one the pre-Effect loop threw: the transport's own error
 * for a failed send or broken body, the SyntaxError for a malformed body, and an Error with the status
 * (or the timeout) in its message otherwise.
 */
function toThrown(e: HttpError): unknown {
  switch (e._tag) {
    case "NetworkError":
    case "BodyReadError":
    case "MalformedBody":
      return e.cause;
    case "RequestTimeout":
    case "HttpStatusError":
      return new Error(e.message);
  }
}

const runAsPromise = <T>(program: Effect.Effect<T, HttpError>): Promise<T> =>
  Effect.runPromise(
    program.pipe(Effect.catch((e: HttpError) => Effect.die(toThrown(e)))),
  );

/** GET a URL as JSON, with exponential backoff on RETRIABLE failures only. */
export async function fetchJsonWithRetry(
  url: string,
  opts: FetchOpts = {},
): Promise<unknown> {
  return runAsPromise(httpGetJson(url, opts));
}

/**
 * GET a URL as TEXT (e.g. a GovInfo HTML rendition), with the SAME retry scope as fetchJsonWithRetry.
 * ONE addition: `notFoundAsNull` turns a 404 into a `null` result instead of a throw — for a source where
 * "not there yet" is a normal outcome (GovInfo publishes the rendition after the FR API lists a
 * document), so the caller can skip and retry next cycle without that ordinary state being logged as a
 * failure. Off by default (a 404 throws, as for JSON). The timeout bounds the body read too.
 */
export async function fetchTextWithRetry(
  url: string,
  opts: FetchOpts & { accept?: string; notFoundAsNull?: boolean } = {},
): Promise<string | null> {
  return runAsPromise(httpGetText(url, opts));
}

/**
 * POST a JSON body and read JSON back, with the SAME retry SCOPE discipline as fetchJsonWithRetry
 * (memory: fetch-retry-scope-gotcha): network/abort failures, transient body-read failures, 429 and 5xx
 * are retried; a non-retriable 4xx (e.g. a 400/401/403 for a bad or absent API key) throws IMMEDIATELY
 * instead of burning the retry budget. The timeout bounds the body read too. The transport is
 * injectable (default global `fetch`) so tests need no network. Returns the parsed JSON body.
 */
export async function postJsonWithRetry(
  url: string,
  body: unknown,
  opts: PostOpts = {},
): Promise<unknown> {
  return runAsPromise(httpPostJson(url, body, opts));
}
