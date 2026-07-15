# Verification Slice V — the accuracy loop (post-close verification + AccuracyRecord + independent cross-check + a real alert path)

> Status: **Shipped except item 5** — PR-V1 (#89), PR-V2 (#92), PR-V3 (#86) merged; both fire
> drills PASSED (stall 2026-07-11, ingest 2026-07-15 — closed #91). Item 5 (the accuracy-degraded
> alert) is issue #90: waiting on a HIGH-sample baseline (~early Aug 2026); the sample-size gauge
> and NaN-at-registration prep merged as #97.
> Followed the observability epic (slices A–D, shipped #49–#65)
> AND the backups + restore-drill phase (`plans/backups-restore-drill.md`, #73). Backups-first is
> deliberate: PR-V1 adds a new irreplaceable append-only table (`accuracy_records`), and landing
> backups first means WAL archiving covers it from its first row.
> This is the "Week 9-10 — Follow-up + proof" stage of the architecture build sequence, pulled
> forward: the product's net-new value is reconciliation + confidence + provenance, so **measuring
> whether the published deadlines were actually right IS product work, not QA**. Its output —
> "% of HIGH-confidence deadlines correct, trailing 90d" — is the sales asset for the D5 buyer
> conversations. Everything here runs on local k3d and fits the colima RAM budget: no new
> platform services (the worker rides in the poller; the cross-check is offline DuckDB on the
> host; the alert receiver is hosted push, 0 GiB).

## Why this slice, why now

Observability tells us the system is **running** (logs, metrics, traces, evals of the LLM
adjudicator). Nothing yet tells us the system is **right**: no process checks a published
`resolved_close_utc` against what the sources say after the fact, both live sources are the same
two gov APIs we ingest from (the system grades its own homework), and the three Grafana alerts
route to a placeholder `local-noop` contact point — an alert that fires today reaches no human.
The architecture already designed the fix (pipeline stage "6. Verify + follow-up": re-poll 7 days
past close, write an AccuracyRecord, every `was_correct=false` becomes a regression test); this
slice builds it.

## What exists today (the seams this slice hooks into)

- **The poll cycle** — `apps/docketclock/src/poll/run.ts`: a single-writer, self-rescheduling cycle running
  `pollFrOnce` → `pollRegsOnce` → `chainReconcileOnce` sequentially, with graceful drain and a
  heartbeat file. A verification pass slots in as **stage 4** of the same cycle — no new
  Deployment, single-writer preserved.
- **The Regs re-poll budget** — #69 added a budgeted re-poll pass + `repoll_deferred` metric; the
  post-close verification re-polls must ride the same budget discipline (closed-window checks are
  deferrable, never allowed to starve discovery).
- **Windows + observations** — `participation_windows` carries `resolved_close_utc`, `confidence`,
  `status` (the `WindowStatus` enum already includes `finalized`), `change_history`, and points
  into the append-only observation log. Late amendments already land as observations; what's
  missing is the **verdict** ("was the published close correct?") and the table to hold it.
- **Contracts @ 0.8.0** — `AccuracyRecord` is the one shape the contracts README lists as TODO.
  Adding it is a contract-keeper change (additive, minor bump).
- **Metrics + dashboards + alerts** (slice B) — `docketclock_*` prom-client conventions,
  annotation scraping, the _DocketClock — App_ dashboard, and 3 provisioned alerts wired to the
  placeholder `local-noop` webhook. Grafana admin creds already flow Vault → ESO (the pattern
  PR-V3 reuses for the receiver secret).
- **The offline bulk-data hook** — `spikes/README.md` documents `SPICY_REGS_PARQUET` as the
  (never-wired) glob for the Mirrulations/spicy-regs Parquet; the DuckDB harness in `spikes/` is
  built for exactly this kind of join. Architecture rule: Mirrulations is **offline eval/seed
  only, never a live freshness source** — so the cross-check is a batch differential, not a third
  adapter.
- **The eval regression pattern** (slice D) — committed gold files + `pnpm eval:chain` + a CI
  gate. PR-V2's "every miss becomes a regression test" reuses this shape (committed fixtures,
  loud validation, CI-runnable without live keys).

## Decisions locked

- **The verifier is a poller stage, not a service.** Stage 4 (`verifyOnce`) of the existing
  cycle, after `chainReconcileOnce`, sharing the pool, the drain, and the heartbeat. Rationale:
  single-writer invariant, zero RAM cost, and the re-poll machinery/budget already live there.
- **Verification horizon = 7 days past `resolved_close_utc`** (per the architecture). While a
  closed window is inside the horizon, its source docs stay in the re-poll set (budgeted,
  deferrable). Interim re-polls write ordinary observations through the existing ingest path —
  no new write path; the final `AccuracyRecord` verdict is written per the next bullet.
- **A verdict requires a confirmed check — never correctness-by-default.** Because the re-poll
  is deferrable, a window could exit the horizon with ZERO post-close checks actually executed;
  writing `was_correct=true` on the mere absence of a contradicting observation would quietly
  inflate the headline number. So: the final verdict is written only once ≥1 successful
  post-close re-poll of the window's sources has landed. If budget pressure defers every
  re-poll, the horizon extends until one lands — hard-capped at 14 days; a window that lapses
  the cap gets `basis: unverified_lapsed`, is EXCLUDED from the headline gauge, and increments
  `docketclock_accuracy_unverified_total`, so re-poll starvation is visible instead of being
  silently blended into "correct".
- **`was_correct` semantics: judge the claim as of close time.** Correct ⇔ no post-close
  observation contradicts the published close (no late correction moving the date, no revealed
  withdrawal, no reopening that shows the close was wrong when published). An extension we linked
  BEFORE close doesn't make the superseded window wrong — the chain already re-derived it; the
  verdict attaches to the window version that was live at close. Basis enum:
  `post_close_repoll | late_amendment | manual | unverified_lapsed`.
- **`accuracy_records` is append-only** (same trigger discipline as the observation log — the
  track record is a trust primitive; it must be as tamper-evident as the observations).
- **The headline metric is HIGH-only, trailing 90d**: share of HIGH-confidence windows whose
  final AccuracyRecord says `was_correct=true`, computed by SQL over `accuracy_records` each
  cycle and exported as a gauge. Sliced by confidence as secondary detail. (Buyers carry deadline
  liability on HIGH — that's the number that has to be defensible.)
- **Every `was_correct=false` becomes a committed regression fixture** — exported with full
  provenance (window snapshot at close + the contradicting observations) into
  `apps/docketclock/eval/accuracy-misses/`, validated like the gold file, replayed in `pnpm test`
  (pure reconcile-level replay; no live calls). A miss is a permanent test, not a dashboard blip.
- **The cross-check is offline and adversarial**: DuckDB over the Mirrulations parquet vs an
  export of our live windows, joined on frDocNum/documentId. Disagreements are triaged into
  {our bug | bulk-data staleness | source drift} — only the first kind becomes a fixture. It
  never writes to the live DB.
- **Alert receiver: hosted push (ntfy), secret via Vault → ESO.** Zero cluster RAM, works on a
  phone, no vendor account dance; the Grafana contact-point secret follows the existing
  admin-creds ESO pattern. (If a Slack workspace is preferred at build time, the wiring is
  identical — only the contact-point type changes; decide in PR-V3, default ntfy.)
- **No public surface.** `GET /accuracy` and any partner-facing dashboard stay deferred — the
  architecture gates them on design partners (D5). This slice produces the number and the
  internal panel; publishing it is Phase 3+ work.
- **Execution order: V3 → V1 → V2.** Both this plan and the backups plan name a real alert
  receiver as the prerequisite for trusting unattended alerts, and the backups phase ships its
  backup-staleness rules (PR-5 there) against `local-noop`. V3 has no dependency on V1/V2, so it
  lands FIRST — one small PR that retroactively wires every existing alert (poller stalled,
  db*up, backup age) to a human. The one item that DOES depend on V1 — the \_Accuracy degraded*
  alert — moves into V1's scope (its threshold can only be committed after the gauge has a
  baseline, which V3-first makes unambiguous).

## PR-V1 — AccuracyRecord: contract + table + the post-close verification pass

1. **Contracts (contract-keeper, minor bump)** — `AccuracyRecord`, additive; nothing else changes:

   ```
   { ocd_id, window_version, confidence_at_close,
     published_close_utc, published_close_display,
     verdict: { was_correct, basis, contradicting_observation_ids },
     horizon: { closed_at_utc, verified_at_utc } }
   ```

2. **Migration `0010_accuracy_records.sql`** — the table + the append-only enforcement trigger
   (mirror `0001`'s discipline) + indexes for the 90d rollup query.
3. **`apps/docketclock/src/verify/`** — `select.ts` (pure: which windows are inside/exiting the
   horizon, incl. the extend-until-confirmed-check and 14-day-lapse rules), `verdict.ts` (pure:
   observations-since-close + did-a-confirmed-check-land → verdict; unit-tested against fixture
   chains incl. the late-correction, revealed-withdrawal, linked-extension, deferred-re-poll
   [no verdict before a confirmed check], and lapse [`unverified_lapsed`] cases), `run.ts`
   (`verifyOnce(sql, opts)`: keep closed-in-horizon docs in the budgeted re-poll set, write
   final records per the verdict rules).
4. **Wire stage 4** into the poll cycle + metrics: `docketclock_accuracy_checks_total{result}`,
   `docketclock_accuracy_records_total{was_correct}`,
   `docketclock_accuracy_high_correct_ratio_90d` (gauge, SQL rollup per cycle),
   `docketclock_accuracy_unverified_total` (the starvation signal), and a
   _DocketClock — App_ dashboard row (ratio stat + misses table via Loki).
5. **_Accuracy degraded_ alert (moved here from V3 — it needs this PR's gauge)**: once the gauge
   has a few weeks of baseline, commit the rule — `docketclock_accuracy_high_correct_ratio_90d`
   below a committed threshold (the architecture's credibility bar is 95% on HIGH) with a
   min-sample guard so an empty/young window set can't page. Lands as a fast-follow commit/PR
   inside V1's scope; V3's receiver (already live, per execution order) delivers it.
6. **Verify:** unit tests green; on live k3d, windows that closed ≥7d ago accrue AccuracyRecords
   over a few cycles; the gauge appears in Prometheus/Grafana; a hand-crafted late-correction
   fixture produces `was_correct=false` with the right contradicting observation ids; re-poll
   budget metrics show closed-window checks deferring under pressure, never starving discovery.

## PR-V2 — Independent cross-check + the miss-to-regression-fixture loop

1. **Wire `SPICY_REGS_PARQUET`** — `spikes/src/xcheck.ts` (`pnpm xcheck` in the spikes package):
   DuckDB joins the parquet snapshot against a read-only export of live windows
   (`scripts/export-windows.ts` → JSONL via the existing port-forward), compares Eastern-date
   closes + status, writes `spikes/out/XCHECK_diff.md` (counts + per-disagreement detail).
2. **Triage doc** — `spikes/out/XCHECK_diff.md` gets a hand-filled `triage` column per
   disagreement: `our_bug | bulk_stale | source_drift`; the README documents the pass and the
   expectation (bulk staleness dominates; anything in `our_bug` is a find). **Cadence:** re-run
   on every fresh parquet snapshot, at least monthly while calibrating; a pass is not done until
   every disagreement carries a triage value (the diff file with an unfilled column is the
   reminder — it's checked in `spikes/out/` alongside the spike outputs).
3. **Fixture exporter** — `apps/docketclock/scripts/export-accuracy-miss.ts`: given an ocd_id
   (from a V1 miss or a V2 `our_bug` triage), snapshot window-at-close + observations into
   `eval/accuracy-misses/<frDocNum>.json`; `test/accuracy-misses.test.ts` replays every committed
   fixture through the pure reconcile/verdict path — no live calls, runs in `pnpm test`/CI.
4. **Verify:** xcheck runs end-to-end on a real parquet snapshot; at least the known-tricky
   historical chains (the BLM land-withdrawal false-positive class, EPA multi-docket) appear
   correctly as agreements; one seeded disagreement exports to a fixture and the replay test
   fails before / passes after a deliberate fix.

## PR-V3 — A real alert path + the dead-man's switch + the fire drill (lands FIRST — see execution order)

1. **Receiver** — ntfy topic (or Slack webhook if preferred at build time); the URL/token lands
   in Vault (`secret/observability/alerting`), flows ESO → the Grafana contact-point secret;
   replace `local-noop` in the provisioned alerting config. Everything stays git-defined. All
   EXISTING alerts (poller stalled, db_up, and the backups phase's backup-age/WAL/CronJob rules)
   start reaching a human with this one change.
2. **External dead-man's switch** — everything above still lives INSIDE the cluster: if colima /
   k3d / the Mini dies entirely, Grafana can't page anyone. A healthchecks.io check (free tier)
   pinged by an in-cluster CronJob (hourly `curl`; URL via the same Vault → ESO secret) pages on
   ABSENCE — pings stop → phone buzzes. Closes the "silent total outage" hole from the progress
   review, which no in-cluster component can cover by definition.
3. **Fire drill** — `task alert-drill` in `infra/Taskfile.yml`: scale the poller to 0, wait for
   _Poller stalled_ to fire and REACH THE PHONE, scale back, confirm resolve notification; also
   pause the dead-man CronJob once and confirm the absence page. Document the drill + a quarterly
   cadence note in `infra/README.md`. An alert path is untested until it has paged someone.
4. **Verify:** drill executed once for real (screenshot-level confidence: notification received);
   `db_up` and the backup alerts route to the same receiver; the dead-man check pages on the
   paused CronJob; secret never appears in git or `kubectl get cm` output.

## Out of scope (later)

- **`GET /accuracy` + partner-facing dashboard** — design-partner-gated (D5); the number exists
  after V1, publishing it is Phase 3+.
- **`window.finalized` via final-rule linkage** — the architecture's "emit finalized when a
  linked final rule appears" needs final-rule discovery; separate design, `WindowStatus` already
  reserves the value.
- **Webhooks / notification products** — the alert path here is ops-facing (Grafana → operator),
  not the customer delivery surface.
- **Chaos/failure-injection drills beyond the alert drill** — worth doing (CNPG failover, Vault
  restart, 429 storms) but a separate reliability track; this slice stays accuracy-shaped.
- **LLM-as-judge / notice-kind evals** — still deferred from slice D; the accuracy-miss fixtures
  will feed that corpus when it happens.
- **The human review/resolve path** (`human_review` observations closing out `PENDING_REVIEW` /
  `CONFLICTING` windows — gap #4 in the progress review). Deliberately NOT folded in: this slice
  measures correctness; resolving flagged windows is operator-workflow with its own design (even
  the minimal `docketclock resolve <ocd-id>` CLI). Named here explicitly so it stays on the
  roadmap rather than vanishing — candidate for its own small slice right after V1, whose miss
  verdicts are exactly what a reviewer wants in front of them.

## Rollback

- **PR-V1:** revert; stage 4 is additive in the cycle, the migration adds one table nothing else
  reads, the contract bump is additive. Accrued `accuracy_records` are inert history.
- **PR-V2:** revert; xcheck is host-side/offline and read-only, fixtures are test-only data.
- **PR-V3:** restore the `local-noop` contact point (one values change); delete the dead-man
  CronJob and pause the healthchecks.io check (else it pages on the absence it was built to
  catch); the Vault secret can stay (unreferenced) or be deleted.
