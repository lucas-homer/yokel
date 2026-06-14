/**
 * @yokel/contracts — the shared seam between the DocketClock substrate and vertical wedges
 * (Watershed Watch). Verticals join on stable OCD-IDs, never internal UUIDs.
 *
 * STATUS: schema STUB derived from docs/architecture/docketclock.md. Field shapes are pinned to the
 * synthesized design; validation logic, refinements, and the reconciliation rulebook are TODO and
 * land when DocketClock is built (after the Week-1 spikes). Do not treat as final.
 */
import { z } from "zod";

/** Confidence is first-class and ALWAYS present. Never ML/LLM-scored; deterministic rulebook only. */
export const Confidence = z.enum([
  "high",
  "medium",
  "low",
  "conflicting", // the marquee differentiator: existing single-source tools give NO signal here
  "stale",
  "unknown",
]);
export type Confidence = z.infer<typeof Confidence>;

/** Typed (not boolean) so consumers handle each failure mode distinctly. */
export const ConflictFlag = z.enum([
  "fr_regs_date_mismatch",
  "tz_normalization_only", // same Eastern date, differ only in UTC — MEDIUM, never CONFLICTING
  "extension_chain_unresolved",
  "correction_pending",
  "withdrawn_vs_open",
  "null_end_date_open_status",
  "late_comment_ambiguous",
  "multi_target_notice",
  "keyword_false_positive", // e.g. the BLM "land-withdrawal extension" trap
]);
export type ConflictFlag = z.infer<typeof ConflictFlag>;

export const WindowType = z.enum([
  "comment",
  "hearing",
  "information_collection",
  "eis_draft", // schema slot for Watershed Watch EIS clock — NOT ingested by the substrate
  "eis_final",
  "other",
]);
export type WindowType = z.infer<typeof WindowType>;

export const WindowStatus = z.enum([
  "open",
  "closed",
  "extended",
  "reopened",
  "withdrawn",
  "finalized",
  "unknown",
]);
export type WindowStatus = z.infer<typeof WindowStatus>;

/**
 * Stable Open Civic Data identifier — the cross-system join key.
 * Federal scheme: ocd-participation-window/federal/{frDocNum}
 *   (or regs:{regsObjectId} when the FR document number is absent).
 * Generated once at first observation; NEVER changes across extensions.
 */
export const OcdId = z.string().regex(/^ocd-participation-window\/federal\/.+/);
export type OcdId = z.infer<typeof OcdId>;

export function makeOcdId(opts: { frDocNum?: string; regsObjectId?: string }): OcdId {
  if (opts.frDocNum) return `ocd-participation-window/federal/${opts.frDocNum}`;
  if (opts.regsObjectId) return `ocd-participation-window/federal/regs:${opts.regsObjectId}`;
  throw new Error("makeOcdId requires frDocNum or regsObjectId");
}

/**
 * The canonical unit of trust. A DERIVED, versioned projection over the append-only Observation log
 * (never a silently-mutated truth field). See docs/architecture/docketclock.md for the full design.
 */
export const ParticipationWindow = z.object({
  ocd_id: OcdId,

  // identifiers (all carried; frDocNum is primary join, docket_id/RIN are fallbacks)
  fr_document_number: z.string().nullable(),
  regs_document_id: z.string().nullable(),
  regs_object_id: z.string().nullable(),
  docket_id: z.array(z.string()).default([]),
  rin: z.string().nullable(),

  window_type: WindowType,

  // operative deadline — nullable + honest when confidence is conflicting/unknown
  resolved_close_utc: z.string().datetime().nullable(),
  resolved_close_display: z.string().nullable(), // verbatim legal language, e.g. "11:59 p.m. ET / 7:59 p.m. AK"

  // unreconciled per-source values, retained for transparency
  raw_fr_close_date: z.string().nullable(), // date-only
  raw_regs_close_datetime: z.string().nullable(), // ISO-8601 + offset

  confidence: Confidence,
  conflict_flags: z.array(ConflictFlag).default([]),
  status: WindowStatus,

  submission_url: z.string().url().nullable(),
  govinfo_url: z.string().url().nullable(), // legal-reliance backstop, embedded in EVERY response

  // opaque to core reconciliation — the extensibility seam. Watershed Watch writes huc_8:/huc_12: here.
  tags: z.array(z.string()).default([]),

  // provenance / versioning
  version: z.number().int().nonnegative(),
  current_observation_ids: z.array(z.string()).default([]),
  // change_history & provenance summary: TODO shape
});
export type ParticipationWindow = z.infer<typeof ParticipationWindow>;

// TODO: Observation (append-only log row), ConflictRecord (published proof feed), AccuracyRecord,
// observation_targets (M:N: one notice extends many dockets), and the REST/webhook payload schemas.
