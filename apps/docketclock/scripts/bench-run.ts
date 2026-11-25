/**
 * bench-run — run agent arms A–C of the agent-vs-DocketClock benchmark with headless Claude Code.
 *
 *   pnpm --filter @yokel/docketclock bench:run --arms B,C --models opus,fable --sample 20 [--repeats 1]
 *       [--key ~/.config/yokel/bench/key/items.jsonl] [--out ~/.config/yokel/bench/runs] [--concurrency 2]
 *       [--max-turns 40] [--strata pin,escalate] [--dry-run]
 *
 * Runs on the operator's Mac, on their own Claude plan (`claude` must be signed in). Secrets come from
 * ~/.config/yokel/bench.env (REGS_API_KEY_BENCH, DOCKETCLOCK_API_URL, DOCKETCLOCK_API_KEY), never argv.
 *
 * Isolation per job: an empty temp working directory (no repo to read), project settings only (no user
 * CLAUDE.md, no user MCP servers), an explicit tool allowlist, and deny rules for the blocked hosts. The
 * transcript is kept; the grader voids any job whose tool calls reached a blocked host or a forbidden tool.
 *
 * Resumable: a job whose result line already exists in the run dir is skipped, so a re-run continues.
 */
import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import {
  appendFileSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { homedir, tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";
import { blockedHosts } from "../src/bench/grade.js";
import {
  ARMS,
  MODELS,
  type AgentArm,
  type Item,
  type ModelKey,
} from "../src/bench/types.js";

const here = dirname(fileURLToPath(import.meta.url));
const promptDir = join(here, "../bench/prompts");
const cfg = join(homedir(), ".config/yokel");

const { values } = parseArgs({
  options: {
    key: { type: "string", default: join(cfg, "bench/key/items.jsonl") },
    out: { type: "string", default: join(cfg, "bench/runs") },
    arms: { type: "string", default: "B,C" },
    models: { type: "string", default: "opus,fable" },
    repeats: { type: "string", default: "1" },
    sample: { type: "string" },
    strata: { type: "string" },
    seed: { type: "string", default: "1" },
    concurrency: { type: "string", default: "2" },
    "max-turns": { type: "string", default: "40" },
    "dry-run": { type: "boolean", default: false },
    preflight: { type: "boolean", default: false },
  },
});

function loadEnvFile(path: string): Record<string, string> {
  if (!existsSync(path)) return {};
  const env: Record<string, string> = {};
  for (const line of readFileSync(path, "utf8").split("\n")) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/);
    if (m) env[m[1]!] = m[2]!.replace(/^['"]|['"]$/g, "");
  }
  return env;
}

const arms = values
  .arms!.split(",")
  .map((a) => a.trim().toUpperCase()) as AgentArm[];
for (const a of arms)
  if (!ARMS.includes(a))
    throw new Error(
      `unknown arm ${a} (agent arms are A, B, C; D needs no run)`,
    );
const models = values.models!.split(",").map((m) => m.trim()) as ModelKey[];
for (const m of models)
  if (!(m in MODELS))
    throw new Error(`unknown model ${m} (${Object.keys(MODELS).join(", ")})`);
const repeats = Number(values.repeats);
const maxTurns = Number(values["max-turns"]);

const secrets = loadEnvFile(join(cfg, "bench.env"));
if (arms.some((a) => a !== "A") && !secrets.REGS_API_KEY_BENCH)
  throw new Error(
    "REGS_API_KEY_BENCH is missing from ~/.config/yokel/bench.env (arms B and C need it)",
  );
if (
  arms.includes("C") &&
  (!secrets.DOCKETCLOCK_API_URL || !secrets.DOCKETCLOCK_API_KEY)
)
  throw new Error(
    "arm C needs DOCKETCLOCK_API_URL and DOCKETCLOCK_API_KEY in ~/.config/yokel/bench.env",
  );
const dcHost = secrets.DOCKETCLOCK_API_URL
  ? new URL(secrets.DOCKETCLOCK_API_URL).host
  : null;

// ── items: optional strata filter, then a stratified sample ────────────────────────────────────────
let items: Item[] = readFileSync(values.key!, "utf8")
  .trim()
  .split("\n")
  .map((l) => JSON.parse(l) as Item);
if (values.strata) {
  const keep = new Set(values.strata.split(","));
  items = items.filter((i) => keep.has(i.stratum));
}
if (values.sample)
  items = stratifiedSample(items, Number(values.sample), Number(values.seed));

function stratifiedSample(xs: Item[], n: number, seed: number): Item[] {
  const by = new Map<string, Item[]>();
  for (const x of xs) by.set(x.stratum, [...(by.get(x.stratum) ?? []), x]);
  const order = [...by.keys()].sort();
  const sorted = new Map(
    order.map((k) => [
      k,
      [...by.get(k)!].sort((a, b) =>
        hash(`${seed}:${a.id}`).localeCompare(hash(`${seed}:${b.id}`)),
      ),
    ]),
  );
  const picked: Item[] = [];
  for (let round = 0; picked.length < n; round++) {
    let added = false;
    for (const k of order) {
      const x = sorted.get(k)![round];
      if (x && picked.length < n) {
        picked.push(x);
        added = true;
      }
    }
    if (!added) break;
  }
  return picked;
}

function hash(s: string): string {
  return createHash("sha256").update(s).digest("hex");
}

// ── frozen prompts → run id ────────────────────────────────────────────────────────────────────────
const common = readFileSync(join(promptDir, "common.md"), "utf8");
const questionsSrc = readFileSync(
  join(here, "../src/bench/questions.ts"),
  "utf8",
);
const armPrompt = (a: AgentArm) =>
  `${common}\n${readFileSync(join(promptDir, `arm-${a}.md`), "utf8")}`;
const promptHash = hash(
  common + questionsSrc + ARMS.map((a) => armPrompt(a)).join(""),
).slice(0, 10);
const runDir = join(values.out!, `prompts-${promptHash}`);
mkdirSync(join(runDir, "transcripts"), { recursive: true, mode: 0o700 });
writeFileSync(
  join(runDir, "prompts.json"),
  JSON.stringify(
    {
      promptHash,
      common,
      arms: Object.fromEntries(ARMS.map((a) => [a, armPrompt(a)])),
    },
    null,
    2,
  ),
);
const resultsPath = join(runDir, "results.jsonl");
const done = new Set<string>(
  existsSync(resultsPath)
    ? readFileSync(resultsPath, "utf8")
        .trim()
        .split("\n")
        .filter(Boolean)
        .map((l) => (JSON.parse(l) as { job: string }).job)
    : [],
);

// ── tool policy per arm ────────────────────────────────────────────────────────────────────────────
const ALLOWED: Record<AgentArm, string[]> = {
  A: ["WebSearch", "WebFetch"],
  B: ["WebSearch", "WebFetch", "Bash(curl:*)", "Bash(jq:*)", "Bash(head:*)"],
  C: ["WebSearch", "WebFetch", "Bash(curl:*)", "Bash(jq:*)", "Bash(head:*)"],
};
const DISALLOWED = [
  "Read",
  "Write",
  "Edit",
  "MultiEdit",
  "Glob",
  "Grep",
  "NotebookEdit",
  "Task",
  "Agent",
  "TodoWrite",
];

function settingsFor(arm: AgentArm): object {
  const deny = blockedHosts(arm, dcHost).flatMap((h) => [
    `WebFetch(domain:${h})`,
    `Bash(curl:*${h}*)`,
  ]);
  return { permissions: { allow: ALLOWED[arm], deny } };
}

function envFor(arm: AgentArm): NodeJS.ProcessEnv {
  const env: NodeJS.ProcessEnv = {
    PATH: process.env.PATH,
    HOME: process.env.HOME,
    USER: process.env.USER,
    LANG: "en_US.UTF-8",
  };
  if (arm !== "A") env.REGS_API_KEY_BENCH = secrets.REGS_API_KEY_BENCH;
  if (arm === "C") {
    env.DOCKETCLOCK_API_URL = secrets.DOCKETCLOCK_API_URL;
    env.DOCKETCLOCK_API_KEY = secrets.DOCKETCLOCK_API_KEY;
  }
  return env;
}

interface Job {
  job: string;
  item: Item;
  arm: AgentArm;
  model: ModelKey;
  rep: number;
}
const jobs: Job[] = [];
for (const item of items)
  for (const arm of arms)
    for (const model of models)
      for (let rep = 0; rep < repeats; rep++) {
        const job = `${item.id}|${arm}|${model}|${rep}`;
        if (!done.has(job)) jobs.push({ job, item, arm, model, rep });
      }

console.log(`run dir ${runDir}`);
console.log(
  `${items.length} items × ${arms.length} arms × ${models.length} models × ${repeats} → ${jobs.length} jobs to run (${done.size} already done)`,
);
if (values["dry-run"]) {
  for (const j of jobs.slice(0, 5))
    console.log(`  ${j.job}\n    ${j.item.question}`);
  process.exit(0);
}

function runJob(j: Job): Promise<void> {
  const cwd = mkdtempSync(join(tmpdir(), "dc-bench-"));
  mkdirSync(join(cwd, ".claude"));
  writeFileSync(
    join(cwd, ".claude/settings.json"),
    JSON.stringify(settingsFor(j.arm)),
  );
  const transcript = join(
    runDir,
    "transcripts",
    `${hash(j.job).slice(0, 16)}.jsonl`,
  );
  const args = [
    "-p",
    j.item.question,
    "--model",
    MODELS[j.model],
    "--output-format",
    "stream-json",
    "--verbose",
    "--max-turns",
    String(maxTurns),
    "--append-system-prompt",
    armPrompt(j.arm),
    "--allowedTools",
    ALLOWED[j.arm].join(","),
    "--disallowedTools",
    DISALLOWED.join(","),
    "--setting-sources",
    "project",
    "--strict-mcp-config",
    "--mcp-config",
    '{"mcpServers":{}}',
  ];
  const started = Date.now();
  return new Promise((resolve) => {
    const child = spawn("claude", args, {
      cwd,
      env: envFor(j.arm),
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (d) => {
      stdout += d;
    });
    child.stderr.on("data", (d) => {
      stderr += d;
    });
    child.on("close", (code) => {
      writeFileSync(transcript, stdout, { mode: 0o600 });
      const events = stdout
        .split("\n")
        .filter(Boolean)
        .flatMap((l) => {
          try {
            return [JSON.parse(l)];
          } catch {
            return [];
          }
        });
      const result =
        [...events].reverse().find((e) => e.type === "result") ?? null;
      const toolCalls: { name: string; input: string }[] = [];
      for (const e of events)
        if (e.type === "assistant")
          for (const c of e.message?.content ?? [])
            if (c.type === "tool_use")
              toolCalls.push({ name: c.name, input: JSON.stringify(c.input) });
      appendFileSync(
        resultsPath,
        JSON.stringify({
          job: j.job,
          item_id: j.item.id,
          arm: j.arm,
          model: j.model,
          model_id: MODELS[j.model],
          rep: j.rep,
          prompt_hash: promptHash,
          exit_code: code,
          wall_ms: Date.now() - started,
          result_text: result?.result ?? null,
          is_error: result?.is_error ?? true,
          num_turns: result?.num_turns ?? null,
          usage: result?.usage ?? null,
          cost_usd: result?.total_cost_usd ?? null,
          tool_calls: toolCalls,
          transcript,
          stderr_tail: stderr.slice(-500),
        }) + "\n",
      );
      rmSync(cwd, { recursive: true, force: true });
      console.log(
        `  ${code === 0 ? "ok " : "ERR"} ${j.job} (${Math.round((Date.now() - started) / 1000)}s, ${toolCalls.length} tool calls)`,
      );
      resolve();
    });
  });
}

/**
 * --preflight: one trivial arm-A job, then print what the session actually loaded (tools, MCP servers,
 * model, memory/CLAUDE.md paths if any). Run it once on a new machine: anything beyond the arm's
 * allowlist, or any memory file, means the isolation leaks and the run should not start.
 */
async function preflight() {
  const cwd = mkdtempSync(join(tmpdir(), "dc-bench-pre-"));
  mkdirSync(join(cwd, ".claude"));
  writeFileSync(
    join(cwd, ".claude/settings.json"),
    JSON.stringify(settingsFor("A")),
  );
  const args = [
    "-p",
    "Reply with the single word OK.",
    "--model",
    MODELS[models[0]!],
    "--output-format",
    "stream-json",
    "--verbose",
    "--max-turns",
    "2",
    "--allowedTools",
    ALLOWED.A.join(","),
    "--disallowedTools",
    DISALLOWED.join(","),
    "--setting-sources",
    "project",
    "--strict-mcp-config",
    "--mcp-config",
    '{"mcpServers":{}}',
  ];
  const out: string = await new Promise((res) => {
    const c = spawn("claude", args, {
      cwd,
      env: envFor("A"),
      stdio: ["ignore", "pipe", "inherit"],
    });
    let s = "";
    c.stdout.on("data", (d) => {
      s += d;
    });
    c.on("close", () => res(s));
  });
  rmSync(cwd, { recursive: true, force: true });
  const init = out
    .split("\n")
    .filter(Boolean)
    .map((l) => {
      try {
        return JSON.parse(l);
      } catch {
        return null;
      }
    })
    .find((e) => e?.type === "system" && e?.subtype === "init");
  if (!init) {
    console.log("no init event; raw output:\n" + out.slice(0, 2000));
    process.exit(1);
  }
  const { tools, mcp_servers, model, ...rest } = init;
  console.log(
    JSON.stringify(
      { model, tools, mcp_servers, other_keys: Object.keys(rest) },
      null,
      2,
    ),
  );
  console.log(
    "Check: tools should be only what arm A allows plus built-ins you expect; mcp_servers should be empty.",
  );
}

async function main() {
  if (values.preflight) return preflight();
  const conc = Math.max(1, Number(values.concurrency));
  let next = 0;
  await Promise.all(
    Array.from({ length: conc }, async () => {
      while (next < jobs.length) await runJob(jobs[next++]!);
    }),
  );
  console.log(
    `done. grade with: pnpm --filter @yokel/docketclock bench:grade --run ${runDir}`,
  );
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
