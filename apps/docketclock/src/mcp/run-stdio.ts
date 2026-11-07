/** Explicit entrypoint: never starts pollers, migrations, reconciliation, HTTP or an LLM. */
import {
  serveStdio,
  StdioServerTransport,
} from "@modelcontextprotocol/server/stdio";
import pino from "pino";
import { assertMcpReader, createMcpDatabase } from "./database.js";
import { createToolService } from "./service.js";
import { createMcpServer } from "./server.js";

const log = pino(
  { level: "info", base: { component: "mcp-stdio" } },
  pino.destination(2),
);
const url = process.env.MCP_DATABASE_URL;
if (!url) {
  log.error("MCP_DATABASE_URL is required; use a dedicated SELECT-only role");
  process.exitCode = 1;
} else {
  const sql = createMcpDatabase(url);
  try {
    await assertMcpReader(sql);
    const service = createToolService(sql);
    const handle = serveStdio(
      () =>
        createMcpServer(
          async (name, args) => (await service(name, args)).output,
          {},
          (event) => log.info(event, "tool_call"),
        ),
      {
        transport: new StdioServerTransport(process.stdin, process.stdout, {
          maxBufferSize: 16 * 1024,
        }),
        onerror: () => log.warn("MCP transport error"),
      },
    );
    let closing = false;
    const close = async () => {
      if (closing) return;
      closing = true;
      await handle.close();
      await sql.end({ timeout: 2 });
    };
    process.once("SIGINT", () => {
      void close();
    });
    process.once("SIGTERM", () => {
      void close();
    });
    process.stdin.once("end", () => {
      void close();
    });
    process.stdin.once("close", () => {
      void close();
    });
  } catch {
    // Never log an exception containing a connection URL, SQL or source payload.
    log.error("MCP startup rejected database configuration or permissions");
    process.exitCode = 1;
    await sql.end({ timeout: 2 });
  }
}
