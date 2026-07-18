/**
 * reconcile.test.ts — proves the deterministic reconciliation rulebook + the derived-projection persist.
 *
 * Two sections, matching regs.test.ts style (hand-rolled assert/rejects, out[] accumulator, failures
 * counter, process.exit; the DB section guarded by a throwaway Postgres):
 *
 *   PURE engine (no DB): drives reconcile() with synthetic Observation arrays built from the real
 *   fixtures (run through parseFrObservation/parseRegsObservation, then `raw` overridden per case). Every
 *   rulebook outcome is covered + contract-validated:
 *     HIGH · MEDIUM(tz_normalization_only) · MEDIUM(single-source) · MEDIUM(allowLateComments→
 *     late_comment_ambiguous) · LOW(null_end_date_open_status) · LOW(FR-only date-only) ·
 *     CONFLICTING(fr_regs_date_mismatch) · CONFLICTING(withdrawn_vs_open, the #18 fixture) · UNKNOWN.
 *   Plus a DST pair (summer EDT + winter EST) and the structural invariant that tz_normalization_only is
 *   NEVER emitted with conflicting (the FR-2018-27875 fix the contract superRefine also enforces).
 *
 *   DB: drop/recreate public, run migrations, assert 0003 applied + both projection tables exist; seed
 *   an FR + Regs observation for one ocd_id, reconcileOcdId, assert the window row + confidence; re-derive
 *   after mutating the Regs close → assert version bumped + change_history appended; assert a
 *   conflict_records row for a seeded conflict and that re-running does NOT duplicate it.
 *
 * Deterministic: a fixed `now` is injected into reconcile() so every stamp is reproducible.
 */
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { ParticipationWindow, type Observation } from "@yokel/contracts";
import { createClient } from "../src/db/client.js";
import { runMigrations } from "../src/db/migrate.js";
import { parseFrObservation } from "../src/sources/federal-register.js";
import { parseRegsObservation } from "../src/sources/regulations-gov.js";
import { ingestObservation } from "../src/ingest/observe.js";
import { RECONCILER_VERSION, reconcile } from "../src/reconcile/reconcile.js";
import {
  easternCalendarDate,
  utcCalendarDate,
  frCloseDateToUtcInstant,
} from "../src/reconcile/eastern-date.js";
import { reconcileOcdId } from "../src/reconcile/persist.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}
async function rejects(name: string, op: () => unknown, re: RegExp) {
  try {
    await op();
    assert(name, false, "did not throw");
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    assert(name, re.test(msg), msg);
  }
}

const HERE = dirname(fileURLToPath(import.meta.url));
const frFixture = JSON.parse(
  await readFile(join(HERE, "fixtures", "fr-2025-02910.json"), "utf8"),
) as Record<string, unknown>;
const regsFixture = JSON.parse(
  await readFile(
    join(HERE, "fixtures", "regs-FAA-2025-5396-0001.json"),
    "utf8",
  ),
) as { data: { id: string; attributes: Record<string, unknown> } };

const NOW = new Date("2026-06-01T00:00:00Z"); // fixed clock for deterministic stamps

let idSeq = 0;
/**
 * Build a synthetic FR Observation for one ocd_id with the given `raw` overrides. The fr fixture is
 * already FR-2025-02910; we override comments_close_on / dates etc per case and force a shared ocd_id so
 * the FR + Regs rows reconcile together.
 */
function frObs(
  ocdId: string,
  rawOverrides: Record<string, unknown>,
  fetchedAt = "2026-05-01T00:00:00Z",
): Observation {
  const raw = { ...frFixture, ...rawOverrides };
  const cand = parseFrObservation(raw);
  return {
    observation_id: `fr-${idSeq++}`,
    ...cand,
    ocd_id: ocdId,
    raw,
    fetched_at: fetchedAt,
  } as Observation;
}

/** Build a synthetic Regs Observation: deep-clone the fixture, overlay attribute overrides, share ocd_id. */
function regsObs(
  ocdId: string,
  attrOverrides: Record<string, unknown>,
  fetchedAt = "2026-05-01T00:00:00Z",
): Observation {
  const raw = JSON.parse(JSON.stringify(regsFixture)) as typeof regsFixture;
  Object.assign(raw.data.attributes, attrOverrides);
  const cand = parseRegsObservation(raw);
  return {
    observation_id: `regs-${idSeq++}`,
    ...cand,
    ocd_id: ocdId,
    raw,
    fetched_at: fetchedAt,
  } as Observation;
}

const OCD = "ocd-participation-window/federal/2025-02910";

function parses(name: string, w: unknown): void {
  const r = ParticipationWindow.safeParse(w);
  assert(
    `${name} — window passes ParticipationWindow.parse`,
    r.success,
    r.success ? "" : JSON.stringify(r.error.issues),
  );
}

// ── EASTERN-DATE PRIMITIVES — DST-correct normalization (model: formatEastern) ────────────────────────
// FR convention: a date-only close resolves to 23:59:59 ET. In summer (EDT, UTC-4) 23:59:59 ET is
// 03:59:59Z the NEXT UTC day; in winter (EST, UTC-5) it's 04:59:59Z the next UTC day.
{
  const summer = frCloseDateToUtcInstant("2026-06-16");
  assert(
    "DST(EDT): 2026-06-16 23:59:59 ET resolves to 2026-06-17T03:59:59Z",
    summer === "2026-06-17T03:59:59.000Z",
    summer,
  );
  assert(
    "DST(EDT): Eastern calendar date round-trips to 2026-06-16",
    easternCalendarDate(new Date(summer)) === "2026-06-16",
    easternCalendarDate(new Date(summer)),
  );
  assert(
    "DST(EDT): UTC calendar date is the NEXT day 2026-06-17 (the tz artifact)",
    utcCalendarDate(new Date(summer)) === "2026-06-17",
    utcCalendarDate(new Date(summer)),
  );
  const winter = frCloseDateToUtcInstant("2026-12-31");
  assert(
    "DST(EST): 2026-12-31 23:59:59 ET resolves to 2027-01-01T04:59:59Z",
    winter === "2027-01-01T04:59:59.000Z",
    winter,
  );
  assert(
    "DST(EST): Eastern calendar date round-trips to 2026-12-31",
    easternCalendarDate(new Date(winter)) === "2026-12-31",
    easternCalendarDate(new Date(winter)),
  );
}

// ── HIGH — realistic 11:59 p.m. ET close: same Eastern date, NEXT UTC day (tz_normalization_only) ─────
// Product-ratified: Eastern-date agreement IS HIGH. A normal 23:59:59 ET close is stored by Regs as the
// NEXT UTC calendar day (the FR-2018-27875 artifact) — still HIGH, carrying tz_normalization_only as an
// INFORMATIONAL marker (the contract superRefine permits it with HIGH; only CONFLICTING forbids it).
{
  // FR Eastern 2026-06-16, Regs commentEndDate 2026-06-17T03:59:59Z (Eastern 06-16, UTC 06-17).
  const fr = frObs(OCD, { comments_close_on: "2026-06-16" });
  const regs = regsObs(OCD, {
    commentEndDate: "2026-06-17T03:59:59Z",
    withdrawn: false,
    openForComment: true,
  });
  const { window, conflict } = reconcile([fr, regs], NOW);
  assert(
    "HIGH(11:59pm ET): confidence high",
    window.confidence === "high",
    window.confidence,
  );
  assert(
    "HIGH(11:59pm ET): flag is exactly [tz_normalization_only]",
    window.conflict_flags.length === 1 &&
      window.conflict_flags[0] === "tz_normalization_only",
    window.conflict_flags.join(","),
  );
  assert("HIGH(11:59pm ET): NO ConflictRecord", conflict === null);
  assert(
    "HIGH(11:59pm ET): same Eastern date but different UTC day",
    window.raw_fr_close_date === "2026-06-16" &&
      window.raw_regs_close_datetime === "2026-06-17T03:59:59Z",
    `${window.raw_fr_close_date} / ${window.raw_regs_close_datetime}`,
  );
  parses("HIGH(11:59pm ET)", window);
}

// ── HIGH — same-UTC-day close (daytime): Eastern agreement, no tz artifact, NO flags ──────────────────
{
  // commentEndDate at noon UTC -> same calendar day in both Eastern and UTC; FR matches it.
  const fr = frObs(OCD, { comments_close_on: "2026-07-15" });
  const regs = regsObs(OCD, {
    commentEndDate: "2026-07-15T12:00:00Z",
    withdrawn: false,
    openForComment: true,
  });
  const { window, conflict } = reconcile([fr, regs], NOW);
  assert(
    "HIGH(same-UTC-day): confidence high",
    window.confidence === "high",
    window.confidence,
  );
  assert(
    "HIGH(same-UTC-day): no conflict_flags",
    window.conflict_flags.length === 0,
    window.conflict_flags.join(","),
  );
  assert("HIGH(same-UTC-day): no ConflictRecord", conflict === null);
  assert(
    "HIGH(same-UTC-day): resolved_close_utc from Regs",
    window.resolved_close_utc === "2026-07-15T12:00:00.000Z",
    String(window.resolved_close_utc),
  );
  parses("HIGH(same-UTC-day)", window);
}

// ── CONFLICTING — fr_regs_date_mismatch (real Eastern-day difference) ─────────────────────────────────
{
  const fr = frObs(OCD, { comments_close_on: "2026-07-01" });
  const regs = regsObs(OCD, {
    commentEndDate: "2026-08-11T03:59:59Z", // Eastern 2026-08-10 — a true >=1 day difference
    withdrawn: false,
    openForComment: true,
  });
  const { window, conflict } = reconcile([fr, regs], NOW);
  assert(
    "MISMATCH: confidence conflicting",
    window.confidence === "conflicting",
    window.confidence,
  );
  assert(
    "MISMATCH: flag is exactly [fr_regs_date_mismatch]",
    window.conflict_flags.length === 1 &&
      window.conflict_flags[0] === "fr_regs_date_mismatch",
    window.conflict_flags.join(","),
  );
  assert("MISMATCH: emits a ConflictRecord", conflict !== null);
  assert(
    "MISMATCH: ConflictRecord names both sources + the flag",
    !!conflict &&
      conflict.source_a === "federal_register" &&
      conflict.source_b === "regulations_gov" &&
      conflict.conflict_flags[0] === "fr_regs_date_mismatch",
  );
  assert(
    "MISMATCH: NEVER also tz_normalization_only",
    !window.conflict_flags.includes("tz_normalization_only"),
  );
  parses("MISMATCH", window);
}

// ── CONFLICTING — withdrawn_vs_open (THE issue #18 fixture) ───────────────────────────────────────────
// EXPLICIT #18 case: Regs marks the notice withdrawn while it otherwise reads open (FR has a close /
// openForComment true). This flag is fully wired + tested here, but PRODUCTION cannot surface it until
// issue #18 lands (the differential poll's withinCommentPeriod=true filter drops a notice the moment it
// is withdrawn, so no withdrawn:true observation reaches the log yet — see the code comment in
// reconcile.ts). This test pins the engine behavior for when that observation CAN arrive.
{
  const fr = frObs(OCD, { comments_close_on: "2026-07-15" });
  const regs = regsObs(OCD, {
    commentEndDate: "2026-07-15T12:00:00Z",
    withdrawn: true, // the withdrawal signal
    openForComment: true, // still reads open => contradiction
  });
  const { window, conflict } = reconcile([fr, regs], NOW);
  assert(
    "#18 WITHDRAWN-VS-OPEN: confidence conflicting",
    window.confidence === "conflicting",
    window.confidence,
  );
  assert(
    "#18 WITHDRAWN-VS-OPEN: flag is exactly [withdrawn_vs_open]",
    window.conflict_flags.length === 1 &&
      window.conflict_flags[0] === "withdrawn_vs_open",
    window.conflict_flags.join(","),
  );
  assert("#18 WITHDRAWN-VS-OPEN: emits a ConflictRecord", conflict !== null);
  assert(
    "#18 WITHDRAWN-VS-OPEN: status is withdrawn",
    window.status === "withdrawn",
    window.status,
  );
  assert(
    "#18 WITHDRAWN-VS-OPEN: NEVER also tz_normalization_only",
    !window.conflict_flags.includes("tz_normalization_only"),
  );
  parses("#18 WITHDRAWN-VS-OPEN", window);
}

// ── MEDIUM — single source (Regs only, no FR observation) ─────────────────────────────────────────────
{
  const regs = regsObs(OCD, {
    commentEndDate: "2026-07-15T12:00:00Z",
    withdrawn: false,
    openForComment: true,
    allowLateComments: false,
  });
  const { window, conflict } = reconcile([regs], NOW);
  assert(
    "SINGLE(Regs): confidence medium",
    window.confidence === "medium",
    window.confidence,
  );
  assert("SINGLE(Regs): no conflict_flags", window.conflict_flags.length === 0);
  assert("SINGLE(Regs): no ConflictRecord", conflict === null);
  assert(
    "SINGLE(Regs): resolved_close from Regs",
    window.resolved_close_utc === "2026-07-15T12:00:00.000Z",
  );
  parses("SINGLE(Regs)", window);
}

// ── MEDIUM — allowLateComments=true → late_comment_ambiguous ──────────────────────────────────────────
{
  const regs = regsObs(OCD, {
    commentEndDate: "2026-07-15T12:00:00Z",
    withdrawn: false,
    openForComment: true,
    allowLateComments: true,
  });
  const { window } = reconcile([regs], NOW);
  assert(
    "LATE-COMMENTS: confidence medium",
    window.confidence === "medium",
    window.confidence,
  );
  assert(
    "LATE-COMMENTS: flag is exactly [late_comment_ambiguous]",
    window.conflict_flags.length === 1 &&
      window.conflict_flags[0] === "late_comment_ambiguous",
    window.conflict_flags.join(","),
  );
  parses("LATE-COMMENTS", window);
}

// ── MEDIUM(tz) — FR/Regs agree on Eastern date, Regs NOT open for comment, UTC day differs ────────────
// Eastern dates agree but Regs openForComment=false degrades HIGH → MEDIUM (the contradiction-free
// agreement is gone). Because the close is the 11:59 p.m. ET artifact (Regs stores it the NEXT UTC day),
// tz_normalization_only ALSO attaches. The contract permits tz_normalization_only with MEDIUM.
{
  // FR Eastern 2026-06-16; Regs 2026-06-17T03:59:59Z = Eastern 06-16 / UTC 06-17 (UTC day differs).
  const fr = frObs(OCD, { comments_close_on: "2026-06-16" });
  const regs = regsObs(OCD, {
    commentEndDate: "2026-06-17T03:59:59Z",
    withdrawn: false,
    openForComment: false, // not open → degrade to MEDIUM
  });
  const { window, conflict } = reconcile([fr, regs], NOW);
  assert(
    "MEDIUM(tz, not-open): confidence medium",
    window.confidence === "medium",
    window.confidence,
  );
  assert(
    "MEDIUM(tz, not-open): flag is exactly [tz_normalization_only]",
    window.conflict_flags.length === 1 &&
      window.conflict_flags[0] === "tz_normalization_only",
    window.conflict_flags.join(","),
  );
  assert("MEDIUM(tz, not-open): no ConflictRecord", conflict === null);
  parses("MEDIUM(tz, not-open)", window);
}

// ── MEDIUM — FR has a date + Regs has NO commentEndDate but allowLateComments=true → late_comment_ambiguous ─
// FR supplies the close; the Regs observation exists but is dateless (no commentEndDate) and NOT open for
// comment (so it does NOT hit the null_end_date_open_status LOW branch, which requires openForComment=true).
// One source with a usable close + a Regs row that allows late comments → MEDIUM + late_comment_ambiguous.
{
  const fr = frObs(OCD, { comments_close_on: "2026-07-20" });
  const regs = regsObs(OCD, {
    commentEndDate: null,
    withdrawn: false,
    openForComment: false, // NOT true → avoids the null_end_date_open_status branch
    allowLateComments: true,
  });
  const { window, conflict } = reconcile([fr, regs], NOW);
  assert(
    "FR+LATE-DATELESS-REGS: confidence medium",
    window.confidence === "medium",
    window.confidence,
  );
  assert(
    "FR+LATE-DATELESS-REGS: conflict_flags includes late_comment_ambiguous",
    window.conflict_flags.includes("late_comment_ambiguous"),
    window.conflict_flags.join(","),
  );
  assert("FR+LATE-DATELESS-REGS: no ConflictRecord", conflict === null);
  assert(
    "FR+LATE-DATELESS-REGS: resolved_close via FR 11:59pm ET",
    window.resolved_close_utc === frCloseDateToUtcInstant("2026-07-20"),
    String(window.resolved_close_utc),
  );
  assert(
    "FR+LATE-DATELESS-REGS: display carries the date + inference note",
    window.resolved_close_display ===
      "closes 2026-07-20 at 11:59 p.m. ET (inferred from FR date-only value)",
    String(window.resolved_close_display),
  );
  parses("FR+LATE-DATELESS-REGS", window);
}

// ── DEGRADE — a rolled-over Regs commentEndDate (2026-02-30 → Mar 2) is treated as ABSENT, not fabricated ─
// Symmetric with the FR asCalendarDate guard: a date that silently rolls over must NEVER become an
// operative close. With NO FR date either, the window degrades to UNKNOWN (null close) — never March.
{
  const fr = frObs(OCD, { comments_close_on: null });
  const regs = regsObs(OCD, {
    commentEndDate: "2026-02-30T00:00:00Z", // rolls over to Mar 2 in a naive parse
    withdrawn: false,
    openForComment: false,
  });
  const { window, conflict } = reconcile([fr, regs], NOW);
  assert(
    "BAD-REGS-DATE: confidence unknown (rolled-over date treated as absent)",
    window.confidence === "unknown",
    window.confidence,
  );
  assert(
    "BAD-REGS-DATE: resolved_close_utc null (no fabricated March date)",
    window.resolved_close_utc === null,
    String(window.resolved_close_utc),
  );
  assert(
    "BAD-REGS-DATE: no rolled-over March date appears anywhere",
    !String(window.resolved_close_utc).startsWith("2026-03"),
    String(window.resolved_close_utc),
  );
  assert("BAD-REGS-DATE: no ConflictRecord", conflict === null);
  parses("BAD-REGS-DATE", window);
}

// ── LOW — null_end_date_open_status (Regs commentEndDate null + openForComment true, FR supplies date) ─
{
  const fr = frObs(OCD, { comments_close_on: "2026-07-20" });
  const regs = regsObs(OCD, {
    commentEndDate: null,
    withdrawn: false,
    openForComment: true,
  });
  const { window, conflict } = reconcile([fr, regs], NOW);
  assert(
    "NULL-END-DATE: confidence low",
    window.confidence === "low",
    window.confidence,
  );
  assert(
    "NULL-END-DATE: flag is exactly [null_end_date_open_status]",
    window.conflict_flags.length === 1 &&
      window.conflict_flags[0] === "null_end_date_open_status",
    window.conflict_flags.join(","),
  );
  assert("NULL-END-DATE: no ConflictRecord", conflict === null);
  assert(
    "NULL-END-DATE: resolved_close non-null (LOW requires it) via FR 11:59pm ET",
    window.resolved_close_utc === frCloseDateToUtcInstant("2026-07-20"),
    String(window.resolved_close_utc),
  );
  assert(
    "NULL-END-DATE: display carries the date + inference note",
    window.resolved_close_display ===
      "closes 2026-07-20 at 11:59 p.m. ET (inferred from FR date-only value)",
    String(window.resolved_close_display),
  );
  parses("NULL-END-DATE", window);
}

// ── LOW — FR-only date-only (no Regs observation at all) ──────────────────────────────────────────────
{
  const fr = frObs(OCD, { comments_close_on: "2026-09-10" });
  const { window, conflict } = reconcile([fr], NOW);
  assert(
    "FR-ONLY: confidence low",
    window.confidence === "low",
    window.confidence,
  );
  assert("FR-ONLY: no conflict_flags", window.conflict_flags.length === 0);
  assert("FR-ONLY: no ConflictRecord", conflict === null);
  assert(
    "FR-ONLY: resolved_close via 11:59pm ET convention",
    window.resolved_close_utc === frCloseDateToUtcInstant("2026-09-10"),
    String(window.resolved_close_utc),
  );
  assert(
    "FR-ONLY: display carries the calendar date AND notes date-only inference",
    window.resolved_close_display ===
      "closes 2026-09-10 at 11:59 p.m. ET (inferred from FR date-only value)",
    String(window.resolved_close_display),
  );
  assert(
    "FR-ONLY: govinfo_url null (fixture has no publication_date)",
    window.govinfo_url === null,
    String(window.govinfo_url),
  );
  parses("FR-ONLY", window);
}

// ── LOW — FR-only with publication_date builds the govinfo legal-reliance URL ─────────────────────────
{
  const fr = frObs(OCD, {
    comments_close_on: "2026-09-10",
    publication_date: "2025-02-14",
    comment_url:
      "https://www.regulations.gov/commenton/EPA-HQ-OW-2024-0454-0022",
  });
  const { window } = reconcile([fr], NOW);
  assert(
    "GOVINFO: url built from FR publication_date + document_number",
    window.govinfo_url ===
      "https://www.govinfo.gov/content/pkg/FR-2025-02-14/html/2025-02910.htm",
    String(window.govinfo_url),
  );
  assert(
    "GOVINFO: submission_url from FR comment_url",
    window.submission_url ===
      "https://www.regulations.gov/commenton/EPA-HQ-OW-2024-0454-0022",
    String(window.submission_url),
  );
  parses("GOVINFO", window);
}

// ── UNKNOWN — both structured deadline fields missing ─────────────────────────────────────────────────
{
  const fr = frObs(OCD, { comments_close_on: null });
  const regs = regsObs(OCD, {
    commentEndDate: null,
    withdrawn: false,
    openForComment: false,
  });
  const { window, conflict } = reconcile([fr, regs], NOW);
  assert(
    "UNKNOWN: confidence unknown",
    window.confidence === "unknown",
    window.confidence,
  );
  assert(
    "UNKNOWN: resolved_close_utc forced null (contract)",
    window.resolved_close_utc === null,
    String(window.resolved_close_utc),
  );
  assert("UNKNOWN: no ConflictRecord", conflict === null);
  parses("UNKNOWN", window);
}

// ── MALFORMED FR DATE — never crash, never roll over (treat as ABSENT → UNKNOWN with Regs absent) ─────
// 2026-13-01 / 2026-00-15 are out-of-range; 2026-02-30 silently rolls over to Mar 2 in a naive parse.
// All three must be treated as ABSENT (null close), and with no Regs date the window degrades to UNKNOWN.
for (const bad of ["2026-13-01", "2026-00-15", "2026-02-30"]) {
  let threw = false;
  let window: ParticipationWindow | null = null;
  try {
    const fr = frObs(OCD, { comments_close_on: bad });
    window = reconcile([fr], NOW).window;
  } catch {
    threw = true;
  }
  assert(`BAD-FR-DATE(${bad}): reconcile does NOT throw`, !threw);
  assert(
    `BAD-FR-DATE(${bad}): confidence unknown (treated as absent)`,
    window?.confidence === "unknown",
    String(window?.confidence),
  );
  assert(
    `BAD-FR-DATE(${bad}): resolved_close_utc null (no fabricated/rolled-over close)`,
    window?.resolved_close_utc === null,
    String(window?.resolved_close_utc),
  );
  // A rollover would surface 2026-03-02/03-03 in the operative close — assert it never appears anywhere.
  assert(
    `BAD-FR-DATE(${bad}): no rolled-over March date appears`,
    !String(window?.resolved_close_utc).startsWith("2026-03"),
    String(window?.resolved_close_utc),
  );
  if (window) parses(`BAD-FR-DATE(${bad})`, window);
}

// ── WITHDRAWN — Regs-ONLY (no FR): NOT a cross-source conflict, status withdrawn, NOT push-eligible ───
{
  // Regs alone, internally contradictory (withdrawn AND openForComment true) — NOT CONFLICTING because
  // there is no OTHER source to disagree with. status=withdrawn, confidence LOW (a close exists), no
  // ConflictRecord.
  const regs = regsObs(OCD, {
    commentEndDate: "2026-07-15T12:00:00Z",
    withdrawn: true,
    openForComment: true,
  });
  const { window, conflict } = reconcile([regs], NOW);
  assert(
    "REGS-ONLY-WITHDRAWN: NOT conflicting",
    window.confidence !== "conflicting",
    window.confidence,
  );
  assert(
    "REGS-ONLY-WITHDRAWN: status withdrawn",
    window.status === "withdrawn",
    window.status,
  );
  assert(
    "REGS-ONLY-WITHDRAWN: confidence low (close exists) — not push-eligible",
    window.confidence === "low",
    window.confidence,
  );
  assert("REGS-ONLY-WITHDRAWN: NO ConflictRecord", conflict === null);
  assert(
    "REGS-ONLY-WITHDRAWN: resolved_close non-null (LOW requires it)",
    window.resolved_close_utc === "2026-07-15T12:00:00.000Z",
    String(window.resolved_close_utc),
  );
  parses("REGS-ONLY-WITHDRAWN", window);
}

// ── WITHDRAWN — Regs-ONLY with NO date anywhere → UNKNOWN (null close), still status withdrawn ────────
{
  const regs = regsObs(OCD, {
    commentEndDate: null,
    withdrawn: true,
    openForComment: false,
  });
  const { window, conflict } = reconcile([regs], NOW);
  assert(
    "REGS-ONLY-WITHDRAWN(no date): confidence unknown",
    window.confidence === "unknown",
    window.confidence,
  );
  assert(
    "REGS-ONLY-WITHDRAWN(no date): status withdrawn",
    window.status === "withdrawn",
    window.status,
  );
  assert(
    "REGS-ONLY-WITHDRAWN(no date): resolved_close null",
    window.resolved_close_utc === null,
    String(window.resolved_close_utc),
  );
  assert("REGS-ONLY-WITHDRAWN(no date): NO ConflictRecord", conflict === null);
  parses("REGS-ONLY-WITHDRAWN(no date)", window);
}

// ── INVARIANT — every CONFLICTING window emits a non-null ConflictRecord (suppression is never silence) ─
{
  const conflictingCases: Observation[][] = [
    // fr_regs_date_mismatch (true Eastern-day difference)
    [
      frObs(OCD, { comments_close_on: "2026-07-01" }),
      regsObs(OCD, {
        commentEndDate: "2026-08-11T03:59:59Z",
        withdrawn: false,
        openForComment: true,
      }),
    ],
    // cross-source withdrawn_vs_open (FR open + Regs withdrawn)
    [
      frObs(OCD, { comments_close_on: "2026-07-15" }),
      regsObs(OCD, {
        commentEndDate: "2026-07-15T12:00:00Z",
        withdrawn: true,
        openForComment: true,
      }),
    ],
  ];
  let allEmit = true;
  for (const obs of conflictingCases) {
    const { window, conflict } = reconcile(obs, NOW);
    if (window.confidence === "conflicting" && conflict === null)
      allEmit = false;
  }
  assert(
    "CONFLICT-INVARIANT: every CONFLICTING window emits a non-null ConflictRecord",
    allEmit,
  );
}

// ── STRUCTURAL INVARIANT — tz_normalization_only is NEVER emitted with conflicting ────────────────────
// Sweep representative inputs; the engine + contract superRefine both forbid the pairing.
{
  const cases: Observation[][] = [
    [
      frObs(OCD, { comments_close_on: "2026-06-16" }),
      regsObs(OCD, {}), // tz-only
    ],
    [
      frObs(OCD, { comments_close_on: "2026-07-01" }),
      regsObs(OCD, { commentEndDate: "2026-08-11T03:59:59Z" }), // mismatch
    ],
    [
      frObs(OCD, { comments_close_on: "2026-07-15" }),
      regsObs(OCD, {
        commentEndDate: "2026-07-15T12:00:00Z",
        withdrawn: true,
        openForComment: true,
      }), // withdrawn-vs-open
    ],
  ];
  let everPaired = false;
  for (const obs of cases) {
    const { window } = reconcile(obs, NOW);
    if (
      window.confidence === "conflicting" &&
      window.conflict_flags.includes("tz_normalization_only")
    )
      everPaired = true;
  }
  assert(
    "INVARIANT: tz_normalization_only NEVER co-occurs with conflicting",
    everPaired === false,
  );
}

// ── GUARD — mixed ocd_ids throw ───────────────────────────────────────────────────────────────────────
await rejects(
  "reconcile throws on observations spanning multiple ocd_ids",
  () =>
    reconcile(
      [
        frObs(OCD, { comments_close_on: "2026-07-15" }),
        frObs("ocd-participation-window/federal/2025-99999", {
          comments_close_on: "2026-07-15",
        }),
      ],
      NOW,
    ),
  /multiple ocd_ids/,
);
await rejects(
  "reconcile throws on an empty observation array",
  () => reconcile([], NOW),
  /no observations/,
);

// ── DB — derived projections + version bump + conflict dedupe ─────────────────────────────────────────
const sql = createClient();
try {
  await sql.unsafe(
    "drop schema if exists public cascade; create schema public;",
  );
  const applied = await runMigrations(sql);
  assert(
    "migration 0003 applies (participation windows)",
    applied.includes("0003_participation_windows.sql"),
    applied.join(", "),
  );
  const tables = await sql<{ tablename: string }[]>`
    select tablename from pg_tables
    where tablename in ('participation_windows', 'conflict_records')
    order by tablename
  `;
  assert(
    "both projection tables exist",
    tables.length === 2 &&
      tables[0]!.tablename === "conflict_records" &&
      tables[1]!.tablename === "participation_windows",
    tables.map((t) => t.tablename).join(", "),
  );

  // Seed an FR + a Regs observation for ONE ocd_id (tz-normalization agreement → HIGH window w/ marker).
  const frRaw = { ...frFixture, comments_close_on: "2026-06-16" };
  const frCand = parseFrObservation(frRaw);
  await ingestObservation(sql, frCand);

  const regsRaw = JSON.parse(JSON.stringify(regsFixture)) as typeof regsFixture;
  // Force the Regs frDocNum to match the FR fixture so they share the OCD-ID; close agrees in Eastern.
  regsRaw.data.attributes.frDocNum = "2025-02910";
  regsRaw.data.attributes.commentEndDate = "2026-06-17T03:59:59Z";
  const regsCand = parseRegsObservation(regsRaw);
  await ingestObservation(sql, regsCand);

  const r1 = await reconcileOcdId(sql, OCD, NOW);
  assert(
    "reconcileOcdId derives a HIGH window with the tz_normalization_only marker",
    r1.window.confidence === "high" &&
      r1.window.conflict_flags.includes("tz_normalization_only"),
    `${r1.window.confidence} [${r1.window.conflict_flags.join(",")}]`,
  );
  assert("reconcileOcdId reports a first insert", r1.persist.inserted === true);
  assert(
    "first derive does NOT bump version",
    r1.persist.versionBumped === false,
  );

  const [row1] = await sql<
    { confidence: string; version: number; resolved_close_utc: Date | null }[]
  >`
    select confidence, version, resolved_close_utc from participation_windows where ocd_id = ${OCD}
  `;
  assert(
    "window row persisted with HIGH confidence",
    row1?.confidence === "high",
  );
  assert(
    "window row persisted at version 0",
    row1?.version === 0,
    String(row1?.version),
  );

  // The operational reconciler_version column (NOT a contract field) records which rulebook derived it.
  const [verRow] = await sql<{ reconciler_version: string }[]>`
    select reconciler_version from participation_windows where ocd_id = ${OCD}
  `;
  assert(
    "persisted window carries the current RECONCILER_VERSION",
    verRow?.reconciler_version === RECONCILER_VERSION,
    String(verRow?.reconciler_version),
  );

  // Re-derive with the SAME data → idempotent, no version bump.
  const rSame = await reconcileOcdId(sql, OCD, NOW);
  assert(
    "idempotent re-derive does not bump version",
    rSame.persist.versionBumped === false,
  );
  const [rowSame] = await sql<{ version: number }[]>`
    select version from participation_windows where ocd_id = ${OCD}
  `;
  assert(
    "version still 0 after idempotent re-derive",
    rowSame?.version === 0,
    String(rowSame?.version),
  );

  // Mutate the Regs close (append a new observation) → re-derive bumps version + appends change_history.
  const regsRaw2 = JSON.parse(JSON.stringify(regsRaw)) as typeof regsRaw;
  regsRaw2.data.attributes.commentEndDate = "2026-06-20T03:59:59Z"; // moves the close
  await ingestObservation(sql, parseRegsObservation(regsRaw2));

  const r2 = await reconcileOcdId(sql, OCD, new Date("2026-06-02T00:00:00Z"));
  assert(
    "re-derive after a moved close bumps version",
    r2.persist.versionBumped === true,
  );
  const [row2] = await sql<
    { version: number; change_history: unknown[]; resolved_close_utc: Date }[]
  >`
    select version, change_history, resolved_close_utc from participation_windows where ocd_id = ${OCD}
  `;
  assert("version bumped to 1", row2?.version === 1, String(row2?.version));
  assert(
    "change_history has one prior entry",
    Array.isArray(row2?.change_history) && row2!.change_history.length === 1,
    String(row2?.change_history?.length),
  );
  const prior = row2!.change_history[0] as {
    version: number;
    resolved_close_utc: string;
  };
  assert(
    "change_history entry carries the PRIOR version (0) + prior close",
    prior.version === 0 &&
      new Date(prior.resolved_close_utc).toISOString() ===
        "2026-06-17T03:59:59.000Z",
    `v${prior.version} @ ${prior.resolved_close_utc}`,
  );

  // ── CONFLICT — seed a withdrawn-vs-open pair under a fresh ocd_id; assert a conflict_records row ─────
  const OCD2 = "ocd-participation-window/federal/2025-77777";
  const frC = {
    ...frFixture,
    document_number: "2025-77777",
    comments_close_on: "2026-07-15",
  };
  await ingestObservation(sql, parseFrObservation(frC));
  const regsC = JSON.parse(JSON.stringify(regsFixture)) as typeof regsFixture;
  regsC.data.attributes.frDocNum = "2025-77777";
  regsC.data.attributes.commentEndDate = "2026-07-15T12:00:00Z";
  regsC.data.attributes.withdrawn = true;
  regsC.data.attributes.openForComment = true;
  await ingestObservation(sql, parseRegsObservation(regsC));

  const rc1 = await reconcileOcdId(sql, OCD2, NOW);
  assert(
    "withdrawn-vs-open derive is conflicting",
    rc1.window.confidence === "conflicting" &&
      rc1.conflict !== null &&
      rc1.conflict.conflict_flags[0] === "withdrawn_vs_open",
    rc1.window.confidence,
  );
  const conflictCount = async () =>
    (
      await sql<{ count: string }[]>`
        select count(*)::text as count from conflict_records where ocd_id = ${OCD2}
      `
    )[0]!.count;
  assert(
    "one conflict_records row after first detect",
    (await conflictCount()) === "1",
    await conflictCount(),
  );

  // Re-run reconcile on the SAME disagreeing pair → must NOT duplicate the proof-feed row, and must NOT
  // bump the original detected_at (idempotent metadata refresh only).
  const [beforeReRun] = await sql<{ detected_at: Date }[]>`
    select detected_at from conflict_records where ocd_id = ${OCD2}
  `;
  await reconcileOcdId(sql, OCD2, new Date("2026-06-03T00:00:00Z"));
  assert(
    "re-running reconcile does NOT duplicate the conflict_records row",
    (await conflictCount()) === "1",
    await conflictCount(),
  );
  const [afterReRun] = await sql<{ detected_at: Date }[]>`
    select detected_at from conflict_records where ocd_id = ${OCD2}
  `;
  assert(
    "re-detecting the SAME pair does NOT bump the original detected_at",
    afterReRun!.detected_at.getTime() === beforeReRun!.detected_at.getTime(),
    `${beforeReRun!.detected_at.toISOString()} -> ${afterReRun!.detected_at.toISOString()}`,
  );

  // ── RETIREMENT (a): a conflict that RESOLVES (mismatch → agreeing re-derivation) retires its row ────
  const OCD3 = "ocd-participation-window/federal/2025-33333";
  const openConflictCount = async (ocd: string) =>
    (
      await sql<{ count: string }[]>`
        select count(*)::text as count from conflict_records
        where ocd_id = ${ocd} and resolved_at is null
      `
    )[0]!.count;

  // First derivation: FR vs Regs disagree by >=1 Eastern day → CONFLICTING (fr_regs_date_mismatch).
  const frR3 = {
    ...frFixture,
    document_number: "2025-33333",
    comments_close_on: "2026-07-01",
  };
  await ingestObservation(sql, parseFrObservation(frR3));
  const regsR3 = JSON.parse(JSON.stringify(regsFixture)) as typeof regsFixture;
  regsR3.data.attributes.frDocNum = "2025-33333";
  regsR3.data.attributes.commentEndDate = "2026-08-11T03:59:59Z"; // Eastern 08-10, a true mismatch
  await ingestObservation(sql, {
    ...parseRegsObservation(regsR3),
    fetched_at: "2026-05-01T00:00:00Z",
  });
  await reconcileOcdId(sql, OCD3, NOW);
  assert(
    "RETIRE(a): conflict open after mismatch",
    (await openConflictCount(OCD3)) === "1",
    await openConflictCount(OCD3),
  );

  // New Regs observation that now AGREES on the Eastern date → window no longer conflicting → retire.
  const regsR3b = JSON.parse(JSON.stringify(regsR3)) as typeof regsR3;
  regsR3b.data.attributes.commentEndDate = "2026-07-02T03:59:59Z"; // Eastern 07-01, agrees with FR
  await ingestObservation(sql, {
    ...parseRegsObservation(regsR3b),
    fetched_at: "2026-05-02T00:00:00Z",
  });
  await reconcileOcdId(sql, OCD3, new Date("2026-06-04T00:00:00Z"));
  assert(
    "RETIRE(a): open conflict rows = 0 after an agreeing re-derivation",
    (await openConflictCount(OCD3)) === "0",
    await openConflictCount(OCD3),
  );

  // ── RETIREMENT (b): a conflicting pair SUPERSEDED by a NEW conflicting pair retires the old one ─────
  const OCD4 = "ocd-participation-window/federal/2025-44444";
  const frR4 = {
    ...frFixture,
    document_number: "2025-44444",
    comments_close_on: "2026-07-01",
  };
  await ingestObservation(sql, parseFrObservation(frR4));
  const regsR4 = JSON.parse(JSON.stringify(regsFixture)) as typeof regsFixture;
  regsR4.data.attributes.frDocNum = "2025-44444";
  regsR4.data.attributes.commentEndDate = "2026-08-11T03:59:59Z"; // Eastern 08-10, mismatch
  await ingestObservation(sql, {
    ...parseRegsObservation(regsR4),
    fetched_at: "2026-05-01T00:00:00Z",
  });
  await reconcileOcdId(sql, OCD4, NOW);
  const [firstPair] = await sql<{ observation_b_id: string }[]>`
    select observation_b_id from conflict_records
    where ocd_id = ${OCD4} and resolved_at is null
  `;

  // A NEW Regs observation (new observation_id) that STILL conflicts → a new conflicting pair supersedes.
  const regsR4b = JSON.parse(JSON.stringify(regsR4)) as typeof regsR4;
  regsR4b.data.attributes.commentEndDate = "2026-09-15T03:59:59Z"; // Eastern 09-14, still a mismatch
  await ingestObservation(sql, {
    ...parseRegsObservation(regsR4b),
    fetched_at: "2026-05-02T00:00:00Z",
  });
  await reconcileOcdId(sql, OCD4, new Date("2026-06-05T00:00:00Z"));
  assert(
    "RETIRE(b): exactly one OPEN conflict row after a superseding conflicting pair",
    (await openConflictCount(OCD4)) === "1",
    await openConflictCount(OCD4),
  );
  const [supersededRow] = await sql<{ resolved_at: Date | null }[]>`
    select resolved_at from conflict_records
    where ocd_id = ${OCD4} and observation_b_id = ${firstPair!.observation_b_id}
  `;
  assert(
    "RETIRE(b): the OLD (superseded) pair has resolved_at set",
    supersededRow?.resolved_at !== null,
    String(supersededRow?.resolved_at),
  );
  const [openRow] = await sql<{ observation_b_id: string }[]>`
    select observation_b_id from conflict_records
    where ocd_id = ${OCD4} and resolved_at is null
  `;
  assert(
    "RETIRE(b): the open row is the NEW pair (not the superseded one)",
    openRow!.observation_b_id !== firstPair!.observation_b_id,
    `${openRow!.observation_b_id} vs ${firstPair!.observation_b_id}`,
  );
} finally {
  await sql.end();
}

console.log("\n=== reconcile results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
