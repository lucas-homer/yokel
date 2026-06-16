-- 0002_regs_doc_index.sql — the FR<->Regs reconciliation join/dedupe index for the Regs.gov adapter.
--
-- 0001 noted this explicitly: observations_regs_obj_idx covers the (rarer) objectId-keyed path, but the
-- Regs.gov adapter dedupes/joins on the Regs DOCUMENT id (regs_document_id) — its differential poll
-- skips an insert when a candidate's payload_hash matches the LATEST row for (source, regs_document_id).
-- This is the latest-first index that lookup needs, mirroring observations_fr_doc_idx for FR.
--
-- Idempotent: safe to re-run (guarded by IF NOT EXISTS).

create index if not exists observations_regs_doc_idx
  on observations (regs_document_id, source, fetched_at desc)
  where regs_document_id is not null;
