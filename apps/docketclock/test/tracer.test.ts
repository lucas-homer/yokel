/**
 * tracer.test.ts — PR-C2 (observability slice C): the LLM-tracing SIDE CHANNEL, proven in ISOLATION with NO
 * network and NO live Langfuse server. Pins the load-bearing behavior:
 *
 *   • NoopTracer is truly INERT — every method is a no-op, flush()/shutdown() resolve, nothing throws. This
 *     is the default with no LANGFUSE_* env, so the adjudication path is byte-for-byte unchanged.
 *   • selectTracer is ALL-OR-NOTHING — a NoopTracer unless LANGFUSE_HOST + PUBLIC_KEY + SECRET_KEY are ALL
 *     present (whitespace-only counts as absent); only then a LangfuseTracer.
 *   • GeminiAdjudicator parses `usageMetadata` (prompt/candidates/total → input/output/total) and feeds the
 *     INJECTED tracer a generation with model, verdict, latency, content_hash, adjudicator_id, kind.
 *   • The API key NEVER appears in what is handed to the tracer (deep-stringify check).
 *   • LangfuseTracer maps a generation → trace.generation(...).end({ usage: {..., unit:"TOKENS"} }) and a
 *     cache hit → trace.span({ cached:true }), attaches OCD-ids from setActivePair, flush()→flushAsync(),
 *     and NEVER puts the secret key in a trace body — all against an INJECTED fake client (no network).
 *
 * Repo test style: hand-rolled assert, out[] accumulator, failures counter, process.exit. Needs no DB.
 */
import type { AdjudicationInput } from "@yokel/contracts";
import { GeminiAdjudicator } from "../src/adjudicator/gemini-adjudicator.js";
import { selectAdjudicator, selectTracer } from "../src/adjudicator/select.js";
import {
  NoopTracer,
  NOOP_TRACER,
  safeTracer,
} from "../src/adjudicator/tracer.js";
import type {
  LlmCacheHitRecord,
  LlmGenerationRecord,
  LlmTracer,
} from "../src/adjudicator/tracer.js";
import {
  LangfuseTracer,
  type LangfuseClientLike,
  type LangfuseTraceLike,
} from "../src/adjudicator/langfuse-tracer.js";
import type { FetchLike } from "../src/sources/http.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

const MODEL = "gemini-2.5-flash";
const KEY = "AIzaSy-super-secret-not-real-key";
const RULEBOOK = "rulebox-2026-06-18";

const noticeInput: AdjudicationInput = {
  kind: "notice",
  rulebook_version: RULEBOOK,
  flag_key: "withdrawal",
  text: "Withdrawal of Land from Mineral Entry; Notice of Realty Action",
};

/** A capturing fake tracer — records every call so the test can assert what the adapter handed it. */
function captureTracer(): LlmTracer & {
  generations: LlmGenerationRecord[];
  hits: LlmCacheHitRecord[];
  cycles: number;
  flushes: number;
} {
  const t = {
    generations: [] as LlmGenerationRecord[],
    hits: [] as LlmCacheHitRecord[],
    cycles: 0,
    flushes: 0,
    startCycle() {
      t.cycles++;
    },
    setActivePair() {},
    recordGeneration(gen: LlmGenerationRecord) {
      t.generations.push(gen);
    },
    recordCacheHit(hit: LlmCacheHitRecord) {
      t.hits.push(hit);
    },
    async flush() {
      t.flushes++;
    },
    async shutdown() {},
  };
  return t;
}

/** A Gemini OK response carrying a verdict JSON in parts[0].text and an optional usageMetadata block. */
function geminiOk(verdictJson: unknown, usageMetadata?: unknown): Response {
  const body: Record<string, unknown> = {
    candidates: [
      {
        content: { parts: [{ text: JSON.stringify(verdictJson) }] },
        finishReason: "STOP",
      },
    ],
  };
  if (usageMetadata) body.usageMetadata = usageMetadata;
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}

function onceTransport(res: Response): FetchLike {
  return async () => res;
}

// ── NoopTracer is INERT ─────────────────────────────────────────────────────────────────────────────
{
  const noop = new NoopTracer();
  let threw = false;
  try {
    noop.startCycle({ kind: "chain", surfaced: 3, cap: 25 });
    noop.setActivePair({ fromOcdId: "a", toOcdId: "b" });
    noop.setActivePair(null);
    noop.recordGeneration({
      model: MODEL,
      input: noticeInput,
      output: { classification: "affirm", rationale: "x" },
      verdict: { classification: "affirm", rationale: "x" },
      latencyMs: 5,
      contentHash: "0".repeat(64),
      adjudicatorId: `gemini:${MODEL}@${RULEBOOK}`,
      rulebookVersion: RULEBOOK,
      kind: "notice",
    });
    noop.recordCacheHit({
      contentHash: "0".repeat(64),
      adjudicatorId: `gemini:${MODEL}@${RULEBOOK}`,
      rulebookVersion: RULEBOOK,
      kind: "chain",
      classification: "reject",
    });
    await noop.flush();
    await noop.shutdown();
  } catch {
    threw = true;
  }
  assert("NoopTracer: every method is a no-op and nothing throws", !threw);
  assert("NoopTracer: flush() and shutdown() resolve (await completed)", true);
  assert(
    "NOOP_TRACER singleton is a NoopTracer instance",
    NOOP_TRACER instanceof NoopTracer,
  );
}

// ── selectTracer is ALL-OR-NOTHING ──────────────────────────────────────────────────────────────────
{
  assert(
    "selectTracer: empty env → NoopTracer (no langfuse client constructed)",
    selectTracer({} as NodeJS.ProcessEnv) instanceof NoopTracer,
  );
  assert(
    "selectTracer: only HOST set → NoopTracer",
    selectTracer({
      LANGFUSE_HOST: "http://langfuse.langfuse.svc:3000",
    } as NodeJS.ProcessEnv) instanceof NoopTracer,
  );
  assert(
    "selectTracer: HOST + PUBLIC but no SECRET → NoopTracer",
    selectTracer({
      LANGFUSE_HOST: "http://x:3000",
      LANGFUSE_PUBLIC_KEY: "pk-lf-dev",
    } as NodeJS.ProcessEnv) instanceof NoopTracer,
  );
  assert(
    "selectTracer: whitespace-only SECRET → NoopTracer (trimmed → absent)",
    selectTracer({
      LANGFUSE_HOST: "http://x:3000",
      LANGFUSE_PUBLIC_KEY: "pk-lf-dev",
      LANGFUSE_SECRET_KEY: "  \n ",
    } as NodeJS.ProcessEnv) instanceof NoopTracer,
  );
  const lf = selectTracer({
    LANGFUSE_HOST: "http://langfuse.langfuse.svc:3000",
    LANGFUSE_PUBLIC_KEY: "pk-lf-dev-docketclock",
    LANGFUSE_SECRET_KEY: "sk-lf-dev-docketclock",
  } as NodeJS.ProcessEnv);
  assert(
    "selectTracer: all three set → a configured (non-noop) tracer",
    lf !== NOOP_TRACER && !(lf instanceof NoopTracer),
  );

  // selectAdjudicator wires the SAME tracer onto the adapter it injects.
  const gemNoop = selectAdjudicator({
    ADJUDICATOR: "gemini",
    GEMINI_API_KEY: KEY,
  } as NodeJS.ProcessEnv) as GeminiAdjudicator;
  assert(
    "selectAdjudicator: gemini + no LANGFUSE → adapter.tracer is NoopTracer",
    gemNoop.tracer instanceof NoopTracer,
  );
  const gemLf = selectAdjudicator({
    ADJUDICATOR: "gemini",
    GEMINI_API_KEY: KEY,
    LANGFUSE_HOST: "http://langfuse.langfuse.svc:3000",
    LANGFUSE_PUBLIC_KEY: "pk-lf-dev-docketclock",
    LANGFUSE_SECRET_KEY: "sk-lf-dev-docketclock",
  } as NodeJS.ProcessEnv) as GeminiAdjudicator;
  assert(
    "selectAdjudicator: gemini + all LANGFUSE → adapter.tracer is a configured (non-noop) tracer",
    gemLf.tracer !== NOOP_TRACER && !(gemLf.tracer instanceof NoopTracer),
  );
}

// ── GeminiAdjudicator parses usageMetadata + feeds the injected tracer ───────────────────────────────
{
  const tracer = captureTracer();
  const adj = new GeminiAdjudicator({
    apiKey: KEY,
    model: MODEL,
    transport: onceTransport(
      geminiOk(
        { classification: "affirm", rationale: "genuine action" },
        {
          promptTokenCount: 120,
          candidatesTokenCount: 8,
          totalTokenCount: 128,
        },
      ),
    ),
    tracer,
  });
  const v = await adj.adjudicate(noticeInput);
  assert(
    "verdict is returned unchanged (side channel did not alter it)",
    v.classification === "affirm" && v.rationale === "genuine action",
  );
  assert(
    "tracer.recordGeneration was called exactly once on the real call",
    tracer.generations.length === 1,
    String(tracer.generations.length),
  );
  const g = tracer.generations[0]!;
  assert("generation carries the model id", g.model === MODEL, g.model);
  assert(
    "usageMetadata parsed: input=promptTokenCount, output=candidatesTokenCount, total=totalTokenCount",
    g.usage?.input === 120 && g.usage?.output === 8 && g.usage?.total === 128,
    JSON.stringify(g.usage),
  );
  assert(
    "generation carries the parsed verdict",
    g.verdict.classification === "affirm",
  );
  assert(
    "generation carries a 64-hex content_hash",
    /^[a-f0-9]{64}$/.test(g.contentHash),
    g.contentHash,
  );
  assert(
    "generation carries adjudicator_id provenance gemini:<model>@<rulebook>",
    g.adjudicatorId === `gemini:${MODEL}@${RULEBOOK}`,
    g.adjudicatorId,
  );
  assert(
    "generation carries kind + rulebookVersion",
    g.kind === "notice" && g.rulebookVersion === RULEBOOK,
  );
  assert(
    "generation latencyMs is a non-negative number",
    typeof g.latencyMs === "number" && g.latencyMs >= 0,
    String(g.latencyMs),
  );

  // KEY NON-LEAK: nothing the adapter handed the tracer may contain the API key.
  const blob = JSON.stringify(g);
  assert(
    "the Gemini API key NEVER appears in what is handed to the tracer",
    !blob.includes(KEY),
    blob.includes(KEY) ? "LEAKED" : "ok",
  );
}

// ── usageMetadata ABSENT → generation recorded without usage (no fabricated zeros) ───────────────────
{
  const tracer = captureTracer();
  const adj = new GeminiAdjudicator({
    apiKey: KEY,
    model: MODEL,
    transport: onceTransport(
      geminiOk({ classification: "reject", rationale: "fp" }),
    ),
    tracer,
  });
  await adj.adjudicate(noticeInput);
  assert(
    "no usageMetadata → generation.usage is undefined (no fabricated token counts)",
    tracer.generations.length === 1 &&
      tracer.generations[0]!.usage === undefined,
    JSON.stringify(tracer.generations[0]?.usage),
  );
}

// ── MALFORMED response → THROW and NO generation recorded (trace mirrors persisted set) ──────────────
{
  const tracer = captureTracer();
  const adj = new GeminiAdjudicator({
    apiKey: KEY,
    model: MODEL,
    transport: onceTransport(
      new Response(
        JSON.stringify({ promptFeedback: { blockReason: "SAFETY" } }),
        {
          status: 200,
          headers: { "content-type": "application/json" },
        },
      ),
    ),
    tracer,
  });
  let threw = false;
  try {
    await adj.adjudicate(noticeInput);
  } catch {
    threw = true;
  }
  assert(
    "a blocked/malformed response throws AND records NO generation",
    threw && tracer.generations.length === 0,
    `threw=${threw} gens=${tracer.generations.length}`,
  );
}

// ── LangfuseTracer maps to the SDK client correctly (injected fake, no network) ──────────────────────
{
  interface Ended {
    output: unknown;
    usage?: { input?: number; output?: number; total?: number; unit?: string };
  }
  const generations: Array<{ body: Record<string, unknown>; ended: Ended[] }> =
    [];
  const spans: Array<Record<string, unknown>> = [];
  const traces: Array<Record<string, unknown>> = [];
  let flushed = 0;
  let shutdowns = 0;

  const fakeTrace: LangfuseTraceLike = {
    generation(body) {
      const rec = { body, ended: [] as Ended[] };
      generations.push(rec);
      return {
        end(endBody) {
          rec.ended.push(endBody as unknown as Ended);
          return undefined;
        },
      };
    },
    span(body) {
      spans.push(body);
      return undefined;
    },
    event(body) {
      spans.push(body);
      return undefined;
    },
  };
  const fakeClient: LangfuseClientLike = {
    trace(body) {
      traces.push(body);
      return fakeTrace;
    },
    async flushAsync() {
      flushed++;
    },
    async shutdownAsync() {
      shutdowns++;
    },
  };

  const SECRET = "sk-lf-dev-docketclock-SECRET";
  const tracer = new LangfuseTracer({
    host: "http://langfuse.langfuse.svc:3000",
    publicKey: "pk-lf-dev-docketclock",
    secretKey: SECRET,
    client: fakeClient,
  });

  tracer.startCycle({ kind: "chain", surfaced: 2, cap: 25 });
  assert(
    "LangfuseTracer.startCycle opens exactly one trace",
    traces.length === 1,
    String(traces.length),
  );

  tracer.setActivePair({ fromOcdId: "ocd-a", toOcdId: "ocd-b" });
  tracer.recordGeneration({
    model: MODEL,
    input: { kind: "chain", rulebook_version: RULEBOOK },
    output: { classification: "affirm", rationale: "B amends A" },
    verdict: { classification: "affirm", rationale: "B amends A" },
    usage: { input: 100, output: 10, total: 110 },
    latencyMs: 42,
    contentHash: "a".repeat(64),
    adjudicatorId: `gemini:${MODEL}@${RULEBOOK}`,
    rulebookVersion: RULEBOOK,
    kind: "chain",
    // NB: adapter does NOT pass OCD-ids — they must come from setActivePair.
  });
  assert(
    "recordGeneration creates one generation on the cycle trace",
    generations.length === 1,
    String(generations.length),
  );
  const gend = generations[0]!;
  assert(
    "generation body has the model",
    gend.body.model === MODEL,
    String(gend.body.model),
  );
  const meta = gend.body.metadata as Record<string, unknown>;
  assert(
    "generation metadata carries content_hash / adjudicator_id / kind / cached=false",
    meta.content_hash === "a".repeat(64) &&
      meta.adjudicator_id === `gemini:${MODEL}@${RULEBOOK}` &&
      meta.kind === "chain" &&
      meta.cached === false,
    JSON.stringify(meta),
  );
  assert(
    "generation metadata picks up OCD-ids from setActivePair",
    meta.from_ocd_id === "ocd-a" && meta.to_ocd_id === "ocd-b",
    JSON.stringify({ from: meta.from_ocd_id, to: meta.to_ocd_id }),
  );
  assert(
    "generation .end() carries output + usage with unit TOKENS",
    gend.ended.length === 1 &&
      gend.ended[0]!.usage?.input === 100 &&
      gend.ended[0]!.usage?.output === 10 &&
      gend.ended[0]!.usage?.total === 110 &&
      gend.ended[0]!.usage?.unit === "TOKENS",
    JSON.stringify(gend.ended[0]),
  );

  tracer.recordCacheHit({
    contentHash: "b".repeat(64),
    adjudicatorId: `gemini:${MODEL}@${RULEBOOK}`,
    rulebookVersion: RULEBOOK,
    kind: "chain",
    classification: "reject",
    fromOcdId: "ocd-c",
    toOcdId: "ocd-d",
  });
  assert(
    "recordCacheHit creates a cached span",
    spans.length === 1 &&
      (spans[0]!.metadata as Record<string, unknown>).cached === true,
    JSON.stringify(spans[0]?.metadata),
  );

  await tracer.flush();
  assert(
    "flush() calls the client's flushAsync",
    flushed === 1,
    String(flushed),
  );
  await tracer.shutdown();
  assert(
    "shutdown() calls the client's shutdownAsync",
    shutdowns === 1,
    String(shutdowns),
  );

  // SECRET NON-LEAK: the secret key is held by the client but NEVER attached to any trace/observation body.
  const everything = JSON.stringify({ traces, generations, spans });
  assert(
    "LANGFUSE_SECRET_KEY never appears in any trace/generation/span body",
    !everything.includes(SECRET),
    everything.includes(SECRET) ? "LEAKED" : "ok",
  );
}

// ── LangfuseTracer: a generation recorded with NO open cycle still creates a standalone trace ────────
{
  const traces: Array<Record<string, unknown>> = [];
  const fakeTrace: LangfuseTraceLike = {
    generation() {
      return { end() {} };
    },
    span() {},
    event() {},
  };
  const fakeClient: LangfuseClientLike = {
    trace(body) {
      traces.push(body);
      return fakeTrace;
    },
    async flushAsync() {},
    async shutdownAsync() {},
  };
  const tracer = new LangfuseTracer({
    host: "http://x:3000",
    publicKey: "pk",
    secretKey: "sk",
    client: fakeClient,
  });
  // No startCycle() — a notice-kind adjudication run outside a chain cycle.
  tracer.recordGeneration({
    model: MODEL,
    input: noticeInput,
    output: { classification: "affirm", rationale: "x" },
    verdict: { classification: "affirm", rationale: "x" },
    latencyMs: 1,
    contentHash: "c".repeat(64),
    adjudicatorId: `gemini:${MODEL}@${RULEBOOK}`,
    rulebookVersion: RULEBOOK,
    kind: "notice",
  });
  assert(
    "recordGeneration with no open cycle creates a standalone trace",
    traces.length === 1,
    String(traces.length),
  );
}

// ── safeTracer SWALLOWS a throwing inner tracer (structural side-channel guarantee) ──────────────────
{
  // A hostile tracer whose every method throws — stands in for a future/partial impl that isn't self-safe.
  const hostile: LlmTracer = {
    startCycle() {
      throw new Error("boom");
    },
    setActivePair() {
      throw new Error("boom");
    },
    recordGeneration() {
      throw new Error("boom");
    },
    recordCacheHit() {
      throw new Error("boom");
    },
    async flush() {
      throw new Error("boom");
    },
    async shutdown() {
      throw new Error("boom");
    },
  };
  const safe = safeTracer(hostile);
  let threw = false;
  try {
    safe.startCycle({ kind: "chain" });
    safe.setActivePair({ fromOcdId: "a", toOcdId: "b" });
    safe.recordGeneration({
      model: MODEL,
      input: noticeInput,
      output: { classification: "affirm", rationale: "x" },
      verdict: { classification: "affirm", rationale: "x" },
      latencyMs: 1,
      contentHash: "a".repeat(64),
      adjudicatorId: `gemini:${MODEL}@${RULEBOOK}`,
      rulebookVersion: RULEBOOK,
      kind: "notice",
    });
    safe.recordCacheHit({
      contentHash: "b".repeat(64),
      adjudicatorId: `gemini:${MODEL}@${RULEBOOK}`,
      rulebookVersion: RULEBOOK,
      kind: "chain",
      classification: "reject",
    });
    await safe.flush();
    await safe.shutdown();
  } catch {
    threw = true;
  }
  assert(
    "safeTracer swallows every throw from a hostile inner tracer (never reaches the path)",
    !threw,
  );
}

console.log("\n=== tracer results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
