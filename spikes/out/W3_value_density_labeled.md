# W3 — In-basin value density (LABELED)

**Labeled:** 2026-06-14 · resolves the pending hand-label of `W3_value_density.md`.
**Basin:** HUC-8 `02060005` Choptank (DE/MD) · **Window:** last 4 quarters (2025-07-01 → 2026-06-14)
**Method:** each of the 16 upper-bound candidates labeled `in_basin?` (does the text place it in the
Choptank HUC-8, not merely mention a keyword) and `novel?` (a window the org wouldn't already know).
Ambiguous EIS/drawbridge rows resolved by fetching FR raw text (keyless).

## Death line
`≳ a handful/quarter with EIS a meaningful share` → GO; `~2–3/quarter or EIS share ≈ 0` → STOP.

## Labeled candidate sheet

| quarter | bucket | FR doc # | matched kw | title (short) | in_basin? | novel? | why it dropped |
| --- | --- | --- | --- | --- | :---: | :---: | --- |
| 2025Q3 | Regs | 2025-18634 | Chesapeake Bay | Safety Zone; Chesapeake Bay, Baltimore MD | N | — | Baltimore/Patapsco, not Choptank HUC-8 |
| 2025Q3 | Regs | 2025-16354 | Chesapeake Bay | Safety Zone; Chesapeake Bay, Baltimore MD | N | — | Baltimore/Patapsco, not Choptank HUC-8 |
| 2025Q3 | Regs | 2025-18816 | Chesapeake Bay | Water Quality Standards — Delaware River | N | — | Delaware River; Chesapeake is incidental mention |
| 2025Q3 | Regs | 2025-16933 | Chesapeake Bay | ESA; Five Species Not Warranted | N | — | National ESA finding |
| 2025Q3 | Regs | 2025-15703 | Chesapeake Bay | Migratory Bird Hunting Frameworks | N | — | National framework |
| 2025Q4 | Regs | 2025-19806 | Chesapeake Bay | Marine Mammals; Atlantic Fleet Training & Testing | N | — | Atlantic-wide |
| 2025Q4 | Regs | 2025-20402 | Chesapeake Bay | Updated Definition of “WOTUS” | N | — | National rule |
| 2026Q1 | Regs | 2026-01400 | Tuckahoe | Drawbridge; Removal of Obsolete Regs | N | — | National bulk removal of 81 obsolete drawbridges nationwide |
| 2026Q1 | Regs | 2025-24203 | Chesapeake Bay | Harbor Porpoise Take Reduction; gillnet | N | — | Mid-Atlantic/Gulf-of-Maine gillnet, not Choptank |
| 2026Q1 | Regs | 2026-01414 | Chesapeake Bay | ESA; 90-Day Findings for 10 Species | N | — | National ESA finding |
| 2026Q2 | Regs | 2026-10159 | Chesapeake Bay | Special Local Reg; Lower Chesapeake Bay, Hampton Roads VA | N | — | Virginia, out of basin |
| 2026Q1 | EIS | 2026-01874 | Chesapeake Bay | EIS NOA → No. 20250190 Chesapeake Bay Crossing Study | N | N | Bay Bridge study: mainstem bay (not Choptank HUC-8); high-profile, not novel; dup of 2026-01267 |
| 2026Q1 | EIS | 2026-01267 | Chesapeake Bay | EIS NOA → No. 20250190 Chesapeake Bay Crossing Study | N | N | Same EIS as 2026-01874 (consecutive weekly NOA) |
| 2026Q1 | EIS | 2026-04958 | Talbot County | EIS NOA → No. 20260024 Dresden–Talbot County 500 kV | N | — | **Talbot County, GEORGIA** (USDA, GA) — wrong county |
| 2026Q1 | EIS | 2026-02362 | Talbot County | EIS NOA → No. 20260008 Dresden–Talbot County 500 kV | N | — | **Talbot County, GEORGIA** — wrong county |
| 2026Q2 | EIS | 2026-06965 | Talbot County | EIS NOA → No. 20260024 Dresden–Talbot County 500 kV | N | — | **Talbot County, GEORGIA** (dup of 2026-04958) |

## Recomputed counts

| metric | upper-bound (pre-label) | **confirmed (post-label)** |
| --- | ---: | ---: |
| in-basin candidates total | 16 | **0** |
| …per quarter | ~4.0 | **0** |
| EIS share | 31% (5 of 16) | **0 (0 EIS)** |
| distinct in-basin novel windows | — | **0** (1 if the Bay Crossing Study is counted, but it fails *novel*) |

## Verdict

**STOP (measured).** The upper-bound count of ~4/quarter collapses to **0 confirmed novel in-basin
windows** over four quarters — below the 2–3/quarter death line. The 16 candidates were entirely:
national/regional rules that merely name "Chesapeake Bay" (11), a nationwide drawbridge-cleanup rule
(1), the **wrong Talbot County (Georgia)** (3 hits / 2 distinct EIS), and the high-profile Bay Bridge
crossing study appearing twice (2 hits / 1 EIS, not novel, not Choptank-proper).

### Root cause
"Chesapeake Bay" is far too broad for a single HUC-8: the whole bay watershed dwarfs the Choptank
sub-basin, so the term guarantees out-of-basin hits. The *tight* in-basin terms (Choptank, Tuckahoe,
Tred Avon, Marshyhope, the four counties) produced **zero** true in-basin rulemakings/EIS — the only
tight-term hits were a Georgia county collision and a nationwide cleanup rule.

### Caveat (one honest gap)
FR-only. The Mirrulations/spicy-regs Regs.gov cross-check (`SPICY_REGS_PARQUET`) was never wired in,
so a pure Regs.gov docket that never surfaces in FR full text with these phrases could be missed.
But the keyword lexicon covers the basin name, all major tributaries, and all four counties — an
in-basin action would almost certainly name one — so recall is unlikely to hide a *handful*/quarter.

### Implication for the wedge
W3 was the business kill-shot. Labeled, it reads **red**, not provisional-green. This is the
"measured no" the week was designed to surface: a single-HUC-8 wedge does not clear the value-density
death line on federal data alone. Before abandoning the vertical entirely, the only thing that could
move this is (a) the Regs.gov parquet cross-check above, or (b) widening the geography from one HUC-8
to a multi-basin region — which changes the product thesis.

_Source artifacts: `data/w3_candidates.json`; FR raw text fetched live for the 6 ambiguous rows._
