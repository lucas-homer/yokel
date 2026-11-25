/**
 * The benchmark grader — PURE, no I/O, so the scoring rules are pinned by tests (test/bench-grade.test.ts).
 *
 * Rules (from the design doc, "Tasks and scoring"):
 *   correct             the answer matches the key (dates compared as America/New_York calendar dates)
 *   honest_miss         wrong or absent, but the arm said `unresolved` or low confidence
 *   correct_abstention  `unresolved` or low confidence where the key is `escalate`
 *   silent_wrong        a wrong answer given with high or medium confidence
 *   unparseable         no final answer in the required JSON shape
 *   void                the run reached a blocked host or used a tool its arm forbids
 * A correct answer with no cited source is still `correct`, but flagged `no_sources`.
 */
import type { Answer, Expectation, Grade } from "./types.js";

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const KINDS = new Set(["date", "withdrawn", "unresolved", "yes", "no"]);
const CONFS = new Set(["high", "medium", "low"]);

/** America/New_York calendar date of an instant: 2026-09-04T03:59:59Z → 2026-09-03. */
export function easternDate(instant: string | Date): string {
  const d = typeof instant === "string" ? new Date(instant) : instant;
  if (Number.isNaN(d.getTime()))
    throw new Error(`bad instant: ${String(instant)}`);
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/New_York",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(d);
}

/**
 * Pull the arm's final answer out of its last message: the LAST ```json fenced block, else the last
 * top-level {...} that parses. Returns null when nothing valid is found — never guesses.
 */
export function parseAnswer(text: string | null | undefined): Answer | null {
  if (!text) return null;
  const candidates: string[] = [];
  for (const m of text.matchAll(/```(?:json)?\s*([\s\S]*?)```/g))
    candidates.push(m[1]!);
  const lastBrace = text.lastIndexOf("{");
  if (lastBrace >= 0) {
    // the last balanced object ending at the last "}"
    const end = text.lastIndexOf("}");
    for (let i = lastBrace; i >= 0; i = text.lastIndexOf("{", i - 1)) {
      candidates.push(text.slice(i, end + 1));
      if (i === 0) break;
    }
  }
  for (let i = candidates.length - 1; i >= 0; i--) {
    const a = validate(candidates[i]!);
    if (a) return a;
  }
  return null;
}

function validate(raw: string): Answer | null {
  let o: unknown;
  try {
    o = JSON.parse(raw.trim());
  } catch {
    return null;
  }
  if (!o || typeof o !== "object") return null;
  const r = o as Record<string, unknown>;
  if (typeof r.answer_kind !== "string" || !KINDS.has(r.answer_kind))
    return null;
  if (typeof r.confidence !== "string" || !CONFS.has(r.confidence)) return null;
  const date = r.date == null ? null : String(r.date);
  if (date !== null && !DATE_RE.test(date)) return null;
  if (r.answer_kind === "date" && date === null) return null;
  return {
    answer_kind: r.answer_kind as Answer["answer_kind"],
    date,
    confidence: r.confidence as Answer["confidence"],
    round: typeof r.round === "string" ? r.round : null,
    sources: Array.isArray(r.sources)
      ? r.sources.filter((s): s is string => typeof s === "string")
      : [],
  };
}

export interface GradeResult {
  grade: Grade;
  no_sources: boolean;
}

export function grade(
  expect: Expectation,
  answer: Answer | null,
  opts: { void?: boolean } = {},
): GradeResult {
  if (opts.void) return { grade: "void", no_sources: false };
  if (!answer) return { grade: "unparseable", no_sources: false };
  const no_sources = answer.sources.length === 0;
  const abstained =
    answer.answer_kind === "unresolved" || answer.confidence === "low";

  if (expect.kind === "unresolved") {
    if (abstained) return { grade: "correct_abstention", no_sources };
    return { grade: "silent_wrong", no_sources };
  }

  if (isCorrect(expect, answer)) return { grade: "correct", no_sources };
  return { grade: abstained ? "honest_miss" : "silent_wrong", no_sources };
}

function isCorrect(
  expect: Exclude<Expectation, { kind: "unresolved" }>,
  a: Answer,
): boolean {
  switch (expect.kind) {
    case "date":
      return a.answer_kind === "date" && a.date === expect.date;
    case "withdrawn":
      return a.answer_kind === "withdrawn";
    case "moved":
      if (!expect.moved) return a.answer_kind === "no";
      return a.answer_kind === "yes" && a.date === expect.earlier_date;
  }
}

export interface Tally {
  n: number;
  correct: number;
  honest_miss: number;
  correct_abstention: number;
  silent_wrong: number;
  unparseable: number;
  void: number;
  no_sources_correct: number;
  /** silent_wrong / scored (void excluded). The headline number. */
  silent_wrong_rate: number;
  /** (correct + correct_abstention) / scored. */
  accuracy: number;
}

export function tally(rows: GradeResult[]): Tally {
  const t: Tally = {
    n: rows.length,
    correct: 0,
    honest_miss: 0,
    correct_abstention: 0,
    silent_wrong: 0,
    unparseable: 0,
    void: 0,
    no_sources_correct: 0,
    silent_wrong_rate: 0,
    accuracy: 0,
  };
  for (const r of rows) {
    t[r.grade]++;
    if (r.grade === "correct" && r.no_sources) t.no_sources_correct++;
  }
  const scored = t.n - t.void;
  t.silent_wrong_rate = scored > 0 ? t.silent_wrong / scored : 0;
  t.accuracy = scored > 0 ? (t.correct + t.correct_abstention) / scored : 0;
  return t;
}

/** Hosts a run must never reach, per arm. A transcript that mentions one voids the item. */
export function blockedHosts(
  arm: "A" | "B" | "C",
  docketclockHost: string | null,
): string[] {
  const always = ["github.com", "githubusercontent.com", "claude.ai"];
  if (arm === "C" || !docketclockHost) return always;
  return [...always, docketclockHost];
}

/** Every blocked host that a tool call in the transcript names (URL, curl target, fetch domain). */
export function leakedHosts(toolInputs: string[], blocked: string[]): string[] {
  const hit = new Set<string>();
  for (const input of toolInputs) {
    const lower = input.toLowerCase();
    for (const h of blocked) if (lower.includes(h.toLowerCase())) hit.add(h);
  }
  return [...hit];
}
