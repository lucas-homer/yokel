-- 0003_participation_windows.sql — the DERIVED projections over the append-only Observation log.
--
-- UNLIKE `observations` (the immutable spine, 0001), these two tables are RE-DERIVED, not appended:
-- every reconcile run recomputes a window from the current observation chain and UPSERTs the result.
-- They are caches/read-models over the log — the log alone can fully re-derive them at any time — so
-- they deliberately carry NO append-only trigger. Mutating a window IS the intended operation; the
-- audit trail that the append-only guard protects lives in `observations` (and, for the deadline value
-- itself, in this table's own `change_history` jsonb, appended in-row on each close-date change).
--
-- Re-derivation semantics:
--   participation_windows — PK ocd_id; `on conflict (ocd_id) do update` overwrites the projection. The
--     persist layer bumps `version` and appends a ChangeHistoryEntry to `change_history` whenever the
--     recomputed resolved_close_utc differs from the stored one (a silent close-date mutation is exactly
--     what the trust model forbids — superseded closes live in change_history forever).
--   conflict_records — surrogate PK; a row is INSERTed when reconcile detects a disagreeing FR/Regs
--     pair. Re-running reconcile on the SAME disagreeing pair must not duplicate rows, so we UPSERT on
--     the natural key (ocd_id, observation_a_id, observation_b_id) — the pair of source observations
--     that disagree uniquely identifies the conflict. detected_at is PRESERVED as the first-detection
--     timestamp across re-detections (the upsert refreshes metadata only — conflict_flags/govinfo_url/
--     resolved_at — never detected_at).
--
-- Operational (NON-contract) columns — present in this projection but deliberately NOT part of the
-- @yokel/contracts shapes, so adding them never touches the frozen contract:
--   participation_windows.derived_at          — last re-derivation timestamp.
--   participation_windows.reconciler_version  — which rulebook version (RECONCILER_VERSION) derived the
--     row; bumped on any rule change, mirrors PARSER_VERSION on the adapters. Lets us identify rows that
--     need re-derivation after a rulebook change without reading the contract object.
--   conflict_records.resolved_at              — proof-feed retirement marker (see the column comment).
--
-- Idempotent: safe to re-run (guarded by IF NOT EXISTS).
-- Array / json-ish contract fields are stored as jsonb (docket_id, conflict_flags, tags,
-- current_observation_ids, provenance, change_history) to mirror the @yokel/contracts shapes 1:1.

-- ── participation_windows — the canonical unit of trust, a versioned projection over the log ────────
create table if not exists participation_windows (
  ocd_id                 text primary key,

  -- identifiers (frDocNum is the primary join; docket_id/RIN are fallbacks)
  fr_document_number     text,
  regs_document_id       text,
  regs_object_id         text,
  docket_id              jsonb not null default '[]'::jsonb,
  rin                    text,

  window_type            text not null,

  -- operative deadline — nullable + honest when confidence is conflicting/unknown
  resolved_close_utc     timestamptz,
  resolved_close_display text,

  -- unreconciled per-source values, retained for transparency
  raw_fr_close_date      text,
  raw_regs_close_datetime text,

  confidence             text not null,
  conflict_flags         jsonb not null default '[]'::jsonb,
  status                 text not null,

  submission_url         text,
  govinfo_url            text,

  tags                   jsonb not null default '[]'::jsonb,

  -- provenance / versioning
  version                int not null default 0,
  current_observation_ids jsonb not null default '[]'::jsonb,
  provenance             jsonb not null default '{"agreeing_observation_ids":[],"conflicting_observation_ids":[]}'::jsonb,
  change_history         jsonb not null default '[]'::jsonb,

  derived_at             timestamptz not null default now(),  -- last re-derivation stamp (operational)
  -- operational, NOT a @yokel/contracts field: the rulebook version that derived this row (mirrors the
  -- adapters' PARSER_VERSION). Lets ops find rows needing re-derivation after a rule change.
  reconciler_version     text not null default 'reconcile-v1'
);

create index if not exists participation_windows_confidence_idx
  on participation_windows (confidence);
create index if not exists participation_windows_status_idx
  on participation_windows (status);

-- ── conflict_records — the published GET /conflicts proof feed (the credibility moat) ───────────────
create table if not exists conflict_records (
  conflict_id        text primary key default gen_random_uuid()::text,  -- surrogate PK
  ocd_id             text not null,
  observation_a_id   text not null,
  observation_b_id   text not null,
  source_a           text not null check (source_a in ('federal_register', 'regulations_gov', 'govinfo')),
  source_b           text not null check (source_b in ('federal_register', 'regulations_gov', 'govinfo')),
  conflict_flags     jsonb not null,                 -- contract: at least one flag
  govinfo_url        text,
  detected_at        timestamptz not null default now(),

  -- resolved_at: NULL while the conflict is LIVE; stamped when the conflict resolves (the current window
  -- is no longer CONFLICTING) or when this pair is SUPERSEDED by a newer conflicting pair for the same
  -- ocd_id. The GET /conflicts proof feed publishes only live conflicts (resolved_at IS NULL) — it must
  -- never surface dead/superseded conflicts. Not part of the @yokel/contracts ConflictRecord shape; it
  -- is a server-side retirement marker over the proof feed.
  resolved_at        timestamptz,

  -- The disagreeing source-observation PAIR uniquely identifies a conflict. Re-running reconcile on the
  -- same pair UPSERTs (refreshing metadata only — conflict_flags/govinfo_url/resolved_at) rather than
  -- duplicating the proof-feed row; detected_at is PRESERVED as the first-detection timestamp.
  unique (ocd_id, observation_a_id, observation_b_id)
);

create index if not exists conflict_records_ocd_idx on conflict_records (ocd_id);
