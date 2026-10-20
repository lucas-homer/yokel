---
name: docketclock-review-autopilot
description: Work DocketClock's federal human-review queue unsupervised on a schedule under the written v1 write policy (ADR 0015), in shadow mode (propose, write nothing) or write mode (pin / confirm-withdrawn / escalate with --expect and --reviewer agent), page a human only for the irreducible tail, and run the shadow-gate harness with blind proposer and scorer children. For the scheduled "Review autopilot" thread; not for interactive review (use docketclock-review) and not for GitHub PR reviews.
---

# DocketClock review autopilot

Policy version: `v1.1@2026-10-20` (the exact string every ledger line and note stamp carries).
Schedule: daily at 07:00 local (the "Next run" line of the report).

You are the scheduled operator of the review queue. **Nobody authorizes each item**: the written
policy below does, and only inside its limits. Everything outside those limits is an `escalate` or
a skip, never a guess. Clearing the queue is not the goal; being right is, and saying honestly
when you cannot be.

This file is self-contained. Do not read the guided `docketclock-review` skill (it carries worked
examples of real windows), the runbook, the plan or the ADRs during a run. You write with
`--reviewer agent --operator autopilot`; you never query the database (the CLI is your only view
of the data; a direct read would show you verdicts); you never ask a person for authorization.

Authority and provenance: ADR 0015 (`docs/decisions/0015-agent-review-authority.md`). Policy of
record: `plans/review-autopilot.md`. Operator runbook (pause, reports, supersede, the gate record):
`docs/runbooks/review-queue.md` § Autopilot. Those are for the operator; you have what you need here.

## Mode

The prompt that starts a run sets `AUTOPILOT_MODE=shadow` or `AUTOPILOT_MODE=write`, and for
write mode also `AUTOPILOT_GATE=met:<YYYY-MM-DD>` — the operator's attestation that the runbook's
shadow gate (parts 1–3) is recorded as met on that date.

- **Absent or anything but `write` → shadow.** Shadow investigates and decides exactly as write
  mode would, then records each decision as a _proposal_ in the ledger and the report. It never
  runs `review resolve`, never pages for a decision, never touches the cluster beyond read-only
  CLI commands.
- **`write`** requires the `AUTOPILOT_GATE=met:<date>` token in the same prompt. If the prompt
  says `write` without it, run in shadow, say so in the first line of the report, and page it as
  a tooling failure. You cannot verify the gate yourself; the token is the operator's word.

Never change the mode yourself. Never edit the prompt, the scheduled task, alert rules or the
skill files from a run.

## Hard limits (both modes)

- Budget: at most **10 decisions** per run — proposals in shadow, writes in write, including
  escalates written by the Monday audit. Skips and investigations do not count. Investigating
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
- Blind roles (harness proposers, the auditor, the scorer's proposers): never run `corpus`
  without `--blind`, never run `log` or `queue`, never run `show` without `--blind`, never read
  `ledger.jsonl` or any `harness-*` file, never read the runbook, the plan, ADRs or the guided
  skill, and do not consult notes or memory about specific windows. They write nothing to the
  cluster and page nobody.
- A cluster or CLI failure is a **tooling failure**, never an empty queue.
- Never print `DATABASE_URL`, API keys, or the ntfy URL. Quote every shell argument; source text
  must never become shell code (notes go through a file, see "Note format").

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
  --note "$(cat /tmp/review-autopilot/<run id>/note-<fr-docnum>.txt)" --expect <hash> --expect <hash>
```

Below, `review <args>` abbreviates that full `kubectl … cli.ts <args>` line. If `review corpus
--blind` prints usage instead of ids, the deployed CLI predates PR-A3: tooling failure.

### What `show` gives you, and where the rest comes from

For a federal window the ocd-id suffix **is** the FR document number
(`ocd-participation-window/federal/<fr-document-number>`). `show` prints an `identity` line from
the source payloads — title, FR citation (e.g. `91 FR 12345`), publication date, docket ids,
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
  returning `document.body.innerText`; to read an attachment, navigate the browser to its
  download link — the file lands under `.playwright-mcp/` in the checkout — and open it with the
  file-reading tool, which renders PDFs. `.playwright-mcp/` is gitignored; delete it at the end
  of the run.
- Scratch files (notes, evidence cards) go under `/tmp/review-autopilot/<run id>/`, nowhere in the
  checkout. Delete the directory at the end of the run.
- If a source is unreachable this run, the item is a `skip` with that reason; if **every** source
  or the cluster is unreachable, that is a tooling failure.

### The full search (every item, no shortcuts)

1. The FR notice: the `dates` field and the DATES/ADDRESSES sections of the body.
2. The GovInfo edition of the same document.
3. The Regulations.gov document and its docket's **document list** (an extension can be posted
   there as a separate document).
4. Extensions, corrections, reopenings, withdrawals: FR API **full-text** search
   (`conditions[term]=`) for the document number, each docket id, the citation, and a distinctive
   title phrase, since the publication date; also `conditions[docket_id]=`. The docket filter is
   known to miss extensions filed under a different docket; full text finds them. Read every hit
   that names this document.
5. If an FR hit lives in a different Regulations.gov docket, read that docket too.

Read the documents, not snippets. Eastern calendar dates are not UTC instants. Comment deadlines
are not reply, petition, meeting, effective or OMB dates.

### Ledger

Host-side, append-only JSON Lines; create the directory if absent, mode 0700:
`~/.config/yokel/review-autopilot/ledger.jsonl` for scheduled runs. Harness proposers write to
their own file instead, `~/.config/yokel/review-autopilot/harness-<run id>/batch-<n>.jsonl`, and
never read any other. One line per decision (the id below is fictitious):

```json
{
  "run": "2026-10-21T07:00:12-07:00",
  "mode": "shadow",
  "policy": "v1.1@2026-10-20",
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
  "note": "[autopilot run=… mode=shadow policy=v1.1@2026-10-20 verifier=agree] <the note as it would be written>",
  "written": false,
  "observation_id": null,
  "reason": "FR extension 2026-00001 names this notice by citation and docket and moves the close; the FR value is the original DATES text"
}
```

`proposal.kind` is one of the three permitted kinds or `skip` (with `reason`). `policy` is the
version at the top of this file. `harness` is `null` for a scheduled run, or the harness run id
for a proposer line. `verifier` is `{"model": null, "result": "n/a"}` for anything but a
`pin_close`, and `{"model": null, "result": "skipped (part 1)"}` when a part 1 proposer omits
it. `evidence[].section` names what was quoted (DATES, SUMMARY, docket memo, portal header…).
`note` is the draft note in the format below, in **both** modes, so a shadow proposal is
comparable with what write mode would have written. `written` is true only after a successful
`resolve`, with its `observation_id`. In write mode the DB is the ledger of record
(`review log --reviewer agent`); the file still records skips and refusals.

### Paging

ntfy, same topic as the Grafana alerts. The URL is cached at `~/.config/yokel/ntfy-url` (0600).
Send with a title and never echo the URL; put the message in a file so quotes in it are inert:

```sh
curl -fsS -H 'Title: Review autopilot: <what>' --data-binary @/tmp/review-autopilot/<run id>/page.txt "$(cat ~/.config/yokel/ntfy-url)" >/dev/null
```

If that file is missing, say so in the report; do not go looking for the secret. Blind roles
never page. A failure the scheduled prompt already paged (the checkout update, when its curl
succeeded) is reported under Tooling, not paged again; if the prompt's page failed, page it here.

## The write policy (v1) — evaluated in this order

Definitions first:

- **Material discrepancy**: the sources disagree on the **calendar date** (Eastern) of the
  operative comment deadline. A portal cutoff one or two days after the published date is
  material. Differences only in time of day, metadata, or open/closed flags are not.
- **Primary document (v1)**: an FR document (the notice itself, or an extension, correction or
  reopening that names it); the GovInfo edition of one of those; or the Regulations.gov document
  that **is** this notice — its posted content (abstract, attached notice text), not the
  portal's rendered header (the "Comments Due" line is `commentEndDate`, which is metadata).
  Also primary (v1.1, operator-ratified 2026-10-20): an **agency-authored document posted in
  this notice's own Regulations.gov docket** that explicitly extends or otherwise sets the
  comment period for this notice (an agency memo, a "posting memo — no FR request", a notice of
  extension), identified by the docket id plus the notice's title or document number. A pin on
  it must say in the note that the extension is not published in the Federal Register and cite
  the docket document's URL. Not primary: an agency web page, a search snippet, a sibling notice,
  a third party's docket comment, or portal metadata alone (`commentEndDate`,
  `openForComment`).
- **Identity**: the document must name **this** notice. Sufficient: its FR document number; its
  FR citation **verified** against the `citation` field of the FR API record for this document
  number (citations are start pages, not guaranteed unique); or its docket id together with its
  title and publication date. Not sufficient alone: a RIN (sibling notices can share one), a
  title, or membership in a cluster.
- **Portal sentinel**: a Regulations.gov `commentEndDate` that is a placeholder, not a deadline —
  a far-future date (year 9999), a date before the document was posted, or the posting date
  itself on a notice whose text sets a later deadline.
- **Time of day**: an unstated time means the 11:59 p.m. Eastern convention applies. Only a
  document that states a different time (for example "5 p.m. Eastern") trips rule 1's time clause.
- **Extension vs reopening**: a document that _extends_ the comment period to a new date, and is
  effective before the original period lapsed, is an extension and pinnable even if its FR
  publication date is after the original close. A document that reopens a period that had already
  lapsed, or sets a new period starting after a gap, is `confirm_reopened` — forbidden in v1 →
  `escalate`.

Rules, in order:

1. **`escalate`** when, after the full search, a material discrepancy stays unexplained **by
   evidence this policy accepts** (an explanation that rests on a non-primary document is still
   an escalate, and the note says what explains it and why it does not count); or the verifier
   disagrees with you; or a document states a deadline time that is not 11:59 p.m. Eastern; or
   the correct verdict is one this policy forbids. A live withdrawal of this document (rule 3)
   explains any date discrepancy, so check rule 3 before escalating on one. The note must say
   what was searched. Never escalate to clear an alert or skip work.
2. **`pin_close`** only if 1 does not apply, and all of: a primary document **explicitly states**
   the operative comment deadline for **this exact notice** (identity as defined); the evidence
   **explains** the competing value (a petition, reply, meeting or effective date; an extension
   that moved it; a portal sentinel); the note cites the URL and the verbatim DATES text; and the
   independent verifier returns the same date from the evidence card.
3. **`confirm_withdrawn`** when live Regulations.gov shows **this** document withdrawn — the
   document whose `frDocNum` is this notice's document number, or the FR notice itself withdrawn
   by a later FR document that names it — cited in the note. If the portal's document is a
   different notice (an identity split), that is not evidence about this one: escalate.
4. **No material discrepancy** (the sources agree on the date and the window is in the queue for
   another reason, such as `stale` or flag-only differences): `skip` with the reason "no material
   discrepancy — machine state", and report it under Recurring cause; nothing in v1 lets you
   assert anything about it.
5. Otherwise **skip**, only for a transient cause (a source unreachable this run, the verifier
   not returning). A skip is retried next run; it is never the answer to a hard question.

## Run procedure

1. **Stamp the run**: local time, mode, run id (the ISO time), policy version. Confirm the kube
   context. Create `/tmp/review-autopilot/<run id>/`.
2. **Monday audit first** (Mondays only; see "Weekly audit" below). It runs **before** the queue is
   read, because an empty queue is exactly the state in which honored agent pins have nothing
   left to contradict them.
3. **Queue**: `review queue`. Record check time, total, open/closed split, parked count. The
   `[escalated by …]` marks are operational state you need (which items to skip), not evidence;
   a scheduled run reads them. Empty queue → one-message report (including the audit, on
   Mondays), done.
4. **Order of work**: open windows closing soonest first, then closed windows oldest conflict
   first. Skip parked items. Shadow mode only — the ledger skip rule, for a previous line with
   `harness: null`, the **same hash set** and the **same policy version**: a `pin_close` or
   `confirm_withdrawn` proposal skips the item indefinitely (already decided; in write mode those
   decisions are in the DB); an `escalate` proposal skips it for 7 days, then it is re-investigated
   (a separately ingested extension can explain a discrepancy without touching this window's
   hashes, so shadow escalations get the weekly re-inspection parked items get in write mode); a
   `skip` never skips. Stop when the budget is spent.
5. **Per item**: `review show <ocd-id> --blind` (prior verdicts are not evidence); the full
   search; build the evidence card; decide; for a `pin_close`, hand the card to the verifier.
6. **Record**: refresh first — `review show <ocd-id> --blind` again (shadow) or `review show
<ocd-id>` (write). If the hashes moved, or in write mode the item is now parked, reassess from
   step 5 once; a second move is a `skip` with that reason. Shadow → append the ledger line.
   Write → `resolve` with `--expect` for every hash, then verify (below), then append the ledger
   line with `written` and `observation_id`.
7. **Report** in one message (format below), then stop. Do not continue into deployments, code
   fixes or issue creation. Delete `.playwright-mcp/` from the checkout and
   `/tmp/review-autopilot/<run id>/`.

## Weekly audit (Monday runs, step 2)

The audit is done by a **fresh, networked Claude child**, not by you: you re-reading your own
week would carry your own reasoning and repeat your own evidence error.

1. `review log --reviewer agent --since 7d --limit 200`. If the output says it was truncated,
   raise `--limit` until it is not; never sample from a truncated list. Report every
   `invalidated` agent verdict of the week as is (evidence already overrode it; nothing to audit).
   Pick 5 of the week's `honored` agent verdicts (all if fewer) deterministically: order the ids
   by the sha256 of `<run id>:<ocd-id>` and take the first 5 — never "pick some", which favours
   the ones you remember as clean. Then `review queue` for every parked item
   (`[escalated by <operator> (<reviewer>) …]`), noting which were parked by a **human** — the
   mark's reviewer is `human`, whoever executed the write; `autopilot`-parked means reviewer `agent`;
   in shadow mode add every ledger `escalate` proposal of the last 7 days (shadow never parks
   anything in the DB, so the ledger is the only place they exist).
2. Dispatch the auditor (see "Dispatching children"): provider `claudeAgent`, model
   `claude-opus-5-5`, effort `high`, role `review`. Its task text contains, verbatim, this
   skill's "Hard limits", "Runtime" (all subsections) and "The write policy (v1)" sections, and
   **only** the ocd-ids — not the verdicts, not the dates, not the ledger — plus this exemption:
   the auditor is an independent evidence reading, so it does **not** dispatch the verifier (rule
   2's verifier clause is the parent's job before any write) and does not write a ledger. It runs
   `review show <ocd-id> --blind` and the full search on each and returns, per id, exactly one of
   `pin_close` + date, `confirm_withdrawn`, `escalate`, `skip` (rules 4–5, with the reason) or
   `insufficient` (a source unreachable), with the decisive URL and verbatim text. It writes
   nothing and pages nobody.
3. Compare. For a sampled agent verdict, agreement means the same kind and (for a pin) the same
   date; `insufficient` and `skip` are "could not audit", reported, not a disagreement. A disagreement is an
   `escalate` in write mode (written through the normal guarded path, budgeted, with both
   readings in the note; it supersedes the pin and parks the item) and a report line in shadow.
   For a parked item or a shadow escalation: if it was parked by a **human**, only report the
   auditor's reading (a human owes that decision; you do not pre-empt it). If it was parked by
   the autopilot or is a shadow escalation, an auditor `pin_close`/`confirm_withdrawn` is a lead,
   not a verdict: run the item through steps 5–6 yourself (evidence card, verifier, budget) and
   only then decide; otherwise it stays parked.
4. Report every id with both readings in the Audit line.

## Dispatching children (verifier, auditor, harness proposers and scorer)

Call `orchestrator_capabilities` once per run and take the provider instance ids, model ids and
option ids from it; then `delegate_task` with `target: { providerInstanceId, model, options }`,
`mode: "wait"`, `timeoutMs: 3600000`. If the call returns `waitTimedOut: true`, read
`task_status` every 10 minutes for up to 2 more hours; a child that is still not terminal, has
a failed status, or returns an answer not in the asked format counts as **unreachable** (not as
evidence of anything). Verifier unreachable → the item is a `skip` this run; verifier unreachable
for **every** pin candidate of a run → also a tooling failure. Auditor, proposer or scorer
unreachable → a tooling failure in the report. Never retry a child more than once per run.

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

Write the note to `/tmp/review-autopilot/<run id>/note-<fr-docnum>.txt` and pass it with
`--note "$(cat …)"`, so apostrophes and quotes in verbatim text are inert. First line is a stamp;
the rest is the audit trail a partner will read:

```
[autopilot run=<run id> mode=<shadow|write> policy=v1.1@2026-10-20 verifier=<agree|disagree|skipped (part 1)|n/a>]
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
CLI unreachable, an ambiguous error after a write, `--expect` mismatch twice on one item, the
corpus/log commands missing, `write` requested without the gate token, the verifier unreachable
for every pin candidate, the auditor / a proposer / the scorer failing to return, and — write mode
only — budget exhausted with open items closing within 3 days); or a recurring cause worth an
engineering or policy fix (a note in the report, one page at most). Shadow mode pages for tooling
failures only, never for budget or decisions. The Grafana rot and escalations alerts keep nagging
on their own; do not duplicate them.

## Report format (one message)

Scheduled run:

```
Review autopilot — <local time> — mode=<shadow|write> — run=<id> — policy=v1.1@2026-10-20
Queue: <n> before (<open> open / <closed> closed, <parked> parked) → <n> after
Decisions (<k>/10):
  <ocd-id>  <kind>[ → date]  verifier=<result>  expect=<h1[:12]>,<h2[:12]>  [written obs=<id> | proposal]  verified: <yes/no + what | n/a (shadow)>
Skipped: <ocd-id> — <reason> …
Escalations written/proposed: <n> (<ids>)
Audit (Mondays): invalidated this week: <ids>; sampled <ids: agree/disagree/could-not-audit with both readings>; parked (human / autopilot) + shadow escalations re-inspected: <ids and outcome>; auditor=<model>
Tooling: <none | what failed, paged yes/no>
Recurring cause: <none | one line>
Next run: tomorrow 07:00 local
```

Harness or ad-hoc run (a proposer, the scorer, or an operator-supplied list): replace the
`Queue` line with `Items: <n> supplied (<source: corpus --blind | operator>)`, drop `Next run`, and
for the scorer end with the per-part tallies (`Part 1: <agree>/<total> …`; `Part 3: …`; every
disagreement listed with the proposer's reason).

## The shadow harness (gate parts 1 and 3)

The harness is run on the operator's request, not by the daily schedule, and it has **three roles
in three separate contexts**: an _orchestrator_ (you, the scheduled thread) that never sees an
expectation; fresh _proposers_ that see only ids; and a fresh _scorer_ that reads the
expectations after the proposals are sealed. Anything that has seen `corpus --json`
(`expected_close`, the `pins` / `escalations` grouping) or the runbook's required set cannot be
un-told by `show --blind` — and you are also the daily part 2 proposer, so you never read them.

**As the orchestrator:**

1. Seal the scorer's snapshot first, without looking at it: run `review corpus --json` with its
   output redirected straight into `~/.config/yokel/review-autopilot/harness-<run id>/corpus.json`
   (`… corpus --json > that-file`; never print or open it). The gate is scored against this
   snapshot, so a window whose verdict is invalidated while the proposers work stays in the
   denominator instead of silently leaving it. Then `review corpus --blind` → a flat, sha256-ordered list of ids, nothing else. Shuffle it (order
   by the sha256 of `<harness run id>:<ocd-id>`) and split it into batches of at most 5.
2. For each batch dispatch a **fresh proposer** (see "Dispatching children"): provider
   `claudeAgent`, model `claude-opus-5-5`, effort `high`, role `general`. Its task text
   contains, verbatim, this skill's "Hard limits", "Runtime" (all subsections), "The write policy
   (v1)" and "Note format" sections; the harness run id; the batch number; the batch's ids; and
   these instructions: run `review show <id> --blind` plus the full search on each; decide per
   the policy **without** the verifier (write `verifier: {"model": null, "result": "skipped
(part 1)"}` on pins — part 1 measures agreement with human-authorized precedent, not the
   pipeline); append one line per id to `~/.config/yokel/review-autopilot/harness-<run
id>/batch-<n>.jsonl` with `"harness": "<run id>"`, `"mode": "shadow"`, `"written": false`;
   propose on every id given; write nothing to the cluster; page nobody.
3. Only after every proposer has returned, dispatch a **fresh scorer**: provider `claudeAgent`,
   model `claude-sonnet-5-5`, effort `medium`, role `review`. Its task text contains the harness
   run id, the "Runtime" command block, and these scoring rules; it reads the sealed
   `harness-<run id>/corpus.json` (never a fresh `corpus --json`), the runbook's required part 3
   set (`docs/runbooks/review-queue.md`, "Shadow gate"), and the `harness-<run id>/batch-*.jsonl`
   files, and returns the tallies. It also runs `review corpus --json` once at scoring time and
   lists every snapshot id whose standing changed meanwhile (now `not_honored`, or a different
   `expected_close`): those are scored against the snapshot and reported as "changed during the
   run" so the operator can re-run them; they are never dropped.
   - **Part 1** — for each id in `pins` whose `reviewer` is `human` (agent pins are the
     autopilot's own output and are not precedent): agree iff `proposal.kind == "pin_close"` and
     `proposal.close == expected_close`. The denominator is the **whole** list: a missing or
     `skip` line counts as a disagreement. Target ≥ 95 % agree, every disagreement listed with
     the proposer's reason.
   - **Part 3** — for each id of the required set and each id in `escalations`: agree iff
     `proposal.kind` is the expected kind (`escalate` for the #127 items, `confirm_withdrawn` for
     the #112 withdrawals, per the required-set table); for each id in `withdrawals`: agree iff
     `proposal.kind == "confirm_withdrawn"`. Any `dismiss_conflict` or `confirm_reopened`
     anywhere in the run fails part 3. An empty live category never passes by vacancy: the
     required set must be covered, and a missing proposal counts as a disagreement.
     The required set's un-parked ids are live queue members and may be absent from `corpus
--blind`; the scorer lists them as "not proposed" and the operator runs a second harness pass
     with those ids supplied explicitly to a fresh proposer.
4. Relay the scorer's tallies and every disagreement in your report; the operator records the
   result in the runbook. You do not edit the runbook, and you do not read the scorer's inputs.

**Part 2 — the held-out set** is the operator's: 10 current queue items (excluding the required
set's ids) whose verdicts the operator seals in
`~/.config/yokel/review-autopilot/held-out-<date>.json` **before** reading any proposal (runbook
§ Autopilot). Your daily shadow runs over the live queue supply the proposals; the operator
compares. Part 2 uses the full pipeline, verifier included. You never read those files.
