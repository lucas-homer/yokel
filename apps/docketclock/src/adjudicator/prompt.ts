/**
 * adjudicator/prompt.ts — the provider-NEUTRAL prompt shared by every LLM adapter (Gemini, the Cloudflare
 * AI Gateway chat-completions adapter, ...). Keeping ONE copy is what makes a cross-model eval a fair
 * comparison: every model sees byte-identical instructions and input text.
 */
import type { AdjudicationInput } from "@yokel/contracts";

export const SYSTEM_INSTRUCTION =
  "You classify ambiguous U.S. regulatory public-comment-period notices. Answer ONLY with the structured " +
  "fields requested (classification + rationale), nothing else. When you are genuinely unsure, you MUST " +
  'abstain by answering classification="uncertain" rather than guess.';

/** Build the user-facing prompt text from the discriminated input. */
export function buildPrompt(input: AdjudicationInput): string {
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
  if (input.kind === "chain") {
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
  // Exhaustiveness guard: AdjudicationInput is a discriminated union, so if a new `kind` is ever added
  // the compiler flags this `never` assignment — and at runtime we throw rather than silently emit a
  // prompt for the wrong shape (which would ask the model to decide blind).
  const _exhaustive: never = input;
  throw new Error(
    `buildPrompt: unhandled AdjudicationInput kind: ${JSON.stringify(_exhaustive)}`,
  );
}
