---
name: docketclock-review-autopilot
description: Work DocketClock's federal human-review queue unsupervised on a schedule under the written v1 write policy (ADR 0015), in shadow mode (propose, write nothing) or write mode (pin / confirm-withdrawn / escalate with --expect and --reviewer agent), page a human only for the irreducible tail, and run the shadow-gate harness as a blind proposer or as the scorer. For the scheduled "Review autopilot" thread; not for interactive review (use docketclock-review) and not for GitHub PR reviews.
---

# DocketClock review autopilot

Policy version: **v1 @ 2026-10-20** (stamp every ledger line with it; see Ledger).

You are the scheduled operator of the review queue. **Nobody authorizes each item**: the written
policy below does, and only inside its limits. Everything outside those limits is an `escalate` or
a skip, never a guess. Clearing the queue is not the goal; being right is, and saying honestly
when you cannot be.

From the guided [`docketclock-review`](../docketclock-review/SKILL.md) skill read **only** its
"Triage and investigate" section (what counts as evidence; deadline types; Eastern dates). Its
other guidance does not apply here and is overridden by this file: you write with
`--reviewer agent --operator autopilot` (never `codex`, never `human`); you never query the
database (the CLI is your only view of the data; a direct read would show you verdicts); you
never ask a person for authorization. Do not read the runbook, the plan or the ADRs during a run:
everything you need is here.

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
- Only `review resolve` writes. No SQL, no database connections, no observation inserts, no
  edits to windows, conflicts, accuracy records, alerts, schedules or secrets.
- Scheduled runs skip items the queue marks `[escalated by …]` (parked) except in the weekly
  audit. Harness proposers are given ids and propose on **every** id given; they never see the
  queue.
- Never read `~/.config/yokel/review-autopilot/held-out-*.json` (the operator's sealed answers).
- As a harness **proposer**, never run `corpus` without `--blind`, never run `log` or `queue`,
  never run `show` without `--blind`, and do not consult notes or memory about specific windows:
  each would show you the answer.
- A cluster or CLI failure is a **tooling failure**, never an empty queue.
- Never print `DATABASE_URL`, API keys, or the ntfy URL. Quote every shell argument; source text
  must never become shell code.

## Runtime

Cluster: Kubernetes context `k3d-yokel`, namespace `docketclock`; the poller pod carries the
runtime and credentials. Verify the context before anything else. Spell the full command out in
every invocation: shell variables and functions do not persist between tool calls, and `$R …`
style shortcuts fail under zsh (an unquoted scalar is not word-split).

```sh
kubectl config current-context
kubectl --context k3d-yokel -n docketclock exec deploy/docketclock-poller -- pnpm exec tsx src/review/cli.ts queue
kubectl --context k3d-yokel -n docketclock exec deploy/docketclock-poller -- pnpm exec tsx src/review/cli.ts show <ocd-id> --blind
kubectl --context k3d-yokel -n docketclock exec deploy/docketclock-poller -- pnpm exec tsx src/review/cli.ts show <ocd-id>
kubectl --context k3d-yokel -n docketclock exec deploy/docketclock-poller -- pnpm exec tsx src/review/cli.ts log --reviewer agent --since 7d --limit 200
kubectl --context k3d-yokel -n docketclock exec deploy/docketclock-poller -- pnpm exec tsx src/review/cli.ts corpus --blind
kubectl --context k3d-yokel -n docketclock exec deploy/docketclock-poller -- pnpm exec tsx src/review/cli.ts corpus --json
kubectl --context k3d-yokel -n docketclock exec deploy/docketclock-poller -- pnpm exec tsx src/review/cli.ts resolve <ocd-id> \
  --kind <kind> [--close YYYY-MM-DD] --reviewer agent --operator autopilot \
  --note '<note>' --expect <hash> --expect <hash>
```

Below, `review <args>` abbreviates that full `kubectl … cli.ts <args>` line. If `review corpus
--blind` prints usage instead of ids, the deployed CLI predates PR-A3: tooling failure.

### What `show` gives you, and where the rest comes from

For a federal window the ocd-id suffix **is** the FR document number
(`ocd-participation-window/federal/<fr-document-number>`). `show` prints an `identity` line from
the source payloads — title, FR citation (e.g. `91 FR 54096`), publication date, docket ids,
RINs, the Regulations.gov document id and docket, and the `frDocNum` the portal attaches — and
each source's close under its own field name (`comments_close_on`, `commentEndDate`). It does not
print the DATES text or any document body; read those at the sources.

Access, keyless (verified 2026-10-20):

- **Federal Register**: `https://www.federalregister.gov/api/v1/documents/<docnum>.json` (title,
  citation, `dates`, `docket_ids`, `regulation_id_numbers`, `regulations_dot_gov_info`,
  `publication_date`, `body_html_url`); the HTML at `https://www.federalregister.gov/d/<docnum>`.
  `curl` works.
- **GovInfo**: `https://www.govinfo.gov/content/pkg/FR-YYYY-MM-DD/html/<docnum>.htm`. `curl`
  works.
- **Regulations.gov** is a JavaScript app: `curl` returns nothing useful and
  `downloads.regulations.gov` refuses it. Use the Playwright MCP browser: `browser_navigate` to
  `https://www.regulations.gov/document/<id>` or `/docket/<docket-id>` and `browser_evaluate`
  returning `document.body.innerText`; to read an attachment, navigate the browser to it and read
  the downloaded file. The browser writes `.playwright-mcp/` into the checkout; it is gitignored
  and must stay out of commits.
- Scratch files go under `/tmp/review-autopilot/<run id>/`, nowhere in the checkout.

### The full search (every item, no shortcuts)

1. The FR notice: the `dates` field and the DATES/ADDRESSES sections of the body.
2. The GovInfo edition of the same document.
3. The Regulations.gov document and its docket's **document list** (an extension can be posted
   there as a separate document).
4. Extensions, corrections, reopenings, withdrawals: FR API **full-text** search
   (`conditions[term]=`) for the document number, each docket id, the citation, and a distinctive
   title phrase, since the publication date; also `conditions[docket_id]=` (it misses documents
   whose docket differs: the SBA 2026-19546 extension sat in another docket and was found only by
   full text). Read every hit that names this document.
5. If an FR hit lives in a different Regulations.gov docket, read that docket too.

Read the documents, not snippets. Eastern calendar dates are not UTC instants. Comment deadlines
are not reply, petition, meeting, effective or OMB dates.

### Ledger

Host-side, append-only JSON Lines; create the directory if absent, mode 0700:
`~/.config/yokel/review-autopilot/ledger.jsonl`. One line per decision in both modes (the id
below is fictitious):

```json
{
  "run": "2026-10-21T07:00:12-07:00",
  "mode": "shadow",
  "policy": "v1@2026-10-20",
  "harness": null,
  "ocd_id": "ocd-participation-window/federal/2026-00000",
  "hashes": ["<fr sha256>", "<regs sha256>"],
  "proposal": { "kind": "pin_close", "close": "2026-11-20" },
  "verifier": { "model": "gpt-6-astra/high", "result": "2026-11-20" },
  "evidence": [
    {
      "url": "https://www.federalregister.gov/d/2026-00001",
      "section": "DATES",
      "quote": "The comment period … is extended … Comments must be received on or before November 20, 2026."
    }
  ],
  "note": "[autopilot run=… mode=shadow policy=v1@2026-10-20 verifier=gpt-6-astra/high:agree] <the note as it would be written>",
  "written": false,
  "observation_id": null,
  "reason": "FR extension 2026-00001 names this notice by citation and docket and moves the close; the FR value is the original DATES text"
}
```

`proposal.kind` is one of the three permitted kinds or `skip` (with `reason`). `policy` is the
version at the top of this file. `harness` is `null` for a scheduled run, or the harness run id
for a proposer line. `verifier` is `{"model": null, "result": "n/a"}` for anything but a
`pin_close`, and `"skipped (part 1)"` / `"skipped (smoke)"` when a harness run omits it.
`evidence[].section` names what was quoted (DATES, SUMMARY, docket memo, portal header…).
`note` is the draft note in the format below, in **both** modes, so a shadow proposal is
comparable with what write mode would have written. `written` is true only after a successful
`resolve`, with its `observation_id`. In write mode the DB is the ledger of record
(`review log --reviewer agent`); the file still records skips and refusals.

### Paging

ntfy, same topic as the Grafana alerts. The URL is cached at `~/.config/yokel/ntfy-url` (0600).
Send with a title and never echo the URL:

```sh
curl -fsS -H 'Title: Review autopilot: <what>' -d '<one-paragraph message>' "$(cat ~/.config/yokel/ntfy-url)" >/dev/null
```

If that file is missing, say so in the report; do not go looking for the secret.

## The write policy (v1) — evaluated in this order

Definitions first:

- **Material discrepancy**: the sources disagree on the **calendar date** (Eastern) of the
  operative comment deadline. A portal cutoff one or two days after the published date is
  material. Differences only in time of day, metadata, or open/closed flags are not.
- **Primary document (v1)**: an FR document (the notice itself, or an extension, correction or
  reopening that names it); the GovInfo edition of one of those; or the Regulations.gov document
  that **is** this notice (its own posted text and header). Not, in v1: an agency memo or other
  attachment posted in the docket, an agency web page, a search snippet, a sibling notice, or
  portal metadata alone (`commentEndDate`, `openForComment`). _(v1.1 candidate, operator's
  decision pending: an agency-authored docket document that explicitly extends this notice's
  comment period. Until adopted, that class is an `escalate` with a "Recurring cause" line.)_
- **Identity**: the document must name **this** notice. Sufficient: its FR document number; its
  FR citation **verified** against the `citation` field of the FR API record for this document
  number (citations are start pages, not guaranteed unique); or its docket id together with its
  title and publication date. Not sufficient alone: a RIN (siblings share it — the SBA size-
  standards NPRM and methodology notice carry one RIN between them), a title, or membership in
  a cluster.
- **Time of day**: an unstated time means the 11:59 p.m. Eastern convention applies. Only a
  document that states a different time (for example "5 p.m. Eastern") trips rule 1's time clause.
- **Extension vs reopening**: a document that says it _extends_ the comment period to a new date
  is an extension and pinnable even if published after the original close (SBA 2026-19546,
  effective on filing, published three days later). A document that _reopens_ a period that had
  closed, or sets a new period starting after a gap, is `confirm_reopened` — forbidden in v1 →
  `escalate`.

Rules, in order:

1. **`escalate`** when, after the full search, a material discrepancy stays unexplained **by
   evidence this policy accepts** (an explanation that rests on a non-primary document is still
   an escalate, and the note says what explains it and why it does not count); or the verifier
   disagrees with you; or a document states a deadline time that is not 11:59 p.m. Eastern; or
   the correct verdict is one this policy forbids. The note must say what was searched. Never
   escalate to clear an alert or skip work.
2. **`pin_close`** only if 1 does not apply, and all of: a primary document **explicitly states**
   the operative comment deadline for **this exact notice** (identity as defined); the evidence
   **explains** the competing value (a petition, reply, meeting or effective date; an extension
   that moved it; a portal sentinel); the note cites the URL and the verbatim DATES text; and the
   independent verifier returns the same date from the evidence card.
3. **`confirm_withdrawn`** when live Regulations.gov shows **this** document withdrawn (identity
   checked; the #112 identity-split class), cited in the note.
4. Otherwise **skip**, only for a transient cause (a source unreachable this run, the verifier
   not returning). A skip is retried next run; it is never the answer to a hard question.

## Run procedure

1. **Stamp the run**: local time, mode, run id (the ISO time), policy version. Confirm the kube
   context.
2. **Monday audit first** (Mondays only; see "Weekly audit" below). It runs **before** the queue is
   read, because an empty queue is exactly the state in which honored agent pins have nothing
   left to contradict them.
3. **Queue**: `review queue`. Record check time, total, open/closed split, parked count. The
   `[escalated by …]` marks are operational state you need (which items to skip), not evidence;
   a scheduled run reads them. Empty queue → one-message report (including the audit, on
   Mondays), done.
4. **Order of work**: open windows closing soonest first, then closed windows oldest conflict
   first. Skip parked items. Shadow mode only: skip an item whose ledger line from a previous run
   has the **same hash set**, the **same policy version**, `harness: null`, and a `pin_close` or
   `confirm_withdrawn` proposal (already decided; in write mode those decisions are in the DB). A
   previous `escalate` proposal does **not** skip the item once it is 7 days old: a separately
   ingested extension can explain a discrepancy without touching this window's hashes, so shadow
   escalations are re-investigated weekly, as parked items are in write mode. A `skip` never
   skips. Stop when the budget is spent.
5. **Per item**: `review show <ocd-id> --blind` (prior verdicts are not evidence); the full
   search; build the evidence card; decide; for a `pin_close`, hand the card to the verifier.
6. **Record**: refresh first — shadow → `review show <ocd-id> --blind` again and confirm the
   hashes are the ones you assessed (the ledger's hashes drive the skip rule), then append the
   ledger line. Write → `review show <ocd-id>` (plain) immediately before writing; if it is now
   parked or the hashes moved, reassess from step 5 once; then `resolve` with `--expect` for every
   hash; then verify (below). Append the ledger line with `written` and `observation_id`.
7. **Report** in one message (format below), then stop. Do not continue into deployments, code
   fixes or issue creation. Delete `.playwright-mcp/` from the checkout and your scratch directory.

## Weekly audit (Monday runs, step 2)

The audit is done by a **fresh, networked Claude child**, not by you: you re-reading your own
week would carry your own reasoning and repeat your own evidence error.

1. `review log --reviewer agent --since 7d --limit 200`. If the output says it was truncated,
   raise `--limit` until it is not; never sample from a truncated list. Pick a random 5 of the
   week's `honored` agent verdicts (all of them if fewer). Then `review queue` for every parked
   item (`[escalated by …]`); in shadow mode add every ledger `escalate` proposal of the last 7
   days (shadow never parks anything in the DB, so the ledger is the only place they exist).
2. Dispatch the auditor (see "Dispatching children"): provider `claudeAgent`, model
   `claude-opus-5-5`, effort `high`, role `review`. Give it **only** the ocd-ids and this
   skill's "What `show` gives you", "The full search" and "The write policy (v1)" sections; not
   the verdicts, not the dates, not the ledger. It runs `review show <ocd-id> --blind` and the
   full search on each and returns, per id, its own verdict (`pin_close` + date,
   `confirm_withdrawn`, `escalate`, or `insufficient`) with the decisive URL and verbatim text.
   It writes nothing and pages nobody.
3. Compare. For a sampled agent verdict, agreement means the same kind and (for a pin) the same
   date. A disagreement is an `escalate` in write mode (written through the normal guarded path,
   with both readings in the note; it supersedes the pin and parks the item) and a report line in
   shadow. For a parked item or a shadow escalation, an auditor `pin_close`/`confirm_withdrawn`
   that meets the policy's bar is a proposal like any other (budgeted); otherwise it stays parked.
4. Report every id with both readings in the Audit line.

## Dispatching children (verifier, auditor, harness proposers)

Call `orchestrator_capabilities` once per run and take the provider instance ids, model ids and
option ids from it; then `delegate_task` with `target: { providerInstanceId, model, options }`,
`mode: "wait"`, `timeoutMs: 900000`. A result with `waitTimedOut: true`, a failed status, or an
answer that does not follow the asked format counts as **unreachable** (not as evidence of
anything): verifier unreachable → the item is a `skip` this run; auditor or proposer unreachable
→ a tooling failure in the report. Never retry a child more than once per run.

## Evidence card (what the verifier sees)

The verifier is **Codex `gpt-6-astra`** with `reasoningEffort: high`, cross-provider by house
rule. Codex children have no network: the card must carry everything, verbatim. It does **not**
contain your proposed date or kind.

```
EVIDENCE CARD — <ocd-id>
Notice: <title>, FR document <docnum>, <citation>, published <YYYY-MM-DD>, RIN <rins or none>, docket <ids or none>, Regulations.gov document <id or none>
Source values: federal_register comments_close_on=<v> (hash <h>); regulations_gov commentEndDate=<v> openForComment=<v> (hash <h>)
Documents (verbatim quotes; each with URL, the document's own identifiers, and the section quoted):
  1. <url> — DATES: "<text>"
  2. <url> (<docnum>, <citation>, published <date>) — DATES: "<extension / correction text>"  |  or: no extension, correction or reopening found; searched <terms, since <date>>
  3. <url> — <section>: "<Regulations.gov document / docket text relevant to the deadline>"
Question: From these documents alone, what is the operative comment deadline for THIS notice
(calendar date, Eastern), and what explains the other source's value? Answer with one date
or INSUFFICIENT, and one paragraph of reasoning. Do not infer from patterns or sibling notices.
```

Verifier agreement means its date equals yours. `INSUFFICIENT` or a different date → `escalate`,
with both readings in the note.

## Note format (both modes; written in write mode, recorded in the ledger in shadow)

First line is a stamp; the rest is the audit trail a partner will read:

```
[autopilot run=<run id> mode=<shadow|write> policy=v1@2026-10-20 verifier=gpt-6-astra/high:<agree|n/a>]
<decision in one sentence>. Decisive: <url> — "<verbatim DATES text>". Competing value: <what it is and why it is not the deadline>. Searched: <extensions/corrections/reopenings by docnum, docket, citation, title — result>.
```

For `escalate`: the stamp, what was searched, the two readings, what (if anything) explains the
discrepancy and why it does not count, and what would resolve it.

## Verify after every write

`review show <ocd-id>`: the honored verdict is yours (operator `autopilot`, reviewer `agent`);
for a pin, confidence `HIGH`, flags include `agent_resolved` and never `human_resolved`, the close
is the pinned date; for a withdrawal, status `withdrawn`; for an escalate, `PARKED`. Then
`review queue`: the window left the queue (pin, withdrawal) or is marked
`[escalated by autopilot (agent) …]`. Record the verification in the report. A refusal
(`--expect mismatch`, "escalate parks nothing", contract error) writes nothing: reassess once; a
second refusal on the same item is a tooling failure.

## Paging — only the irreducible tail

Page (ntfy) only for: an `escalate` you just **wrote** (write mode); a tooling failure (cluster or
CLI unreachable, the checkout could not be updated, an ambiguous error after a write, `--expect`
mismatch twice on one item, the corpus/log commands missing, the gate record missing in write mode,
the auditor or a proposer child failing to return, budget exhausted with open items closing within
3 days); or a recurring cause worth an engineering or policy fix (a note in the report, one page at
most). Shadow mode pages for tooling failures only. The Grafana rot and escalations alerts keep
nagging on their own; do not duplicate them.

## Report format (one message)

Scheduled run:

```
Review autopilot — <local time> — mode=<shadow|write> — run=<id> — policy=v1@2026-10-20
Queue: <n> before (<open> open / <closed> closed, <parked> parked) → <n> after
Decisions (<k>/10):
  <ocd-id>  <kind>[ → date]  verifier=<result>  expect=<h1[:12]>,<h2[:12]>  [written obs=<id> | proposal]  verified: <yes/no + what | n/a (shadow)>
Skipped: <ocd-id> — <reason> …
Escalations written/proposed: <n> (<ids>)
Audit (Mondays): sampled <ids: agree/disagree with both readings>; parked + shadow escalations re-inspected: <ids and outcome>; auditor=<model>
Tooling: <none | what failed, paged yes/no>
Recurring cause: <none | one line>
Next run: <time>
```

Harness or ad-hoc run (a proposer, the scorer, or an operator-supplied list): replace the
`Queue` line with `Items: <n> supplied (<source: corpus --blind | operator>)`, drop `Next run`, and
for the scorer end with the per-part tallies (`Part 1: <agree>/<total> …`; `Part 3: …`; every
disagreement listed with the proposer's reason).

## The shadow harness (gate parts 1 and 3)

The harness is run on the operator's request, not by the daily schedule, and it has **two roles
that must never be the same context**: a _proposer_ that sees only ids, and a _scorer_ that reads
the expectations after the proposals are sealed. A proposer that has seen `corpus --json`
(`expected_close`, the `pins` / `escalations` grouping) cannot be un-told by `show --blind`.

**As the scheduled thread (scorer):**

1. `review corpus --blind` → a flat, sha256-ordered list of ids, nothing else. Add the ids of the
   runbook's required part 3 set that are not already listed (they may be ordinary queue members).
   Shuffle the combined list and split it into batches of at most 10.
2. For each batch dispatch a **fresh proposer** (see "Dispatching children"): provider
   `claudeAgent`, model `claude-opus-5-5`, effort `high`, role `general`. Its task text contains:
   this skill's "Hard limits", "Runtime" (all subsections), "The write policy (v1)" and "Note
   format" sections; the harness run id; the batch's ids; and the instruction to run `review show
<id> --blind` plus the full search on each, decide per the policy, and append one ledger line
   per id with `"harness": "<run id>"`, `"mode": "shadow"`, `"written": false`. Part 1 proposers
   run **without** the verifier (`verifier.result = "skipped (part 1)"`): part 1 measures
   agreement with human-authorized precedent, not the pipeline. The proposer never runs `corpus`
   without `--blind`, `log`, `queue` or plain `show`; never reads the runbook, the plan, ADRs,
   the held-out files or notes about specific windows; proposes on every id given; and never
   writes.
3. Only after every proposer has returned: `review corpus --json`, and the runbook's **required
   part 3 set**. Score from the ledger lines of this harness run id:
   - **Part 1** — for each id in `pins`: agree iff `proposal.kind == "pin_close"` and
     `proposal.close == expected_close`. Tally agree / disagree / skipped over the whole `pins`
     list; the target is ≥ 95 % agree, every disagreement listed with the proposer's reason.
   - **Part 3** — for each id in `escalations` **and** each id of the runbook's required set that
     is not an honored pin: agree iff `proposal.kind == "escalate"`; for each id in `withdrawals`:
     agree iff `proposal.kind == "confirm_withdrawn"`. Any `dismiss_conflict` or
     `confirm_reopened` anywhere in the run fails part 3. An **empty** `escalations` or
     `withdrawals` category does not pass by vacancy: the required set must be covered, and a
     missing proposal counts as a disagreement.
4. Report the tallies per part with every disagreement; the operator records the result in the
   runbook. You do not edit the runbook.

**Part 2 — the held-out set** is the operator's: 10 current queue items whose verdicts the
operator seals in `~/.config/yokel/review-autopilot/held-out-<date>.json` **before** reading any
proposal (runbook § Autopilot). Your daily shadow runs over the live queue supply the proposals;
the operator compares. Part 2 uses the full pipeline, verifier included. You never read those files.
