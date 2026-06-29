/**
 * adjudicator/eval-gold.ts — the GOLD-LABEL file: human ground truth for the chain-adjudicator eval (Slice
 * D). The eval corpus is a git-committed JSON array (apps/docketclock/eval/chain-gold.json). Each entry
 * EMBEDS the full AdjudicationInput (public FR text — no PII), so the eval runner is self-contained: it
 * needs NO Postgres and NO Langfuse to score, just this file + the model. `model_verdict` is the model's
 * own historical call, kept for REFERENCE only — `gold` is the human's authoritative label.
 *
 * loadGold() parses + VALIDATES the file and fails loudly on a malformed or half-labeled corpus (a missing
 * or null `gold`, or an `input` that no longer satisfies the frozen contract). This is the seam D2's
 * `eval:chain` consumes. Pure (no I/O beyond the single readFile) and unit-tested (test/eval-gold.test.ts).
 *
 * `gold` reuses the contract's AdjudicationClassification enum (affirm|reject|uncertain) — the SAME shape the
 * adjudicator emits — so scoring is a direct categorical compare. The template produced by
 * scripts/export-gold-template.ts carries `gold: null`; copy it to chain-gold.json and fill each `gold`.
 */
import { readFileSync } from "node:fs";
import {
  AdjudicationInput,
  AdjudicationClassification,
  AdjudicationVerdict,
  PayloadHash,
} from "@yokel/contracts";
import { z } from "zod";

/** Safely turn an unknown thrown value into a message (a non-Error throw must not itself throw here). */
function errMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

/** One labeled corpus entry. `gold` is REQUIRED (a template's null/missing gold fails validation). */
export const GoldEntry = z.object({
  /** sha256 cache key — the `adjudications` row's content_hash and the Langfuse dataset item id. Validated
   *  as a 64-hex PayloadHash (same shape as AdjudicationRecord.content_hash) so a malformed key is caught. */
  content_hash: PayloadHash,
  /** the human's authoritative label. */
  gold: AdjudicationClassification,
  /** optional free-text rationale for the label (why a human called it this way). */
  note: z.string().optional().default(""),
  /** the model's own historical verdict — REFERENCE only, never authoritative. */
  model_verdict: AdjudicationVerdict.optional(),
  /** the full adjudication input the model was (and the eval will be) given. */
  input: AdjudicationInput,
});
export type GoldEntry = z.infer<typeof GoldEntry>;

/** The whole gold corpus: a non-empty array of labeled entries with UNIQUE content_hashes. */
export const GoldFile = z
  .array(GoldEntry)
  .min(1, "gold file is empty — export a template and label it first")
  .superRefine((entries, ctx) => {
    const seen = new Set<string>();
    for (const e of entries) {
      if (seen.has(e.content_hash)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `duplicate content_hash in gold file: ${e.content_hash}`,
        });
      }
      seen.add(e.content_hash);
    }
  });
export type GoldFile = z.infer<typeof GoldFile>;

/**
 * Read + validate the gold corpus at `path`. Throws with a clear message on bad JSON, a schema violation
 * (e.g. a still-null `gold`, an `input` that fails the contract), an empty array, or a duplicate hash.
 */
export function loadGold(path: string): GoldEntry[] {
  let raw: string;
  try {
    raw = readFileSync(path, "utf8");
  } catch (err) {
    throw new Error(
      `could not read gold file at ${path} (export+label it first): ${errMessage(err)}`,
    );
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (err) {
    throw new Error(
      `gold file at ${path} is not valid JSON: ${errMessage(err)}`,
    );
  }
  const result = GoldFile.safeParse(parsed);
  if (!result.success) {
    throw new Error(
      `gold file at ${path} failed validation:\n${result.error.issues
        .map((i) => `  • ${i.path.join(".") || "(root)"}: ${i.message}`)
        .join("\n")}`,
    );
  }
  return result.data;
}
