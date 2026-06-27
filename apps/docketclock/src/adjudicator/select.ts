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
 *   2. The provider's OWN key must be present: GEMINI_API_KEY. (Credentials are provider-specific, so the env
 *      var names the provider — the provider-agnostic seam is THIS selector + the Adjudicator port, not the
 *      key name. A future provider adds its own branch reading e.g. ANTHROPIC_API_KEY.) ADJUDICATOR=gemini
 *      with NO key → NullAdjudicator (we do NOT construct a keyless gemini client).
 *   3. Only when both hold do we return GeminiAdjudicator with:
 *        - GEMINI_MODEL   (default "gemini-2.5-flash") → id "gemini:<model>"
 *        - GEMINI_BASE_URL (optional; default the public endpoint)
 *        - LLM_TIMEOUT_MS (generic — a timeout is provider-agnostic behavior, not a credential; default 15000)
 */
import type { Adjudicator } from "./port.js";
import { NullAdjudicator } from "./null-adjudicator.js";
import { GeminiAdjudicator } from "./gemini-adjudicator.js";
import { NOOP_TRACER, safeTracer, type LlmTracer } from "./tracer.js";
import { LangfuseTracer } from "./langfuse-tracer.js";

const DEFAULT_MODEL = "gemini-2.5-flash";
const DEFAULT_TIMEOUT_MS = 15_000;

/**
 * selectTracer — pick the LLM observability tracer (PR-C2). ALL-OR-NOTHING: a Langfuse-backed tracer is
 * returned ONLY when LANGFUSE_HOST, LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are ALL present (trimmed —
 * ESO/Vault secrets commonly carry a trailing newline). Otherwise a NoopTracer is returned and the
 * `langfuse` client is NEVER constructed, so a deploy without Langfuse (and every test) is a true no-op with
 * byte-for-byte unchanged adjudication behavior. Reads env LAZILY (at call time), so the entrypoints'
 * `process.loadEnvFile()`-then-import ordering is respected.
 */
export function selectTracer(env: NodeJS.ProcessEnv = process.env): LlmTracer {
  const host = (env.LANGFUSE_HOST || "").trim();
  const publicKey = (env.LANGFUSE_PUBLIC_KEY || "").trim();
  const secretKey = (env.LANGFUSE_SECRET_KEY || "").trim();
  if (!host || !publicKey || !secretKey) return NOOP_TRACER;
  // Guard construction (defense-in-depth): `new Langfuse()` is lazy today, but a future SDK/bad config that
  // threw here would otherwise break the poll cycle on the DETERMINISTIC path. Fall back to a true no-op.
  // safeTracer wraps every method so no tracer call can ever throw into the adjudication/reconcile path.
  try {
    return safeTracer(new LangfuseTracer({ host, publicKey, secretKey }));
  } catch {
    return NOOP_TRACER;
  }
}

export function selectAdjudicator(
  env: NodeJS.ProcessEnv = process.env,
): Adjudicator {
  const provider = (env.ADJUDICATOR ?? "").trim().toLowerCase();
  if (provider !== "gemini") {
    // unset / "null" / anything else → the safe abstain default.
    return new NullAdjudicator();
  }

  // The gemini provider reads its OWN key, GEMINI_API_KEY (a credential is provider-specific — the
  // abstraction lives in this selector, not the key name). TRIM it: secret material from K8s/Vault/ESO
  // commonly carries a trailing newline, and a whitespace-only value is NOT a usable key — treating it as
  // present would construct a client that 400s every cycle instead of degrading. Trimming keeps the
  // safe-default guard honest for mis-provisioned env.
  const apiKey = (env.GEMINI_API_KEY || "").trim();
  if (!apiKey) {
    // provider selected but no (usable) key → do NOT construct a keyless client; degrade to abstain.
    return new NullAdjudicator();
  }

  const model = (env.GEMINI_MODEL || "").trim() || DEFAULT_MODEL;
  const baseUrl = (env.GEMINI_BASE_URL || "").trim();
  const timeoutMs = Number(env.LLM_TIMEOUT_MS);
  // Construct the observability tracer ONCE here and inject it: the SAME instance is shared between the
  // adapter (which records each real call as a generation) and the chain orchestrator (which reads it off
  // `adjudicator.tracer` to open the per-cycle trace + flush). No LANGFUSE_* env → NoopTracer (true no-op).
  return new GeminiAdjudicator({
    apiKey,
    model,
    ...(baseUrl ? { baseUrl } : {}),
    timeoutMs:
      Number.isFinite(timeoutMs) && timeoutMs > 0
        ? timeoutMs
        : DEFAULT_TIMEOUT_MS,
    tracer: selectTracer(env),
  });
}
