-- 0014_poll_cycles.sql — one row per poll cycle, kept for long-term trends.
--
-- Traces in Grafana Cloud expire after 14 days (free tier). This table keeps the part worth trending over
-- months: when each cycle ran, how long it took, how it ended, and per pass its duration, success and the
-- numeric fields of its summary (documents fetched, windows re-derived, ...). `trace_id` links a recent row
-- to its trace while Grafana still has it.
--
-- `outcome`:
--   ok           every pass succeeded
--   pass_failed  the cycle ran, but at least one isolated pass failed
--   skipped      another process held the poll-cycle lock, so nothing ran
--   failed       the cycle could not run at all (e.g. taking the lock failed)
--
-- `passes` is a JSON array in run order: [{ "name", "ok", "ms", "summary": {..}, "error"? }].
-- Append-only and written after the cycle releases its lock, so it never touches the single-writer path.
create table if not exists poll_cycles (
  cycle_id    bigserial primary key,
  started_at  timestamptz not null,
  finished_at timestamptz not null,
  duration_ms integer not null,
  outcome     text not null check (outcome in ('ok', 'pass_failed', 'skipped', 'failed')),
  run_once    boolean not null,
  trace_id    text,
  passes      jsonb not null default '[]'::jsonb
);

create index if not exists poll_cycles_started_idx on poll_cycles (started_at desc);
