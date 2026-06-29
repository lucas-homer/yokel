# Observability Slice D — Evals (human gold labels + scoring run + nightly regression gate)

> Status: **PR-D1 built** — gold tooling + a 50-item human-labeled corpus
> (`eval/chain-gold.json`, 23 affirm / 26 reject / 1 uncertain) committed on `feat/eval-gold-labels`.
> Awaiting go on PR-D2 (eval runner + scoring).
> Target: local k3d for the Langfuse enrichment; the eval CORE is Langfuse-independent and runs anywhere
> (incl. GitHub Actions). Builds directly on Slice C (`observability-llm.md`, shipped): the seeded
> `docketclock-adjudications` Langfuse dataset, the pure `selectDatasetItems()` selection, the injected
> `LlmTracer`, and the `adjudicate(input)` seam.

## Why this slice, why now

Slice C gave us per-call **traces** and a **seeded eval dataset** — but the dataset's `expectedOutput` is the
model's OWN past verdict (provisional, flagged `provisional: true`). Scoring Gemini against its own answers
is circular (~100%, minus nondeterminism) and tells us nothing. **The whole point of D is to establish HUMAN
ground truth and measure the adjudicator against it** — classification accuracy on the amends/doesn't-amend
call — then watch that number over time so a prompt/model/rulebook change that regresses quality is caught.

## What exists today (the seams this slice hooks into)

- **The eval corpus** — the Langfuse dataset `docketclock-adjudications` (Slice C / PR-C3), item id =
  `content_hash`, `input` = canonical `AdjudicationInput`, `expectedOutput` = the provisional verdict,
  `metadata.provisional = true`. Currently 50 items (25 chain/affirm + 25 chain/reject by the model's call).
- **Pure selection** — `src/adjudicator/eval-dataset.ts` `selectDatasetItems(rows, {cap, includeNull})`:
  the same deterministic, stratified, capped, deduped selection that produced the dataset. **D1 reuses it**
  so the gold file holds exactly the same items (same `content_hash`es) as the Langfuse dataset.
- **The adjudicator seam** — `src/adjudicator/port.ts` `adjudicate(input): Promise<AdjudicationVerdict>`;
  `selectAdjudicator(env)` builds the Gemini adapter (with the injected `LlmTracer`) from `ADJUDICATOR` +
  `GEMINI_API_KEY` + `GEMINI_MODEL`. The eval calls `adjudicate(input)` directly (NOT `consultAdjudicator`
  — the eval must bypass the `adjudications` read-through cache so it measures the live model, not a replay).
- **Langfuse v2 (2.95.11)** — confirmed core support for **scores** (`langfuse.score`) and **dataset runs**
  (`getDataset(name).items[].link(trace, runName)`), so a run + per-item score + an accuracy/experiments
  view all work natively. (Annotation queues exist upstream since 2024-10 but we deliberately do NOT depend
  on the UI for labeling — see decisions.) The server is **local-only / not internet-exposed**, so CI cannot
  reach it; the Langfuse push is therefore an OPTIONAL local enrichment, never a hard dependency of the eval.
- **Test/style conventions** — hand-rolled `assert` + `out[]` + `process.exit` runners wired into
  `pnpm test` (see `test/eval-dataset.test.ts`); `*.smoke.ts` for live one-shots; prettier `--check .` and
  `tsc` are the `check` gate. The CNPG docketclock DB is reached locally via a `docketclock-pg-rw`
  port-forward (`DATABASE_URL` from the `-app` secret).

## Decisions locked

- **Ground truth = a git-committed gold file**, `apps/docketclock/eval/chain-gold.json`. Each entry embeds
  the FULL `AdjudicationInput` (public FR text — no PII), the model's provisional verdict (for reference
  only), and a human `gold` field. Embedding the input makes the file the SELF-CONTAINED eval corpus: the
  runner needs no Postgres and no Langfuse to score. The file is reviewable in PRs and reproducible.
- **Eval scores live in Langfuse dataset-runs** (native v2), reusing the Slice C dataset — a run per
  invocation (`runName = "<adjudicator.id>@<git-sha-or-timestamp>"`), a trace per item, an exact-match
  `score` (0/1). PLUS a printed local summary (accuracy + confusion matrix). The Langfuse push is
  ALL-OR-NOTHING on `LANGFUSE_*` (like the tracer): absent ⇒ skip the push, still compute + print + gate.
- **Regression gate = a WEEKLY canary + a path-filtered on-merge run**, not per-PR (each run makes ~N live
  Gemini calls — real cost + a key + provider flakiness). The weekly cron catches slow provider drift; the
  `push: main` + `paths:` trigger catches OUR regressions at the commit that introduces them (prompt/model/
  rulebook/gold), post-merge so it never blocks a PR. Needs only `GEMINI_API_KEY` (the eval core is
  Langfuse-independent). Fails / alerts when accuracy drops below a committed threshold (margin for temp-0
  nondeterminism). See PR-D3 for why the corpus being static makes this two-trigger shape strictly better
  than any single cadence.
- **Bypass the cache.** The eval calls `adjudicate(input)` directly; it must NOT go through
  `consultAdjudicator` (which would replay the cached verdict and measure history, not the live model).
- **Metric — binary primary, 3-way secondary.** Downstream, ONLY `affirm` promotes a cross_window link;
  `reject`, `uncertain`, and any error are downstream-IDENTICAL (no link — see
  `chain-adjudicate.ts:236`). So the operationally-meaningful decision is **affirm vs not-affirm**, and the
  PRIMARY metric is that BINARY "amends?" accuracy (collapse reject+uncertain → "not-affirm" on BOTH gold
  and prediction). This also means a gold label of `reject` vs `uncertain` does NOT move the headline number
  — so the corpus can be labeled by what's most truthful without gaming the metric, and a model that
  conservatively abstains (`uncertain`) is not punished for the operationally-correct no-link outcome. The
  full 3×3 confusion matrix over {affirm, reject, uncertain} is reported as SECONDARY detail (it surfaces
  reject↔uncertain disagreement for inspection). Pure + unit-tested.
- **No contract change.** `AdjudicationVerdict` stays frozen; no contract-keeper involvement. A small local
  zod schema validates the gold file shape.

## PR-D1 — Gold-file export + the human labeling pass (script + committed data)

The one PR with a human-in-the-loop step. Independently useful: produces the labeled corpus D2 consumes.

1. **`apps/docketclock/scripts/export-gold-template.ts`** (`pnpm export:gold-template`) — read
   `adjudications` (oldest-first), run `selectDatasetItems()` (SAME cap/stratification as the seed, so the
   gold corpus == the Langfuse dataset), and write `eval/chain-gold.template.json`: for each item
   `{ content_hash, input, model_verdict: {classification, rationale}, gold: null, note: "" }`. Read-only on
   Postgres; never overwrites a hand-filled `chain-gold.json`. `--dry-run` prints counts.
2. **Human labels** the items: copy the template to `eval/chain-gold.json`, set each `gold` ∈
   {affirm, reject, uncertain} from the embedded titles/dates/corroboration signals (no external lookup
   needed). The model_verdict is visible for reference but is NOT authoritative.
3. **`src/adjudicator/eval-gold.ts`** — a zod schema + `loadGold(path)` that parses/validates the gold file
   (every entry has a non-null `gold`; `input` re-parses against `AdjudicationInput`) and returns typed
   entries. Fails loudly on a malformed/half-labeled file. Pure, unit-tested
   (`test/eval-gold.test.ts`, wired into `pnpm test`).
4. **Commit** `eval/chain-gold.json` (and a short `eval/README.md` on how to re-export + re-label as the
   corpus grows). **Verify:** `loadGold` accepts the committed file; counts match the Langfuse dataset.

## PR-D2 — Eval runner + scoring (app code)

1. **`src/adjudicator/eval-score.ts`** — PURE scoring: `scoreEval(results)` where each result is
   `{ contentHash, kind, gold, predicted }` → `{ amendsAccuracy /* PRIMARY: affirm-vs-not binary */,
amendsConfusion /* 2×2: TP/FP/FN/TN on "amends" */, exactAccuracy /* 3-way, secondary */, confusion: 3×3,
n }`. The binary collapses {reject, uncertain} → "not-amends" on both gold and prediction (they are
   downstream-identical). No I/O. Unit-tested (`test/eval-score.test.ts`): binary collapse, the 2×2 and 3×3
   matrices, that reject↔uncertain disagreement moves only the 3-way number (not the headline), empty input.
2. **`scripts/eval-chain.ts`** (`pnpm eval:chain`) — orchestration:
   - `loadGold("eval/chain-gold.json")`; build `selectAdjudicator()` (must resolve to the Gemini adapter,
     else fail loudly — mirror the smoke's guard).
   - For each entry: `adjudicate(entry.input)` (DIRECT — cache-bypassed), collect `predicted`. Sequential
     (≤ a few hundred items); a small concurrency cap is a later optimization.
   - `scoreEval(...)` → print accuracy / accuracyExclUncertain / confusion matrix.
   - **Langfuse enrichment (optional, all-or-nothing on `LANGFUSE_*`):** `getDataset("docketclock-
adjudications")`, and for each item `item.link(trace, runName)` + `langfuse.score({ traceId, name:
"classification_match", value: predicted===gold ? 1 : 0, comment })`. `runName =
"<adjudicator.id>@<short-sha|ISO-ts>"`. `flush()`/`shutdown()` at the end. Absent `LANGFUSE_*` ⇒ skip
     cleanly (the printed summary + exit code are unaffected).
   - `--min-accuracy <x>`: exit non-zero when accuracy < x (default: no gate locally). `--limit N` for a
     quick subset.
3. **Verify:** run locally against the committed gold (real key + `task langfuse`): printed accuracy +
   confusion matrix match; a dataset run appears in the Langfuse UI with per-item scores; `--min-accuracy`
   gates as expected; with `LANGFUSE_*` unset the run still scores + prints + gates (no push).

## PR-D3 — Regression gate (CI): weekly canary + path-filtered on-merge

Two triggers, because the gold corpus is STATIC: between runs the only time-varying input is Gemini's own
provider drift (slow), while OUR regressions are introduced at a COMMIT (the prompt in
`gemini-adjudicator.ts`, `GEMINI_MODEL`, a rulebook bump, the gold file). A time-based cadence catches the
former; an event-based trigger catches the latter at its source. (Cost is a non-factor either way —
`gemini-2.5-flash` on ~50 small calls is ~$0.10–0.15/run.)

1. **`.github/workflows/eval-chain.yml`** — ONE workflow, two triggers:
   - **`schedule:`** a WEEKLY cron (e.g. Monday early UTC) — the provider-drift canary. Low noise, ~4
     runs/mo. (Weekly, not nightly: faster detection buys little against slow provider drift and only adds
     temp-0-wobble false alarms.)
   - **`push:` to `main` with `paths:`** filtered to the files that can actually move the number —
     `apps/docketclock/src/adjudicator/**`, `apps/docketclock/src/rulebox/**` (the rulebook),
     `apps/docketclock/eval/chain-gold.json`, and the workflow itself. Runs the eval ONLY when a merged
     change could affect the verdict, at the source, immediately, and POST-merge so it never blocks or
     flakes a PR (same spirit as the `smoke`). Add **`workflow_dispatch`** for manual runs.
   - Steps (shared): checkout, pnpm install, `pnpm --filter @yokel/docketclock eval:chain --min-accuracy
<THRESHOLD>` with `ADJUDICATOR=gemini` + `GEMINI_API_KEY` from repo secrets. NO `LANGFUSE_*` (the local
     server is unreachable from Actions), so it runs the Langfuse-independent core: gold → adjudicate →
     score → threshold. On failure the red job IS the alert (optionally open/update a tracking issue).
2. **Threshold** committed (in the workflow or `eval/threshold.json`) with margin below the observed
   baseline for temp-0 wobble; document how to bump it when the prompt/model intentionally changes (an
   intentional change rides in on a `main` push, so the on-merge run is also where you re-baseline).
3. **Verify:** `workflow_dispatch` a manual run green against the current corpus; a touch-test that a commit
   under the filtered paths triggers the on-merge run while an unrelated change does NOT; confirm a
   deliberately low threshold fails the job (alert path works); confirm no `LANGFUSE_*`/DB is required.

## Out of scope (later)

- **Larger/auto-growing corpus** — as the live poller adjudicates more ambiguous pairs, re-export the
  template and label the new items (the selection is stable/monotonic, so existing labels are untouched).
  Automating "label the new tail" can come later.
- **Per-PR gate** — rejected for cost/flakiness; revisit only if eval calls become cheap/mocked.
- **promptfoo** — the Langfuse-native run covers our need; a promptfoo matrix is a possible later add for
  prompt A/B exploration, not regression gating.
- **LLM-as-judge / rationale quality** — D scores the categorical verdict only; grading rationale text is a
  separate, later effort.
- **Notice-kind evals** — the corpus is currently all `chain`; notice-kind items get labeled + scored once
  they exist (the grid already covers them).

## Rollback

- PR-D1: delete `eval/chain-gold.json` + the export script; nothing else depends on them (the Langfuse
  dataset and `adjudications` are untouched — the script is read-only).
- PR-D2: revert; `eval-score.ts`/`eval-chain.ts` are additive and call nothing in the live pipeline. Any
  Langfuse runs/scores already pushed are inert history in the UI.
- PR-D3: delete the workflow; it only ever read the corpus + called Gemini on a schedule.

```

```
