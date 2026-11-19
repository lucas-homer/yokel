/**
 * sync-healthchecks.ts — apply the cloud alert checks (src/alerts/checks.ts) to healthchecks.io, so the
 * checks are defined in git and nothing is set up by hand. Run by .github/workflows/alerts-sync.yml.
 *
 *   HEALTHCHECKS_API_KEY=... tsx scripts/sync-healthchecks.ts [--dry-run]
 *
 * For each check: create it if no check has its slug, otherwise update name, timeout, grace and description
 * in place (its ping history and status are kept). Every check is attached to ALL of the project's
 * integrations (`channels: "*"`), so the ntfy integration set up in the healthchecks.io project pages for
 * all of them. Checks in the project that are not in checks.ts are listed, never deleted.
 *
 * The API key is the project's read-write key (healthchecks.io → project Settings → API Access). It is
 * never printed.
 */
import { CHECKS, type HealthcheckDef } from "../src/alerts/checks.js";

const API = "https://healthchecks.io/api/v3";
const dryRun = process.argv.includes("--dry-run");
const key = process.env.HEALTHCHECKS_API_KEY?.trim();
if (!key) {
  console.error("HEALTHCHECKS_API_KEY is not set");
  process.exit(1);
}

interface RemoteCheck {
  name: string;
  slug: string;
  timeout?: number;
  grace: number;
  desc: string;
  status: string;
  update_url: string;
}

async function api(path: string, init: RequestInit = {}): Promise<unknown> {
  const url = path.startsWith("http") ? path : `${API}${path}`;
  const res = await fetch(url, {
    ...init,
    headers: { "X-Api-Key": key!, "content-type": "application/json" },
    signal: AbortSignal.timeout(20_000),
  });
  const text = await res.text();
  if (!res.ok)
    throw new Error(
      `${init.method ?? "GET"} ${path} → ${res.status} ${text.slice(0, 300)}`,
    );
  return text ? JSON.parse(text) : null;
}

const body = (c: HealthcheckDef) => ({
  name: c.name,
  slug: c.slug,
  timeout: c.timeout,
  grace: c.grace,
  desc: c.desc,
  tags: "docketclock cloud",
  channels: "*",
});

const { checks: remote } = (await api("/checks/")) as { checks: RemoteCheck[] };
const bySlug = new Map(remote.map((r) => [r.slug, r]));

for (const c of Object.values(CHECKS)) {
  const existing = bySlug.get(c.slug);
  const verb = existing ? "update" : "create";
  console.log(
    `${dryRun ? "[dry-run] " : ""}${verb} ${c.slug} (every ${c.timeout / 60}m, grace ${c.grace / 60}m)` +
      (existing ? ` — now ${existing.status}` : ""),
  );
  if (dryRun) continue;
  if (existing) {
    await api(existing.update_url, {
      method: "POST",
      body: JSON.stringify(body(c)),
    });
  } else {
    await api("/checks/", { method: "POST", body: JSON.stringify(body(c)) });
  }
}

const ours = new Set<string>(Object.values(CHECKS).map((c) => c.slug));
for (const r of remote) {
  if (!ours.has(r.slug))
    console.log(
      `not managed here (left alone): ${r.slug || r.name} — ${r.status}`,
    );
}
