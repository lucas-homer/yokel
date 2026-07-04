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

/** GET a URL as JSON, with exponential backoff on RETRIABLE failures only. */
export async function fetchJsonWithRetry(
  url: string,
  opts: FetchOpts = {},
): Promise<unknown> {
  const { retries = 4, timeoutMs = 30_000, headers = {} } = opts;
  let attempt = 0;

  for (;;) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), timeoutMs);

    // Only network/abort failures are caught here (retriable). HTTP-status handling lives OUTSIDE this
    // try, so a non-retriable 4xx throw propagates immediately instead of being retried.
    let res: Response;
    try {
      res = await fetch(url, {
        headers: { Accept: "application/json", ...headers },
        signal: ctrl.signal,
      });
    } catch (err) {
      clearTimeout(timer);
      if (attempt >= retries) throw err;
      const backoff = Math.min(30_000, 500 * 2 ** attempt);
      attempt++;
      await sleep(backoff);
      continue;
    }
    clearTimeout(timer);

    if (res.ok) return (await res.json()) as unknown;

    // 4xx (other than 429) is non-retriable — a 404/422 must fail fast, not burn retries.
    const retriable = res.status === 429 || res.status >= 500;
    if (!retriable || attempt >= retries) {
      const body = await res.text().catch(() => "");
      throw new Error(
        `GET ${url} -> ${res.status} ${res.statusText}${body ? `: ${body.slice(0, 300)}` : ""}`,
      );
    }

    // Retriable (429 / 5xx): back off, honoring (a capped) Retry-After when present.
    const backoff = retriableBackoffMs(res, attempt);
    attempt++;
    await sleep(backoff);
  }
}

/**
 * POST a JSON body and read JSON back, with the SAME retry SCOPE discipline as fetchJsonWithRetry
 * (memory: fetch-retry-scope-gotcha): ONLY the `await transport()` (network/abort) is inside the
 * try/catch — retriable. HTTP-status handling lives OUTSIDE it, so a non-retriable 4xx (e.g. a 400/401/403
 * for a bad or absent API key) throws IMMEDIATELY instead of burning the retry budget. We retry ONLY
 * network/abort errors, 429, and 5xx.
 *
 * The timeout is enforced with an AbortController per attempt; an abort surfaces as a thrown (network-like)
 * error that is itself retriable. The transport is injectable (default global `fetch`) so tests need no
 * network. Returns the parsed JSON body.
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
  let attempt = 0;

  for (;;) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), timeoutMs);

    // Only network/abort failures are caught here (retriable). HTTP-status handling lives OUTSIDE this
    // try, so a non-retriable 4xx throw propagates immediately instead of being retried.
    let res: Response;
    try {
      res = await transport(url, {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          ...headers,
        },
        body: payload,
        signal: ctrl.signal,
      });
    } catch (err) {
      clearTimeout(timer);
      if (attempt >= retries) throw err;
      const backoff = Math.min(30_000, 500 * 2 ** attempt);
      attempt++;
      await sleep(backoff);
      continue;
    }
    clearTimeout(timer);

    if (res.ok) return (await res.json()) as unknown;

    // 4xx (other than 429) is non-retriable — a 400/401/403 (bad/absent key) must fail fast.
    const retriable = res.status === 429 || res.status >= 500;
    if (!retriable || attempt >= retries) {
      const errBody = await res.text().catch(() => "");
      throw new Error(
        `POST ${url} -> ${res.status} ${res.statusText}${errBody ? `: ${errBody.slice(0, 300)}` : ""}`,
      );
    }

    // Retriable (429 / 5xx): back off, honoring (a capped) Retry-After when present.
    const backoff = retriableBackoffMs(res, attempt);
    attempt++;
    await sleep(backoff);
  }
}
