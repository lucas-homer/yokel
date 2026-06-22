/**
 * @yokel/contracts — the shared seam between the DocketClock substrate and vertical wedges
 * (Watershed Watch). Verticals join on stable OCD-IDs, never internal UUIDs.
 *
 * ┌─────────────────────────────────────────────────────────────────────────────────────────────┐
 * │ FROZEN @ 0.8.0 (2026-06-18)                                                                    │
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
 * │       unique; classify rules reserve an OPTIONAL `ambiguous` marker (no LLM payload). SerializableRegex │
 * │       REJECTS the stateful g/y flags (evaluator .test()s without resetting lastIndex). [2026-06-18] │
 * │   • Adjudication (AMBIGUOUS-tail escalation, provider-NEUTRAL — no SDK/"gemini"/"anthropic" types): │
 * │       AdjudicationInput = discriminatedUnion("kind", [notice, chain]); BOTH carry rulebook_version │
 * │       (part of cache identity). AdjudicationVerdict is a SINGLE shared shape: categorical            │
 * │       AdjudicationClassification (affirm | reject | uncertain (abstain)) + free-text rationale, with │
 * │       NO numeric confidence/score field ANYWHERE (confidence is never LLM-scored; advisory only,     │
 * │       never deadline resolution). AdjudicationRecord = persisted cache/replay row (content_hash:     │
 * │       PayloadHash key over canonical(input); input; verdict; adjudicator_id PROVENANCE — NOT part of │
 * │       the key, first verdict per content_hash wins forever; created_at). [2026-06-18]               │
 * │                                                                                               │
 * │ INTENTIONALLY DEFERRED (contract pre-shaped or out of MVP scope — add when the builder lands): │
 * │   • Webhook payload schemas (HMAC-signed outbox events: notify_on kinds + delivery envelope) — │
 * │     Week 6-7, alongside GET /events undelivered visibility. (REST envelope landed @0.3.0.)      │
 * │   • RSS/Atom/ICS/CSV serialization shapes — v1.1.                                              │
 * │   • MCP tool I/O schemas — until a named AI-agent buyer commits.                               │
 * │   • Enrichment-API tag-namespace contract for THIRD-PARTY verticals — when Watershed Watch     │
 * │     commits (built-in agency/CFR enrichment writes into the opaque `tags` field as-is).        │
 * │   • The reconciliation confidence-EXPLANATION object internals (rules_fired / source_agreement / │
 * │     parse_path / staleness / conflict_ids). RuleBox's rule schema landed @0.6.0 and the AMBIGUOUS- │
 * │     tail Adjudication schemas landed @0.7.0; the explanation object consumes both but is a later slice. │
 * └─────────────────────────────────────────────────────────────────────────────────────────────┘
 *
 * REVISIONS
 *   • 0.8.0 (2026-06-18) — One additive ConflictFlag value: "llm_corroborated" (RuleBox/classifier
 *       Slice 3b). Slice 3b wires the LLM adjudicator into the cross-window (chain) reconcile engine:
 *       the deterministic engine CONSERVATIVELY under-links a pair that shares a docket, has valid
 *       amendment-after-original ordering, and is recent, but LACKS identity corroboration (no shared
 *       RIN AND no explicit doc-number reference) — that structurally-plausible-but-uncorroborated pair
 *       is escalated to the LLM, and an `affirm` PROMOTES it to a cross_window conflict. Such a link
 *       rests on LLM JUDGMENT of titles/dates, NOT a deterministic identity signal, so per "don't
 *       publish fake certainty" the /conflicts feed must distinguish it from a deterministically-
 *       corroborated link. "llm_corroborated" is a PROVENANCE / honesty marker (NOT a confidence score —
 *       confidence is NEVER LLM-scored; that invariant is untouched) that rides ALONGSIDE the link's
 *       type flag(s) (extension_chain_unresolved / correction_pending / withdrawn_vs_open / reopening),
 *       exactly as multi_target_notice rides alongside today, and signals LOWER certainty than a
 *       deterministically-corroborated link. APPENDED to the ConflictFlag enum — no existing value
 *       reordered/renamed/removed (stored conflict_flags arrays keep their spelling). It flows through
 *       ConflictRecord automatically (conflict_flags: z.array(ConflictFlag)); NO other schema changed.
 *   • 0.7.0 (2026-06-18) — Adjudication subsystem schemas (additive; no existing schema/enum/field changed).
 *       The AMBIGUOUS-tail escalation seam (RuleBox Slice 2): the deterministic RuleBox (0.6.0) classifies
 *       ~95%+ for free; a ClassifyRule's reserved `ambiguous` marker escalates the rest to a SINGLE LLM call
 *       resolved behind a provider-agnostic port (Gemini first) defined in the APP — these schemas are
 *       provider-NEUTRAL (no SDK types, no "gemini"/"anthropic" anywhere; the provider surfaces ONLY as the
 *       adjudicator_id provenance STRING). Three new exports: (1) AdjudicationInput = discriminatedUnion
 *       ("kind", [notice, chain]) — notice disambiguates a keyword notice-type match vs false-positive
 *       (flag_key + text); chain decides whether amendment B amends original A (A/B title + dates_text +
 *       publication_date + shared_docket/shared_rin/explicit_reference corroboration). BOTH members carry
 *       rulebook_version so a rulebook content change re-keys (re-adjudicates) rather than replaying a stale
 *       verdict. The input is LOAD-BEARING (it feeds the content hash) — minimal faithful signal set, not
 *       over-modeled. (2) AdjudicationVerdict = a SINGLE shared shape (not kind-discriminated): categorical
 *       AdjudicationClassification (affirm | reject | uncertain) + free-text rationale. NO numeric
 *       confidence/probability/score field exists ANYWHERE in these schemas — by design, enforced by absence
 *       (confidence is NEVER LLM-scored; the verdict is advisory classification only, never deadline
 *       resolution). `uncertain` is the explicit ABSTAIN value the null adapter / failed-or-timed-out call
 *       returns so the caller degrades to the deterministic conservative path. A stray model-emitted
 *       `confidence` is STRIPPED on parse (default Zod object behavior, matching every existing schema here),
 *       never stored. (3) AdjudicationRecord = the persisted cache/replay row: content_hash (reuses the
 *       existing PayloadHash 64-hex shape; sha256 of canonical(input), app-computed) is the CACHE KEY; plus
 *       input + verdict + adjudicator_id ("provider:model@rulebook_version" PROVENANCE, EXCLUDED from the key
 *       so the FIRST verdict per content_hash wins and is stable FOREVER — swapping providers changes only
 *       future uncached inputs, the replay-determinism guarantee) + created_at. Every existing schema is
 *       UNCHANGED; purely additive.
 *   • 0.6.0 (2026-06-18) — RuleBox rule schema (additive; no existing schema/enum changed). Adds the
 *       deterministic, VERSIONED rules-as-DATA rulebook the reconcile classifier (Slice 1b) will consume:
 *       RuleBox { version, rules[] }, Rule = discriminatedUnion("kind", [ClassifyRule, DenyRule]),
 *       the NoticeFlagKey enum (the four is_* notice flags, sans prefix), and SerializableRegex
 *       ({source,flags}) — a JSON-round-trippable regex whose source must COMPILE and whose flags are the
 *       legal JS subset MINUS the stateful g/y (the evaluator .test()s without resetting lastIndex, so g/y
 *       would break determinism — rejected at LOAD, not match time). ClassifyRule sets a NoticeFlagKey and reserves
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
  "llm_corroborated", // PROVENANCE/honesty marker (NOT a confidence score — confidence is NEVER LLM-scored): a cross_window (chain) link the LLM adjudicator AFFIRMED for a pair that passed the structural rules (shared docket + amendment-after-original ordering + recency) but had NO deterministic identity corroboration (no shared RIN AND no explicit doc-number reference). Signals LOWER certainty than a deterministically-corroborated link; rides ALONGSIDE the link's type flag(s) (extension_chain_unresolved / correction_pending / withdrawn_vs_open / reopening), as multi_target_notice does.
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
 *
 * The STATEFUL g/y flags are additionally rejected (second refine, path: flags): the evaluator calls
 * RegExp.prototype.test() without resetting lastIndex, so a g/y rule would go non-deterministic across
 * repeated .test() calls — the "PURE + deterministic" guarantee is enforced structurally, at LOAD time.
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
  )
  // The evaluator (apps/docketclock/src/rulebox) calls RegExp.prototype.test() WITHOUT resetting
  // lastIndex, so the stateful g/y flags would make a rule non-deterministic across repeated .test()
  // calls — breaking the "PURE + deterministic" guarantee. Reject them at LOAD, not at match time.
  // Runs after the compile check (which never throws here): a source that compiles with g/y still fails.
  .refine((r) => !r.flags.includes("g") && !r.flags.includes("y"), {
    message:
      "SerializableRegex must not use the stateful g/y flags — the evaluator calls .test() without resetting lastIndex, which would break determinism",
    path: ["flags"],
  });
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
// ADJUDICATION — the AMBIGUOUS-tail escalation contract (provider-NEUTRAL). The deterministic RuleBox
// (above) resolves ~95%+ of records for free; a ClassifyRule's reserved `ambiguous` marker means "this
// match is genuinely ambiguous — escalate to a SINGLE LLM call." A future provider (Google Gemini first,
// behind a provider-agnostic PORT defined in the app — NOT here) resolves ONLY the ambiguous tail (<5%
// of records, ~50 calls/day; docketclock.md). These schemas are the data crossing that seam.
//
// HARD INVARIANTS the shapes enforce STRUCTURALLY (docketclock.md confidence model):
//   • Confidence is NEVER LLM-scored. The verdict carries NO numeric confidence/probability/score field
//     of ANY kind — only a categorical `classification` + a free-text `rationale`. Enforced by absence.
//   • The LLM never touches deadline resolution: a verdict is ADVISORY classification only. It feeds the
//     deterministic engine's notice-flag / chain-link decision; it never sets resolved_close_utc.
//   • Verdicts are PERSISTED + replayed (an LLM call is non-deterministic; the system prizes deterministic
//     replay), keyed by a content_hash over the canonical input, with provenance recording which engine
//     produced each verdict. The FIRST verdict for a content_hash wins and is stable forever.
//
// Provider-neutral by construction: no SDK types, no "gemini"/"anthropic" in any schema. The provider is
// an app-level adapter detail surfaced ONLY as a provenance STRING (adjudicator_id), never as structure.
// ───────────────────────────────────────────────────────────────────────────────────────────────

/**
 * AdjudicationInput — what is sent to the adjudicator when a deterministic match is AMBIGUOUS, AND what
 * defines the cache identity (its canonical serialization is sha256'd into AdjudicationRecord.content_hash).
 * A discriminated union over the TWO escalation seams the RuleBox surfaces:
 *
 *   • "notice" — is a keyword match a TRUE notice-type signal or a keyword FALSE-POSITIVE? (The hot-path
 *     peer of the deterministic DenyRule / BLM 2023-27468 trap, for titles a deny rule can't settle.)
 *   • "chain"  — does amendment B genuinely amend original A? (The chain-classification escalation; the
 *     advisory peer of the deterministic chain pass.)
 *
 * BOTH members carry `rulebook_version` — the deterministic rulebook that PRODUCED the ambiguity. It is
 * part of the cache identity, so a rulebook content change naturally RE-ADJUDICATES (a new content_hash)
 * rather than replaying a verdict the old rules implied. This shape is LOAD-BEARING (it feeds the content
 * hash): favor stability over completeness — the minimal faithful signal set, deliberately NOT over-modeled.
 */
export const AdjudicationInput = z.discriminatedUnion("kind", [
  /**
   * notice seam — disambiguate a notice-type keyword match. Carries the text under question (the
   * haystack the keyword tripped in) and WHICH NoticeFlagKey the deterministic rule was about to set,
   * so the adjudicator answers a precise yes/no rather than re-classifying from scratch.
   */
  z.object({
    kind: z.literal("notice"),
    rulebook_version: z.string().min(1), // the rulebook that produced the ambiguity (part of cache identity)
    flag_key: NoticeFlagKey, // the notice flag the tripped keyword would set, if confirmed
    text: z.string(), // the haystack under question (title / DATES text the keyword matched in)
  }),
  /**
   * chain seam — decide whether amendment B genuinely amends original A. Carries the minimal faithful
   * signal set a human/LLM chain decision needs: each side's title + dates_text + publication_date, and
   * the three corroboration signals (shared docket? shared RIN? an explicit reference from B to A?).
   * NOT modeled: full payloads, observation ids, ocd_ids — none change the amends/doesn't-amend verdict,
   * and including them would churn the content hash without changing the decision.
   */
  z.object({
    kind: z.literal("chain"),
    rulebook_version: z.string().min(1), // the rulebook that produced the ambiguity (part of cache identity)
    // side A — the original notice
    a_title: z.string(),
    a_dates_text: z.string().nullable(),
    a_publication_date: z.string().nullable(), // date-only as published; not normalized
    // side B — the candidate amendment
    b_title: z.string(),
    b_dates_text: z.string().nullable(),
    b_publication_date: z.string().nullable(),
    // corroboration signals the chain decision weighs (deterministically computed by the app, passed in)
    shared_docket: z.boolean(), // A and B share a docket id
    shared_rin: z.boolean(), // A and B share a RIN
    explicit_reference: z.boolean(), // B's text explicitly references A (e.g. "amends 2025-02910")
  }),
]);
export type AdjudicationInput = z.infer<typeof AdjudicationInput>;

/**
 * AdjudicationClassification — the categorical verdict the adjudicator returns. Categorical, NEVER a
 * score — there is deliberately NO numeric confidence anywhere in this contract (confidence is never
 * LLM-scored; docketclock.md). `uncertain` is the explicit ABSTAIN value: the null adapter returns it,
 * and any failed/timed-out real call returns it, so the caller degrades to the deterministic conservative
 * path (treat as NOT-a-signal / NOT-a-chain) rather than acting on a fabricated answer.
 */
export const AdjudicationClassification = z.enum([
  "affirm", // the ambiguous signal is REAL: a true notice-type signal / B genuinely amends A
  "reject", // the ambiguous signal is a FALSE-POSITIVE: not a notice signal / B does not amend A
  "uncertain", // ABSTAIN — null adapter, or a failed/timed-out call; caller takes the conservative path
]);
export type AdjudicationClassification = z.infer<
  typeof AdjudicationClassification
>;

/**
 * AdjudicationVerdict — the provider-neutral RESULT. A SINGLE shared shape (NOT kind-discriminated): both
 * seams reduce to the same honest outcome — affirm/reject/uncertain + a rationale — and the per-seam
 * meaning of "affirm" lives in the INPUT's kind (already on the persisted record), so discriminating the
 * verdict by kind would only duplicate that with no new information. Simpler shape, same expressiveness.
 *
 * `classification` is categorical (see AdjudicationClassification). `rationale` is free text for the audit
 * trail (why the adjudicator decided this). There is NO numeric confidence/probability/score field, by
 * DESIGN: confidence is never LLM-scored — surfacing a model-emitted number would manufacture exactly the
 * fake certainty this product exists to refuse. A model that volunteers a "confidence: 0.9" has that field
 * STRIPPED on parse (default Zod object behavior, matching every other schema here), never stored.
 */
export const AdjudicationVerdict = z.object({
  classification: AdjudicationClassification,
  rationale: z.string(), // free-text audit trail; the ONLY explanatory field — no score accompanies it
});
export type AdjudicationVerdict = z.infer<typeof AdjudicationVerdict>;

/**
 * AdjudicationRecord — the PERSISTED cache row (audit + deterministic replay), provider-neutral.
 *
 * The CACHE KEY is the COMPOSITE (content_hash, adjudicator_id). content_hash is the sha256 of the
 * CANONICAL serialization of `input` (which includes rulebook_version); adjudicator_id is the engine that
 * produced the verdict (see below). Each adjudicator's verdict for a given input is cached and replayed
 * independently under its own id: same input + same adjudicator ⇒ replay the stored verdict instead of
 * calling the LLM. content_hash reuses PayloadHash (64-hex) — the app computes both key parts; the contract
 * only TYPES them. (App-side keying: apps/docketclock/migrations/0009_adjudications_per_adjudicator_key.sql.)
 *
 * adjudicator_id is both PROVENANCE and HALF THE KEY. It records WHICH engine produced the verdict as a
 * "provider:model@rulebook_version" string (e.g. "null:abstain@rulebox-2026-06-18" or
 * "gemini:gemini-2.5-flash@rulebox-2026-06-18"). Because it is part of the key, a non-deciding adapter's
 * verdict ("null:abstain@<rb>") lives under a DIFFERENT key than a real adjudicator's verdict
 * ("gemini:...@<rb>") for the same input, so it can NEVER shadow it — the bug that motivated the per-
 * adjudicator key (a null:abstain `uncertain` shadowing Gemini and silently suppressing chain links).
 * Replay determinism is therefore PER-ADJUDICATOR, not global: a provider/model swap OR a rulebook change
 * re-adjudicates (new adjudicator_id and/or content_hash), which is correct — a different engine or
 * rulebook is a genuinely different question.
 */
export const AdjudicationRecord = z.object({
  content_hash: PayloadHash, // sha256 of canonical(input) — key part 1 (app-computed; includes rulebook_version)
  input: AdjudicationInput, // the question that was adjudicated (the hashed payload)
  verdict: AdjudicationVerdict, // the advisory result
  adjudicator_id: z.string().min(1), // PROVENANCE + key part 2: "provider:model@rulebook_version" (cache key = (content_hash, adjudicator_id))
  created_at: z.string().datetime(), // when this verdict was first persisted (ISO-8601)
});
export type AdjudicationRecord = z.infer<typeof AdjudicationRecord>;

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
