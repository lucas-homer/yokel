/**
 * contract.adversary.probe.ts — SECOND-PASS adversary probe against the FROZEN @0.2.0 contract.
 *
 * The committed contract.adversary.ts already guards the four named edge cases. This probe hunts for
 * NOVEL ways to make `confidence` lie that the existing refinements may not cover. Each block prints
 * the OBSERVED parse result (PASS/FAIL of safeParse) so the adversary can judge whether the schema's
 * behavior is acceptable — these are not all "must fail"; some expose gaps where the schema is SILENT.
 *
 * Run: pnpm --filter @yokel/contracts exec tsx src/contract.adversary.probe.ts
 */
import { ParticipationWindow, ConflictRecord, OcdId, makeOcdId } from "./index.js";

const out: string[] = [];
function probe(name: string, accepted: boolean, note = "") {
  out.push(`  ${accepted ? "ACCEPTS" : "REJECTS"}  ${name}${note ? ` — ${note}` : ""}`);
}

function baseWindow(over: Record<string, unknown> = {}) {
  return {
    ocd_id: makeOcdId({ frDocNum: "2018-27875" }),
    fr_document_number: "2018-27875",
    regs_document_id: null,
    regs_object_id: null,
    docket_id: [],
    rin: null,
    window_type: "comment",
    resolved_close_utc: "2018-12-21T05:00:00.000Z",
    resolved_close_display: "11:59 p.m. ET",
    raw_fr_close_date: "2018-12-20",
    raw_regs_close_datetime: "2018-12-21T04:59:00-05:00",
    confidence: "medium",
    conflict_flags: [],
    status: "open",
    submission_url: null,
    govinfo_url: null,
    tags: [],
    version: 1,
    current_observation_ids: [],
    provenance: { agreeing_observation_ids: [], conflicting_observation_ids: [] },
    change_history: [],
    ...over,
  };
}
const P = (o: Record<string, unknown>) => ParticipationWindow.safeParse(baseWindow(o)).success;

// ── PROBE A: CONFLICTING with EMPTY conflict_flags — a verdict of "they disagree" naming no reason.
probe("A) confidence='conflicting' with conflict_flags=[] (no named reason)",
  P({ confidence: "conflicting", conflict_flags: [], resolved_close_utc: null }),
  "is a CONFLICTING window allowed to name zero conflict flags?");

// ── PROBE B: HIGH confidence carrying a conflict flag — "confident AND sources mismatch".
probe("B) confidence='high' + conflict_flags=['fr_regs_date_mismatch']",
  P({ confidence: "high", conflict_flags: ["fr_regs_date_mismatch"] }),
  "HIGH means sources AGREE; can a date-mismatch flag ride on HIGH?");

// ── PROBE C: HIGH carrying withdrawn_vs_open — a flag that the spec says forces CONFLICTING.
probe("C) confidence='high' + conflict_flags=['withdrawn_vs_open']",
  P({ confidence: "high", conflict_flags: ["withdrawn_vs_open"] }),
  "spec: withdrawn-vs-open => CONFLICTING; can it hide under HIGH?");

// ── PROBE D: tz_normalization_only on a NON-medium confidence other than conflicting.
//    Spec pins it as a MEDIUM signal. Refinement #2 only blocks it on 'conflicting'.
probe("D1) tz_normalization_only on confidence='high'",
  P({ confidence: "high", conflict_flags: ["tz_normalization_only"] }),
  "spec calls tz_normalization_only a MEDIUM signal; HIGH allowed?");
probe("D2) tz_normalization_only on confidence='unknown' (+null close)",
  P({ confidence: "unknown", conflict_flags: ["tz_normalization_only"], resolved_close_utc: null,
      resolved_close_display: null, raw_fr_close_date: null, raw_regs_close_datetime: null }),
  "tz artifact on the lowest-confidence state?");
probe("D3) tz_normalization_only on confidence='stale'",
  P({ confidence: "stale", conflict_flags: ["tz_normalization_only"] }),
  "");

// ── PROBE E: OcdId regex permissiveness. The regex is /^ocd-participation-window\/federal\/.+$/.
//    `.+` is greedy-but-dotless-on-newline; what garbage passes the seam?
const ocdProbe = (s: string) => OcdId.safeParse(s).success;
probe("E1) ocd_id 'ocd-participation-window/federal/ ' (trailing space only after slash)",
  ocdProbe("ocd-participation-window/federal/ "), "whitespace-only tail accepted?");
probe("E2) ocd_id with embedded newline 'ocd-participation-window/federal/x\\ny'",
  ocdProbe("ocd-participation-window/federal/x\ny"), "JS $ matches before \\n — second line slips?");
probe("E3) ocd_id with a SECOND federal segment injected",
  ocdProbe("ocd-participation-window/federal/a/../../evil"), "path-traversal-shaped id accepted?");
probe("E4) makeOcdId with a frDocNum containing a slash",
  (() => { try { return OcdId.safeParse(makeOcdId({ frDocNum: "2025-01/../x" })).success; } catch { return false; } })(),
  "minting path lets a slash-bearing frDocNum mint a structurally-ambiguous id?");

// ── PROBE F: resolved_close_utc that is NOT actually UTC. Field name says _utc; does datetime() enforce Z?
probe("F1) resolved_close_utc with a -05:00 offset (not Z) under HIGH",
  P({ confidence: "high", resolved_close_utc: "2018-12-21T00:00:00-05:00" }),
  "field is named _utc; does z.string().datetime() reject non-Z offsets?");
probe("F2) resolved_close_utc date-only '2018-12-21' under HIGH",
  P({ confidence: "high", resolved_close_utc: "2018-12-21" }),
  "a date-only string masquerading as a UTC instant?");

// ── PROBE G: ConflictRecord whose ONLY flag is tz_normalization_only — publishing a NON-conflict
//    to the /conflicts proof feed. Refinement #2 lives on ParticipationWindow, NOT ConflictRecord.
probe("G) ConflictRecord with conflict_flags=['tz_normalization_only'] ONLY",
  ConflictRecord.safeParse({
    ocd_id: makeOcdId({ frDocNum: "2018-27875" }),
    observation_a_id: "o1", observation_b_id: "o2",
    source_a: "federal_register", source_b: "regulations_gov",
    conflict_flags: ["tz_normalization_only"],
    govinfo_url: null, detected_at: "2024-01-01T00:00:00.000Z",
  }).success,
  "can a pure tz-artifact be published as a CONFLICT in the proof feed?");

// ── PROBE H: ConflictRecord where source_a === source_b — a 'conflict' between a source and itself.
probe("H) ConflictRecord with source_a === source_b (same source)",
  ConflictRecord.safeParse({
    ocd_id: makeOcdId({ frDocNum: "2018-27875" }),
    observation_a_id: "o1", observation_b_id: "o1",
    source_a: "federal_register", source_b: "federal_register",
    conflict_flags: ["fr_regs_date_mismatch"],
    govinfo_url: null, detected_at: "2024-01-01T00:00:00.000Z",
  }).success,
  "fr_regs_date_mismatch between FR and FR (same obs id) — self-conflict?");

// ── PROBE I: duplicate conflict_flags array — ['tz_normalization_only','tz_normalization_only'].
probe("I) duplicate conflict_flags entries accepted",
  P({ confidence: "medium", conflict_flags: ["tz_normalization_only", "tz_normalization_only"] }),
  "no set semantics; duplicates allowed (cosmetic)");

// ── PROBE J: status='withdrawn' but confidence='high' with an operative close — withdrawn yet confident open deadline.
probe("J) status='withdrawn' + confidence='high' + a real resolved_close_utc",
  P({ confidence: "high", status: "withdrawn", resolved_close_utc: "2025-01-01T00:00:00.000Z" }),
  "a withdrawn window shipping a HIGH-confidence live deadline?");

console.log("\n=== contract.adversary.probe (observed schema behavior) ===");
console.log(out.join("\n"));
