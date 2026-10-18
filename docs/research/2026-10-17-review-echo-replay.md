# Portal close echo: seven-case replay

Verified `reconcile-v2.2` against a read-only export of the full observation histories of the seven
live windows that exhibit the echo, taken at **2026-10-18 06:13:26 UTC** and committed as
`apps/docketclock/test/fixtures/review-echo-histories.json` (210 observations, one `pin_close`
verdict per window, plus the live `participation_windows` rows at export time). The fixture is a
read-only export; no cluster data was changed.

## Result

Under `reconcile-v2.1` all seven are `conflicting`, `closed`, flagged `fr_regs_date_mismatch`, and
sit in the review queue. Under `reconcile-v2.2` every window reconciles to `high` confidence,
`closed` status, no conflict, flags `fr_regs_date_mismatch` + `human_resolved`, and
`resolved_close_utc` equal to the pinned instant, which is the value the live v2.1 row already
carries. The projection sweep can therefore retire the conflicts without a version bump.

| Document   | Subject                                   | Pinned close | Observations | First flip observed at |
| ---------- | ----------------------------------------- | ------------ | -----------: | ---------------------- |
| 2026-08826 | Title 21 terminology                      | 2026-10-02   |            8 | 2026-10-03T07:01:55Z   |
| 2026-13615 | PFOA/PFOS in biosolids draft guidance     | 2026-10-05   |           75 | 2026-10-06T05:57:29Z   |
| 2026-16246 | DAYVIGO                                   | 2026-10-09   |            7 | 2026-10-10T07:33:59Z   |
| 2026-16247 | BRINSUPRI                                 | 2026-10-09   |            8 | 2026-10-10T07:34:00Z   |
| 2026-16664 | National Organic Standards Board          | 2026-10-01   |           31 | 2026-10-02T05:57:28Z   |
| 2026-16776 | America's Great Corridors of Commerce RFI | 2026-10-02   |           27 | 2026-10-03T07:01:50Z   |
| 2026-16965 | Roadless                                  | 2026-10-06   |           54 | 2026-10-07T07:47:19Z   |

In each case the reviewed Regs baseline's `commentEndDate`, in Eastern time, equals the pinned
date; the first post-close refresh changed only `openForComment` and `withinCommentPeriod` from
`true` to `false`; later refreshes repeated that state; no newer FR or GovInfo observation exists.

These are replays of previously authorized verdicts, not fresh legal determinations about the dates.
The rule and its fail-closed boundaries are recorded in
[ADR 0014](../decisions/0014-portal-close-echo-preserves-pin.md), which amends ADR 0010.

## Verification

- Clause tests: each flag alone, both flags in one observation, both in successive observations,
  DST edges (pinned 2026-11-01 and 2026-03-08: a flip one second after the pinned instant is
  honored, one second before is not), an offset-form `commentEndDate`, a baseline already `false`
  (plain v2.1 path), a repin after an invalidating change, input order reversal, immutable inputs,
  and two runs deep-equal.
- Adversary negatives: flip before or exactly at the pinned instant; pin one day off the portal's
  Eastern date (including the UTC-day artifact); flip plus a date, attribute, or envelope change;
  each non-pin kind; flip then revert (both flags and each alone); a material change then revert
  before the flip; a newer FR or GovInfo observation; `false → true`; absent↔present flags; the
  string `"false"`; tied timestamps that disagree; a missing reviewed hash; omitted history.
- Live replay: all seven complete histories reconcile as above; truncated histories ending before
  the flip and exactly at the first flipped observation are also honored.

## Rollout status

Implemented on branch `t3/automate-federal-review`. The running cluster has not been deployed or
re-derived. Apply through git → Argo CD, then run the `rederive-stale-windows.ts` sweep. The sweep
re-derives every window stamped with an older reconciler version, not just these seven; expected:
the 7 echo conflicts retired, 0 version bumps, queue 42 → 35. Verify with `review queue` /
`review show`. A
future substantive source change may correctly invalidate any of these verdicts.
