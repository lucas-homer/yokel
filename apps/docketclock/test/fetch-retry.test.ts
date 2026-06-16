/**
 * fetch-retry.test.ts — proves fetchFrDocument's retry SCOPE (memory: fetch-retry-scope-gotcha).
 *
 * The subtlest code in the FR adapter is what it retries vs. what it fails fast on. This stubs
 * globalThis.fetch (NO network, NO Postgres) and asserts the load-bearing branches:
 *   - a 404/4xx fails IMMEDIATELY (one call, no backoff) — must NOT burn retries;
 *   - a transient 5xx is retried and then succeeds;
 *   - a network error is retried and then succeeds;
 *   - a persistent 5xx exhausts the retry budget and throws (attempts = retries + 1).
 *
 * Run: pnpm --filter @yokel/docketclock test
 */
import { fetchFrDocument } from "../src/sources/federal-register.js";

let failures = 0;
const log: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  log.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}
/** Assert that an async op rejects, and that the thrown message matches. */
async function rejects(name: string, op: () => Promise<unknown>, re: RegExp) {
  try {
    await op();
    assert(name, false, "operation SUCCEEDED — expected a throw");
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    assert(name, re.test(msg), msg);
  }
}

const realFetch = globalThis.fetch;
/**
 * Install a fetch stub that returns/throws the programmed steps in order, counting calls. A step is
 * either a () => Response thunk or a () => throw (to simulate a network error). The call count proves
 * how many attempts happened.
 */
function stubFetch(steps: Array<() => Response>): { calls: () => number } {
  let i = 0;
  let calls = 0;
  globalThis.fetch = (async () => {
    calls++;
    const step = steps[Math.min(i, steps.length - 1)];
    i++;
    return step!();
  }) as typeof fetch;
  return { calls: () => calls };
}

const okJson = (body: unknown) =>
  new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
  });

try {
  // ── 404 fast-fails: ONE call, no retry, message carries the status ───────────────────────────────
  {
    const f = stubFetch([() => new Response("not found", { status: 404 })]);
    await rejects(
      "404 throws immediately",
      () => fetchFrDocument("nope", { retries: 4 }),
      /404/,
    );
    assert(
      "404 is not retried (exactly one fetch call)",
      f.calls() === 1,
      `calls=${f.calls()}`,
    );
  }

  // A different 4xx (422) is likewise non-retriable.
  {
    const f = stubFetch([() => new Response("bad", { status: 422 })]);
    await rejects(
      "422 throws immediately",
      () => fetchFrDocument("bad", { retries: 4 }),
      /422/,
    );
    assert(
      "422 is not retried (exactly one fetch call)",
      f.calls() === 1,
      `calls=${f.calls()}`,
    );
  }

  // ── transient 5xx then success: retried, then returns the parsed body ─────────────────────────────
  {
    const f = stubFetch([
      () => new Response("boom", { status: 503 }),
      () => okJson({ document_number: "2025-02910" }),
    ]);
    const body = (await fetchFrDocument("2025-02910", { retries: 4 })) as {
      document_number: string;
    };
    assert(
      "503-then-200 retries and returns the parsed body",
      body.document_number === "2025-02910",
      JSON.stringify(body),
    );
    assert(
      "503-then-200 took exactly two fetch calls",
      f.calls() === 2,
      `calls=${f.calls()}`,
    );
  }

  // ── network error then success: the catch-branch retry path ───────────────────────────────────────
  {
    const f = stubFetch([
      () => {
        throw new TypeError("fetch failed");
      },
      () => okJson({ document_number: "abc" }),
    ]);
    const body = (await fetchFrDocument("abc", { retries: 4 })) as {
      document_number: string;
    };
    assert(
      "network-error-then-200 retries and returns the body",
      body.document_number === "abc",
      JSON.stringify(body),
    );
    assert(
      "network-error-then-200 took exactly two fetch calls",
      f.calls() === 2,
      `calls=${f.calls()}`,
    );
  }

  // ── persistent 5xx exhausts the budget: attempts = retries + 1, then throws ───────────────────────
  {
    const f = stubFetch([() => new Response("down", { status: 500 })]);
    await rejects(
      "persistent 500 throws after exhausting retries",
      () => fetchFrDocument("down", { retries: 1 }),
      /500/,
    );
    assert(
      "persistent 500 with retries=1 makes exactly two attempts",
      f.calls() === 2,
      `calls=${f.calls()}`,
    );
  }
} finally {
  globalThis.fetch = realFetch;
}

console.log("\n=== fetch-retry results ===");
console.log(log.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
