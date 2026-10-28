-- 0013_amendment_loader_idx.sql — indexes for the reconcile-v2.4 amendment loader (ADR 0016).
--
-- loadAmendmentEvidence runs on EVERY reconcileOcdId (ingest, rederive sweep, status refresh, review),
-- so on a production-sized log (30k observations, 8.3k windows) its reads must be index lookups, not
-- table scans. Measured on a prod copy before this migration: 0.4–5.4 s per call, and a full re-derive
-- that did not finish in 30 min (main: 79 s). Four indexes, each matching one query's exact predicate:
--
--   1. observations (ocd_id, source, fetched_at desc, observation_id desc) — "the latest <source> row
--      of this window". The window's own latest FR row (loader side A), the latest govinfo row per
--      amendment, and loadObservations' whole-chain read (which every derive path runs — main had no
--      ocd_id index on observations at all and seq-scanned the log per window).
--   2. observations (fetched_at) WHERE source in ('federal_register','govinfo') — the amendment-corpus
--      freshness stamp (count + max fetched_at over exactly those rows) as an index-only aggregate.
--   3. observations (ocd_id) WHERE source = 'federal_register' AND <any amendment signal> — the windows
--      that have EVER carried an amendment signal (the four flags, or a non-empty correction_of — the
--      fr-v3 rule read off raw). The corpus re-checks the signal on each window's LATEST row, so a
--      document whose latest row lost its flags is still excluded, exactly as before.
--   4. observations (normalized citation) WHERE source = 'federal_register' — the citation uniqueness
--      count; the expression is byte-identical to the loader's query so the planner can match it.
--
-- Idempotent: IF NOT EXISTS, same discipline as every index in 0001–0012. Plain CREATE INDEX (not
-- CONCURRENTLY): migrations run in one transaction each (migrate.ts), and the log is ~30k rows, so the
-- build is sub-second. All four are stock btree on PG18 (CNPG 18.3 image); regexp_replace/btrim and the
-- jsonb operators are IMMUTABLE, so the expression and partial predicates are index-legal. Partition-
-- compatible like the 0001 indexes (attach per partition if the deferred RANGE partitioning lands).
create index if not exists observations_ocd_source_idx
  on observations (ocd_id, source, fetched_at desc, observation_id desc);

create index if not exists observations_fr_govinfo_fetched_idx
  on observations (fetched_at)
  where source in ('federal_register', 'govinfo');

create index if not exists observations_fr_amendment_idx
  on observations (ocd_id)
  where source = 'federal_register'
    and (is_extension or is_correction or is_withdrawal or is_reopening
         or coalesce(raw->>'correction_of', '') <> '');

create index if not exists observations_fr_citation_idx
  on observations ((regexp_replace(btrim(raw->>'citation'), '\s+', ' ', 'g')))
  where source = 'federal_register';
