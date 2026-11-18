/**
 * chat-completions-adjudicator.test.ts — the OpenAI-compatible adapter used for Cloudflare AI Gateway,
 * against an injectable transport. NO network, NO token.
 *
 * Pins: request shape (Bearer auth in the header, gateway header, model, temperature 0, strict json_schema,
 * shared prompt text); happy-path parse incl. fenced JSON and array content; malformed → throw; the knob
 * ladder (400 naming temperature / response_format drops ONLY that knob; 401/402 never ladder); and the
 * selectAdjudicator ai-gateway branch (needs account id AND token, else null; LLM_MODEL → id).
 */
import type { AdjudicationInput } from "@yokel/contracts";
import { ChatCompletionsAdjudicator } from "../src/adjudicator/chat-completions-adjudicator.js";
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

const json = (status: number, body: unknown) =>
  new Response(typeof body === "string" ? body : JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
const ok = (content: unknown) =>
  json(200, {
    choices: [{ message: { content }, finish_reason: "stop" }],
    usage: { prompt_tokens: 120, completion_tokens: 30, total_tokens: 150 },
  });

interface Call {
  url: string;
  headers: Record<string, string>;
  body: Record<string, unknown>;
}
function spy(responses: Array<() => Response>): {
  transport: FetchLike;
  calls: Call[];
} {
  const calls: Call[] = [];
  let i = 0;
  const transport: FetchLike = async (url, init) => {
    calls.push({
      url,
      headers: Object.fromEntries(new Headers(init.headers).entries()),
      body: JSON.parse(String(init.body)),
    });
    const r = responses[Math.min(i++, responses.length - 1)]!;
    return r();
  };
  return { transport, calls };
}

const make = (transport: FetchLike) =>
  new ChatCompletionsAdjudicator({
    baseUrl: "https://api.example.test/ai/v1/",
    apiKey: "tok-not-real",
    model: "google/gemini-3-flash",
    idPrefix: "aigw",
    headers: { "cf-aig-gateway-id": "docketclock" },
    retries: 0,
    timeoutMs: 2000,
    transport,
  });

// ── request shape + happy path ─────────────────────────────────────────────────────────────────────
{
  const { transport, calls } = spy([
    () =>
      ok(
        JSON.stringify({
          classification: "affirm",
          rationale: "extends A",
          confidence: 0.9,
        }),
      ),
  ]);
  const a = make(transport);
  const v = await a.adjudicate(chainInput);
  const c = calls[0]!;
  assert("id is prefix:model", a.id === "aigw:google/gemini-3-flash", a.id);
  assert(
    "POSTs to {base}/chat/completions (trailing slash trimmed)",
    c.url === "https://api.example.test/ai/v1/chat/completions",
    c.url,
  );
  assert(
    "Bearer token in Authorization header",
    c.headers["authorization"] === "Bearer tok-not-real",
  );
  assert("token NOT in the URL", !c.url.includes("tok-not-real"));
  assert(
    "gateway header sent",
    c.headers["cf-aig-gateway-id"] === "docketclock",
  );
  assert("model in body", c.body.model === "google/gemini-3-flash");
  assert("temperature 0", c.body.temperature === 0);
  const rf = c.body.response_format as
    | { type?: string; json_schema?: { strict?: boolean } }
    | undefined;
  assert(
    "strict json_schema response_format",
    rf?.type === "json_schema" && rf.json_schema?.strict === true,
  );
  const msgs = c.body.messages as Array<{ role: string; content: string }>;
  assert(
    "system + user messages",
    msgs[0]?.role === "system" && msgs[1]?.role === "user",
  );
  assert(
    "prompt carries both titles",
    msgs[1]!.content.includes("Original Rule on Widget Safety") &&
      msgs[1]!.content.includes("Extension of Comment Period"),
  );
  assert(
    "verdict parsed",
    v.classification === "affirm" && v.rationale === "extends A",
  );
  assert("stray confidence stripped", !("confidence" in v));
}

{
  const { transport } = spy([
    () =>
      ok('```json\n{"classification":"reject","rationale":"unrelated"}\n```'),
  ]);
  const v = await make(transport).adjudicate(chainInput);
  assert("fenced JSON tolerated", v.classification === "reject");
}
{
  const { transport } = spy([
    () =>
      ok([
        { type: "text", text: '{"classification":"uncertain",' },
        { type: "text", text: '"rationale":"?"}' },
      ]),
  ]);
  const v = await make(transport).adjudicate(chainInput);
  assert("array content parts joined", v.classification === "uncertain");
}

// ── malformed → throw ──────────────────────────────────────────────────────────────────────────────
await rejects(
  "no choices → throw",
  () =>
    make(spy([() => json(200, { choices: [] })]).transport).adjudicate(
      chainInput,
    ),
  /no choice/,
);
await rejects(
  "empty content → throw",
  () => make(spy([() => ok(null)]).transport).adjudicate(chainInput),
  /empty choice/,
);
await rejects(
  "non-JSON → throw",
  () =>
    make(spy([() => ok("I think it amends.")]).transport).adjudicate(
      chainInput,
    ),
  /not valid JSON/,
);
await rejects(
  "invalid classification → throw",
  () =>
    make(
      spy([() => ok('{"classification":"maybe","rationale":"x"}')]).transport,
    ).adjudicate(chainInput),
  /classification|invalid/i,
);

// ── knob ladder ────────────────────────────────────────────────────────────────────────────────────
{
  const { transport, calls } = spy([
    () =>
      json(400, {
        error: {
          message: "Unsupported value: 'temperature' does not support 0",
        },
      }),
    () => ok('{"classification":"affirm","rationale":"r"}'),
  ]);
  const v = await make(transport).adjudicate(chainInput);
  assert(
    "400 naming temperature → retried without it",
    calls.length === 2 &&
      !("temperature" in calls[1]!.body) &&
      v.classification === "affirm",
  );
  assert(
    "…and kept the schema",
    (calls[1]!.body.response_format as { type: string }).type === "json_schema",
  );
}
{
  const { transport, calls } = spy([
    () =>
      json(400, {
        error: {
          message:
            "response_format json_schema is not supported for this model",
        },
      }),
    () =>
      json(400, {
        error: { message: "response_format json_object is not supported" },
      }),
    () => ok('{"classification":"reject","rationale":"r"}'),
  ]);
  const v = await make(transport).adjudicate(chainInput);
  const types = calls.map(
    (c) =>
      (c.body.response_format as { type?: string } | undefined)?.type ?? "none",
  );
  assert(
    "schema → json_object → none",
    types.join(",") === "json_schema,json_object,none",
    types.join(","),
  );
  assert("…then parses", v.classification === "reject");
}
{
  const { transport, calls } = spy([() => json(401, { error: "bad token" })]);
  await rejects(
    "401 throws",
    () => make(transport).adjudicate(chainInput),
    /401/,
  );
  assert("401 never ladders", calls.length === 1);
}
{
  const { transport, calls } = spy([
    () => json(402, { error: "insufficient credits; temperature" }),
  ]);
  await rejects(
    "402 throws",
    () => make(transport).adjudicate(chainInput),
    /402/,
  );
  assert("402 never ladders even if body names a knob", calls.length === 1);
}
{
  const { transport, calls } = spy([
    () => json(400, { error: "temperature unsupported" }),
  ]);
  await rejects(
    "ladder is bounded",
    () => make(transport).adjudicate(chainInput),
    /400/,
  );
  assert(
    "bounded: one temperature drop then stop",
    calls.length === 2,
    String(calls.length),
  );
}

// ── selectAdjudicator ai-gateway branch ────────────────────────────────────────────────────────────
{
  const base = {
    ADJUDICATOR: "ai-gateway",
    CLOUDFLARE_ACCOUNT_ID: "acct123",
    CLOUDFLARE_AI_TOKEN: "tok\n",
  };
  assert(
    "ai-gateway + id + token → aigw default model",
    selectAdjudicator(base).id === "aigw:google/gemini-2.5-flash",
    selectAdjudicator(base).id,
  );
  assert(
    "LLM_MODEL picks the model",
    selectAdjudicator({ ...base, LLM_MODEL: "openai/gpt-5.4-mini" }).id ===
      "aigw:openai/gpt-5.4-mini",
  );
  assert(
    "no token → null",
    selectAdjudicator({ ...base, CLOUDFLARE_AI_TOKEN: "  " }).id.startsWith(
      "null:",
    ),
  );
  assert(
    "no account → null",
    selectAdjudicator({ ...base, CLOUDFLARE_ACCOUNT_ID: "" }).id.startsWith(
      "null:",
    ),
  );
  assert(
    "CASE-insensitive selector",
    selectAdjudicator({ ...base, ADJUDICATOR: "AI-Gateway" }).id.startsWith(
      "aigw:",
    ),
  );
}

console.log("chat-completions-adjudicator.test.ts");
console.log(out.join("\n"));
console.log(failures === 0 ? "ALL PASS" : `${failures} FAILURE(S)`);
process.exit(failures === 0 ? 0 : 1);
