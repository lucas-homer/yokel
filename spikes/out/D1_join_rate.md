# D1 — frDocNum join hit-rate

**Run:** 2026-06-14 (Eastern) · open-comment cutoff `commentEndDate / comment_date >= 2026-06-14`
**Regs key:** real REGS_KEY

## Primary join (regs.frDocNum = fr.document_number)

| metric | value |
| --- | ---: |
| Regs.gov open docs | 1184 |
| …with a non-null frDocNum | 987 |
| joined to an FR document | 932 |
| **hit_pct** (joined / all open) | **78.7%** |
| hit_pct among docs that *have* a frDocNum | 94.4% |

## Fallback (docket_id array overlap, for the misses)

| metric | value |
| --- | ---: |
| frDocNum misses | 252 |
| …of which carry **no frDocNum at all** | 197 |
| recovered via docketId ∈ fr.docket_ids | 1 |
| **combined coverage** (frDocNum + docket) | **78.8%** |

> **Interpretation:** the docket fallback is measured against the *open* FR set only, so it recovers
> little — 197/252 misses have a null frDocNum and are mostly stale,
> perpetually-open Regs dockets (e.g. `*-2007-*` with far-future commentEndDate) whose FR notice is
> years old and not in today's open pull. A production fallback would join against the *full* FR
> corpus, not just the open window. Treat `combined coverage` here as a conservative floor.
>
> RIN fallback not computed: Regs.gov exposes RIN at the *docket* level, not on the document record,
> so a document-level RIN join needs a second `/v4/dockets` pull. docketId overlap is the cheap proxy.

## Decision

**hit_pct = 78.7% → GO — frDocNum as primary reconciliation key**

- Rule: `hit_pct ≥ 60%` → GO frDocNum-primary; `< 60%` → PIVOT to Regs.gov-primary with
  docket_id-array-overlap + RIN; FR-only records carry `confidence=medium,
  conflict_reason="no_cross_source_join"`.
- Note: a meaningful share of open Regs docs carry no frDocNum at all (1184 open, 987 with frDocNum); the docket fallback still matters for those even under GO.

_Artifacts: `data/fr_open.json` (1132 rows), `data/regs_open.json` (1184 rows)._
