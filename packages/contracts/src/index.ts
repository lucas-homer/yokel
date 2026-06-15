/**
 * @yokel/contracts — the shared seam between the DocketClock substrate and vertical wedges
 * (Watershed Watch). Verticals join on stable OCD-IDs, never internal UUIDs.
 *
 * ┌─────────────────────────────────────────────────────────────────────────────────────────────┐
 * │ FROZEN @ 0.2.1 (2026-06-15)                                                                    │
 * │                                                                                               │
 * │ LOCKED (builders may propose changes; the contract-keeper adjudicates — nobody else edits):   │
 * │   • Confidence / ConflictFlag / WindowType / WindowStatus enums.                              │
 * │   • OCD-ID namespace: ocd-participation-window/federal/{frDocNum}                             │
 * │       (…/federal/regs:{regsObjectId} fallback when the FR doc number is absent).               │
 * │       makeOcdId is the ONLY minting path; OcdId regex pins the federal scheme.                 │
 * │   • Observation (append-only log row) + ObservationTarget (M:N: one notice -> many windows).  │
 * │   • ParticipationWindow as a DERIVED, versioned projection over the Observation log, with      │
 * │       provenance summary + append-only change_history.                                         │
 * │   • ConflictRecord (published /conflicts proof feed) + AccuracyRecord (track-record metric).   │
 * │   • Refinements that make illegal states unrepresentable (see each schema):                    │
 * │       - high | medium | low | stale  =>  resolved_close_utc MUST be non-null (assert a close).  │
 * │       - unknown  =>  resolved_close_utc MUST be null (both deadline fields missing; never       │
 * │         coerce a guess). conflicting MAY be null (engine abstains) but is not force-nulled.     │
 * │       - tz_normalization_only is a MEDIUM signal; it must NOT co-occur with confidence         │
 * │         'conflicting' (the load-bearing FR-2018-27875 fix, expressed structurally).            │
 * │   • tags is string[] and OPAQUE to core — HUC/vertical fields NEVER enter the canonical object.│
 * │                                                                                               │
 * │ INTENTIONALLY DEFERRED (contract pre-shaped or out of MVP scope — add when the builder lands): │
 * │   • REST/webhook envelope payloads (disclaimer + api_version + request_id) — Week 6-7.         │
 * │   • RSS/Atom/ICS/CSV serialization shapes — v1.1.                                              │
 * │   • MCP tool I/O schemas — until a named AI-agent buyer commits.                               │
 * │   • Enrichment-API tag-namespace contract for THIRD-PARTY verticals — when Watershed Watch     │
 * │     commits (built-in agency/CFR enrichment writes into the opaque `tags` field as-is).        │
 * │   • The reconciliation RuleBox rule schema + explanation object internals.                     │
 * └─────────────────────────────────────────────────────────────────────────────────────────────┘
 *
 * REVISIONS
 *   • 0.2.1 (2026-06-15) — OcdId hardening (no schema-shape change; tightened validation only).
 *       The OcdId regex was narrowed from `…/federal/.+` to pin the final segment to the two legal
 *       shapes ({frDocNum} | regs:{regsObjectId}), forbidding slashes, embedded whitespace, and a
 *       trailing-newline tail so the public join key can't be structurally ambiguous. makeOcdId now
 *       self-validates via OcdId.parse, so the sole minting path can never emit a malformed id.
 *       Strictly more restrictive than 0.2.0; no field/enum added or removed.
 *
 * Canonical spec: docs/architecture/docketclock.md (field tables, confidence model, edge cases:
 * FR-2018-27875 tz artifact, BLM 2023-27468 deny-list, EPA 2025-02910 multi-target,
 * FR 2025-03547 null-end-date extension).
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

/** The three live data sources behind every Observation. Mirrulations/spicy-regs is OFFLINE-only and
 *  deliberately NOT a source enum member — it never produces a live observation. */
export const ObservationSource = z.enum([
  "federal_register",
  "regulations_gov",
  "govinfo",
]);
export type ObservationSource = z.infer<typeof ObservationSource>;

/**
 * Stable Open Civic Data identifier — the cross-system join key.
 * Federal scheme: ocd-participation-window/federal/{frDocNum}
 *   (or regs:{regsObjectId} when the FR document number is absent).
 * Generated once at first observation; NEVER changes across extensions.
 *
 * The final segment is pinned to the two legal shapes so the PUBLIC join key can never carry a slash
 * (path-traversal-shaped ids), embedded whitespace/newlines, or a trailing-newline tail — any of which
 * would let two "equal" ids fail to join. `.+` was too permissive; see test/contract.adversary.probe.ts (E).
 *   • {frDocNum}: alphanumeric, may contain dashes (e.g. 2018-27875, E9-12345). No slash/space.
 *   • regs:{regsObjectId}: the `regs:` prefix + alphanumerics.
 * `(?![\s\S])` is JS's airtight end-of-string anchor — unlike `$`, it also rejects a trailing "\n".
 */
export const OcdId = z
  .string()
  .regex(
    /^ocd-participation-window\/federal\/(?:regs:[A-Za-z0-9]+|[A-Za-z0-9][A-Za-z0-9-]*)(?![\s\S])/,
    "ocd_id must match ocd-participation-window/federal/{frDocNum|regs:regsObjectId} (no slashes/whitespace)",
  );
export type OcdId = z.infer<typeof OcdId>;

export function makeOcdId(opts: {
  frDocNum?: string;
  regsObjectId?: string;
}): OcdId {
  const raw = opts.frDocNum
    ? `ocd-participation-window/federal/${opts.frDocNum}`
    : opts.regsObjectId
      ? `ocd-participation-window/federal/regs:${opts.regsObjectId}`
      : null;
  if (raw === null)
    throw new Error("makeOcdId requires frDocNum or regsObjectId");
  // makeOcdId is the ONLY minting path, so validate here: a slash- or whitespace-bearing source id
  // must never mint a structurally-ambiguous public key. Throws (ZodError) on a malformed source id.
  return OcdId.parse(raw);
}

/** sha256 hex digest of a raw payload — the idempotency + tamper-evidence key on the log. */
export const PayloadHash = z
  .string()
  .regex(/^[a-f0-9]{64}$/, "payload_hash must be a sha256 hex digest");
export type PayloadHash = z.infer<typeof PayloadHash>;

/**
 * Observation — one append-only log row. The audit spine: full replay can re-derive every window and
 * conflict from observations alone. DB enforces append-only (BEFORE UPDATE/DELETE trigger); this schema
 * validates the shape at the boundary. Skipped on insert if payload_hash matches the latest for
 * (source, document_id).
 */
export const Observation = z.object({
  observation_id: z.string(), // immutable log row id (internal; NOT the public key)

  // OCD linkage — which window(s) this row feeds is expressed via observation_targets (M:N), but the
  // primary derived window is carried for the common 1:1 case + indexing.
  ocd_id: OcdId,

  source: ObservationSource,

  // source document identifiers as fetched
  fr_document_number: z.string().nullable(),
  regs_document_id: z.string().nullable(),
  regs_object_id: z.string().nullable(),

  payload_hash: PayloadHash, // sha256 of `raw`
  fetched_at: z.string().datetime(),
  parser_version: z.string(), // pins which parser produced the flags below

  // verbatim, legally-authoritative DATES text — never reformatted
  raw_dates_text: z.string().nullable(),

  // notice-type flags parsed at insert (regex + RuleBox deny-list; BLM 2023-27468 false-positive guard)
  is_extension: z.boolean(),
  is_correction: z.boolean(),
  is_withdrawal: z.boolean(),

  // the raw payload, retained intact for replay/transparency (JSONB at rest)
  raw: z.unknown(),
});
export type Observation = z.infer<typeof Observation>;

/**
 * observation_targets — the M:N join so ONE notice can update MANY windows. A single FR extension
 * notice (EPA 2025-02910) writes updates to N distinct windows; modeling this as a join (not a 1:1
 * fk) is what prevents the "second window silently goes stale" failure.
 */
export const ObservationTarget = z.object({
  observation_id: z.string(),
  ocd_id: OcdId, // a window this observation contributes to
});
export type ObservationTarget = z.infer<typeof ObservationTarget>;

/**
 * provenance — summarizes which observations agreed vs conflicted in the reconcile that produced the
 * current window version. A read-model summary over the log, not a source of truth.
 */
export const Provenance = z.object({
  agreeing_observation_ids: z.array(z.string()).default([]),
  conflicting_observation_ids: z.array(z.string()).default([]),
});
export type Provenance = z.infer<typeof Provenance>;

/**
 * change_history entry — one append-only record of a PRIOR resolved_close_utc and the observation refs
 * that justified the change. The window is a versioned projection; mutating the close date silently is
 * exactly what the trust model forbids, so superseded values live here forever.
 */
export const ChangeHistoryEntry = z.object({
  version: z.number().int().nonnegative(),
  resolved_close_utc: z.string().datetime().nullable(),
  observation_ids: z.array(z.string()).default([]),
  changed_at: z.string().datetime(),
});
export type ChangeHistoryEntry = z.infer<typeof ChangeHistoryEntry>;

/**
 * The canonical unit of trust. A DERIVED, versioned projection over the append-only Observation log
 * (never a silently-mutated truth field). See docs/architecture/docketclock.md for the full design.
 *
 * Two structural invariants are enforced below via superRefine:
 *   (1) confidence 'conflicting' | 'unknown' => resolved_close_utc may be null (never coerce a guess).
 *       (HIGH/MEDIUM/LOW/STALE keep close as-is; the engine only ever ABSTAINS, never invents.)
 *   (2) conflict_flags containing 'tz_normalization_only' must NOT co-occur with confidence
 *       'conflicting' — a same-Eastern-date / differ-only-in-UTC case is a MEDIUM signal, NOT a
 *       conflict. This is the FR-2018-27875 fatal-flaw fix expressed structurally.
 */
export const ParticipationWindow = z
  .object({
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
    provenance: Provenance,
    change_history: z.array(ChangeHistoryEntry).default([]),
  })
  .superRefine((w, ctx) => {
    // (2) tz_normalization_only is a MEDIUM signal — it can never ride with a 'conflicting' verdict.
    // A 1-UTC-day gap that resolves to the SAME Eastern date is a normalization artifact, not a
    // conflict; pairing it with CONFLICTING would re-introduce the exact false-positive flood the
    // Eastern-date rule exists to prevent (FR-2018-27875).
    if (
      w.confidence === "conflicting" &&
      w.conflict_flags.includes("tz_normalization_only")
    ) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["conflict_flags"],
        message:
          "tz_normalization_only is a MEDIUM signal and must not co-occur with confidence 'conflicting' (FR-2018-27875 Eastern-date artifact, not a conflict).",
      });
    }

    // (1) Don't publish fake certainty — FORWARD direction: HIGH/MEDIUM/LOW/STALE assert a real
    // operative close, so it must be present. CONFLICTING/UNKNOWN are the ONLY states permitted to
    // carry a null close — and they may (the engine abstains rather than guess).
    const mustHaveClose =
      w.confidence === "high" ||
      w.confidence === "medium" ||
      w.confidence === "low" ||
      w.confidence === "stale";
    if (mustHaveClose && w.resolved_close_utc === null) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["resolved_close_utc"],
        message:
          "resolved_close_utc may only be null when confidence is 'conflicting' or 'unknown'; other states assert an operative deadline.",
      });
    }

    // (1) REVERSE direction for UNKNOWN — the spec-mandated NULL: docketclock.md defines UNKNOWN as
    // "Both structured deadline fields missing; resolved_close_utc = NULL ... never coerced to a
    // guessed date." A window stamped with the lowest-confidence state must NOT also ship a concrete
    // date a downstream consumer would read and trust — that is the exact lie this product exists to
    // prevent. So UNKNOWN forces resolved_close_utc === null at the schema level. (CONFLICTING is
    // deliberately NOT force-nulled: the spec lets the engine abstain there, but a reconciled-yet-
    // disputed close may still be the operative legal value worth surfacing alongside the conflict.)
    if (w.confidence === "unknown" && w.resolved_close_utc !== null) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["resolved_close_utc"],
        message:
          "confidence 'unknown' means both structured deadline fields are missing; resolved_close_utc MUST be null (docketclock.md: never coerce a guess).",
      });
    }
  });
export type ParticipationWindow = z.infer<typeof ParticipationWindow>;

/**
 * ConflictRecord — a row in the PUBLISHED GET /conflicts proof feed (the credibility moat no
 * single-source competitor offers). Carries the two source observations that disagree, the govinfo
 * legal-reliance anchor, the typed conflict_flags, and when it was detected.
 */
export const ConflictRecord = z.object({
  ocd_id: OcdId,
  // the two disagreeing source observations (by log id) + their source provenance
  observation_a_id: z.string(),
  observation_b_id: z.string(),
  source_a: ObservationSource,
  source_b: ObservationSource,
  conflict_flags: z.array(ConflictFlag).min(1), // a conflict record always names at least one flag
  govinfo_url: z.string().url().nullable(), // legal-reliance backstop embedded in the feed
  detected_at: z.string().datetime(),
});
export type ConflictRecord = z.infer<typeof ConflictRecord>;

/**
 * AccuracyRecord — the post-close track-record metric (% of HIGH-confidence deadlines correct,
 * trailing 90d). Written by the verification worker after resolved_close_utc passes; every
 * was_correct=false becomes a labeled regression test.
 */
export const AccuracyRecord = z.object({
  ocd_id: OcdId,
  published_close: z.string().datetime().nullable(), // what we published (may be null if we abstained)
  actual_close: z.string().datetime().nullable(), // observed truth after follow-up
  published_confidence: Confidence,
  was_correct: z.boolean(),
  evaluated_at: z.string().datetime(),
});
export type AccuracyRecord = z.infer<typeof AccuracyRecord>;
