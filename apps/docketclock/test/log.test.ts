/**
 * log.test.ts — pins the LOGGER CONTRACT of src/log.ts (PR-A1), not log spam. Hermetic: every assertion
 * runs against a logger built over a CAPTURE stream (a plain { write } sink pino flushes to synchronously),
 * never the real stdout/global. We exercise the REAL exported functions — buildLogger + componentLogger —
 * just with their sink swapped, so the function under test is genuine.
 *
 * Proves:
 *   (a) componentLogger("x") binds a `component` field on every line.
 *   (b) LOG_LEVEL is honored — a debug call is SUPPRESSED at the default "info" and EMITTED at "debug".
 *   (c) the default level falls back to "info" when LOG_LEVEL is unset.
 *
 * Repo style: hand-rolled assert, out[] accumulator, failures counter, process.exit (matches api/regs/etc).
 */
import { buildLogger, componentLogger } from "../src/log.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = ""): void {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

/** A synchronous capture sink — pino writes one NDJSON line per log call; collect + parse them. */
function capture(): {
  lines: () => Record<string, unknown>[];
  stream: { write(s: string): void };
} {
  const chunks: string[] = [];
  return {
    stream: {
      write(s: string): void {
        chunks.push(s);
      },
    },
    lines: () =>
      chunks
        .join("")
        .split("\n")
        .filter((l) => l.trim().length > 0)
        .map((l) => JSON.parse(l) as Record<string, unknown>),
  };
}

// ── (a) componentLogger binds `component` ─────────────────────────────────────────────────────────────
{
  const cap = capture();
  const base = buildLogger({ level: "info", destination: cap.stream });
  const log = componentLogger("poller", base);
  log.info({ surfaced: 3 }, "chain adjudicate cycle");
  const lines = cap.lines();
  assert(
    "componentLogger emits exactly one line",
    lines.length === 1,
    `got ${lines.length}`,
  );
  assert(
    "line carries component=poller",
    lines[0]?.component === "poller",
    JSON.stringify(lines[0]?.component),
  );
  assert("line carries the structured field", lines[0]?.surfaced === 3);
  assert(
    "line carries the message",
    lines[0]?.msg === "chain adjudicate cycle",
  );
}

// ── (b) LOG_LEVEL honored: debug suppressed at info, emitted at debug ─────────────────────────────────
{
  const cap = capture();
  const log = buildLogger({ level: "info", destination: cap.stream });
  log.debug({ chatty: true }, "should be suppressed at info");
  log.info({}, "info passes");
  const lines = cap.lines();
  assert(
    "at level=info a debug() line is suppressed",
    lines.length === 1,
    `got ${lines.length}`,
  );
  assert(
    "at level=info the info() line passes",
    lines[0]?.msg === "info passes",
  );
}
{
  const cap = capture();
  const log = buildLogger({ level: "debug", destination: cap.stream });
  log.debug({}, "now visible");
  const lines = cap.lines();
  assert(
    "at level=debug a debug() line is emitted",
    lines.length === 1,
    `got ${lines.length}`,
  );
  assert(
    "the emitted debug line keeps its message",
    lines[0]?.msg === "now visible",
  );
}

// ── (c) default level is info when LOG_LEVEL is unset ─────────────────────────────────────────────────
{
  const prev = process.env.LOG_LEVEL;
  delete process.env.LOG_LEVEL;
  try {
    const cap = capture();
    const log = buildLogger({ destination: cap.stream }); // no explicit level → env (unset) → "info"
    log.debug({}, "below default");
    log.info({}, "at default");
    const lines = cap.lines();
    assert(
      "default level suppresses debug (LOG_LEVEL unset → info)",
      lines.length === 1,
      `got ${lines.length}`,
    );
    assert(
      "buildLogger default level resolves to info",
      log.level === "info",
      log.level,
    );
  } finally {
    if (prev === undefined) delete process.env.LOG_LEVEL;
    else process.env.LOG_LEVEL = prev;
  }
}

// ── env override is read by buildLogger ───────────────────────────────────────────────────────────────
{
  const prev = process.env.LOG_LEVEL;
  process.env.LOG_LEVEL = "warn";
  try {
    const cap = capture();
    const log = buildLogger({ destination: cap.stream }); // sink swapped — keep the assertion off real stdout
    assert(
      "buildLogger reads LOG_LEVEL from env",
      log.level === "warn",
      log.level,
    );
  } finally {
    if (prev === undefined) delete process.env.LOG_LEVEL;
    else process.env.LOG_LEVEL = prev;
  }
}

// ── empty/whitespace LOG_LEVEL is treated as unset (would otherwise crash pino at construction) ─────────
{
  const prev = process.env.LOG_LEVEL;
  process.env.LOG_LEVEL = "   ";
  try {
    const cap = capture();
    const log = buildLogger({ destination: cap.stream });
    assert(
      "blank LOG_LEVEL falls back to info (not passed through to pino)",
      log.level === "info",
      log.level,
    );
  } finally {
    if (prev === undefined) delete process.env.LOG_LEVEL;
    else process.env.LOG_LEVEL = prev;
  }
}

console.log("\n=== log results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL PASS" : `${failures} FAILED`} (${out.length} assertions)`,
);
process.exit(failures === 0 ? 0 : 1);
