/**
 * Migration runner — applies migrations/*.sql in lexical order, exactly once, inside a transaction
 * each. Idempotent: applied files are recorded in `schema_migrations` and skipped on re-run. This is
 * what the CNPG-aware migration Job runs in-cluster (charts/docketclock/templates/migrate-job.yaml),
 * and what the local tests run against a throwaway Postgres.
 *
 * Run: DATABASE_URL=... pnpm --filter @yokel/docketclock migrate
 */
import { readdir, readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createClient, type Sql } from "./client.js";

// Resolved relative to this module: src/db/ -> migrations/ when run via tsx, and dist/db/ ->
// dist/migrations/ when run compiled (the chart Job runs `node dist/db/migrate.js`). `pnpm build`
// copies migrations/ into dist/ so both layouts find the .sql files at ../../migrations.
const MIGRATIONS_DIR = join(
  dirname(fileURLToPath(import.meta.url)),
  "..",
  "..",
  "migrations",
);

export async function runMigrations(sql: Sql): Promise<string[]> {
  await sql`
    create table if not exists schema_migrations (
      filename   text primary key,
      applied_at timestamptz not null default now()
    )
  `;

  const files = (await readdir(MIGRATIONS_DIR))
    .filter((f) => f.endsWith(".sql"))
    .sort();
  const applied: string[] = [];

  for (const filename of files) {
    const already =
      await sql`select 1 from schema_migrations where filename = ${filename}`;
    if (already.length > 0) continue;

    const ddl = await readFile(join(MIGRATIONS_DIR, filename), "utf8");
    // One transaction per migration: DDL + the schema_migrations bookmark commit or roll back together.
    await sql.begin(async (tx) => {
      await tx.unsafe(ddl);
      await tx`insert into schema_migrations (filename) values (${filename})`;
    });
    applied.push(filename);
  }
  return applied;
}

// CLI entrypoint — only when run directly, not when imported by tests. pathToFileURL canonicalizes
// argv[1] (which may be a relative path, e.g. `dist/db/migrate.js`) so the comparison is robust.
const invokedPath = process.argv[1];
if (invokedPath && import.meta.url === pathToFileURL(invokedPath).href) {
  const sql = createClient();
  try {
    const applied = await runMigrations(sql);
    console.log(
      applied.length
        ? `✅ applied: ${applied.join(", ")}`
        : "✅ schema up to date (nothing to apply)",
    );
  } finally {
    await sql.end();
  }
}
