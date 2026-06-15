/**
 * Postgres client factory (postgres.js). The app talks to Postgres by connection string only — no
 * lock-in (ADR 0008). DATABASE_URL is injected from the CloudNativePG-managed `<cluster>-app` Secret
 * in-cluster; locally it points at a throwaway Postgres.
 */
import postgres from "postgres";

export type Sql = postgres.Sql;

/** Resolve the connection string or fail loudly — a silent default would mask a misconfig in-cluster. */
export function databaseUrl(): string {
  const url = process.env.DATABASE_URL;
  if (!url) throw new Error("DATABASE_URL is not set");
  return url;
}

export function createClient(url: string = databaseUrl()): Sql {
  return postgres(url, { onnotice: () => {} }); // silence NOTICE chatter (e.g. IF NOT EXISTS skips)
}
