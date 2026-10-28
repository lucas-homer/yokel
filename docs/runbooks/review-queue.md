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
kubectl -n docketclock exec deploy/docketclock-poller -- pnpm exec tsx src/review/cli.ts corpus [--blind] [--json]
```

`log` is the verdict ledger, newest first, each verdict with its **standing** under the engine's
honoring rule: `honored`, `parked` (an honored `escalate`), `superseded` (a later verdict exists),
`invalidated` (the latest verdict, but newer evidence returned the window to machine derivation) or
`unparseable`; `--limit` caps the newest N and the output says so when more matched. `corpus` is the
shadow-gate harness input (below): `--blind` prints only the ids, flat and sha256-ordered — the
proposer's view; everything else (`expected_close`, the grouping) is the scorer's. `log`, `corpus`
and the `show` identity line exist in-cluster only once the poller image built from PR-A3 is
rolled; until then the pod's CLI prints usage for them.

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
`claude-opus-5-5`, effort `high`; the thread lives in its own worktree on branch
`t3/review-autopilot`, created from `main`, never committed to, and fast-forwarded to `origin/main`
by each run). It is an operator like any other: it uses only this CLI through
`kubectl exec`, writes nothing the CLI would refuse, and has a phone-pageable owner. Its decisions
are bound by the plan's **write policy v1.2**: `escalate` first; `pin_close` only on a primary
document (an FR document, its GovInfo edition, the notice's own Regulations.gov text, or an
agency-authored extension document in the notice's own docket) that states the deadline for that
exact notice, explains the competing value, and that an
independent cross-provider verifier reads the same way; `confirm_withdrawn` on a live identity
check; never `dismiss_conflict` or `confirm_reopened`; at most 10 decisions per run; every write
`--reviewer agent --operator autopilot` with `--expect` for every live hash.

**Mode.** The task's prompt (kept verbatim in
[`scheduled-prompt.md`](../../.agents/skills/docketclock-review-autopilot/scheduled-prompt.md))
carries `AUTOPILOT_MODE=shadow|write`. In **shadow** it investigates and decides exactly as write
mode would but writes nothing and pages nobody except for tooling failures; its decisions are
_proposals_ in the host-side ledger `~/.config/yokel/review-autopilot/ledger.jsonl` and in the
run report. **Write** mode may be set only after the gate record below is complete, and the prompt
must then also carry `AUTOPILOT_GATE=met:<date>` — the agent cannot read this runbook during a run,
so that token is how it knows the gate was recorded; `write` without it runs as shadow and pages.

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
it — the Monday audit reports those as is, and PR-A4's attributable monitoring grades them. Shadow
proposals are only in `ledger.jsonl` (one JSON line per decision: run, mode, policy version,
harness id, ocd_id, hashes, proposal, verifier, evidence, note, written, observation_id, reason).
The Monday audit's re-reads are done by a fresh networked Claude child that sees only ids (never
the verdicts), so the agent never grades its own homework; it covers 5 of the week's honored agent
verdicts (chosen by hash order, not by the agent), every parked item (a human-parked item is only
reported, never re-decided), and in shadow mode every shadow escalation of the week.

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

**Blind by construction.** Parts 1 and 3 are run on request (ask the "Review autopilot" thread to
"run the shadow harness"), never by the daily schedule, and in three separate contexts: the thread
only orchestrates and never reads an expectation (it is also the daily part 2 proposer); fresh
_proposer_ children get only the ids from `review corpus --blind` (flat, sha256-ordered, no
grouping, no expectation) and seal one line per id in their own `harness-<run id>/` files; a fresh
_scorer_ child then reads `review corpus --json`, the required set below and those files, and
returns the tallies. Anything that had seen `expected_close`, the `pins` / `escalations` grouping
or this table could not be blinded afterwards.

1. **Blinded historical agreement** — `review corpus` part 1: every honored `pin_close`. The
   proposer's blind proposal must equal the pinned date on ≥ 95 % of them (the denominator is every
   human-reviewer pin; a missing or skipped proposal counts against), with every disagreement
   explained. Measures agreement with human-authorized precedent, not truth: a floor, not the gate.
   Run without the verifier (it measures the proposer, not the pipeline). Agent-reviewer pins, once
   write mode has produced some, are excluded: they are the autopilot's own output.
2. **Held-out independent set** — 10 current queue items the operator reviews **before** seeing
   any proposal. Protocol: pick the ids from `review queue`, excluding the five ids of the required
   set below (the thread never sees their expectations, but they are gate items, not independent
   ones); write your verdict for each (`kind`,
   `close` for a pin, one line of reasoning) to `~/.config/yokel/review-autopilot/held-out-<date>.json`
   _before_ reading the thread or the ledger; let the daily shadow runs propose (full pipeline,
   verifier included); compare. Agreement on kind ≥ 9/10; **any false pin** (the agent pins where
   you escalated or chose another date) is blocking until explained and the policy amended.
   Refresh the set whenever the policy changes. The agent is forbidden to read these files.
3. **Escalation discipline** — the **required set** below, plus whatever `review corpus` part 3
   lists at run time: every one of these must be proposed `escalate` (the #127 cases) or
   `confirm_withdrawn` (the withdrawals), and zero `dismiss_conflict` / `confirm_reopened` may
   appear anywhere in the harness run. An empty live category never passes by vacancy: a missing
   proposal is a disagreement.

   | required set (part 3)                         | expected            | why                                          |
   | --------------------------------------------- | ------------------- | -------------------------------------------- |
   | `ocd-participation-window/federal/2026-15983` | `escalate`          | #127 CDC — parked live 2026-10-19            |
   | `ocd-participation-window/federal/2026-18052` | `escalate`          | #127 FAA — still an ordinary queue member    |
   | `ocd-participation-window/federal/2026-16791` | `escalate`          | #127 Census — still an ordinary queue member |
   | `ocd-participation-window/federal/2026-14942` | `confirm_withdrawn` | #112 shadow-withdrawn, confirmed 2026-09-03  |
   | `ocd-participation-window/federal/2026-15740` | `confirm_withdrawn` | #112 shadow-withdrawn, confirmed 2026-09-03  |

   The two un-parked #127 items are in the live queue, so `corpus --blind` does not list them: the
   scorer reports them as "not proposed" and the operator asks for a second harness pass with those
   ids supplied explicitly to a fresh proposer. Escalating them by hand (so the gauge and the alert
   see all three) is a separate, worthwhile step; it does not change this set.

| part                             | date | run id | result | met? |
| -------------------------------- | ---- | ------ | ------ | ---- |
| 1 — blinded historical agreement |      |        |        |      |
| 2 — held-out independent set     |      |        |        |      |
| 3 — escalation discipline        |      |        |        |      |

Flipping to write: fill the table, then update `scheduled-prompt.md` and the task's prompt
(`update_scheduled_task`) to `AUTOPILOT_MODE=write` plus `AUTOPILOT_GATE=met:<date>` in the same
change, and note that date below this table.

Gate flipped to write on: _not yet_.

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

### `reconcile-v2.4` — the amended FR close ([ADR 0016](../decisions/0016-fr-amendment-close.md))

`reconcile-v2.4` lets a deterministically linked FR extension or correction move the original
window's FR side, verified from the amendment's published GovInfo text. It also adds a GovInfo
sweep and a post-chain re-derive pass to the poll cycle, the FR parser bump `fr-v3`
(`correction_of` ⇒ correction) and contract 0.12.0 (`fr_close_amended`). Its one migration, 0013,
only adds indexes for the amendment loader; `govinfo` is already a 0001 `source` member, and
`conflict_flags` is JSONB with no CHECK.

**Expected result, in one line** (measured on a replay of the 2026-10-27 production dump): the
rederive sweep reports `versionBumped 1` and `failed 0`; the three target windows leave the queue
`high` with `fr_close_amended`; 12 closed windows enter it as `conflicting`; `review queue` goes
from 36 to 45. Every protected window (PHMSA, USCG, ICE, EPA, listed below) is unchanged.

**Deploy.** The docketclock app tier is a plain Helm release, not an Argo application
(`app-docketclock.yaml` was never applied), so merging alone does not deploy it. Deploy it the way
`reconcile-v2.2`/`v2.3` and the autopilot PRs were: run Tilt in CI mode from a clean checkout of the
merged `main`. Tilt builds the image, pushes it to the k3d registry (`yokel-registry:5000`, tag
`tilt-<content hash>`), applies the chart with local values, re-runs the migrate Job (migration 0013)
and waits for both workloads:

```sh
git worktree add --detach /tmp/yokel-deploy origin/main   # clean tree at the merge commit
cd /tmp/yokel-deploy && tilt ci --port 10351
```

Before relying on it, confirm the release really is Helm-only with
`kubectl -n argocd get application docketclock` (expect NotFound). If it is now Argo-managed, the
deploy is git → Argo sync instead, and Tilt would fight it.

**First poll cycles.** After the FR pass, `govinfoSweepOnce` (log line `govinfo sweep cycle`)
fetches the GovInfo HTML for every FR amendment document in the 120-day keyword lookback that has no
`govinfo` observation yet. That means any of the four flags, or a non-empty `correction_of`, which
also catches the stored fr-v2 C1 row. It fetches at most 50 per cycle
(`GOVINFO_MAX_FETCHES_PER_CYCLE`), 300 ms apart, never-failed documents first and then newest
first. It is append-only and backfills the existing amendments over the first few cycles.
U+0000 page-break artifacts are stripped from each page before storage (Postgres cannot hold them).
A 404 within 3 days of publication counts as `notPublished` and is retried next cycle. A later 404,
or any other error, is recorded in `poll_dead_letter` (source `govinfo`). After 3 consecutive
failures the document is dead-lettered (WARN `govinfo sweep: document DEAD-LETTERED`), and from
then on it is retried only once a day, behind every fresh candidate. To list them:
`select document_key, attempts, last_error from poll_dead_letter where source = 'govinfo'`. After the chain pass, `rederiveChainOriginals` (log `amended originals cycle`,
or a WARN `amended originals MOVED a close`) re-derives the originals of every confident
cross_window link. That way the Census, USDA and IRS windows pick up the amendment in the same
cycle the text lands. Expect the chain summary's `linked` to rise: the IRS correction is now
chained through `correction_of`, and the USDA and USCG pairs become confident through the
`citation` basis. `llmLinked` drops correspondingly. Expect no new pass failures
(`docketclock_poll_pass_failures_total{pass="govinfo"|"amended_originals"}`).

**Then run the rederive sweep** once, after the GovInfo backfill has landed (at least one full
cycle with `govinfo sweep cycle` showing `candidates: 0`, or no remaining amendment candidates):

```sh
kubectl -n docketclock exec deploy/docketclock-poller -- pnpm exec tsx src/db/rederive-stale-windows.ts
```

It re-stamps every window `reconcile-v2.4`. Migration 0013 adds the indexes the amendment loader
needs, and the migrate Job applies it on deploy. On a production copy (8,296 windows) the sweep took
24–29 s. Before 0013, the same copy took 65 s with no loader, and an estimated hours with the
unindexed loader. Expect `failed 0` and `versionBumped 1`. On the 2026-10-27 production copy the one
bump was EPA 2026-05167: an FR-only window, LOW confidence, closing May 1. Extension 2026-08518
(shared docket and RIN, published May 1) moves it to May 15. Any other bump means a close moved
unexpectedly: inspect it with `review show` before going further.

**Verify.**

```sh
kubectl -n docketclock exec deploy/docketclock-poller -- pnpm exec tsx src/review/cli.ts show ocd-participation-window/federal/2026-18481
kubectl -n docketclock exec deploy/docketclock-poller -- pnpm exec tsx src/review/cli.ts show ocd-participation-window/federal/2026-18531
kubectl -n docketclock exec deploy/docketclock-poller -- pnpm exec tsx src/review/cli.ts show ocd-participation-window/federal/2026-18574
kubectl -n docketclock exec deploy/docketclock-poller -- pnpm exec tsx src/review/cli.ts queue
```

**Expected effect.** The IRS (2026-18574, Oct 16 → Oct 26 via C1-2026-18574), Census (2026-18481 →
Nov 2 via 2026-20328) and USDA (2026-18531 → Nov 2 via 2026-19710) windows become `high` with
`fr_close_amended`, plus `tz_normalization_only` where the UTC day differs. Their cross_source
conflicts retire, so they leave `review queue`. `raw_fr_close_date` still shows the original FR
date.

**Human verdicts survive the GovInfo sweep.** The sweep appends a `govinfo` observation to every
recent amendment document's own chain, including windows a person already resolved. Under
`reconcile-v2.4` that row is not evidence about the window (ADR 0016 §6; only `federal_register` and
`regulations_gov` are). It neither supersedes an honored verdict nor un-parks an escalation, and it
is not part of the `--expect` set: `review show` lists it under `context`. On the replay, 12
human-resolved windows had such a row land after their verdict:
2026-13006, 15026, 15671, 16083, 16246, 16247, 16713, 17890, 18218, 18297, 18298 and 18300. All 12
must still show their verdict as `honored verdict:` after the sweep and after the rederive sweep. If any of
them shows "superseded by newer evidence" with only a `govinfo` row newer than its verdict, that is a
regression.

**A linked amendment newer than a verdict reopens it (ADR 0016 §7).** A linked extension,
correction, reopening or withdrawal is an input to the original window's derivation. If one lands
after the window's verdict and changes what the window derives, the verdict is superseded and the
window returns to the queue for re-review. A GovInfo copy that only confirms the same date does
not count. `review show` now lists the linked amendments' FR and GovInfo rows under "latest per
source" (`linked amendment <docnum> …`), and those hashes are part of `--expect`. On the
2026-10-27 production copy, the seven closed pinned windows that gain `fr_close_amended`
(2026-07061, 07800, 10815, 12621, 13294, 13674, 16965) all stay honored. Each amendment was
fetched before its verdict and each pin already equals the amended date.

Measured on the 2026-10-27 production copy, 23 windows derive differently in total. An amended date
moves a window only when it is corroborated (ADR 0016 §8): by the window's own portal close, or by
the amendment's own plausible FR `comments_close_on`. `ambiguous` never changes a window.

- **3 conflicting → high.** The three windows above, all corroborated by the portal. Census's
  amendment also carries a matching FR close; USDA's FR value (2026-09-11) is the bad one and is not
  used; IRS's correction has none.
- **7 high → high.** Closed windows; the only change is the added `fr_close_amended` flag. Each is
  corroborated by both the portal and the amendment's FR close.
- **1 low → low, close moved.** EPA 2026-05167, FR-only with no portal. It moves May 1 → May 15
  because extension 2026-08518's own FR `comments_close_on` (May 15) corroborates the text.
- **12 medium → conflicting.** All closed: 2026-09791, 09792, 10611, 12696, 12922, 13123, 13944,
  14552, 14702, 14974, 15483 and 16258. Their own FR close and the portal agreed; the portal had
  already flipped `openForComment` to false, which is why they were MEDIUM. A deterministically
  linked, text-verified extension then moved the FR side later, and in every case the extension's
  own FR `comments_close_on` corroborates the new date. Their portals disagree, so they are
  conflicting.
- **2026-13761 stays unchanged.** It was the 13th last round. Its extension 2026-18218 really does
  extend the period 90 days to Dec 7, but nothing corroborates that: its FR `comments_close_on`
  (2026-07-08) is a publication-date extraction error, like USDA's, and the portal still shows
  Sep 8. That is the deliberate cost of the backstop.
  - **Stale polling is not the cause.** In all 13 (the 12 above plus 2026-13761), measured on both the production copy and the
    replay database, we fetched a Regulations.gov observation of the original document after the
    extension was published (and after we had ingested it). It still showed the original date. The
    agency extended through the new FR document and left the original's portal date where it was.
  - **Consequence.** These are real FR-vs-portal disagreements, not artifacts of our polling. The
    published close stays the portal instant, and they enter the closed part of `review queue`.
  - **Decision for the user.** Whether to accept them in the queue as they are; the reconciler does
    not change their semantics.

Nothing else should change. In particular:

- ICE 2026-20660 stays as it is: its stored 12-07 value has no amendment, and FR revising its own
  metadata is a separate follow-up.
- The USCG 2026-17216/19895 reopening stays `ambiguous`, so no move.
- PHMSA and EPA 2026-18134 have no FR amendment, so they stay unchanged.

`show` on a window with any other movement should explain it with an `fr_close_amended` flag and an
amendment observation id in `current_observation_ids`. Anything unexplained is a regression. Roll
back by redeploying the previous image, then running its rederive sweep. The observation log is
append-only, so re-deriving under the old engine restores the old projection. The `govinfo` rows
stay in the log, and the old engine ignores them.
