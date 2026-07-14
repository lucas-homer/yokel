# Week-1 validation spikes

Runnable harness for the go/no-go spikes in
[`docs/plans/week1-validation-spikes.md`](../docs/plans/week1-validation-spikes.md). **Run on the
Mac Mini.** These answer the questions that gate the build — a measured "no" this week is a success.

📋 **Results so far:** [`docs/plans/week1-go-no-go-memo.md`](../docs/plans/week1-go-no-go-memo.md) —
the Go/No-Go memo populated with measured numbers from the implemented spikes.

## Setup (Mini)

```bash
pnpm install                 # from repo root
cp .env.example .env         # add REGS_KEY from https://api.data.gov/signup/
```

## The spikes

| Cmd          | Spike | Question (the decision it gates)                                             |
| ------------ | ----- | ---------------------------------------------------------------------------- |
| `pnpm d1`    | D1 ⭐ | frDocNum join hit-rate — primary key vs docket_id/RIN fallback (MASTER GATE) |
| `pnpm d2`    | D2    | Eastern-date conflict rate — "conflict intelligence" vs "reliable alerts"    |
| `pnpm d3`    | D3    | extension/correction volume + deny-list precision — review-console staffing  |
| `pnpm w1`    | W1    | is Regulations.gov `POST /comments` open to non-gov submitters? (kill-shot)  |
| `pnpm w2`    | W2    | EPA EIS machine-readability — API vs scraper                                 |
| `pnpm w3` ⭐ | W3    | novel in-basin windows/quarter for a Chesapeake HUC-8 (business kill-shot)   |

⭐ = the two that matter most: D1 (does the join hold?) and W3 (is there enough basin signal?).

The two that matter most run first. D4 (GSA rate-increase request), D5 (buyer calls), W4–W6
(geo-recall labels, USACE §404, partner fit) are non-code tasks — see the plan.

## Status

| Spike  | State          | Notes                                                                                         |
| ------ | -------------- | --------------------------------------------------------------------------------------------- |
| **D1** | ✅ implemented | FR (keyless) + Regs.gov pull → DuckDB join → `out/D1_join_rate.md`.                           |
| **W3** | ✅ implemented | WBD HUC-8 resolve + FR full-text basin search → `out/W3_value_density.md` + candidate sheet.  |
| **D2** | ✅ implemented | Reuses the D1 pull; Eastern-vs-UTC date conflict in DuckDB → `out/D2_conflict_rate.md`.       |
| **D3** | ✅ implemented | FR 90-day title detector + FP heuristics → `out/D3_extension_volume.md` + 50-row label sheet. |
| **W1** | ✅ implemented | Non-destructive POST probes of Regs.gov submission endpoints → `out/W1_comment_post.md`.      |
| **W2** | ✅ implemented | EPA EIS endpoint probes + FR EIS-notice spine sample → `out/W2_eis_source.md`.                |

All six code spikes are implemented. D4/D5 and W4–W6 are non-code action/interview tasks — see the plan.

Outputs go to `out/` (gitignored); pulled API data to `data/` (gitignored).

## xcheck — the offline accuracy cross-check (verification slice V, PR-V2)

Not a Week-1 spike: a RECURRING differential that reuses this package's DuckDB harness. It joins
the [spicy-regs](https://github.com/civictechdc/spicy-regs) Parquet mirror of Regulations.gov
(public R2 bucket, read in place over `httpfs` — nothing downloaded) against a read-only export of
the live `participation_windows`, compares **Eastern-calendar-date** closes + the `withdrawn`
signal, and writes [`out/XCHECK_diff.md`](out/XCHECK_diff.md) — the one `out/` artifact that is
**checked in**, because its hand-filled `triage` column is the work product.

```bash
pnpm --filter @yokel/docketclock export:windows   # live export → data/windows.jsonl
pnpm --filter @yokel/spikes xcheck                # differential → out/XCHECK_diff.md
```

Every disagreement gets a hand-filled triage value: `our_bug` (the live projection is wrong — a
FIND: export it with `export:accuracy-miss` so it becomes a committed replay fixture),
`bulk_stale` (the mirror lags live Regs.gov — the EXPECTED dominant bucket), or `source_drift`
(the sources themselves changed). Re-runs carry filled triage forward for persisting
disagreements — keyed by (ocd_id, category), so a finding that changes category re-triages from
scratch — and never clobber finished work. When hand-editing a note, spell a literal pipe as
`\|` (markdown-standard): a raw `|` breaks the table row and costs that row its triage on the
next re-run.

**Cadence:** re-run on every fresh parquet snapshot, at least monthly while calibrating. A pass is
NOT done until every disagreement carries a triage value — an unfilled column in the committed
diff is the reminder. Architecture rule: the mirror is offline eval/seed only, **never** a live
freshness source; this stays a batch differential, not a third adapter.

### Env / flags

- `REGS_KEY` — **required for an authoritative D1 run.** Without it D1 falls back to `DEMO_KEY`
  (free key: <https://api.data.gov/signup/>). DEMO_KEY works only while the open set fits in one
  cursor window (~5k docs) before its hourly cap bites.
- `D1_USE_CACHE=1` / `D3_USE_CACHE=1` — re-run the analysis over the last `data/` pull with **no API
  calls** (iterate on the report, or when an API budget is spent).
- `HUC8=02060005` — which HUC-8 W3 measures (default Choptank). Add a keyword seed in `BASIN_SEED`
  for new basins, or pass `W3_KEYWORDS="term1,term2,..."` to extend the search/filter terms.
- `SPICY_REGS_PARQUET` — URL/glob for the spicy-regs Parquet `documents` table, read via DuckDB
  httpfs. Default `https://r2.spicy-regs.dev/documents.parquet` (the civictechdc/spicy-regs public
  R2 bucket; also `dockets.parquet` / `comments.parquet` there). Used by `pnpm xcheck`; point it at
  a local snapshot to pin a pass to a fixed dataset.
- `WINDOWS_JSONL` — xcheck's live-windows export path (default `data/windows.jsonl`, written by
  `pnpm --filter @yokel/docketclock export:windows`).

### Verified API facts (cost us a debug cycle — don't relearn)

- Regs.gov v4 filter is `filter[commentEndDate][ge]` — **`[ge]`, not `[gte]`.** Past page 20 (5k
  docs) you must advance a `lastModifiedDate` cursor and dedupe by `id`.
- FR `conditions[term]` has **no `"a" OR "b"` boolean** — issue one quoted phrase per call.
- FR **returns** `type` as display strings (`"Notice"`, `"Proposed Rule"`, `"Rule"`) even though the
  request _filter_ uses abbreviations (`NOTICE`/`PRORULE`/`RULE`). Classify on the display values.
- The National Map WBD HUC-8 layer is `wbd/MapServer/4`.
- Regs.gov v4 `GET /comments` requires `page[size] >= 5` (a `1` returns HTTP 400).
- Regs.gov v4 comment submission is **tier-gated**: a standard key gets `201` on `POST /submission-keys`
  but `403 API_KEY_UNAUTHORIZED` on `POST /comments` (W1 kill-shot). EPA's EIS DB (cdxapps) is HTML-only;
  the Federal Register EIS-notice stream is the keyless machine-readable spine (W2).
