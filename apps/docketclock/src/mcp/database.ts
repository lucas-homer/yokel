/** Stdio is local, but still uses a separate SELECT-only database principal. */
import postgres from "postgres";
import type { Sql } from "../db/client.js";

export const MCP_READ_TABLES = [
  "participation_windows",
  "observations",
  "observation_targets",
  "conflict_records",
] as const;

export function createMcpDatabase(url: string): Sql {
  return postgres(url, {
    max: 4,
    connect_timeout: 3,
    idle_timeout: 20,
    onnotice: () => {},
    connection: {
      application_name: "docketclock-mcp-phase0",
      default_transaction_read_only: true,
      statement_timeout: 2000,
      search_path: "pg_catalog, public",
    },
  });
}

/** Fail closed for owner/poller credentials, inherited roles and extra writable surfaces.
 * This is a startup guard, not a replacement for DB grants or read-only transactions.
 */
export async function assertMcpReader(sql: Sql): Promise<void> {
  const [role] = await sql`
    select r.rolsuper, r.rolcreaterole, r.rolcreatedb, r.rolreplication, r.rolbypassrls,
      (select d.datdba = r.oid from pg_database d where d.datname = current_database()) as db_owner,
      exists(select 1 from pg_roles other where other.oid <> r.oid
        and pg_has_role(current_user, other.oid, 'MEMBER')) as memberships
    from pg_roles r where r.rolname = current_user
  `;
  if (!role || Object.values(role).some(Boolean))
    throw new Error(
      "MCP requires an unprivileged, non-owner database role without memberships",
    );
  const schemas = await sql`
    select nspname from pg_namespace where nspname !~ '^pg_' and nspname <> 'information_schema'
      and has_schema_privilege(current_user, oid, 'CREATE')
  `;
  if (schemas.length)
    throw new Error("MCP database role must not create schema objects");
  const tables = await sql`
    select n.nspname, c.relname, c.relowner = (select oid from pg_roles where rolname = current_user) as owned,
      has_table_privilege(current_user, c.oid, 'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') as writable,
      has_any_column_privilege(current_user, c.oid, 'INSERT,UPDATE,REFERENCES') as column_writable,
      has_table_privilege(current_user, c.oid, 'SELECT') as readable
    from pg_class c join pg_namespace n on n.oid = c.relnamespace
    where c.relkind in ('r','p','v','m','f') and n.nspname !~ '^pg_' and n.nspname <> 'information_schema'
  `;
  if (
    tables.some(
      (t) =>
        t.owned ||
        t.writable ||
        t.column_writable ||
        (t.readable &&
          (t.nspname !== "public" || !MCP_READ_TABLES.includes(t.relname))),
    )
  )
    throw new Error(
      "MCP role must have SELECT only on the four delivery tables",
    );
  if (
    MCP_READ_TABLES.some(
      (name) =>
        !tables.some(
          (t) => t.nspname === "public" && t.relname === name && t.readable,
        ),
    )
  )
    throw new Error(
      "MCP role is missing a required delivery-table SELECT grant",
    );
  const functions = await sql`
    select p.oid from pg_proc p join pg_namespace n on n.oid = p.pronamespace
    where p.prosecdef and n.nspname !~ '^pg_' and n.nspname <> 'information_schema'
      and has_function_privilege(current_user, p.oid, 'EXECUTE')
  `;
  if (functions.length)
    throw new Error(
      "MCP role must not execute application security-definer functions",
    );
}
