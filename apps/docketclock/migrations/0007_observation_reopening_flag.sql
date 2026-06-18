-- 0007_observation_reopening_flag.sql — add the 4th notice-type flag, is_reopening, to the log (#O4).
--
-- WHAT THIS IS. Issue #31's deferred follow-up O4: a "Reopening of the Comment Period" notice is a
-- distinct legal event from an extension — it re-opens an ALREADY-CLOSED period (a gap; a fresh reliance
-- window), whereas an extension moves a still-open deadline later. Until now `reopen` was folded into the
-- is_extension keyword pass, so a reopening was mis-flagged as an extension (and the chain engine emitted
-- `extension_chain_unresolved` for it). @yokel/contracts 0.5.0 adds is_reopening to the Observation schema
-- and a `reopening` ConflictFlag; this migration adds the matching column so the parser can persist it as a
-- first-class peer of is_extension/is_correction/is_withdrawal.
--
-- APPEND-ONLY SAFETY. `observations` carries a BEFORE UPDATE/DELETE trigger (0001) that rejects all row
-- mutation. `ALTER TABLE ... ADD COLUMN` is DDL, NOT a row UPDATE, so the row trigger does not fire; with a
-- DEFAULT, Postgres performs a metadata-only add (no row rewrite). Existing rows therefore read
-- is_reopening = false until they are re-derived. RE-DERIVING EXISTING ROWS is a SEPARATE, dev-only one-shot
-- (src/db/backfill-reopening-flag.ts) that recomputes all notice flags from each row's retained `raw` — it
-- is NOT part of this migration, so the production migrate Job never disables the append-only guard.
--
-- IDEMPOTENT: `add column if not exists`, re-runnable. The DEFAULT is retained (harmless): the parser always
-- supplies is_reopening explicitly on insert, and the default only makes the metadata-only add satisfy NOT
-- NULL for pre-existing rows. (The sibling flags carry no default; this one keeps it as the add-time seed.)

alter table observations
  add column if not exists is_reopening boolean not null default false;
