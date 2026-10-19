# 0014. The portal recording its own announced close is not new evidence

- Status: Accepted
- Date: 2026-10-17
- Amends: [0010](0010-review-evidence-freshness.md)

## Context

Seven pinned windows resurfaced in the review queue as **closed** conflicting items. In every case
the human had pinned the close to the date Regulations.gov itself announced: the reviewed baseline's
`commentEndDate`, read as an America/New_York calendar date, equals `pinned_close_date`
(e.g. `2026-10-03T03:59:59Z` is Eastern 2026-10-02 = pin 2026-10-02), with `openForComment` and
`withinCommentPeriod` both `true`. A few hours after 11:59:59 p.m. ET of that date, a Regs refresh
flipped only those two flags to `false`; later refreshes repeated the flipped state. No newer
Federal Register or GovInfo observation existed.

ADR 0010 exempts only `modifyDate` and `links.self`, so `reconcile-v2.1` counted the flip as new
evidence, dropped the pin, and re-queued the window. The seven were 7 of the 26 closed queue
items. Any pin equal to the portal's own date will echo on its close date, so no review policy
fixes this: it is a treadmill, and the fix belongs in the reconciler.

## Decision

`reconcile-v2.2` keeps the v2.1 rule and adds one narrow exception. A newer Regulations.gov
observation chain still counts as the reviewed evidence when **all** of the following hold:

1. The latest verdict is `pin_close` and is otherwise eligible exactly as in v2.1: a baseline
   exists (latest Regs observation at or before the verdict, same deterministic tiebreak) and its
   `payload_hash` is in `reviewed_payload_hashes`. `confirm_withdrawn`, `confirm_reopened` and
   `dismiss_conflict` get no exception.
2. The baseline's `commentEndDate` is non-null and its America/New_York calendar date strictly
   equals `pinned_close_date`. The transition is predicted by the portal's own date; fetch timing
   is not asked to prove anything else.
3. Beyond the ADR 0010 metadata fields, the only differences between the baseline and any
   post-verdict observation are `data.attributes.openForComment` and/or
   `data.attributes.withinCommentPeriod`, and each of those must either deep-equal the baseline's
   value or be boolean `false` where the baseline's was boolean `true`. Everything else
   invalidates: absent↔present, non-boolean values (the string `"false"`), `true → null`,
   `false → true`, any other attribute, any top-level or data-level change, any envelope change
   (parser version, notice flags, identifiers, `raw_dates_text`), or a newer non-Regs observation.
   Either flag may flip alone.
4. Every post-verdict observation showing a flipped value has `fetched_at` **strictly after**
   `frCloseDateToUtcInstant(pinned_close_date)` (11:59:59 p.m. ET, DST-correct). Equality fails.
5. Monotonic over the whole post-verdict history in deterministic order (fetch epoch, then
   observation ID): once a flag is observed `false`, every later observation shows it `false`. A
   later `true` invalidates. Two post-verdict observations with the same fetch epoch that disagree
   in flag state invalidate; ambiguous order fails closed.

Pins that differ from the portal's date keep invalidating. That is correct: the portal then closed
on a date the pin did not assert, and a human should look. Everything else in v2.1 stands: full
envelope comparison, every intervening observation checked, equal-to-verdict timestamps are not
"newer", and a later human verdict supersedes. The honored overlay is unchanged (HIGH,
`human_resolved` alongside the machine flags, status from the pinned instant).

The decision is pure reconciler logic, stamped `RECONCILER_VERSION = "reconcile-v2.2"`. No contract
change, no payload or hash mutation, no change to ingestion or deduplication.

## Consequences

- The echo stops for pins equal to the portal's own date. A flip followed by a reopen invalidates,
  so a reopened portal is never left pinned closed by an honored pin overriding the status rule.
- Rollout: deploy via git → Argo CD, then run the `rederive-stale-windows.ts` sweep. Expected queue
  depth 42 → 35, no verdicts written, and no deadline version bumps because the pinned instant
  equals the `resolved_close_utc` the live v2.1 rows already carry.
- Rollback: redeploy the `reconcile-v2.1` rule (code and version stamp together) and run the sweep;
  the seven return to the queue and nothing else changes. Changing only `RECONCILER_VERSION` is not
  a rollback: the sweep would re-derive every window with the v2.2 rule still active.
- Verification: a positive test per clause (each flag alone, both together, both in succession, DST
  edges, offset-form dates, order independence, immutability), an adversary test per negative in
  clause 3–5 and per non-pin kind, and a committed read-only replay of all seven live histories
  (`test/fixtures/review-echo-histories.json`, 210 observations), including truncated histories
  ending before and exactly at the first flip. The replay does not change cluster data.
