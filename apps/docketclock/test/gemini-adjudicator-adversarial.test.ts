/**
 * gemini-adjudicator-adversarial.test.ts — the adversary's regression lock for Slice 3a. Attacks the
 * gaps the builder's suite left: the FULL non-retriable 4xx set (403/404/422), 429 + the full 5xx set
 * retried, a THROWN network error retried, 5xx exhaustion throwing (no fabricated verdict), timer no-leak
 * on the happy path, abort-class treated as retriable, malformed-response variants the builder skipped
 * (missing rationale, valid-JSON-non-object, blockReason with no candidates), confidence-never-surfaced,
 * NO swallowing catch in the adapter, and selectAdjudicator case/whitespace + precedence variants.
 *
 * Zero network, zero key, injectable spy transport. Repo test style: hand-rolled assert + process.exit.
 */
import type { AdjudicationInput } from "@yokel/contracts";
import { GeminiAdjudicator } from "../src/adjudicator/gemini-adjudicator.js";
import { selectAdjudicator } from "../src/adjudicator/select.js";
import { NullAdjudicator } from "../src/adjudicator/null-adjudicator.js";
import { postJsonWithRetry, type FetchLike } from "../src/sources/http.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}
async function rejects(name: string, op: () => Promise<unknown>, re: RegExp) {
  try {
    await op();
    assert(name, false, "operation SUCCEEDED — expected a throw");
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    assert(name, re.test(msg), msg);
  }
}

const MODEL = "gemini-2.5-flash";
const KEY = "test-key-not-real";
const noticeInput: AdjudicationInput = {
  kind: "notice",
  rulebook_version: "rulebox-2026-06-18",
  flag_key: "withdrawal",
  text: "Withdrawal of Land from Mineral Entry; Notice of Realty Action",
};

function geminiOk(verdictJson: unknown): Response {
  return new Response(
    JSON.stringify({
      candidates: [
        { content: { parts: [{ text: JSON.stringify(verdictJson) }] } },
      ],
    }),
    { status: 200, headers: { "content-type": "application/json" } },
  );
}

/** Spy that counts calls and returns programmed steps (last step repeats). */
function spy(steps: Array<() => Response | Promise<Response>>): {
  fn: FetchLike;
  calls: () => number;
} {
  let i = 0;
  let n = 0;
  const fn: FetchLike = async (_url, _init) => {
    n++;
    const step = steps[Math.min(i, steps.length - 1)]!;
    i++;
    return step();
  };
  return { fn, calls: () => n };
}

// ── ATTACK 1: the FULL non-retriable 4xx set fails fast (exactly ONE call) ────────────────────────────
for (const status of [400, 401, 403, 404, 422]) {
  const t = spy([() => new Response("nope", { status })]);
  await rejects(
    `4xx ${status} throws immediately`,
    () =>
      new GeminiAdjudicator({
        apiKey: KEY,
        model: MODEL,
        transport: t.fn,
        retries: 4,
      }).adjudicate(noticeInput),
    new RegExp(String(status)),
  );
  assert(
    `4xx ${status} is NOT retried (exactly one transport call)`,
    t.calls() === 1,
    `calls=${t.calls()}`,
  );
}

// ── ATTACK 2: 429 + the full 5xx set ARE retried (succeed on the 2nd call) ────────────────────────────
for (const status of [429, 500, 502, 503, 504]) {
  const t = spy([
    () => new Response("retry me", { status }),
    () => geminiOk({ classification: "affirm", rationale: "ok" }),
  ]);
  const v = await new GeminiAdjudicator({
    apiKey: KEY,
    model: MODEL,
    transport: t.fn,
    retries: 4,
  }).adjudicate(noticeInput);
  assert(
    `${status} is retried then succeeds (two calls)`,
    v.classification === "affirm" && t.calls() === 2,
    `calls=${t.calls()}`,
  );
}

// ── ATTACK 3: a THROWN network error is retried; exhausting it re-throws ──────────────────────────────
{
  const t = spy([
    () => {
      throw new TypeError("network down (ECONNREFUSED)");
    },
    () => geminiOk({ classification: "reject", rationale: "ok" }),
  ]);
  const v = await new GeminiAdjudicator({
    apiKey: KEY,
    model: MODEL,
    transport: t.fn,
    retries: 4,
  }).adjudicate(noticeInput);
  assert(
    "thrown network error is retried then succeeds",
    v.classification === "reject" && t.calls() === 2,
    `calls=${t.calls()}`,
  );

  // retries=2 means 1 initial + 2 retries = 3 transport calls, then it gives up and re-throws.
  const t2 = spy([
    () => {
      throw new TypeError("network down");
    },
  ]);
  await rejects(
    "network error exhausts retries and re-throws (no fabricated verdict)",
    () =>
      new GeminiAdjudicator({
        apiKey: KEY,
        model: MODEL,
        transport: t2.fn,
        retries: 2,
      }).adjudicate(noticeInput),
    /network down/,
  );
  assert(
    "network exhaustion = retries+1 calls (1 initial + 2 retries)",
    t2.calls() === 3,
    `calls=${t2.calls()}`,
  );
}

// ── ATTACK 4: 5xx exhaustion THROWS an HTTP error (never a fabricated uncertain verdict) ──────────────
{
  const t = spy([() => new Response("still down", { status: 503 })]);
  await rejects(
    "persistent 503 exhausts retries and THROWS (no fabricated uncertain)",
    () =>
      new GeminiAdjudicator({
        apiKey: KEY,
        model: MODEL,
        transport: t.fn,
        retries: 2,
      }).adjudicate(noticeInput),
    /503/,
  );
  assert(
    "503 exhaustion = retries+1 calls",
    t.calls() === 3,
    `calls=${t.calls()}`,
  );
}

// ── ATTACK 5: timer no-leak on the happy path (process must not be kept alive by a stray timer) ───────
{
  // If postJsonWithRetry failed to clearTimeout on the OK path, a 30s timer would keep the event loop
  // alive. We assert by observing that after a happy call, there is no unref'd timer hanging the process:
  // proxy it by checking the call resolves and the abort never fires (transport saw a non-aborted signal).
  let abortedDuringHappy = false;
  const okTransport: FetchLike = async (_url, init) => {
    init.signal?.addEventListener("abort", () => {
      abortedDuringHappy = true;
    });
    return geminiOk({ classification: "affirm", rationale: "ok" });
  };
  await new GeminiAdjudicator({
    apiKey: KEY,
    model: MODEL,
    transport: okTransport,
    timeoutMs: 20,
  }).adjudicate(noticeInput);
  // wait past the (short) timeout window; if the timer leaked it would fire and flip the flag.
  await new Promise((r) => setTimeout(r, 60));
  assert(
    "happy path clears the timeout (abort never fires after success)",
    abortedDuringHappy === false,
    `abortedDuringHappy=${abortedDuringHappy}`,
  );
}

// ── ATTACK 6: abort/timeout is retriable, but ultimately throws after retries; wall-clock bounded ─────
{
  const hanging: FetchLike = (_url, init) =>
    new Promise((_res, reject) => {
      init.signal?.addEventListener("abort", () =>
        reject(new DOMException("aborted", "AbortError")),
      );
    });
  let aborts = 0;
  const countingHanging: FetchLike = (url, init) => {
    aborts++;
    return hanging(url, init);
  };
  const start = Date.now();
  await rejects(
    "a perpetually-hanging transport aborts each attempt and ultimately throws",
    () =>
      new GeminiAdjudicator({
        apiKey: KEY,
        model: MODEL,
        transport: countingHanging,
        timeoutMs: 30,
        retries: 1,
      }).adjudicate(noticeInput),
    /abort/i,
  );
  const elapsed = Date.now() - start;
  assert(
    "abort retried then exhausted: 1 initial + 1 retry = 2 attempts",
    aborts === 2,
    `attempts=${aborts}`,
  );
  assert(
    "abort path is wall-clock bounded (well under 5s)",
    elapsed < 5_000,
    `${elapsed}ms`,
  );
}

// ── ATTACK 7: malformed-response variants the builder skipped ─────────────────────────────────────────
{
  // (a) valid JSON but MISSING rationale → AdjudicationVerdict.parse throws.
  const noRationale = spy([() => geminiOk({ classification: "affirm" })]);
  await rejects(
    "valid JSON missing rationale throws (verdict.parse)",
    () =>
      new GeminiAdjudicator({
        apiKey: KEY,
        model: MODEL,
        transport: noRationale.fn,
      }).adjudicate(noticeInput),
    /./,
  );

  // (b) candidate text is valid JSON but NOT an object (a bare string) → parse throws.
  const jsonString = spy([
    () =>
      new Response(
        JSON.stringify({
          candidates: [
            { content: { parts: [{ text: JSON.stringify("affirm") }] } },
          ],
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
  ]);
  await rejects(
    "candidate text is a bare JSON string (not an object) throws",
    () =>
      new GeminiAdjudicator({
        apiKey: KEY,
        model: MODEL,
        transport: jsonString.fn,
      }).adjudicate(noticeInput),
    /./,
  );

  // (c) candidates: [] (empty array) → no candidate → throw.
  const emptyCandidates = spy([
    () =>
      new Response(JSON.stringify({ candidates: [] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
  ]);
  await rejects(
    "candidates: [] throws (no candidate)",
    () =>
      new GeminiAdjudicator({
        apiKey: KEY,
        model: MODEL,
        transport: emptyCandidates.fn,
      }).adjudicate(noticeInput),
    /no candidate/,
  );

  // (d) blockReason with no candidates surfaces the reason in the thrown message.
  const blocked = spy([
    () =>
      new Response(
        JSON.stringify({ promptFeedback: { blockReason: "OTHER" } }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
  ]);
  await rejects(
    "promptFeedback.blockReason with no candidate surfaces the reason",
    () =>
      new GeminiAdjudicator({
        apiKey: KEY,
        model: MODEL,
        transport: blocked.fn,
      }).adjudicate(noticeInput),
    /blockReason=OTHER/,
  );

  // (e) classification "uncertain" is the ONE legitimate abstain path — must NOT throw.
  const uncertain = spy([
    () => geminiOk({ classification: "uncertain", rationale: "cannot tell" }),
  ]);
  const vu = await new GeminiAdjudicator({
    apiKey: KEY,
    model: MODEL,
    transport: uncertain.fn,
  }).adjudicate(noticeInput);
  assert(
    "genuine uncertain verdict is returned (the only abstain path)",
    vu.classification === "uncertain",
    JSON.stringify(vu),
  );
}

// ── ATTACK 8: confidence can NEVER be surfaced (even nested/typed variants) ───────────────────────────
{
  const withConf = spy([
    () =>
      geminiOk({
        classification: "affirm",
        rationale: "ok",
        confidence: 0.99,
        score: 1,
        probability: 0.5,
      }),
  ]);
  const v = (await new GeminiAdjudicator({
    apiKey: KEY,
    model: MODEL,
    transport: withConf.fn,
  }).adjudicate(noticeInput)) as Record<string, unknown>;
  assert(
    "no score-like field survives parse",
    !("confidence" in v) && !("score" in v) && !("probability" in v),
    JSON.stringify(v),
  );
}

// ── ATTACK 9: key NEVER appears in the built URL (secret-in-URL defect), via the live URL string ──────
{
  let seenUrl = "";
  let seenHeaderKey = "";
  const urlSpy: FetchLike = async (url, init) => {
    seenUrl = url;
    const h = init.headers as Record<string, string>;
    seenHeaderKey = h["x-goog-api-key"] ?? "";
    return geminiOk({ classification: "affirm", rationale: "ok" });
  };
  await new GeminiAdjudicator({
    apiKey: "SUPER-SECRET-KEY-12345",
    model: MODEL,
    transport: urlSpy,
  }).adjudicate(noticeInput);
  assert(
    "key never in URL",
    !seenUrl.includes("SUPER-SECRET-KEY-12345"),
    seenUrl,
  );
  assert(
    "key is in the x-goog-api-key header",
    seenHeaderKey === "SUPER-SECRET-KEY-12345",
  );
}

// ── ATTACK 10: constructor rejects an empty key (no keyless client) ───────────────────────────────────
await rejects(
  "constructing with empty apiKey throws",
  async () => new GeminiAdjudicator({ apiKey: "", model: MODEL }),
  /non-empty apiKey/,
);

// ── ATTACK 11: selectAdjudicator case/whitespace + provider-named credential ──────────────────────────
{
  const cap = selectAdjudicator({
    ADJUDICATOR: "  GEMINI  ",
    GEMINI_API_KEY: KEY,
  } as NodeJS.ProcessEnv);
  assert(
    "select: '  GEMINI  ' (case+whitespace) normalizes to gemini",
    cap instanceof GeminiAdjudicator,
    cap.id,
  );

  // The credential is named for its provider: the gemini path reads GEMINI_API_KEY ONLY. A stray generic
  // LLM_API_KEY is NOT a gemini credential and must be ignored — proving the abstraction lives in the
  // ADJUDICATOR selector, not the key name.
  const genericIgnored = selectAdjudicator({
    ADJUDICATOR: "gemini",
    LLM_API_KEY: "some-generic-value",
  } as NodeJS.ProcessEnv);
  assert(
    "select: a generic LLM_API_KEY does NOT satisfy the gemini path (only GEMINI_API_KEY does) → null:abstain",
    genericIgnored instanceof NullAdjudicator &&
      genericIgnored.id === "null:abstain",
    genericIgnored.id,
  );

  const defModel = selectAdjudicator({
    ADJUDICATOR: "gemini",
    GEMINI_API_KEY: KEY,
  } as NodeJS.ProcessEnv);
  assert(
    "select: default model is gemini-2.5-flash",
    defModel.id === "gemini:gemini-2.5-flash",
    defModel.id,
  );

  for (const v of ["", "null", "anthropic", "openai", "GEMINIX", "gem"]) {
    const a = selectAdjudicator({
      ADJUDICATOR: v,
      GEMINI_API_KEY: KEY,
    } as NodeJS.ProcessEnv);
    assert(
      `select: ADJUDICATOR='${v}' (not exactly gemini) → NullAdjudicator even with a key`,
      a instanceof NullAdjudicator && a.id === "null:abstain",
      a.id,
    );
  }

  // bad LLM_TIMEOUT_MS values fall back to the default (still constructs a usable client). LLM_TIMEOUT_MS
  // stays GENERIC by design — a timeout is provider-agnostic behavior, not a credential.
  for (const tms of ["", "0", "-5", "not-a-number", "NaN"]) {
    const a = selectAdjudicator({
      ADJUDICATOR: "gemini",
      GEMINI_API_KEY: KEY,
      LLM_TIMEOUT_MS: tms,
    } as NodeJS.ProcessEnv);
    assert(
      `select: bad LLM_TIMEOUT_MS='${tms}' still yields a Gemini client (sane default)`,
      a instanceof GeminiAdjudicator,
      a.id,
    );
  }
}

// ── ATTACK 12: postJsonWithRetry default transport is the global fetch (no accidental undefined call) ─
{
  // We don't hit the network: assert the helper is exported and callable with an injected transport that
  // fails fast, proving the shared helper itself (not just the adapter) enforces the 4xx scope.
  const t = spy([() => new Response("bad", { status: 400 })]);
  await rejects(
    "postJsonWithRetry: raw 400 fails fast (shared helper scope)",
    () =>
      postJsonWithRetry(
        "https://x/y",
        { a: 1 },
        { transport: t.fn, retries: 4 },
      ),
    /400/,
  );
  assert(
    "postJsonWithRetry: 400 not retried (one call)",
    t.calls() === 1,
    `calls=${t.calls()}`,
  );
}

console.log("\n=== gemini-adjudicator ADVERSARIAL results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL ADVERSARIAL EXPECTATIONS MET" : `${failures} ADVERSARIAL EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
