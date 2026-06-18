/**
 * adjudicator/gemini-adjudicator.ts — Slice 3a: a concrete Adjudicator backed by Google Gemini's
 * generateContent API, behind the provider-NEUTRAL port (port.ts). Raw `fetch` only — NO @google/genai
 * SDK dependency (keeps the subsystem dependency-light and the wire format auditable here).
 *
 * NOT WIRED into any pipeline in this slice: nothing in src/sources|reconcile|poll constructs or calls
 * this. It is selected (config-driven) by select.ts, exercised only by tests against an injectable
 * transport. The live-key wire-up is a later integrator step.
 *
 * FAIL MODE — THROW, persist nothing. consult.ts is the read-through cache and it already handles a thrown
 * adjudicate() correctly: the error propagates and NOTHING is persisted, so the next consult retries
 * cleanly. We therefore do NOT fall back to an `uncertain` verdict on failure — a persisted abstain would
 * make the `adjudicator_id` provenance LIE (record "gemini:..." for a verdict the model never produced) and
 * would poison the write-once cache with a fabricated answer. ANY failure here (HTTP error, abort/timeout,
 * blocked/empty candidate, non-JSON text, shape mismatch, invalid classification) is a throw. `uncertain` is
 * reserved for a verdict the model GENUINELY emitted (it was instructed to abstain when unsure).
 *
 * Wire format CONFIRMED against the live v1beta discovery doc
 * (https://generativelanguage.googleapis.com/$discovery/rest?version=v1beta) and a live 400 probe:
 *   - endpoint:  POST {baseUrl}/v1beta/models/{model}:generateContent
 *   - auth:      x-goog-api-key header (NOT a query string — avoids key-in-URL logging). A bad/absent key
 *                returns HTTP 400 INVALID_ARGUMENT (non-retriable 4xx → fails fast).
 *   - request:   { systemInstruction: Content, contents: Content[], generationConfig: {...} }
 *   - structured output: generationConfig.responseMimeType="application/json" +
 *                responseSchema (a Schema: type/enum/properties/required, with UPPERCASE type values like
 *                "OBJECT"/"STRING") + temperature: 0.
 *   - response:  candidates[0].content.parts[0].text holds the JSON string we parse.
 */
import { AdjudicationVerdict, type AdjudicationInput } from "@yokel/contracts";
import { postJsonWithRetry, type FetchLike } from "../sources/http.js";
import type { Adjudicator } from "./port.js";

export interface GeminiAdjudicatorOpts {
  apiKey: string;
  model: string;
  /** default https://generativelanguage.googleapis.com */
  baseUrl?: string;
  /** hard per-attempt timeout (AbortController). default 15_000. */
  timeoutMs?: number;
  /** retries on network/abort/429/5xx (default 4). 4xx never retries. */
  retries?: number;
  /** injectable transport (default global fetch) — tests pass a spy. */
  transport?: FetchLike;
}

const DEFAULT_BASE = "https://generativelanguage.googleapis.com";

/**
 * The responseSchema we constrain the model to: an OBJECT with a categorical `classification` (the exact
 * three contract enum values) and a free-text `rationale`, BOTH required. This pins the model to the
 * AdjudicationVerdict shape on the wire. We deliberately offer NO `confidence` field — confidence is never
 * LLM-scored (and AdjudicationVerdict.parse would strip it anyway).
 */
const RESPONSE_SCHEMA = {
  type: "OBJECT",
  properties: {
    classification: {
      type: "STRING",
      enum: ["affirm", "reject", "uncertain"],
    },
    rationale: { type: "STRING" },
  },
  required: ["classification", "rationale"],
} as const;

const SYSTEM_INSTRUCTION =
  "You classify ambiguous U.S. regulatory public-comment-period notices. Answer ONLY with the structured " +
  "fields requested (classification + rationale), nothing else. When you are genuinely unsure, you MUST " +
  'abstain by answering classification="uncertain" rather than guess.';

/** Build the user-facing prompt text from the discriminated input. */
function buildPrompt(input: AdjudicationInput): string {
  if (input.kind === "notice") {
    return [
      `Is this notice title a GENUINE "${input.flag_key}" action, or a keyword false-positive`,
      `(the word appears but the notice is not actually a "${input.flag_key}" action)?`,
      "",
      `Title: ${input.text}`,
      "",
      'Answer "affirm" if it is a genuine action of that kind, "reject" if it is a keyword',
      'false-positive, or "uncertain" if you cannot tell.',
    ].join("\n");
  }
  // chain
  return [
    "Does notice B genuinely AMEND notice A (e.g. extend/reopen/modify A's comment period or rule),",
    "or are they merely two related-looking notices that do not actually form an amendment chain?",
    "",
    "Notice A (the original):",
    `  title: ${input.a_title}`,
    `  dates text: ${input.a_dates_text ?? "(none)"}`,
    `  publication date: ${input.a_publication_date ?? "(none)"}`,
    "",
    "Notice B (the candidate amendment):",
    `  title: ${input.b_title}`,
    `  dates text: ${input.b_dates_text ?? "(none)"}`,
    `  publication date: ${input.b_publication_date ?? "(none)"}`,
    "",
    "Corroboration signals (deterministically computed):",
    `  shared docket: ${input.shared_docket}`,
    `  shared RIN: ${input.shared_rin}`,
    `  B explicitly references A: ${input.explicit_reference}`,
    "",
    'Answer "affirm" if B genuinely amends A, "reject" if it does not, or "uncertain" if you cannot tell.',
  ].join("\n");
}

/** Minimal shape we read off the generateContent response; everything else is ignored. */
interface GenerateContentResponse {
  candidates?: Array<{
    content?: { parts?: Array<{ text?: string }> };
    finishReason?: string;
  }>;
  promptFeedback?: { blockReason?: string };
}

export class GeminiAdjudicator implements Adjudicator {
  readonly id: string;
  private readonly apiKey: string;
  private readonly model: string;
  private readonly baseUrl: string;
  private readonly timeoutMs: number;
  private readonly retries: number;
  private readonly transport?: FetchLike;

  constructor(opts: GeminiAdjudicatorOpts) {
    if (!opts.apiKey) {
      throw new Error("GeminiAdjudicator requires a non-empty apiKey");
    }
    this.apiKey = opts.apiKey;
    this.model = opts.model;
    this.baseUrl = (opts.baseUrl ?? DEFAULT_BASE).replace(/\/+$/, "");
    this.timeoutMs = opts.timeoutMs ?? 15_000;
    this.retries = opts.retries ?? 4;
    this.transport = opts.transport;
    // provenance fragment, e.g. "gemini:gemini-2.5-flash" — recorded on the cache row by consult.ts.
    this.id = `gemini:${this.model}`;
  }

  async adjudicate(input: AdjudicationInput): Promise<AdjudicationVerdict> {
    const url = `${this.baseUrl}/v1beta/models/${this.model}:generateContent`;
    const requestBody = {
      systemInstruction: {
        parts: [{ text: SYSTEM_INSTRUCTION }],
      },
      contents: [
        {
          role: "user",
          parts: [{ text: buildPrompt(input) }],
        },
      ],
      generationConfig: {
        temperature: 0,
        responseMimeType: "application/json",
        responseSchema: RESPONSE_SCHEMA,
      },
    };

    const raw = (await postJsonWithRetry(url, requestBody, {
      // key in the HEADER, never the URL (avoids key-in-URL logging).
      headers: { "x-goog-api-key": this.apiKey },
      timeoutMs: this.timeoutMs,
      retries: this.retries,
      ...(this.transport ? { transport: this.transport } : {}),
    })) as GenerateContentResponse;

    const candidate = raw.candidates?.[0];
    if (!candidate) {
      const reason = raw.promptFeedback?.blockReason;
      throw new Error(
        `gemini: no candidate in response${reason ? ` (blockReason=${reason})` : ""}`,
      );
    }
    const parts = candidate.content?.parts;
    const text = parts?.[0]?.text;
    if (typeof text !== "string" || text.length === 0) {
      throw new Error(
        `gemini: empty/blocked candidate (finishReason=${candidate.finishReason ?? "unknown"})`,
      );
    }

    let parsed: unknown;
    try {
      parsed = JSON.parse(text);
    } catch {
      throw new Error(
        `gemini: candidate text was not valid JSON: ${text.slice(0, 200)}`,
      );
    }

    // AdjudicationVerdict.parse strips any stray field (incl. a hallucinated `confidence`) and REJECTS an
    // invalid classification — a parse failure throws, which consult.ts turns into "persist nothing".
    return AdjudicationVerdict.parse(parsed);
  }
}
