/**
 * adjudicator/select.ts — the config-driven factory that picks WHICH Adjudicator the substrate uses.
 * Slice 3a wires gemini-or-null; the SAFE DEFAULT is NullAdjudicator (abstain), so prod/CI with no
 * provider configured and no API key is unchanged and never reaches the network.
 *
 * NOT wired into any pipeline in this slice — nothing in src/sources|reconcile|poll calls this yet. The
 * live integrator step provisions the key and invokes selectAdjudicator(); until then this is exercised
 * only by tests.
 *
 * PRECEDENCE (a Gemini adapter requires BOTH a provider selector AND a key, else we fall back to null):
 *   1. ADJUDICATOR must equal "gemini" (case-insensitive). Any other value, or unset, or "null" → NullAdjudicator.
 *   2. A key must be present: LLM_API_KEY (generic — what we provision) takes precedence, else GEMINI_API_KEY.
 *      ADJUDICATOR=gemini with NO key → NullAdjudicator (we do NOT construct a keyless gemini client).
 *   3. Only when both hold do we return GeminiAdjudicator with:
 *        - GEMINI_MODEL   (default "gemini-2.5-flash") → id "gemini:<model>"
 *        - GEMINI_BASE_URL (optional; default the public endpoint)
 *        - LLM_TIMEOUT_MS (default 15000)
 */
import type { Adjudicator } from "./port.js";
import { NullAdjudicator } from "./null-adjudicator.js";
import { GeminiAdjudicator } from "./gemini-adjudicator.js";

const DEFAULT_MODEL = "gemini-2.5-flash";
const DEFAULT_TIMEOUT_MS = 15_000;

export function selectAdjudicator(
  env: NodeJS.ProcessEnv = process.env,
): Adjudicator {
  const provider = (env.ADJUDICATOR ?? "").trim().toLowerCase();
  if (provider !== "gemini") {
    // unset / "null" / anything else → the safe abstain default.
    return new NullAdjudicator();
  }

  // generic LLM_API_KEY wins; fall back to the provider-specific GEMINI_API_KEY.
  const apiKey = env.LLM_API_KEY || env.GEMINI_API_KEY || "";
  if (!apiKey) {
    // provider selected but no key → do NOT construct a keyless client; degrade to abstain.
    return new NullAdjudicator();
  }

  const model = env.GEMINI_MODEL || DEFAULT_MODEL;
  const timeoutMs = Number(env.LLM_TIMEOUT_MS);
  return new GeminiAdjudicator({
    apiKey,
    model,
    ...(env.GEMINI_BASE_URL ? { baseUrl: env.GEMINI_BASE_URL } : {}),
    timeoutMs:
      Number.isFinite(timeoutMs) && timeoutMs > 0
        ? timeoutMs
        : DEFAULT_TIMEOUT_MS,
  });
}
