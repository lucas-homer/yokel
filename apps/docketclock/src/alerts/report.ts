/**
 * alerts/report.ts — the I/O around alerts/evaluate.ts: gather the signals evaluate() needs that the
 * cycle did not already hold, then deliver its pings (healthchecks.io) and its daily nag (ntfy).
 *
 * Configuration (all optional; unset = that part is off, so local, test and Mac mini runs send nothing):
 *   HEALTHCHECKS_PING_KEY  the healthchecks.io project's ping key (pings go to hc-ping.com/<key>/<slug>)
 *   NTFY_URL               the ntfy topic URL for the daily nag (a `?template=` query is dropped)
 *   DOCKETCLOCK_API_URL    the API's base URL, probed at /readyz once an hour
 *
 * NEVER THROWS, and every request has a timeout: an alerting hiccup must not fail or hang the cycle.
 */
import type { Sql } from "../db/client.js";
import { componentLogger } from "../log.js";
import { CHECKS } from "./checks.js";
import type { Evaluation, PassFailureCount } from "./evaluate.js";

const log = componentLogger("alerts");

const TIMEOUT_MS = 10_000;
const PING_BASE = "https://hc-ping.com";

export interface AlertConfig {
  pingKey: string;
  ntfyUrl: string;
  apiUrl: string;
}

export function alertConfig(env: NodeJS.ProcessEnv = process.env): AlertConfig {
  const ntfy = (env.NTFY_URL ?? "").trim();
  return {
    pingKey: (env.HEALTHCHECKS_PING_KEY ?? "").trim(),
    ntfyUrl: ntfy ? ntfy.split("?")[0]! : "",
    apiUrl: (env.DOCKETCLOCK_API_URL ?? "").trim().replace(/\/+$/, ""),
  };
}

/** Per-pass failure counts over the last hour of poll_cycles (the current cycle's row included). */
export async function recentPassFailures(
  sql: Sql,
): Promise<PassFailureCount[]> {
  const rows = await sql<
    { name: string; failures: string; last_error: string | null }[]
  >`
    select p->>'name' as name,
           count(*) as failures,
           (array_agg(p->>'error' order by c.started_at desc))[1] as last_error
    from poll_cycles c, jsonb_array_elements(c.passes) p
    where c.started_at > now() - interval '1 hour'
      and (p->>'ok')::boolean = false
    group by 1
  `;
  return rows.map((r) => ({
    name: r.name,
    failures: Number(r.failures),
    lastError: r.last_error,
  }));
}

/** GET <api>/readyz. Any non-200, timeout or network error is "not ok". */
export async function probeApi(
  apiUrl: string,
  fetchImpl: typeof fetch = fetch,
): Promise<{ ok: boolean; detail: string }> {
  const url = `${apiUrl}/readyz`;
  try {
    const res = await fetchImpl(url, {
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    const text = (await res.text()).slice(0, 200);
    return {
      ok: res.status === 200,
      detail: `GET /readyz → ${res.status} ${text}`,
    };
  } catch (err) {
    return {
      ok: false,
      detail: `GET /readyz failed: ${err instanceof Error ? err.message : String(err)}`,
    };
  }
}

const SUFFIX = { success: "", fail: "/fail", log: "/log" } as const;

/** Send every ping and the nag, in parallel. Logs failures; never throws. */
export async function deliver(
  cfg: AlertConfig,
  ev: Evaluation,
  fetchImpl: typeof fetch = fetch,
): Promise<void> {
  const sends: Promise<void>[] = [];
  if (cfg.pingKey) {
    for (const p of ev.pings) {
      const url = `${PING_BASE}/${cfg.pingKey}/${CHECKS[p.check].slug}${SUFFIX[p.kind]}`;
      sends.push(
        post(fetchImpl, url, p.body, {}).then((ok) => {
          if (p.kind === "fail") {
            log.warn(
              { check: p.check, body: p.body, delivered: ok },
              "alert firing",
            );
          }
        }),
      );
    }
  }
  if (cfg.ntfyUrl && ev.nag) {
    sends.push(
      post(fetchImpl, cfg.ntfyUrl, ev.nag.message, {
        Title: ev.nag.title,
        Tags: "clipboard",
      }).then((ok) => log.info({ delivered: ok }, "daily review nag sent")),
    );
  }
  await Promise.all(sends);
}

async function post(
  fetchImpl: typeof fetch,
  url: string,
  body: string,
  headers: Record<string, string>,
): Promise<boolean> {
  // The ping key and ntfy topic are secrets: log the host only.
  const host = new URL(url).host;
  try {
    const res = await fetchImpl(url, {
      method: "POST",
      body,
      headers: { "content-type": "text/plain", ...headers },
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    if (!res.ok)
      log.warn({ host, status: res.status }, "alert delivery rejected");
    return res.ok;
  } catch (err) {
    log.warn({ host, err: String(err) }, "alert delivery failed");
    return false;
  }
}
