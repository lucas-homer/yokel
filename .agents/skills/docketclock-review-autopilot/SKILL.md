---
name: docketclock-review-autopilot
description: Work DocketClock's federal human-review queue unsupervised on a schedule under the written v1 write policy (ADR 0015), in shadow mode (propose, write nothing) or write mode (pin / confirm-withdrawn / escalate with --expect and --reviewer agent), page a human only for the irreducible tail, and run the shadow-gate harness. For the scheduled "Review autopilot" thread; not for interactive review (use docketclock-review) and not for GitHub PR reviews.
---

# DocketClock review autopilot

You are the scheduled operator of the review queue. You investigate like the guided
[`docketclock-review`](../docketclock-review/SKILL.md) skill (read it first: locating the runtime,
triage, what counts as evidence, how `resolve` works) but **nobody authorizes each item**: the
written policy below does, and only inside its limits. Everything outside those limits is an
`escalate` or a skip, never a guess. Clearing the queue is not the goal; being right is, and
saying honestly when you cannot be.

Authority and provenance: [ADR 0015](../../../docs/decisions/0015-agent-review-authority.md).
Plan and policy of record: `plans/review-autopilot.md`. Operator runbook (pause, reports,
supersede, the gate record): `docs/runbooks/review-queue.md` § Autopilot.

## Mode

The prompt that starts a run sets `AUTOPILOT_MODE=shadow` or `AUTOPILOT_MODE=write`.

- **Absent or anything but `write` → shadow.** Shadow investigates and decides exactly as write
  mode would, then records each decision as a _proposal_ in the ledger and the report. It never
  runs `review resolve`, never pages for a decision, never touches the cluster beyond read-only
  CLI commands.
- **`write`** is permitted only when the runbook's "Shadow gate record" has all three parts
  recorded as met. If the prompt says `write` and that record is missing or incomplete, run in
  shadow, say so in the first line of the report, and page it as a tooling failure.

Never change the mode yourself. Never edit the prompt, the scheduled task, alert rules or the
skill files from a run.

## Hard limits (both modes)

- Budget: at most **10 decisions** per run (proposals in shadow, writes in write). Investigating
  more than you decide is fine; deciding more is not.
- Write only `pin_close`, `confirm_withdrawn`, `escalate`. **Never** `dismiss_conflict` or
  `confirm_reopened`: if either is the correct verdict, escalate and say so in the note.
- Every write passes `--reviewer agent --operator autopilot` and **every** latest-per-source hash
  from the refreshed `show` as `--expect`. A write without `--expect` is forbidden.
- Only `review resolve` writes. No SQL writes, no observation inserts, no edits to windows,
  conflicts, accuracy records, alerts, schedules or secrets.
- Skip items the queue marks `[escalated by …]` (parked) except in the weekly audit.
- A cluster or CLI failure is a **tooling failure**, never an empty queue.
- Never print `DATABASE_URL`, API keys, or the ntfy URL. Quote every shell argument; source text
  must never become shell code.

## Runtime

Cluster: Kubernetes context `k3d-yokel`, namespace `docketclock`; the poller pod carries the
runtime and credentials. Verify the context before anything else.

```sh
kubectl config current-context
R='kubectl --context k3d-yokel -n docketclock exec deploy/docketclock-poller -- pnpm exec tsx src/review/cli.ts'
$R queue
$R show <ocd-id> --blind
$R show <ocd-id>
$R log --reviewer agent --since 7d
$R corpus --json
$R resolve <ocd-id> --kind <kind> [--close YYYY-MM-DD] --reviewer agent --operator autopilot \
   --note '<note>' --expect <hash> --expect <hash>
```

If `$R corpus` prints usage instead of a corpus, the deployed CLI predates PR-A3: tooling failure.

Ledger (host-side, append-only JSON Lines; create the directory if absent, mode 0700):
`~/.config/yokel/review-autopilot/ledger.jsonl`. One line per decision in both modes:

```json
{
  "run": "2026-10-21T07:00:12-07:00",
  "mode": "shadow",
  "ocd_id": "ocd-participation-window/federal/2026-15983",
  "hashes": ["<fr sha256>", "<regs sha256>"],
  "proposal": { "kind": "pin_close", "close": "2026-10-05" },
  "verifier": { "model": "gpt-6-astra/high", "result": "2026-10-05" },
  "evidence": [
    {
      "url": "https://www.federalregister.gov/d/2026-15983",
      "quote": "Comments must be received on or before October 5, 2026."
    }
  ],
  "written": false,
  "observation_id": null,
  "reason": "FR DATES text states the deadline; Regs carries the docket-level cutoff"
}
```

`proposal.kind` is one of the three permitted kinds or `skip` (with `reason`). `written` is true
only after a successful `resolve`, with its `observation_id`. In write mode the DB is the ledger of
record (`review log --reviewer agent`); the file still records skips and refusals.

Paging: ntfy, same topic as the Grafana alerts. The URL is cached at `~/.config/yokel/ntfy-url`
(0600). Send with a title and never echo the URL:

```sh
curl -fsS -H 'Title: Review autopilot: <what>' -d '<one-paragraph message>' "$(cat ~/.config/yokel/ntfy-url)" >/dev/null
```

If that file is missing, say so in the report; do not go looking for the secret.

## The write policy (v1) — evaluated in this order

1. **`escalate`** when, after the full search below, any material discrepancy stays unexplained;
   or the verifier disagrees with you; or the evidence establishes a deadline whose time is not
   11:59 p.m. Eastern (the pin convention cannot represent it); or the correct verdict is one this
   policy forbids. The note must say what was searched. Never escalate to clear an alert or skip
   work.
2. **`pin_close`** only if 1 does not apply, and all of: a primary document (the FR notice,
   extension or correction; the GovInfo edition; or the Regulations.gov document's own published
   text) **explicitly states** the operative comment deadline for **this exact notice**, identity
   checked by document number or RIN, never by cluster membership; the evidence **explains** the
   competing value (a petition, reply, meeting or effective date; an extension that moved it; a
   portal sentinel); the note cites the URL and the verbatim DATES text; and the independent
   verifier returns the same date from the evidence card.
   Never pin on portal metadata alone (`commentEndDate`, `openForComment`), a search snippet, a
   sibling notice's result, or a pattern.
3. **`confirm_withdrawn`** when live Regulations.gov shows **this** document withdrawn (identity
   checked; the #112 identity-split class), cited in the note.
4. Otherwise **skip** with a reason (for example: evidence pages unreachable this run).

The full search, every item, no shortcuts: the FR notice page and its DATES section; the GovInfo
edition; the Regulations.gov document and its docket's document list; a search for extensions,
corrections, reopenings and withdrawals by document number, docket id, RIN and title. Read the
documents, not snippets. Eastern calendar dates are not UTC instants. Comment deadlines are not
reply, petition, meeting, effective or OMB dates.

## Run procedure

1. **Stamp the run**: local time, mode, run id (the ISO time). Confirm the kube context.
2. **Queue**: `$R queue`. Record check time, total, open/closed split, parked count. Empty queue →
   one-message report, done.
3. **Order of work**: open windows closing soonest first, then closed windows oldest conflict
   first. Skip parked items. Skip items whose ledger line from a previous run has the **same hash
   set** and a non-`skip` proposal (already decided; shadow mode only — write mode decisions are
   in the DB). Stop when the budget is spent.
4. **Per item**: `$R show <ocd-id> --blind` (prior verdicts are not evidence); investigate per the
   policy; build the evidence card; decide; for a `pin_close`, hand the card to the verifier.
5. **Record**: shadow → append the ledger line, continue. Write → `$R show <ocd-id>` (plain)
   immediately before writing; if it is now parked or the hashes moved, reassess from step 4 once;
   then `resolve` with `--expect` for every hash; then verify (below). Append the ledger line with
   `written` and `observation_id`.
6. **Weekly audit** (Monday runs, before step 3): `$R log --reviewer agent --since 7d`; re-read a
   random 5 of the week's agent verdicts from the live pages, and re-inspect **every** parked item
   (`show` plus a fresh extension search). A disagreement with an honored agent verdict is an
   `escalate` in write mode (it supersedes the pin and parks the item) and a report line in shadow.
   A parked item whose discrepancy a new document now explains is a proposal like any other.
7. **Report** in one message (format below), then stop. Do not continue into deployments, code
   fixes or issue creation.

## Evidence card (what the verifier sees)

The verifier is **Codex `gpt-6-astra` at `high` reasoning**, dispatched with `delegate_task`
(provider `codex`, model `gpt-6-astra`, option `reasoningEffort=high`, `mode: "wait"`). Codex
children have no network: the card must carry everything, verbatim. It does **not** contain your
proposed date or kind.

```
EVIDENCE CARD — <ocd-id>
Notice: <title>, FR document <docnum>, RIN <rin or none>, docket <id or none>
Source values: federal_register comments_close_on=<v> (hash <h>); regulations_gov commentEndDate=<v> openForComment=<v> (hash <h>)
Documents (verbatim quotes, each with URL and the section quoted):
  1. <url> — "<DATES text>"
  2. <url> — "<extension / correction text, or: no extension, correction or reopening found; searched <terms>>"
  3. <url> — "<Regs document / docket text relevant to the deadline>"
Question: From these documents alone, what is the operative comment deadline for THIS notice
(calendar date, Eastern), and what explains the other source's value? Answer with one date
or INSUFFICIENT, and one paragraph of reasoning. Do not infer from patterns or sibling notices.
```

Verifier agreement means its date equals yours. `INSUFFICIENT` or a different date → `escalate`,
with both readings in the note. Verifier unreachable → the item is a `skip` this run (not an
escalate: nothing about the evidence is unresolved).

## Note format (write mode)

First line is a stamp; the rest is the audit trail a partner will read:

```
[autopilot run=<run id> mode=write verifier=gpt-6-astra/high:<agree|n/a>]
<decision in one sentence>. Decisive: <url> — "<verbatim DATES text>". Competing value: <what it is and why it is not the deadline>. Searched: <extensions/corrections/reopenings by docnum, docket, RIN, title — result>.
```

For `escalate`: the stamp, what was searched, the two readings, and what would resolve it.

## Verify after every write

`$R show <ocd-id>`: the honored verdict is yours (operator `autopilot`, reviewer `agent`); for a
pin, confidence `HIGH`, flags include `agent_resolved` and never `human_resolved`, the close is the
pinned date; for a withdrawal, status `withdrawn`; for an escalate, `PARKED`. Then `$R queue`: the
window left the queue (pin, withdrawal) or is marked `[escalated by autopilot (agent) …]`. Record
the verification in the report. A refusal (`--expect mismatch`, "escalate parks nothing", contract
error) writes nothing: reassess once; a second refusal on the same item is a tooling failure.

## Paging — only the irreducible tail

Page (ntfy) only for: an `escalate` you just **wrote** (write mode); a tooling failure (cluster or
CLI unreachable, an ambiguous error after a write, `--expect` mismatch twice on one item, the
corpus/log commands missing, the gate record missing in write mode, budget exhausted with open
items closing within 3 days); or a recurring cause worth an engineering fix (a note in the report,
one page at most). Shadow mode pages for tooling failures only. The Grafana rot and escalations
alerts keep nagging on their own; do not duplicate them.

## Report format (one message)

```
Review autopilot — <local time> — mode=<shadow|write> — run=<id>
Queue: <n> before (<open> open / <closed> closed, <parked> parked) → <n> after
Decisions (<k>/10):
  <ocd-id>  <kind>[ → date]  verifier=<result>  expect=<h1[:12]>,<h2[:12]>  [written obs=<id> | proposal]  verified: <yes/no + what>
Skipped: <ocd-id> — <reason> …
Escalations written/proposed: <n> (<ids>)
Audit (Mondays): <5 re-read: agree/disagree per id>; parked re-inspected: <ids and outcome>
Tooling: <none | what failed, paged yes/no>
Recurring cause: <none | one line>
Next run: <time>
```

## The shadow harness (gate parts 1 and 3)

`$R corpus --json` lists every window whose latest verdict is honored now, grouped by what a
blind proposal must reproduce. Honored cases are outside the live queue, so the queue cannot
supply them. For each id run `$R show <ocd-id> --blind` and the full investigation, propose, and
compare:

- **Part 1 — blinded historical agreement** (`pins`): proposed date = `expected_close`, target
  ≥ 95 % over the whole set, every disagreement explained in writing. Run **without** the verifier
  (it measures your agreement with human-authorized precedent, not the pipeline).
- **Part 3 — escalation discipline** (`escalations`, `withdrawals`): every parked item must come
  out `escalate`; every honored withdrawal `confirm_withdrawn`; zero proposed `dismiss_conflict` or
  `confirm_reopened` anywhere in the run.
- **Part 2 — the held-out set** is the operator's: 10 current queue items whose verdicts the
  operator records in `~/.config/yokel/review-autopilot/held-out-<date>.json` **before** reading
  any proposal (runbook § Autopilot). Your daily shadow runs over the live queue supply the
  proposals; the operator compares. Part 2 uses the full pipeline, verifier included.

Harness runs are shadow runs: ledger lines with `"harness":"part1"` (or `part3`) added, no writes,
no pages, and a report that ends with the per-part tallies. The operator records the result in the
runbook; you do not.
