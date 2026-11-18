/**
 * adjudicator-spans.test.ts — the trace an adjudication leaves (ADR 0018, slice 4). NO network, NO token.
 *
 * Captures spans with an in-memory Tracer and runs the adapter the way the poller does: Promise code
 * (`adjudicate()`) called from inside an Effect span via `withAmbient` (ambient.ts). Pins:
 *   - the GenAI span `chat <model>` (kind client) nests under the caller's span, in the caller's trace;
 *   - it carries provider, model, token usage, finish reason, verdict and the knobs the ladder dropped;
 *   - each HTTP send is a child `POST` span with its status code, and no secret reaches any attribute;
 *   - a retried GET is one span per attempt with http.request.resend_count, and its query string
 *     (Regulations.gov's api_key) never reaches url.full;
 *   - outside any ambient context the Promise port still works (no spans required).
 */
import type { AdjudicationInput } from "@yokel/contracts";
import { Effect, Tracer } from "effect";
import { withAmbient } from "../src/ambient.js";
import { ChatCompletionsAdjudicator } from "../src/adjudicator/chat-completions-adjudicator.js";
import { fetchJsonWithRetry, type FetchLike } from "../src/sources/http.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

const spans: Tracer.NativeSpan[] = [];
const tracer = Tracer.make({
  span(options) {
    const span = new Tracer.NativeSpan(options);
    spans.push(span);
    return span;
  },
});
/** Run Promise code inside an Effect span named `outer`, with the capturing tracer, the poller's way. */
const underSpan = <A>(outer: string, run: () => Promise<A>) =>
  Effect.runPromise(
    withAmbient(run).pipe(
      Effect.withSpan(outer),
      Effect.provideService(Tracer.Tracer, tracer),
    ),
  );
const byName = (name: string) => spans.filter((s) => s.name === name);
const parentName = (s: Tracer.NativeSpan) =>
  s.parent._tag === "Some" && "name" in s.parent.value
    ? (s.parent.value as Tracer.NativeSpan).name
    : undefined;

const input: AdjudicationInput = {
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
const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });

const SECRET = "sk-test-SECRET-token";

try {
  // ── a laddered adjudication inside a traced pass ─────────────────────────────────────────────────
  {
    let n = 0;
    const transport: FetchLike = async () => {
      n++;
      if (n === 1)
        return json(400, {
          error: {
            message: "Unsupported value: 'temperature' does not support 0",
          },
        });
      return json(200, {
        choices: [
          {
            message: {
              content: JSON.stringify({
                classification: "affirm",
                rationale: "Explicit extension of the same docket.",
              }),
            },
            finish_reason: "stop",
          },
        ],
        usage: { prompt_tokens: 120, completion_tokens: 30, total_tokens: 150 },
      });
    };
    const adj = new ChatCompletionsAdjudicator({
      baseUrl: "https://api.example.test/ai/v1",
      apiKey: SECRET,
      model: "google/gemini-3-flash",
      retries: 0,
      transport,
    });
    const verdict = await underSpan("poll.pass.chain", () =>
      adj.adjudicate(input),
    );
    assert("verdict returned", verdict.classification === "affirm");

    const pass = byName("poll.pass.chain")[0];
    const chat = byName("chat google/gemini-3-flash")[0];
    assert("one chat span", byName("chat google/gemini-3-flash").length === 1);
    assert(
      "chat span nests under the pass span, same trace",
      !!chat &&
        !!pass &&
        parentName(chat) === "poll.pass.chain" &&
        chat.traceId === pass.traceId,
      chat ? `parent=${parentName(chat)}` : "no chat span",
    );
    assert("chat span is a client span", chat?.kind === "client");
    const a = chat?.attributes;
    assert(
      "GenAI request attributes",
      a?.get("gen_ai.operation.name") === "chat" &&
        a?.get("gen_ai.provider.name") === "google" &&
        a?.get("gen_ai.request.model") === "google/gemini-3-flash",
    );
    assert(
      "token usage and finish reason",
      a?.get("gen_ai.usage.input_tokens") === 120 &&
        a?.get("gen_ai.usage.output_tokens") === 30 &&
        JSON.stringify(a?.get("gen_ai.response.finish_reasons")) === '["stop"]',
    );
    assert(
      "verdict and dropped knob recorded",
      a?.get("docketclock.verdict.classification") === "affirm" &&
        a?.get("docketclock.ladder.dropped") === "temperature",
      String(a?.get("docketclock.ladder.dropped")),
    );
    const posts = byName("POST");
    assert(
      "two POST spans under the chat span (the ladder re-send)",
      posts.length === 2 &&
        posts.every((p) => parentName(p) === "chat google/gemini-3-flash"),
      `posts=${posts.length}`,
    );
    assert(
      "POST spans carry their status codes",
      posts
        .map((p) => p.attributes.get("http.response.status_code"))
        .join(",") === "400,200",
    );
    const everything = JSON.stringify(
      spans.map((s) => Object.fromEntries(s.attributes)),
    );
    assert("no secret in any span attribute", !everything.includes(SECRET));
    assert(
      "all spans ended",
      spans.every((s) => s.status._tag === "Ended"),
    );
  }

  // ── a retried GET: one span per attempt, no query string ─────────────────────────────────────────
  {
    spans.length = 0;
    const realFetch = globalThis.fetch;
    let n = 0;
    globalThis.fetch = (async () => {
      n++;
      return n === 1
        ? new Response("busy", { status: 503, headers: { "retry-after": "0" } })
        : json(200, { ok: true });
    }) as typeof fetch;
    try {
      const body = await underSpan("poll.pass.regs", () =>
        fetchJsonWithRetry(
          "https://api.regulations.gov/v4/documents?api_key=REGS-KEY&page=1",
          { retries: 2 },
        ),
      );
      assert("GET retried to success", (body as { ok: boolean }).ok === true);
    } finally {
      globalThis.fetch = realFetch;
    }
    const gets = byName("GET");
    assert("one GET span per attempt", gets.length === 2, `got ${gets.length}`);
    assert(
      "resend_count marks the retry only",
      gets[0]?.attributes.get("http.request.resend_count") === undefined &&
        gets[1]?.attributes.get("http.request.resend_count") === 1,
    );
    assert(
      "url.full has no query string",
      gets.every(
        (g) =>
          g.attributes.get("url.full") ===
          "https://api.regulations.gov/v4/documents",
      ),
      String(gets[0]?.attributes.get("url.full")),
    );
    assert(
      "GET spans nest under the pass",
      gets.every((g) => parentName(g) === "poll.pass.regs"),
    );
    assert(
      "no API key in any span attribute",
      !JSON.stringify(
        spans.map((s) => Object.fromEntries(s.attributes)),
      ).includes("REGS-KEY"),
    );
  }

  // ── outside an ambient context the Promise port still works ─────────────────────────────────────
  {
    const adj = new ChatCompletionsAdjudicator({
      baseUrl: "https://api.example.test/ai/v1",
      apiKey: SECRET,
      model: "openai/gpt-5.4-mini",
      retries: 0,
      transport: async () =>
        json(200, {
          choices: [
            {
              message: {
                content:
                  '{"classification":"reject","rationale":"Different docket."}',
              },
            },
          ],
        }),
    });
    const v = await adj.adjudicate(input);
    assert("plain Promise call works", v.classification === "reject");
  }
} catch (err) {
  failures++;
  out.push(`  FAIL  unexpected error — ${String(err)}`);
}

console.log(`adjudicator-spans.test.ts\n${out.join("\n")}`);
console.log(failures === 0 ? "ALL PASS" : `${failures} FAILURE(S)`);
process.exit(failures === 0 ? 0 : 1);
