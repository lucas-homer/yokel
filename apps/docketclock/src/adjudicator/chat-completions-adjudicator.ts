/**
 * adjudicator/chat-completions-adjudicator.ts — an Adjudicator over any OpenAI-compatible
 * `POST {baseUrl}/chat/completions` endpoint. The production target is Cloudflare AI Gateway's REST API
 * (https://api.cloudflare.com/client/v4/accounts/{account}/ai/v1/chat/completions), which fronts Google,
 * OpenAI, Anthropic, xAI and Workers AI (`@cf/...`) models behind ONE request format, ONE Cloudflare API
 * token and ONE bill (Unified Billing). That is what lets the eval compare many models by changing only the
 * `model` string, e.g. "google/gemini-3-flash", "openai/gpt-5.4-mini", "@cf/zai-org/glm-5.3-flash".
 *
 * Raw `fetch` through postJsonWithRetry (no SDK), same as the Gemini adapter. Same FAIL MODE: any failure
 * (HTTP error, timeout, empty choice, non-JSON, invalid classification) THROWS so consult.ts persists
 * nothing — never a fabricated `uncertain`.
 *
 * PORTABILITY LADDER. Providers behind one compat endpoint disagree on optional knobs: some reasoning models
 * reject `temperature: 0`, some reject a strict `json_schema` response_format. On a 400 that names one of
 * those knobs we retry ONCE per knob without it (schema → json_object → none), in that order. The prompt
 * already demands JSON and the parse is strict, so dropping a knob can never let a malformed verdict
 * through — it only lets a model that can't take the knob still be scored. Auth/402/404 never ladder.
 *
 * EFFECT (ADR 0018, slice 4). The call is an Effect program: the ladder is one `Effect.catchTag` on the
 * typed `HttpStatusError`, and a bad answer is a tagged `BadCompletion`. The whole call is one OpenTelemetry
 * GenAI client span (`chat <model>`, with token usage, finish reason, verdict and the knobs the ladder
 * dropped) whose HTTP attempts are child spans. Inside a traced poll pass the span joins that pass's trace
 * (ambient.ts). `adjudicate()` keeps the Promise port and throws exactly what it threw before.
 */
import { AdjudicationVerdict, type AdjudicationInput } from "@yokel/contracts";
import { Data, Effect } from "effect";
import { runAmbient } from "../ambient.js";
import {
  httpPostJson,
  toThrown,
  type FetchLike,
  type HttpError,
  type HttpStatusError,
} from "../sources/http.js";
import { adjudicationContentHash } from "./content-hash.js";
import type { Adjudicator } from "./port.js";
import { SYSTEM_INSTRUCTION, buildPrompt } from "./prompt.js";
import { NOOP_TRACER, type LlmTokenUsage, type LlmTracer } from "./tracer.js";

export interface ChatCompletionsAdjudicatorOpts {
  /** Base URL WITHOUT the trailing `/chat/completions`. */
  baseUrl: string;
  /** Bearer token (for Cloudflare: an API token with Account > Workers AI > Read). */
  apiKey: string;
  /** Model string as the endpoint names it, e.g. "google/gemini-3-flash". */
  model: string;
  /** Extra request headers (e.g. Cloudflare's `cf-aig-gateway-id`). Never put secrets in the id/logs. */
  headers?: Record<string, string>;
  timeoutMs?: number;
  retries?: number;
  transport?: FetchLike;
  tracer?: LlmTracer;
}

const VERDICT_JSON_SCHEMA = {
  type: "object",
  properties: {
    classification: { type: "string", enum: ["affirm", "reject", "uncertain"] },
    rationale: { type: "string" },
  },
  required: ["classification", "rationale"],
  additionalProperties: false,
} as const;

/** Appended to the system message so models that ignore `response_format` still answer in our shape. */
const JSON_INSTRUCTION =
  ' Respond with a single JSON object exactly of the form {"classification": "affirm" | "reject" | ' +
  '"uncertain", "rationale": "<one or two sentences>"} and no other text.';

interface ChatCompletionResponse {
  choices?: Array<{
    message?: {
      content?: string | Array<{ type?: string; text?: string }> | null;
      refusal?: string | null;
    };
    finish_reason?: string;
  }>;
  usage?: {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
  };
}

type ResponseFormatMode = "schema" | "json" | "none";

/** Pull the text out of a choice; some providers return content as an array of parts. */
function contentText(
  content: string | Array<{ type?: string; text?: string }> | null | undefined,
): string | undefined {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    const joined = content
      .map((p) => (typeof p?.text === "string" ? p.text : ""))
      .join("");
    return joined || undefined;
  }
  return undefined;
}

/**
 * Parse the verdict JSON. Tolerates a ```json fence or leading prose ONLY by extracting the outermost
 * {...}; the result still goes through AdjudicationVerdict.parse, so a wrong shape still throws.
 */
export function extractJson(text: string): unknown {
  const trimmed = text.trim();
  try {
    return JSON.parse(trimmed);
  } catch {
    const first = trimmed.indexOf("{");
    const last = trimmed.lastIndexOf("}");
    if (first !== -1 && last > first)
      return JSON.parse(trimmed.slice(first, last + 1));
    throw new Error(`not JSON: ${trimmed.slice(0, 200)}`);
  }
}

function parseUsage(
  u: ChatCompletionResponse["usage"],
): LlmTokenUsage | undefined {
  if (!u) return undefined;
  const usage: LlmTokenUsage = {};
  if (typeof u.prompt_tokens === "number") usage.input = u.prompt_tokens;
  if (typeof u.completion_tokens === "number")
    usage.output = u.completion_tokens;
  if (typeof u.total_tokens === "number") usage.total = u.total_tokens;
  return Object.keys(usage).length > 0 ? usage : undefined;
}

/** The response arrived but holds no usable verdict (no choice, empty text, not JSON). Never retried. */
export class BadCompletion extends Data.TaggedError("BadCompletion")<{
  readonly message: string;
}> {}

/** A 400/422 whose body names a knob we can drop. Other 4xx (401/402/403/404) never ladder. */
function rejectedKnob(
  err: HttpStatusError,
): "temperature" | "response_format" | undefined {
  if (err.status !== 400 && err.status !== 422) return undefined;
  // The same text the pre-Effect ladder matched: the error message, which carries the first 300 body chars.
  const msg = err.message;
  if (/temperature/i.test(msg)) return "temperature";
  if (
    /response_format|json_schema|json schema|structured output|schema/i.test(
      msg,
    )
  )
    return "response_format";
  return undefined;
}

/** `gen_ai.provider.name` from the gateway model id: "google/gemini-3-flash" → "google", "@cf/…" → workers-ai. */
function providerOf(model: string): string {
  if (model.startsWith("@cf/")) return "cloudflare.workers_ai";
  const slash = model.indexOf("/");
  return slash > 0 ? model.slice(0, slash) : "unknown";
}

export class ChatCompletionsAdjudicator implements Adjudicator {
  readonly id: string;
  readonly tracer: LlmTracer;
  private readonly url: string;
  private readonly apiKey: string;
  private readonly model: string;
  private readonly headers: Record<string, string>;
  private readonly timeoutMs: number;
  private readonly retries: number;
  private readonly transport?: FetchLike;

  constructor(opts: ChatCompletionsAdjudicatorOpts) {
    const apiKey = opts.apiKey?.trim() ?? "";
    if (!apiKey)
      throw new Error("ChatCompletionsAdjudicator requires a non-empty apiKey");
    const model = opts.model?.trim() ?? "";
    if (!model)
      throw new Error("ChatCompletionsAdjudicator requires a non-empty model");
    const baseUrl = opts.baseUrl?.trim().replace(/\/+$/, "") ?? "";
    if (!baseUrl)
      throw new Error(
        "ChatCompletionsAdjudicator requires a non-empty baseUrl",
      );
    this.apiKey = apiKey;
    this.model = model;
    this.url = `${baseUrl}/chat/completions`;
    this.headers = opts.headers ?? {};
    this.timeoutMs = opts.timeoutMs ?? 15_000;
    this.retries = opts.retries ?? 4;
    this.transport = opts.transport;
    this.tracer = opts.tracer ?? NOOP_TRACER;
    // Provenance is the model id itself (e.g. "google/gemini-3-flash"): the transport is always the gateway,
    // so only the model changes what a verdict means.
    this.id = model;
  }

  private body(
    input: AdjudicationInput,
    withTemperature: boolean,
    format: ResponseFormatMode,
  ) {
    return {
      model: this.model,
      messages: [
        { role: "system", content: SYSTEM_INSTRUCTION + JSON_INSTRUCTION },
        { role: "user", content: buildPrompt(input) },
      ],
      ...(withTemperature ? { temperature: 0 } : {}),
      ...(format === "schema"
        ? {
            response_format: {
              type: "json_schema",
              json_schema: {
                name: "adjudication_verdict",
                strict: true,
                schema: VERDICT_JSON_SCHEMA,
              },
            },
          }
        : format === "json"
          ? { response_format: { type: "json_object" } }
          : {}),
    };
  }

  /**
   * One send, then the ladder: a 400/422 that names a droppable knob re-sends once without it. Every other
   * failure passes through untouched.
   */
  private send(
    input: AdjudicationInput,
    withTemperature: boolean,
    format: ResponseFormatMode,
    dropped: string[],
  ): Effect.Effect<ChatCompletionResponse, HttpError> {
    return httpPostJson(this.url, this.body(input, withTemperature, format), {
      headers: { Authorization: `Bearer ${this.apiKey}`, ...this.headers },
      timeoutMs: this.timeoutMs,
      retries: this.retries,
      ...(this.transport ? { transport: this.transport } : {}),
    }).pipe(
      Effect.map((raw) => raw as ChatCompletionResponse),
      // At most 1 (temperature) + 2 (schema→json→none) knob drops, so this recursion is bounded at 4 sends.
      Effect.catchTag("HttpStatusError", (err) => {
        const knob = rejectedKnob(err);
        if (knob === "temperature" && withTemperature) {
          return this.send(input, false, format, [...dropped, "temperature"]);
        }
        if (knob === "response_format" && format !== "none") {
          const next = format === "schema" ? "json" : "none";
          return this.send(input, withTemperature, next, [
            ...dropped,
            `response_format:${format}`,
          ]);
        }
        return Effect.fail(err);
      }),
      Effect.tap(() =>
        dropped.length > 0
          ? Effect.annotateCurrentSpan(
              "docketclock.ladder.dropped",
              dropped.join(","),
            )
          : Effect.void,
      ),
    );
  }

  /** The verdict in the completion, or a BadCompletion saying why there isn't one. */
  private verdictOf(
    raw: ChatCompletionResponse,
  ): Effect.Effect<AdjudicationVerdict, BadCompletion> {
    const choice = raw.choices?.[0];
    if (!choice)
      return Effect.fail(
        new BadCompletion({ message: `${this.id}: no choice in response` }),
      );
    const text = contentText(choice.message?.content);
    if (!text) {
      return Effect.fail(
        new BadCompletion({
          message: `${this.id}: empty choice (finish_reason=${choice.finish_reason ?? "unknown"}${
            choice.message?.refusal
              ? `, refusal=${choice.message.refusal.slice(0, 100)}`
              : ""
          })`,
        }),
      );
    }
    return Effect.try({
      try: () => extractJson(text),
      catch: () =>
        new BadCompletion({
          message: `${this.id}: choice text was not valid JSON: ${text.slice(0, 200)}`,
        }),
    }).pipe(
      // A wrong verdict shape is a ZodError, rethrown as-is at the Promise boundary (a defect here).
      Effect.map((parsed) => AdjudicationVerdict.parse(parsed)),
    );
  }

  /** The whole adjudication as an Effect: one GenAI client span around the sends, the parse and the record. */
  adjudicateEffect(
    input: AdjudicationInput,
  ): Effect.Effect<AdjudicationVerdict, HttpError | BadCompletion> {
    const self = this;
    return Effect.gen(function* () {
      const startedAt = Date.now();
      const raw = yield* self.send(input, true, "schema", []);
      const latencyMs = Date.now() - startedAt;
      const usage = parseUsage(raw.usage);
      if (usage?.input !== undefined)
        yield* Effect.annotateCurrentSpan(
          "gen_ai.usage.input_tokens",
          usage.input,
        );
      if (usage?.output !== undefined)
        yield* Effect.annotateCurrentSpan(
          "gen_ai.usage.output_tokens",
          usage.output,
        );
      const finish = raw.choices?.[0]?.finish_reason;
      if (finish)
        yield* Effect.annotateCurrentSpan("gen_ai.response.finish_reasons", [
          finish,
        ]);
      const verdict = yield* self.verdictOf(raw);
      yield* Effect.annotateCurrentSpan(
        "docketclock.verdict.classification",
        verdict.classification,
      );
      const contentHash = adjudicationContentHash(input);
      self.tracer.recordGeneration({
        model: self.model,
        input,
        output: verdict,
        verdict,
        ...(usage ? { usage } : {}),
        latencyMs,
        contentHash,
        adjudicatorId: `${self.id}@${input.rulebook_version}`,
        rulebookVersion: input.rulebook_version,
        kind: input.kind,
      });
      return verdict;
    }).pipe(
      // OpenTelemetry GenAI conventions: span "chat <model>", kind client.
      Effect.withSpan(`chat ${this.model}`, {
        kind: "client",
        attributes: {
          "gen_ai.operation.name": "chat",
          "gen_ai.provider.name": providerOf(this.model),
          "gen_ai.request.model": this.model,
          "gen_ai.request.temperature": 0,
          "docketclock.adjudication.kind": input.kind,
          "docketclock.rulebook_version": input.rulebook_version,
        },
      }),
    );
  }

  /** The Promise port: the same errors as before (HTTP errors as http.ts throws them, a BadCompletion's message). */
  adjudicate(input: AdjudicationInput): Promise<AdjudicationVerdict> {
    return runAmbient(
      this.adjudicateEffect(input).pipe(
        Effect.catch((err) =>
          Effect.die(
            err._tag === "BadCompletion"
              ? new Error(err.message)
              : toThrown(err),
          ),
        ),
      ),
    );
  }
}
