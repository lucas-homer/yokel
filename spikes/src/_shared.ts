/**
 * Shared helpers for the Week-1 validation spikes.
 *   - env loading (.env via dotenv)
 *   - data/ + out/ paths and writers (both gitignored)
 *   - fetchJson with retry/backoff + a simple rate limiter (Regs.gov is 1,000/hr)
 *   - DuckDB convenience wrappers
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { config as dotenvConfig } from "dotenv";
import { DuckDBInstance, type DuckDBConnection } from "@duckdb/node-api";

const HERE = dirname(fileURLToPath(import.meta.url));
export const SPIKES_ROOT = resolve(HERE, "..");
export const DATA_DIR = resolve(SPIKES_ROOT, "data");
export const OUT_DIR = resolve(SPIKES_ROOT, "out");

dotenvConfig({ path: resolve(SPIKES_ROOT, ".env") });

function ensureDirs(): void {
  mkdirSync(DATA_DIR, { recursive: true });
  mkdirSync(OUT_DIR, { recursive: true });
}

/** Write a JSON artifact to data/<name>. */
export function writeData(name: string, data: unknown): string {
  ensureDirs();
  const path = resolve(DATA_DIR, name);
  writeFileSync(path, JSON.stringify(data, null, 2));
  return path;
}

/** Write a markdown artifact to out/<name>. */
export function writeOut(name: string, markdown: string): string {
  ensureDirs();
  const path = resolve(OUT_DIR, name);
  writeFileSync(path, markdown);
  return path;
}

export const sleep = (ms: number): Promise<void> =>
  new Promise((r) => setTimeout(r, ms));

/** Today's date as YYYY-MM-DD in the given IANA zone (default Eastern). */
export function today(zone = "America/New_York"): string {
  const fmt = new Intl.DateTimeFormat("en-CA", {
    timeZone: zone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
  return fmt.format(new Date());
}

/** Min-interval gate so we never exceed a per-hour API budget. */
export class RateLimiter {
  private last = 0;
  constructor(private readonly minIntervalMs: number) {}
  /** requests/hour -> a limiter that spaces calls evenly under that budget. */
  static perHour(reqPerHour: number): RateLimiter {
    return new RateLimiter(Math.ceil(3_600_000 / reqPerHour));
  }
  async wait(): Promise<void> {
    const now = Date.now();
    const waitMs = this.last + this.minIntervalMs - now;
    if (waitMs > 0) await sleep(waitMs);
    this.last = Date.now();
  }
}

export interface FetchOpts {
  headers?: Record<string, string>;
  /** retries on 429/5xx (default 5) */
  retries?: number;
  limiter?: RateLimiter;
  timeoutMs?: number;
}

/** GET JSON with exponential backoff on 429/5xx, honoring Retry-After. */
export async function fetchJson<T = unknown>(
  url: string,
  opts: FetchOpts = {},
): Promise<T> {
  const { headers = {}, retries = 5, limiter, timeoutMs = 30_000 } = opts;
  let attempt = 0;
  for (;;) {
    if (limiter) await limiter.wait();
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), timeoutMs);
    try {
      const res = await fetch(url, {
        headers: { Accept: "application/json", ...headers },
        signal: ctrl.signal,
      });
      if (res.ok) return (await res.json()) as T;

      const retriable = res.status === 429 || res.status >= 500;
      if (!retriable || attempt >= retries) {
        const body = await res.text().catch(() => "");
        throw new Error(
          `GET ${url} -> ${res.status} ${res.statusText}${body ? `: ${body.slice(0, 300)}` : ""}`,
        );
      }
      const retryAfter = Number(res.headers.get("retry-after"));
      const backoff = Number.isFinite(retryAfter) && retryAfter > 0
        ? retryAfter * 1000
        : Math.min(30_000, 500 * 2 ** attempt);
      console.warn(`  ${res.status} on attempt ${attempt + 1}; retrying in ${backoff}ms`);
      await sleep(backoff);
      attempt++;
    } catch (err) {
      if (attempt >= retries) throw err;
      const backoff = Math.min(30_000, 500 * 2 ** attempt);
      console.warn(`  fetch error (${String(err)}); retry in ${backoff}ms`);
      await sleep(backoff);
      attempt++;
    } finally {
      clearTimeout(timer);
    }
  }
}

/** Build a query string from params, encoding bracketed keys (FR/JSON:API style). */
export function qs(params: Record<string, string | number | undefined>): string {
  const parts: string[] = [];
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined) continue;
    parts.push(`${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`);
  }
  return parts.join("&");
}

/** Open an in-memory DuckDB, run fn, always close. */
export async function withDuckDB<T>(
  fn: (conn: DuckDBConnection) => Promise<T>,
): Promise<T> {
  const instance = await DuckDBInstance.create(":memory:");
  const conn = await instance.connect();
  try {
    return await fn(conn);
  } finally {
    conn.closeSync();
  }
}

/** Run a query and return plain row objects. */
export async function rows<T = Record<string, unknown>>(
  conn: DuckDBConnection,
  sql: string,
): Promise<T[]> {
  const reader = await conn.runAndReadAll(sql);
  return reader.getRowObjects() as T[];
}
