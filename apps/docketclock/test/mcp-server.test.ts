import assert from "node:assert/strict";
import { Client } from "@modelcontextprotocol/client";
import { InMemoryTransport } from "@modelcontextprotocol/server";
import { DISCLAIMER } from "@yokel/contracts";
import {
  createMcpServer,
  toolError,
  MAX_RESULT_BYTES,
} from "../src/mcp/server.js";
import {
  parseSearchQuery,
  nextSearchQuery,
  QuerySyntaxError,
} from "../src/mcp/query.js";

const parsed = parseSearchQuery(
  'agency:environmental-protection-agency "water quality" status:open',
);
assert.equal(parsed.keyword, "water quality");
assert.equal(parsed.limit, 10);
assert.deepEqual(parseSearchQuery(nextSearchQuery(parsed, 10)), {
  ...parsed,
  offset: 10,
});
for (const query of [
  "bad:filter",
  "status:open status:closed",
  "offset:-1",
  '"unterminated',
  "after:2026-11-01T00:00:00Z before:2026-10-01T00:00:00Z",
])
  assert.throws(() => parseSearchQuery(query));
assert.throws(() => parseSearchQuery("status:"), QuerySyntaxError);

let mode = "normal";
let calls = 0;
let release: (() => void) | undefined;
const blocked = new Promise<void>((resolve) => {
  release = resolve;
});
const audit: unknown[] = [];
const server = createMcpServer(
  async () => {
    calls++;
    if (mode === "throw") throw new Error("SECRET database SQL");
    if (mode === "invalid")
      return { confidence: "high", resolved_close_utc: null };
    if (mode === "block") await blocked;
    return toolError("internal_error", "No fixture for this call");
  },
  {},
  (event) => audit.push(event),
);
const client = new Client({ name: "docketclock-contract-smoke", version: "1" });
const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
try {
  await server.connect(serverTransport);
  await client.connect(clientTransport);
  const listed = await client.listTools();
  assert.deepEqual(listed.tools.map((t) => t.name).sort(), [
    "explain_window",
    "fetch",
    "get_submission_info",
    "list_conflicts",
    "list_windows",
    "search",
  ]);
  for (const tool of listed.tools) {
    assert.equal(tool.annotations?.readOnlyHint, true);
    assert.equal(tool.annotations?.destructiveHint, false);
    assert.ok(tool.outputSchema);
  }
  const result = await client.callTool({
    name: "fetch",
    arguments: { id: "2026-10001" },
  });
  assert.equal(result.isError, true);
  assert.equal(result.content.length, 1);
  assert.equal(result.content[0]?.type, "text");
  if (result.content[0]?.type !== "text")
    throw new Error("Missing text mirror");
  assert.deepEqual(
    JSON.parse(result.content[0].text),
    result.structuredContent,
  );
  assert.equal(
    (result.structuredContent as Record<string, unknown>).disclaimer,
    DISCLAIMER,
  );
  assert.ok(Buffer.byteLength(JSON.stringify(result)) <= MAX_RESULT_BYTES);
  assert.ok(result.content[0].text.startsWith('{"disclaimer":'));
  await assert.rejects(client.callTool({ name: "__proto__", arguments: {} }));
  assert.equal(calls, 1, "Unknown tool must not dispatch");
  for (mode of ["throw", "invalid"]) {
    const error = await client.callTool({
      name: "fetch",
      arguments: { id: "2026-10001" },
    });
    assert.equal(error.isError, true);
    assert.equal(
      (error.structuredContent as Record<string, unknown>).confidence,
      "unknown",
    );
    assert.ok(!JSON.stringify(error).includes("SECRET"));
  }
  mode = "block";
  const pending = Array.from({ length: 4 }, () =>
    client.callTool({ name: "fetch", arguments: { id: "2026-10001" } }),
  );
  // In-memory requests are dispatched on queued microtasks.
  await new Promise((resolve) => setImmediate(resolve));
  const limited = await client.callTool({
    name: "fetch",
    arguments: { id: "2026-10001" },
  });
  assert.equal(
    (limited.structuredContent as { error: { code: string } }).error.code,
    "rate_limited",
  );
  release!();
  await Promise.all(pending);
  assert.equal(audit.length, 8);
  console.log(
    "PASS MCP SDK negotiation, six tool schemas, JSON mirror, error sanitization, concurrency cap and lexical grammar",
  );
} finally {
  release!();
  await client.close();
  await server.close();
}
