# Review Autopilot — an agent works the human review queue; humans get only the irreducible tail

> Status: **IN PROGRESS** (proposed 2026-10-16; revised the same day after a cross-provider review
> by Codex GPT-6 Astra, whose ten findings are folded in below). PR-A1 and PR-A2 are merged and
> deployed; PR-A3 is in review; nothing is scheduled and no agent verdict has been written.
> Follows Slice R (`plans/review-resolve.md`, shipped) and ADR 0010. Every number below is a
> measurement from a live read of the k3d cluster on 2026-10-16 19:10Z, not an estimate.
> Target: local k3d, no new platform services, no new RAM. The agent runs **outside** the cluster
> (T3 Code scheduler on the Mini, claude.ai subscription), operates the existing `review` CLI through
> `kubectl exec`, and never touches the reconciler, the contract, or the DB directly.

## Why this slice, why now

The queue is growing faster than a weekly human sweep clears it, and the agent-assisted path
already carries most of the load: of the 51 verdicts ever written, 49 are `pin_close` verdicts
with `operator=codex` (2026-09-19 → 09-28, each individually authorized by the operator via the
`docketclock-review` skill) and 2 are `confirm_withdrawn` by `claude`. What is missing is (1) a
reconciler rule so correct pins stop echoing back into the queue, (2) a written policy that
replaces per-item authorization, (3) a durable parking state for the irreducible cases, (4) a
write path that binds a verdict to the evidence actually assessed, and (5) an honest measure of
agent accuracy that does not grade the agent's own homework.

## What the live queue looks like (2026-10-16 19:10Z)

| measure                                                | value                                                                            |
| ------------------------------------------------------ | -------------------------------------------------------------------------------- |
| queue depth                                            | 42 windows, **all** `fr_regs_date_mismatch` (no `stale`, no `withdrawn_vs_open`) |
| open / closed                                          | 16 open / 26 closed                                                              |
| arrivals last 24h                                      | 6                                                                                |
| oldest live conflict                                   | 117 days (`2026-10115`)                                                          |
| windows with a verdict, still honored                  | 44 = 42 pins at HIGH + 2 withdrawals at LOW                                      |
| windows with a verdict, **un-honored** (back in queue) | 7                                                                                |
| retired cross-source conflicts (lifetime)              | 586                                                                              |

The 42 split into recognisable classes (from the raw FR `comments_close_on` vs Regs `commentEndDate`):

- **Regs later than FR by weeks** (≈25) — the pattern every one of the 49 codex pins resolved:
  an extension or a different docket-level date on Regs; the pin went to the date a primary
  document established. Includes a 10-item PHMSA cluster (`PHMSA-2025-01xx` / `2026-15xx`,
  FR 06-23 vs Regs 09-05 and 11-21) that is one investigation, not ten — **after** confirming each
  notice's identity individually (a cluster is a hypothesis, not evidence).
- **FR later than Regs** (≈9) — e.g. `FDA-2025-E-*` (patent-review notices where FR metadata carries
  the petition date and Regs the comment date — issue #124, six already pinned), FAA `2026-18052`,
  DEA `2026-19538`, ICEB `2026-20660`.
- **Off-by-one-day** (≈4) — `2026-10115` (06-22 vs 06-21), `2026-16791`, `2026-20154`,
  `2026-15078`: a portal cutoff one or two days off the published date with no extension on
  record. This is the issue #127 class.

### Finding 1 — the measured echo class: correct pins invalidated by the portal closing

All 7 un-honored windows were pinned correctly: the Regs `commentEndDate` never moved and, in
Eastern time, **equals** the pinned date in every case. Each was invalidated by the first Regs
refresh fetched after the pinned close passed, whose only non-metadata change was
`openForComment: true → false` and `withinCommentPeriod: true → false` — the portal recording the
close its own date announced. ADR 0010 (`reconcile-v2.1`) exempts only `modifyDate` and
`links.self`, so this flip counts as new evidence and the window resurfaces as a **closed**
conflicting item.

Consequence: any pin whose date equals the portal's own date will echo on its close date. 7 of the
26 closed items are this echo. No review policy fixes a treadmill; PR-A1 below is a reconciler
rule and ships first. (Pins that differ from the portal date are a different class and still
invalidate — see PR-A1.)

### Finding 2 — the "truly needs a human" class is already defined and is ~6%

Issue #127 documents three cases (CDC `2026-15983`, FAA `2026-18052`, Census `2026-16791`) where
a full primary-source review (FR notice, GovInfo edition, Regs document + docket list, extension/
correction search) found an explicit published date, an explicit different portal cutoff, and
**no** document explaining the difference. The reviewer correctly declined to pin (a pin would
publish HIGH on a disputed date) and declined to dismiss (a real disagreement is not noise). Three
such cases against ~52 reviewed items is the base rate to design "rare" around.

Today those three items have no parking state: they stay `conflicting`, keep the rot alert firing,
and any sweep re-investigates them from scratch. That is the second structural fix (PR-A2).

### Finding 3 — the existing verify pass cannot grade a pin

Slice V's post-close verdict compares the close snapshotted at close time with the **current
derived** close and the post-close notice flags (`verify/verdict.ts`). For an honored pin the
current close _is_ the pin, so a wrong pin that no later notice contradicts is graded
`was_correct=true`. Worse, the confirmed-check candidates include every post-close observation
without excluding `source='human_review'` (`verify/run.ts` ~199), so a verdict written after
close can itself count as the "successful source check". The verify pass is post-close
**contradiction monitoring**, not independent grading. PR-A4 fixes the second point and the plan
stops calling the first "ground truth".

## Decisions proposed

- **This is a new authority and gets its own ADR (0015).** Today the only path by which anything
  other than the deterministic rulebook sets a HIGH close is a human_review verdict authorized by
  a person. Letting an agent choose that date unsupervised expands that authority, whatever CLI it
  goes through. ADR 0015 states exactly what an agent may assert, on what evidence, under what
  verification, and how it is attributed — rather than claiming the "LLM never touches deadline
  resolution" principle is untouched. The in-engine invariants (confidence never LLM-scored, no
  numeric scores, the adjudicator advisory-only) are unchanged.
- **Honest provenance, not fake certainty.** Contract 0.11.0 (contract-keeper's call on the exact
  shape): `HumanReviewVerdict.reviewer: "human" | "agent"` — the **decision authority**, optional,
  default `human` — while `operator` names the executor. The 49 legacy codex pins are therefore
  `reviewer=human` (a person authorized each) executed by an agent, and parse unchanged. The
  reconciler stamps `agent_resolved` instead of `human_resolved` when `reviewer=agent`.
- **Escalation is an observation too.** New verdict kind `escalate`: "primary sources examined
  (hashes recorded); the discrepancy cannot be resolved from documents; a human decision or agency
  clarification is needed." It derives **nothing** (window stays `conflicting`, the ConflictRecord
  stays live — suppression is never silence) but it is visible on `review show`/`queue`, the
  autopilot skips items whose latest _honored_ verdict is `escalate`, and new **invalidating**
  evidence (anything the 0010/PR-A1 exceptions do not cover) un-parks it. A human later
  supersedes it with a real verdict. Caveat (reviewer finding 9): reconciliation reads only the
  target `ocd_id`'s observations, so a separately ingested extension notice does not un-park by
  itself — parked items are re-inspected weekly by the autopilot (a `show` plus an extension
  search), which is cheap. _Alternative the contract-keeper may prefer:_ a CLI-managed operational
  ledger keyed by ocd_id + reviewed hashes, no contract change; this plan prefers the observation
  because it rides the audit chain and the supersedence rule for free.
- **A written write-policy replaces per-item authorization**, with **escalation taking
  precedence** over every other kind (below).
- **Writes are bound to assessed evidence.** `review resolve` gains `--expect <hash>…`: the
  latest-per-source payload hashes the investigation (and the verifier) actually assessed. The
  write refuses, in one transaction with the hash read, if the live set differs (closing the
  "known narrow gap" in `review/core.ts`). Automation never writes without it.
- **Humans are paged through the existing alert path.** A new
  `docketclock_review_queue_depth{reason="escalated"}` gauge and one provisioned Grafana rule
  (`escalated > 0`, `cadence=daily`) → ntfy. Tooling failures are published by the run itself to
  the same ntfy topic (the URL is already cached host-side at `~/.config/yokel/ntfy-url` for the
  drill scripts). The existing rot alert is **unchanged** and will keep nagging daily while parked
  items age — that is the intended standing reminder that a human owes a decision, not a bug.
- **Measure before trusting, blind.** The autopilot runs in **shadow mode** (writes nothing)
  until it meets the gate in "Reliability" below, with prior verdicts hidden from it.

## The write policy (v1)

The autopilot may write, per run, at most **10** verdicts and only these, evaluated in this order:

| kind                | allowed when                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | never when                                                                                                                                         |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `escalate`          | **first**: a full search (FR notice, GovInfo edition, Regs document and docket list, extension/correction/reopening search by document number, docket, RIN, title) leaves any material discrepancy unexplained; the verifier disagrees with the primary; the deadline the evidence establishes carries a time that is not 11:59 p.m. ET (the pin convention cannot represent it); or the correct verdict is one this policy forbids. The note must say what was searched.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | as a way to clear an alert or skip work                                                                                                            |
| `pin_close`         | **only if escalation does not apply**: a primary document (FR notice/extension/correction, GovInfo edition, or the Regs document's own published text) **explicitly states** the operative comment deadline for **this exact notice** (identity checked by document number, by an FR citation verified against the FR API record, or by docket id together with title and publication date — a RIN alone is insufficient, siblings share them; never by cluster membership). Since v1.1 (2026-10-20) a primary document also includes an agency-authored document in the notice's own Regulations.gov docket that explicitly extends the period, with the note saying so; since v1.2 (2026-10-28) such a docket document may also be tied to the notice by docket id plus FR publication date when the docket document itself states that date as the FR publication date and that docket holds exactly one FR document of any type published that day, being this notice (checked against the docket's document list, an FR docket-id search and an FR same-day search by agency; if any is unavailable or shows a second same-day FR document, the date does not identify the notice; the note says how it was checked), the evidence **explains** the competing value (e.g. the other date is a petition/reply/meeting date, or an extension notice moved it), the note cites URL + verbatim DATES text, and the independent verifier returns the same date from the evidence card | the only support is portal metadata (`commentEndDate`, `openForComment`), a search snippet, a sibling notice's result, or inference from a pattern |
| `confirm_withdrawn` | live Regulations.gov shows **this** document withdrawn (identity checked; the #112 identity-split class), cited in the note                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | —                                                                                                                                                  |
| `confirm_reopened`  | **not permitted** in v1                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | —                                                                                                                                                  |
| `dismiss_conflict`  | **not permitted** in v1 (dismissal can conceal a real disagreement and never establishes a close)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | —                                                                                                                                                  |

Order of work: open windows closing soonest first, then closed windows oldest-conflict first (the
rot alert is anchored on the oldest live conflict). Before every write: refresh `show` and pass
`--expect` with the assessed hashes; after every write: confirm the provenance flag, confidence and
queue membership, and record the verification in the run report.

## Scheduling and trigger

- **Trigger: T3 Code scheduler, `fixed_time` 07:00 local, every day**, bound to a dedicated
  "Review autopilot" thread (not an interactive one), provider `claudeAgent`. The run does the
  Monday audit first (where applicable), then reads the queue and exits in one message when it is
  empty. Arrivals run ~2–6/day with bursts;
  closing-soonest items get a day of latency at worst, well inside the 7-day rot threshold. An
  event trigger (poller → webhook → T3) is possible later via `{type:'webhook'}` but needs T3
  Connect; daily is enough to validate the loop.
- **Model: `claude-opus-5-5` at `high`** for the operating agent (ambiguous reasoning, real
  consequences, needs web access to FR/GovInfo/Regs). Escalate to `claude-fable-5-1` if the shadow
  gate fails on reasoning rather than evidence.
- **Independent verifier per `pin_close`: Codex `gpt-6-astra` at `high`**, cross-provider by the
  house rule. It receives the evidence card (URLs + verbatim quoted text + both source values +
  the reviewed hashes) and **not** the proposed date, and returns its own date or "insufficient".
  Codex children have no network, so this checks reasoning against captured evidence, not the
  evidence itself; the weekly audit covers fabrication risk.
- **Weekly audit (Monday run):** a networked Claude child re-reads a random 5 of the week's agent
  verdicts from the live pages and re-inspects every parked item; any disagreement becomes an
  escalation and a report line.
- Cluster access: same as the skill today (`kubectl --context k3d-yokel -n docketclock exec
deploy/docketclock-poller -- pnpm exec tsx src/review/cli.ts …`). The Mini must be awake at run
  time; a failed connection is reported as a tooling failure, never as an empty queue.

## What "truly needs a human" means (the escalation contract)

A run pages a human (ntfy) only for:

1. an `escalate` verdict it just wrote (the #127 class, verifier disagreement, unrepresentable
   deadline time, or a forbidden-but-correct verdict);
2. a tooling failure: cluster unreachable, `resolve` returned an ambiguous error after a write,
   `--expect` mismatch twice on the same item, or budget exhausted with open items closing within
   3 days;
3. a recurring cause worth an engineering fix (reported as a note, not an item — e.g. Finding 1).

Separately, the standing Grafana reminders continue: the rot alert (oldest live conflict > 7d,
daily) and the new escalations-pending alert (daily). Everything else is in the run report and
nobody is paged. The report is one message: time, queue before/after, verdicts written (ocd-id,
kind, date, verifier result, `--expect` hashes), items skipped and why, escalations created, and
the next run time.

## Reliability — the gate and the ongoing measure

- **Shadow gate (before any write).** The evaluation harness feeds ocd-ids directly (honored cases
  are outside the live queue) and runs `show --blind` (prior verdicts hidden) so the agent cannot
  read the answer. Three parts, each reported separately:
  1. _Blinded historical agreement_ on the 42 honored pins: proposed date = pinned date ≥ 95%,
     every disagreement explained. This measures agreement with human-authorized precedent, not
     independent truth; it is a necessary floor, not the gate.
  2. _Held-out independent set_: 10 current queue items the operator reviews **before** seeing
     the agent's proposal (escalate / pin / withdrawn + date). Agreement on kind ≥ 9/10; **any
     false pin** (agent pins where the operator escalated or chose another date) is blocking
     until explained and the policy amended.
  3. _Escalation discipline_: the 3 #127 cases → `escalate` 3/3; the 2 withdrawals →
     `confirm_withdrawn` 2/2; zero proposed `dismiss_conflict`/`confirm_reopened`.
     Three runs over the same corpus measure repeatability, not sample size; the held-out set is the
     only independent sample and should be refreshed each time the policy changes.
- **Ongoing — post-close contradiction monitoring (not grading).** Agent pins derive HIGH and
  enter the Slice V watch like any window; a later extension, correction, withdrawal or
  unexplained close movement convicts them (`late_amendment`). PR-A4 makes this attributable:
  the watch row records the honored verdict's observation_id **at snapshot time** (so a later
  supersession cannot re-attribute or hide an invalidated mistake), and the rollup reports
  eligible / pending / lapsed / ungraded counts per `reviewer`, not just a ratio. Note the
  existing accuracy-degraded alert fires only on the **aggregate** HIGH ratio < 95% with sample
  ≥ 20; PR-A4 adds a **per-agent-miss** rule (any `was_correct=false` attributed to an agent
  verdict → ntfy) and the monthly xcheck (#114) remains the offline check.
- **Kill switch:** pause = `update_scheduled_task enabled=false`; a bad verdict is corrected by a
  superseding human verdict, never an edit.

## PRs

### PR-A1 — `reconcile-v2.2`: the portal recording its own announced close is not new evidence (ships first)

Status 2026-10-17: implemented on branch `t3/automate-federal-review` (ADR 0014, fixture-backed live
replay); deploy + sweep pending merge.

Extend ADR 0010's exception, narrowly, for the **measured transition class only**. A newer Regs
observation still counts as the reviewed evidence when **all** of:

1. the latest verdict is `pin_close` and is otherwise honored under v2.1 (baseline present and in
   `reviewed_payload_hashes`);
2. the reviewed Regs baseline's `commentEndDate`, in Eastern time, **equals** `pinned_close_date`
   — the transition is predicted by the portal's own date, so fetch timing is not asked to prove
   anything about when the portal actually closed (reviewer finding 3);
3. beyond the 0010 metadata fields, the only differences from the baseline are
   `data.attributes.openForComment` and/or `withinCommentPeriod` going `true → false`;
4. the flip is observed at `fetched_at` **strictly after** the pinned close instant (11:59:59 p.m.
   ET of `pinned_close_date`); equality fails;
5. **monotonic over the whole post-verdict history**: once a flag has been observed `false`, any
   later observation showing it `true` (or any other change) invalidates — a flip-then-revert must
   never leave a pin honored while the portal is open again, because an honored pin overrides the
   status rule that would otherwise keep the window open (reviewer finding 2).

Everything else in v2.1 stands: full-envelope comparison, every intervening observation checked,
newer FR/GovInfo invalidates, non-pin kinds get no exception, a date change plus flip invalidates,
equal-to-verdict timestamps keep the v2 tie policy. All 7 live cases satisfy 1–5. ADR 0014;
adversary tests for each clause's negative (flip before the pinned instant; flip at equality; pin
≠ portal date; flip + date change; non-pin kind; flip then revert; reversal before the flip) and
the 7-case live replay (all stay honored). Then the `rederive-stale-windows.ts` sweep. Expected
effect: queue 42 → 35 with no verdicts written, and the echo closed for pins that equal the
portal's own date (pins that differ from it keep invalidating — correctly, since the portal then
closed on a date the pin did not assert).

**Verify:** `pnpm -r test && pnpm -r typecheck`; replay the seven histories read-only; after
deploy + sweep, `review queue` shows the 7 gone and `review show` shows `human_resolved` at HIGH.

### PR-A2 — ADR 0015 + contract 0.11.0 + reconciler + CLI: `escalate`, `reviewer`, `agent_resolved`, `--expect`

Status 2026-10-19: merged (#133) and deployed the same evening; the v2.3 sweep re-stamped 7,896
windows with 0 derivation changes, as predicted; the live round-trip escalated CDC `2026-15983`
(reviewer human, `--expect` both hashes) — parked, queue 35 with 1 parked, gauge `escalated=1`,
rule `review-queue-escalated` fired through ntfy after exactly the 1h hold. One deliberate reading
recorded in the ADR: the 0014 echo exception is not extended to `escalate`, so the portal's own
close flip un-parks an open escalated item once. The other two #127 items are not escalated yet.

ADR 0015 (agent authority) first. Contract-keeper: `HumanReviewVerdictKind += escalate` (date
forbidden — the existing pin⇔date refinement already covers it; note + hashes required),
`HumanReviewVerdict.reviewer` optional enum defaulting to `human`, `ConflictFlag += agent_resolved`.
No migration (raw is JSONB; the 0011 CHECK is unaffected). Reconciler: `escalate` is honored for
freshness purposes but must **bypass** the overlay's unconditional `human_resolved` stamp and
observation-id push (the two lines before the kind switch) so machine derivation is byte-for-byte
unchanged; provenance flag chosen by `reviewer`. CLI: `--kind escalate`, `--reviewer agent`,
`--expect <hash>…` (refuse on mismatch, same transaction as the hash read); `show` gains
`--blind`; `queue` prints `[escalated by <operator> <date>]`; the CLI's "verdict NOT honored"
check keys on honored-ness rather than on the `human_resolved` flag alone. `reviewQueueStats.byReason`
gains `escalated` (counted separately, so the rot alert's meaning is unchanged). One new provisioned
Grafana rule on the new gauge, `cadence=daily`, receiver ntfy.

**Verify:** contract probes (escalate with a date must not parse; reviewer defaults to human on
every existing row, including the 49 codex pins); engine tests (escalate preserves machine
derivation byte-for-byte; invalidating evidence un-parks; 0010/PR-A1-class refreshes do not);
`--expect` mismatch refuses and writes nothing; CLI round-trip on the live cluster for one #127
item; the gauge visible in Prometheus and the alert fires/resolves through the drilled path.

### PR-A3 — the autopilot skill, the scheduled task, shadow mode

Status 2026-10-20: implemented on branch `t3/review-autopilot-shadow`: the skill (policy, run
procedure, evidence card, verifier hand-off, note and report formats, weekly audit, mode switch,
harness), the scheduled task's prompt kept verbatim in the skill directory, the runbook's
"Autopilot" section with the gate record table, and two read-only CLI additions this slice needs:
`review log` (the verdict ledger with each verdict's standing: honored / parked / superseded /
invalidated / unparseable — how an operator reads the agent's work) and `review corpus` (the
shadow-gate corpus computed live from honored verdicts, so the harness never goes stale). The CLI
additions mean the poller image is redeployed through the app's usual path; no cluster or chart
change. The scheduled task is created after merge, from a dedicated "Review autopilot" thread.
Cross-provider review round 1 (Codex GPT-6 Astra, high, 2026-10-20): 10 findings, all folded in —
the harness is now blind by construction (`corpus --blind` ids-only for fresh proposer children; the
scorer reads expectations only after proposals are sealed); part 3 names a required set (the three
#127 cases and the two withdrawals; an empty live category never passes by vacancy); the Monday
audit runs before the empty-queue exit and is done by a fresh networked Claude child that sees only
ids; `log` reports truncation and the audit must never sample a truncated list; shadow `escalate`
proposals are re-investigated weekly and skip-reuse is scoped by policy version; the runtime
examples are full commands (zsh does not word-split `$R`); the scheduled prompt pages a failed
checkout update inline and continues; `--since`/`--limit` are bounded argument-side; an unparseable
corpus row carries no invented kind or authority; plus a spawned CLI argument-validation test.
Shadow smoke run (Claude Opus 5.5, high, 2026-10-20, three items, outcomes withheld, no writes,
no pages): one `pin_close` agreeing with the human precedent via an FR extension found only by
full-text search, two `escalate`; 18 skill findings folded in (full commands; a fictitious ledger
example; identity rule widened to verified citations and docket+title+date, RIN alone
insufficient; "material", "primary document", time-of-day and extension-vs-reopening defined;
search mechanics and keyless source access prescribed, Regulations.gov via the Playwright browser,
`.playwright-mcp/` gitignored; `show` prints an identity line and labels each close field; the
ledger gains `note`, `section` and a defined `verifier` for non-pins; child dispatch via
`orchestrator_capabilities` with a timeout rule; a hash refresh before every ledger line; a report
variant for harness runs). **Policy v1.1 (operator-ratified 2026-10-20):** an agency-authored
document posted in the notice's own Regulations.gov docket that explicitly extends the comment
period (an "FDMS posting memo — no FR request") is a primary document; a pin on it must say the
extension is not published in the FR and cite the docket document. The smoke run had escalated the
EPA construction-general-permit extension to 2026-09-17 — which a person pinned in September —
under the stricter v1 reading; the precedent and the policy now agree.

`.agents/skills/docketclock-review-autopilot/SKILL.md` (the existing guided skill stays for
interactive use and is referenced, not duplicated): the write policy above, the run procedure,
the evidence-card format, the verifier hand-off, the report format, the parked-item weekly
re-inspection, and the `AUTOPILOT_MODE=shadow|write` switch read from the prompt. The shadow
harness (ocd-id list + `show --blind`) and the held-out protocol are documented. The T3 scheduled
task is created with the shadow prompt. `docs/runbooks/review-queue.md` gains an "Autopilot"
section (how to pause, how to read a report, how to supersede an agent verdict). No cluster or
chart changes.

**Verify:** shadow gate parts 1–3 met and recorded in the runbook; only then flip the prompt to
`write`. The gate record lives in the runbook ("Shadow gate — what must be true before write
mode"); the held-out set is sealed host-side before any proposal is read.

### PR-A4 — attributable post-close monitoring

Verify pass: exclude `source='human_review'` from the confirmed-check candidates; record the
honored verdict's observation_id on the watch row at snapshot time. SQL rollup + Grafana panel for
agent-attributed windows (eligible / pending / lapsed / graded-correct / graded-miss, trailing
90d); a per-agent-miss alert rule; a `reviewer` split in the monthly xcheck report (#114).

**Verify:** a seeded agent pin followed by a seeded extension observation yields a miss attributed
to that verdict and fires the new rule in the drill folder; `validate-argocd-apps.py` green.

## Related

- `plans/review-learning-loop.md` — how closed items become fixtures, route rules and ratified
  resolve rules so classes leave the queue permanently, and where a cheap typed-judgment model
  (TypeSafe Jev or the already-keyed Gemini categorical seam) may and may not sit.

## Out of scope (deliberate)

- **Agency outreach** (#127's own design) — the autopilot only _parks_ those cases.
- **Petition windows** (#124) and the **#112 identity-split fix** — the autopilot handles their
  symptoms under the policy (pin the comment date; confirm withdrawals) and reports the counts.
- **An in-cluster agent** (CronJob + API-billed model): rejected for now — it would need an API
  route the house rules forbid, and an agent that is visibly an operator with a phone-pageable
  owner is the honest shape for this authority.
- **`dismiss_conflict` / `confirm_reopened` by the agent** — revisit after 90 days of
  attributable monitoring data.

## Rollback

- PR-A1: redeploy the `reconcile-v2.1` rule (code and version stamp, not the stamp alone) **and**
  run the projection sweep; the 7 echoes return to the queue, nothing else changes.
- PR-A2: additive contract; `escalate` rows become inert log data under an older reconciler.
  **Order matters:** pause the autopilot _before_ reverting agent-aware reconciler code, because
  a pre-0.11.0 reconciler would parse an agent pin and stamp it `human_resolved`. If agent pins
  already exist, keep the provenance-aware reconciler (or supersede those pins by hand) rather
  than reverting it.
- PR-A3: `update_scheduled_task enabled=false` (instant) or delete the task; verdicts already
  written remain, each supersedable by a human verdict.
- PR-A4: revert the panel/rollup/rule; the watch-row column is additive and harmless.

## Review log

- **Round 1 (2026-10-16, Codex GPT-6 Astra, high):** 10 findings, 6 P1 — all accepted and folded
  in: escalation precedence and identity checks in the policy; PR-A1 tightened (portal date must
  equal the pin, monotonic history, equality fails, no fetch-time claim about transition timing);
  `--expect` evidence binding; Slice V re-described as contradiction monitoring with the
  `human_review` leak fixed and snapshot-time attribution; blinded + held-out gate with 42/2/3
  split; ADR 0015 for the authority and `reviewer` as decision authority; alerting and rollback
  claims corrected. Reviewer's overall verdict on the original text: the plan's substance (its
  evidence gates, freshness rule and verification attribution) was not yet strong enough to let
  the agent write verdicts unsupervised. This was a judgment about the design, not about tooling
  or permissions. Round 2 pending the direction decision.
- **2026-10-20 (operator):** policy v1.1 ratified — docket-only agency extension documents are
  primary evidence for a pin, with a note requirement. Policy version string `v1.1@2026-10-20`.
- **2026-10-28 (operator):** policy v1.2 ratified — for an agency-authored docket document, the
  docket id plus the notice's FR publication date also identifies the notice, but only when that
  docket contains exactly one FR notice published on that date. The reviewer establishes this from
  the docket's document list plus an FR search on the docket id returning no other FR document
  published that day, and the pin's note says how it was checked (the v1.1 note requirements still
  apply). The general identity definition is unchanged. Policy version string `v1.2@2026-10-28`;
  per the gate's held-out rule, the part 2 set is to be refreshed for v1.2. Cross-provider review
  (Codex GPT-6 Astra high, Claude Fable 5.1 high) folded in clarifications: the single same-day
  FR document may be of any type and must be this notice, dated by FR `publication_date` (never
  the Regulations.gov posted date); rule 2's identity clause names the v1.2 route; the note gains
  a fixed `Identity (v1.2)` line. Three operator-approved tightenings from the same review: the
  docket document must itself state the date as the FR publication date; a third check (FR
  documents published that day by the notice's agencies, scanned for the docket id, because FR
  docket fields are often empty); and an `Identity basis` line on the verifier's evidence card,
  which answers INSUFFICIENT when identity is not established.
- **2026-10-20 (PR-A3 reviews):** the pin row's identity clause above was amended to match the
  executed policy (a RIN alone is insufficient — the SBA size-standards pair shares one); the
  harness was made blind by construction (orchestrator / proposer / scorer in separate contexts;
  held-out set excludes the required-set ids); the write-mode flip carries an explicit
  `AUTOPILOT_GATE` token because the agent cannot read the runbook during a run.
- **2026-10-17 (operator):** go-ahead for PR-A1. Two policy recommendations ratified: CMS
  desk-officer rule-resolved windows derive MEDIUM, HIGH only when a human or the agent read the
  notice; multi-stage comment periods use the initial deadline as the operative close in v1, with
  the reply deadline kept visible in the window's notes. TypeSafe Jev dropped from consideration
  (no second API-billed vendor; Gemini's categorical seam remains the only cheap-model seam).
