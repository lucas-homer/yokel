/**
 * xcheck-lib.ts — the PURE logic behind the offline cross-check (see xcheck.ts for the pass
 * itself). Split out so the parsing/classification rules — the subtlest code in the pass — are
 * unit-tested in CI (xcheck.test.ts) without importing the CLI's side effects (network parquet
 * scan, file writes).
 */

/** "YYYY-MM-DD" in America/New_York for a UTC instant string (DST-correct; mirrors the reconcile
 *  engine's easternCalendarDate — duplicated here because spikes never import app code). Requires
 *  an EXPLICIT-OFFSET instant: a date-only or naive string would parse machine-TZ-dependently and
 *  misclassify SILENTLY (adversary #4 — false "agree" included), so it throws instead. Today's
 *  mirror is 100% "…T…Z" (verified over all 525k comment_end_date values); this guard exists for
 *  the day a mirror format regression breaks that. */
export function easternDate(utcIso: string): string {
  if (
    !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})$/.test(
      utcIso,
    )
  )
    throw new Error(
      `easternDate: refusing non-explicit-offset instant "${utcIso}" (naive/date-only strings parse machine-TZ-dependently)`,
    );
  const instant = new Date(utcIso);
  if (Number.isNaN(instant.getTime()))
    throw new Error(`easternDate: invalid instant "${utcIso}"`);
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/New_York",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(instant);
  const p = (t: string) => parts.find((x) => x.type === t)?.value ?? "";
  return `${p("year")}-${p("month")}-${p("day")}`;
}

export interface JoinedRow {
  ocd_id: string;
  fr_document_number: string | null;
  regs_document_id: string | null;
  resolved_close_utc: string | null;
  confidence: string;
  status: string;
  derived_at: string;
  // NULL for windows with no mirror match at all (LEFT JOIN aggregates over zero rows).
  join_via: string | null; // 'regs_id' | 'fr_doc_num' | null
  // aggregated over every matched parquet row (EPA multi-docket: one fr_doc_num, many documents);
  // NULL when unmatched — main() branches on this before calling classify().
  parquet_doc_ids: string | null;
  parquet_end_dates: string | null; // distinct non-null comment_end_date values, '||'-joined
  parquet_withdrawn_any: boolean;
  parquet_modified_max: string | null;
}

export type Category =
  | "agree"
  | "date_mismatch"
  | "withdrawn_mismatch"
  | "we_abstain"
  | "parquet_no_close"
  | "unmatched";

export interface Finding {
  category: Category;
  row: JoinedRow;
  oursEastern: string | null;
  parquetEastern: string[]; // distinct Eastern dates carried by the matched parquet rows
}

export const TRIAGE_ENUM = ["our_bug", "bulk_stale", "source_drift"];

/** The carry-forward key: ocd_id + category. A window whose disagreement CHANGES CATEGORY between
 *  runs (date_mismatch → withdrawn_mismatch is plausible: classify checks status first) is a
 *  materially different, never-reviewed finding — its old triage must NOT silently reattach. */
export function triageKey(ocdId: string, category: string): string {
  return `${ocdId}::${category}`;
}

/** Parse hand-filled triage/note values out of a previous committed diff, keyed by
 *  triageKey(ocd_id, category). Detail rows end `… | <triage> | <note> |`: after splitting on
 *  UNESCAPED pipes (markdown table cells spell a literal pipe `\|` — adversary RB-1: a note
 *  quoting a federal title with a pipe must not shift the cells and eat the triage) the trailing
 *  `|` yields a final '' element, so note is at length-2 and triage at length-3. Triage carries
 *  ONLY when it is a recognized enum value — anything else is warned about loudly instead of
 *  silently perpetuated; the note carries verbatim either way. */
export function parseTriage(
  markdown: string,
  warn: (msg: string) => void = console.warn,
): Map<string, { triage: string; note: string }> {
  const out = new Map<string, { triage: string; note: string }>();
  for (const line of markdown.split("\n")) {
    const cells = line.split(/(?<!\\)\|/).map((c) => c.trim());
    if (cells.length < 5 || !cells[1]?.startsWith("ocd-participation-window/"))
      continue;
    // Only the DISAGREEMENTS table carries triage/note columns; the abstention table's rows share
    // the ocd_id prefix but their trailing cells are join metadata — anchoring on the category
    // cell keeps them from being slurped in as bogus "notes".
    const category = cells[2] ?? "";
    if (!["date_mismatch", "withdrawn_mismatch"].includes(category)) continue;
    const rawTriage = cells[cells.length - 3] ?? "";
    const note = cells[cells.length - 2] ?? "";
    const triage = TRIAGE_ENUM.includes(rawTriage) ? rawTriage : "";
    if (rawTriage && !triage)
      warn(
        `WARN unrecognized triage "${rawTriage}" on ${cells[1]} — NOT carried (fix it by hand: ${TRIAGE_ENUM.join("|")})`,
      );
    if (triage || note)
      out.set(triageKey(cells[1], category), { triage, note });
  }
  return out;
}

export function classify(r: JoinedRow): Finding {
  const parquetDates = [
    ...new Set(
      (r.parquet_end_dates ?? "")
        .split("||")
        .filter((d) => d !== "")
        .map(easternDate),
    ),
  ].sort();
  const oursEastern = r.resolved_close_utc
    ? easternDate(r.resolved_close_utc)
    : null;

  // Status first: the mirror explicitly says withdrawn but our projection doesn't. (The reverse —
  // we say withdrawn, mirror says nothing — is NOT flagged: `withdrawn` is null on 99% of mirror
  // rows, so absence carries no signal. Serialization verified against the live mirror
  // 2026-07-14: `select withdrawn, count(*) group by 1` over all 1.98M rows yields exactly
  // {null, 'false', 'true'} — the bool_or(withdrawn = 'true') aggregation in xcheck.ts matches.)
  if (r.parquet_withdrawn_any && r.status !== "withdrawn")
    return {
      category: "withdrawn_mismatch",
      row: r,
      oursEastern,
      parquetEastern: parquetDates,
    };

  if (parquetDates.length === 0)
    return {
      category: "parquet_no_close",
      row: r,
      oursEastern,
      parquetEastern: [],
    };
  if (oursEastern === null)
    return {
      category: "we_abstain",
      row: r,
      oursEastern,
      parquetEastern: parquetDates,
    };

  // Agreement = every matched parquet row that carries a close lands on OUR Eastern date. A single
  // matched row on a different Eastern date is a disagreement — "any row agrees" would let the
  // multi-docket case hide exactly the drift this pass exists to surface.
  if (parquetDates.length === 1 && parquetDates[0] === oursEastern)
    return {
      category: "agree",
      row: r,
      oursEastern,
      parquetEastern: parquetDates,
    };
  return {
    category: "date_mismatch",
    row: r,
    oursEastern,
    parquetEastern: parquetDates,
  };
}

/** Escape a value for embedding in a single-quoted DuckDB string literal (Copilot #3: a path like
 *  /tmp/o'reilly/windows.jsonl must fail loudly in OUR code or not at all — never as mangled SQL). */
export function sqlLit(value: string): string {
  return value.replace(/'/g, "''");
}
