# Chain-adjudicator eval corpus (Slice D)

Ground truth for measuring the chain-seam adjudicator (does notice B genuinely amend notice A?) against
**human** labels — not the model's own past verdicts. See `plans/observability-evals.md`.

## Files

- **`chain-gold.json`** — the committed, hand-labeled corpus the eval scores against. Each entry embeds the
  full `AdjudicationInput` (public Federal Register text — no PII), so the eval runner needs no Postgres and
  no Langfuse. `gold` is the authoritative human label; `model_verdict` is the model's own past call, kept
  for **reference only**.
- **`chain-gold.template.json`** — generated, not committed (gitignored). The export script writes it with
  `gold: null`; you copy it to `chain-gold.json` and fill the labels.

## Workflow

1. **Export the template** (reads the `adjudications` cache; reuses the exact selection that seeded the
   Langfuse dataset, so the corpus lines up item-for-item):

   ```bash
   # DATABASE_URL → the docketclock Postgres (port-forward svc/docketclock-pg-rw locally)
   pnpm --filter @yokel/docketclock export:gold-template            # writes chain-gold.template.json
   pnpm --filter @yokel/docketclock export:gold-template --dry-run  # just prints the stratification
   ```

2. **Label.** Copy the template to `chain-gold.json` and set each `gold` to one of:
   - `affirm` — B genuinely amends A (extends/reopens/modifies A's comment period or rule).
   - `reject` — they merely look related; B does not actually amend A.
   - `uncertain` — genuinely can't tell from the notice text (use sparingly — it's low eval signal).

   Judge from the embedded fields: `a_title` / `b_title`, `a_dates_text` / `b_dates_text`, publication
   dates, and the corroboration signals `shared_docket` / `shared_rin` / `explicit_reference`. The optional
   `note` records why. `model_verdict` is visible but is **not** authoritative — correct it freely.

3. **Validate + commit.** `loadGold()` (and the eval) reject a half-labeled file (any null `gold`), a bad
   `input`, duplicate `content_hash`es, or an empty corpus — so a malformed corpus fails loudly. Commit
   `chain-gold.json`.

## Growing the corpus

As the live poller adjudicates more ambiguous pairs, re-run the export: the selection is stable and
monotonic, so re-exporting only **adds** new items at the tail. Label the new entries and re-commit.
Existing labels are never clobbered (the export only writes `*.template.json`).
