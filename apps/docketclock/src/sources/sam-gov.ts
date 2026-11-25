/**
 * SAM.gov source adapter: the Federal Hierarchy public API (departments and sub-tiers) and the Get
 * Opportunities public API (contract notices with a response deadline). docs/plans/sam-gov.md.
 *
 * Pure parts (URL builders, payload parsers) are exported for tests. The one network function,
 * `samGetJson`, takes the request budget into account BEFORE sending and redacts the key from every error,
 * because SAM.gov takes the key as an `api_key` query parameter, and our HttpStatusError message embeds
 * the URL.
 *
 * Field names below are from the GSA docs (open.gsa.gov/api/fh-public-api, get-opportunities-public-api),
 * not yet checked against a live response. Two facts to confirm with a real key (the plan lists them):
 * the responseDeadLine format, and whether an amended notice comes back with a newer postedDate.
 */
import { Effect } from "effect";
import { runAmbient } from "../ambient.js";
import { httpGetJson, type HttpError } from "./http.js";

export const SAM_PARSER_VERSION = "sam-v1";

/**
 * Requests per UTC day across both SAM APIs. GSA documents 10/day for a non-federal key without a SAM.gov
 * role (1,000/day with a role or a federal account). 9 leaves one request for a manual check. A literal on
 * purpose: raise it here if the key gets a role.
 */
export const SAM_DAILY_REQUEST_CAP = 9;

export const FH_ORGS_URL =
  "https://api.sam.gov/prod/federalorganizations/v1/orgs";
export const OPPORTUNITIES_URL = "https://api.sam.gov/opportunities/v2/search";
/** Page sizes: the documented maximums. */
export const FH_PAGE_SIZE = 100;
export const OPP_PAGE_SIZE = 1000;

/** The key, or null when unset (the SAM pass then skips; it is optional, unlike REGS_API_KEY). */
export function samApiKey(env: NodeJS.ProcessEnv = process.env): string | null {
  const k = (env.SAM_API_KEY ?? "").trim();
  return k ? k : null;
}

export const opportunitySubjectId = (noticeId: string) =>
  `ocd-contract-opportunity/federal/${noticeId}`;
export const federalOrgSubjectId = (fhorgid: string) =>
  `ocd-federal-org/${fhorgid}`;
export const noticeUrl = (noticeId: string) =>
  `https://sam.gov/opp/${noticeId}/view`;

/** "YYYY-MM-DD" → "MM/dd/yyyy" (the Opportunities API's date format). */
export function toSamDate(isoDate: string): string {
  const [y, m, d] = isoDate.split("-");
  return `${m}/${d}/${y}`;
}

export function fhOrgsUrl(p: {
  apiKey: string;
  offset: number;
  updatedFrom?: string; // YYYY-MM-DD
  updatedTo?: string;
}): string {
  const q = new URLSearchParams({
    api_key: p.apiKey,
    limit: String(FH_PAGE_SIZE),
    offset: String(p.offset),
  });
  if (p.updatedFrom) q.set("updateddatefrom", p.updatedFrom);
  if (p.updatedTo) q.set("updateddateto", p.updatedTo);
  return `${FH_ORGS_URL}?${q}`;
}

/**
 * One Opportunities page. `by` picks the window's meaning: "posted" (postedFrom/postedTo, the delta) or
 * "deadline" (rdlfrom/rdlto, the backfill of everything still open). The API requires postedFrom/postedTo
 * on every call, so a deadline query also sends the widest posted window it allows (1 year).
 */
export function opportunitiesUrl(p: {
  apiKey: string;
  offset: number;
  by: "posted" | "deadline";
  from: string; // YYYY-MM-DD
  to: string;
}): string {
  const q = new URLSearchParams({
    api_key: p.apiKey,
    limit: String(OPP_PAGE_SIZE),
    offset: String(p.offset),
  });
  if (p.by === "posted") {
    q.set("postedFrom", toSamDate(p.from));
    q.set("postedTo", toSamDate(p.to));
  } else {
    q.set("postedFrom", toSamDate(addDays(p.to, -364)));
    q.set("postedTo", toSamDate(p.to));
    q.set("rdlfrom", toSamDate(p.from));
    q.set("rdlto", toSamDate(p.to));
  }
  return `${OPPORTUNITIES_URL}?${q}`;
}

export function addDays(isoDate: string, days: number): string {
  const d = new Date(`${isoDate}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

/** Strip the key from anything that might carry a URL (error messages, logs). */
export function redactKey(text: string): string {
  return text.replace(/api_key=[^&\s"']*/gi, "api_key=REDACTED");
}

// ── parsing ─────────────────────────────────────────────────────────────────────────────────────────

const str = (v: unknown): string | null =>
  typeof v === "string" && v.trim() !== ""
    ? v.trim()
    : typeof v === "number"
      ? String(v)
      : null;

/** An ISO-8601 timestamp WITH an explicit offset (or Z) → Date. Anything else → null: we never guess a zone. */
export function parseOffsetInstant(raw: string | null): Date | null {
  if (!raw) return null;
  if (
    !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})$/.test(
      raw,
    )
  )
    return null;
  const d = new Date(raw);
  return Number.isNaN(d.getTime()) ? null : d;
}

/**
 * A SAM wall-clock date ("YYYY-MM-DD", "YYYY-MM-DD HH:MM" or "YYYY-MM-DD HH:MM:SS", no zone) → the instant,
 * read as US Eastern (SAM.gov is an Eastern-time system). Only used for valid-from dates (posted, updated),
 * where a day's precision is what matters; never for a response deadline. An explicit offset wins.
 */
export function parseSamWallClock(raw: string | null): Date | null {
  if (!raw) return null;
  const withOffset = parseOffsetInstant(raw.replace(" ", "T"));
  if (withOffset) return withOffset;
  const m =
    /^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?$/.exec(raw);
  if (!m) return null;
  const [, y, mo, d, h = "00", mi = "00", s = "00"] = m;
  const asUtc = Date.UTC(+y!, +mo! - 1, +d!, +h, +mi, +s);
  return new Date(asUtc - easternOffsetMs(new Date(asUtc)));
}

/** America/New_York's offset from UTC at (about) an instant, in ms (negative: -4h or -5h). DST-correct. */
function easternOffsetMs(at: Date): number {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    hourCycle: "h23",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).formatToParts(at);
  const p = (t: string) => Number(parts.find((x) => x.type === t)?.value);
  const wall = Date.UTC(
    p("year"),
    p("month") - 1,
    p("day"),
    p("hour"),
    p("minute"),
    p("second"),
  );
  return wall - at.getTime();
}

export interface ParsedOpportunity {
  noticeId: string;
  title: string | null;
  solicitationNumber: string | null;
  type: string | null;
  baseType: string | null;
  active: boolean | null;
  postedAt: Date | null;
  responseDeadlineRaw: string | null;
  responseDeadline: Date | null;
  archiveDate: string | null;
  fullParentPathCode: string | null;
  fullParentPathName: string | null;
  naicsCode: string | null;
  setAsideCode: string | null;
}

/** One `opportunitiesData[]` item → the fields the projection keeps. Null when it has no noticeId. */
export function parseOpportunity(item: unknown): ParsedOpportunity | null {
  if (!item || typeof item !== "object") return null;
  const o = item as Record<string, unknown>;
  const noticeId = str(o.noticeId);
  if (!noticeId) return null;
  const rdl = str(o.responseDeadLine);
  const active = str(o.active);
  const archive = str(o.archiveDate);
  return {
    noticeId,
    title: str(o.title),
    solicitationNumber: str(o.solicitationNumber),
    type: str(o.type),
    baseType: str(o.baseType),
    active: active === null ? null : active.toLowerCase() === "yes",
    postedAt: parseSamWallClock(str(o.postedDate)),
    responseDeadlineRaw: rdl,
    responseDeadline: parseOffsetInstant(rdl),
    archiveDate:
      archive && /^\d{4}-\d{2}-\d{2}/.test(archive)
        ? archive.slice(0, 10)
        : null,
    fullParentPathCode: str(o.fullParentPathCode),
    fullParentPathName: str(o.fullParentPathName),
    naicsCode: str(o.naicsCode),
    setAsideCode: str(o.typeOfSetAside) ?? str(o.setAsideCode),
  };
}

export interface ParsedOrg {
  fhorgid: string;
  name: string;
  orgType: string;
  status: string | null;
  parentFhorgid: string | null;
  agencyCode: string | null;
  cgac: string[];
  createdAt: Date | null;
  updatedAt: Date | null;
}

/** One FH `orglist[]` item. Null when it lacks an id, name or type. */
export function parseOrg(item: unknown): ParsedOrg | null {
  if (!item || typeof item !== "object") return null;
  const o = item as Record<string, unknown>;
  const fhorgid = str(o.fhorgid);
  const name = str(o.fhorgname);
  const orgType = str(o.fhorgtype);
  if (!fhorgid || !name || !orgType) return null;
  const dept = str(o.fhdeptindagencyorgid);
  const cgac = Array.isArray(o.cgaclist)
    ? o.cgaclist
        .map((c) => str((c as Record<string, unknown> | null)?.cgac))
        .filter((c): c is string => c !== null)
    : [];
  return {
    fhorgid,
    name,
    orgType,
    status: str(o.status)?.toUpperCase() ?? null,
    parentFhorgid: dept && dept !== fhorgid ? dept : null,
    agencyCode: str(o.agencycode),
    cgac,
    createdAt: parseSamWallClock(str(o.createddate)),
    updatedAt: parseSamWallClock(str(o.lastupdateddate)),
  };
}

/** A page: its items and the total the API reports (FH: totalrecords; Opportunities: totalRecords). */
export function pageOf(
  body: unknown,
  listKey: "orglist" | "opportunitiesData",
) {
  const b = (body ?? {}) as Record<string, unknown>;
  const items = Array.isArray(b[listKey]) ? (b[listKey] as unknown[]) : [];
  const total = Number(b.totalrecords ?? b.totalRecords);
  return { items, total: Number.isFinite(total) ? total : null };
}

// ── network ─────────────────────────────────────────────────────────────────────────────────────────

/** A SAM request failed. `status` is set for an HTTP error; the message never contains the key. */
export class SamRequestError extends Error {
  constructor(
    message: string,
    readonly status: number | null,
  ) {
    super(redactKey(message));
    this.name = "SamRequestError";
  }
}

/**
 * GET one SAM URL as JSON. NO retries: every attempt spends a request from a ~10/day budget, and a 429
 * means the day's budget is gone (the caller stops until the next UTC day). Errors are redacted.
 */
export function samGetJson(url: string): Promise<unknown> {
  return runAmbient(
    httpGetJson(url, { retries: 0, timeoutMs: 60_000 }).pipe(
      Effect.catch((e: HttpError) =>
        Effect.die(
          new SamRequestError(
            e._tag === "HttpStatusError"
              ? e.message
              : `${e._tag}: ${String((e as { cause?: unknown }).cause ?? e)}`,
            e._tag === "HttpStatusError" ? e.status : null,
          ),
        ),
      ),
    ),
  );
}
