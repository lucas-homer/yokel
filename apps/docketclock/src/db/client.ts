/**
 * Postgres client factory (postgres.js). The app talks to Postgres by connection string only — no
 * lock-in (ADR 0008). DATABASE_URL is injected from the CloudNativePG-managed `<cluster>-app` Secret
 * in-cluster; locally it points at a throwaway Postgres.
 */
import postgres from "postgres";

export type Sql = postgres.Sql;
/**
 * A query handle that is EITHER the pool client or a transaction-scoped `tx` from `sql.begin`.
 * postgres.js types the two as siblings (both extend its ISql), so a function that must run inside a
 * caller's transaction takes this instead of `Sql`. It can run tagged queries, `.json()` and the
 * identifier helper; it cannot `.begin()` or `.end()` — exactly the point.
 */
export type SqlHandle = postgres.Sql | postgres.TransactionSql;

/** Resolve the connection string or fail loudly — a silent default would mask a misconfig in-cluster. */
export function databaseUrl(): string {
  const url = process.env.DATABASE_URL;
  if (!url) throw new Error("DATABASE_URL is not set");
  return url;
}

/**
 * idle_timeout closes a pooled connection after 2 idle minutes, so the pool never hands out a socket the
 * server side may already have dropped (Neon cuts every connection when it scales to zero, after 5 minutes
 * without queries). postgres.js reconnects transparently on the next query.
 */
export const IDLE_TIMEOUT_SECONDS = 120;

export function createClient(url: string = databaseUrl()): Sql {
  return postgres(url, {
    onnotice: () => {}, // silence NOTICE chatter (e.g. IF NOT EXISTS skips)
    idle_timeout: IDLE_TIMEOUT_SECONDS,
  });
}

/**
 * A ONE-connection client for session-scoped state (the poll-cycle advisory lock, cycle-lock.ts). Use this
 * instead of `sql.reserve()` for anything that must outlive a dropped socket: postgres.js 3.4 crashes the
 * process (an uncaught TypeError in `nextWrite`) when a query runs on a RESERVED connection whose socket has
 * already closed, and `release()` hands that dead connection back to the pool. A plain max:1 client instead
 * reconnects on its next query, so a dropped session costs one failed query, never the process.
 */
export function createSessionClient(url: string = databaseUrl()): Sql {
  return postgres(url, { onnotice: () => {}, max: 1 });
}
