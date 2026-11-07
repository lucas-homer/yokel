/**
 * Phase 0 MCP tool service: six read-only tools over the shared delivery reads. Transport-neutral:
 * returns the validated output ENVELOPE (success or McpToolError), never an MCP wire result. The
 * transport owns the single JSON text mirror, structuredContent, timeouts and unknown-tool errors.
 *
 * Trust rules enforced here: per-window confidence/flags are copied from the validated projection,
 * never recomputed; collections abstain (confidence=unknown, collection_no_aggregate, union of
 * returned flags); every answer carries the exact disclaimer; citations are official HTTPS pages,
 * never raw payload URLs; review executors and notes stay redacted; the federal boundary is applied
 * by the read adapter before pagination. Honoring uses the engine's pure selector on the COMPLETE
 * primary chain plus the engine's linked-amendment inputs (ADR 0016 §7); it never re-derives or
 * persists a deadline.
 */
import { randomUUID } from "node:crypto";
import { isDeepStrictEqual } from "node:util";
import { ZodError, type ZodIssue, type ZodTypeAny } from "zod";
import {
  API_VERSION,
  ConflictFlag,
  DISCLAIMER,
  HumanReviewVerdict,
  type ConflictRecord,
  type Observation,
  type ParticipationWindow,
} from "@yokel/contracts";
import {
  McpReadError,
  getEngineObservations,
  getEngineReconcileOptions,
  getEvidencePage,
  getProjectionStamp,
  getWindowMetadata,
  listMcpConflicts,
  listMcpWindows,
  readEvidenceByIds,
  resolveWindow,
  withMcpRead,
  type McpConflictFilters,
  type McpEvidenceRow,
  type McpPageResult,
  type McpWindowFilters,
  type McpWindowPage,
  type WindowMetadata,
} from "../api/mcp-queries.js";
import type { Sql } from "../db/client.js";
import {
  RECONCILER_VERSION,
  selectHonoredVerdict,
  type HonoredVerdict,
  type ReconcileOptions,
} from "../reconcile/reconcile.js";
import {
  citationFor,
  confidenceSentence,
  displayText,
  evidenceSourceUrl,
  fitsResultBudget,
  linkHost,
  linkSafety,
  MAX_RESULT_BYTES,
  renderFetchText,
  requiresVerification,
  trustLabel,
  type Citation,
} from "./presentation.js";
import {
  nextSearchQuery,
  parseSearchQuery,
  QuerySyntaxError,
} from "./query.js";
import {
  AgencySlug,
  BoundedHistoryEntry,
  Coverage,
  DeliveryMeta,
  EnvelopeMeta,
  ExplainSummary,
  ExplainWindowInput,
  ExplainWindowOutput,
  ExplainWindowSuccess,
  FetchInput,
  FederalOcdId,
  FetchOutput,
  FetchSuccess,
  ListConflictsInput,
  ListConflictsOutput,
  ListConflictsSuccess,
  ListWindowsInput,
  ListWindowsOutput,
  ListWindowsSuccess,
  McpToolError,
  Reference,
  SearchInput,
  SearchOutput,
  SearchSuccess,
  SubmissionInfoInput,
  SubmissionInfoOutput,
  SubmissionInfoSuccess,
  TOOL_SCHEMA_VERSION,
  toEvidenceSummary,
  toPageExcerpt,
  toVerdictSummary,
  toWindowSummary,
  type ConflictEvidence,
  type EvidenceResult,
  type Honoring,
  type McpToolErrorCode,
  type Trust,
  type VerdictSummary,
  type WindowSummary,
} from "./schemas.js";

// ─── Tool catalog ────────────────────────────────────────────────────────────────────────────

export const TOOL_NAMES = [
  "list_windows",
  "search",
  "fetch",
  "list_conflicts",
  "explain_window",
  "get_submission_info",
] as const;
export type ToolName = (typeof TOOL_NAMES)[number];
export function isToolName(name: string): name is ToolName {
  return (TOOL_NAMES as readonly string[]).includes(name);
}

export interface ToolDefinition {
  title: string;
  description: string;
  inputSchema: ZodTypeAny;
  /** Describes the full result: success OR McpToolError. */
  outputSchema: ZodTypeAny;
  /** Client hints only (standard MCP annotation names); never an authorization mechanism. */
  annotations: {
    readOnlyHint: true;
    destructiveHint: false;
    idempotentHint: true;
    openWorldHint: false;
  };
}
const READ_ONLY = {
  readOnlyHint: true,
  destructiveHint: false,
  idempotentHint: true,
  openWorldHint: false,
} as const;
const CARRY =
  "Every result carries a disclaimer: DocketClock is not legal notice. Repeat it and every " +
  "unknown, conflicting or stale caveat in your answer, and cite the official source.";
export const TOOL_DEFINITIONS: Record<ToolName, ToolDefinition> = {
  list_windows: {
    title: "List stored federal participation windows",
    description:
      "List stored federal DocketClock participation windows (default: comment periods), each with its own " +
      "confidence, conflict flags and evidence counts. Filters are conjunctive and exact: agency is an exact " +
      "Federal Register agency slug (e.g. environmental-protection-agency); docket_id and rin are exact; keyword " +
      "is a literal substring of the stored title or identifiers. closes_after/closes_before are EXCLUSIVE " +
      "instants that require a timezone offset; resolve phrases like 'this month' into explicit bounds yourself " +
      "and show them to the user. Closing bounds exclude windows with no operative close: when " +
      "coverage.unresolved_close_followup is true, also run close_mode=unknown without bounds; " +
      "coverage.disputed_close_count counts conflicting (disputed) closes inside the bounds. status=open is the " +
      "stored status, not a live portal check. Collection confidence is always 'unknown' (no aggregate rating): " +
      "read each window's confidence. Counts describe stored data, never complete federal coverage. Page size " +
      "at most 20, offset at most 1000; continue from next_offset. " +
      CARRY,
    inputSchema: ListWindowsInput,
    outputSchema: ListWindowsOutput,
    annotations: READ_ONLY,
  },
  search: {
    title: "Search stored federal windows (deterministic grammar)",
    description:
      "Deterministic search over the same stored windows as list_windows; it does not interpret natural " +
      'language. Plain words and "quoted phrases" match titles and identifiers literally. Optional operators ' +
      "map exactly to list_windows filters: agency:<FR slug> docket:<id> rin:<rin> status:<status> " +
      "confidence:<confidence> type:<window type> after:<instant> before:<instant> (exclusive, offset required) " +
      "close:any|known|unknown offset:<n>. Unknown operators or invalid values fail. 'EPA this month' as plain " +
      "words is a lexical match, so convert it to agency:environmental-protection-agency after:... before:... " +
      "yourself. Fixed page size 10; use meta.next_query to continue. Hit titles start with a confidence label. " +
      CARRY,
    inputSchema: SearchInput,
    outputSchema: SearchOutput,
    annotations: READ_ONLY,
  },
  fetch: {
    title: "Fetch one stored window",
    description:
      "Fetch one stored federal window by OCD-ID or Federal Register document number and return the stored " +
      "OCD-ID, an official citation URL, a deterministic text summary and the bounded window record. An " +
      "ambiguous document number returns candidate OCD-IDs instead of guessing. Returns citation_unavailable " +
      "(with the window) when no official citation URL is stored or derivable. " +
      CARRY,
    inputSchema: FetchInput,
    outputSchema: FetchOutput,
    annotations: READ_ONLY,
  },
  list_conflicts: {
    title: "List live source conflicts",
    description:
      "List LIVE (unresolved) conflicts between sources (cross_source, same window) or between an amendment " +
      "and the window it changes (cross_window, side_b present), optionally for one OCD-ID on either side. " +
      "Each item carries both window summaries and bounded evidence for the two disagreeing observations; " +
      "missing evidence is shown explicitly with a warning, never dropped. Collection confidence is 'unknown' " +
      "(no aggregate). " +
      CARRY,
    inputSchema: ListConflictsInput,
    outputSchema: ListConflictsOutput,
    annotations: READ_ONLY,
  },
  explain_window: {
    title: "Explain a window's confidence and evidence",
    description:
      "Explain why a stored window has its confidence: section=summary (stored source close values, " +
      "provenance counts, the engine-honored review verdict and review-overlay alignment; no causal rules " +
      "trace is recorded), or paged sections observations, verdicts, history and references. Page one returns " +
      "evidence_as_of; follow-up pages (offset > 0) must send that evidence_as_of and the window version as " +
      "expected_version, and a changed version returns stale_read (restart from offset 0). An honored " +
      "'escalate' verdict parks the window and asserts no deadline. Executors and review notes are redacted. " +
      CARRY,
    inputSchema: ExplainWindowInput,
    outputSchema: ExplainWindowOutput,
    annotations: READ_ONLY,
  },
  get_submission_info: {
    title: "Get the stored submission link",
    description:
      "Return the stored submission and GovInfo links for one window. availability=unavailable means no " +
      "submission link is stored, not that comments are closed. Links are not checked live, other submission " +
      "channels are not modeled, and nothing is submitted or filled in. A link on a non-official host is " +
      "labeled for verification. " +
      CARRY,
    inputSchema: SubmissionInfoInput,
    outputSchema: SubmissionInfoOutput,
    annotations: READ_ONLY,
  },
};

// ─── Read port (the adapter seam; replaceable in tests) ───────────────────────────────────────

export interface McpReader {
  resolveWindow(id: string): Promise<ParticipationWindow | null>;
  getWindowMetadata(ocdId: string): Promise<WindowMetadata>;
  listWindows(filters: McpWindowFilters): Promise<McpWindowPage>;
  listConflicts(
    filters: McpConflictFilters,
  ): Promise<McpPageResult<ConflictRecord>>;
  getEvidencePage(
    ocdId: string,
    options: { limit: number; offset: number; evidenceAsOf?: string },
  ): Promise<McpPageResult<McpEvidenceRow>>;
  readEvidenceByIds(ocdId: string, ids: string[]): Promise<Observation[]>;
  getEngineObservations(ocdId: string): Promise<Observation[]>;
  getEngineReconcileOptions(ocdId: string): Promise<ReconcileOptions>;
  getProjectionStamp(
    id: string,
  ): Promise<{ derivedAt: string | null; reconcilerVersion: string | null }>;
}
/** One call = one read-only repeatable-read transaction (or the test double's equivalent). */
export interface McpReadPort {
  read<T>(work: (reader: McpReader) => Promise<T>): Promise<T>;
}
export function sqlReadPort(sql: Sql): McpReadPort {
  return {
    read: (work) =>
      withMcpRead(sql, (tx) =>
        work({
          resolveWindow: (id) => resolveWindow(tx, id),
          getWindowMetadata: (id) => getWindowMetadata(tx, id),
          listWindows: (filters) => listMcpWindows(tx, filters),
          listConflicts: (filters) => listMcpConflicts(tx, filters),
          getEvidencePage: (id, options) => getEvidencePage(tx, id, options),
          readEvidenceByIds: (id, ids) => readEvidenceByIds(tx, id, ids),
          getEngineObservations: (id) => getEngineObservations(tx, id),
          getEngineReconcileOptions: (id) => getEngineReconcileOptions(tx, id),
          getProjectionStamp: (id) => getProjectionStamp(tx, id),
        }),
      ),
  };
}

// ─── Service ──────────────────────────────────────────────────────────────────────────────────

export interface ToolServiceOptions {
  now?: () => Date;
  requestId?: () => string;
  /** Total serialized budget for structuredContent + JSON text mirror. Default 48 KiB. */
  maxResultBytes?: number;
  /** Server-side hook for unexpected failures (DB/data/validation). The tool output stays sanitized. */
  onFailure?: (
    error: unknown,
    context: { tool: ToolName; requestId: string },
  ) => void;
}
export interface ToolOutcome {
  /** True for McpToolError envelopes (map to CallToolResult.isError). */
  isError: boolean;
  /** Validated success envelope (root disclaimer first) or an McpToolError envelope. */
  output: Record<string, unknown>;
}
/** Never rejects for tool failures; rejects only with UnknownToolError for an unregistered name. */
export type ToolService = (name: string, args: unknown) => Promise<ToolOutcome>;
/** Thrown (not returned) so the transport answers with its protocol-level unknown-tool error. */
export class UnknownToolError extends Error {
  constructor(public readonly toolName: string) {
    super("Unknown tool");
    this.name = "UnknownToolError";
  }
}

export function createToolService(
  sql: Sql,
  options: ToolServiceOptions = {},
): ToolService {
  return createToolServiceFromPort(sqlReadPort(sql), options);
}

interface Ctx {
  root: EnvelopeMeta;
  readAt: string;
  maxBytes: number;
}
type Handler = (
  reader: McpReader,
  input: never,
  ctx: Ctx,
) => Promise<Record<string, unknown>>;
const HANDLERS: Record<ToolName, Handler> = {
  list_windows: listWindowsTool as Handler,
  search: searchTool as Handler,
  fetch: fetchTool as Handler,
  list_conflicts: listConflictsTool as Handler,
  explain_window: explainWindowTool as Handler,
  get_submission_info: submissionInfoTool as Handler,
};

export function createToolServiceFromPort(
  port: McpReadPort,
  options: ToolServiceOptions = {},
): ToolService {
  const now = options.now ?? (() => new Date());
  const newRequestId = options.requestId ?? randomUUID;
  const maxBytes = options.maxResultBytes ?? MAX_RESULT_BYTES;
  return async (name, args) => {
    if (!isToolName(name)) throw new UnknownToolError(name);
    const requestId = newRequestId();
    const ctx: Ctx = {
      root: {
        disclaimer: DISCLAIMER,
        api_version: API_VERSION,
        request_id: requestId,
      },
      readAt: now().toISOString(),
      maxBytes,
    };
    try {
      const parsed = TOOL_DEFINITIONS[name].inputSchema.safeParse(
        args === undefined ? {} : args,
      );
      if (!parsed.success) throw inputFailure(parsed.error);
      const output = await port.read((reader) =>
        HANDLERS[name](reader, parsed.data as never, ctx),
      );
      if (!fitsResultBudget(output, false, maxBytes))
        throw new ToolFailure(
          "result_too_large",
          "The result exceeds the 48 KiB limit. Use the official citation, or a narrower explain_window section or page.",
          { window: attachedWindow(output) },
        );
      return { isError: false, output };
    } catch (error) {
      if (
        error instanceof ToolFailure
          ? error.code === "internal_error"
          : !(error instanceof McpReadError)
      )
        options.onFailure?.(error, { tool: name, requestId });
      return { isError: true, output: failureOutput(error, ctx) };
    }
  };
}

// ─── Errors ───────────────────────────────────────────────────────────────────────────────────

interface FailureOptions {
  retryable?: boolean;
  window?: WindowSummary;
  candidateIds?: string[];
}
class ToolFailure extends Error {
  constructor(
    readonly code: McpToolErrorCode,
    message: string,
    readonly options: FailureOptions = {},
  ) {
    super(message);
    this.name = "ToolFailure";
  }
}
function clip(text: string, max: number): string {
  return text.length <= max ? text : `${text.slice(0, max - 1)}…`;
}

const RETRYABLE_SQLSTATE = /^(?:08|53|57P|40001|40P01|57014|25P0[34])/u;
const RETRYABLE_NETWORK = new Set([
  "CONNECT_TIMEOUT",
  "CONNECTION_CLOSED",
  "CONNECTION_ENDED",
  "CONNECTION_DESTROYED",
  "ECONNREFUSED",
  "ECONNRESET",
  "ETIMEDOUT",
  "ENOTFOUND",
  "EAI_AGAIN",
  "EPIPE",
  "MCP_READ_TIMEOUT",
]);
function isTransient(error: unknown): boolean {
  if (typeof error !== "object" || error === null) return false;
  const code = (error as { code?: unknown }).code;
  if (typeof code !== "string") return false;
  return (error as { name?: unknown }).name === "PostgresError"
    ? RETRYABLE_SQLSTATE.test(code)
    : RETRYABLE_NETWORK.has(code);
}

function errorEnvelope(
  ctx: Ctx,
  code: McpToolErrorCode,
  message: string,
  options: FailureOptions,
) {
  const build = (window: WindowSummary | undefined) =>
    McpToolError.parse({
      ...ctx.root,
      confidence: window?.confidence ?? "unknown",
      conflict_flags: window ? [...window.conflict_flags] : [],
      confidence_scope: window ? "window" : "no_record",
      error: {
        code,
        message: clip(message, 500),
        retryable: options.retryable ?? false,
        ...(options.candidateIds && options.candidateIds.length >= 2
          ? { candidate_ids: options.candidateIds.slice(0, 20) }
          : {}),
      },
      ...(window ? { window } : {}),
    });
  const withWindow = build(options.window);
  // A window that does not fit still leaves a valid abstaining error.
  return options.window && !fitsResultBudget(withWindow, true, ctx.maxBytes)
    ? build(undefined)
    : withWindow;
}
function failureOutput(error: unknown, ctx: Ctx): Record<string, unknown> {
  if (error instanceof ToolFailure)
    return errorEnvelope(ctx, error.code, error.message, error.options);
  if (error instanceof McpReadError) {
    const message =
      error.code === "ambiguous_identifier"
        ? "The FR document number matches more than one stored window; call again with one of candidate_ids."
        : error.message;
    return errorEnvelope(ctx, error.code, message, {
      candidateIds: error.candidateOcdIds,
    });
  }
  if (isTransient(error))
    return errorEnvelope(
      ctx,
      "temporarily_unavailable",
      "The DocketClock read store is temporarily unavailable or the read timed out. Retry later.",
      { retryable: true },
    );
  return errorEnvelope(
    ctx,
    "internal_error",
    "DocketClock could not complete this read; no partial result is returned.",
    {},
  );
}
function attachedWindow(
  output: Record<string, unknown>,
): WindowSummary | undefined {
  const o = output as {
    metadata?: { data?: WindowSummary };
    data?: { window?: WindowSummary };
  };
  return o.metadata?.data ?? o.data?.window;
}

const SEARCH_FILTER_NAMES: Record<string, string> = {
  docket_id: "docket",
  window_type: "type",
  closes_after: "after",
  closes_before: "before",
  close_mode: "close",
};
function describeIssue(
  issue: ZodIssue,
  prefix: string,
  rename: Record<string, string> = {},
): string {
  const path =
    issue.path.map((part) => rename[String(part)] ?? String(part)).join(".") ||
    prefix;
  switch (issue.code) {
    case "invalid_type":
      return `${path}: expected ${issue.expected}`;
    case "invalid_enum_value":
      return `${path}: expected one of ${issue.options.join(", ")}`;
    case "too_small":
      return `${path}: below the minimum ${String(issue.minimum)}`;
    case "too_big":
      return `${path}: above the maximum ${String(issue.maximum)}`;
    case "invalid_string":
      return (
        `${path}: invalid ${typeof issue.validation === "string" ? issue.validation : "format"}` +
        (issue.validation === "datetime"
          ? " (an ISO-8601 instant with offset is required)"
          : "")
      );
    case "custom":
      return `${path}: ${issue.message}`; // schema-authored messages; they never echo input values
    default:
      return `${path}: invalid value`;
  }
}
/** Sanitized input errors: no input values are echoed except bounded, identifier-shaped field names. */
function inputFailure(
  error: ZodError,
  prefix = "input",
  rename: Record<string, string> = {},
): ToolFailure {
  const unknownKeys = error.issues.flatMap((issue) =>
    issue.code === "unrecognized_keys" ? issue.keys : [],
  );
  if (unknownKeys.length) {
    const names = unknownKeys
      .slice(0, 5)
      .map((key) => (/^[A-Za-z0-9_]{1,40}$/u.test(key) ? key : "(unnamed)"));
    return new ToolFailure(
      "unsupported_filter",
      `Unsupported field(s): ${names.join(", ")}. Unsupported filters are rejected, never ignored.`,
    );
  }
  const details = error.issues
    .slice(0, 4)
    .map((issue) => describeIssue(issue, prefix, rename));
  return new ToolFailure(
    "invalid_input",
    `Invalid ${prefix}: ${details.join("; ")}`,
  );
}

// ─── Shared mapping ───────────────────────────────────────────────────────────────────────────

/** Fail closed on stored links that are not plain http(s) public URLs; they are never displayed. */
function assertLinksSafe(links: (string | null)[]): void {
  if (links.some((link) => linkSafety(link) === "unsafe"))
    throw new ToolFailure(
      "internal_error",
      "A stored record failed the link-safety check and is withheld. Consult the official source.",
    );
}
const withholdUnsafe = (link: string | null) =>
  linkSafety(link) === "unsafe" ? null : link;
/**
 * Collections show other windows too, so one unsafe stored link is withheld rather than failing the
 * page. Single-window answers keep failing closed through windowSummaryOf.
 */
function withholdUnsafeLinks(window: ParticipationWindow): ParticipationWindow {
  const submission_url = withholdUnsafe(window.submission_url);
  const govinfo_url = withholdUnsafe(window.govinfo_url);
  return submission_url === window.submission_url &&
    govinfo_url === window.govinfo_url
    ? window
    : { ...window, submission_url, govinfo_url };
}
const withheldLinkWarning = (count: number) =>
  count === 0
    ? []
    : [
        `${count} stored record(s) here had a link that failed the safety check. It is withheld and shown as null, so consult the official notice.`,
      ];
/** Bounded public summary of a validated projection. Indivisible oversize values are never shortened. */
export function windowSummaryOf(
  window: ParticipationWindow,
  metadata: WindowMetadata,
): WindowSummary {
  assertLinksSafe([window.submission_url, window.govinfo_url]);
  try {
    const summary = toWindowSummary(window, {
      title: displayText(metadata.title),
      // Malformed slugs cannot match the exact agency filter; they are not public vocabulary.
      agencySlugs: metadata.agencySlugs.filter(
        (slug) => AgencySlug.safeParse(slug).success,
      ),
      observationIds: metadata.observationIds,
    });
    return { ...summary, title: displayExcerpt(metadata.title) };
  } catch (error) {
    if (!(error instanceof ZodError)) throw error;
    const citation = citationFor(window);
    throw new ToolFailure(
      "result_too_large",
      "A stored window exceeds the bounded summary limits and is not shortened." +
        (citation
          ? ` Official citation: ${citation.url}`
          : " No official citation URL is available."),
    );
  }
}
/** Sanitization is a removal from the source excerpt, so retain its original length. */
function displayExcerpt(raw: string | null) {
  const shown = toPageExcerpt(displayText(raw));
  return {
    ...shown,
    original_characters: raw?.length ?? 0,
    truncated: (shown.text?.length ?? 0) < (raw?.length ?? 0),
  };
}
function publicEvidence(
  observation: Observation,
  metadata: Parameters<typeof toEvidenceSummary>[1],
) {
  const summary = toEvidenceSummary(observation, metadata);
  return {
    ...summary,
    // Review notes are private even if a legacy row also copied them into DATES.
    raw_dates_excerpt: displayExcerpt(
      observation.source === "human_review" ? null : observation.raw_dates_text,
    ),
  };
}
async function summarize(
  reader: McpReader,
  window: ParticipationWindow,
): Promise<WindowSummary> {
  return windowSummaryOf(window, await reader.getWindowMetadata(window.ocd_id));
}
async function resolveOrFail(
  reader: McpReader,
  id: string,
): Promise<ParticipationWindow> {
  const window = await reader.resolveWindow(id);
  if (!window)
    throw new ToolFailure(
      "not_found",
      "No stored federal window matches this identifier. DocketClock coverage is not complete.",
    );
  return window;
}

function unionFlags(items: Trust[]): ConflictFlag[] {
  const flags = new Set(items.flatMap((item) => item.conflict_flags));
  return ConflictFlag.options.filter((flag) => flags.has(flag));
}
function collectionDelivery(
  ctx: Ctx,
  items: Trust[],
  warnings: string[],
): DeliveryMeta {
  return DeliveryMeta.parse({
    confidence: "unknown",
    conflict_flags: unionFlags(items),
    tool_schema_version: TOOL_SCHEMA_VERSION,
    read_at: ctx.readAt,
    confidence_scope: "collection_no_aggregate",
    warnings,
  });
}
function windowDelivery(
  ctx: Ctx,
  window: WindowSummary,
  warnings: string[],
): DeliveryMeta {
  return DeliveryMeta.parse({
    confidence: window.confidence,
    conflict_flags: [...window.conflict_flags], // byte-for-byte, same order
    tool_schema_version: TOOL_SCHEMA_VERSION,
    read_at: ctx.readAt,
    confidence_scope: "window",
    warnings: warnings.slice(0, 10),
  });
}
/** Per-window caveats. Hosts are bounded; no other source text enters warnings. */
export function windowWarnings(window: WindowSummary): string[] {
  const warnings: string[] = [];
  if (requiresVerification(window.confidence))
    warnings.push(
      `Confidence is ${window.confidence}: ${confidenceSentence(window)}`,
    );
  if (window.conflict_flags.includes("fr_close_amended"))
    warnings.push(
      `raw_fr_close_date ${window.raw_fr_close_date ?? "(none)"} is the original Federal Register value, superseded by a verified FR amendment. Do not report it as the current FR deadline.`,
    );
  if (
    window.submission_url !== null &&
    linkSafety(window.submission_url) !== "official"
  )
    warnings.push(
      `The stored submission link is on ${clip(linkHost(window.submission_url), 100)}, not a recognized official host; verify it against the official notice.`,
    );
  if (
    window.govinfo_url !== null &&
    citationFor({
      ...window,
      fr_document_number: null,
      regs_document_id: null,
    }) === null
  )
    warnings.push(
      "The stored GovInfo link is not on an official GovInfo HTTPS host and is not used as a citation.",
    );
  if (window.title.text === null || window.agency_slugs.length === 0)
    warnings.push(
      "No stored Federal Register title or agency metadata is available for this window.",
    );
  return warnings;
}
function collectionTrustWarnings(windows: WindowSummary[]): string[] {
  const warnings: string[] = [];
  const verify = windows.filter((w) =>
    requiresVerification(w.confidence),
  ).length;
  if (verify)
    warnings.push(
      `${verify} returned window(s) have unknown, conflicting or stale confidence and require verification against official sources; do not present them as settled.`,
    );
  const disputed = windows.filter(
    (w) => w.confidence === "conflicting" && w.resolved_close_utc !== null,
  ).length;
  if (disputed)
    warnings.push(
      `${disputed} returned window(s) carry a disputed (conflicting) close; it is shown for transparency, not as the settled deadline.`,
    );
  const amended = windows.filter((w) =>
    w.conflict_flags.includes("fr_close_amended"),
  ).length;
  if (amended)
    warnings.push(
      `${amended} returned window(s) carry fr_close_amended: raw_fr_close_date is the original FR value, superseded by a verified FR amendment.`,
    );
  const offHost = windows.filter(
    (w) =>
      w.submission_url !== null && linkSafety(w.submission_url) !== "official",
  ).length;
  if (offHost)
    warnings.push(
      `${offHost} returned window(s) have a stored submission link on a non-official host; verify those links against the official notice.`,
    );
  return warnings;
}
function nextOffset(
  offset: number,
  count: number,
  total: number,
): number | null {
  const next = offset + count;
  return next < total && next <= 1000 ? next : null;
}
function pagingWarnings(
  offset: number,
  count: number,
  total: number,
  reduced: boolean,
): string[] {
  const warnings: string[] = [];
  if (reduced)
    warnings.push(
      `Only ${count} item(s) fit the 48 KiB result or warning limit; continue from next_offset.`,
    );
  if (offset + count < total && offset + count > 1000)
    warnings.push(
      "Results beyond offset 1000 cannot be paged; narrow the filters.",
    );
  return warnings;
}

/** Down-page by the serialized size of BOTH copies; zero fitting items is a typed error, never an empty loop. */
function fitPage<T>(
  items: T[],
  ctx: Ctx,
  build: (slice: T[], reduced: boolean) => Record<string, unknown> | null,
): Record<string, unknown> {
  for (let count = items.length; count >= (items.length ? 1 : 0); count--) {
    const output = build(items.slice(0, count), count < items.length);
    if (output && fitsResultBudget(output, false, ctx.maxBytes)) return output;
  }
  throw new ToolFailure(
    "result_too_large",
    "Even one item exceeds the 48 KiB result limit. Use fetch or a narrower explain_window section for that window.",
  );
}

// ─── list_windows / search ───────────────────────────────────────────────────────────────────

function windowFilters(input: ListWindowsInput): McpWindowFilters {
  return { ...input };
}
function omitsNullCloses(input: ListWindowsInput): boolean {
  return (
    input.closes_after !== undefined ||
    input.closes_before !== undefined ||
    input.close_mode === "known"
  );
}
function coverageOf(page: McpWindowPage, input: ListWindowsInput): Coverage {
  return Coverage.parse({
    jurisdiction: "federal",
    corpus: "stored_docketclock_windows",
    completeness: "not_asserted",
    metadata_missing_count: page.metadataMissingCount,
    unknown_close_count: page.unknownCloseCount,
    disputed_close_count: page.disputedCloseCount,
    unresolved_close_followup:
      omitsNullCloses(input) && page.unknownCloseCount > 0,
  });
}
function coverageWarnings(
  input: ListWindowsInput,
  coverage: Coverage,
): string[] {
  const warnings: string[] = [];
  const dated =
    input.closes_after !== undefined || input.closes_before !== undefined;
  if (dated)
    warnings.push(
      "Closing bounds are exclusive: closes_after < operative close < closes_before.",
    );
  if (coverage.unresolved_close_followup)
    warnings.push(
      `${coverage.unknown_close_count} window(s) matching the other filters have no operative close and are excluded here; they cannot be said to close in this range. Query close_mode=unknown without closing bounds.`,
    );
  if (coverage.disputed_close_count > 0)
    warnings.push(
      `${coverage.disputed_close_count} matching window(s) have a disputed (conflicting) close inside these filters; also query confidence=conflicting with the same bounds.`,
    );
  if (
    (input.agency !== undefined || input.keyword !== undefined) &&
    coverage.metadata_missing_count > 0
  )
    warnings.push(
      `${coverage.metadata_missing_count} candidate window(s), counted before agency/keyword filters, lack stored title or agency metadata and cannot match them. This is a broader population, not a count of missed matches.`,
    );
  return warnings;
}
async function readWindowPage(reader: McpReader, input: ListWindowsInput) {
  const page = await reader.listWindows(windowFilters(input));
  const summaries: WindowSummary[] = [];
  let withheld = 0;
  for (const window of page.rows) {
    const safe = withholdUnsafeLinks(window);
    if (safe !== window) withheld++;
    summaries.push(await summarize(reader, safe));
  }
  return { page, summaries, withheld, coverage: coverageOf(page, input) };
}

async function listWindowsTool(
  reader: McpReader,
  input: ListWindowsInput,
  ctx: Ctx,
) {
  const { page, summaries, withheld, coverage } = await readWindowPage(
    reader,
    input,
  );
  const base = [
    ...withheldLinkWarning(withheld),
    ...coverageWarnings(input, coverage),
  ];
  return fitPage(summaries, ctx, (slice, reduced) => {
    const warnings = [
      ...base,
      ...collectionTrustWarnings(slice),
      ...pagingWarnings(input.offset, slice.length, page.total, reduced),
    ];
    return ListWindowsSuccess.parse({
      ...ctx.root,
      data: slice,
      pagination: {
        limit: input.limit,
        offset: input.offset,
        total: page.total,
      },
      delivery: collectionDelivery(ctx, slice, warnings.slice(0, 10)),
      coverage,
      applied_filters: input,
      next_offset: nextOffset(input.offset, slice.length, page.total),
    });
  });
}

export function hitTitle(window: WindowSummary): string {
  const name =
    window.title.text === null
      ? (window.fr_document_number ?? window.ocd_id)
      : `${window.title.text}${window.title.truncated ? "…" : ""}`;
  return clip(`${trustLabel(window)} ${name}`, 600);
}
function continuationQuery(filters: ListWindowsInput, offset: number): string {
  // Emit a continuation only if it round-trips to exactly the same filters at the next offset.
  let query: string;
  try {
    query = nextSearchQuery(filters, offset);
    if (isDeepStrictEqual(parseSearchQuery(query), { ...filters, offset }))
      return query;
  } catch {
    // fall through
  }
  throw new ToolFailure(
    "invalid_input",
    "These filters cannot be continued as a search query (500-character grammar limit); use list_windows with the same filters.",
  );
}
async function searchTool(reader: McpReader, input: SearchInput, ctx: Ctx) {
  let filters: ListWindowsInput;
  try {
    filters = parseSearchQuery(input.query);
  } catch (error) {
    if (error instanceof QuerySyntaxError)
      throw new ToolFailure(
        error.message.startsWith("Unsupported query operator")
          ? "unsupported_filter"
          : "invalid_input",
        `Invalid query: ${clip(error.message, 200)}. See the tool description for the grammar.`,
      );
    if (error instanceof ZodError)
      throw inputFailure(error, "query", SEARCH_FILTER_NAMES);
    throw error;
  }
  const { page, summaries, withheld, coverage } = await readWindowPage(
    reader,
    filters,
  );
  const cited = summaries.map((window) => ({
    window,
    citation: citationFor(window),
  }));
  const uncited = cited.filter((hit) => hit.citation === null).length;
  if (uncited)
    // Never silently drop a hit (that would falsify pagination totals).
    throw new ToolFailure(
      "citation_unavailable",
      `${uncited} matching window(s) on this page have no usable official citation URL. Use list_windows with the same filters to inspect them.`,
    );
  const base = [
    ...withheldLinkWarning(withheld),
    ...coverageWarnings(filters, coverage),
  ];
  return fitPage(
    cited as { window: WindowSummary; citation: Citation }[],
    ctx,
    (slice, reduced) => {
      const windows = slice.map((hit) => hit.window);
      const next = nextOffset(filters.offset, slice.length, page.total);
      const warnings = [
        ...base,
        ...collectionTrustWarnings(windows),
        ...pagingWarnings(filters.offset, slice.length, page.total, reduced),
      ];
      return SearchSuccess.parse({
        ...ctx.root,
        results: slice.map(({ window, citation }) => ({
          id: window.ocd_id,
          title: hitTitle(window),
          url: citation.url,
          trust: {
            confidence: window.confidence,
            conflict_flags: [...window.conflict_flags],
          },
        })),
        meta: {
          delivery: collectionDelivery(ctx, windows, warnings.slice(0, 10)),
          coverage,
          pagination: { limit: 10, offset: filters.offset, total: page.total },
          next_query: next === null ? null : continuationQuery(filters, next),
        },
      });
    },
  );
}

// ─── fetch / get_submission_info ─────────────────────────────────────────────────────────────

async function fetchTool(reader: McpReader, input: { id: string }, ctx: Ctx) {
  const summary = await summarize(
    reader,
    await resolveOrFail(reader, input.id),
  );
  const citation = citationFor(summary);
  if (!citation)
    throw new ToolFailure(
      "citation_unavailable",
      "No usable official citation URL is stored or derivable for this window. Its stored fields are attached; verify against the official notice.",
      { window: summary },
    );
  const stamp = await reader.getProjectionStamp(summary.ocd_id);
  const text = renderFetchText({
    window: summary,
    citation,
    derivedAt: stamp.derivedAt,
    readAt: ctx.readAt,
  });
  if (text.length > 24000)
    throw new ToolFailure(
      "result_too_large",
      `The window summary is too large to render. Official citation: ${citation.url}`,
      { window: summary },
    );
  return FetchSuccess.parse({
    ...ctx.root,
    id: summary.ocd_id,
    title: hitTitle(summary),
    text,
    url: citation.url,
    metadata: {
      data: summary,
      delivery: windowDelivery(ctx, summary, windowWarnings(summary)),
    },
  });
}

async function submissionInfoTool(
  reader: McpReader,
  input: { id: string },
  ctx: Ctx,
) {
  const summary = await summarize(
    reader,
    await resolveOrFail(reader, input.id),
  );
  const available = summary.submission_url !== null;
  const warnings = [
    ...windowWarnings(summary),
    available
      ? "The stored submission link was not checked live; other submission channels are not modeled."
      : "No submission link is stored. This does not mean comments are closed; consult the official notice for submission instructions.",
  ];
  return SubmissionInfoSuccess.parse({
    ...ctx.root,
    data: {
      window: summary,
      submission_url: summary.submission_url,
      govinfo_url: summary.govinfo_url,
      availability: available ? "stored_link" : "unavailable",
      channel_details: "not_modeled",
      checked_live: false,
    },
    delivery: windowDelivery(ctx, summary, warnings),
  });
}

// ─── list_conflicts ──────────────────────────────────────────────────────────────────────────

async function conflictSideEvidence(
  reader: McpReader,
  scopeOcdId: string,
  observationId: string,
  source: Observation["source"],
): Promise<EvidenceResult> {
  try {
    const [observation] = await reader.readEvidenceByIds(scopeOcdId, [
      observationId,
    ]);
    if (!observation || observation.observation_id !== observationId)
      return {
        missing: true,
        observation_id: observationId,
        reason: "not_found",
      };
    if (observation.source !== source)
      return {
        missing: true,
        observation_id: observationId,
        reason: "unreadable",
      };
    return publicEvidence(observation, {
      sourceUrl: evidenceSourceUrl(observation),
      relationship: ["conflict_side"],
    });
  } catch (error) {
    if (error instanceof ZodError)
      return {
        missing: true,
        observation_id: observationId,
        reason: "unreadable",
      };
    throw error;
  }
}
function missingEvidenceWarning(evidence: EvidenceResult): string[] {
  if (!("missing" in evidence)) return [];
  return [
    `Conflict evidence ${evidence.observation_id} is ${evidence.reason === "not_found" ? "not available on this surface" : "unreadable"}; the conflict remains live.`,
  ];
}
async function listConflictsTool(
  reader: McpReader,
  input: ListConflictsInput,
  ctx: Ctx,
) {
  const page = await reader.listConflicts(input);
  const windows = new Map<string, WindowSummary>();
  const unsafeSides = new Set<string>();
  const side = async (ocdId: string) => {
    const cached = windows.get(ocdId);
    if (cached) return cached;
    const window = await reader.resolveWindow(ocdId);
    if (!window)
      throw new Error("A live conflict references a window that is not stored");
    const safe = withholdUnsafeLinks(window);
    if (safe !== window) unsafeSides.add(ocdId);
    const summary = await summarize(reader, safe);
    windows.set(ocdId, summary);
    return summary;
  };
  const items: { item: ConflictEvidence; warnings: string[] }[] = [];
  for (const stored of page.rows) {
    const record = {
      ...stored,
      govinfo_url: withholdUnsafe(stored.govinfo_url),
      govinfo_url_b: withholdUnsafe(stored.govinfo_url_b),
    };
    const unsafeRecord =
      record.govinfo_url !== stored.govinfo_url ||
      record.govinfo_url_b !== stored.govinfo_url_b;
    const side_a = await side(record.ocd_id);
    const side_b =
      record.conflict_scope === "cross_window" && record.ocd_id_b !== null
        ? await side(record.ocd_id_b)
        : null;
    // Side A's one-hop relation set includes both conflict sides of its own conflicts.
    const evidence_a = await conflictSideEvidence(
      reader,
      record.ocd_id,
      record.observation_a_id,
      record.source_a,
    );
    const evidence_b = await conflictSideEvidence(
      reader,
      record.ocd_id,
      record.observation_b_id,
      record.source_b,
    );
    items.push({
      item: { record, side_a, side_b, evidence_a, evidence_b },
      warnings: [
        ...withheldLinkWarning(
          (unsafeRecord ? 1 : 0) +
            (unsafeSides.has(side_a.ocd_id) ? 1 : 0) +
            (side_b && unsafeSides.has(side_b.ocd_id) ? 1 : 0),
        ),
        ...missingEvidenceWarning(evidence_a),
        ...missingEvidenceWarning(evidence_b),
      ],
    });
  }
  return fitPage(items, ctx, (slice, reduced) => {
    const warnings = [
      ...slice.flatMap((entry) => entry.warnings),
      ...pagingWarnings(input.offset, slice.length, page.total, reduced),
    ];
    if (warnings.length > 10) return null; // every missing-evidence warning must be shown
    const data = slice.map((entry) => entry.item);
    return ListConflictsSuccess.parse({
      ...ctx.root,
      data,
      pagination: {
        limit: input.limit,
        offset: input.offset,
        total: page.total,
      },
      delivery: collectionDelivery(
        ctx,
        data
          .flatMap((item) => [
            item.record,
            item.side_a,
            ...(item.side_b ? [item.side_b] : []),
          ])
          .map((item) => ({
            confidence: "unknown" as const,
            conflict_flags: item.conflict_flags,
          })),
        warnings,
      ),
      next_offset: nextOffset(input.offset, slice.length, page.total),
    });
  });
}

// ─── explain_window ──────────────────────────────────────────────────────────────────────────

type EngineChain =
  | { ok: true; observations: Observation[]; options: ReconcileOptions }
  | { ok: false; reason: string };
/** The engine's exact chain (primary OCD-ID). Oversize or unreadable means unknown, never truncated. */
async function engineChain(
  reader: McpReader,
  ocdId: string,
): Promise<EngineChain> {
  try {
    return {
      ok: true,
      observations: await reader.getEngineObservations(ocdId),
      options: await reader.getEngineReconcileOptions(ocdId),
    };
  } catch (error) {
    if (error instanceof McpReadError && error.code === "result_too_large")
      return {
        ok: false,
        reason: "the engine observation chain exceeds 1000 rows",
      };
    if (error instanceof ZodError)
      return {
        ok: false,
        reason: "an engine-chain observation failed validation",
      };
    throw error; // database errors abort the transaction; do not continue on it
  }
}
function epoch(instant: string): number {
  return Date.parse(instant);
}
/** Same total order as the engine's latestBySource: fetched_at, then greater observation_id. */
function newerThan(a: Observation, b: Observation): boolean {
  const ta = epoch(a.fetched_at),
    tb = epoch(b.fetched_at);
  return ta > tb || (ta === tb && a.observation_id > b.observation_id);
}
function latestVerdict(chain: Observation[]): Observation | null {
  let latest: Observation | null = null;
  for (const observation of chain)
    if (
      observation.source === "human_review" &&
      (!latest || newerThan(observation, latest))
    )
      latest = observation;
  return latest;
}
/** honored = selected by the engine's selector; superseded = a later verdict exists; not_honored = latest, invalidated. */
export function verdictHonoring(
  chain: Observation[],
  honored: HonoredVerdict | null,
  observation: Observation,
): Honoring {
  const latest = latestVerdict(chain);
  if (!latest || latest.observation_id !== observation.observation_id)
    return "superseded";
  return honored?.observation.observation_id === observation.observation_id
    ? "honored"
    : "not_honored";
}

export interface AlignmentInput {
  window: Pick<
    ParticipationWindow,
    "conflict_flags" | "current_observation_ids"
  >;
  chain: Observation[] | null;
  honored: HonoredVerdict | null;
  derivedAt: string | null;
  reconcilerVersion: string | null;
}
/** Review-overlay alignment only; `reason` explains an unknown. Never chooses a replacement close. */
export function projectionAlignment(input: AlignmentInput): {
  alignment: "confirmed" | "unknown";
  reason?: string;
} {
  const unknown = (reason: string) => ({
    alignment: "unknown" as const,
    reason,
  });
  if (input.chain === null)
    return unknown("the engine chain could not be evaluated");
  if (
    input.reconcilerVersion !== RECONCILER_VERSION ||
    input.derivedAt === null
  )
    return unknown(
      "the projection was not derived by the current reconciler version",
    );
  const newest = Math.max(
    -Infinity,
    ...input.chain.map((o) => epoch(o.fetched_at)),
  );
  if (epoch(input.derivedAt) < newest)
    return unknown("newer observations arrived after the last derivation");
  const human = input.window.conflict_flags.includes("human_resolved");
  const agent = input.window.conflict_flags.includes("agent_resolved");
  const overlay =
    input.honored && input.honored.verdict.kind !== "escalate"
      ? input.honored
      : null;
  if (overlay) {
    const expectedHuman = overlay.verdict.reviewer === "human";
    if (
      !input.window.current_observation_ids.includes(
        overlay.observation.observation_id,
      ) ||
      human !== expectedHuman ||
      agent === expectedHuman
    )
      return unknown(
        "the stored resolution markers do not match the honored verdict",
      );
  } else if (human || agent)
    return unknown(
      "the stored resolution markers do not match the honored verdict",
    );
  return { alignment: "confirmed" };
}

async function explainWindowTool(
  reader: McpReader,
  input: ExplainWindowInput,
  ctx: Ctx,
) {
  const window = await resolveOrFail(reader, input.id);
  const summary = await summarize(reader, window);
  if (
    input.expected_version !== undefined &&
    input.expected_version !== window.version
  )
    throw new ToolFailure(
      "stale_read",
      `The window changed to version ${window.version}. Restart from offset 0 without expected_version or evidence_as_of.`,
      { window: summary },
    );
  const asOf = input.evidence_as_of ?? ctx.readAt;
  if (epoch(asOf) > epoch(ctx.readAt))
    throw new ToolFailure(
      "invalid_input",
      "evidence_as_of cannot be later than the server read time.",
    );
  const baseWarnings = windowWarnings(summary);
  const unavailable = (reason: string) =>
    new ToolFailure(
      "evidence_unavailable",
      `This explanation cannot be produced: ${reason}.`,
      { window: summary },
    );

  if (input.section === "summary") {
    const chain = await engineChain(reader, window.ocd_id);
    const stamp = await reader.getProjectionStamp(window.ocd_id);
    const observations = chain.ok ? chain.observations : null;
    const honored = chain.ok
      ? selectHonoredVerdict(chain.observations, chain.options)
      : null;
    const latest = observations ? latestVerdict(observations) : null;
    const { alignment, reason } = projectionAlignment({
      window,
      chain: observations,
      honored,
      derivedAt: stamp.derivedAt,
      reconcilerVersion: stamp.reconcilerVersion,
    });
    const limits = [
      "No causal rules trace is recorded; this explains stored fields, source close values, flags and verdicts only.",
      "projection_alignment covers only the review overlay, not the whole deadline derivation.",
      "Honoring uses the engine's own selector on the complete primary chain and linked FR amendments at read_at; nothing is re-derived or published.",
    ];
    if (window.conflict_flags.includes("fr_close_amended"))
      limits.push(
        "source_close_values.raw_fr_close_date is the original FR value. A verified FR amendment superseded it.",
      );
    const warnings = [...baseWarnings];
    if (!chain.ok) {
      limits.push(
        `Honoring is unknown because ${chain.reason}; honored_verdict is null for that reason, not because no verdict exists.`,
      );
      warnings.push(`Review honoring is unknown: ${chain.reason}.`);
    } else if (honored?.verdict.kind === "escalate")
      limits.push(
        "The honored verdict is an escalation: it parks the window for review and asserts no deadline.",
      );
    else if (latest && !honored)
      limits.push(
        "The latest review verdict is not honored: newer source evidence supersedes it (see section=verdicts).",
      );
    if (reason) limits.push(`Overlay alignment is unknown: ${reason}.`);
    if (
      input.evidence_as_of !== undefined &&
      input.evidence_as_of !== ctx.readAt
    )
      limits.push(
        "Honoring reflects the chain at read_at, not at evidence_as_of.",
      );
    const referenced = [
      ...new Set([
        ...window.current_observation_ids,
        ...window.provenance.agreeing_observation_ids,
        ...window.provenance.conflicting_observation_ids,
        ...window.change_history.flatMap((entry) => entry.observation_ids),
      ]),
    ];
    try {
      const found = new Set(
        (await reader.readEvidenceByIds(window.ocd_id, referenced)).map(
          (o) => o.observation_id,
        ),
      );
      const missing = referenced.filter((id) => !found.has(id)).length;
      if (missing) {
        limits.push(
          `${missing} referenced observation(s) are not available on this surface.`,
        );
        warnings.push(
          `${missing} referenced observation(s) are not available on this surface.`,
        );
      }
    } catch (error) {
      if (!(error instanceof ZodError) && !(error instanceof McpReadError))
        throw error;
      limits.push(
        "Referenced evidence could not be fully checked (too many references or an unreadable row).",
      );
    }
    const honoredSummary = honored
      ? toVerdictSummary(honored.observation, { honoring: "honored" })
      : null;
    const explain = ExplainSummary.parse({
      window: summary,
      source_close_values: {
        raw_fr_close_date: summary.raw_fr_close_date,
        raw_regs_close_datetime: summary.raw_regs_close_datetime,
      },
      provenance_counts: {
        agreeing: summary.evidence_counts.agreeing,
        conflicting: summary.evidence_counts.conflicting,
      },
      honored_verdict: honoredSummary,
      honoring_as_of: ctx.readAt,
      derived_at: stamp.derivedAt,
      reconciler_version:
        stamp.reconcilerVersion === null
          ? null
          : clip(stamp.reconcilerVersion, 120),
      projection_alignment: alignment,
      causal_trace: "not_recorded",
      explanation_limits: limits.slice(0, 10),
    });
    return ExplainWindowSuccess.parse({
      ...ctx.root,
      data: { section: "summary", window: summary, summary: explain },
      delivery: windowDelivery(ctx, summary, warnings),
      evidence_as_of: asOf,
    });
  }

  const paged = <T>(items: T[], total: number, warnings: string[] = []) =>
    fitPage(items, ctx, (slice, reduced) =>
      ExplainWindowSuccess.parse({
        ...ctx.root,
        data: {
          section: input.section,
          window: summary,
          pagination: { limit: input.limit, offset: input.offset, total },
          next_offset: nextOffset(input.offset, slice.length, total),
          items: slice,
        },
        delivery: windowDelivery(ctx, summary, [
          ...baseWarnings,
          ...warnings,
          ...pagingWarnings(input.offset, slice.length, total, reduced),
        ]),
        evidence_as_of: asOf,
      }),
    );
  const mapped = <T, U>(items: T[], map: (item: T) => U): U[] => {
    try {
      return items.map(map);
    } catch (error) {
      // Inputs were validated canonical records, so a ZodError here is an indivisible bound violation.
      if (error instanceof ZodError)
        throw new ToolFailure(
          "result_too_large",
          "An item exceeds its bounded summary limits and is not shortened. Consult the official citation.",
          { window: summary },
        );
      throw error;
    }
  };

  const directReferences = [
    ...window.current_observation_ids,
    ...window.provenance.agreeing_observation_ids,
    ...window.provenance.conflicting_observation_ids,
  ];
  const historyReferences = window.change_history.flatMap(
    (entry) => entry.observation_ids,
  );
  const requireReferences = async (ids: string[]) => {
    const required = [...new Set(ids)];
    if (!required.length) return;
    try {
      const eligible = new Set(
        (await reader.readEvidenceByIds(window.ocd_id, required))
          .filter(
            (observation) => FederalOcdId.safeParse(observation.ocd_id).success,
          )
          .map((observation) => observation.observation_id),
      );
      if (required.some((id) => !eligible.has(id)))
        throw unavailable(
          "required referenced observations are not available on this federal surface",
        );
    } catch (error) {
      if (error instanceof ZodError || error instanceof McpReadError)
        throw unavailable(
          "required references exceed the bounded read or contain unreadable evidence",
        );
      throw error;
    }
  };
  if (input.section === "observations") {
    await requireReferences([...directReferences, ...historyReferences]);
    const page = await reader.getEvidencePage(window.ocd_id, {
      limit: input.limit,
      offset: input.offset,
      evidenceAsOf: asOf,
    });
    const items = mapped(page.rows, (row) =>
      publicEvidence(row.observation, {
        sourceUrl: evidenceSourceUrl(row.observation),
        relationship: row.relationship,
      }),
    );
    return paged(items, page.total);
  }
  if (input.section === "history") {
    await requireReferences(historyReferences);
    const entries = [...window.change_history].sort(
      (a, b) => a.version - b.version,
    );
    const slice = entries.slice(input.offset, input.offset + input.limit);
    return paged(
      mapped(slice, (entry) => BoundedHistoryEntry.parse(entry)),
      entries.length,
      [
        "History lists prior operative closes and their observation references; it does not reconstruct past display wording.",
      ],
    );
  }

  // verdicts and reviewed-hash references need the complete engine chain.
  const chain = await engineChain(reader, window.ocd_id);
  if (!chain.ok) throw unavailable(chain.reason);
  const verdicts = chain.observations
    .filter(
      (o) => o.source === "human_review" && epoch(o.fetched_at) <= epoch(asOf),
    )
    .sort((a, b) => (newerThan(a, b) ? -1 : newerThan(b, a) ? 1 : 0));
  if (input.section === "verdicts") {
    const honored = selectHonoredVerdict(chain.observations, chain.options);
    const slice = verdicts.slice(input.offset, input.offset + input.limit);
    const items: VerdictSummary[] = mapped(slice, (o) =>
      toVerdictSummary(o, {
        honoring: verdictHonoring(chain.observations, honored, o),
      }),
    );
    return paged(items, verdicts.length, [
      "Honoring is evaluated at read_at against the complete chain. Executors and notes are redacted.",
    ]);
  }
  await requireReferences(directReferences);
  const references = buildReferences(window, verdicts);
  const slice = references.slice(input.offset, input.offset + input.limit);
  return paged(
    mapped(slice, (reference) => Reference.parse(reference)),
    references.length,
  );
}

const REFERENCE_ORDER = [
  "current",
  "agreeing",
  "conflicting",
  "reviewed_hash",
] as const;
/** Evidence handles scoped to this window: kind, then observation ID / payload hash. */
export function buildReferences(
  window: ParticipationWindow,
  verdicts: Observation[],
): Reference[] {
  const references: Reference[] = [];
  const add = (kind: "current" | "agreeing" | "conflicting", ids: string[]) => {
    for (const id of [...new Set(ids)].sort())
      references.push({
        kind,
        observation_id: id,
        payload_hash: null,
        verdict_observation_id: null,
      });
  };
  add("current", window.current_observation_ids);
  add("agreeing", window.provenance.agreeing_observation_ids);
  add("conflicting", window.provenance.conflicting_observation_ids);
  const reviewed: Reference[] = [];
  for (const observation of verdicts) {
    const verdict = HumanReviewVerdict.parse(observation.raw);
    for (const hash of new Set(verdict.reviewed_payload_hashes))
      reviewed.push({
        kind: "reviewed_hash",
        observation_id: null,
        payload_hash: hash,
        verdict_observation_id: observation.observation_id,
      });
  }
  reviewed.sort((a, b) =>
    a.payload_hash! < b.payload_hash!
      ? -1
      : a.payload_hash! > b.payload_hash!
        ? 1
        : a.verdict_observation_id! < b.verdict_observation_id!
          ? -1
          : a.verdict_observation_id! > b.verdict_observation_id!
            ? 1
            : 0,
  );
  references.push(...reviewed);
  return references.sort(
    (a, b) => REFERENCE_ORDER.indexOf(a.kind) - REFERENCE_ORDER.indexOf(b.kind),
  );
}
