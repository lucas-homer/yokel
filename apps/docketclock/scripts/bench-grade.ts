/**
 * bench-grade — score a benchmark run against its key, including arm D (DocketClock alone, no model).
 *
 *   pnpm --filter @yokel/docketclock bench:grade --run ~/.config/yokel/bench/runs/prompts-<hash>
 *       [--key ~/.config/yokel/bench/key/items.jsonl] [--include-unchecked]
 *
 * Writes <run>/grades.jsonl (one line per job, plus arm D lines) and <run>/report.md, and prints the
 * report. Grading is the pure `grade()` in src/bench/grade.ts; no model is involved.
 *
 * Items marked needs_check (misses, routine, "never moved") are left out until the operator has hand-checked
 * them and set needs_check=false in the key, unless --include-unchecked is passed (the report says so).
 */
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { parseArgs } from "node:util";
import {
  blockedHosts,
  grade,
  leakedHosts,
  parseAnswer,
  tally,
  type GradeResult,
} from "../src/bench/grade.js";
import type { Answer, Item } from "../src/bench/types.js";

const { values } = parseArgs({
  options: {
    run: { type: "string" },
    key: {
      type: "string",
      default: join(homedir(), ".config/yokel/bench/key/items.jsonl"),
    },
    "include-unchecked": { type: "boolean", default: false },
  },
});
if (!values.run) throw new Error("--run <run dir> is required");
const runDir = values.run;

const envFile = join(homedir(), ".config/yokel/bench.env");
const dcUrl = existsSync(envFile)
  ? readFileSync(envFile, "utf8")
      .match(/^DOCKETCLOCK_API_URL=(.*)$/m)?.[1]
      ?.trim()
  : undefined;
const dcHost = dcUrl ? new URL(dcUrl.replace(/^['"]|['"]$/g, "")).host : null;

const items = new Map<string, Item>();
for (const l of readFileSync(values.key!, "utf8").trim().split("\n")) {
  const i = JSON.parse(l) as Item;
  if (i.needs_check && !values["include-unchecked"]) continue;
  items.set(i.id, i);
}

interface ResultLine {
  job: string;
  item_id: string;
  arm: "A" | "B" | "C";
  model: string;
  rep: number;
  result_text: string | null;
  num_turns: number | null;
  cost_usd: number | null;
  wall_ms: number;
  usage: {
    input_tokens?: number;
    output_tokens?: number;
    cache_read_input_tokens?: number;
    cache_creation_input_tokens?: number;
  } | null;
  tool_calls: { name: string; input: string }[];
}
interface GradeLine extends GradeResult {
  item_id: string;
  stratum: string;
  family: string;
  arm: string;
  model: string;
  rep: number;
  answer: Answer | null;
  void_reason: string | null;
  tokens: number | null;
  turns: number | null;
  wall_ms: number | null;
}

const ALLOWED_TOOL_NAMES: Record<string, Set<string>> = {
  A: new Set(["WebSearch", "WebFetch"]),
  B: new Set(["WebSearch", "WebFetch", "Bash"]),
  C: new Set(["WebSearch", "WebFetch", "Bash"]),
};

const lines: GradeLine[] = [];
const resultsPath = join(runDir, "results.jsonl");
const results: ResultLine[] = existsSync(resultsPath)
  ? readFileSync(resultsPath, "utf8")
      .trim()
      .split("\n")
      .filter(Boolean)
      .map((l) => JSON.parse(l))
  : [];
for (const r of results) {
  const item = items.get(r.item_id);
  if (!item) continue;
  const forbidden = r.tool_calls
    .filter((t) => !ALLOWED_TOOL_NAMES[r.arm]!.has(t.name))
    .map((t) => t.name);
  const nonCurlBash = r.tool_calls.filter((t) => {
    if (t.name !== "Bash") return false;
    try {
      const cmd = String(
        (JSON.parse(t.input) as { command?: unknown }).command ?? "",
      );
      // one curl, no chaining into another program (a pipe to jq is allowed). Quoted text is dropped
      // first, so an "&" inside a quoted query string is not mistaken for a command separator.
      const bare = cmd.replace(/'[^']*'|"(?:[^"\\]|\\.)*"/g, "''");
      return (
        !/^\s*curl\s/.test(bare) ||
        /[;&`]|\$\(|\|(?!\s*(?:jq|head)\b)/.test(bare)
      );
    } catch {
      return true;
    }
  });
  const leaks = leakedHosts(
    r.tool_calls.map((t) => t.input),
    blockedHosts(r.arm, dcHost),
  );
  const voidReason = leaks.length
    ? `blocked host: ${leaks.join(", ")}`
    : forbidden.length
      ? `forbidden tool: ${[...new Set(forbidden)].join(", ")}`
      : nonCurlBash.length
        ? "Bash other than curl"
        : null;
  const answer = parseAnswer(r.result_text);
  const u = r.usage;
  const tokens = u
    ? (u.input_tokens ?? 0) +
      (u.output_tokens ?? 0) +
      (u.cache_read_input_tokens ?? 0) +
      (u.cache_creation_input_tokens ?? 0)
    : null;
  lines.push({
    item_id: item.id,
    stratum: item.stratum,
    family: item.family,
    arm: r.arm,
    model: r.model,
    rep: r.rep,
    answer,
    void_reason: voidReason,
    tokens,
    turns: r.num_turns,
    wall_ms: r.wall_ms,
    ...grade(item.expect, answer, { void: voidReason !== null }),
  });
}
// Arm D: DocketClock alone. D-machine = the blind derivation (no human verdicts); D-published = what it published.
for (const item of items.values()) {
  for (const [arm, a] of [
    ["D-machine", item.docketclock.machine],
    ["D-published", item.docketclock.published],
  ] as const) {
    if (!a) continue;
    lines.push({
      item_id: item.id,
      stratum: item.stratum,
      family: item.family,
      arm,
      model: "-",
      rep: 0,
      answer: a,
      void_reason: null,
      tokens: 0,
      turns: 0,
      wall_ms: 0,
      ...grade(item.expect, a),
    });
  }
}
writeFileSync(
  join(runDir, "grades.jsonl"),
  lines.map((l) => JSON.stringify(l)).join("\n") + "\n",
  { mode: 0o600 },
);

// ── report ─────────────────────────────────────────────────────────────────────────────────────────
const pct = (x: number) => `${(x * 100).toFixed(1)}%`;
const groups = new Map<string, GradeLine[]>();
for (const l of lines) {
  for (const k of [
    `${l.arm}|${l.model}|ALL ${l.family}`,
    `${l.arm}|${l.model}|${l.stratum}`,
  ])
    groups.set(k, [...(groups.get(k) ?? []), l]);
}
const rows = [...groups.entries()]
  .sort(([a], [b]) => a.localeCompare(b))
  .map(([k, ls]) => {
    const [arm, model, slice] = k.split("|");
    const t = tally(ls);
    const toks = ls.map((l) => l.tokens).filter((x): x is number => x !== null);
    const medTok = toks.length
      ? toks.sort((a, b) => a - b)[Math.floor(toks.length / 2)]!
      : null;
    return `| ${arm} | ${model} | ${slice} | ${t.n} | ${pct(t.accuracy)} | **${pct(t.silent_wrong_rate)}** | ${t.honest_miss} | ${t.unparseable} | ${t.void} | ${t.no_sources_correct} | ${medTok ?? "-"} |`;
  });
const unchecked = values["include-unchecked"]
  ? "\n> Includes items still marked needs_check: their keys are not hand-verified.\n"
  : "";
const report = [
  `# Agent vs DocketClock — ${runDir.split("/").pop()}`,
  unchecked,
  `| Arm | Model | Slice | n | Accuracy | Silent-wrong | Honest miss | Unparseable | Void | Correct, no source | Median tokens |`,
  `| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |`,
  ...rows,
  "",
  "Accuracy = (correct + correct abstention) / scored; silent-wrong = confident wrong / scored; void is excluded from both.",
  "D-machine is DocketClock's own derivation with human verdicts hidden; D-published includes your pins, so it wins the pin stratum by construction.",
].join("\n");
writeFileSync(join(runDir, "report.md"), report + "\n");
console.log(report);
