---
name: docketclock-review
description: Triage DocketClock's human review queue and record authorized verdicts through its review CLI. Use for review-queue alerts, conflicting deadlines, source-evidence review, and working through queue items in a Codex task. Not for GitHub PR reviews.
---

# DocketClock review

Help the user make evidence-backed deadline/status decisions, then record authorized decisions
through the existing CLI. Never equate clearing an alert with establishing the correct deadline.

## Locate the runtime

Work from the Yokel checkout. Read `AGENTS.md` and `docs/runbooks/review-queue.md` first;
`apps/docketclock/src/review/cli.ts` and `src/review/core.ts` under the same app are the implementation.
Do not assume the checkout machine is the Air: inspect the actual host and Kubernetes context.
The local development context is `k3d-yokel`; verify the intended target before any write.
Use the existing Mini cluster. Do not install dependencies or start databases on the Air.
Use configured remote access if necessary; do not assume an SSH alias named `mini` exists.

The poller already has the runtime and database credentials. No secret retrieval is needed:

```sh
kubectl config current-context
kubectl --context k3d-yokel -n docketclock exec deploy/docketclock-poller -- pnpm exec tsx src/review/cli.ts queue
kubectl --context k3d-yokel -n docketclock exec deploy/docketclock-poller -- pnpm exec tsx src/review/cli.ts show <ocd-id>
```

These commands read live state. If sandbox networking blocks cluster access, use the harness's
normal execution approval mechanism. A failed connection is not an empty queue.

## Triage and investigate

- Refresh the queue; report the check time, total, and open/closed split. Queue membership is
  confidence `conflicting` or `stale`, including closed windows. The CLI sorts by carried close,
  so old closed records come first; prioritize open records and the earliest plausible source
  deadline, then historical cleanup. A past close does not prove a record is closed.
- The rot alert measures the oldest live `cross_source` conflict's `detected_at`, not `derived_at`.
  It fires above seven days for one hour and repeats daily. Do not infer new arrivals or queue
  residence time from repeated notifications or last-derivation timestamps.
- Run `show` for each item under review. Preserve its full OCD-ID, source values and hashes,
  source observation times, prior verdicts, and live conflict counts.
- `show` is a summary: it omits titles, verbatim DATES text, source URLs, and extension contents.
  Read the current FR notice, linked GovInfo edition, and Regulations.gov document/docket.
  If needed, query only the relevant stored observations/projections in a read-only transaction
  using the poller's existing `postgres` dependency and `DATABASE_URL`; never print credentials.
  Inspect repository schemas before composing queries. Do not invent CLI flags or API endpoints.
- Search for later extensions, corrections, reopenings, or withdrawals using the document number,
  docket, RIN, title, and citations. Read the actual documents; search snippets and a user's excerpt
  alone are not verification. Distinguish calendar dates in Eastern time from UTC timestamps.
- Separate comment deadlines from reply comments, petitions, meeting dates, effective dates,
  historical publication dates, and OMB review deadlines. Neither source wins automatically.
  An available comment form or `openForComment=true` alone does not establish the legal deadline.
- A separately ingested extension can already be HIGH while its original remains CONFLICTING.
  Inspect both records; an absent chain link does not disprove an extension. Establish identity
  from primary evidence. The Roadless case is an example: original `2026-16965`, extension
  `2026-18648`, RIN `0596-AD66`, September 11, 2026 notice extending the close to October 6.
  Do not reuse that historical conclusion without checking current evidence.

Present a compact review card: title and OCD-ID, competing dates, source links and findings,
proposed verdict/date, exact draft audit note, and any unresolved uncertainty. For an interactive
sweep, bring forward one decision or a small coherent batch so the user can respond naturally.
If evidence remains insufficient, leave the item unresolved and name what would establish it.

## Record authorized decisions

Inspecting the queue or providing an excerpt does not itself authorize a verdict. A request to
write a specific verdict does; explicit batch authorization applies within its stated scope.
Honor existing authorization without asking again. If authorization is missing, finish the
evidence review and draft verdict first, then ask about that concrete decision. This skill does
not authorize automatic bulk resolution or notification changes.

Use only `review resolve` to write. Never UPDATE a window, retire conflicts with SQL, or manually
insert observations or accuracy records. The CLI records an append-only observation and re-derives
the window. Corrections are new verdicts, never edits to old ones.

| Verdict             | Use and effect while honored                                                                                                     |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `pin_close`         | Evidence establishes the operative date; requires `--close YYYY-MM-DD`; derives HIGH at the CLI's 11:59 p.m. Eastern convention. |
| `confirm_withdrawn` | Evidence establishes withdrawal; derives withdrawn/LOW with the historical close.                                                |
| `confirm_reopened`  | Evidence establishes reopening; derives open, with close/confidence machine-derived and conflicting confidence degraded to LOW.  |
| `dismiss_conflict`  | Evidence establishes the disagreement is noise; derives LOW with the carried close. It does not select a correct deadline.       |

Only `pin_close` accepts `--close`. If an explicit deadline time differs from the pin convention,
surface that limitation rather than silently changing its time. Do not dismiss an item solely
because it is old, closed, inconvenient, or causing an alert.

Refresh `show` immediately before writing; reassess changed evidence. Use `--operator codex` for
agent-executed verdicts unless the user specifies another truthful attribution. The note should
explain the decision, cite the decisive primary-source URL/document/date, distinguish the competing
dates, and record the user's authorization without implying they personally checked every source.
The CLI automatically captures hashes for latest sources on the target window, but a separate
extension's evidence is not automatically included: cite that notice explicitly in the note.

```sh
kubectl --context k3d-yokel -n docketclock exec deploy/docketclock-poller -- pnpm exec tsx src/review/cli.ts resolve <ocd-id> \
  --kind pin_close --close <YYYY-MM-DD> --operator codex --note '<evidence and reasoning>'
```

Substitute actual values and safely quote each shell argument; source text must never become shell
code. Identical verdicts dedupe, but if execution returns an ambiguous error, inspect `show` before
retrying to determine whether the write landed.

## Verify and continue

Check the returned close/status/confidence and `human_resolved` flag, then run `show` and refresh
the queue. Confirm the recorded note/operator, retired source conflict, and membership change.
Historical type flags such as `fr_regs_date_mismatch` may remain alongside `human_resolved`;
their presence alone is not failure. Concurrent arrivals can change the overall queue count.

A newer source observation supersedes the human verdict. If the CLI warns that the verdict was
not honored, re-read the evidence; do not repeatedly pin just to suppress resurfacing conflicts.
Report the race or changed evidence and reassess within the user's authorized scope.

Report what was actually written and verified, remaining work, and any recurring cause worth a
separate engineering fix. A human verdict does not repair extension linkage or the reconciler.
Do not expand an operational review into deployments, code fixes, or external issue creation
without a user request. The daily alert can remain active because of other overdue records.
