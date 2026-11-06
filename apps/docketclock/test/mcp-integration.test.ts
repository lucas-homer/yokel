/** Actual stdio subprocess + actual SELECT-only PG role. Fixtures are synthetic, never legal truth. */
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { performance } from "node:perf_hooks";
import { Client } from "@modelcontextprotocol/client";
import { StdioClientTransport } from "@modelcontextprotocol/client/stdio";
import { DISCLAIMER, ParticipationWindow } from "@yokel/contracts";
import { createClient } from "../src/db/client.js";
import { createMcpDatabase, assertMcpReader } from "../src/mcp/database.js";
import { TOOL_DEFINITIONS } from "../src/mcp/service.js";
import { cases, seedEvaluation } from "./fixtures/mcp-evaluation.js";
import { MAX_RESULT_BYTES } from "../src/mcp/server.js";
import { resolveWindow, withMcpRead } from "../src/api/mcp-queries.js";

function guardedUrl(name: string) {
  const value = process.env[name];
  if (!value) throw new Error(`${name} required`);
  const url = new URL(value);
  if (
    !["postgres:", "postgresql:"].includes(url.protocol) ||
    !/^\/docketclock_mcp_test(?:_[a-z0-9_]+)?$/.test(url.pathname) ||
    url.search
  )
    throw new Error(
      "Expected a disposable MCP test URL without routing overrides",
    );
  return value;
}
function objects(value: unknown): Record<string, unknown>[] {
  if (Array.isArray(value)) return value.flatMap(objects);
  if (value !== null && typeof value === "object")
    return [
      value as Record<string, unknown>,
      ...Object.values(value).flatMap(objects),
    ];
  return [];
}
const writerUrl = guardedUrl("MCP_TEST_DATABASE_URL");
const readerUrl = guardedUrl("MCP_TEST_READER_URL");
assert.equal(new URL(writerUrl).pathname, new URL(readerUrl).pathname);
const writer = createClient(writerUrl);
try {
  await seedEvaluation(writer);
} finally {
  await writer.end();
}
const reader = createMcpDatabase(readerUrl);
await assertMcpReader(reader);
const transport = new StdioClientTransport({
  command: process.execPath,
  args: ["--import", "tsx", "src/mcp/run-stdio.ts"],
  cwd: process.cwd(),
  env: { MCP_DATABASE_URL: readerUrl },
  stderr: "pipe",
});
let stderr = "";
transport.stderr?.on("data", (chunk: Buffer) => {
  stderr += chunk.toString();
});
const client = new Client({
  name: "docketclock-phase0-evaluation",
  version: "1",
});
const timings: number[] = [];
async function call(
  name: keyof typeof TOOL_DEFINITIONS,
  args: Record<string, unknown>,
) {
  const started = performance.now();
  const result = await client.callTool({ name, arguments: args });
  timings.push(performance.now() - started);
  assert.equal(result.content.length, 1);
  const content = result.content[0]!;
  assert.equal(content.type, "text");
  if (content.type !== "text") throw new Error("Expected text");
  const output = JSON.parse(content.text) as Record<string, unknown>;
  assert.deepEqual(result.structuredContent, output);
  assert.equal(output.disclaimer, DISCLAIMER);
  assert.ok(content.text.startsWith('{"disclaimer":'));
  assert.ok(Buffer.byteLength(JSON.stringify(result)) <= MAX_RESULT_BYTES);
  TOOL_DEFINITIONS[name].outputSchema.parse(output);
  return { result, output };
}
try {
  await client.connect(transport);
  console.log(
    `MCP negotiated revision: ${client.getNegotiatedProtocolVersion()}`,
  );
  const list = await client.listTools();
  assert.equal(list.tools.length, 6);
  for (const item of cases) {
    const { result, output } = await call(item.tool, item.args);
    assert.ok(!result.isError, `${item.id}: ${JSON.stringify(output)}`);
    let records = objects(output);
    const windows = records.filter(
      (r) => typeof r.ocd_id === "string" && "resolved_close_utc" in r,
    );
    for (const id of item.expected.windowIds ?? [])
      assert.ok(
        windows.some((w) => w.ocd_id === id),
        `${item.id}: missing window ${id}`,
      );
    if (item.expected.confidence)
      assert.ok(
        windows.some((w) => w.confidence === item.expected.confidence),
        item.id,
      );
    if ("close" in item.expected)
      assert.ok(
        windows.some((w) => w.resolved_close_utc === item.expected.close),
        item.id,
      );
    for (const flag of item.expected.flags ?? [])
      assert.ok(
        windows.some((w) => (w.conflict_flags as string[]).includes(flag)),
        `${item.id}: ${flag}`,
      );
    if (item.args.section === "verdicts") {
      const followup = await call("explain_window", {
        id: item.args.id,
        section: "observations",
        limit: 20,
      });
      records = [...records, ...objects(followup.output)];
    }
    for (const id of item.expected.observationIds ?? [])
      assert.ok(
        records.some(
          (r) =>
            r.observation_id === id ||
            (Array.isArray(r.observation_ids) &&
              r.observation_ids.includes(id)),
        ),
        `${item.id}: missing observation ${id}`,
      );
    const verdicts = records.filter((r) => "honoring" in r && "reviewer" in r);
    if (
      item.expected.authority === "human" ||
      item.expected.authority === "agent"
    )
      assert.ok(
        verdicts.some(
          (r) =>
            r.honoring === "honored" && r.reviewer === item.expected.authority,
        ),
        item.id,
      );
    if (item.expected.verdictState === "superseded")
      assert.ok(
        verdicts.some((r) => r.honoring === "superseded"),
        item.id,
      );
    if (item.expected.verdictState === "escalated")
      assert.ok(
        verdicts.some(
          (r) =>
            r.honoring === "honored" &&
            r.kind === "escalate" &&
            r.effect === "parked",
        ),
        item.id,
      );
    for (const verdict of verdicts) {
      assert.equal(verdict.operator, null);
      assert.equal(verdict.redacted, true);
    }
    // Compare every displayed canonical scalar against the same stored read model.
    for (const window of windows) {
      const canonical = await withMcpRead(reader, (tx) =>
        resolveWindow(tx, String(window.ocd_id)),
      );
      assert.ok(canonical);
      ParticipationWindow.parse(canonical);
      for (const field of [
        "ocd_id",
        "confidence",
        "conflict_flags",
        "resolved_close_utc",
        "resolved_close_display",
        "version",
      ] as const)
        assert.deepEqual(
          window[field],
          canonical[field],
          `${item.id}: ${field}`,
        );
    }
    console.log(`PASS ${item.id}`);
  }
  const submitted = await call("get_submission_info", {
    id: "2026-EVAL-SUBMIT",
  });
  assert.equal(
    (submitted.output.data as { availability: string }).availability,
    "stored_link",
  );
  for (const [name, args, code] of [
    [
      "fetch",
      { id: "ocd-participation-window/state/ca/example" },
      "invalid_input",
    ],
    ["fetch", { id: "2026-ABSENT" }, "not_found"],
    ["list_windows", { limit: 21 }, "invalid_input"],
    [
      "explain_window",
      { id: "2026-EVAL-HIGH", expected_version: 999 },
      "stale_read",
    ],
    [
      "explain_window",
      { id: "2026-EVAL-HIGH", section: "observations", offset: 1 },
      "invalid_input",
    ],
  ] as const) {
    const { result, output } = await call(name, args);
    assert.equal(result.isError, true);
    assert.equal((output.error as { code: string }).code, code);
  }
  assert.ok(!stderr.includes(new URL(readerUrl).password));
  assert.ok(!stderr.includes("SYNTHETIC evaluation decision"));
  assert.ok(stderr.includes('"tool_call"'));
  timings.sort((a, b) => a - b);
  if (transport.pid !== null) {
    try {
      const rssKiB = Number(
        execFileSync("ps", ["-o", "rss=", "-p", String(transport.pid)], {
          encoding: "utf8",
        }).trim(),
      );
      if (Number.isFinite(rssKiB))
        console.log(
          `Stdio server RSS after corpus: ${(rssKiB / 1024).toFixed(1)} MiB (snapshot, not peak)`,
        );
    } catch {
      /* ps is an optional local measurement, not a correctness prerequisite. */
    }
  }
  console.log(
    `PASS stdio/PG corpus, trust parity, follow-ups, errors and redaction; ${timings.length} calls, local p95=${timings[Math.ceil(timings.length * 0.95) - 1]!.toFixed(1)}ms (synthetic sequential load, not operator usefulness)`,
  );
} finally {
  await client.close();
  await reader.end({ timeout: 1 });
}
