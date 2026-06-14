# W3 — In-basin value density

**Run:** 2026-06-14 (Eastern)
**Basin:** HUC-8 `02060005` — **Choptank** (DE,MD), 702,873 acres
**Window:** last 4 quarters (2025-07-01 → 2026-06-14)
**Keywords:** `Choptank`, `Tuckahoe`, `Tred Avon`, `Marshyhope`, `Chesapeake Bay`, `Caroline County`, `Talbot County`, `Dorchester County`, `Queen Anne`

## Candidate counts per quarter (estimate — keyword + manual, not the production classifier)

| metric | 2025Q3 | 2025Q4 | 2026Q1 | 2026Q2 | total |
| --- | ---: | ---: | ---: | ---: | ---: |
| EIS | 0 | 0 | 4 | 1 | 5 |
| Regs.gov rulemaking | 5 | 2 | 3 | 1 | 11 |
| **total** | **5** | **2** | **7** | **2** | **16** |

- **Average in-basin candidates/quarter:** 4.0
- **EIS share of candidates:** 31% (5 EIS / 11 Regs.gov rulemaking)

## Decision (provisional — finalize after manual labeling below)

**GO (provisional) — a handful of in-basin candidates/quarter with a real EIS share**

- Rule: `≳ a handful/quarter with EIS a meaningful share` → GO; `~2–3/quarter or EIS share ≈ 0` → STOP.
- ⚠️ These are **candidate** counts (FR full-text search per basin phrase, body mentions included —
  recall-biased, so expect false positives like national rules that merely name a water body). The plan's number is
  *novel* in-basin Tier-1 windows — "novel" (previously-unknown-to-the-org) is a human judgment.
  Label the sheet below, drop false positives + already-known items, then recompute. Treat the
  counts above as an **upper bound**.
- Source caveat: EIS + rulemaking are drawn from the Federal Register (authoritative, keyless). For a
  fuller Regs.gov-rulemaking estimate, set `SPICY_REGS_PARQUET` and cross-check against the
  Mirrulations/spicy-regs Parquet via DuckDB httpfs (not yet wired into the count here).

## Candidate sheet — label each row

`novel?` = is this a window the org wouldn't already know about? `in_basin?` = does the text really
place it in Choptank, not just mention a keyword?

| quarter | bucket | FR doc # | published | matched kw | agency | title | novel? in_basin? (y/n) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2025Q3 | Regs | 2025-18634 | 2025-09-25 | Chesapeake Bay | Homeland Security Department | Safety Zone; Chesapeake Bay, Baltimore, MD |   |
| 2025Q3 | Regs | 2025-16354 | 2025-08-26 | Chesapeake Bay | Homeland Security Department | Safety Zone; Chesapeake Bay, Baltimore, MD |   |
| 2025Q3 | Regs | 2025-18816 | 2025-09-29 | Chesapeake Bay | Environmental Protection Agency | Water Quality Standards To Protect Aquatic Life in the Delaware River |   |
| 2025Q3 | Regs | 2025-16933 | 2025-09-04 | Chesapeake Bay | Interior Department | Endangered and Threatened Wildlife and Plants; Five Species Not Warranted for Listing as E |   |
| 2025Q3 | Regs | 2025-15703 | 2025-08-18 | Chesapeake Bay | Interior Department | Migratory Bird Hunting; Final 2025-26 Frameworks for Migratory Bird Hunting Regulations |   |
| 2025Q4 | Regs | 2025-19806 | 2025-11-07 | Chesapeake Bay | Commerce Department | Takes of Marine Mammals Incidental to Specified Activities; Taking Marine Mammals Incident |   |
| 2025Q4 | Regs | 2025-20402 | 2025-11-20 | Chesapeake Bay | Defense Department | Updated Definition of “Waters of the United States” |   |
| 2026Q1 | Regs | 2026-01400 | 2026-01-26 | Tuckahoe | Homeland Security Department | Drawbridge Operation Regulation; Technical Amendment; Removal of Obsolete Drawbridge Opera |   |
| 2026Q1 | EIS | 2026-01874 | 2026-01-30 | Chesapeake Bay | Environmental Protection Agency | Environmental Impact Statements; Notice of Availability |   |
| 2026Q1 | EIS | 2026-01267 | 2026-01-23 | Chesapeake Bay | Environmental Protection Agency | Environmental Impact Statements; Notice of Availability |   |
| 2026Q1 | Regs | 2025-24203 | 2026-01-02 | Chesapeake Bay | Commerce Department | Taking of Marine Mammals Incidental to Commercial Fishing Operations; Harbor Porpoise Take |   |
| 2026Q1 | Regs | 2026-01414 | 2026-01-26 | Chesapeake Bay | Interior Department | Endangered and Threatened Wildlife and Plants; 90-Day Findings for 10 Species |   |
| 2026Q1 | EIS | 2026-04958 | 2026-03-13 | Talbot County | Environmental Protection Agency | Environmental Impact Statements; Notice of Availability |   |
| 2026Q1 | EIS | 2026-02362 | 2026-02-06 | Talbot County | Environmental Protection Agency | Environmental Impact Statements; Notice of Availability |   |
| 2026Q2 | Regs | 2026-10159 | 2026-05-21 | Chesapeake Bay | Homeland Security Department | Special Local Regulation; Lower Chesapeake Bay, Hampton Roads, and the Elizabeth River, Vi |   |
| 2026Q2 | EIS | 2026-06965 | 2026-04-10 | Talbot County | Environmental Protection Agency | Environmental Impact Statements; Notice of Availability |   |

_Artifact: `data/w3_candidates.json` (16 candidates)._
