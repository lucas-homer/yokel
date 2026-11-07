/**
 * Phase 0 APP-LOCAL candidates. Freeze into @yokel/contracts only after the value gate.
 * No raw source payload crosses this boundary. Indivisible canonical values are rejected
 * when oversized, never shortened; only explicitly marked excerpts may be truncated.
 */
import { z } from "zod";
import {
  API_VERSION,
  ChangeHistoryEntry,
  Confidence,
  ConflictFlag,
  ConflictRecord,
  DISCLAIMER,
  HumanReviewVerdict,
  HumanReviewVerdictKind,
  HumanReviewVerdictReviewer,
  makeOcdId,
  Observation,
  ObservationFields,
  OcdId,
  Pagination,
  ParticipationWindow,
  PayloadHash,
  WindowStatus,
  WindowType,
} from "@yokel/contracts";

export const TOOL_SCHEMA_VERSION = "mcp-v1" as const;
export const Instant = z.string().datetime({ offset: true }).max(64);
export const CanonicalInstant = z.string().datetime().max(64);
export const Count = z.number().int().min(0).max(Number.MAX_SAFE_INTEGER);
export const ObservationId = z.string().min(1).max(256);
// Pin v1's federal release boundary independently of any future canonical state additions.
export const FederalOcdId = OcdId.refine(
  (id) =>
    id.length <= 256 &&
    /^ocd-participation-window\/federal\/(?:regs:[A-Za-z0-9]+|[A-Za-z0-9][A-Za-z0-9-]*)(?![\s\S])/.test(
      id,
    ),
  "Expected a federal OCD-ID of at most 256 characters",
);
export const Url = z.string().url().max(2048);
export const Warning = z.string().min(1).max(300);
export const ConflictFlags = z
  .array(ConflictFlag)
  .max(ConflictFlag.options.length);
export const AgencySlug = z
  .string()
  .min(1)
  .max(120)
  .regex(
    /^[a-z0-9]+(?:-[a-z0-9]+)*(?![\s\S])/,
    "Expected an exact FR agency slug",
  );
export const Identifier = z
  .string()
  .min(1)
  .max(256)
  .superRefine((id, ctx) => {
    if (FederalOcdId.safeParse(id).success) return;
    // Reject bare regs: handles and public-namespace paths. FR shorthand uses the
    // canonical minting validator for validation ONLY, never to rekey a stored row.
    if (!/^[A-Za-z0-9][A-Za-z0-9-]*(?![\s\S])/.test(id)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Expected a federal OCD-ID or FR document number",
      });
      return;
    }
    try {
      makeOcdId({ frDocNum: id });
    } catch {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Invalid FR document number",
      });
    }
  });
export const Page = z
  .object({
    limit: z.number().int().min(1).max(20).default(10),
    offset: z.number().int().min(0).max(1000).default(0),
  })
  .strict();
export const IdInput = z.object({ id: Identifier }).strict();
export const ListWindowsInput = Page.extend({
  agency: AgencySlug.optional(),
  docket_id: z.string().min(1).max(160).optional(),
  rin: z.string().min(1).max(80).optional(),
  keyword: z
    .string()
    .trim()
    .min(1)
    .max(200)
    // A search continuation must round-trip, and the query grammar has no escapes for these.
    .refine((value) => !/\p{Cc}|\p{Cs}/u.test(value), {
      message: "must not contain control characters",
    })
    .optional(),
  status: WindowStatus.optional(),
  confidence: Confidence.optional(),
  window_type: WindowType.default("comment"),
  closes_after: Instant.optional(),
  closes_before: Instant.optional(),
  close_mode: z.enum(["any", "known", "unknown"]).default("any"),
})
  .strict()
  .superRefine((input, ctx) => {
    if (
      input.closes_after &&
      input.closes_before &&
      Date.parse(input.closes_after) >= Date.parse(input.closes_before)
    ) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["closes_before"],
        message: "closes_after must precede closes_before (exclusive bounds)",
      });
    }
    if (
      input.close_mode === "unknown" &&
      (input.closes_after || input.closes_before)
    ) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["close_mode"],
        message: "unknown closes cannot be combined with closing bounds",
      });
    }
  });
export type ListWindowsInput = z.infer<typeof ListWindowsInput>;
export const SearchInput = z
  .object({ query: z.string().trim().min(1).max(500) })
  .strict();
export type SearchInput = z.infer<typeof SearchInput>;
export const FetchInput = IdInput;
export type FetchInput = z.infer<typeof FetchInput>;
export const ListConflictsInput = Page.extend({
  ocd_id: FederalOcdId.optional(),
}).strict();
export type ListConflictsInput = z.infer<typeof ListConflictsInput>;
export const ExplainWindowInput = Page.extend({
  id: Identifier,
  section: z
    .enum(["summary", "observations", "verdicts", "history", "references"])
    .default("summary"),
  expected_version: Count.optional(),
  evidence_as_of: Instant.optional(),
})
  .strict()
  .superRefine((input, ctx) => {
    if (
      input.offset > 0 &&
      (input.expected_version === undefined ||
        input.evidence_as_of === undefined)
    ) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Follow-up pages require expected_version and evidence_as_of",
      });
    }
    if (input.section === "summary" && input.offset !== 0) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["offset"],
        message: "The summary section has no offset pagination",
      });
    }
  });
export type ExplainWindowInput = z.infer<typeof ExplainWindowInput>;
export const SubmissionInfoInput = IdInput;
export type SubmissionInfoInput = z.infer<typeof SubmissionInfoInput>;

// Canonical EnvelopeMeta permits arbitrary strings. Candidates deliberately pin the
// actual constants instead of inheriting that looseness from the design sketch.
export const EnvelopeMeta = z
  .object({
    disclaimer: z.literal(DISCLAIMER),
    api_version: z.literal(API_VERSION),
    request_id: z.string().uuid(),
  })
  .strict();
export type EnvelopeMeta = z.infer<typeof EnvelopeMeta>;
export const Trust = z
  .object({ confidence: Confidence, conflict_flags: ConflictFlags })
  .strict();
export type Trust = z.infer<typeof Trust>;
export const DeliveryMeta = Trust.extend({
  tool_schema_version: z.literal(TOOL_SCHEMA_VERSION),
  read_at: Instant,
  confidence_scope: z.enum(["window", "collection_no_aggregate", "no_record"]),
  warnings: z.array(Warning).max(10),
})
  .strict()
  .superRefine((delivery, ctx) => {
    if (
      delivery.confidence_scope !== "window" &&
      delivery.confidence !== "unknown"
    ) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["confidence"],
        message: "Collections and missing records have no aggregate confidence",
      });
    }
    if (
      delivery.confidence_scope === "no_record" &&
      delivery.conflict_flags.length !== 0
    ) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["conflict_flags"],
        message: "No record has no conflict flags",
      });
    }
  });
export type DeliveryMeta = z.infer<typeof DeliveryMeta>;
export const Coverage = z
  .object({
    jurisdiction: z.literal("federal"),
    corpus: z.literal("stored_docketclock_windows"),
    completeness: z.literal("not_asserted"),
    metadata_missing_count: Count,
    unknown_close_count: Count,
    disputed_close_count: Count,
    unresolved_close_followup: z.boolean(),
  })
  .strict();
export type Coverage = z.infer<typeof Coverage>;

function excerptShape(max: number) {
  return z
    .object({
      text: z.string().max(max).nullable(),
      truncated: z.boolean(),
      original_characters: Count,
    })
    .strict();
}
function excerptInvariant(
  excerpt: {
    text: string | null;
    truncated: boolean;
    original_characters: number;
  },
  ctx: z.RefinementCtx,
) {
  const shown = excerpt.text?.length ?? 0;
  if (
    shown > excerpt.original_characters ||
    excerpt.truncated !== shown < excerpt.original_characters
  ) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: "Excerpt length and truncation must match original_characters",
    });
  }
}
export const Excerpt = excerptShape(2000).superRefine(excerptInvariant);
export type Excerpt = z.infer<typeof Excerpt>;
export const PageExcerpt = excerptShape(400).superRefine(excerptInvariant);
export type PageExcerpt = z.infer<typeof PageExcerpt>;
export function toPageExcerpt(text: string | null): PageExcerpt {
  return PageExcerpt.parse({
    text: text === null ? null : text.slice(0, 400),
    truncated: text !== null && text.length > 400,
    original_characters: text?.length ?? 0,
  });
}
export const EvidenceCounts = z
  .object({
    current: Count,
    agreeing: Count,
    conflicting: Count,
    history: Count,
  })
  .strict();
export type EvidenceCounts = z.infer<typeof EvidenceCounts>;

export const WindowSummary = z
  .object({
    ocd_id: FederalOcdId,
    fr_document_number: z.string().max(256).nullable(),
    regs_document_id: z.string().max(256).nullable(),
    regs_object_id: z.string().max(256).nullable(),
    docket_id: z.array(z.string().max(512)).max(100),
    rin: z.string().max(80).nullable(),
    window_type: WindowType,
    resolved_close_utc: CanonicalInstant.nullable(),
    resolved_close_display: z.string().max(2000).nullable(),
    raw_fr_close_date: z.string().max(256).nullable(),
    raw_regs_close_datetime: z.string().max(256).nullable(),
    confidence: Confidence,
    conflict_flags: ConflictFlags,
    status: WindowStatus,
    submission_url: Url.nullable(),
    govinfo_url: Url.nullable(),
    tags: z.array(z.string().max(256)).max(100),
    version: Count,
    title: PageExcerpt,
    agency_slugs: z.array(AgencySlug).max(100),
    metadata_observation_ids: z.array(ObservationId).max(2),
    evidence_counts: EvidenceCounts,
  })
  .strict()
  .superRefine((window, ctx) => {
    // Run the authoritative refinements, without unwrapping ZodEffects. Omitted
    // evidence fields carry no close/trust semantics. This also picks up future
    // canonical refinements instead of silently diverging from the keeper's schema.
    const canonical = ParticipationWindow.safeParse({
      ...window,
      current_observation_ids: [],
      provenance: {
        agreeing_observation_ids: [],
        conflicting_observation_ids: [],
      },
      change_history: [],
    });
    if (!canonical.success) {
      for (const issue of canonical.error.issues)
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: issue.path,
          message: issue.message,
        });
    }
  });
export type WindowSummary = z.infer<typeof WindowSummary>;
export interface WindowMetadata {
  title: string | null;
  agencySlugs: string[];
  observationIds: string[];
}
export function toWindowSummary(
  input: unknown,
  metadata: WindowMetadata,
): WindowSummary {
  const window = ParticipationWindow.parse(input); // Full validation BEFORE removing evidence.
  const { current_observation_ids, provenance, change_history, ...fields } =
    window;
  return WindowSummary.parse({
    ...fields,
    title: toPageExcerpt(metadata.title),
    agency_slugs: metadata.agencySlugs,
    metadata_observation_ids: metadata.observationIds,
    evidence_counts: {
      current: current_observation_ids.length,
      agreeing: provenance.agreeing_observation_ids.length,
      conflicting: provenance.conflicting_observation_ids.length,
      history: change_history.length,
    },
  });
}

export const EvidenceRelationship = z.enum([
  "primary",
  "target",
  "current",
  "agreeing",
  "conflicting",
  "history",
  "conflict_side",
]);
export type EvidenceRelationship = z.infer<typeof EvidenceRelationship>;
export const EvidenceSummary = z
  .object({
    observation_id: ObservationId,
    ocd_id: FederalOcdId,
    source: ObservationFields.shape.source,
    payload_hash: PayloadHash,
    fetched_at: ObservationFields.shape.fetched_at.max(64),
    parser_version: ObservationFields.shape.parser_version.refine(
      (version) => version.length <= 120,
      "parser_version exceeds 120 characters",
    ),
    raw_dates_excerpt: PageExcerpt,
    source_url: Url.nullable(),
    relationship: z.array(EvidenceRelationship).min(1).max(7),
  })
  .strict();
export type EvidenceSummary = z.infer<typeof EvidenceSummary>;
export function toEvidenceSummary(
  input: unknown,
  metadata: { sourceUrl: string | null; relationship: EvidenceRelationship[] },
): EvidenceSummary {
  const observation = Observation.parse(input);
  return EvidenceSummary.parse({
    observation_id: observation.observation_id,
    ocd_id: observation.ocd_id,
    source: observation.source,
    payload_hash: observation.payload_hash,
    fetched_at: observation.fetched_at,
    parser_version: observation.parser_version,
    raw_dates_excerpt: toPageExcerpt(observation.raw_dates_text),
    source_url: metadata.sourceUrl,
    relationship: metadata.relationship,
  });
}
export const MissingEvidence = z
  .object({
    missing: z.literal(true),
    observation_id: ObservationId,
    reason: z.enum(["not_found", "unreadable"]),
  })
  .strict();
export type MissingEvidence = z.infer<typeof MissingEvidence>;
export const EvidenceResult = z.union([EvidenceSummary, MissingEvidence]);
export type EvidenceResult = z.infer<typeof EvidenceResult>;
export const Honoring = z.enum([
  "honored",
  "superseded",
  "not_honored",
  "unknown",
]);
export type Honoring = z.infer<typeof Honoring>;
export const VerdictEffect = z.enum(["derives", "parked", "none", "unknown"]);
export type VerdictEffect = z.infer<typeof VerdictEffect>;
export const VerdictSummary = z
  .object({
    observation_id: ObservationId,
    payload_hash: PayloadHash,
    fetched_at: ObservationFields.shape.fetched_at.max(64),
    kind: HumanReviewVerdictKind,
    pinned_close_date: z.string().date().optional(),
    reviewer: HumanReviewVerdictReviewer,
    note: PageExcerpt,
    redacted: z.boolean(),
    operator: z.string().min(1).max(120).nullable(),
    operator_redacted: z.boolean(),
    reviewed_payload_hash_count: Count.refine(
      (count) => count >= 1,
      "A verdict requires reviewed hashes",
    ),
    honoring: Honoring,
    effect: VerdictEffect,
  })
  .strict()
  .superRefine((verdict, ctx) => {
    if (
      (verdict.kind === "pin_close") !==
      (verdict.pinned_close_date !== undefined)
    ) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["pinned_close_date"],
        message: "Only pin_close requires and permits pinned_close_date",
      });
    }
    const expected =
      verdict.honoring === "honored"
        ? verdict.kind === "escalate"
          ? "parked"
          : "derives"
        : verdict.honoring === "unknown"
          ? "unknown"
          : "none";
    if (verdict.effect !== expected)
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["effect"],
        message: "Verdict effect must match honoring and kind",
      });
    if (verdict.operator_redacted !== (verdict.operator === null))
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["operator"],
        message:
          "Redacted executor must be null; public executors require an approved alias",
      });
    if (verdict.redacted && verdict.note.text !== null)
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["note"],
        message: "Redacted notes must not expose note text",
      });
    if (!verdict.redacted && !verdict.note.text?.trim())
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["note"],
        message: "Unredacted verdict note must be nonempty",
      });
  });
export type VerdictSummary = z.infer<typeof VerdictSummary>;
/** Executor and notes default to redaction. A caller may supply ONLY an approved public alias. */
export function toVerdictSummary(
  input: unknown,
  options: {
    honoring?: Honoring;
    operatorAlias?: string;
    redactNote?: boolean;
  } = {},
): VerdictSummary {
  const observation = Observation.parse(input);
  if (observation.source !== "human_review")
    throw new Error("Verdict summary requires a human_review observation");
  const verdict = HumanReviewVerdict.parse(observation.raw);
  const honoring = options.honoring ?? "unknown";
  const redacted = options.redactNote ?? true;
  return VerdictSummary.parse({
    observation_id: observation.observation_id,
    payload_hash: observation.payload_hash,
    fetched_at: observation.fetched_at,
    kind: verdict.kind,
    ...(verdict.pinned_close_date === undefined
      ? {}
      : { pinned_close_date: verdict.pinned_close_date }),
    reviewer: verdict.reviewer,
    note: redacted
      ? {
          text: null,
          truncated: true,
          original_characters: verdict.note.length,
        }
      : toPageExcerpt(verdict.note),
    redacted,
    operator: options.operatorAlias ?? null,
    operator_redacted: options.operatorAlias === undefined,
    reviewed_payload_hash_count: verdict.reviewed_payload_hashes.length,
    honoring,
    effect:
      honoring === "honored"
        ? verdict.kind === "escalate"
          ? "parked"
          : "derives"
        : honoring === "unknown"
          ? "unknown"
          : "none",
  });
}

// Bound existing canonical records without removing their refinements.
export const BoundedConflictRecord = ConflictRecord.superRefine(
  (record, ctx) => {
    const bounds = z
      .object({
        ocd_id: FederalOcdId,
        ocd_id_b: FederalOcdId.nullable(),
        observation_a_id: ObservationId,
        observation_b_id: ObservationId,
        conflict_flags: ConflictFlags,
        govinfo_url: Url.nullable(),
        govinfo_url_b: Url.nullable(),
        detected_at: CanonicalInstant,
      })
      .safeParse(record);
    if (!bounds.success)
      for (const issue of bounds.error.issues)
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: issue.path,
          message: issue.message,
        });
  },
);
export const ConflictEvidence = z
  .object({
    record: BoundedConflictRecord,
    side_a: WindowSummary,
    side_b: WindowSummary.nullable(),
    evidence_a: EvidenceResult,
    evidence_b: EvidenceResult,
  })
  .strict()
  .superRefine((conflict, ctx) => {
    const { record } = conflict;
    if (conflict.side_a.ocd_id !== record.ocd_id)
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["side_a"],
        message: "Side A must match the conflict window",
      });
    if (
      record.conflict_scope === "cross_window"
        ? conflict.side_b?.ocd_id !== record.ocd_id_b
        : conflict.side_b !== null
    ) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["side_b"],
        message:
          "Cross-window conflicts require the distinct matching side B; cross-source conflicts require null",
      });
    }
    for (const side of ["a", "b"] as const) {
      const evidence = side === "a" ? conflict.evidence_a : conflict.evidence_b;
      const id =
        side === "a" ? record.observation_a_id : record.observation_b_id;
      const source = side === "a" ? record.source_a : record.source_b;
      // Observation primary OCD-ID can differ for a multi-target association. Do
      // not manufacture equality with the window's OCD-ID here.
      if (
        evidence.observation_id !== id ||
        (!("missing" in evidence) && evidence.source !== source)
      ) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: [`evidence_${side}`],
          message: "Evidence must match its recorded observation ID and source",
        });
      }
    }
  });
export type ConflictEvidence = z.infer<typeof ConflictEvidence>;
export const ProvenanceCounts = z
  .object({ agreeing: Count, conflicting: Count })
  .strict();
export type ProvenanceCounts = z.infer<typeof ProvenanceCounts>;
export const SourceCloseValues = z
  .object({
    raw_fr_close_date: z.string().max(256).nullable(),
    raw_regs_close_datetime: z.string().max(256).nullable(),
  })
  .strict();
export type SourceCloseValues = z.infer<typeof SourceCloseValues>;
export const ExplainSummary = z
  .object({
    window: WindowSummary,
    source_close_values: SourceCloseValues,
    provenance_counts: ProvenanceCounts,
    honored_verdict: VerdictSummary.nullable(),
    honoring_as_of: Instant,
    derived_at: Instant.nullable(),
    reconciler_version: z.string().min(1).max(120).nullable(),
    projection_alignment: z.enum(["confirmed", "unknown"]),
    causal_trace: z.literal("not_recorded"),
    explanation_limits: z.array(Warning).max(10),
  })
  .strict()
  .superRefine((summary, ctx) => {
    if (
      summary.honored_verdict !== null &&
      summary.honored_verdict.honoring !== "honored"
    )
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["honored_verdict"],
        message: "honored_verdict must be honored or null",
      });
    if (
      summary.projection_alignment === "confirmed" &&
      (summary.derived_at === null || summary.reconciler_version === null)
    )
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["projection_alignment"],
        message: "Confirmed alignment requires stored derivation stamps",
      });
    if (summary.projection_alignment === "confirmed") {
      const verdict = summary.honored_verdict;
      const expectedFlag =
        verdict !== null && verdict.kind !== "escalate"
          ? verdict.reviewer === "human"
            ? "human_resolved"
            : "agent_resolved"
          : null;
      const human = summary.window.conflict_flags.includes("human_resolved");
      const agent = summary.window.conflict_flags.includes("agent_resolved");
      if (
        human !== (expectedFlag === "human_resolved") ||
        agent !== (expectedFlag === "agent_resolved") ||
        (verdict !== null &&
          summary.derived_at !== null &&
          Date.parse(verdict.fetched_at) > Date.parse(summary.derived_at))
      ) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["projection_alignment"],
          message:
            "Confirmed overlay alignment requires matching authority markers and a sufficiently recent derivation",
        });
      }
    }
    if (
      summary.source_close_values.raw_fr_close_date !==
        summary.window.raw_fr_close_date ||
      summary.source_close_values.raw_regs_close_datetime !==
        summary.window.raw_regs_close_datetime ||
      summary.provenance_counts.agreeing !==
        summary.window.evidence_counts.agreeing ||
      summary.provenance_counts.conflicting !==
        summary.window.evidence_counts.conflicting
    ) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message:
          "Source values and provenance counts must preserve the stored window",
      });
    }
  });
export type ExplainSummary = z.infer<typeof ExplainSummary>;
export const Reference = z
  .object({
    kind: z.enum(["current", "agreeing", "conflicting", "reviewed_hash"]),
    observation_id: ObservationId.nullable(),
    payload_hash: PayloadHash.nullable(),
    verdict_observation_id: ObservationId.nullable(),
  })
  .strict()
  .superRefine((reference, ctx) => {
    const valid =
      reference.kind === "reviewed_hash"
        ? reference.observation_id === null &&
          reference.payload_hash !== null &&
          reference.verdict_observation_id !== null
        : reference.observation_id !== null &&
          reference.payload_hash === null &&
          reference.verdict_observation_id === null;
    if (!valid)
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message:
          "Observation references require only observation_id; reviewed hashes require payload_hash and verdict_observation_id",
      });
  });
export type Reference = z.infer<typeof Reference>;
export const BoundedHistoryEntry = ChangeHistoryEntry.extend({
  version: Count,
  observation_ids: z.array(ObservationId).max(100),
  resolved_close_utc: CanonicalInstant.nullable(),
  changed_at: CanonicalInstant,
}).strict();
export type BoundedHistoryEntry = z.infer<typeof BoundedHistoryEntry>;
export const BoundedPagination = Pagination.extend({
  limit: z.number().int().min(1).max(20),
  offset: z.number().int().min(0).max(1000),
  total: Count,
}).strict();
export type BoundedPagination = z.infer<typeof BoundedPagination>;
export const NextOffset = z.number().int().min(0).max(1000).nullable();
function pageInvariant(
  page: {
    pagination: z.infer<typeof BoundedPagination>;
    next_offset: number | null;
  },
  count: number,
  ctx: z.RefinementCtx,
) {
  const { limit, offset, total } = page.pagination;
  if (count > limit || offset + count > Math.max(total, offset))
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["pagination"],
      message: "Returned count must fit limit and total",
    });
  const next = offset + count;
  const expected = next < total && next <= 1000 ? next : null;
  if ((count === 0 && offset < total) || page.next_offset !== expected)
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["next_offset"],
      message:
        "Pagination must advance by returned count; empty partial pages are forbidden",
    });
}
const pagedFields = {
  window: WindowSummary,
  pagination: BoundedPagination,
  next_offset: NextOffset,
};
export const ExplainSection = z
  .discriminatedUnion("section", [
    z
      .object({
        section: z.literal("summary"),
        window: WindowSummary,
        summary: ExplainSummary,
      })
      .strict(),
    z
      .object({
        section: z.literal("observations"),
        ...pagedFields,
        items: z.array(EvidenceSummary).max(20),
      })
      .strict(),
    z
      .object({
        section: z.literal("verdicts"),
        ...pagedFields,
        items: z.array(VerdictSummary).max(20),
      })
      .strict(),
    z
      .object({
        section: z.literal("history"),
        ...pagedFields,
        items: z.array(BoundedHistoryEntry).max(20),
      })
      .strict(),
    z
      .object({
        section: z.literal("references"),
        ...pagedFields,
        items: z.array(Reference).max(20),
      })
      .strict(),
  ])
  .superRefine((section, ctx) => {
    if (section.section === "summary") {
      if (
        JSON.stringify(section.window) !==
        JSON.stringify(section.summary.window)
      )
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["summary", "window"],
          message: "Summary must describe the same window and version",
        });
    } else pageInvariant(section, section.items.length, ctx);
  });
export type ExplainSection = z.infer<typeof ExplainSection>;
export const SubmissionInfo = z
  .object({
    window: WindowSummary,
    submission_url: Url.nullable(),
    govinfo_url: Url.nullable(),
    availability: z.enum(["stored_link", "unavailable"]),
    channel_details: z.literal("not_modeled"),
    checked_live: z.literal(false),
  })
  .strict()
  .superRefine((info, ctx) => {
    if (
      info.submission_url !== info.window.submission_url ||
      info.govinfo_url !== info.window.govinfo_url ||
      (info.availability === "stored_link") !== (info.submission_url !== null)
    )
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Availability and links must preserve the stored window",
      });
  });
export type SubmissionInfo = z.infer<typeof SubmissionInfo>;

function sameTrust(delivery: Trust, window: Trust): boolean {
  return (
    delivery.confidence === window.confidence &&
    JSON.stringify(delivery.conflict_flags) ===
      JSON.stringify(window.conflict_flags)
  );
}
function windowDelivery(
  delivery: DeliveryMeta,
  window: WindowSummary,
  ctx: z.RefinementCtx,
) {
  if (delivery.confidence_scope !== "window" || !sameTrust(delivery, window))
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["delivery"],
      message: "Window delivery must preserve confidence and flags",
    });
}
function collectionDelivery(
  delivery: DeliveryMeta,
  items: Trust[],
  ctx: z.RefinementCtx,
) {
  const flags = new Set(items.flatMap((item) => item.conflict_flags));
  if (
    delivery.confidence_scope !== "collection_no_aggregate" ||
    delivery.confidence !== "unknown" ||
    flags.size !== new Set(delivery.conflict_flags).size ||
    delivery.conflict_flags.some((flag) => !flags.has(flag))
  )
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["delivery"],
      message:
        "Collection delivery has unknown confidence and the union of returned flags",
    });
}
export const McpToolErrorCode = z.enum([
  "invalid_input",
  "not_found",
  "ambiguous_identifier",
  "unsupported_filter",
  "stale_read",
  "result_too_large",
  "evidence_unavailable",
  "citation_unavailable",
  "rate_limited",
  "temporarily_unavailable",
  "internal_error",
]);
export type McpToolErrorCode = z.infer<typeof McpToolErrorCode>;
export const McpToolError = EnvelopeMeta.extend({
  ...Trust.shape,
  error: z
    .object({
      code: McpToolErrorCode,
      message: z.string().min(1).max(500),
      retryable: z.boolean(),
      retry_after_seconds: z.number().int().min(0).max(86400).optional(),
      candidate_ids: z.array(FederalOcdId).min(2).max(20).optional(),
    })
    .strict(),
  confidence_scope: z.enum(["no_record", "window"]),
  window: WindowSummary.optional(),
})
  .strict()
  .superRefine((error, ctx) => {
    if (error.confidence_scope === "no_record") {
      if (
        error.window !== undefined ||
        error.confidence !== "unknown" ||
        error.conflict_flags.length !== 0
      )
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "No-record errors must abstain and have no attached window",
        });
    } else if (error.window === undefined || !sameTrust(error, error.window))
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Window-scoped errors require the window's unchanged trust",
      });
    if (
      error.error.candidate_ids !== undefined &&
      (error.error.code !== "ambiguous_identifier" ||
        new Set(error.error.candidate_ids).size !==
          error.error.candidate_ids.length)
    )
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["error", "candidate_ids"],
        message: "Only ambiguous identifiers carry distinct candidate IDs",
      });
  });
export type McpToolError = z.infer<typeof McpToolError>;

export const ListWindowsSuccess = EnvelopeMeta.extend({
  data: z.array(WindowSummary).max(20),
  pagination: BoundedPagination,
  delivery: DeliveryMeta,
  coverage: Coverage,
  applied_filters: ListWindowsInput,
  next_offset: NextOffset,
})
  .strict()
  .superRefine((output, ctx) => {
    pageInvariant(output, output.data.length, ctx);
    collectionDelivery(output.delivery, output.data, ctx);
    if (
      output.pagination.limit !== output.applied_filters.limit ||
      output.pagination.offset !== output.applied_filters.offset
    )
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["pagination"],
        message: "Pagination must match applied filters",
      });
    if (
      (output.applied_filters.closes_after ||
        output.applied_filters.closes_before) &&
      output.coverage.unknown_close_count > 0 &&
      !output.coverage.unresolved_close_followup
    )
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["coverage"],
        message: "Date-filtered results must disclose omitted unknown closes",
      });
  });
export const SearchHit = z
  .object({
    id: FederalOcdId,
    title: z.string().min(1).max(600),
    url: Url,
    trust: Trust,
  })
  .strict();
export type SearchHit = z.infer<typeof SearchHit>;
export const SearchMeta = z
  .object({
    delivery: DeliveryMeta,
    coverage: Coverage,
    pagination: BoundedPagination,
    next_query: z.string().min(1).max(500).nullable(),
  })
  .strict();
export type SearchMeta = z.infer<typeof SearchMeta>;
export const SearchSuccess = EnvelopeMeta.extend({
  results: z.array(SearchHit).max(10),
  meta: SearchMeta,
})
  .strict()
  .superRefine((output, ctx) => {
    collectionDelivery(
      output.meta.delivery,
      output.results.map((hit) => hit.trust),
      ctx,
    );
    const { pagination, next_query } = output.meta;
    if (pagination.limit !== 10)
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["meta", "pagination", "limit"],
        message: "Search uses fixed page size 10",
      });
    const next = pagination.offset + output.results.length;
    pageInvariant(
      { pagination, next_offset: next_query === null ? null : next },
      output.results.length,
      ctx,
    );
  });
export const FetchMeta = z
  .object({ data: WindowSummary, delivery: DeliveryMeta })
  .strict();
export type FetchMeta = z.infer<typeof FetchMeta>;
export const FetchSuccess = EnvelopeMeta.extend({
  id: FederalOcdId,
  title: z.string().min(1).max(600),
  text: z.string().min(1).max(24000),
  url: Url,
  metadata: FetchMeta,
})
  .strict()
  .superRefine((output, ctx) => {
    windowDelivery(output.metadata.delivery, output.metadata.data, ctx);
    if (output.id !== output.metadata.data.ocd_id)
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["id"],
        message: "Fetch identity must equal the stored window identity",
      });
  });
export const ListConflictsSuccess = EnvelopeMeta.extend({
  data: z.array(ConflictEvidence).max(20),
  pagination: BoundedPagination,
  delivery: DeliveryMeta,
  next_offset: NextOffset,
})
  .strict()
  .superRefine((output, ctx) => {
    pageInvariant(output, output.data.length, ctx);
    collectionDelivery(
      output.delivery,
      output.data
        .flatMap((item) => [
          item.record,
          item.side_a,
          ...(item.side_b === null ? [] : [item.side_b]),
        ])
        .map((item) => ({
          confidence: "unknown" as const,
          conflict_flags: item.conflict_flags,
        })),
      ctx,
    );
    for (const conflict of output.data)
      for (const evidence of [conflict.evidence_a, conflict.evidence_b]) {
        if (
          "missing" in evidence &&
          !output.delivery.warnings.some((warning) =>
            warning.includes(evidence.observation_id),
          )
        )
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            path: ["delivery", "warnings"],
            message:
              "Missing conflict evidence requires a per-item warning naming the observation",
          });
      }
  });
export const ExplainWindowSuccess = EnvelopeMeta.extend({
  data: ExplainSection,
  delivery: DeliveryMeta,
  evidence_as_of: Instant,
})
  .strict()
  .superRefine((output, ctx) => {
    windowDelivery(output.delivery, output.data.window, ctx);
    if (Date.parse(output.evidence_as_of) > Date.parse(output.delivery.read_at))
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["evidence_as_of"],
        message: "Evidence boundary cannot be after read_at",
      });
    if (
      output.data.section === "observations" ||
      output.data.section === "verdicts"
    )
      for (const item of output.data.items) {
        if (Date.parse(item.fetched_at) > Date.parse(output.evidence_as_of))
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            path: ["data", "items"],
            message: "Evidence must not exceed evidence_as_of",
          });
      }
  });
export const SubmissionInfoSuccess = EnvelopeMeta.extend({
  data: SubmissionInfo,
  delivery: DeliveryMeta,
})
  .strict()
  .superRefine((output, ctx) =>
    windowDelivery(output.delivery, output.data.window, ctx),
  );

// Each advertised output schema describes failures as well as successes.
export const ListWindowsOutput = z.union([ListWindowsSuccess, McpToolError]);
export type ListWindowsSuccess = z.infer<typeof ListWindowsSuccess>;
export type ListWindowsOutput = z.infer<typeof ListWindowsOutput>;
export const SearchOutput = z.union([SearchSuccess, McpToolError]);
export type SearchSuccess = z.infer<typeof SearchSuccess>;
export type SearchOutput = z.infer<typeof SearchOutput>;
export const FetchOutput = z.union([FetchSuccess, McpToolError]);
export type FetchSuccess = z.infer<typeof FetchSuccess>;
export type FetchOutput = z.infer<typeof FetchOutput>;
export const ListConflictsOutput = z.union([
  ListConflictsSuccess,
  McpToolError,
]);
export type ListConflictsSuccess = z.infer<typeof ListConflictsSuccess>;
export type ListConflictsOutput = z.infer<typeof ListConflictsOutput>;
export const ExplainWindowOutput = z.union([
  ExplainWindowSuccess,
  McpToolError,
]);
export type ExplainWindowSuccess = z.infer<typeof ExplainWindowSuccess>;
export type ExplainWindowOutput = z.infer<typeof ExplainWindowOutput>;
export const SubmissionInfoOutput = z.union([
  SubmissionInfoSuccess,
  McpToolError,
]);
export type SubmissionInfoSuccess = z.infer<typeof SubmissionInfoSuccess>;
export type SubmissionInfoOutput = z.infer<typeof SubmissionInfoOutput>;
