/**
 * Defensive structured-field extraction from an Observation's `raw` payload.
 *
 * An Observation (the frozen contract) has NO structured close-date columns — the deadline-bearing
 * fields live INSIDE `raw` (typed `unknown`), verbatim as fetched. The reconcile engine reads them back
 * out here. Both extractors are fully defensive against missing/malformed/null `raw`: every field comes
 * back `null`/typed rather than throwing, so a garbage payload degrades to UNKNOWN, never a crash.
 *
 * FR raw shape (source = "federal_register"): the FR document JSON — comments_close_on (date-only,
 * Eastern, no tz), dates (verbatim legal text), publication_date, document_number, comment_url,
 * docket_ids, regulation_id_numbers (a PLURAL ARRAY — the singular `regulation_id_number` is null on
 * every live FR document; the real RIN(s) live in the array, often empty for Notices/amendments).
 * Regs raw shape (source = "regulations_gov"): the v4 JSON:API document — data.attributes with
 * commentEndDate (ISO+offset), openForComment, withdrawn, allowLateComments, withinCommentPeriod,
 * docketId.
 */

function asObj(v: unknown): Record<string, unknown> | null {
  return v && typeof v === "object" && !Array.isArray(v)
    ? (v as Record<string, unknown>)
    : null;
}
function asStr(v: unknown): string | null {
  return typeof v === "string" && v.length > 0 ? v : null;
}
function asBool(v: unknown): boolean | null {
  return typeof v === "boolean" ? v : null;
}
function asStrArray(v: unknown): string[] {
  return Array.isArray(v)
    ? v.filter((x): x is string => typeof x === "string")
    : [];
}

/**
 * Validate a "YYYY-MM-DD" calendar date as REAL — correct shape AND a date that actually exists.
 * Returns the input string when valid, else null. This rejects out-of-range month/day (2026-13-01,
 * 2026-00-15) AND silent rollover (2026-02-30 -> Mar 2) by constructing the date and requiring its
 * components to round-trip exactly to the input. A bad FR `comments_close_on` is thus treated as ABSENT
 * (null) — the reconcile rulebook then degrades to UNKNOWN rather than throwing or fabricating a date.
 */
function asCalendarDate(v: unknown): string | null {
  const s = asStr(v);
  if (!s) return null;
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
  if (!m) return null;
  const [, y, mo, d] = m;
  const year = Number(y);
  const month = Number(mo);
  const day = Number(d);
  // Construct in UTC and require an exact round-trip — catches both out-of-range and rollover.
  const dt = new Date(Date.UTC(year, month - 1, day));
  if (
    dt.getUTCFullYear() !== year ||
    dt.getUTCMonth() !== month - 1 ||
    dt.getUTCDate() !== day
  )
    return null;
  return s;
}

export interface FrFields {
  commentsCloseOn: string | null; // "YYYY-MM-DD" Eastern date-only (NO timezone)
  datesText: string | null; // verbatim legal DATES language
  title: string | null; // the FR document title (the land-withdrawal signal often lives ONLY here)
  publicationDate: string | null; // "YYYY-MM-DD" (for the govinfo URL)
  documentNumber: string | null;
  commentUrl: string | null;
  docketIds: string[];
  // rin = the PRIMARY RIN (first element of regulation_id_numbers) for the ParticipationWindow.rin
  // contract column. LOSSY-BY-DESIGN: the contract column is a single nullable string, so a multi-RIN
  // doc keeps only its first RIN here. The full set lives in `rins` (consumed by the chain RIN-
  // intersection corroboration, which must not lose multi-RIN docs).
  rin: string | null;
  // rins = the FULL regulation_id_numbers array (FR's real RIN field — plural; often [] for Notices).
  rins: string[];
}

export function extractFr(raw: unknown): FrFields {
  const doc = asObj(raw);
  if (!doc)
    return {
      commentsCloseOn: null,
      datesText: null,
      title: null,
      publicationDate: null,
      documentNumber: null,
      commentUrl: null,
      docketIds: [],
      rin: null,
      rins: [],
    };
  // FR's real RIN field is the PLURAL ARRAY `regulation_id_numbers` (the singular `regulation_id_number`
  // comes back null on every live document). Read the array; the single `rin` projection takes its first
  // element (primary RIN) for the contract column, while `rins` keeps the full set for the chain pass.
  const rins = asStrArray(doc.regulation_id_numbers);
  return {
    commentsCloseOn: asCalendarDate(doc.comments_close_on),
    datesText: asStr(doc.dates),
    title: asStr(doc.title),
    publicationDate: asStr(doc.publication_date),
    documentNumber: asStr(doc.document_number),
    commentUrl: asStr(doc.comment_url),
    docketIds: asStrArray(doc.docket_ids),
    rin: rins.length > 0 ? rins[0]! : null,
    rins,
  };
}

export interface RegsFields {
  commentEndDate: string | null; // ISO-8601 + offset / "…Z"
  openForComment: boolean | null;
  withdrawn: boolean | null;
  allowLateComments: boolean | null;
  withinCommentPeriod: boolean | null;
  docketId: string | null;
}

export function extractRegs(raw: unknown): RegsFields {
  const doc = asObj(raw);
  const data = doc ? asObj(doc.data) : null;
  const attrs = data ? asObj(data.attributes) : null;
  if (!attrs)
    return {
      commentEndDate: null,
      openForComment: null,
      withdrawn: null,
      allowLateComments: null,
      withinCommentPeriod: null,
      docketId: null,
    };
  return {
    commentEndDate: asStr(attrs.commentEndDate),
    openForComment: asBool(attrs.openForComment),
    withdrawn: asBool(attrs.withdrawn),
    allowLateComments: asBool(attrs.allowLateComments),
    withinCommentPeriod: asBool(attrs.withinCommentPeriod),
    docketId: asStr(attrs.docketId),
  };
}
