-- 0009_adjudications_per_adjudicator_key.sql — RE-KEY the adjudication cache to (content_hash, adjudicator_id).
--
-- WHY THIS REVERSES 0008's "adjudicator_id NOT part of the cache key" decision. 0008 made content_hash
-- ALONE the PRIMARY KEY, so "swapping providers never re-adjudicates a content_hash that already exists".
-- That was wrong in one load-bearing direction: a NON-DECIDING adapter (the null adapter, which only ever
-- returns `uncertain` with adjudicator_id "null:abstain@<rulebook_version>") could persist its abstention
-- under a content_hash and then SHADOW a real adjudicator's verdict for the SAME input forever — the cache
-- replayed the stale `uncertain` and the real provider (Gemini) was never consulted, so the chain link was
-- silently suppressed. (25 such rows had to be hand-deleted from prod.)
--
-- THE FIX: the cache key becomes (content_hash, adjudicator_id). A non-deciding adapter's verdict
-- ("null:abstain@<rb>") then lives under a DIFFERENT key than a real adjudicator's verdict
-- ("gemini:...@<rb>") for the same input, so it can NEVER shadow it. Each adjudicator's own verdict (incl.
-- `uncertain`) is cached and replayed under ITS id — no re-bill, no starvation, deterministic per
-- adjudicator. A provider/model OR rulebook change re-adjudicates (new adjudicator_id and/or content_hash),
-- which is correct: a different engine or rulebook is a genuinely different question.
--
-- DATA: existing rows all have UNIQUE content_hashes (the old PK guaranteed it), so the composite PK
-- (content_hash, adjudicator_id) is satisfied by the existing rows with NO data migration. The
-- adjudications_content_hash_hex_check constraint from 0008 is left UNTOUCHED.
--
-- Idempotent: re-running is a no-op. We only swap the PK when it is still the single-column one (0008's),
-- guarded by inspecting pg_constraint for the composite shape (matching 0008's do$$...end$$ guard style).

do $$
declare
  pk_cols int;
begin
  -- How many columns does the current adjudications PRIMARY KEY span? 1 = 0008's content_hash-only PK
  -- (needs the swap); 2 = this migration already applied (composite) ⇒ no-op.
  select cardinality(conkey) into pk_cols
  from pg_constraint
  where conrelid = 'adjudications'::regclass
    and contype = 'p';

  if pk_cols = 1 then
    alter table adjudications drop constraint adjudications_pkey;
    alter table adjudications
      add constraint adjudications_pkey primary key (content_hash, adjudicator_id);
  end if;
end$$;
