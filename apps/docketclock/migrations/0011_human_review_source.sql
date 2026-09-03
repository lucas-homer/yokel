-- 0011_human_review_source.sql — widen 0001's source CHECK for the human-review write path
-- (Slice R, PR-R1; plans/review-resolve.md). LOCKSTEP with @yokel/contracts 0.10.0, which adds
-- "human_review" as the fourth ObservationSource — the contract and this CHECK must always name
-- the same closed set, so an unknown source is still rejected at BOTH layers (the adversarial
-- probe in the plan: widening is not opening).
--
-- WHY A SOURCE AND NOT A NEW TABLE: a human resolution is an OBSERVATION, never a mutation — it
-- rides the same append-only log, ingest idempotency, and audit discipline as source data (the
-- 0001 append-only trigger applies unchanged; there is no admin UPDATE path and never will be).
-- The typed verdict payload lives in `raw` (HumanReviewVerdict, contract 0.10.0); the reconciler
-- only starts HONORING these rows at reconcile-v2 (PR-R2) — until then they are inert, auditable
-- data in the log (the documented PR-R2 rollback stance).
--
-- The 0001 CHECK is the UNNAMED inline column constraint, so Postgres auto-named it
-- observations_source_check. Idempotent: drop-if-exists + re-add under the same name — a re-run
-- drops the widened constraint and re-adds it identically.
alter table observations drop constraint if exists observations_source_check;
alter table observations add constraint observations_source_check
  check (source in ('federal_register', 'regulations_gov', 'govinfo', 'human_review'));
