/**
 * Federal Register source adapter — the discovery spine + legal-publication anchor.
 *
 * Fetches a single FR document from the keyless public API and maps it into an append-only
 * Observation candidate (the shape the ingest path inserts into the log). The FR `dates` text is the
 * legally-authoritative DATES language and is retained VERBATIM (never reformatted). Notice-type flags
 * are a minimal regex first pass (shared notice-flags.ts; the RuleBox deny-list + Haiku escalation
 * land later).
 *
 * Reference: docs/architecture/docketclock.md (FR field table). The contract this produces lives in
 * @yokel/contracts (Observation). Retry scope + payload hashing are shared across adapters (http.ts,
 * payload.ts).
 */
import { makeOcdId, type ObservationSource } from "@yokel/contracts";
import { fetchJsonWithRetry, type FetchOpts } from "./http.js";
import { payloadHash } from "./payload.js";
import { noticeFlags } from "./notice-flags.js";
import {
  ObservationCandidateSchema,
  type ObservationCandidate,
} from "./observation-candidate.js";

/** Default FR v1 base. Overridable (e.g. a mock) via FR_API_BASE — mirrors REGS_API_BASE. */
const DEFAULT_BASE = "https://www.federalregister.gov/api/v1";

function frBase(): string {
  return process.env.FR_API_BASE || DEFAULT_BASE;
}

const FR_DOC_URL = (documentNumber: string) =>
  `${frBase()}/documents/${encodeURIComponent(documentNumber)}.json`;

/** Pins which parser produced the notice-type flags below. Bump when the flag logic changes. */
export const PARSER_VERSION = "fr-v1";

const SOURCE: ObservationSource = "federal_register";

/**
 * TODAY in America/New_York as a date-only `YYYY-MM-DD` string. The FR `comment_date` filter is
 * date-granular and interpreted in Eastern (the legal-publication zone), so "currently open" means
 * comment_date >= the Eastern calendar date — NOT a UTC instant (a naive UTC date would be wrong for
 * up to 5 hours each night). Mirrors the en-CA date formatter idiom in the FR smoke's todayEastern().
 * (Distinct from regulations-gov.ts formatEastern, which is a wall-clock DATETIME for the v4 filter.)
 */
export function todayEastern(now: Date = new Date()): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/New_York",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(now);
}

/**
 * The Eastern calendar date `lookbackDays` days BEFORE `now`, as `YYYY-MM-DD`. Used as the keyword
 * discovery's publication_date LOWER BOUND (the trailing window for amendment-notice discovery — see
 * frKeywordListUrl). Subtracts whole days in UTC then formats in Eastern; day-granularity makes the
 * exact instant immaterial (the FR publication_date filter is date-granular). Distinct from todayEastern
 * only by the day offset.
 */
export function easternDateDaysAgo(
  lookbackDays: number,
  now: Date = new Date(),
): string {
  const shifted = new Date(now.getTime() - lookbackDays * 86_400_000);
  return todayEastern(shifted);
}

// Re-exported for back-compat with importers that reach for these via the FR adapter.
export { payloadHash } from "./payload.js";
export type { ObservationCandidate } from "./observation-candidate.js";
export type { FetchOpts } from "./http.js";

/**
 * GET an FR document as JSON, with exponential backoff on RETRIABLE failures only (network/429/5xx).
 * A 404/422 fails fast (FR returns 404 for an unknown document number). See http.ts for the scope.
 */
export async function fetchFrDocument(
  documentNumber: string,
  opts: FetchOpts = {},
): Promise<unknown> {
  if (!documentNumber)
    throw new Error("fetchFrDocument requires a document number");
  return fetchJsonWithRetry(FR_DOC_URL(documentNumber), opts);
}

interface FrRegsInfo {
  document_id?: string | null;
  object_id?: string | null;
}
interface FrDocShape {
  document_number?: string | null;
  title?: string | null;
  type?: string | null;
  action?: string | null;
  dates?: string | null;
  regulations_dot_gov_info?: FrRegsInfo | null;
}

function str(v: unknown): string | null {
  return typeof v === "string" && v.length > 0 ? v : null;
}

/**
 * Map a raw FR document JSON into a validated Observation candidate. Throws if the document number is
 * absent (it is the primary OCD-ID minting input) or if the result does not satisfy the frozen
 * Observation contract.
 */
export function parseFrObservation(raw: unknown): ObservationCandidate {
  if (!raw || typeof raw !== "object")
    throw new Error("parseFrObservation: raw is not an object");
  const doc = raw as FrDocShape;

  const frDocNum = str(doc.document_number);
  if (!frDocNum)
    throw new Error("parseFrObservation: FR document has no document_number");

  // FR's regulations_dot_gov_info.document_id is a Regulations.gov DOCUMENT id (e.g.
  // "EPA-HQ-OW-2024-0454-0022") — it belongs in regs_document_id, the field the FR<->Regs reconciler
  // joins on. The Regs.gov internal objectId (a 16-char hex like 0900006484abcd01) is NOT exposed by
  // FR, so regs_object_id stays null unless a record ever carries an explicit object_id.
  const regsInfo = doc.regulations_dot_gov_info ?? null;
  const regsDocumentId = regsInfo ? str(regsInfo.document_id) : null;
  const regsObjectId = regsInfo ? str(regsInfo.object_id) : null;

  const haystack = [doc.title, doc.type, doc.action]
    .map((s) => str(s) ?? "")
    .join(" \n ");

  const candidate: ObservationCandidate = {
    ocd_id: makeOcdId({ frDocNum }),
    source: SOURCE,
    fr_document_number: frDocNum,
    regs_document_id: regsDocumentId,
    regs_object_id: regsObjectId,
    payload_hash: payloadHash(raw),
    fetched_at: new Date().toISOString(),
    parser_version: PARSER_VERSION,
    raw_dates_text: str(doc.dates),
    ...noticeFlags(haystack),
    raw,
  };

  // Prove it satisfies the frozen contract (minus the DB-generated observation_id) at the boundary.
  const parsed = ObservationCandidateSchema.safeParse(candidate);
  if (!parsed.success) {
    throw new Error(
      `parseFrObservation: candidate failed Observation validation: ${JSON.stringify(parsed.error.issues)}`,
    );
  }
  return candidate;
}

/** A single FR list result — the document number to fetch-in-detail + its (immutable) publication date. */
export interface FrListItem {
  documentNumber: string;
  publicationDate: string | null;
}

/** The FR documents.json list response: `{ count, results: [...] }` (FR uses `results`, NOT Regs's `data`). */
interface FrListShape {
  count?: number;
  results?: Array<{
    document_number?: string | null;
    publication_date?: string | null;
  } | null>;
}

/**
 * Dedupe FR list items by documentNumber, keeping the row with the LATEST publicationDate. The open
 * set is paged across multiple requests; this collapses any cross-page duplicate so each document is
 * fetched-in-detail at most once per poll. String compare is chronological for FR's fixed `YYYY-MM-DD`
 * publication_date.
 */
export function dedupeByDocumentNumber(items: FrListItem[]): FrListItem[] {
  const latest = new Map<string, FrListItem>();
  for (const item of items) {
    if (!item.documentNumber) continue;
    const prev = latest.get(item.documentNumber);
    if (!prev || (item.publicationDate ?? "") > (prev.publicationDate ?? "")) {
      latest.set(item.documentNumber, item);
    }
  }
  return [...latest.values()];
}

/**
 * Build an FR documents.json list URL for open-comment discovery — the FULL OPEN SET, no date cursor.
 *
 *   - conditions[comment_date][gte]={commentOpenOnOrAfter}: the caller passes Eastern-today, so the
 *     list is exactly the documents whose comment period is still open (closes today or later). This is
 *     the ONLY discovery filter — there is deliberately NO publication_date cursor (see WHY below).
 *   - order=newest: descending publication_date. NOT load-bearing for correctness — the detail fetch is
 *     by document number, so order never changes which docs we ingest. It only matters IF coverage is
 *     ever truncated at maxPages: newest-first means we keep the MOST RECENT open docs and drop the
 *     oldest tail, the least-bad failure mode (and one the ~1,000-window scale never actually hits).
 *   - per_page (default 1000, FR's max) + page: the paging knobs.
 *   - fields[]=document_number&fields[]=publication_date: the only two fields the list pass needs (the
 *     detail fetch carries the full record).
 *
 * WHY NO publication_date CURSOR (the B1 fix): FR `publication_date` is IMMUTABLE — it is the day the
 * notice was printed and never changes. It is NOT a change-cursor like Regs `lastModifiedDate`. Open
 * comment periods routinely run for MONTHS, so an open doc's publication_date can be far in the past
 * (live FR carries open docs published ~18 months ago). Filtering discovery by
 * conditions[publication_date][gte]={cursor} would list only docs published in the cursor's narrow
 * window and then permanently bury the older open back-catalog (the cursor never reaches them again,
 * because publication_date never moves). So discovery MUST be the full open set each cycle; the
 * differential optimization lives in the caller (skip docs already in the append-only log), keyed on
 * the immutability of FR docs — not on any date.
 *
 * SCALE NOTE: FR enforces page * per_page <= 10,000 (page 11 at per_page=1000 returns HTTP 400). Beyond
 * 10k open docs the list must switch to FR's search_after_cursor; the ~1,000-window design has ~10x
 * headroom today, so that is a deferred scale follow-up, not this slice.
 *
 * NOTE(fr-keyword-discovery, #26): this URL discovers OPEN-comment windows ONLY (the comment_date
 * filter). The keyword path — extension / correction / reopening / WITHDRAWAL notices, which do NOT
 * carry an open comment_date yet must still be ingested so the reconciler can flip an existing window —
 * is DEFERRED to issue #26. It will add a parallel term=/conditions[term]= query here. Not in this slice.
 */
export function frListUrl(opts: {
  commentOpenOnOrAfter: string;
  perPage?: number;
  page?: number;
  base?: string;
}): string {
  const base = opts.base ?? frBase();
  const params = new URLSearchParams();
  params.set("conditions[comment_date][gte]", opts.commentOpenOnOrAfter);
  params.set("order", "newest"); // descending publication_date — keep newest open docs IF ever truncated
  params.set("per_page", String(opts.perPage ?? 1000)); // FR allows up to 1000 per page
  params.set("page", String(opts.page ?? 1));
  params.set("fields[]", "document_number");
  params.append("fields[]", "publication_date");
  return `${base}/documents.json?${params.toString()}`;
}

/**
 * Fetch ONE list page of currently-open FR comment documents (document numbers + publication dates),
 * deduped by documentNumber. FR is KEYLESS (no X-Api-Key); reuses the shared retry-scope fetcher.
 * Mirrors listChangedDocuments. Maps `results[]` (FR's envelope) and guards a missing document_number.
 */
export async function listOpenCommentDocuments(
  opts: {
    commentOpenOnOrAfter: string;
    perPage?: number;
    page?: number;
    base?: string;
  } & FetchOpts,
): Promise<FrListItem[]> {
  const url = frListUrl(opts);
  const raw = (await fetchJsonWithRetry(url, {
    retries: opts.retries,
    timeoutMs: opts.timeoutMs,
    headers: opts.headers,
  })) as FrListShape;
  const items: FrListItem[] = (raw.results ?? [])
    .filter((r): r is NonNullable<typeof r> => !!r && !!r.document_number)
    .map((r) => ({
      documentNumber: r.document_number as string,
      publicationDate: r.publication_date ?? null,
    }));
  return dedupeByDocumentNumber(items);
}

// ── KEYWORD (AMENDMENT-NOTICE) DISCOVERY (#26) ────────────────────────────────────────────────────────
//
// The amendment vocabulary. An extension / correction / reopening / WITHDRAWAL notice frequently carries
// NO open comment_date of its own (a withdrawal CLOSES a period; a correction may just fix text), so the
// comment_date discovery query above never sees it — yet the #31 chain-reconcile pass must be able to
// chain a withdrawal/extension onto the window it amends, which means the notice must be in the
// append-only log. This keyword path gets those notices ingested through the SAME path.
//
// VERIFIED FR `term` SEMANTICS (live keyless API, 2026-06-17): `conditions[term]=` is a relevance-ranked
// FULL-TEXT search. Whitespace-separated terms NARROW the match (it behaves like AND/phrase proximity,
// NOT OR): single `withdrawal` matches >10k docs, but `extension correction reopening withdrawal`
// matches only 705 — the opposite of what we want. The repeated-array form `conditions[term][]=a&[]=b`
// narrows even harder (an explicit AND). So there is NO single-request OR. To get the UNION of all four
// amendment types we issue ONE single-term query per term and union the document numbers (the caller's
// dedupeByDocumentNumber collapses overlap). The term match is deliberately BROAD/imprecise (it surfaces
// false positives like "land withdrawal"); precision is downstream — noticeFlags' regex + the eventual
// RuleBox, and the differential-by-log skip means we only fetch_NEW docs regardless of recall noise.
export const AMENDMENT_TERMS = [
  "extension",
  "correction",
  "reopening",
  "withdrawal",
] as const;

/**
 * Build an FR documents.json list URL for ONE amendment KEYWORD, bounded to a recent publication-date
 * window. Mirrors frListUrl's order/per_page/page/fields exactly; the ONLY differences are the filter
 * (conditions[term] instead of conditions[comment_date][gte]) and the publication_date LOWER BOUND.
 *
 *   - conditions[term]={term}: a single amendment keyword (the caller issues one URL per term and unions).
 *   - conditions[publication_date][gte]={publicationDateOnOrAfter}: a recent trailing-window LOWER BOUND.
 *
 * WHY a publication_date BOUND HERE — and why it was WRONG for the open-comment set: the open-comment set
 * is the FULL set of currently-open windows, whose publication_date can be ~18 months in the past (a long
 * comment period opened long ago) — bounding it by publication_date would permanently BURY that open
 * back-catalog (see frListUrl's B1 note). The keyword set is the OPPOSITE shape: it is unbounded over ALL
 * of FR history (every "extension"/"correction"/"withdrawal" ever printed). An AMENDMENT notice, however,
 * is published CLOSE IN TIME to the window it amends — within days/weeks, not years — so we only ever need
 * a recent TRAILING window, never the full back-catalog. Bounding by publication_date is therefore both
 * SAFE (we don't miss any amendment relevant to a still-relevant window) and NECESSARY (an unbounded term
 * query would page all of FR history every cycle and blow the FR rate budget + the 10k page ceiling). The
 * differential-by-log skip in the poller then dedupes anything already ingested, so re-listing the same
 * trailing window each cycle costs only a few list pages, not re-fetches.
 */
export function frKeywordListUrl(opts: {
  term: string;
  publicationDateOnOrAfter: string;
  perPage?: number;
  page?: number;
  base?: string;
}): string {
  const base = opts.base ?? frBase();
  const params = new URLSearchParams();
  params.set("conditions[term]", opts.term);
  params.set(
    "conditions[publication_date][gte]",
    opts.publicationDateOnOrAfter,
  );
  params.set("order", "newest"); // descending publication_date — keep newest amendments IF ever truncated
  params.set("per_page", String(opts.perPage ?? 1000)); // FR allows up to 1000 per page
  params.set("page", String(opts.page ?? 1));
  params.set("fields[]", "document_number");
  params.append("fields[]", "publication_date");
  return `${base}/documents.json?${params.toString()}`;
}

/**
 * Fetch ONE keyword list page (one amendment term, one page) → FrListItem[], deduped by documentNumber.
 * Mirrors listOpenCommentDocuments exactly (same `results[]` envelope, same missing-document_number
 * guard, same retry-scope passthrough). FR is KEYLESS. The caller pages this to completion per term and
 * unions across terms + the open-comment set.
 */
export async function listAmendmentDocuments(
  opts: {
    term: string;
    publicationDateOnOrAfter: string;
    perPage?: number;
    page?: number;
    base?: string;
  } & FetchOpts,
): Promise<FrListItem[]> {
  const url = frKeywordListUrl(opts);
  const raw = (await fetchJsonWithRetry(url, {
    retries: opts.retries,
    timeoutMs: opts.timeoutMs,
    headers: opts.headers,
  })) as FrListShape;
  const items: FrListItem[] = (raw.results ?? [])
    .filter((r): r is NonNullable<typeof r> => !!r && !!r.document_number)
    .map((r) => ({
      documentNumber: r.document_number as string,
      publicationDate: r.publication_date ?? null,
    }));
  return dedupeByDocumentNumber(items);
}
