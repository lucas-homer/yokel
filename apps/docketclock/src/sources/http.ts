/**
 * Shared source-adapter HTTP — a single GET-JSON-with-retry used by every source adapter, so the
 * load-bearing RETRY SCOPE lives in exactly one place (memory: fetch-retry-scope-gotcha).
 *
 * CRITICAL: only `await fetch()` (network/abort) is inside the try/catch. HTTP-status handling lives
 * OUTSIDE it, so a non-retriable 4xx (e.g. a 404 for an unknown id) throws IMMEDIATELY instead of
 * being swallowed by the catch and burning every retry with backoff. We retry ONLY network/abort
 * errors, 429, and 5xx.
 */
const sleep = (ms: number): Promise<void> =>
  new Promise((r) => setTimeout(r, ms));

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

/**
 * Back-off for a retriable 429/5xx: HONOR Retry-After when present (capped at MAX_RETRY_AFTER_MS), else
 * exponential (500ms · 2^attempt, itself capped at 30s). Exported for direct unit testing of the cap —
 * the load-bearing branch (memory: fetch-retry-scope-gotcha).
 */
export const retriableBackoffMs = (res: Response, attempt: number): number => {
  const retryAfter = Number(res.headers.get("retry-after"));
  return Number.isFinite(retryAfter) && retryAfter > 0
    ? Math.min(retryAfter * 1000, MAX_RETRY_AFTER_MS)
    : Math.min(30_000, 500 * 2 ** attempt);
};

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

/**
 * Read a response body UNDER the request's abort signal (round-1 review, finding 6). The per-attempt
 * timeout must bound the WHOLE request — a server that sends headers and then stalls the body would
 * otherwise hang `res.text()` / `res.json()` forever, and with it the single-writer poll cycle. On abort
 * the unfinished body is cancelled (freeing the socket) and the read rejects; the listener is removed
 * once the read settles, so a completed read is never disturbed.
 */
async function readBody(res: Response, signal: AbortSignal): Promise<string> {
  const body = res.body;
  if (!body) return "";
  // Our own reader (not res.text()): a body that ignores the abort signal can still be CANCELLED through
  // the reader we hold — res.text() would lock the stream and make it uncancellable.
  const reader = body.getReader();
  let onAbort: () => void = () => {};
  const aborted = new Promise<never>((_, reject) => {
    onAbort = () => {
      reader.cancel().catch(() => {});
      reject(new Error("response body timed out"));
    };
    if (signal.aborted) onAbort();
    else signal.addEventListener("abort", onAbort, { once: true });
  });
  aborted.catch(() => {}); // settled by the race below; never an unhandled rejection
  const chunks: Uint8Array[] = [];
  const drain = (async () => {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      chunks.push(value);
    }
    return new TextDecoder().decode(Buffer.concat(chunks));
  })();
  drain.catch(() => {});
  try {
    return await Promise.race([drain, aborted]);
  } finally {
    signal.removeEventListener("abort", onAbort);
  }
}

/** A body-read failure worth retrying: the timeout fired or the stream broke — never a malformed body. */
function transientBodyError(err: unknown, signal: AbortSignal): boolean {
  return signal.aborted || !(err instanceof SyntaxError);
}

/**
 * The ONE retry loop behind every adapter request (memory: fetch-retry-scope-gotcha). Per attempt an
 * AbortController + timer bound the request AND its body read (readBody). Retried: network/abort
 * failures of the send, transient body-read failures, 429 and 5xx (honoring a capped Retry-After). Not
 * retried: any other 4xx (fails fast with the status in the message), a malformed body. `notFound`
 * turns a 404 into a value instead of a throw (GovInfo's "not published yet").
 */
async function requestWithRetry<T>(
  method: "GET" | "POST",
  url: string,
  send: (signal: AbortSignal) => Promise<Response>,
  readOk: (body: string) => T,
  opts: { retries: number; timeoutMs: number },
  notFound?: { value: T },
): Promise<T> {
  type Attempt = { done: true; value: T } | { done: false; backoff: number };
  let attempt = 0;
  const once = async (): Promise<Attempt> => {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), opts.timeoutMs);
    try {
      // Only send failures (network/abort) are caught here — HTTP-status handling lives outside, so a
      // non-retriable 4xx throw propagates immediately instead of being retried.
      let res: Response;
      try {
        res = await send(ctrl.signal);
      } catch (err) {
        if (attempt >= opts.retries) throw err;
        return { done: false, backoff: Math.min(30_000, 500 * 2 ** attempt++) };
      }

      if (res.ok) {
        try {
          return {
            done: true,
            value: readOk(await readBody(res, ctrl.signal)),
          };
        } catch (err) {
          if (!transientBodyError(err, ctrl.signal) || attempt >= opts.retries)
            throw err;
          return {
            done: false,
            backoff: Math.min(30_000, 500 * 2 ** attempt++),
          };
        }
      }
      if (res.status === 404 && notFound) {
        await readBody(res, ctrl.signal).catch(() => "");
        return { done: true, value: notFound.value };
      }

      // 4xx (other than 429) is non-retriable — a 404/422 (or a 400/401/403 bad key) fails fast.
      const retriable = res.status === 429 || res.status >= 500;
      if (!retriable || attempt >= opts.retries) {
        const body = await readBody(res, ctrl.signal).catch(() => "");
        throw new Error(
          `${method} ${url} -> ${res.status} ${res.statusText}${body ? `: ${body.slice(0, 300)}` : ""}`,
        );
      }

      // Retriable (429 / 5xx): back off, honoring (a capped) Retry-After when present.
      const backoff = retriableBackoffMs(res, attempt++);
      res.body?.cancel().catch(() => {});
      return { done: false, backoff };
    } finally {
      clearTimeout(timer); // the timer bounds the attempt, never the backoff sleep
    }
  };
  for (;;) {
    const r = await once();
    if (r.done) return r.value;
    await sleep(r.backoff);
  }
}

/** GET a URL as JSON, with exponential backoff on RETRIABLE failures only. */
export async function fetchJsonWithRetry(
  url: string,
  opts: FetchOpts = {},
): Promise<unknown> {
  const { retries = 4, timeoutMs = 30_000, headers = {} } = opts;
  return requestWithRetry<unknown>(
    "GET",
    url,
    (signal) =>
      fetch(url, {
        headers: { Accept: "application/json", ...headers },
        signal,
      }),
    (text) => JSON.parse(text) as unknown,
    { retries, timeoutMs },
  );
}

/**
 * GET a URL as TEXT (e.g. a GovInfo HTML rendition), with the SAME retry scope as fetchJsonWithRetry.
 * ONE addition: `notFoundAsNull` turns a 404 into a `null` result instead of a throw — for a source where
 * "not there yet" is a normal outcome (GovInfo publishes the rendition after the FR API lists a
 * document), so the caller can skip and retry next cycle without that ordinary state being logged as a
 * failure. Off by default (a 404 throws, as for JSON). The timeout bounds the body read too (readBody).
 */
export async function fetchTextWithRetry(
  url: string,
  opts: FetchOpts & { accept?: string; notFoundAsNull?: boolean } = {},
): Promise<string | null> {
  const {
    retries = 4,
    timeoutMs = 30_000,
    headers = {},
    accept = "text/html",
    notFoundAsNull = false,
  } = opts;
  return requestWithRetry<string | null>(
    "GET",
    url,
    (signal) => fetch(url, { headers: { Accept: accept, ...headers }, signal }),
    (text) => text,
    { retries, timeoutMs },
    notFoundAsNull ? { value: null } : undefined,
  );
}

/**
 * POST a JSON body and read JSON back, with the SAME retry SCOPE discipline as fetchJsonWithRetry
 * (memory: fetch-retry-scope-gotcha): network/abort failures, transient body-read failures, 429 and 5xx
 * are retried; a non-retriable 4xx (e.g. a 400/401/403 for a bad or absent API key) throws IMMEDIATELY
 * instead of burning the retry budget. The timeout bounds the body read too (readBody). The transport is
 * injectable (default global `fetch`) so tests need no network. Returns the parsed JSON body.
 */
export async function postJsonWithRetry(
  url: string,
  body: unknown,
  opts: PostOpts = {},
): Promise<unknown> {
  const {
    retries = 4,
    timeoutMs = 30_000,
    headers = {},
    transport = fetch as unknown as FetchLike,
  } = opts;
  const payload = JSON.stringify(body);
  return requestWithRetry<unknown>(
    "POST",
    url,
    (signal) =>
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
    (text) => JSON.parse(text) as unknown,
    { retries, timeoutMs },
  );
}
