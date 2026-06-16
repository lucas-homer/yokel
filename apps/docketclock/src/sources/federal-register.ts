/**
 * Federal Register source adapter — the discovery spine + legal-publication anchor.
 *
 * Fetches a single FR document from the keyless public API and maps it into an append-only
 * Observation candidate (the shape the ingest path inserts into the log). The FR `dates` text is the
 * legally-authoritative DATES language and is retained VERBATIM (never reformatted). Notice-type flags
 * are a minimal regex first pass; the RuleBox deny-list (BLM 2023-27468 false-positive guard) and the
 * Haiku escalation for genuinely-ambiguous titles belong here later (see TODO below).
 *
 * Reference: docs/architecture/docketclock.md (FR field table); spikes/src/_shared.ts (fetch-with-retry
 * shape). The contract this produces lives in @yokel/contracts (Observation).
 */
import { createHash } from "node:crypto";
import {
  Observation,
  makeOcdId,
  type ObservationSource,
} from "@yokel/contracts";

const FR_DOC_URL = (documentNumber: string) =>
  `https://www.federalregister.gov/api/v1/documents/${encodeURIComponent(documentNumber)}.json`;

/** Pins which parser produced the notice-type flags below. Bump when the flag logic changes. */
export const PARSER_VERSION = "fr-v1";

const SOURCE: ObservationSource = "federal_register";

/**
 * The Observation candidate the ingest path inserts — the full Observation shape MINUS the
 * observation_id (the DB generates that via gen_random_uuid()).
 */
export type ObservationCandidate = Omit<Observation, "observation_id">;

/** The Observation schema minus the DB-generated id — what a candidate must validate against. */
const ObservationCandidateSchema = Observation.omit({ observation_id: true });

export interface FetchOpts {
  /** retries on network errors / 429 / 5xx only (default 4). 4xx never retries. */
  retries?: number;
  timeoutMs?: number;
}

const sleep = (ms: number): Promise<void> =>
  new Promise((r) => setTimeout(r, ms));

/**
 * GET an FR document as JSON, with exponential backoff on RETRIABLE failures only.
 *
 * CRITICAL (memory: fetch-retry-scope-gotcha): the non-retriable-status throw lives OUTSIDE the
 * try/catch that handles network errors. Only `await fetch()` is wrapped — so a 404/422 (FR returns
 * 404 for an unknown document number) throws IMMEDIATELY instead of being swallowed by the catch and
 * burning every retry with backoff. We retry ONLY network/abort errors, 429, and 5xx.
 */
export async function fetchFrDocument(
  documentNumber: string,
  opts: FetchOpts = {},
): Promise<unknown> {
  if (!documentNumber)
    throw new Error("fetchFrDocument requires a document number");
  const { retries = 4, timeoutMs = 30_000 } = opts;
  const url = FR_DOC_URL(documentNumber);
  let attempt = 0;

  for (;;) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), timeoutMs);

    // Only network/abort failures are caught here (retriable). HTTP-status handling lives OUTSIDE
    // this try, so a non-retriable 4xx throw propagates immediately instead of being retried.
    let res: Response;
    try {
      res = await fetch(url, {
        headers: { Accept: "application/json" },
        signal: ctrl.signal,
      });
    } catch (err) {
      clearTimeout(timer);
      if (attempt >= retries) throw err;
      const backoff = Math.min(30_000, 500 * 2 ** attempt);
      attempt++;
      await sleep(backoff);
      continue;
    }
    clearTimeout(timer);

    if (res.ok) return (await res.json()) as unknown;

    // 4xx (other than 429) is non-retriable — a 404/422 must fail fast, not burn retries.
    const retriable = res.status === 429 || res.status >= 500;
    if (!retriable || attempt >= retries) {
      const body = await res.text().catch(() => "");
      throw new Error(
        `GET ${url} -> ${res.status} ${res.statusText}${body ? `: ${body.slice(0, 300)}` : ""}`,
      );
    }

    // Retriable (429 / 5xx): back off, honoring Retry-After when present.
    const retryAfter = Number(res.headers.get("retry-after"));
    const backoff =
      Number.isFinite(retryAfter) && retryAfter > 0
        ? retryAfter * 1000
        : Math.min(30_000, 500 * 2 ** attempt);
    attempt++;
    await sleep(backoff);
  }
}

/** Stable JSON serialization so the payload hash is canonical across key-ordering. */
function canonicalize(value: unknown): string {
  return JSON.stringify(sortKeys(value));
}
function sortKeys(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortKeys);
  if (value && typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const k of Object.keys(value as Record<string, unknown>).sort()) {
      out[k] = sortKeys((value as Record<string, unknown>)[k]);
    }
    return out;
  }
  return value;
}

/** sha256 hex of the canonical raw JSON — the dedupe + tamper-evidence key on the log. */
export function payloadHash(raw: unknown): string {
  return createHash("sha256").update(canonicalize(raw), "utf8").digest("hex");
}

// Minimal regex flag detection over title + type + action. Kept deliberately simple.
const RE_EXTENSION = /\bextension\b|\bextend(?:ed|ing)?\b|\breopen/i;
const RE_CORRECTION = /\bcorrection\b|\bcorrect(?:ed|ing)?\b/i;
const RE_WITHDRAWAL = /\bwithdraw(?:al|n|ing)?\b/i;

// TODO(rulebox): route these flags through the RuleBox deny-list before trusting them. The BLM
// 2023-27468 "land-withdrawal extension" title is a keyword false-positive (a land withdrawal, NOT a
// comment-period extension/withdrawal) and must be suppressed here; genuinely-ambiguous titles
// escalate to a single Haiku call, not the hot path (docs/architecture/docketclock.md).

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
    is_extension: RE_EXTENSION.test(haystack),
    is_correction: RE_CORRECTION.test(haystack),
    is_withdrawal: RE_WITHDRAWAL.test(haystack),
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
