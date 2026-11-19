/**
 * alerts.test.ts — the cloud alert rules (src/alerts/):
 *   - evaluate(): each Mini rule ported (poller, passes, llm, accuracy, api, daily review nag), and the
 *     "no input → no ping" rule for checks whose pass did not run;
 *   - report.ts: config parsing, delivery URLs (hc-ping.com/<key>/<slug>[/fail]), never throws;
 *   - recentPassFailures(): the poll_cycles look-back (needs a THROWAWAY Postgres, like cycle-log.test.ts).
 *
 *   DATABASE_URL=postgres://... tsx test/alerts.test.ts
 */
import { createClient } from "../src/db/client.js";
import { runMigrations } from "../src/db/migrate.js";
import { CHECKS, RULES } from "../src/alerts/checks.js";
import {
  evaluate,
  isDailyNagSlot,
  type CycleSignals,
  type Ping,
} from "../src/alerts/evaluate.js";
import {
  alertConfig,
  deliver,
  probeApi,
  recentPassFailures,
} from "../src/alerts/report.js";
import { recordPollCycle, type PassRecord } from "../src/poll/cycle-log.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

const ok = (name: string, summary: PassRecord["summary"] = {}): PassRecord => ({
  name,
  ok: true,
  ms: 1,
  summary,
});
const bad = (name: string, error = "boom"): PassRecord => ({
  name,
  ok: false,
  ms: 1,
  summary: {},
  error,
});

const NOT_NAG = new Date("2026-11-19T10:31:00Z");
const NAG = new Date(`2026-11-19T${RULES.dailyNagUtcHour}:00:30Z`);

const base = (over: Partial<CycleSignals> = {}): CycleSignals => ({
  now: NOT_NAG,
  outcome: "ok",
  passes: [
    ok("chain", { llmCalls: 10, llmErrors: 0 }),
    ok("verify"),
    ok("queue_stats"),
  ],
  recentPassFailures: [],
  accuracy: { ratio: 0.99, sample: 50 },
  queue: { escalated: 0, oldestAgeSeconds: 3600 },
  api: null,
  ...over,
});

const ping = (pings: Ping[], check: Ping["check"]) =>
  pings.find((p) => p.check === check);

try {
  // ── evaluate ─────────────────────────────────────────────────────────────────────────────────────
  {
    const ev = evaluate(base());
    assert(
      "healthy cycle: poller, passes, llm, accuracy all succeed",
      ["poller", "passes", "llm", "accuracy"].every(
        (c) => ping(ev.pings, c as Ping["check"])?.kind === "success",
      ),
    );
    assert(
      "healthy cycle: no api ping when not probed",
      !ping(ev.pings, "api"),
    );
    assert("healthy cycle: no nag", ev.nag === null);
  }
  {
    const ev = evaluate(base({ outcome: "failed", passes: [] }));
    assert(
      "failed cycle → poller /fail",
      ping(ev.pings, "poller")?.kind === "fail",
    );
    assert("failed cycle → only the poller ping", ev.pings.length === 1);
  }
  {
    const ev = evaluate(
      base({ outcome: "failed", passes: [], api: { ok: true, detail: "200" } }),
    );
    assert(
      "failed cycle still reports the API probe",
      ping(ev.pings, "api")?.kind === "success",
    );
  }
  {
    const ev = evaluate(base({ outcome: "skipped", passes: [] }));
    assert(
      "skipped cycle → poller success (scheduler alive)",
      ping(ev.pings, "poller")?.kind === "success",
    );
    assert("skipped cycle → no other checks", ev.pings.length === 1);
  }
  {
    const ev = evaluate(
      base({
        outcome: "pass_failed",
        passes: [
          bad("fr"),
          ok("chain", { llmCalls: 1, llmErrors: 0 }),
          ok("verify"),
        ],
        recentPassFailures: [{ name: "fr", failures: 2, lastError: "x" }],
      }),
    );
    assert(
      "pass_failed cycle → poller still success",
      ping(ev.pings, "poller")?.kind === "success",
    );
    assert(
      "poller body names the failed pass",
      /fr/.test(ping(ev.pings, "poller")!.body),
    );
    assert(
      "2 failures in an hour → passes success",
      ping(ev.pings, "passes")?.kind === "success",
    );
  }
  {
    const ev = evaluate(
      base({
        outcome: "pass_failed",
        recentPassFailures: [
          {
            name: "regs",
            failures: RULES.passFailuresPerHour,
            lastError: "429",
          },
        ],
      }),
    );
    const p = ping(ev.pings, "passes");
    assert(
      "3 failures of one pass in an hour → passes /fail",
      p?.kind === "fail",
    );
    assert(
      "passes body names pass + error",
      /regs/.test(p!.body) && /429/.test(p!.body),
    );
  }
  {
    const ev = evaluate(base({ recentPassFailures: null }));
    assert("look-back unavailable → no passes ping", !ping(ev.pings, "passes"));
  }
  {
    const at = evaluate(
      base({ passes: [ok("chain", { llmCalls: 9, llmErrors: 3 })] }),
    );
    const over = evaluate(
      base({ passes: [ok("chain", { llmCalls: 9, llmErrors: 4 })] }),
    );
    assert(
      "3 LLM errors → llm success (rule is > 3)",
      ping(at.pings, "llm")?.kind === "success",
    );
    assert(
      "4 LLM errors → llm /fail",
      ping(over.pings, "llm")?.kind === "fail",
    );
    const failed = evaluate(base({ passes: [bad("chain"), ok("verify")] }));
    assert("chain pass failed → no llm ping", !ping(failed.pings, "llm"));
  }
  {
    const low = evaluate(base({ accuracy: { ratio: 0.9, sample: 40 } }));
    assert(
      "HIGH accuracy 90% on n=40 → accuracy /fail",
      ping(low.pings, "accuracy")?.kind === "fail",
    );
    const small = evaluate(base({ accuracy: { ratio: 0.5, sample: 5 } }));
    assert(
      "small sample → accuracy success (not judged)",
      ping(small.pings, "accuracy")?.kind === "success",
    );
    const none = evaluate(base({ accuracy: { ratio: null, sample: 0 } }));
    assert(
      "no sample → accuracy success",
      ping(none.pings, "accuracy")?.kind === "success",
    );
    const noVerify = evaluate(
      base({
        passes: [ok("chain", { llmCalls: 0, llmErrors: 0 }), bad("verify")],
      }),
    );
    assert(
      "verify failed → no accuracy ping",
      !ping(noVerify.pings, "accuracy"),
    );
  }
  {
    const down = evaluate(base({ api: { ok: false, detail: "503" } }));
    assert(
      "API probe not ok → api /fail",
      ping(down.pings, "api")?.kind === "fail",
    );
  }
  {
    assert("nag slot: 16:00Z", isDailyNagSlot(NAG));
    assert(
      "nag slot: not 16:15Z",
      !isDailyNagSlot(new Date("2026-11-19T16:15:00Z")),
    );
    const quiet = evaluate(base({ now: NAG }));
    assert("nag slot, empty queue → no nag", quiet.nag === null);
    const esc = evaluate(
      base({ now: NAG, queue: { escalated: 2, oldestAgeSeconds: 60 } }),
    );
    assert(
      "nag slot, escalations → nag",
      !!esc.nag && /2 escalated/.test(esc.nag.message),
    );
    const rot = evaluate(
      base({
        now: NAG,
        queue: { escalated: 0, oldestAgeSeconds: RULES.reviewRotSeconds + 1 },
      }),
    );
    assert(
      "nag slot, oldest conflict > 7d → nag",
      !!rot.nag && /oldest/.test(rot.nag.message),
    );
    const offSlot = evaluate(
      base({ queue: { escalated: 2, oldestAgeSeconds: 60 } }),
    );
    assert("escalations outside the nag slot → no nag", offSlot.nag === null);
  }

  // ── report: config + delivery ────────────────────────────────────────────────────────────────────
  {
    const cfg = alertConfig({
      HEALTHCHECKS_PING_KEY: " key123 ",
      NTFY_URL: "https://ntfy.sh/topic?template=grafana",
      DOCKETCLOCK_API_URL: "https://api.example/",
    });
    assert("config trims the ping key", cfg.pingKey === "key123");
    assert(
      "config drops the ntfy ?template query",
      cfg.ntfyUrl === "https://ntfy.sh/topic",
    );
    assert(
      "config drops the API URL's trailing slash",
      cfg.apiUrl === "https://api.example",
    );
    const off = alertConfig({});
    assert(
      "unset config → all off",
      !off.pingKey && !off.ntfyUrl && !off.apiUrl,
    );
  }
  {
    const calls: { url: string; body: string; title?: string }[] = [];
    const fake = (async (url: string, init: RequestInit) => {
      calls.push({
        url,
        body: String(init.body),
        title: (init.headers as Record<string, string>).Title,
      });
      return new Response("OK", { status: 200 });
    }) as unknown as typeof fetch;
    await deliver(
      { pingKey: "K", ntfyUrl: "https://ntfy.sh/t", apiUrl: "" },
      {
        pings: [
          { check: "poller", kind: "success", body: "a" },
          { check: "llm", kind: "fail", body: "b" },
          { check: "passes", kind: "log", body: "c" },
        ],
        nag: { title: "T", message: "m" },
      },
      fake,
    );
    const urls = calls.map((c) => c.url).sort();
    assert(
      "deliver: ping URLs are hc-ping.com/<key>/<slug>[/fail|/log]",
      urls.includes(`https://hc-ping.com/K/${CHECKS.poller.slug}`) &&
        urls.includes(`https://hc-ping.com/K/${CHECKS.llm.slug}/fail`) &&
        urls.includes(`https://hc-ping.com/K/${CHECKS.passes.slug}/log`),
      urls.join(" "),
    );
    assert(
      "deliver: nag goes to ntfy with a Title",
      calls.some(
        (c) =>
          c.url === "https://ntfy.sh/t" && c.title === "T" && c.body === "m",
      ),
    );
  }
  {
    const boom = (async () => {
      throw new Error("network down");
    }) as unknown as typeof fetch;
    let threw = false;
    try {
      await deliver(
        { pingKey: "K", ntfyUrl: "https://ntfy.sh/t", apiUrl: "" },
        {
          pings: [{ check: "poller", kind: "success", body: "" }],
          nag: { title: "t", message: "m" },
        },
        boom,
      );
    } catch {
      threw = true;
    }
    assert("deliver never throws on a network error", !threw);
    const probe = await probeApi("https://api.example", boom);
    assert(
      "probeApi: network error → not ok",
      !probe.ok && /network down/.test(probe.detail),
    );
    const r503 = await probeApi(
      "https://api.example",
      (async () =>
        new Response('{"status":"unavailable"}', {
          status: 503,
        })) as unknown as typeof fetch,
    );
    assert("probeApi: 503 → not ok", !r503.ok && /503/.test(r503.detail));
    const r200 = await probeApi(
      "https://api.example",
      (async () =>
        new Response('{"status":"ok"}', {
          status: 200,
        })) as unknown as typeof fetch,
    );
    assert("probeApi: 200 → ok", r200.ok);
  }

  // ── recentPassFailures (DB) ──────────────────────────────────────────────────────────────────────
  const sql = createClient();
  try {
    await sql.unsafe(
      "drop schema if exists public cascade; create schema public;",
    );
    await runMigrations(sql);
    const now = Date.now();
    const cycle = (minsAgo: number, passes: PassRecord[]) =>
      recordPollCycle(sql, {
        startedAt: new Date(now - minsAgo * 60_000),
        finishedAt: new Date(now - minsAgo * 60_000 + 1000),
        outcome: passes.every((p) => p.ok) ? "ok" : "pass_failed",
        runOnce: true,
        traceId: null,
        passes,
      });
    await cycle(90, [bad("regs", "too old")]); // outside the hour
    await cycle(45, [bad("regs", "first"), ok("fr")]);
    await cycle(30, [bad("regs", "second"), bad("fr", "fr-err")]);
    await cycle(15, [ok("regs"), ok("fr")]);
    await cycle(1, [bad("regs", "latest")]);
    const got = await recentPassFailures(sql);
    const regs = got.find((g) => g.name === "regs");
    const fr = got.find((g) => g.name === "fr");
    assert(
      "look-back counts only the last hour",
      regs?.failures === 3,
      JSON.stringify(got),
    );
    assert("look-back carries the newest error", regs?.lastError === "latest");
    assert("look-back counts each pass separately", fr?.failures === 1);
  } finally {
    await sql.end({ timeout: 5 });
  }
} catch (err) {
  failures++;
  out.push(`  FAIL  unexpected error — ${String(err)}`);
}

console.log(`alerts.test.ts\n${out.join("\n")}`);
console.log(failures === 0 ? "ALL PASS" : `${failures} FAILURE(S)`);
process.exit(failures === 0 ? 0 : 1);
