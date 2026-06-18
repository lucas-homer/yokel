-- 0008_adjudications_cache.sql — the adjudication read-through CACHE (LLM ambiguous-tail escalation).
--
-- WHAT THIS IS (Slice 2 of the RuleBox/classifier feature). The adjudication subsystem escalates an
-- AMBIGUOUS deterministic match (a notice-type keyword that a deny rule can't settle, or a chain
-- amends/doesn't-amend call) to a provider-neutral Adjudicator, OUT-OF-BAND from the parse hot path. This
-- table is its cache + replay log. It is BEHAVIOR-PRESERVING for the live pipeline: nothing in
-- parse/reconcile writes or reads it yet (today's rulebook has no `ambiguous` rules); Slice 3 wires it.
--
-- Columns mirror the frozen @yokel/contracts AdjudicationRecord @ 0.7.0:
--   • content_hash  — sha256 of canonical(input) (app-computed; includes rulebook_version). PRIMARY KEY
--     = the cache key. Same input ⇒ same hash ⇒ replay the stored verdict instead of re-adjudicating.
--   • input         — the AdjudicationInput that was adjudicated (the hashed payload).
--   • verdict       — the AdjudicationVerdict (categorical classification + free-text rationale; NO score).
--   • adjudicator_id — PROVENANCE "provider:model@rulebook_version" (e.g. "null:abstain@rulebox-2026-06-18").
--     NOT part of the cache key — swapping providers never re-adjudicates a content_hash that already exists.
--   • created_at    — when this verdict was FIRST persisted.
--
-- WRITE-ONCE by convention (ON CONFLICT (content_hash) DO NOTHING in consult.ts): a content_hash is
-- inserted once and its row is IMMUTABLE — the first verdict wins, forever, for replay determinism. We do
-- NOT attach the heavy observations append-only BEFORE UPDATE/DELETE trigger: this is a DERIVED cache, not
-- the source-of-truth log, and the ON CONFLICT DO NOTHING write path already enforces first-writer-wins.
--
-- Idempotent: create table / index are IF NOT EXISTS, matching the guard style of 0003/0005/0006.

create table if not exists adjudications (
  content_hash   text primary key,                       -- sha256(canonical(input)); the cache key
  input          jsonb not null,                          -- the AdjudicationInput (hashed payload)
  verdict        jsonb not null,                          -- the AdjudicationVerdict (classification + rationale)
  adjudicator_id text not null,                           -- PROVENANCE "provider:model@rulebook_version"
  created_at     timestamptz not null default now()       -- first-persisted instant
);

-- The content_hash is 64-hex; enforce the shape at the DB level too (mirrors the PayloadHash contract).
do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conrelid = 'adjudications'::regclass
      and conname = 'adjudications_content_hash_hex_check'
  ) then
    alter table adjudications
      add constraint adjudications_content_hash_hex_check
      check (content_hash ~ '^[a-f0-9]{64}$');
  end if;
end$$;
