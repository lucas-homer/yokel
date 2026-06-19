/**
 * gemini-adjudicator.test.ts — Slice 3a: the Google Gemini Adjudicator + config-driven select factory,
 * proven in ISOLATION against an INJECTABLE transport (a spy `fetch`-like fn). NO network, NO API key.
 *
 * Pins the load-bearing behavior:
 *   • REQUEST BUILDING — for a notice AND a chain input: POST to .../models/<model>:generateContent, the
 *     key in the x-goog-api-key HEADER (never the URL), responseMimeType=application/json, a responseSchema
 *     constraining classification to the 3 enum values, and a prompt that contains the input's salient text.
 *   • HAPPY PATH PARSE — a well-formed candidates→content→parts→text JSON yields the right verdict; a stray
 *     `confidence` is stripped by AdjudicationVerdict.parse.
 *   • MALFORMED → THROW — missing candidates, empty parts (safety block), non-JSON text, and an invalid
 *     classification each throw (so consult persists nothing).
 *   • RETRY SCOPE — 500-then-200 retries and succeeds (two calls); a 400/401 throws immediately (one call).
 *   • TIMEOUT — a transport that never resolves but respects the abort signal → adjudicate rejects.
 *   • selectAdjudicator — ADJUDICATOR=gemini + key → GeminiAdjudicator (id gemini:<model>); empty env →
 *     NullAdjudicator; ADJUDICATOR=gemini with NO key → NullAdjudicator (no keyless client constructed).
 *
 * Repo test style: hand-rolled assert, out[] accumulator, failures counter, process.exit. Needs no DB.
 */
import type { AdjudicationInput } from "@yokel/contracts";
import { GeminiAdjudicator } from "../src/adjudicator/gemini-adjudicator.js";
import { selectAdjudicator } from "../src/adjudicator/select.js";
import type { FetchLike } from "../src/sources/http.js";

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

const chainInput: AdjudicationInput = {
  kind: "chain",
  rulebook_version: "rulebox-2026-06-18",
  a_title: "Original Rule on Widget Safety",
  a_dates_text: "Comments due by 2025-03-01",
  a_publication_date: "2025-01-15",
  b_title: "Extension of Comment Period for Widget Safety",
  b_dates_text: "Comments now due 2025-04-01",
  b_publication_date: "2025-02-20",
  shared_docket: true,
  shared_rin: false,
  explicit_reference: true,
};

/** A Response carrying a well-formed Gemini structured-output body (the verdict JSON in parts[0].text). */
function geminiOk(verdictJson: unknown): Response {
  const body = {
    candidates: [
      {
        content: { parts: [{ text: JSON.stringify(verdictJson) }] },
        finishReason: "STOP",
      },
    ],
  };
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}

/** Capture every request the transport sees, and return programmed responses in order. */
interface Captured {
  url: string;
  init: RequestInit;
  headers: Record<string, string>;
  body: any;
}
function spyTransport(steps: Array<() => Response>): {
  fn: FetchLike;
  calls: () => number;
  last: () => Captured;
  all: Captured[];
} {
  const all: Captured[] = [];
  let i = 0;
  const fn: FetchLike = async (url, init) => {
    const headers: Record<string, string> = {};
    const h = init.headers as Record<string, string> | undefined;
    if (h) for (const k of Object.keys(h)) headers[k.toLowerCase()] = h[k]!;
    all.push({
      url,
      init,
      headers,
      body: init.body ? JSON.parse(init.body as string) : undefined,
    });
    const step = steps[Math.min(i, steps.length - 1)];
    i++;
    return step!();
  };
  return { fn, calls: () => all.length, last: () => all[all.length - 1]!, all };
}

// ── REQUEST BUILDING: notice ───────────────────────────────────────────────────────────────────────
{
  const t = spyTransport([
    () => geminiOk({ classification: "reject", rationale: "keyword fp" }),
  ]);
  const adj = new GeminiAdjudicator({
    apiKey: KEY,
    model: MODEL,
    transport: t.fn,
  });
  await adj.adjudicate(noticeInput);
  const cap = t.last();
  assert(
    "notice: POST to the generateContent endpoint for the model",
    cap.url ===
      `https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent`,
    cap.url,
  );
  assert("notice: method is POST", cap.init.method === "POST");
  assert(
    "notice: key is in the x-goog-api-key HEADER",
    cap.headers["x-goog-api-key"] === KEY,
    cap.headers["x-goog-api-key"],
  );
  assert("notice: key is NOT in the URL", !cap.url.includes(KEY), cap.url);
  assert(
    "notice: responseMimeType is application/json",
    cap.body.generationConfig?.responseMimeType === "application/json",
    JSON.stringify(cap.body.generationConfig?.responseMimeType),
  );
  assert(
    "notice: temperature is 0 (deterministic)",
    cap.body.generationConfig?.temperature === 0,
  );
  const enumVals =
    cap.body.generationConfig?.responseSchema?.properties?.classification?.enum;
  assert(
    "notice: responseSchema constrains classification to the 3 enum values",
    Array.isArray(enumVals) &&
      enumVals.length === 3 &&
      ["affirm", "reject", "uncertain"].every((v) => enumVals.includes(v)),
    JSON.stringify(enumVals),
  );
  const promptText = cap.body.contents?.[0]?.parts?.[0]?.text ?? "";
  assert(
    "notice: prompt contains the title text under question",
    promptText.includes("Withdrawal of Land from Mineral Entry"),
    promptText.slice(0, 80),
  );
  assert(
    "notice: prompt contains the flag_key",
    promptText.includes("withdrawal"),
  );
  assert(
    "notice: a system instruction is present",
    typeof cap.body.systemInstruction?.parts?.[0]?.text === "string" &&
      cap.body.systemInstruction.parts[0].text.length > 0,
  );
}

// ── REQUEST BUILDING: chain ─────────────────────────────────────────────────────────────────────────
{
  const t = spyTransport([
    () => geminiOk({ classification: "affirm", rationale: "B amends A" }),
  ]);
  const adj = new GeminiAdjudicator({
    apiKey: KEY,
    model: MODEL,
    transport: t.fn,
  });
  await adj.adjudicate(chainInput);
  const promptText = t.last().body.contents?.[0]?.parts?.[0]?.text ?? "";
  assert(
    "chain: prompt contains A's title",
    promptText.includes("Original Rule on Widget Safety"),
  );
  assert(
    "chain: prompt contains B's title",
    promptText.includes("Extension of Comment Period for Widget Safety"),
  );
  assert(
    "chain: prompt surfaces the corroboration signals (shared docket/rin, explicit ref)",
    /shared docket/i.test(promptText) &&
      /shared RIN/i.test(promptText) &&
      /references A/i.test(promptText),
  );
}

// ── HAPPY PATH PARSE + stray confidence stripped ─────────────────────────────────────────────────────
{
  const t = spyTransport([
    () => geminiOk({ classification: "affirm", rationale: "genuine action" }),
  ]);
  const adj = new GeminiAdjudicator({
    apiKey: KEY,
    model: MODEL,
    transport: t.fn,
  });
  const v = await adj.adjudicate(noticeInput);
  assert(
    "happy path: verdict is the parsed classification + rationale",
    v.classification === "affirm" && v.rationale === "genuine action",
    JSON.stringify(v),
  );

  const t2 = spyTransport([
    () =>
      geminiOk({
        classification: "reject",
        rationale: "fp",
        confidence: 0.92,
      }),
  ]);
  const adj2 = new GeminiAdjudicator({
    apiKey: KEY,
    model: MODEL,
    transport: t2.fn,
  });
  const v2 = (await adj2.adjudicate(noticeInput)) as Record<string, unknown>;
  assert(
    "stray confidence is STRIPPED by AdjudicationVerdict.parse",
    v2.classification === "reject" && !("confidence" in v2),
    JSON.stringify(v2),
  );
}

// ── MALFORMED RESPONSES → THROW (consult persists nothing) ───────────────────────────────────────────
{
  const noCandidates = spyTransport([
    () =>
      new Response(
        JSON.stringify({ promptFeedback: { blockReason: "SAFETY" } }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
  ]);
  await rejects(
    "missing candidates throws (blockReason surfaced)",
    () =>
      new GeminiAdjudicator({
        apiKey: KEY,
        model: MODEL,
        transport: noCandidates.fn,
      }).adjudicate(noticeInput),
    /no candidate|blockReason=SAFETY/,
  );

  const emptyParts = spyTransport([
    () =>
      new Response(
        JSON.stringify({
          candidates: [{ content: { parts: [] }, finishReason: "SAFETY" }],
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
  ]);
  await rejects(
    "empty parts (safety block) throws",
    () =>
      new GeminiAdjudicator({
        apiKey: KEY,
        model: MODEL,
        transport: emptyParts.fn,
      }).adjudicate(noticeInput),
    /empty\/blocked candidate/,
  );

  const nonJson = spyTransport([
    () =>
      new Response(
        JSON.stringify({
          candidates: [{ content: { parts: [{ text: "not json at all {" }] } }],
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
  ]);
  await rejects(
    "non-JSON candidate text throws",
    () =>
      new GeminiAdjudicator({
        apiKey: KEY,
        model: MODEL,
        transport: nonJson.fn,
      }).adjudicate(noticeInput),
    /not valid JSON/,
  );

  const badClass = spyTransport([
    () => geminiOk({ classification: "maybe", rationale: "huh" }),
  ]);
  await rejects(
    "an invalid classification value throws (AdjudicationVerdict.parse)",
    () =>
      new GeminiAdjudicator({
        apiKey: KEY,
        model: MODEL,
        transport: badClass.fn,
      }).adjudicate(noticeInput),
    /./,
  );
}

// ── RETRY SCOPE (mirrors fetch-retry.test.ts) ────────────────────────────────────────────────────────
{
  const t = spyTransport([
    () => new Response("boom", { status: 500 }),
    () => geminiOk({ classification: "affirm", rationale: "ok" }),
  ]);
  const adj = new GeminiAdjudicator({
    apiKey: KEY,
    model: MODEL,
    transport: t.fn,
    retries: 4,
  });
  const v = await adj.adjudicate(noticeInput);
  assert(
    "500-then-200 retries and succeeds",
    v.classification === "affirm" && t.calls() === 2,
    `calls=${t.calls()}`,
  );

  const t400 = spyTransport([() => new Response("bad", { status: 400 })]);
  await rejects(
    "400 throws immediately (bad request)",
    () =>
      new GeminiAdjudicator({
        apiKey: KEY,
        model: MODEL,
        transport: t400.fn,
        retries: 4,
      }).adjudicate(noticeInput),
    /400/,
  );
  assert(
    "400 is NOT retried (exactly one call)",
    t400.calls() === 1,
    `calls=${t400.calls()}`,
  );

  const t401 = spyTransport([() => new Response("unauth", { status: 401 })]);
  await rejects(
    "401 (bad/absent key) throws immediately",
    () =>
      new GeminiAdjudicator({
        apiKey: KEY,
        model: MODEL,
        transport: t401.fn,
        retries: 4,
      }).adjudicate(noticeInput),
    /401/,
  );
  assert(
    "401 is NOT retried (exactly one call)",
    t401.calls() === 1,
    `calls=${t401.calls()}`,
  );
}

// ── TIMEOUT: a transport that never resolves but respects abort → reject ─────────────────────────────
{
  const hangingTransport: FetchLike = (_url, init) =>
    new Promise((_resolve, reject) => {
      const signal = init.signal;
      if (signal) {
        signal.addEventListener("abort", () =>
          reject(new DOMException("aborted", "AbortError")),
        );
      }
    });
  const adj = new GeminiAdjudicator({
    apiKey: KEY,
    model: MODEL,
    transport: hangingTransport,
    timeoutMs: 50,
    retries: 0,
  });
  const start = Date.now();
  await rejects(
    "a hanging transport aborts via the timeout and rejects",
    () => adj.adjudicate(noticeInput),
    /abort/i,
  );
  assert(
    "the timeout fired promptly (well under 5s)",
    Date.now() - start < 5_000,
    `${Date.now() - start}ms`,
  );
}

// ── selectAdjudicator ────────────────────────────────────────────────────────────────────────────────
{
  const gem = selectAdjudicator({
    ADJUDICATOR: "gemini",
    GEMINI_API_KEY: KEY,
  } as NodeJS.ProcessEnv);
  assert(
    "select: ADJUDICATOR=gemini + GEMINI_API_KEY → GeminiAdjudicator id gemini:<model>",
    gem instanceof GeminiAdjudicator && gem.id === `gemini:${MODEL}`,
    gem.id,
  );

  const gemModel = selectAdjudicator({
    ADJUDICATOR: "gemini",
    GEMINI_API_KEY: KEY,
    GEMINI_MODEL: "gemini-2.5-pro",
  } as NodeJS.ProcessEnv);
  assert(
    "select: GEMINI_MODEL override is reflected in the id",
    gemModel instanceof GeminiAdjudicator &&
      gemModel.id === "gemini:gemini-2.5-pro",
    gemModel.id,
  );

  const empty = selectAdjudicator({} as NodeJS.ProcessEnv);
  assert(
    "select: empty env → NullAdjudicator (id null:abstain) — the safe default",
    empty.id === "null:abstain",
    empty.id,
  );

  const noKey = selectAdjudicator({
    ADJUDICATOR: "gemini",
  } as NodeJS.ProcessEnv);
  assert(
    "select: ADJUDICATOR=gemini but NO key → NullAdjudicator (no keyless client)",
    noKey.id === "null:abstain",
    noKey.id,
  );

  const nullProvider = selectAdjudicator({
    ADJUDICATOR: "null",
    GEMINI_API_KEY: KEY,
  } as NodeJS.ProcessEnv);
  assert(
    "select: ADJUDICATOR=null → NullAdjudicator even with a key present",
    nullProvider.id === "null:abstain",
    nullProvider.id,
  );
}

// ── whitespace robustness (PR #42 review Ⓐ/Ⓑ: trailing-newline secrets must not bypass safe default) ──
{
  const wsKey = selectAdjudicator({
    ADJUDICATOR: "gemini",
    GEMINI_API_KEY: "  \n ",
  } as NodeJS.ProcessEnv);
  assert(
    "select: whitespace-only key → NullAdjudicator (trimmed → treated as absent)",
    wsKey.id === "null:abstain",
    wsKey.id,
  );

  await rejects(
    "ctor: whitespace-only apiKey throws (not a usable key)",
    async () => new GeminiAdjudicator({ apiKey: " \n ", model: MODEL }),
    /non-empty apiKey/,
  );
  await rejects(
    "ctor: empty/whitespace model throws (no bogus gemini: id / invalid endpoint)",
    async () => new GeminiAdjudicator({ apiKey: KEY, model: "  " }),
    /non-empty model/,
  );
}

console.log("\n=== gemini-adjudicator results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
