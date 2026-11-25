-- 0015_sam_gov.sql — SAM.gov sources: the Federal Hierarchy (agency tree) and Contract Opportunities
-- (solicitations with a response deadline). docs/plans/sam-gov.md has the design.
--
-- Same trust primitive as the comment-window side (0001): an APPEND-ONLY raw log is primary and the
-- tables people query are projections re-derivable from it. It is a separate log, not more rows in
-- `observations`, because that table's columns are comment-window specific (ocd_id NOT NULL, FR/Regs
-- document keys, is_extension/is_correction flags).
--
-- Valid time vs seen time: `fetched_at` is when we saw a payload; `source_modified_at` is when the source
-- says that version took effect (a notice's postedDate, an org's lastupdateddate). The API serves only
-- the LATEST version of a notice, so each amendment we see appends its own row, dated by both.

-- ── sam_observations — one immutable row per distinct fetched payload ─────────────────────────────
create table if not exists sam_observations (
  observation_id     text primary key default gen_random_uuid()::text,
  source             text not null check (source in ('sam_opportunities', 'sam_federal_hierarchy')),
  -- the source's own id: a noticeId (opportunities) or an fhorgid (hierarchy)
  entity_id          text not null,
  -- the stable public subject id, e.g. ocd-contract-opportunity/federal/<noticeId>, ocd-federal-org/<fhorgid>
  subject_id         text not null,
  payload_hash       text not null check (payload_hash ~ '^[a-f0-9]{64}$'),
  fetched_at         timestamptz not null default now(),
  source_modified_at timestamptz,          -- valid-from as the source states it; null if absent/unparseable
  parser_version     text not null,
  raw                jsonb not null
);

-- Dedupe lookup ("skip if the hash matches the latest for this entity"), latest-first.
create index if not exists sam_observations_entity_idx
  on sam_observations (source, entity_id, fetched_at desc);

drop trigger if exists sam_observations_append_only on sam_observations;
create trigger sam_observations_append_only
  before update or delete on sam_observations
  for each row execute function docketclock_reject_mutation();

drop trigger if exists sam_observations_no_truncate on sam_observations;
create trigger sam_observations_no_truncate
  before truncate on sam_observations
  for each statement execute function docketclock_reject_mutation();

-- ── federal_orgs — projection: the department / sub-tier tree (public FH API stops at sub-tier) ────
create table if not exists federal_orgs (
  fhorgid            text primary key,
  subject_id         text not null,
  name               text not null,
  org_type           text not null,        -- 'Department/Ind. Agency' | 'Sub-Tier' (as the source spells it)
  status             text,                 -- 'ACTIVE' | 'INACTIVE'
  parent_fhorgid     text,                 -- the department for a sub-tier; null for a department
  agency_code        text,                 -- the code opportunities use in fullParentPathCode
  cgac               text[] not null default '{}',
  source_created_at  timestamptz,
  source_updated_at  timestamptz,
  observation_id     text not null references sam_observations (observation_id),
  first_seen_at      timestamptz not null,
  last_seen_at       timestamptz not null
);
create index if not exists federal_orgs_parent_idx on federal_orgs (parent_fhorgid);
create index if not exists federal_orgs_agency_code_idx on federal_orgs (agency_code);

-- ── contract_deadlines — projection: the current state of each notice ──────────────────────────────
create table if not exists contract_deadlines (
  notice_id               text primary key,
  subject_id              text not null,
  title                   text,
  solicitation_number     text,
  notice_type             text,            -- current type, e.g. 'Solicitation'
  base_type               text,            -- original type
  active                  boolean,
  posted_at               timestamptz,     -- the current version's posted date (valid-from)
  -- The deadline as an instant AND verbatim. The raw string keeps the offset the notice states
  -- (solicitations use local times), and is the provenance quote. response_deadline is null when the
  -- raw value is absent or carries no offset (we never guess a zone).
  response_deadline       timestamptz,
  response_deadline_raw   text,
  archive_date            date,
  full_parent_path_code   text,
  full_parent_path_name   text,
  agency_fhorgid          text,            -- resolved via federal_orgs; null while unresolved
  naics_code              text,
  set_aside_code          text,
  source_url              text,            -- public notice page
  observation_id          text not null references sam_observations (observation_id),
  deadline_changed_at     timestamptz,     -- seen-time of the last change to response_deadline_raw
  first_seen_at           timestamptz not null,
  last_seen_at            timestamptz not null
);
create index if not exists contract_deadlines_deadline_idx
  on contract_deadlines (response_deadline) where response_deadline is not null;
create index if not exists contract_deadlines_agency_idx on contract_deadlines (agency_fhorgid);

-- ── sam_request_budget — the per-UTC-day request counter (a personal key gets ~10 requests/day) ────
create table if not exists sam_request_budget (
  day           date primary key,
  requests      integer not null default 0,
  exhausted_at  timestamptz              -- set on a 429: no more SAM calls until the next UTC day
);

-- ── sam_sync_state — where each SAM sync is (backfill paging survives a budget cut across days) ────
create table if not exists sam_sync_state (
  source            text primary key check (source in ('sam_opportunities', 'sam_federal_hierarchy')),
  phase             text not null check (phase in ('backfill', 'delta')),
  page_offset       integer not null default 0,
  window_from       date,                 -- the current query window (inclusive)
  window_to         date,
  last_completed_at timestamptz,          -- when the last full window finished
  updated_at        timestamptz not null default now()
);
