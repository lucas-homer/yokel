-- 0005_poll_dead_letter.sql — the bounded-retry / dead-letter ledger for BOTH poll loops (issue #21).
--
-- WHY THIS EXISTS (issue #21). The differential pollers correctly HOLD on a failing document so a
-- transient failure is retried next cycle and never silently skipped:
--   * pollRegsOnce advances its lastModifiedDate cursor only through the CONTIGUOUS-success prefix — the
--     first doc whose fetch/parse/ingest fails freezes the cursor, re-listing + retrying it next cycle.
--   * pollFrOnce is differential-by-the-log — a doc that fails stays ABSENT from the log, so the full
--     open set re-lists it and it is re-fetched next cycle.
-- That is exactly right for a TRANSIENT failure. But a PERMANENTLY-failing document (a malformed payload,
-- a perma-500 detail) wedges forever: Regs freezes its cursor every cycle (starving every CHANGE behind
-- it), and FR re-fetches the same doomed doc every cycle (burning the FR rate budget). This table is the
-- escape valve: count CONSECUTIVE failures per (source, document), and once they cross a threshold,
-- DEAD-LETTER the doc — Regs then lets its cursor ADVANCE past it (recorded + alerted, never silently
-- skipped) and FR stops re-fetching it on the hot path. A slow background sweep re-attempts dead-lettered
-- docs on a throttle so a doc that recovers (the upstream payload is fixed) is healed without manual
-- intervention.
--
-- A CHECKPOINT, NOT THE SPINE. Like poll_cursor / regs_poll_watch (0004) and UNLIKE `observations` (the
-- immutable append-only spine, 0001), this is MUTABLE OPERATIONAL STATE. It is fully re-derivable: drop
-- it and the worst that happens is the failure counters reset to zero and the bounded-retry clock starts
-- over (a wedged doc would be re-discovered + re-counted from scratch). It is droppable/resettable with
-- ZERO loss of the audit trail, and therefore carries NO append-only trigger — UPSERTing a failure count
-- forward, and DELETEing a row on recovery, ARE the intended operations.
--
-- SOURCE-AGNOSTIC. One table serves both pollers, keyed by (source, document_key):
--   * source       — 'regulations_gov' | 'federal_register'
--   * document_key — the natural per-source id: regs_document_id for Regs, fr_document_number for FR.
--
-- CONSECUTIVE-FAILURE SEMANTICS. `attempts` counts CONSECUTIVE failed attempts, NOT lifetime failures.
-- ANY success (a normal ingest OR a successful retry-sweep re-attempt) DELETEs the row, so a doc that
-- fails a few times and then recovers resets cleanly — its next failure starts counting from 1 again.
-- The failure counter is bumped on parse/ingest failures too, not only fetch failures (per the #21
-- owner-comment): a doc that fetches fine but whose payload can never be parsed/ingested must dead-letter
-- the same way as a doc that can never be fetched.
--
-- ROW-STATE READING:
--   * a row PRESENT with dead_lettered_at IS NULL  → still in BOUNDED RETRY (attempts < threshold); the
--     poller is still holding/re-listing it on the hot path every cycle.
--   * a row PRESENT with dead_lettered_at NOT NULL → DEAD-LETTERED; the poller has stopped blocking on it
--     (Regs cursor advances past it, FR skips re-fetching it) and only the slow retry sweep re-attempts
--     it, throttled by coalesce(last_retry_at, dead_lettered_at) < (now - retryStaleAfter).
-- dead_lettered_at is set ONCE (coalesce(existing, now)) when attempts first cross the threshold and is
-- never moved later, so the "how long has this been dead-lettered" signal is stable.
--
-- Idempotent: safe to re-run (guarded by IF NOT EXISTS).

create table if not exists poll_dead_letter (
  source           text not null,             -- 'regulations_gov' | 'federal_register'
  document_key     text not null,             -- regs_document_id (Regs) | fr_document_number (FR)
  attempts         int  not null default 0,   -- CONSECUTIVE failed attempts (row deleted on success)
  first_failed_at  timestamptz not null,
  last_failed_at   timestamptz not null,
  last_error       text,
  dead_lettered_at timestamptz,               -- set once attempts crossed the threshold; NULL while still in bounded retry
  last_retry_at    timestamptz,               -- when the slow drain sweep last re-attempted a dead-lettered doc
  updated_at       timestamptz not null default now(),
  primary key (source, document_key)
);
