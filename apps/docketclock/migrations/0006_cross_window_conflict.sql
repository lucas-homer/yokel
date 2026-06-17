-- 0006_cross_window_conflict.sql — widen conflict_records to carry CROSS-WINDOW (chain) conflicts (#31).
--
-- WHAT THIS IS (Slice 1, plumbing only). The published GET /conflicts proof feed (conflict_records,
-- 0003) today holds only CROSS-SOURCE conflicts: one window (`ocd_id`) whose FR and Regs observations
-- disagree. Issue #31 adds a second kind — a CROSS-WINDOW (chain) conflict that spans TWO distinct
-- windows (e.g. an amendment notice that mints its own standalone `ocd_id` yet contradicts the parent's
-- deadline). The frozen @yokel/contracts ConflictRecord @ 0.4.0 already models both kinds in ONE shape
-- via three additive, defaulted fields (conflict_scope, ocd_id_b, govinfo_url_b). This migration brings
-- the projection table up to that shape and widens the dedup key. NO cross_window rows are emitted yet —
-- the engine/persist still writes only cross_source; a later slice flips on the chain detector. This is a
-- behavior-preserving seam.
--
-- THE NULL-vs-'' DESIGN DECISION (load-bearing — read carefully). The contract models `ocd_id_b` as
-- NULLABLE (it is null on the wire for a cross_source conflict — there is no side-B window). But a
-- Postgres UNIQUE constraint treats NULL as DISTINCT from every other NULL, so a unique key that included
-- a nullable ocd_id_b would let DUPLICATE cross_source rows (both with ocd_id_b = NULL) slip past dedup —
-- the very dedup the natural key exists to enforce. Therefore at the DB level ocd_id_b is NOT NULL
-- DEFAULT '' (the empty string is the sentinel for "no side B"). The persist/query seam maps the two
-- representations:
--   • write (persist.ts):  contract null  →  DB ''
--   • read  (queries.ts):  DB ''          →  contract null
-- So every cross_source row shares ocd_id_b = '' and the widened unique key collapses them (correct
-- dedup), while the wire/contract stays cleanly nullable. A cross_window row carries a real distinct
-- ocd_id_b, so its side-B identity participates in the key and two different chain pairs never collide.
--
-- THE WIDENED DEDUP KEY. The natural key becomes (ocd_id, observation_a_id, observation_b_id, ocd_id_b).
-- For cross_source rows ocd_id_b = '' is constant, so the key degrades to the original 3-column key (no
-- behavior change — re-detecting the same FR↔Regs pair still UPSERTs, detected_at preserved). For
-- cross_window rows the 4th column distinguishes side B, so the SAME observation pair conflicting across
-- two different B-windows would be two distinct rows (the correct chain semantics).
--
-- EITHER-SIDE LOOKUP. A window must be able to find conflicts where it is side B as well as side A (the
-- amendment wants to see the chain conflict it is the second party to). conflict_records_ocd_id_b_idx
-- backs the `ocd_id_b = ?` half of the either-side filter in listConflicts.
--
-- Idempotent: every statement is guarded (IF NOT EXISTS / IF NOT EXISTS-equivalent via pg_constraint /
-- DROP ... IF EXISTS), matching the guard style of 0003/0005. Safe to re-run.

-- ── new columns (defaulted so existing rows back-fill to the cross_source meaning) ──────────────────
alter table conflict_records
  add column if not exists conflict_scope text not null default 'cross_source';

-- guard the scope CHECK so a re-run does not error on the already-present constraint.
do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conrelid = 'conflict_records'::regclass
      and conname = 'conflict_records_conflict_scope_check'
  ) then
    alter table conflict_records
      add constraint conflict_records_conflict_scope_check
      check (conflict_scope in ('cross_source', 'cross_window'));
  end if;
end$$;

-- ocd_id_b is NOT NULL DEFAULT '' at the DB level (the '' sentinel = "no side B"; see the header).
alter table conflict_records
  add column if not exists ocd_id_b text not null default '';

alter table conflict_records
  add column if not exists govinfo_url_b text;  -- nullable: side B's legal-reliance anchor (cross_window only)

-- ── widen the dedup key from the 3-column pair to include side B ─────────────────────────────────────
-- Drop the original auto-named 3-column unique constraint (verified name against a live PG18:
-- conflict_records_ocd_id_observation_a_id_observation_b_id_key) and replace it with the 4-column key.
alter table conflict_records
  drop constraint if exists conflict_records_ocd_id_observation_a_id_observation_b_id_key;

do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conrelid = 'conflict_records'::regclass
      and conname = 'conflict_records_pair_key'
  ) then
    alter table conflict_records
      add constraint conflict_records_pair_key
      unique (ocd_id, observation_a_id, observation_b_id, ocd_id_b);
  end if;
end$$;

-- back the either-side (ocd_id_b = ?) half of the listConflicts filter.
create index if not exists conflict_records_ocd_id_b_idx on conflict_records (ocd_id_b);
