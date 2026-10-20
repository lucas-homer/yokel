# Review queue — the operator resolution path (Slice R)

The system detects wrongness (CONFLICTING windows, accuracy misses, xcheck disagreements); this
runbook is how a human **resolves** it. A resolution is an **observation, never a mutation**: the
`review` CLI appends a typed `human_review` verdict to the same append-only log the federal sources
write to, and the reconciler honors it under the supersedence rule below. There is no admin UPDATE
path, and the delivery API stays read-only — this CLI is the only write surface.

## Guided review in Codex

In a Codex task opened in this checkout, ask: **"Use $docketclock-review to work through the
review queue with me, one item at a time."** The repository's
[review skill](../../.agents/skills/docketclock-review/SKILL.md) gathers current source evidence,
checks for extensions and distinct deadline types, drafts verdicts, and writes authorized
decisions through this CLI. It verifies each result and preserves unresolved uncertainty.

## Running it

In-cluster, zero setup (the poller image ships `src/` and `DATABASE_URL`):

```sh
kubectl -n docketclock exec deploy/docketclock-poller -- pnpm exec tsx src/review/cli.ts queue
kubectl -n docketclock exec deploy/docketclock-poller -- pnpm exec tsx src/review/cli.ts show <ocd-id> [--blind]
kubectl -n docketclock exec deploy/docketclock-poller -- pnpm exec tsx src/review/cli.ts resolve <ocd-id> \
  --kind pin_close --close 2026-09-20 --note "why, in one honest sentence" --operator lucas \
  [--reviewer human|agent] [--expect <sha256> --expect <sha256> …]
kubectl -n docketclock exec deploy/docketclock-poller -- pnpm exec tsx src/review/cli.ts log \
  [--reviewer human|agent] [--operator <name>] [--kind <kind>] [--since 7d|2026-10-01] [--limit 50] [--json]
kubectl -n docketclock exec deploy/docketclock-poller -- pnpm exec tsx src/review/cli.ts corpus [--json]
```

`log` is the verdict ledger, newest first, each verdict with its **standing** under the engine's
honoring rule: `honored`, `parked` (an honored `escalate`), `superseded` (a later verdict exists),
`invalidated` (the latest verdict, but newer evidence returned the window to machine derivation) or
`unparseable`. `corpus` is the shadow-gate harness input (below).

`--reviewer` says who **decided** (default `human`; `agent` only for an unsupervised autopilot write,
[ADR 0015](../decisions/0015-agent-review-authority.md)); `--operator` says who executed the write.
`--expect` binds the write to the evidence you assessed (below). `--blind` is the shadow-gate view:
verdicts, the retired-conflict history and chain links are hidden and the window shown is the
machine's own derivation of the sources, so an agent under measurement cannot read the answer.

Host-side (port-forward the pg primary pod-direct, `docketclock-pg-app` creds):

```sh
DATABASE_URL=… pnpm --filter @yokel/docketclock review queue
```

## The weekly sweep

1. `review queue` — v1 queue = windows with confidence `conflicting` or `stale`, closing-soonest
   first. An empty queue is the goal state; PR-R4 adds the depth gauge + oldest-item alert so an
   unworked queue pages instead of rotting.
2. For each item: `review show <ocd-id>` — latest per-source values side by side, notice flags,
   prior verdicts, live/retired conflict counts, chain links. Check the sources' live pages when
   the payloads disagree (the xcheck triage discipline: verify against live regs.gov/FR before
   judging).
3. `review resolve` with the right kind and an honest `--note` — the note is the point; it is the
   audit trail a partner will eventually read.

## Verdict kinds

| kind                | asserts                                                                       | derives (while honored)                                                                                                                 |
| ------------------- | ----------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `pin_close`         | the operative close is `--close`                                              | that close at **HIGH** (11:59 p.m. ET convention), status from the pinned date                                                          |
| `confirm_withdrawn` | the notice is withdrawn (machine can't see it — e.g. the #112 identity split) | status `withdrawn`, LOW with the historical close (never push-eligible)                                                                 |
| `confirm_reopened`  | the window is open again                                                      | status `open`; close/confidence stay machine-derived (conflicting degrades LOW)                                                         |
| `dismiss_conflict`  | the detected disagreement is noise                                            | **LOW** with the machine's carried close — dismissal adds no corroboration and never picks a winner; if you know the close, `pin_close` |
| `escalate`          | primary sources examined; the discrepancy cannot be resolved from documents   | **nothing** — the window keeps its machine derivation and its live conflict; the item is _parked_ (see below) until a human decides     |

## Escalation — parking the irreducible cases

Some items (issue #127: an explicit published date, an explicit different portal cutoff, and no
document that explains the difference) should be neither pinned (that publishes HIGH on a disputed
date) nor dismissed (a real disagreement is not noise). `--kind escalate` records exactly that, with
a `--note` saying **what was searched** (FR notice, GovInfo edition, Regs document and docket list,
extension/correction/reopening search by document number, docket, RIN and title).

An escalation asserts nothing: the reconciler derives byte-for-byte what it would without it, the
window stays `conflicting`, the ConflictRecord stays live and the rot alert keeps ageing it — by
design, that is the standing reminder. What changes is visibility: `review queue` marks the row
`[escalated by <operator> (<reviewer>) <date>]` and counts parked items in its header, `review show`
reports `honored verdict: escalate … PARKED`, the autopilot skips parked items, the
`docketclock_review_queue_depth{reason="escalated"}` gauge counts them, and the
`review-queue-escalated` alert nags daily until none are left.

A parked item is honored for freshness like any verdict: a metadata-only Regs refresh keeps it
parked; a newer FR/GovInfo observation, a substantive Regs change, or the portal flipping to closed
after its own date un-parks it (the ADR 0014 echo exception is `pin_close`-only), after which it is
an ordinary queue member again. To resolve a parked item, write a real verdict with `review resolve`
— the latest verdict wins; a second `escalate` re-parks it. An escalate that would park nothing is
refused: if the window would not be a queue member with it (the sources agree, or the machine is
not conflicting), `resolve` rolls it back and says so — pin or confirm instead, or supersede the
wrong earlier verdict. Escalating over an honored pin you disagree with is fine: the window returns
to its conflicting machine derivation and parks.

## Provenance — who decided

Every verdict carries `reviewer` (`human` | `agent`, default `human`) and `operator`. The 2026-09
Codex pins are `reviewer=human, operator=codex`: a person authorized each one. While honored, a
verdict stamps exactly one provenance flag on the window — `human_resolved` or `agent_resolved` —
alongside the machine's type flags, so every consumer can see which authority resolved it. An
`escalate` stamps neither.

## Evidence binding — `--expect`

`review show` prints the latest-per-source payload hashes. Passing each of them as `--expect` makes
the write refuse — in one transaction, writing nothing — unless the live set is exactly that set,
both before and after the insert. The refusal names which assessed hashes are no longer latest and
which latest hashes were never assessed; re-run `show` and reassess. Automation always passes
`--expect`; a human may omit it and binds to whatever is live at write time (`reviewed_payload_hashes`
is filled either way).

## Autopilot — the scheduled agent

The review autopilot (`plans/review-autopilot.md`, [ADR 0015](../decisions/0015-agent-review-authority.md))
is a T3 Code scheduled task that runs the
[`docketclock-review-autopilot`](../../.agents/skills/docketclock-review-autopilot/SKILL.md) skill
daily at 07:00 local in a dedicated "Review autopilot" thread (provider `claudeAgent`, model
`claude-opus-5-5`, effort `high`; the thread lives in its own worktree on `main`, which each run
fast-forwards first). It is an operator like any other: it uses only this CLI through
`kubectl exec`, writes nothing the CLI would refuse, and has a phone-pageable owner. Its decisions
are bound by the plan's **write policy v1**: `escalate` first; `pin_close` only on a primary
document that states the deadline for that exact notice, explains the competing value, and that an
independent cross-provider verifier reads the same way; `confirm_withdrawn` on a live identity
check; never `dismiss_conflict` or `confirm_reopened`; at most 10 decisions per run; every write
`--reviewer agent --operator autopilot` with `--expect` for every live hash.

**Mode.** The task's prompt (kept verbatim in
[`scheduled-prompt.md`](../../.agents/skills/docketclock-review-autopilot/scheduled-prompt.md))
carries `AUTOPILOT_MODE=shadow|write`. In **shadow** it investigates and decides exactly as write
mode would but writes nothing and pages nobody except for tooling failures; its decisions are
_proposals_ in the host-side ledger `~/.config/yokel/review-autopilot/ledger.jsonl` and in the
run report. **Write** mode may be set only after the gate record below is complete.

**Pause / resume / kill.** From any T3 thread in this project: `list_scheduled_tasks` →
`update_scheduled_task enabled=false` (instant; resume with `enabled=true`), or
`delete_scheduled_task`. Verdicts already written remain, each supersedable (next item). Pause the
task **before** any rollback of the provenance-aware reconciler (ADR 0015).

**Reading what it did.** The narrative is the run report in the "Review autopilot" thread (queue
before/after, every decision with its verifier result and the `--expect` hashes, skips, pages).
The ledger of record is the DB:

```sh
kubectl -n docketclock exec deploy/docketclock-poller -- pnpm exec tsx src/review/cli.ts log --reviewer agent --since 7d
```

`honored` means the verdict still governs the window; `invalidated` means newer evidence overrode
it — the signal the Monday audit and PR-A4's attributable monitoring read. Shadow proposals are only
in `ledger.jsonl` (one JSON line per decision: run, hashes, proposal, verifier, evidence, reason).

**Superseding an agent verdict.** Write a human verdict; the latest wins and the window stamps
`human_resolved` instead of `agent_resolved`:

```sh
kubectl -n docketclock exec deploy/docketclock-poller -- pnpm exec tsx src/review/cli.ts resolve <ocd-id> \
  --kind <pin_close|confirm_withdrawn|confirm_reopened|dismiss_conflict|escalate> [--close YYYY-MM-DD] \
  --operator <you> --note "why the agent's verdict was wrong, with the decisive source"
```

Never edit or delete the agent's row; corrections accrete. If the same mistake recurs, amend the
policy in the plan (and this skill) before re-enabling write mode.

### Shadow gate — what must be true before write mode

Three parts, measured on `show --blind` (prior verdicts hidden), each recorded here with the date,
the run id and the tally. Write mode may be enabled only when all three are recorded as met.

1. **Blinded historical agreement** — `review corpus` part 1: every honored `pin_close`. The
   agent's blind proposal must equal the pinned date on ≥ 95 % of them, with every disagreement
   explained. Measures agreement with human-authorized precedent, not truth: a floor, not the gate.
2. **Held-out independent set** — 10 current queue items the operator reviews **before** seeing
   any proposal. Protocol: pick the ids from `review queue`; write your verdict for each (`kind`,
   `close` for a pin, one line of reasoning) to `~/.config/yokel/review-autopilot/held-out-<date>.json`
   _before_ reading the thread or the ledger; let the daily shadow runs propose; compare. Agreement
   on kind ≥ 9/10; **any false pin** (the agent pins where you escalated or chose another date) is
   blocking until explained and the policy amended. Refresh the set whenever the policy changes.
3. **Escalation discipline** — `review corpus` part 3: every parked item → `escalate`, every
   honored withdrawal → `confirm_withdrawn`, and zero proposed `dismiss_conflict` /
   `confirm_reopened` anywhere in the runs.

| part                             | date | run id | result | met? |
| -------------------------------- | ---- | ------ | ------ | ---- |
| 1 — blinded historical agreement |      |        |        |      |
| 2 — held-out independent set     |      |        |        |      |
| 3 — escalation discipline        |      |        |        |      |

Flipping to write: update `scheduled-prompt.md` and the task's prompt (`update_scheduled_task`)
to `AUTOPILOT_MODE=write` in the same change, and note the date in this table's caption.

## Supersedence — what "honored" means

Your verdict remains authoritative while the evidence it reviewed remains current. A newer source
observation returns the window to pure machine derivation unless it qualifies for the narrow
metadata exception below. If the sources still disagree, the conflict **resurfaces** (a live
ConflictRecord, back in the queue). A resolution changes what we assert, never what we watch.

Since `reconcile-v2.1` ([ADR 0010](../decisions/0010-review-evidence-freshness.md)), Regulations.gov
refreshes may differ only in `data.attributes.modifyDate` and top-level `links.self`. The full
remaining payload and observation envelope must match the latest pre-verdict Regs observation,
whose hash must be in `reviewed_payload_hashes`. Every intervening source observation must pass;
a substantive change followed by a reversion does not revive the verdict. Missing evidence,
unknown changed fields, parser/notice-flag changes, and newer FR/GovInfo observations still
invalidate it. Raw payloads, hashes, notes, and operators remain unchanged. Equal timestamps
retain the original tie policy. Practical consequences:

- Resolving is idempotent and safe to retry (identical verdicts dedupe on the window).
- A second verdict supersedes the first (latest wins); corrections accrete, nothing is edited.
- `resolve` prints the re-derived window — if it warns "verdict NOT honored", a source observation
  may have invalidated it, or the verdict could not be parsed; inspect the evidence before re-issuing.
  The check is the engine's own honoring rule (`selectHonoredVerdict`), not the presence of a flag,
  so it is right for `escalate` too; `show` prints the same decision as `honored verdict:`.
- Evidence is recorded automatically: `reviewed_payload_hashes` is filled from the latest per-source
  observations at write time.

Guards: `resolve` refuses an unknown ocd-id and a window with no source observations (a typo must
never mint a source-less HIGH window).

## xcheck integration

An `our_bug` triage on an **open** window (spikes/out/XCHECK_diff.md) gets resolved through this
CLI — the verdict enters the audit chain, and the markdown table stops being the system of record
for live-data judgments. Closed-window misses keep flowing the PR-V2 regression-fixture path
(`export:accuracy-miss`). The five #112 shadow-withdrawn originals are the standing example: each
gets `confirm_withdrawn` with a note citing the live regs.gov check.

## Out of scope (deliberate)

Chain-ambiguous pair triage and dead-letter replay live in follow-ups; manual AccuracyRecords stay
off-limits (the verifier is the only accuracy writer); the D5 web console is spec'd by this CLI.

## Rolling out a reconciler rule change

Deploy the versioned reconciler through git → Argo CD. Then run the existing
`src/db/rederive-stale-windows.ts` sweep from the deployed image to refresh projections stamped
with the previous rule version (see that script for the command). Re-derivation preserves the
append-only observation log and retires resolved conflicts through the normal persistence path.
Verify affected items with `review show` and `review queue`; do not add duplicate verdicts just
to force a refresh. A code deployment alone does not refresh windows without new observations.

Since `reconcile-v2.2` ([ADR 0014](../decisions/0014-portal-close-echo-preserves-pin.md)) a Regs
refresh that only records the portal's own announced close (`openForComment` /
`withinCommentPeriod` `true → false` after the pinned date, same `commentEndDate`) no longer
resurfaces a window whose pin equals the portal's own Eastern close date. If such a window does
resurface after its close, something other than those two flags changed and `review show` will
show it. A pin that differs from the portal's date still resurfaces when the portal closes, by
design: the portal closed on a date the pin did not assert. The v2.2 sweep re-derives every window
stamped with an older version and is expected to retire the 7 echo conflicts with no version
bumps, because the pinned instant equals the `resolved_close_utc` already stored.

`reconcile-v2.3` ([ADR 0015](../decisions/0015-agent-review-authority.md)) adds the `escalate`
kind and the `reviewer`-driven provenance flag. No existing row derives differently (no escalate or
agent verdicts exist before it ships), so its sweep is expected to re-stamp every window and change
nothing; run it anyway so the stamps are honest.
