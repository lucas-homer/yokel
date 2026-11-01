/**
 * review-cli-args.test.ts — the review CLI's ARGUMENT-SIDE validation (#117 discipline: a bad
 * invocation prints usage or a specific message and exits 2 BEFORE any database connection). Spawns
 * the real CLI with no DATABASE_URL so a validation gap would surface as a connection error, not a
 * usage line. Covers the PR-A3 `log` / `corpus` flags and the shared unknown-option handling.
 *
 * Needs no database.
 */
import { execFile } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";

const run = promisify(execFile);
const APP = join(dirname(fileURLToPath(import.meta.url)), "..");
const TSX = join(APP, "node_modules", ".bin", "tsx");

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

async function cli(
  ...args: string[]
): Promise<{ code: number; stderr: string; stdout: string }> {
  const env = { ...process.env };
  delete env.DATABASE_URL;
  try {
    const r = await run(TSX, ["src/review/cli.ts", ...args], {
      cwd: APP,
      env,
      timeout: 60_000,
    });
    return { code: 0, stderr: r.stderr, stdout: r.stdout };
  } catch (e) {
    const err = e as { code?: number; stderr?: string; stdout?: string };
    return {
      code: typeof err.code === "number" ? err.code : -1,
      stderr: err.stderr ?? "",
      stdout: err.stdout ?? "",
    };
  }
}

const cases: {
  name: string;
  args: string[];
  expect: RegExp;
}[] = [
  { name: "no command → usage", args: [], expect: /^usage: review/m },
  {
    name: "unknown command → usage",
    args: ["frobnicate"],
    expect: /^usage: review/m,
  },
  {
    name: "queue --bogus → unknown option reported, then usage",
    args: ["queue", "--bogus"],
    expect: /Unknown option[\s\S]*usage: review/,
  },
  {
    name: "queue with a stray positional → reported, then usage",
    args: ["queue", "unexpected"],
    expect: /Unexpected argument[\s\S]*usage: review/,
  },
  {
    name: "log --since with a word → specific message",
    args: ["log", "--since", "yesterday"],
    expect: /--since takes/,
  },
  {
    name: "log --since with an impossible date → specific message",
    args: ["log", "--since", "2026-02-30"],
    expect: /--since takes/,
  },
  {
    name: "log --since with an absurd relative window → specific message, not Invalid Date",
    args: ["log", "--since", "999999999999999999h"],
    expect: /--since takes/,
  },
  {
    name: "log --limit 1e100 → specific message (not a safe integer)",
    args: ["log", "--limit", "1e100"],
    expect: /--limit must be an integer from 1 to 10000/,
  },
  {
    name: "log --limit 0 → specific message",
    args: ["log", "--limit", "0"],
    expect: /--limit must be an integer from 1 to 10000/,
  },
  {
    name: "log --limit 10001 → specific message",
    args: ["log", "--limit", "10001"],
    expect: /--limit must be an integer from 1 to 10000/,
  },
  {
    name: "log --operator '' → specific message",
    args: ["log", "--operator", ""],
    expect: /--operator must not be empty/,
  },
  {
    name: "log --reviewer bot → specific message",
    args: ["log", "--reviewer", "bot"],
    expect: /--reviewer must be one of human \| agent/,
  },
  {
    name: "log --kind nope → specific message",
    args: ["log", "--kind", "nope"],
    expect: /--kind must be one of/,
  },
  {
    name: "log --bogus → unknown option reported, then usage",
    args: ["log", "--bogus"],
    expect: /Unknown option[\s\S]*usage: review/,
  },
  {
    name: "corpus --bogus → unknown option reported, then usage",
    args: ["corpus", "--bogus"],
    expect: /Unknown option[\s\S]*usage: review/,
  },
  {
    name: "show --bogus (pre-existing command) → unknown option reported, then usage",
    args: ["show", "ocd-participation-window/federal/x", "--bogus"],
    expect: /Unknown option[\s\S]*usage: review/,
  },
  {
    name: "resolve without --kind → usage",
    args: ["resolve", "ocd-participation-window/federal/x", "--note", "n"],
    expect: /^usage: review/m,
  },
  {
    name: "resolve --expect <fingerprint> → refused: fingerprints are for the ledger skip, never --expect",
    args: [
      "resolve",
      "ocd-participation-window/federal/x",
      "--kind",
      "pin_close",
      "--close",
      "2026-10-01",
      "--note",
      "n",
      "--reviewer",
      "agent",
      "--operator",
      "autopilot",
      "--expect",
      "fp1:" + "a".repeat(64),
    ],
    expect:
      /--expect takes sha256 hex payload hashes[\s\S]*fingerprint= value is for the ledger skip only/,
  },
];

for (const c of cases) {
  const r = await cli(...c.args);
  assert(
    `${c.name} (exit 2, no connection attempt)`,
    r.code === 2 &&
      c.expect.test(r.stderr) &&
      !/DATABASE_URL|ECONNREFUSED|connect/i.test(r.stderr + r.stdout),
    `exit=${r.code} stderr=${JSON.stringify(r.stderr.slice(0, 200))}`,
  );
}

console.log(`review-cli-args.test.ts\n${out.join("\n")}`);
if (failures > 0) {
  console.error(`\n${failures} failure(s)`);
  process.exit(1);
}
console.log("\nall passed");
