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
kubectl -n docketclock exec deploy/docketclock-poller -- pnpm exec tsx src/review/cli.ts show <ocd-id>
kubectl -n docketclock exec deploy/docketclock-poller -- pnpm exec tsx src/review/cli.ts resolve <ocd-id> \
  --kind pin_close --close 2026-09-20 --note "why, in one honest sentence" --operator lucas
```

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
