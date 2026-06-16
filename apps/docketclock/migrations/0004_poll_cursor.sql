-- 0004_poll_cursor.sql — the differential poll's per-source CHECKPOINT (issue #18 poll-loop slice).
--
-- UNLIKE `observations` (the immutable append-only spine, 0001), this is MUTABLE OPERATIONAL STATE: a
-- single small row per source that records how far the differential poll has consumed. It is a
-- checkpoint, NOT part of the trust spine — the observation log alone re-derives every window, and this
-- table can be dropped/reset and rebuilt by a re-poll without any loss of the audit trail. It therefore
-- deliberately carries NO append-only trigger; UPSERTing the cursor forward IS the intended operation.
--
-- `cursor_last_modified` is the MAX lastModifiedDate (UTC) consumed from the LIST response so far (NULL
-- before the first run — the poller then seeds an initial lookback rather than backfilling all history).
-- It is advanced MONOTONICALLY by the poller (writeCursor never moves it backward) so a late/empty poll
-- cannot regress it. The cursor is advanced from the LIST item's lastModifiedDate, never a detail
-- payload's modifyDate (the NOTE(cursor-slice) trap in regulations-gov.ts).
--
-- Idempotent: safe to re-run (guarded by IF NOT EXISTS).

create table if not exists poll_cursor (
  source               text primary key,        -- e.g. 'regulations_gov'
  cursor_last_modified timestamptz,             -- max lastModifiedDate (UTC) consumed; NULL before first run
  last_polled_at       timestamptz,
  updated_at           timestamptz not null default now()
);

-- regs_poll_watch — the per-DOCUMENT re-poll throttle stamp (issues #18 / adversary fixes #5 + #2).
--
-- Records when we last fetched a given Regs.gov document's DETAIL (in EITHER the differential pass or the
-- re-poll pass). This DECOUPLES the re-poll staleness throttle from the (dedupe-skipping) observation log:
--   * #5 — an unchanged re-polled window dedupe-skips ingest, so observations.fetched_at never advances and
--     the old "max(observations.fetched_at) < now-6h" throttle re-polled it EVERY cycle (budget blowout).
--     Stamping last_checked_at on every successful detail fetch makes the throttle advance even on a skip.
--   * #2 — an FR-discovered open window has a regs_document_id but NO regulations_gov observation yet, so the
--     old subquery was NULL and "NULL < x" is falsy → it was NEVER re-polled. coalesce(last_checked_at,
--     'epoch') makes a never-checked document maximally stale → eligible.
--
-- Like poll_cursor (and UNLIKE observations), this is MUTABLE OPERATIONAL STATE, NOT the append-only spine:
-- it can be dropped/reset and rebuilt by a re-poll with zero loss of the audit trail, and therefore carries
-- NO append-only trigger — UPSERTing the stamp forward IS the intended operation.
--
-- Idempotent: safe to re-run (guarded by IF NOT EXISTS).

create table if not exists regs_poll_watch (
  regs_document_id text primary key,
  last_checked_at  timestamptz not null,
  updated_at       timestamptz not null default now()
);
