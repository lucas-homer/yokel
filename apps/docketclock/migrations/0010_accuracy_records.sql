-- 0010_accuracy_records.sql — the post-close verification pass (verification slice V, PR-V1).
--
-- TWO tables with OPPOSITE mutation disciplines:
--
--   accuracy_records    — APPEND-ONLY (0001's trigger discipline, same docketclock_reject_mutation
--     function). The track record ("% of HIGH-confidence deadlines correct") is a TRUST PRIMITIVE —
--     the sales asset for design-partner conversations — so it must be as tamper-evident as the
--     observation log. One FINAL verdict per (ocd_id, window_version); never updated, never deleted.
--
--   verification_watch  — MUTABLE + OPERATIONAL (the regs_poll_watch pattern; NOT a contract shape).
--     The verdict must judge the window AS OF CLOSE TIME ("was the published close correct?"), but
--     participation_windows is a re-derived projection: a post-close correction mutates confidence/
--     close/version in place (with close history in change_history, but NO confidence history). So the
--     verify stage SNAPSHOTS a window's at-close state on the FIRST cycle after its close passes
--     (±1 poll interval, ~15 min — documented approximation) and the final AccuracyRecord is written
--     from the SNAPSHOT, immune to post-close projection drift. Without this, a post-close correction
--     that flips a HIGH window to CONFLICTING would silently remove that window from the HIGH gauge —
--     hiding exactly the miss the metric exists to count.
--
-- Idempotent: safe to re-run (IF NOT EXISTS / CREATE OR REPLACE via 0001's shared trigger function).
-- Requires 0001 (docketclock_reject_mutation) — migrations run in file order.

-- ── verification_watch — the at-close snapshot + horizon bookkeeping (operational, mutable) ─────────
create table if not exists verification_watch (
  ocd_id                  text not null,
  window_version          int  not null,          -- projection version live at snapshot (≈ at close)
  confidence_at_close     text not null,          -- Confidence enum value live at snapshot
  published_close_utc     timestamptz not null,   -- the close claim under judgment
  published_close_display text,                   -- verbatim legal language, may be absent
  snapshotted_at          timestamptz not null default now(),
  primary key (ocd_id, window_version)
);

-- Horizon-exit scans select watch rows by close age; the table stays small (rows become inert once the
-- matching accuracy_record exists) but the scan runs every poll cycle.
create index if not exists verification_watch_close_idx
  on verification_watch (published_close_utc);

-- ── accuracy_records — one immutable FINAL verdict per verified window version ──────────────────────
create table if not exists accuracy_records (
  accuracy_record_id      text primary key default gen_random_uuid()::text, -- internal id (NOT public)
  ocd_id                  text not null,
  window_version          int  not null,
  -- 'unknown' is unrepresentable by contract (0.9.0): an UNKNOWN window force-nulls its close, so it
  -- can never have PUBLISHED the close this record judges. The DB check mirrors the Zod refinement.
  confidence_at_close     text not null check (confidence_at_close in
                            ('high','medium','low','conflicting','stale')),
  published_close_utc     timestamptz not null,
  published_close_display text,

  -- the verdict — was the published close correct, judged AS OF CLOSE TIME?
  --   was_correct NULL ⇔ basis 'unverified_lapsed' (the horizon lapsed with ZERO confirmed post-close
  --   checks; writing true on the mere absence of evidence would inflate the headline number, writing
  --   false would smear it — NULL is the only honest value, and lapsed rows are EXCLUDED from the gauge).
  was_correct             boolean,
  basis                   text not null check (basis in
                            ('post_close_repoll','late_amendment','manual','unverified_lapsed')),
  check ((basis = 'unverified_lapsed') = (was_correct is null)),
  -- a MISS must name its evidence: the post-close observation ids that contradict the published close.
  -- 'manual' is exempt (an operator adjudication may rest on out-of-band evidence with no log row).
  contradicting_observation_ids jsonb not null default '[]'::jsonb,
  check (
    was_correct is distinct from false
    or basis = 'manual'
    or jsonb_array_length(contradicting_observation_ids) > 0
  ),
  -- …and ONLY a miss may carry contradictions (contract refinements 3+4, adversary RB-3): 'correct'
  -- means none exist, and a lapsed abstention never reached a verdict. The documented `manual`
  -- operator path is direct SQL, where the DB is the only validator — and the table is append-only,
  -- so an incoherent row accepted today is permanent.
  check (
    was_correct is not distinct from false
    or jsonb_array_length(contradicting_observation_ids) = 0
  ),

  -- horizon bookkeeping
  closed_at_utc           timestamptz not null,   -- the close instant the horizon anchored on
  verified_at_utc         timestamptz not null default now(),
  -- verification is post-close by definition (mirrors the AccuracyHorizon contract refinement)
  check (verified_at_utc >= closed_at_utc),

  -- one FINAL verdict per window version: a reopened window that closes again gets a NEW record at its
  -- new version; re-running the verify stage over the same version is an idempotent no-op, never a dupe.
  unique (ocd_id, window_version)
);

-- The 90d HIGH rollup (the headline gauge, recomputed each poll cycle) filters on confidence + close
-- recency and excludes lapsed rows; this composite covers it without a second scan-shaped index.
create index if not exists accuracy_records_rollup_idx
  on accuracy_records (confidence_at_close, closed_at_utc desc);
create index if not exists accuracy_records_ocd_idx
  on accuracy_records (ocd_id);

-- ── append-only enforcement — by EXCEPTION, not convention (0001's discipline, same function) ───────
drop trigger if exists accuracy_records_append_only on accuracy_records;
create trigger accuracy_records_append_only
  before update or delete on accuracy_records
  for each row execute function docketclock_reject_mutation();

drop trigger if exists accuracy_records_no_truncate on accuracy_records;
create trigger accuracy_records_no_truncate
  before truncate on accuracy_records
  for each statement execute function docketclock_reject_mutation();
