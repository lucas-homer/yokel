-- 0012_conflict_live_detected_idx.sql — index the review-queue rot-age query (Slice R, PR-R4).
--
-- reviewQueueStats runs EVERY poll cycle and asks for min(detected_at) over LIVE cross_source
-- conflicts. conflict_records only accretes (rows are retired via resolved_at, never deleted), so
-- without an index that aggregate devolves to a growing table scan (#118 review). A PARTIAL index
-- matching the query's exact predicate keeps it a tiny index-ordered lookup forever: the live set
-- is small by design (retirement is the norm), so the index stays a few entries no matter how large
-- the retired history grows.
--
-- Idempotent: IF NOT EXISTS, same discipline as every index in 0001/0003.
create index if not exists conflict_records_live_detected_idx
  on conflict_records (detected_at)
  where resolved_at is null and conflict_scope = 'cross_source';
