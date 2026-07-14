/**
 * xcheck.test.ts — unit tests for the cross-check's pure logic (xcheck-lib.ts). Runs in CI via
 * `pnpm -r test` (no DB, no network — the parsing/classification rules are the subtlest code in
 * the pass and were previously verified only by hand-run adversary probes). Hand-rolled assert
 * pattern, matching apps/docketclock/test/*.
 */
import {
  type JoinedRow,
  classify,
  easternDate,
  parseTriage,
  sqlLit,
  triageKey,
} from "./xcheck-lib.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}
function throws(fn: () => unknown): boolean {
  try {
    fn();
    return false;
  } catch {
    return true;
  }
}

// ── easternDate ──────────────────────────────────────────────────────────────────────────────────
assert(
  "UTC instant lands on the prior Eastern date (the FR-2018-27875 artifact)",
  easternDate("2026-07-21T03:59:59Z") === "2026-07-20",
);
assert(
  "spring-forward boundary: 04:59:59Z and 03:59:59Z on 03-08 both map to 03-07",
  easternDate("2026-03-08T04:59:59Z") === "2026-03-07" &&
    easternDate("2026-03-08T03:59:59Z") === "2026-03-07",
);
assert(
  "fall-back boundary: 2026-11-01T04:59:59Z and 05:00:00Z both map to 11-01",
  easternDate("2026-11-01T04:59:59Z") === "2026-11-01" &&
    easternDate("2026-11-01T05:00:00Z") === "2026-11-01",
);
assert(
  "explicit positive offset accepted",
  easternDate("2026-07-21T03:59:59+00:00") === "2026-07-20",
);
assert(
  "date-only string REFUSED (machine-TZ-dependent)",
  throws(() => easternDate("2026-05-01")),
);
assert(
  "naive datetime REFUSED (machine-TZ-dependent)",
  throws(() => easternDate("2026-05-01T00:00:00")),
);
assert(
  "garbage REFUSED",
  throws(() => easternDate("not-a-date")) &&
    throws(() => easternDate("2026-99-99T00:00:00Z")),
);

// ── classify ─────────────────────────────────────────────────────────────────────────────────────
const base: JoinedRow = {
  ocd_id: "ocd-participation-window/federal/0000-00000",
  fr_document_number: "0000-00000",
  regs_document_id: "TEST-2026-0001-0001",
  resolved_close_utc: "2026-07-21T03:59:59Z", // Eastern 2026-07-20
  confidence: "high",
  status: "closed",
  derived_at: "2026-07-14T00:00:00Z",
  join_via: "regs_id",
  parquet_doc_ids: "TEST-2026-0001-0001",
  parquet_end_dates: "2026-07-21T03:59:59Z",
  parquet_withdrawn_any: false,
  parquet_modified_max: "2026-07-01T00:00:00Z",
};

assert("same Eastern date → agree", classify(base).category === "agree");
assert(
  "1-UTC-day gap, same Eastern date → agree (never a false mismatch)",
  classify({ ...base, parquet_end_dates: "2026-07-20T23:00:00Z" }).category ===
    "agree",
);
assert(
  "different Eastern date → date_mismatch",
  classify({ ...base, parquet_end_dates: "2026-07-22T03:59:59Z" }).category ===
    "date_mismatch",
);
{
  // Multi-docket: one matched row agrees, one doesn't — MUST be a mismatch ("any row agrees"
  // would hide exactly the drift the pass exists to surface).
  const f = classify({
    ...base,
    parquet_end_dates: "2026-07-21T03:59:59Z||2026-08-06T03:59:59Z",
  });
  assert(
    "internally-split parquet dates → date_mismatch listing both",
    f.category === "date_mismatch" &&
      f.parquetEastern.join("/") === "2026-07-20/2026-08-05",
  );
}
assert(
  "duplicate-instant parquet dates collapse to one → agree",
  classify({
    ...base,
    parquet_end_dates: "2026-07-21T03:59:59Z||2026-07-20T23:59:59-04:00",
  }).category === "agree",
);
assert(
  "withdrawn signal beats date agreement → withdrawn_mismatch",
  classify({ ...base, parquet_withdrawn_any: true }).category ===
    "withdrawn_mismatch",
);
assert(
  "our status withdrawn + mirror withdrawn → NOT flagged",
  classify({ ...base, parquet_withdrawn_any: true, status: "withdrawn" })
    .category === "agree",
);
assert(
  "no parquet dates → parquet_no_close",
  classify({ ...base, parquet_end_dates: null }).category ===
    "parquet_no_close",
);
assert(
  "our close null, mirror has date → we_abstain",
  classify({ ...base, resolved_close_utc: null }).category === "we_abstain",
);
assert(
  "withdrawn check precedes null-close routing",
  classify({
    ...base,
    resolved_close_utc: null,
    parquet_withdrawn_any: true,
  }).category === "withdrawn_mismatch",
);

// ── parseTriage ──────────────────────────────────────────────────────────────────────────────────
const OCD = "ocd-participation-window/federal/2026-99999";
const row = (category: string, triage: string, note: string) =>
  `| ${OCD} | ${category} | 2026-07-20 | 2026-07-21 | closed | low | regs_id | DOC-1 | 2026-07-14T00:00:00Z | 2026-07-10T00:00:00Z | ${triage} | ${note} |`;

{
  const m = parseTriage(row("date_mismatch", "our_bug", "checked live"));
  assert(
    "enum triage + note carried, keyed by (ocd_id, category)",
    m.get(triageKey(OCD, "date_mismatch"))?.triage === "our_bug" &&
      m.get(triageKey(OCD, "date_mismatch"))?.note === "checked live",
  );
  assert(
    "category flip does NOT inherit the old triage",
    m.get(triageKey(OCD, "withdrawn_mismatch")) === undefined,
  );
}
{
  // RB-1: an escaped pipe inside the note must not shift cells and eat the triage.
  const m = parseTriage(
    row("date_mismatch", "bulk_stale", 'title reads "Ryan White \\| Part C"'),
  );
  const got = m.get(triageKey(OCD, "date_mismatch"));
  assert(
    "escaped pipe in note: triage survives, note intact",
    got?.triage === "bulk_stale" &&
      got?.note === 'title reads "Ryan White \\| Part C"',
  );
}
{
  const warnings: string[] = [];
  const m = parseTriage(row("date_mismatch", "our_bugg", ""), (w) =>
    warnings.push(w),
  );
  assert(
    "unrecognized triage NOT carried + loud warning",
    m.get(triageKey(OCD, "date_mismatch")) === undefined &&
      warnings.length === 1 &&
      (warnings[0]?.includes("our_bugg") ?? false),
  );
}
assert(
  "abstention-table rows (non-disagreement category cell) ignored",
  parseTriage(`| ${OCD} | 2026-07-21 | open | low | regs_id | DOC-1 |`).size ===
    0,
);
assert(
  "empty triage + empty note → no entry",
  parseTriage(row("date_mismatch", "", "")).size === 0,
);
assert(
  "note-only rows carry (the note is preserved even before triage is decided)",
  parseTriage(row("withdrawn_mismatch", "", "investigating")).get(
    triageKey(OCD, "withdrawn_mismatch"),
  )?.note === "investigating",
);

// ── sqlLit ───────────────────────────────────────────────────────────────────────────────────────
assert(
  "single quotes doubled for DuckDB literals",
  sqlLit("/tmp/o'reilly/windows.jsonl") === "/tmp/o''reilly/windows.jsonl" &&
    sqlLit("plain") === "plain",
);

console.log(out.join("\n"));
if (failures > 0) {
  console.error(`\n${failures} FAILURE(S)`);
  process.exit(1);
}
console.log("\nALL EXPECTATIONS MET");
