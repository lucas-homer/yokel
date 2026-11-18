/**
 * adjudicator/select.ts — builds the Adjudicator the poller uses.
 *
 * Every LLM call goes through Cloudflare AI Gateway (ai-gateway.ts below: one Cloudflare API token, one
 * bill, every call in the gateway's logs). The only real choice is WHICH MODEL, and the live one is the
 * ADJUDICATOR_MODEL constant in ./model.ts — change models with a reviewed one-line diff there, after the
 * "Eval — compare models" workflow picks a winner.
 *
 * ADJUDICATOR (env) is an override, not the source of truth:
 *   - unset / ""             → ADJUDICATOR_MODEL (the live model)
 *   - "off" | "null" | "none" → NullAdjudicator (deterministic-only)
 *   - a catalog id containing "/" (e.g. "openai/gpt-5.4-mini", "@cf/zai-org/glm-5.3-flash") → that model
 *   - anything else (e.g. the retired "gemini") → NullAdjudicator, so a stale value can never call a
 *     made-up model id.
 * The gateway needs CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_AI_TOKEN (Account > Workers AI > Read); missing
 * either → NullAdjudicator, so tests, CI and keyless dev never reach the network.
 * Optional: CLOUDFLARE_AI_GATEWAY (gateway id, default "default"), LLM_TIMEOUT_MS (default 15000).
 */
import type { Adjudicator } from "./port.js";
import { NullAdjudicator } from "./null-adjudicator.js";
import { ADJUDICATOR_MODEL } from "./model.js";
import { ChatCompletionsAdjudicator } from "./chat-completions-adjudicator.js";
import {
  NOOP_TRACER,
  safeTracer,
  composeTracers,
  type LlmTracer,
} from "./tracer.js";
import { LangfuseTracer } from "./langfuse-tracer.js";
import { getMetricsTracer } from "./metrics-tracer.js";

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

/**
 * aiGatewayAdjudicator — the Cloudflare AI Gateway adjudicator for one model, or undefined when the
 * account id / token are missing. Exported so the eval can build one per candidate model with its own tracer.
 */
export function aiGatewayAdjudicator(
  env: NodeJS.ProcessEnv,
  model: string,
  tracer?: LlmTracer,
): ChatCompletionsAdjudicator | undefined {
  const accountId = (env.CLOUDFLARE_ACCOUNT_ID || "").trim();
  // TRIM: secret material commonly carries a trailing newline; whitespace-only is not a usable token.
  const apiKey = (env.CLOUDFLARE_AI_TOKEN || "").trim();
  if (!accountId || !apiKey) return undefined;
  const gateway = (env.CLOUDFLARE_AI_GATEWAY || "").trim() || "default";
  const timeoutMs = Number(env.LLM_TIMEOUT_MS);
  return new ChatCompletionsAdjudicator({
    baseUrl: `https://api.cloudflare.com/client/v4/accounts/${accountId}/ai/v1`,
    apiKey,
    model,
    headers: { "cf-aig-gateway-id": gateway },
    timeoutMs:
      Number.isFinite(timeoutMs) && timeoutMs > 0
        ? timeoutMs
        : DEFAULT_TIMEOUT_MS,
    // ONE tracer instance shared by the adapter (records each real call) and the chain orchestrator (reads
    // it off `adjudicator.tracer` for the per-cycle trace + flush): the always-on MetricsTracer plus the
    // all-or-nothing Langfuse tracer (dropped when LANGFUSE_* is unset).
    tracer: tracer ?? composeTracers(getMetricsTracer(), selectTracer(env)),
  });
}

/** Resolve which model the ADJUDICATOR override asks for; undefined means "off". */
export function resolveAdjudicatorModel(
  env: NodeJS.ProcessEnv = process.env,
): string | undefined {
  const raw = (env.ADJUDICATOR ?? "").trim();
  if (!raw) return ADJUDICATOR_MODEL;
  if (["off", "null", "none"].includes(raw.toLowerCase())) return undefined;
  return raw.includes("/") ? raw : undefined;
}

export function selectAdjudicator(
  env: NodeJS.ProcessEnv = process.env,
): Adjudicator {
  const model = resolveAdjudicatorModel(env);
  if (!model) return new NullAdjudicator();
  return aiGatewayAdjudicator(env, model) ?? new NullAdjudicator();
}
