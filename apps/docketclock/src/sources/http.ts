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

export interface FetchOpts {
  /** retries on network errors / 429 / 5xx only (default 4). 4xx never retries. */
  retries?: number;
  timeoutMs?: number;
  /** extra request headers (e.g. an X-Api-Key for keyed sources). Accept: application/json is added. */
  headers?: Record<string, string>;
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

    // Retriable (429 / 5xx): back off, honoring Retry-After when present.
    const retryAfter = Number(res.headers.get("retry-after"));
    const backoff =
      Number.isFinite(retryAfter) && retryAfter > 0
        ? retryAfter * 1000
        : Math.min(30_000, 500 * 2 ** attempt);
    attempt++;
    await sleep(backoff);
  }
}
