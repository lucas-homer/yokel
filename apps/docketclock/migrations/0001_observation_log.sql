-- 0001_observation_log.sql — the Spine's trust primitive (ADR 0008; docs/architecture/docketclock.md).
--
-- The append-only Observation log is PRIMARY: full replay can re-derive every window and conflict from
-- observations alone. Append-only is enforced at the DB level (a trigger raising an exception), NOT by
-- convention — the audit trail IS the legal-defensibility primitive. A single FR notice can extend
-- MANY dockets (EPA 2025-02910), so observations relate to windows MANY-TO-MANY via observation_targets.
--
-- Idempotent: safe to re-run (guarded by IF NOT EXISTS / CREATE OR REPLACE).

-- ── observations — one immutable row per fetched raw payload ───────────────────────────────────────
create table if not exists observations (
  observation_id    text primary key default gen_random_uuid()::text, -- internal log id (NOT public)
  ocd_id            text not null,        -- primary derived window (M:N fan-out lives in _targets)
  source            text not null check (source in ('federal_register', 'regulations_gov', 'govinfo')),

  -- source document identifiers as fetched (frDocNum is the primary join; the others are fallbacks)
  fr_document_number text,
  regs_document_id   text,
  regs_object_id     text,

  payload_hash      text not null check (payload_hash ~ '^[a-f0-9]{64}$'), -- sha256 of raw; dedupe key
  fetched_at        timestamptz not null default now(),
  parser_version    text not null,        -- pins which parser produced the flags below

  raw_dates_text    text,                 -- verbatim, legally-authoritative DATES text — never reformatted

  -- notice-type flags parsed at insert (regex + RuleBox deny-list; BLM 2023-27468 false-positive guard)
  is_extension      boolean not null,
  is_correction     boolean not null,
  is_withdrawal     boolean not null,

  raw               jsonb not null        -- the raw payload, retained intact for replay/transparency
);

-- Indexes per the architecture: the two source-document lookups (latest-first), used by the
-- payload-hash dedupe ("skip if hash matches the latest for that (source, document_id)").
create index if not exists observations_fr_doc_idx
  on observations (fr_document_number, source, fetched_at desc)
  where fr_document_number is not null;
create index if not exists observations_regs_obj_idx
  on observations (regs_object_id, source, fetched_at desc)
  where regs_object_id is not null;

-- NOTE(phase-1+): the architecture calls for monthly RANGE partitioning on fetched_at. Deferred —
-- premature at ~1,000 windows; revisit when the log volume justifies it. The trigger + indexes are
-- the load-bearing parts and are partition-compatible (attach to each partition when introduced).

-- ── observation_targets — the M:N join: one observation contributes to one-or-many windows ──────────
create table if not exists observation_targets (
  observation_id text not null references observations (observation_id),
  ocd_id         text not null,
  primary key (observation_id, ocd_id)
);
create index if not exists observation_targets_ocd_idx on observation_targets (ocd_id);

-- ── append-only enforcement — by EXCEPTION, not convention ──────────────────────────────────────────
-- One function reused for both the row-level (UPDATE/DELETE) and statement-level (TRUNCATE) guards.
-- TRUNCATE is covered explicitly: it bypasses row-level DELETE triggers and would otherwise be a hole.
create or replace function docketclock_reject_mutation() returns trigger
  language plpgsql as $$
begin
  raise exception 'append-only violation: % on % is forbidden (the observation log is immutable)',
    tg_op, tg_table_name
    using errcode = 'restrict_violation';
end;
$$;

drop trigger if exists observations_append_only on observations;
create trigger observations_append_only
  before update or delete on observations
  for each row execute function docketclock_reject_mutation();

drop trigger if exists observations_no_truncate on observations;
create trigger observations_no_truncate
  before truncate on observations
  for each statement execute function docketclock_reject_mutation();

drop trigger if exists observation_targets_append_only on observation_targets;
create trigger observation_targets_append_only
  before update or delete on observation_targets
  for each row execute function docketclock_reject_mutation();

drop trigger if exists observation_targets_no_truncate on observation_targets;
create trigger observation_targets_no_truncate
  before truncate on observation_targets
  for each statement execute function docketclock_reject_mutation();
