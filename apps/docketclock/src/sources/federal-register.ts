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

const FR_DOC_URL = (documentNumber: string) =>
  `https://www.federalregister.gov/api/v1/documents/${encodeURIComponent(documentNumber)}.json`;

/** Pins which parser produced the notice-type flags below. Bump when the flag logic changes. */
export const PARSER_VERSION = "fr-v1";

const SOURCE: ObservationSource = "federal_register";

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
