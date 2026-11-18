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
 */
import { AdjudicationVerdict, type AdjudicationInput } from "@yokel/contracts";
import { postJsonWithRetry, type FetchLike } from "../sources/http.js";
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

/** A 400/422 whose body names a knob we can drop. Other 4xx (401/402/403/404) never ladder. */
function rejectedKnob(
  err: unknown,
): "temperature" | "response_format" | undefined {
  const msg = err instanceof Error ? err.message : String(err);
  if (!/-> (400|422) /.test(msg)) return undefined;
  if (/temperature/i.test(msg)) return "temperature";
  if (
    /response_format|json_schema|json schema|structured output|schema/i.test(
      msg,
    )
  )
    return "response_format";
  return undefined;
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

  async adjudicate(input: AdjudicationInput): Promise<AdjudicationVerdict> {
    let withTemperature = true;
    let format: ResponseFormatMode = "schema";
    const startedAt = Date.now();
    let raw: ChatCompletionResponse;
    // At most 1 (temperature) + 2 (schema→json→none) knob drops, so the loop is bounded at 4 sends.
    for (;;) {
      try {
        raw = (await postJsonWithRetry(
          this.url,
          this.body(input, withTemperature, format),
          {
            headers: {
              Authorization: `Bearer ${this.apiKey}`,
              ...this.headers,
            },
            timeoutMs: this.timeoutMs,
            retries: this.retries,
            ...(this.transport ? { transport: this.transport } : {}),
          },
        )) as ChatCompletionResponse;
        break;
      } catch (err) {
        const knob = rejectedKnob(err);
        if (knob === "temperature" && withTemperature) {
          withTemperature = false;
          continue;
        }
        if (knob === "response_format" && format !== "none") {
          format = format === "schema" ? "json" : "none";
          continue;
        }
        throw err;
      }
    }
    const latencyMs = Date.now() - startedAt;

    const choice = raw.choices?.[0];
    if (!choice) throw new Error(`${this.id}: no choice in response`);
    const text = contentText(choice.message?.content);
    if (!text) {
      throw new Error(
        `${this.id}: empty choice (finish_reason=${choice.finish_reason ?? "unknown"}${
          choice.message?.refusal
            ? `, refusal=${choice.message.refusal.slice(0, 100)}`
            : ""
        })`,
      );
    }
    let parsed: unknown;
    try {
      parsed = extractJson(text);
    } catch {
      throw new Error(
        `${this.id}: choice text was not valid JSON: ${text.slice(0, 200)}`,
      );
    }
    const verdict = AdjudicationVerdict.parse(parsed);
    const usage = parseUsage(raw.usage);
    this.tracer.recordGeneration({
      model: this.model,
      input,
      output: verdict,
      verdict,
      ...(usage ? { usage } : {}),
      latencyMs,
      contentHash: adjudicationContentHash(input),
      adjudicatorId: `${this.id}@${input.rulebook_version}`,
      rulebookVersion: input.rulebook_version,
      kind: input.kind,
    });
    return verdict;
  }
}
