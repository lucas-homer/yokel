/**
 * Differential-poll cursor persistence (issue #18 poll-loop slice). Reads/writes the per-source
 * checkpoint row in `poll_cursor` (0004) — the MAX lastModifiedDate (UTC) the differential poll has
 * consumed so far. This is MUTABLE operational state, NOT the append-only spine: the observation log
 * alone re-derives every window, so the cursor is a pure throughput optimization (it bounds the
 * lastModifiedDate filter so a poll re-fetches only what changed since last run).
 *
 * The cursor is advanced from the LIST item's lastModifiedDate, NEVER a detail payload's modifyDate
 * (the NOTE(cursor-slice) trap in regulations-gov.ts) — that wiring lives in the caller (poll.ts);
 * this module only persists whatever UTC-ISO instant it is handed, with a monotonic forward-only guard.
 */
import type { Sql } from "../db/client.js";

/** The stored cursor (max lastModifiedDate consumed) as a UTC ISO string, or null before the first run. */
export async function readCursor(
  sql: Sql,
  source: string,
): Promise<string | null> {
  const [row] = await sql<{ cursor_last_modified: Date | null }[]>`
    select cursor_last_modified
    from poll_cursor
    where source = ${source}
  `;
  if (!row || row.cursor_last_modified === null) return null;
  // postgres.js returns timestamptz as a Date; the cursor is carried as a UTC ISO string everywhere else.
  return row.cursor_last_modified instanceof Date
    ? row.cursor_last_modified.toISOString()
    : row.cursor_last_modified;
}

/**
 * Upsert the cursor for `source`. MONOTONIC FORWARD-ONLY: if the stored cursor is already newer than
 * (or equal to) the supplied one, the stored value is KEPT — a late or empty poll must never regress
 * the checkpoint (which would re-fetch already-consumed history and risk re-crossing the 6h overlap
 * window pointlessly). The guard is enforced in SQL (greatest()) so it holds atomically on conflict.
 *
 * `last_polled_at` is always refreshed (it records the poll attempt, not the cursor), so an empty poll
 * still stamps that we ran without moving the cursor.
 */
export async function writeCursor(
  sql: Sql,
  source: string,
  cursorUtcIso: string,
  polledAt: Date,
): Promise<void> {
  const cursor = new Date(cursorUtcIso);
  if (Number.isNaN(cursor.getTime()))
    throw new Error(`writeCursor: invalid cursor "${cursorUtcIso}"`);
  await sql`
    insert into poll_cursor (source, cursor_last_modified, last_polled_at, updated_at)
    values (${source}, ${cursor.toISOString()}, ${polledAt.toISOString()}, now())
    on conflict (source) do update set
      -- forward-only: keep whichever is newer (greatest is NULL-tolerant only if both are non-null; the
      -- stored value is non-null here because a row exists with a previously-written cursor — but a row
      -- could exist with a NULL cursor if last_polled_at was stamped on an empty first poll, so coalesce).
      cursor_last_modified = greatest(
        poll_cursor.cursor_last_modified,
        excluded.cursor_last_modified
      ),
      last_polled_at = excluded.last_polled_at,
      updated_at = now()
  `;
}

/**
 * Stamp ONLY last_polled_at for a poll that consumed no list items (so we never move the cursor). Keeps
 * the "we ran" signal current without an artificial cursor advance.
 */
export async function touchPolledAt(
  sql: Sql,
  source: string,
  polledAt: Date,
): Promise<void> {
  await sql`
    insert into poll_cursor (source, cursor_last_modified, last_polled_at, updated_at)
    values (${source}, ${null}, ${polledAt.toISOString()}, now())
    on conflict (source) do update set
      last_polled_at = excluded.last_polled_at,
      updated_at = now()
  `;
}

/**
 * Stamp `last_checked_at = when` for a Regs.gov document in `regs_poll_watch` — the per-document re-poll
 * throttle (adversary fixes #5 + #2). Called whenever we SUCCESSFULLY fetch a document's detail, in BOTH
 * the differential pass and the re-poll pass. MONOTONIC FORWARD-ONLY (greatest()) so an out-of-order/late
 * stamp never regresses the throttle and re-opens a just-checked document for an immediate re-poll.
 *
 * This is MUTABLE operational state (see 0004), so this is a plain upsert — NOT an append to the log.
 */
export async function stampChecked(
  sql: Sql,
  regsDocumentId: string,
  when: Date,
): Promise<void> {
  await sql`
    insert into regs_poll_watch (regs_document_id, last_checked_at, updated_at)
    values (${regsDocumentId}, ${when.toISOString()}, now())
    on conflict (regs_document_id) do update set
      last_checked_at = greatest(regs_poll_watch.last_checked_at, excluded.last_checked_at),
      updated_at = now()
  `;
}
