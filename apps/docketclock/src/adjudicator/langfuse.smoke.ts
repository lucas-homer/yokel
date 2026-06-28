/**
 * langfuse.smoke.ts — a one-shot LIVE proof that the adjudicator → Langfuse tracing seam works end to end
 * (NOT a gated test; it makes a REAL Gemini call AND ships a real trace to Langfuse). It exercises the exact
 * production path — selectAdjudicator() builds a GeminiAdjudicator with a LangfuseTracer injected from env —
 * but feeds ONE hand-crafted ambiguous chain pair so a generation deterministically lands, instead of
 * waiting for the live poller to happen upon an ambiguous pair.
 *
 * Requires (in repo-root .env): ADJUDICATOR=gemini, a real GEMINI_API_KEY, and all three LANGFUSE_* vars.
 * With `task langfuse` running, LANGFUSE_HOST=http://localhost:3001 reaches the in-cluster server.
 *
 * Run:  pnpm --filter @yokel/docketclock smoke:langfuse
 */
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import type { AdjudicationInput } from "@yokel/contracts";
import { selectAdjudicator } from "./select.js";

// Load the repo-root .env (this file is apps/docketclock/src/adjudicator/ → 4 levels up to the root) BEFORE
// selectAdjudicator() reads process.env. Mirrors the entrypoints' loadEnvFile()-then-select ordering, and
// is GUARDED like poll.smoke.ts: skip if the file is absent so a shell that exports the vars directly still
// runs (unconditional loadEnvFile throws ERR_MISSING_DOTENV_FILE on a fresh checkout/CI).
const envPath = fileURLToPath(new URL("../../../../.env", import.meta.url));
if (existsSync(envPath)) process.loadEnvFile(envPath);

// A synthetic, deliberately AMBIGUOUS amendment chain: B looks like it could extend A's comment period and
// shares a docket, but does not explicitly reference A — exactly the "is this really an amendment?" call the
// deterministic rulebook punts to the LLM. (Public-style FR notice text only; no secrets, no PII.)
const input: AdjudicationInput = {
  kind: "chain",
  rulebook_version: "smoke-langfuse",
  a_title:
    "Airworthiness Directives; Various Transport Category Airplanes — Notice of Proposed Rulemaking",
  a_dates_text: "Comments must be received on or before March 3, 2026.",
  a_publication_date: "2026-01-02",
  b_title:
    "Airworthiness Directives; Various Transport Category Airplanes — Extension of Comment Period",
  b_dates_text:
    "The comment period for the proposed rule is extended to April 17, 2026.",
  b_publication_date: "2026-02-20",
  shared_docket: true,
  shared_rin: false,
  explicit_reference: false,
};

async function main(): Promise<void> {
  const adjudicator = selectAdjudicator();
  console.log(`adjudicator.id = ${adjudicator.id}`);
  if (adjudicator.id.startsWith("null:")) {
    throw new Error(
      "selectAdjudicator() returned the null adjudicator — set ADJUDICATOR=gemini and a real GEMINI_API_KEY in .env",
    );
  }
  // This is a LIVE proof — it must trace to a REAL Langfuse, not silently no-op. selectAdjudicator() →
  // selectTracer() falls back to NOOP_TRACER when any LANGFUSE_* is unset, which would let this smoke "pass"
  // while sending nothing. Assert all three are present and fail loudly instead.
  const missing = [
    "LANGFUSE_HOST",
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
  ].filter((k) => !(process.env[k] || "").trim());
  if (missing.length > 0) {
    throw new Error(
      `missing ${missing.join(", ")} — this live smoke needs a real Langfuse to trace to ` +
        "(set them in .env and run `task langfuse`)",
    );
  }
  // GeminiAdjudicator always carries a tracer, but the Adjudicator port types it `tracer?` — narrow it for
  // TS (strict) and as a last-line guard.
  const tracer = adjudicator.tracer;
  if (!tracer) {
    throw new Error(
      "adjudicator exposes no tracer — expected a LangfuseTracer injected by selectAdjudicator()",
    );
  }
  // Bracket the call the way the chain orchestrator does: open a per-cycle trace, name the active pair so the
  // generation carries from/to OCD-ids, run the real call, then flush so the trace is delivered promptly.
  tracer.startCycle({ kind: "chain", surfaced: 1, cap: 1 });
  tracer.setActivePair({
    fromOcdId: "ocd-notice/smoke-a",
    toOcdId: "ocd-notice/smoke-b",
  });

  console.log("calling Gemini…");
  const verdict = await adjudicator.adjudicate(input);
  console.log("verdict:", JSON.stringify(verdict));

  await tracer.flush();
  await tracer.shutdown();
  console.log(
    "flushed. Open Langfuse → DocketClock project → Traces; look for 'chain-adjudicate-cycle'.",
  );
}

main().catch((err) => {
  console.error("smoke failed:", err);
  process.exit(1);
});
