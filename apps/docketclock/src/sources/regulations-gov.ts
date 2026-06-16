/**
 * Regulations.gov v4 source adapter — the OPERATIONAL STATUS authority (the second source behind the
 * FR<->Regs reconciliation). FR anchors legal publication; Regs.gov says whether a window is actually
 * open (commentEndDate / openForComment / withinCommentPeriod / withdrawn) and carries frDocNum — the
 * primary join key back to the FR observation.
 *
 * This module is a thin, stateless fetcher + parser plus the load-bearing DIFFERENTIAL-POLLING math.
 * The recurring poll loop itself (scheduling, cursor persistence) is the differential-polling slice;
 * here we provide its safe primitives: the Eastern/UTC cursor lower bound with overlap, and documentId
 * dedupe. The keyed fetch reuses the shared retry-scope helper (http.ts).
 *
 * CRITICAL (docs/architecture/docketclock.md): the v4 `filter[lastModifiedDate]` is interpreted in
 * America/New_York while response `lastModifiedDate` values are UTC. A naive UTC->Eastern cursor would
 * silently MISS documents modified in the offset window. We subtract a 6-hour overlap from the cursor
 * (covers the 4–5h Eastern offset + margin) and dedupe by documentId to drop the re-fetched overlap.
 *
 * Reference: Regs.gov field table in docs/architecture/docketclock.md; api key passed as X-Api-Key.
 */
import { makeOcdId, type ObservationSource } from "@yokel/contracts";
import { fetchJsonWithRetry, type FetchOpts } from "./http.js";
import { payloadHash } from "./payload.js";
import { noticeFlags } from "./notice-flags.js";
import {
  ObservationCandidateSchema,
  type ObservationCandidate,
} from "./observation-candidate.js";

/** Pins which parser produced the notice-type flags below. Bump when the flag logic changes. */
export const PARSER_VERSION = "regs-v1";

const SOURCE: ObservationSource = "regulations_gov";

/** Default v4 base. Overridable (e.g. api.data.gov, or a mock) via REGS_API_BASE. */
const DEFAULT_BASE = "https://api.regulations.gov/v4";

/** Hours of overlap subtracted from the cursor to cover the Eastern-filter / UTC-response skew. */
export const CURSOR_OVERLAP_HOURS = 6;

/** Resolve the Regs.gov API key or fail loudly — a silent default would mask a misconfig. */
export function regsApiKey(): string {
  const key = process.env.REGS_API_KEY;
  if (!key) throw new Error("REGS_API_KEY is not set");
  return key;
}

function regsBase(): string {
  return process.env.REGS_API_BASE || DEFAULT_BASE;
}

export interface RegsFetchOpts extends FetchOpts {
  /** the api.regulations.gov key; defaults to regsApiKey() (process.env.REGS_API_KEY). */
  apiKey?: string;
  base?: string;
}

function withKey(opts: RegsFetchOpts): FetchOpts {
  const apiKey = opts.apiKey ?? regsApiKey();
  return {
    retries: opts.retries,
    timeoutMs: opts.timeoutMs,
    headers: { ...opts.headers, "X-Api-Key": apiKey },
  };
}

/**
 * Format a UTC instant as an America/New_York wall-clock "YYYY-MM-DD HH:MM:SS" string — the zone the
 * v4 lastModifiedDate filter expects. DST-correct (Intl resolves the offset for the date).
 */
export function formatEastern(instant: Date): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/New_York",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).formatToParts(instant);
  const p = (t: string) => parts.find((x) => x.type === t)?.value ?? "";
  // en-CA can emit "24" for midnight hour; normalize to "00".
  const hour = p("hour") === "24" ? "00" : p("hour");
  return `${p("year")}-${p("month")}-${p("day")} ${hour}:${p("minute")}:${p("second")}`;
}

/**
 * The lower bound for the next differential poll: the cursor (max lastModifiedDate seen, a UTC ISO
 * instant) shifted back by the overlap and rendered in Eastern wall-clock for the v4 filter. This is
 * the silent-miss guard — never query from the bare cursor.
 */
export function easternCursorLowerBound(
  sinceUtcIso: string,
  overlapHours: number = CURSOR_OVERLAP_HOURS,
): string {
  const since = new Date(sinceUtcIso);
  if (Number.isNaN(since.getTime()))
    throw new Error(`easternCursorLowerBound: invalid cursor "${sinceUtcIso}"`);
  return formatEastern(new Date(since.getTime() - overlapHours * 3_600_000));
}

export interface RegsListItem {
  documentId: string;
  lastModifiedDate: string | null;
}

/** A v4 list page (data[] of {id, attributes}). Minimal shape — detail fetch carries the full record. */
interface RegsListShape {
  data?: Array<{
    id?: string | null;
    attributes?: { lastModifiedDate?: string | null } | null;
  } | null>;
}

/**
 * Dedupe list items by documentId, keeping the row with the LATEST lastModifiedDate. The 6h cursor
 * overlap deliberately re-fetches the boundary window; this drops the duplicates it produces so each
 * changed document is fetched-in-detail/ingested at most once per poll.
 *
 * "Latest" uses a string compare, which is chronological ONLY because v4 emits UTC second-precision
 * "…Z" timestamps (lexicographic == chronological for that fixed format). If Regs ever returns
 * offset-bearing timestamps this must switch to Date comparison.
 */
export function dedupeByDocumentId(items: RegsListItem[]): RegsListItem[] {
  const latest = new Map<string, RegsListItem>();
  for (const item of items) {
    if (!item.documentId) continue;
    const prev = latest.get(item.documentId);
    if (
      !prev ||
      (item.lastModifiedDate ?? "") > (prev.lastModifiedDate ?? "")
    ) {
      latest.set(item.documentId, item);
    }
  }
  return [...latest.values()];
}

/** Build a v4 /documents list URL for the differential poll (withinCommentPeriod + cursor lower bound). */
export function regsListUrl(opts: {
  sinceUtcIso?: string;
  pageSize?: number;
  pageNumber?: number;
  base?: string;
}): string {
  const base = opts.base ?? regsBase();
  const params = new URLSearchParams();
  // NOTE(poll-loop, issue #18): this filter discovers OPEN windows, but a window that just got
  // withdrawn flips withinCommentPeriod -> false and drops out of the list — so the poll loop must
  // separately re-poll the detail of windows it has seen open to observe the withdrawn-vs-open
  // transition (a marquee CONFLICTING signal). The bare list filter alone will silently miss it.
  params.set("filter[withinCommentPeriod]", "true");
  if (opts.sinceUtcIso) {
    params.set(
      "filter[lastModifiedDate][ge]",
      easternCursorLowerBound(opts.sinceUtcIso),
    );
  }
  params.set("sort", "lastModifiedDate");
  params.set("page[size]", String(opts.pageSize ?? 250));
  params.set("page[number]", String(opts.pageNumber ?? 1));
  return `${base}/documents?${params.toString()}`;
}

/** Fetch one page of changed open-comment documents (ids + lastModifiedDate), deduped by documentId. */
export async function listChangedDocuments(
  opts: {
    sinceUtcIso?: string;
    pageSize?: number;
    pageNumber?: number;
  } & RegsFetchOpts = {},
): Promise<RegsListItem[]> {
  const url = regsListUrl(opts);
  const raw = (await fetchJsonWithRetry(
    url,
    withKey({ ...opts, base: undefined }),
  )) as RegsListShape;
  const items: RegsListItem[] = (raw.data ?? [])
    .filter((d): d is NonNullable<typeof d> => !!d && !!d.id)
    .map((d) => ({
      documentId: d.id as string,
      lastModifiedDate: d.attributes?.lastModifiedDate ?? null,
    }));
  return dedupeByDocumentId(items);
}

/** GET a single Regs.gov document (detail) as JSON. A 404 for an unknown documentId fails fast. */
export async function fetchRegsDocument(
  documentId: string,
  opts: RegsFetchOpts = {},
): Promise<unknown> {
  if (!documentId) throw new Error("fetchRegsDocument requires a document id");
  const base = opts.base ?? regsBase();
  const url = `${base}/documents/${encodeURIComponent(documentId)}`;
  return fetchJsonWithRetry(url, withKey(opts));
}

interface RegsDocAttributes {
  frDocNum?: string | null;
  objectId?: string | null;
  docketId?: string | null;
  title?: string | null;
  documentType?: string | null;
  commentEndDate?: string | null;
  openForComment?: boolean | null;
  withinCommentPeriod?: boolean | null;
  withdrawn?: boolean | null;
  // NOTE(cursor-slice): the DETAIL payload's change timestamp is `modifyDate`, NOT `lastModifiedDate`
  // (that field exists only on the LIST response — see RegsListShape). The differential cursor ("max
  // lastModifiedDate seen") must be advanced from the LIST item, never read off a detail payload, or it
  // will silently read undefined and never advance. Intentionally NOT declared here so no one tries.
}
interface RegsDocShape {
  data?: {
    id?: string | null;
    attributes?: RegsDocAttributes | null;
  } | null;
}

function str(v: unknown): string | null {
  return typeof v === "string" && v.length > 0 ? v : null;
}

/**
 * Map a raw Regs.gov v4 document-detail JSON into a validated Observation candidate.
 *
 * Identity mapping (docs/architecture/docketclock.md): the JSON:API `data.id` IS the Regs DOCUMENT id
 * (-> regs_document_id, the FR<->Regs join column). attributes.objectId is the comment-association key
 * (-> regs_object_id). attributes.frDocNum is the primary join back to FR. The OCD-ID is minted from
 * frDocNum when present, so a Regs observation lands on the SAME ocd_id as its FR counterpart; absent
 * an frDocNum we fall back to regs:{objectId}. Throws if neither is present (cannot mint a stable id).
 *
 * withdrawn=true is the AUTHORITATIVE operational withdrawal signal (OR'd with a title-keyword pass).
 * Regs.gov has no verbatim DATES blob (that legal text is FR's), so raw_dates_text stays null.
 */
export function parseRegsObservation(raw: unknown): ObservationCandidate {
  if (!raw || typeof raw !== "object")
    throw new Error("parseRegsObservation: raw is not an object");
  const doc = (raw as RegsDocShape).data ?? null;
  if (!doc) throw new Error("parseRegsObservation: missing data envelope");

  const regsDocumentId = str(doc.id);
  if (!regsDocumentId)
    throw new Error("parseRegsObservation: document has no id (documentId)");

  const attrs = doc.attributes ?? {};
  const frDocNum = str(attrs.frDocNum);
  const regsObjectId = str(attrs.objectId);
  if (!frDocNum && !regsObjectId)
    throw new Error(
      `parseRegsObservation: ${regsDocumentId} has neither frDocNum nor objectId — cannot mint an OCD-ID`,
    );

  const haystack = [attrs.title, attrs.documentType]
    .map((s) => str(s) ?? "")
    .join(" \n ");
  const flags = noticeFlags(haystack);

  const candidate: ObservationCandidate = {
    ocd_id: makeOcdId({
      frDocNum: frDocNum ?? undefined,
      regsObjectId: regsObjectId ?? undefined,
    }),
    source: SOURCE,
    fr_document_number: frDocNum,
    regs_document_id: regsDocumentId,
    regs_object_id: regsObjectId,
    payload_hash: payloadHash(raw),
    fetched_at: new Date().toISOString(),
    parser_version: PARSER_VERSION,
    raw_dates_text: null, // Regs.gov carries structured dates, not FR's verbatim legal DATES text
    is_extension: flags.is_extension,
    is_correction: flags.is_correction,
    is_withdrawal: flags.is_withdrawal || attrs.withdrawn === true,
    raw,
  };

  const parsed = ObservationCandidateSchema.safeParse(candidate);
  if (!parsed.success) {
    throw new Error(
      `parseRegsObservation: candidate failed Observation validation: ${JSON.stringify(parsed.error.issues)}`,
    );
  }
  return candidate;
}
