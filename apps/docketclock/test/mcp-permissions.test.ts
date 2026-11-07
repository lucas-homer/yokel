import assert from "node:assert/strict";
import { createMcpDatabase, assertMcpReader } from "../src/mcp/database.js";
import { withMcpRead } from "../src/api/mcp-queries.js";

function testUrl(name: string): string {
  const value = process.env[name];
  if (
    !value ||
    !/^\/docketclock_mcp_test(?:_[a-z0-9_]+)?$/.test(new URL(value).pathname)
  )
    throw new Error(
      `${name} must identify a disposable docketclock_mcp_test[_suffix] database`,
    );
  return value;
}
const reader = createMcpDatabase(testUrl("MCP_TEST_READER_URL"));
const owner = createMcpDatabase(testUrl("MCP_TEST_DATABASE_URL"));
try {
  await assertMcpReader(reader);
  await assert.rejects(assertMcpReader(owner), /non-owner/);
  // Turn off the session default to prove grants, not just the default, deny DML.
  await assert.rejects(
    reader.begin("read write", async (tx) => {
      await tx`delete from participation_windows where false`;
    }),
    (e: unknown) => (e as { code: string }).code === "42501",
  );
  await assert.rejects(
    reader`select * from poll_dead_letter`,
    (e: unknown) => (e as { code: string }).code === "42501",
  );
  await assert.rejects(
    withMcpRead(reader, async (tx) => {
      await tx`select pg_sleep(3)`;
    }),
    (e: unknown) => (e as { code: string }).code === "57014",
  );
  const start = performance.now();
  await assert.rejects(
    withMcpRead(reader, async (tx) => {
      for (let i = 0; i < 10; i++) await tx`select pg_sleep(0.7)`;
    }),
  );
  assert.ok(
    performance.now() - start < 6500,
    "Whole transaction must stop near 5s",
  );
  await assertMcpReader(reader); // Timed-out reads leave the pool usable.
  console.log(
    "PASS SELECT-only role, owner rejection, DML denial, unrelated-table denial, statement and transaction timeouts",
  );
} finally {
  await reader.end({ timeout: 1 });
  await owner.end({ timeout: 1 });
}
