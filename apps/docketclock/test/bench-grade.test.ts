/**
 * bench-grade.test.ts — the agent-vs-DocketClock grader is PURE; this pins its scoring rules.
 * Repo test style: hand-rolled assert, out[] accumulator, failures counter, process.exit.
 */
import {
  blockedHosts,
  easternDate,
  grade,
  leakedHosts,
  parseAnswer,
  tally,
} from "../src/bench/grade.js";
import type { Answer } from "../src/bench/types.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}
const ans = (p: Partial<Answer>): Answer => ({
  answer_kind: "date",
  date: "2026-09-03",
  confidence: "high",
  round: null,
  sources: ["https://www.federalregister.gov/d/2026-1"],
  ...p,
});
const D = { kind: "date", date: "2026-09-03" } as const;

// easternDate: the 23:59:59 ET close stored as 03:59:59Z the next day
assert(
  "EDT close maps to the prior UTC day",
  easternDate("2026-09-04T03:59:59Z") === "2026-09-03",
);
assert(
  "EST close maps to the prior UTC day",
  easternDate("2026-11-21T04:59:59Z") === "2026-11-20",
);

// grade: date keys
assert("right date → correct", grade(D, ans({})).grade === "correct");
assert(
  "wrong date, high → silent_wrong",
  grade(D, ans({ date: "2026-09-08" })).grade === "silent_wrong",
);
assert(
  "wrong date, medium → silent_wrong",
  grade(D, ans({ date: "2026-09-08", confidence: "medium" })).grade ===
    "silent_wrong",
);
assert(
  "wrong date, low → honest_miss",
  grade(D, ans({ date: "2026-09-08", confidence: "low" })).grade ===
    "honest_miss",
);
assert(
  "unresolved on a resolvable key → honest_miss",
  grade(D, ans({ answer_kind: "unresolved", date: null })).grade ===
    "honest_miss",
);
assert(
  "withdrawn (high) on a date key → silent_wrong",
  grade(D, ans({ answer_kind: "withdrawn", date: null })).grade ===
    "silent_wrong",
);
assert(
  "right date at low confidence still correct",
  grade(D, ans({ confidence: "low" })).grade === "correct",
);
assert(
  "no sources flagged, still correct",
  (() => {
    const g = grade(D, ans({ sources: [] }));
    return g.grade === "correct" && g.no_sources;
  })(),
);

// escalate keys
const U = { kind: "unresolved" } as const;
assert(
  "unresolved on escalate → correct_abstention",
  grade(U, ans({ answer_kind: "unresolved", date: null })).grade ===
    "correct_abstention",
);
assert(
  "low-confidence date on escalate → correct_abstention",
  grade(U, ans({ confidence: "low" })).grade === "correct_abstention",
);
assert(
  "confident date on escalate → silent_wrong",
  grade(U, ans({})).grade === "silent_wrong",
);

// withdrawn and moved keys
assert(
  "withdrawn key, withdrawn answer → correct",
  grade({ kind: "withdrawn" }, ans({ answer_kind: "withdrawn", date: null }))
    .grade === "correct",
);
const M = { kind: "moved", moved: true, earlier_date: "2026-07-11" } as const;
assert(
  "moved: yes + earlier date → correct",
  grade(M, ans({ answer_kind: "yes", date: "2026-07-11" })).grade === "correct",
);
assert(
  "moved: yes + wrong earlier date → silent_wrong",
  grade(M, ans({ answer_kind: "yes", date: "2026-07-12" })).grade ===
    "silent_wrong",
);
assert(
  "moved: confident no → silent_wrong",
  grade(M, ans({ answer_kind: "no", date: null })).grade === "silent_wrong",
);
assert(
  "not moved: no → correct",
  grade({ kind: "moved", moved: false }, ans({ answer_kind: "no", date: null }))
    .grade === "correct",
);

// null / void
assert("no answer → unparseable", grade(D, null).grade === "unparseable");
assert(
  "void wins over a right answer",
  grade(D, ans({}), { void: true }).grade === "void",
);

// parseAnswer
const fenced =
  'Reasoning...\n```json\n{"answer_kind":"date","date":"2026-09-03","confidence":"high","round":"initial","sources":["u"]}\n```';
assert("parses a fenced block", parseAnswer(fenced)?.date === "2026-09-03");
const two =
  '```json\n{"answer_kind":"date","date":"2026-01-01","confidence":"high","sources":[]}\n```\nRevised:\n```json\n{"answer_kind":"date","date":"2026-02-02","confidence":"medium","sources":[]}\n```';
assert("takes the LAST valid block", parseAnswer(two)?.date === "2026-02-02");
assert(
  "bare trailing object parses",
  parseAnswer(
    'Final: {"answer_kind":"unresolved","date":null,"confidence":"low","sources":[]}',
  )?.answer_kind === "unresolved",
);
assert(
  "bad date format rejected",
  parseAnswer('{"answer_kind":"date","date":"Sept 3","confidence":"high"}') ===
    null,
);
assert(
  "date kind without a date rejected",
  parseAnswer('{"answer_kind":"date","date":null,"confidence":"high"}') ===
    null,
);
assert(
  "unknown confidence rejected",
  parseAnswer(
    '{"answer_kind":"date","date":"2026-09-03","confidence":"sure"}',
  ) === null,
);
assert("empty text → null", parseAnswer("") === null);

// tally
const t = tally([
  { grade: "correct", no_sources: false },
  { grade: "silent_wrong", no_sources: false },
  { grade: "honest_miss", no_sources: false },
  { grade: "void", no_sources: false },
]);
assert(
  "silent-wrong rate excludes void",
  Math.abs(t.silent_wrong_rate - 1 / 3) < 1e-9,
  String(t.silent_wrong_rate),
);
assert("empty tally is zeros, not NaN", tally([]).silent_wrong_rate === 0);

// leakage
assert(
  "arms A/B block the DocketClock host",
  blockedHosts("B", "dc.example.workers.dev").includes(
    "dc.example.workers.dev",
  ),
);
assert(
  "arm C may reach DocketClock",
  !blockedHosts("C", "dc.example.workers.dev").includes(
    "dc.example.workers.dev",
  ),
);
assert(
  "leak detected in a curl",
  leakedHosts(
    ["curl -s https://github.com/lucas-homer/yokel"],
    blockedHosts("A", null),
  ).includes("github.com"),
);
assert(
  "no leak on the FR API",
  leakedHosts(
    ["curl -s https://www.federalregister.gov/api/v1/documents/2026-1.json"],
    blockedHosts("B", null),
  ).length === 0,
);

console.log(out.join("\n"));
console.log(
  failures === 0
    ? `bench-grade: all ${out.length} passed`
    : `bench-grade: ${failures} FAILED`,
);
process.exit(failures === 0 ? 0 : 1);
