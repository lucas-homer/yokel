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

**Stubs.** Each `src/*.ts` carries its objective, method, and decision rule as comments with a
`TODO`. Fill them in on the Mini (the plan has the exact DuckDB queries + curl probes). Outputs go to
`out/` (gitignored); pulled API data to `data/` (gitignored).
