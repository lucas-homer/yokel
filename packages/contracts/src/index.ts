/**
 * @yokel/contracts — the shared seam between the DocketClock substrate and vertical wedges
 * (Watershed Watch). Verticals join on stable OCD-IDs, never internal UUIDs.
 *
 * ┌─────────────────────────────────────────────────────────────────────────────────────────────┐
 * │ FROZEN @ 0.6.0 (2026-06-18)                                                                    │
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
 * │   • REST response envelope: DISCLAIMER + API_VERSION constants, EnvelopeMeta, Pagination, and  │
 * │       the apiItemEnvelope / apiListEnvelope factories (the single source for response shape so  │
 * │       the published OpenAPI and actual responses can never diverge).                            │
 * │   • Refinements that make illegal states unrepresentable (see each schema):                    │
 * │       - high | medium | low | stale  =>  resolved_close_utc MUST be non-null (assert a close).  │
 * │       - unknown  =>  resolved_close_utc MUST be null (both deadline fields missing; never       │
 * │         coerce a guess). conflicting MAY be null (engine abstains) but is not force-nulled.     │
 * │       - tz_normalization_only is an INFORMATIONAL marker: may ride with HIGH, never with        │
 * │         'conflicting' (the load-bearing FR-2018-27875 fix, expressed structurally).             │
 * │   • tags is string[] and OPAQUE to core — HUC/vertical fields NEVER enter the canonical object.│
 * │   • RuleBox: the deterministic, VERSIONED rules-as-DATA rulebook (RuleBox + Rule discriminated  │
 * │       union of ClassifyRule | DenyRule; NoticeFlagKey enum; SerializableRegex). Expresses today's │
 * │       two regex stopgaps as data (notice-flags 4 classify regexes; chain.ts DENY_PATTERNS deny    │
 * │       regexes). Regexes are DATA ({source,flags}) that must COMPILE at load; rule ids are kebab + │
 * │       unique; classify rules reserve an OPTIONAL `ambiguous` marker (no LLM payload). [2026-06-18] │
 * │                                                                                               │
 * │ INTENTIONALLY DEFERRED (contract pre-shaped or out of MVP scope — add when the builder lands): │
 * │   • Webhook payload schemas (HMAC-signed outbox events: notify_on kinds + delivery envelope) — │
 * │     Week 6-7, alongside GET /events undelivered visibility. (REST envelope landed @0.3.0.)      │
 * │   • RSS/Atom/ICS/CSV serialization shapes — v1.1.                                              │
 * │   • MCP tool I/O schemas — until a named AI-agent buyer commits.                               │
 * │   • Enrichment-API tag-namespace contract for THIRD-PARTY verticals — when Watershed Watch     │
 * │     commits (built-in agency/CFR enrichment writes into the opaque `tags` field as-is).        │
 * │   • The reconciliation confidence-EXPLANATION object internals (rules_fired / source_agreement / │
 * │     parse_path / staleness / conflict_ids) and the AMBIGUOUS-tail Adjudicator schema (provider   │
 * │     port + verdict). RuleBox's rule schema landed @0.6.0; these consume it but are a later slice. │
 * └─────────────────────────────────────────────────────────────────────────────────────────────┘
 *
 * REVISIONS
 *   • 0.6.0 (2026-06-18) — RuleBox rule schema (additive; no existing schema/enum changed). Adds the
 *       deterministic, VERSIONED rules-as-DATA rulebook the reconcile classifier (Slice 1b) will consume:
 *       RuleBox { version, rules[] }, Rule = discriminatedUnion("kind", [ClassifyRule, DenyRule]),
 *       the NoticeFlagKey enum (the four is_* notice flags, sans prefix), and SerializableRegex
 *       ({source,flags}) — a JSON-round-trippable regex whose source must COMPILE and whose flags are the
 *       legal JS subset, validated at LOAD not match time. ClassifyRule sets a NoticeFlagKey and reserves
 *       an OPTIONAL `ambiguous` boolean (escalation marker; NO LLM/adjudication payload — that's deferred);
 *       DenyRule suppresses an amendment signal (the BLM 2023-27468 land-withdrawal trap), no target flag.
 *       Both carry a kebab `id` (unique within a box, superRefine-enforced) + a `rationale` audit string.
 *       This encodes today's two regex stopgaps (notice-flags.ts 4 RE_* + chain.ts DENY_PATTERNS) as data.
 *       Observation/ConflictFlag/ConflictRecord and every existing schema are UNCHANGED; purely additive.
 *   • 0.5.0 (2026-06-17) — `reopening` becomes a first-class notice classification (additive; un-defers
 *       O4 on #31). Two additions, both additive: (a) a new ConflictFlag member "reopening" — a
 *       previously-CLOSED comment period RE-OPENED (a gap + fresh reliance window), the legally distinct
 *       peer of extension_chain_unresolved (which moves a STILL-OPEN deadline later, continuous); and (b)
 *       a 4th required boolean on Observation, is_reopening, a true peer of is_extension/is_correction/
 *       is_withdrawal. WindowStatus already carried `reopened`, so this only aligns the conflict +
 *       observation vocabulary with a distinction the window level already commits to. No existing field
 *       changed type/nullability and no enum member was reordered/renamed, so a legacy consumer still
 *       parses; the only new producer obligation is supplying is_reopening (wired in the same PR's
 *       notice-flags split + backfill, outside contracts). Supersedes the 0.4.0 note that deferred a chain
 *       reopening flag — O4 is no longer deferred.
 *   • 0.4.0 (2026-06-17) — Cross-window (chain) conflict support on ConflictRecord (additive; for #31).
 *       Added three optional/defaulted fields to ConflictRecord so the ONE published /conflicts feed can
 *       also carry chain conflicts spanning TWO windows (an amendment's window vs the original's):
 *       conflict_scope ("cross_source" default | "cross_window"), ocd_id_b (side B's distinct window,
 *       null for cross_source), and govinfo_url_b (side B's govinfo anchor, null for cross_source). A
 *       superRefine pins the invariants — cross_window REQUIRES ocd_id_b present AND distinct from ocd_id;
 *       cross_source REQUIRES ocd_id_b null. Backward-compatible by defaults: a legacy row / current
 *       reconcile emit site that omits all three parses as cross_source with both B fields null (the
 *       original meaning), so NO existing field changed type/nullability and NO emit site needs edits.
 *       NO new ConflictFlag added at 0.4.0 (chain reopening flag was deferred — see O4 on #31; that
 *       deferral was lifted at 0.5.0, which adds the "reopening" flag). At 0.4.0 the existing flag
 *       vocabulary (extension_chain_unresolved / correction_pending / withdrawn_vs_open /
 *       multi_target_notice) already covered chain conflicts.
 *   • 0.3.0 (2026-06-16) — REST response envelope (additive; no existing schema/enum changed).
 *       Added the Delivery API read-surface (GET /windows, /windows/{ocd_id}, /conflicts) envelope:
 *       the DISCLAIMER + API_VERSION canonical constants, the EnvelopeMeta schema
 *       (disclaimer + api_version + request_id), the Pagination schema (limit/offset/total), and the
 *       apiItemEnvelope(data) / apiListEnvelope(item) factories that compose per-endpoint response
 *       schemas so the published OpenAPI spec and the actual responses share ONE definition. Every
 *       Observation/ParticipationWindow/ConflictRecord shape is unchanged; the "REST envelope" item
 *       moved OUT of INTENTIONALLY DEFERRED (webhook payloads remain deferred to Week 6-7).
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
  "tz_normalization_only", // same Eastern date, differ only in UTC — informational; may ride with HIGH, never CONFLICTING
  "extension_chain_unresolved",
  "correction_pending",
  "withdrawn_vs_open",
  "reopening", // a previously-CLOSED comment period was RE-OPENED (a fresh reliance window after a gap) — distinct from extension_chain_unresolved, which moves a STILL-OPEN deadline later (continuous)
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
  is_reopening: z.boolean(), // 4th notice-type flag, peer to the three above; a previously-CLOSED comment period re-opened (a gap + fresh reliance window), NOT an open-deadline extension

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
 *       'conflicting' — a same-Eastern-date / differ-only-in-UTC case is an INFORMATIONAL signal (it may
 *       ride with HIGH, never CONFLICTING), NOT a conflict. This is the FR-2018-27875 fatal-flaw fix
 *       expressed structurally.
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
    // (2) tz_normalization_only is an INFORMATIONAL signal — it may ride with HIGH (or MEDIUM) but can
    // never ride with a 'conflicting' verdict. A 1-UTC-day gap that resolves to the SAME Eastern date is
    // a normalization artifact, not a conflict; pairing it with CONFLICTING would re-introduce the exact
    // false-positive flood the Eastern-date rule exists to prevent (FR-2018-27875).
    if (
      w.confidence === "conflicting" &&
      w.conflict_flags.includes("tz_normalization_only")
    ) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["conflict_flags"],
        message:
          "tz_normalization_only is an informational signal (may ride with HIGH, never CONFLICTING) and must not co-occur with confidence 'conflicting' (FR-2018-27875 Eastern-date artifact, not a conflict).",
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
 * single-source competitor offers). Carries the two observations that disagree, the govinfo
 * legal-reliance anchor(s), the typed conflict_flags, and when it was detected.
 *
 * conflict_scope discriminates the TWO kinds of disagreement this one published shape carries:
 *   • "cross_source" (the original, default shape) — the two observations are on the SAME window
 *     (`ocd_id`) and disagree across SOURCES (FR vs Regs). `ocd_id_b` is null and `govinfo_url_b`
 *     is null because there is no "B window": both sides share `ocd_id`/`govinfo_url`. This is the
 *     only shape the reconcile engine emits today (FR↔Regs date mismatch / withdrawn-vs-open).
 *   • "cross_window" (#31 chain conflicts) — the two observations live on TWO DIFFERENT windows: an
 *     amendment notice (extension/correction/withdrawal) is a SEPARATE FR document that mints its
 *     OWN ocd_id, so the disagreement spans `ocd_id` (side A) and `ocd_id_b` (side B). Both sides are
 *     self-describing: each carries its own observation id, source, and govinfo anchor (`govinfo_url`
 *     for A, `govinfo_url_b` for B). Such conflicts are often SAME-SOURCE (both federal_register: the
 *     amendment doc vs the original doc), so source_a/source_b may be equal here.
 *
 * Back-compat by defaults: the three #31 fields are all optional/defaulted, so a legacy serialized
 * row (and every reconcile emit site today) that carries NEITHER ocd_id_b NOR conflict_scope parses
 * cleanly as { conflict_scope: "cross_source", ocd_id_b: null, govinfo_url_b: null } — i.e. exactly
 * the original cross-source meaning. No existing field changed type or nullability; this is additive.
 */
export const ConflictRecord = z
  .object({
    ocd_id: OcdId, // side A's window (the only window for cross_source)
    // the two disagreeing observations (by log id) + their source provenance
    observation_a_id: z.string(),
    observation_b_id: z.string(),
    source_a: ObservationSource,
    source_b: ObservationSource,
    conflict_flags: z.array(ConflictFlag).min(1), // a conflict record always names at least one flag
    govinfo_url: z.string().url().nullable(), // side A's legal-reliance backstop, embedded in the feed

    // ── #31 cross-window (chain) fields — additive, defaulted for back-compat ──────────────────────
    // conflict_scope: which kind of disagreement (see the doc block above). Defaults to "cross_source"
    // so legacy rows / current emit sites that omit it keep their original meaning.
    conflict_scope: z
      .enum(["cross_source", "cross_window"])
      .default("cross_source"),
    // ocd_id_b: side B's window — present ONLY for cross_window (the amendment's standalone window) and
    // null for cross_source (both sides share `ocd_id`). Enforced by the superRefine below.
    ocd_id_b: OcdId.nullable().default(null),
    // govinfo_url_b: side B's legal-reliance anchor — its own govinfo URL when B is a distinct window
    // (cross_window). Null for cross_source (there is no second window/anchor).
    govinfo_url_b: z.string().url().nullable().default(null),
    detected_at: z.string().datetime(),
  })
  .superRefine((c, ctx) => {
    // cross_window MUST name a second window, and it must be a DIFFERENT window than side A — otherwise
    // it is not a cross-WINDOW conflict at all (a chain conflict spans two ocd_ids by definition).
    if (c.conflict_scope === "cross_window") {
      if (c.ocd_id_b === null) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["ocd_id_b"],
          message:
            "conflict_scope 'cross_window' requires ocd_id_b (side B's distinct window); a chain conflict spans two windows.",
        });
      } else if (c.ocd_id_b === c.ocd_id) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["ocd_id_b"],
          message:
            "conflict_scope 'cross_window' requires ocd_id_b to differ from ocd_id (the two sides are distinct windows); use 'cross_source' for a same-window disagreement.",
        });
      }
    } else {
      // cross_source is single-window: there is no side-B window, so ocd_id_b MUST be null. (govinfo_url_b
      // is left free to be null by default; a non-null B anchor without a B window is meaningless but not
      // worth a hard error — the load-bearing invariant is the window identity, pinned via ocd_id_b.)
      if (c.ocd_id_b !== null) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["ocd_id_b"],
          message:
            "conflict_scope 'cross_source' is a single-window (FR↔Regs) disagreement; ocd_id_b must be null (use 'cross_window' for a chain conflict spanning two windows).",
        });
      }
    }
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

// ───────────────────────────────────────────────────────────────────────────────────────────────
// RULEBOX — the deterministic, VERSIONED rulebook (rules-as-DATA, Zod-validated) that does cheap
// keyword classification forever (docketclock.md: "JSON RuleBox + Zod"). A future LLM (Gemini, via a
// provider-agnostic port in a LATER slice) is consulted ONLY for the AMBIGUOUS tail (<5% of records)
// and NEVER touches confidence or deadline resolution. THIS schema is the data shape the deterministic
// evaluator (Slice 1b) consumes — no LLM/adjudication types live here (deferred to the Adjudicator slice).
//
// It expresses, as DATA, the two regex stopgaps in the codebase today:
//   • classify rules ⇐ apps/docketclock/src/sources/notice-flags.ts (4 keyword regexes → notice flags).
//   • deny rules     ⇐ apps/docketclock/src/reconcile/chain.ts DENY_PATTERNS (5 land-withdrawal regexes
//     that mark an amendment candidate's signal a keyword false-positive — the BLM 2023-27468 trap).
// ───────────────────────────────────────────────────────────────────────────────────────────────

/**
 * NoticeFlagKey — the FOUR notice-type classifications a classify rule may set, pinned to the exact
 * is_* notice-flag vocabulary already on Observation (is_extension/is_correction/is_withdrawal/
 * is_reopening). A classify rule names a NoticeFlagKey, not a free string, so a rulebook can never set
 * a flag the canonical object does not carry. The values are the bare key (e.g. "extension") — the
 * evaluator maps `extension` → the is_extension boolean; keeping the bare key avoids re-encoding the
 * `is_` prefix in data and keeps the enum aligned with the keyof the four flags one-to-one.
 */
export const NoticeFlagKey = z.enum([
  "extension",
  "correction",
  "withdrawal",
  "reopening",
]);
export type NoticeFlagKey = z.infer<typeof NoticeFlagKey>;

/**
 * SerializableRegex — a regex stored as DATA so a rulebook can live as JSON and round-trip (NOT a live
 * RegExp instance; z.instanceof(RegExp) would not survive serialization). `flags` is constrained to the
 * legal JS regex flag set, and the whole pattern is refined to COMPILE: an un-compilable source (or an
 * illegal flag combination) fails validation at LOAD time, not silently at match time. This is the
 * single trust boundary that guarantees the evaluator never calls `new RegExp` on data that throws.
 *
 * The legal-flag regex pins each char to the JS set (d,g,i,m,s,u,y) and forbids duplicates via the
 * negative-lookahead; `new RegExp` is the final authority (it also rejects e.g. `u`+`v` style clashes
 * and malformed sources), so the refine is the load-bearing check and the flag regex is the fast guard.
 */
export const SerializableRegex = z
  .object({
    source: z.string().min(1), // the regex body, e.g. "\\bextension\\b|\\bextend(?:ed|ing)?\\b"
    flags: z
      .string()
      .regex(
        /^(?!.*(.).*\1)[dgimsuy]*$/,
        "flags must be a subset of the legal JS regex flags (d,g,i,m,s,u,y) with no duplicates",
      )
      .default(""),
  })
  .refine(
    (r) => {
      try {
        new RegExp(r.source, r.flags);
        return true;
      } catch {
        return false;
      }
    },
    {
      message:
        "SerializableRegex.source must compile with the given flags (rejected at load, never deferred to match time)",
      path: ["source"],
    },
  );
export type SerializableRegex = z.infer<typeof SerializableRegex>;

/**
 * ClassifyRule — a keyword pattern that, when it matches a notice's text, SETS a notice-type flag.
 * Mirrors the 4 RE_* regexes in notice-flags.ts as data (one rule per flag, or many rules per flag).
 *
 * `ambiguous` (OPTIONAL, default false) is a RESERVED marker: a rule may flag its match as needing
 * escalation to the AMBIGUOUS-tail adjudicator (a later slice). It is intentionally a bare boolean and
 * carries NO LLM/adjudication payload — the Adjudicator schema (provider port, verdict, rules_fired
 * explanation) is deferred. A rulebook that omits it is the common case (today's 4 regexes are all
 * unambiguous), so it never changes existing behavior and the deterministic evaluator may ignore it.
 */
export const ClassifyRule = z.object({
  kind: z.literal("classify"),
  id: z
    .string()
    .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, "rule id must be kebab-case"),
  pattern: SerializableRegex,
  sets: NoticeFlagKey, // the notice flag this match sets (constrained to the four known flags)
  rationale: z.string().min(1), // audit-trail description (why this pattern, what it targets)
  ambiguous: z.boolean().default(false), // RESERVED escalation marker; no LLM payload in this slice
});
export type ClassifyRule = z.infer<typeof ClassifyRule>;

/**
 * DenyRule — a keyword pattern whose match marks an amendment candidate a KEYWORD FALSE-POSITIVE, so
 * its amendment signal is SUPPRESSED (the candidate is never linked). Mirrors chain.ts DENY_PATTERNS:
 * the BLM 2023-27468 "land-withdrawal extension" trap (a public-lands action, NOT a comment-period
 * action). A deny rule sets NO flag — it only suppresses — so it carries no `sets` target.
 */
export const DenyRule = z.object({
  kind: z.literal("deny"),
  id: z
    .string()
    .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, "rule id must be kebab-case"),
  pattern: SerializableRegex,
  rationale: z.string().min(1), // audit-trail description (why this is a false-positive vehicle)
});
export type DenyRule = z.infer<typeof DenyRule>;

/** Rule — the discriminated union the evaluator dispatches on (`kind`). */
export const Rule = z.discriminatedUnion("kind", [ClassifyRule, DenyRule]);
export type Rule = z.infer<typeof Rule>;

/**
 * RuleBox — a deterministic, VERSIONED rulebook: an ordered list of classify + deny rules.
 *
 * `version` is the RULEBOOK's OWN version string, INDEPENDENT of the @yokel/contracts package version —
 * it gets stamped into verdict provenance (rules_fired) in a later slice, so it must be a required,
 * human-meaningful, non-empty string (e.g. "rulebox-2026-06-18" or a semver). Rule `id`s are unique
 * across the box (a duplicate id would make a fired-rule reference ambiguous in the audit trail).
 */
export const RuleBox = z
  .object({
    version: z.string().min(1), // the rulebook's own version (NOT the package version)
    rules: z.array(Rule).default([]),
  })
  .superRefine((box, ctx) => {
    const seen = new Set<string>();
    for (let i = 0; i < box.rules.length; i++) {
      const rule = box.rules[i];
      if (rule === undefined) continue;
      const id = rule.id;
      if (seen.has(id)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["rules", i, "id"],
          message: `duplicate rule id "${id}" — rule ids must be unique within a RuleBox (fired-rule references must be unambiguous in the audit trail).`,
        });
      }
      seen.add(id);
    }
  });
export type RuleBox = z.infer<typeof RuleBox>;

// ───────────────────────────────────────────────────────────────────────────────────────────────
// REST RESPONSE ENVELOPE — the Delivery API read-surface contract (GET /windows, /windows/{ocd_id},
// /conflicts). docketclock.md: "Every response carries disclaimer + api_version + request_id."
// ───────────────────────────────────────────────────────────────────────────────────────────────

/**
 * DISCLAIMER — the canonical legal-reliance string every API response carries (in EnvelopeMeta).
 *
 * Why it exists: buyers carry deadline LIABILITY, and the Federal Register payloads we derive from are
 * an "Unofficial XML rendition — NOT legal notice" (see docketclock.md data-source gotchas). govinfo is
 * the legal-reliance backstop, so the disclaimer steers anyone about to rely on a deadline back to the
 * official sources (and the per-window govinfo_url) BEFORE acting. This is a product invariant, not
 * decoration — it must ride on every response, which is why it lives in the frozen contract, not the API.
 */
export const DISCLAIMER =
  "DocketClock data is derived from the Federal Register and Regulations.gov APIs and is provided for " +
  "informational purposes only — it is NOT legal notice. Verify all deadlines against the official " +
  "sources (govinfo.gov) before relying on them.";

/**
 * API_VERSION — the current public REST API MAJOR version. The REST path/version policy keys off this
 * (e.g. /v1/windows) and it is echoed in every EnvelopeMeta.api_version so a cached/forwarded response
 * always self-identifies its contract generation. Bump on a breaking response-shape change only.
 */
export const API_VERSION = "v1";

/**
 * EnvelopeMeta — the trio attached to EVERY Delivery API response (merged into each response object by
 * the envelope factories below). disclaimer is the legal-reliance line (see DISCLAIMER); api_version is
 * the public-API generation (see API_VERSION); request_id is a per-request UUID minted by the API on
 * each request for support/tracing/log-correlation (clients quote it in tickets). All three are always
 * present — like confidence/conflict_flags, the envelope never suppresses its own honesty signals.
 */
export const EnvelopeMeta = z.object({
  disclaimer: z.string(),
  api_version: z.string(),
  request_id: z.string(), // UUID set by the API per request — for support/tracing
});
export type EnvelopeMeta = z.infer<typeof EnvelopeMeta>;

/**
 * Pagination — the limit/offset/total block on list endpoints (GET /windows, /conflicts).
 *   • limit  — max items the caller asked for in this page (non-negative).
 *   • offset — how many items were skipped before this page (non-negative).
 *   • total  — total items matching the query across ALL pages (non-negative), so a client can compute
 *     remaining pages without walking them. All three are non-negative integers.
 */
export const Pagination = z.object({
  limit: z.number().int().nonnegative(),
  offset: z.number().int().nonnegative(),
  total: z.number().int().nonnegative(),
});
export type Pagination = z.infer<typeof Pagination>;

/**
 * apiItemEnvelope(dataSchema) — composes the single-resource response shape: { data } + EnvelopeMeta.
 * The API layer applies it per endpoint, e.g. apiItemEnvelope(ParticipationWindow) for
 * GET /windows/{ocd_id} (or an ocd_id + observations detail shape). A pure schema factory — no runtime
 * logic beyond composition — so the published OpenAPI and the actual response derive from ONE definition.
 */
export function apiItemEnvelope<T extends z.ZodTypeAny>(dataSchema: T) {
  return z.object({ data: dataSchema }).merge(EnvelopeMeta);
}

/**
 * apiListEnvelope(itemSchema) — composes the paginated list response shape:
 * { data: itemSchema[], pagination: Pagination } + EnvelopeMeta. Applied per endpoint, e.g.
 * apiListEnvelope(ParticipationWindow) for GET /windows and apiListEnvelope(ConflictRecord) for
 * GET /conflicts. A pure schema factory — composition only — so spec and responses can never diverge.
 */
export function apiListEnvelope<T extends z.ZodTypeAny>(itemSchema: T) {
  return z
    .object({ data: z.array(itemSchema), pagination: Pagination })
    .merge(EnvelopeMeta);
}
