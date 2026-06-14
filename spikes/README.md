# Week-1 validation spikes

Runnable harness for the go/no-go spikes in
[`docs/plans/week1-validation-spikes.md`](../docs/plans/week1-validation-spikes.md). **Run on the
Mac Mini.** These answer the questions that gate the build — a measured "no" this week is a success.

## Setup (Mini)

```bash
pnpm install                 # from repo root
cp .env.example .env         # add REGS_KEY from https://api.data.gov/signup/
```

## The spikes

| Cmd            | Spike | Question (the decision it gates)                                              |
| -------------- | ----- | ---------------------------------------------------------------------------- |
| `pnpm d1`      | D1 ⭐ | frDocNum join hit-rate — primary key vs docket_id/RIN fallback (MASTER GATE)  |
| `pnpm d2`      | D2    | Eastern-date conflict rate — "conflict intelligence" vs "reliable alerts"     |
| `pnpm d3`      | D3    | extension/correction volume + deny-list precision — review-console staffing   |
| `pnpm w1`      | W1    | is Regulations.gov `POST /comments` open to non-gov submitters? (kill-shot)   |
| `pnpm w2`      | W2    | EPA EIS machine-readability — API vs scraper                                  |
| `pnpm w3` ⭐   | W3    | novel in-basin windows/quarter for a Chesapeake HUC-8 (business kill-shot)    |

⭐ = the two that matter most: D1 (does the join hold?) and W3 (is there enough basin signal?).

The two that matter most run first. D4 (GSA rate-increase request), D5 (buyer calls), W4–W6
(geo-recall labels, USACE §404, partner fit) are non-code tasks — see the plan.

## Status

| Spike | State | Notes |
| --- | --- | --- |
| **D1** | ✅ implemented | FR (keyless) + Regs.gov pull → DuckDB join → `out/D1_join_rate.md`. |
| **W3** | ✅ implemented | WBD HUC-8 resolve + FR full-text basin search → `out/W3_value_density.md` + candidate sheet. |
| **D2** | ✅ implemented | Reuses the D1 pull; Eastern-vs-UTC date conflict in DuckDB → `out/D2_conflict_rate.md`. |
| D3, W1, W2 | stubs | Each `src/*.ts` carries its objective, method, and decision rule as comments. |

Outputs go to `out/` (gitignored); pulled API data to `data/` (gitignored).

### Env / flags

- `REGS_KEY` — **required for an authoritative D1 run.** Without it D1 falls back to `DEMO_KEY`
  (free key: <https://api.data.gov/signup/>). DEMO_KEY works only while the open set fits in one
  cursor window (~5k docs) before its hourly cap bites.
- `D1_USE_CACHE=1` — re-run D1's join/report over the last `data/` pull with **no API calls** (iterate
  on the analysis, or when the Regs.gov hourly budget is spent).
- `HUC8=02060005` — which HUC-8 W3 measures (default Choptank). Add a keyword seed in `BASIN_SEED`
  for new basins, or pass `W3_KEYWORDS="term1,term2,..."` to extend the search/filter terms.
- `SPICY_REGS_PARQUET` — (future) glob for the spicy-regs/Mirrulations Parquet so W3 can cross-check
  the Regs.gov-rulemaking count via DuckDB httpfs.

### Verified API facts (cost us a debug cycle — don't relearn)

- Regs.gov v4 filter is `filter[commentEndDate][ge]` — **`[ge]`, not `[gte]`.** Past page 20 (5k
  docs) you must advance a `lastModifiedDate` cursor and dedupe by `id`.
- FR `conditions[term]` has **no `"a" OR "b"` boolean** — issue one quoted phrase per call.
- FR **returns** `type` as display strings (`"Notice"`, `"Proposed Rule"`, `"Rule"`) even though the
  request *filter* uses abbreviations (`NOTICE`/`PRORULE`/`RULE`). Classify on the display values.
- The National Map WBD HUC-8 layer is `wbd/MapServer/4`.
