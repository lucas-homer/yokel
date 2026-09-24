# Resurfaced verdict fix: seven-case verification

Verified `reconcile-v2.1` against a read-only cluster snapshot taken at
**2026-09-23 23:46:14 UTC**. The snapshot contains 87 observations across seven windows, including
one original human verdict per window. No cluster data was changed.

## Result

All seven currently conflicting windows return to their original approved dates with `high`
confidence, `open` status, and `human_resolved`. No new verdict is needed.

| Document | Subject | Original approved close | Observations | Refresh that resurfaced review |
| --- | --- | --- | ---: | --- |
| 2026-16246 | DAYVIGO | 2026-10-09 | 6 | Added Regs `links.self` |
| 2026-16247 | BRINSUPRI | 2026-10-09 | 6 | Added Regs `links.self` |
| 2026-16664 | National Organic Standards Board | 2026-10-01 | 21 | Regs `modifyDate` |
| 2026-16965 | Roadless | 2026-10-06 | 37 | Regs `modifyDate` |
| 2026-18297 | ANKTIVA | 2026-11-09 | 8 | Added Regs `links.self` |
| 2026-18298 | ANZUPGO | 2026-11-09 | 4 | Added Regs `links.self` |
| 2026-18300 | ANDEMBRY | 2026-11-09 | 5 | Added Regs `links.self` |

These are replays of previously authorized verdicts, not fresh legal determinations about the dates.
The rule and its conservative boundaries are recorded in [ADR 0010](../decisions/0010-review-evidence-freshness.md).

## Verification

- The two metadata regression cases failed under the old rule and pass under the new rule.
- Tests cover substantive payload and envelope changes, unrecognized fields, missing reviewed
  hashes/history, other sources, substantive change followed by reversion, all four verdict kinds,
  deterministic ordering, and immutable inputs.
- The review CLI integration test checks append → reconcile → queue/show: metadata remains in the
  log while the conflict stays retired; a changed deadline resurfaces without rewriting the verdict.
- Full workspace tests (`pnpm -r test`) and type checks (`pnpm -r typecheck`) pass using the Mini's
  existing dependencies and a disposable PostgreSQL 18 database.
- Pure replay checks all seven complete exported histories, including every intervening observation.
- A database rehearsal imports all 87 observations through ingestion into the disposable database,
  reproduces the seven current machine-derived conflicts, and runs `rederiveStaleWindows`.
  Result: **7 scanned, 7 rederived, 0 failed, 0 deadline version bumps**. Queue depth falls from
  7 to 0; every case has zero live conflicts, one retired conflict, and exactly its original verdict.
  All 87 stored observations remain unchanged by the sweep. Repeating it scans zero windows.

Raw snapshots, replay scripts, results, and test logs are local scratch artifacts in
`/private/tmp/docketclock-open-review-2026-09-23/`. They are not committed source fixtures.

## Rollout status

Implemented and verified locally. The running cluster has not been deployed or refreshed.
Apply the code through git → Argo CD, then use the supported re-derivation path and verify queue
membership again. A future substantive source change may correctly invalidate any of these verdicts.
