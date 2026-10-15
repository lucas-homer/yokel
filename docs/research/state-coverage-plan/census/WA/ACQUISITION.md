# WA acquisition: protocol step 3 (account for every expected source unit)

Operator: research sub-agent (Claude Opus 5.5), 2026-10-15. Protocol v1.2 (r3 coverage rules).
Universe: `UNIVERSE.md` v0.1, signed via `../SCOPE-DECISIONS.md` (WA answers) and
`../../rights/DECISIONS.md` items 1–16. Manifest `universe_version`: `wa-v0.1+scope-signed-2026-10-15`.
**Step 4 (enumeration) has not started.** No candidate opportunities were labelled. Counts below
are source-unit accounting only.

## Result

`python3 census/validate.py census/WA --stage manifest --verify-bytes` exits 1 with **59 errors,
all C03 "needs human review"**:

- 52 gap entries, grouped under 38 named review references. Every gap is listed below.
- 7 single-lineage process rows that still need an owner reference.

There are no C01, C02 or C10 errors. Every retrieved entry's bytes, hash, length and sidecar
linkage verify. These errors cannot clear before an owner writes human adjudication records, which
an agent cannot sign. jsonschema is not installed, so the validator skips schema checks. A stdlib
subset checker (`tools/minischema.py`) reports 0 schema errors for `manifest.jsonl` and `run.json`.

| kind | retrieved | missing | not_attempted |
|---|---|---|---|
| issue | 21 | – | 2 (26-20, 26-21: not yet published) |
| index | 84 | – | – |
| agency_roster | 1 | – | – |
| attachment | 2,700 | 32 (16 sequence holes × htm/pdf) | – |
| portal_slice (agency cross-checks) | 7 | – | 5 (4 terms skips + Ecology) |
| **total 2,852** | 2,813 | 32 | 7 |

Completeness: 2,800 entries `accounted`, 52 `gap`.

## What was enumerated and how expected counts were derived

- **Issue calendar.** Publication dates come from column 4 ("Publication Date") of the Code
  Reviser closing-date calendars (`wa-calendar-25-23`, `-26-11`, `-26-19`). They confirm the
  universe's inferred dates: 25-23 = 2025-12-03, 25-24 = 2025-12-17, 26-10 = 2026-05-20,
  26-11 = 2026-06-03, 26-12 = 06-17, 26-13 = 07-01, 26-14 = 07-15, 26-15 = 08-05, 26-16 = 08-19,
  26-17 = 09-02, 26-20 = 10-21, 26-21 = 11-04. `WsrByIssue.htm` links 2026 issues 01–19; 20–24
  are unlinked (not yet published).
- **Per-issue units.** One `issue` entry per issue page. Its children are:
  - the type indexes `WSRNN-IITYPE.htm`;
  - in interval issues, the 8 certified section PDFs (PREP, PROP, EXPE, PERM, EMER, MISC, TABLE,
    INDEX);
  - every filing numbered in that issue, as HTML plus certified PDF (`wsrpdf/`);
  - embedded PNG attachments of filing HTML;
  - explicit entries for sequence holes.

  `expected_children` equals that planned set.

  | cohort | issues | Register types collected | filings (×2 formats) |
  |---|---|---|---|
  | interval | 26-11…26-16 | all six | 613 distinct WSR numbers (MISC 162, PERM 123, PREP 116, PROP 113, EMER 86, EXPE 13) |
  | carry-in backward search | 25-23…26-10 | PREP, PROP, EXPE | 510 (PREP 232, PROP 220, EXPE 58) |
  | follow-up | 26-17…26-19 | PROP, EXPE, MISC | 139 (MISC 76, PROP 57, EXPE 6) |

  In the backward search, "candidate carry-ins" was applied mechanically. Every CR-101,
  CR-102-family and CR-105 filing within the statutory boundary was collected, because index
  hearing dates are metadata only and say nothing about comment closes. PERM, EMER and MISC filings
  in backward issues are outside the signed universe and were not collected.
- **Universe count vs filings.** The universe's "616 issue rows" sum distinct numbers per issue.
  Four interval holdovers (26-12-053, 26-12-061, 26-13-025, 26-13-101) are listed in two interval
  issues. Deduped, that leaves 613 distinct filings, including two backward-numbered holdovers
  listed in interval issues (26-09-129, 26-10-027) that are captured as interval units. Rows
  repeat per co-filing agency (for example DSHS plus a sub-administration), so all accounting
  dedupes by WSR number.
- **Filing-number sequences and terminal proof.** For every captured issue, numbers 1…max must
  appear on its own issue page or as a holdover in a later one.
  - **16 numbers are listed nowhere** in 25-23…26-19. Both direct URLs (htm and pdf) return HTTP
    404, so each is an explicit `missing` gap: 25-23-096, 25-24-067, 26-01-144, 26-01-146,
    26-04-106, 26-08-070, 26-12-045, 26-13-090, 26-13-114, 26-14-089, 26-14-099, 26-17-064,
    26-18-006, 26-18-087, 26-19-020 and 26-19-022. Likely void or unused numbers, but that is
    unproven.
  - Terminal probes of max+1 for each interval issue (26-11-069, 26-12-083, 26-13-120,
    26-14-124, 26-15-132, 26-16-093) all return 404. They are recorded as issue
    `terminal_evidence_refs`, not as manifest units.
  - Suffix number 26-16-026A (L&I PROP) is listed on the issue page and present in the section
    PDF (p.11), but is absent from `WSR26-16PROP.htm`. That is the only index discrepancy (gap).
- **The holdover effect.** A holdover filing is listed on its numbering issue's page **and**,
  marked "holdover", on a later issue's page. Its body URL stays under the numbering issue.
  Section-PDF page headers show the filing printed **in full, including the "Original Notice"
  cover, in both issues**:

  | filing | first printed | reprinted |
  |---|---|---|
  | 26-09-129 | 26-09 PROP pp.287–291 | 26-11 PROP pp.1–2 |
  | 26-10-027 | 26-10 | 26-12 |
  | 26-12-053 | 26-12 pp.108–109 | 26-13 pp.1–2 |
  | 26-16-075 | 26-16 pp.70–71 | 26-17 (58 pp.) |

  Body entries are children of the numbering issue, and the later listing is recorded in their
  evidence refs. **Consequence for scope:** by the earliest-publication rule, 26-09-129 (hearing
  June 23) and 26-10-027 (Columbia River Gorge Commission, excluded) are carry-in candidates, not
  new interval notices. This is review case `wa-holdover-double-publication`. The universe note
  that 26-17-052 "is listed in issue 26-19 as holdover" is right, but it is also listed in 26-17.
- **Roster.** `AgencyWac.htm` is captured as the roster authority. Filers are grouped as follows:
  - `wa-state-agencies` (default);
  - `wa-local-clean-air` (name contains "Clean Air" or "Air Pollution"; SCOPE Q2a exclusion);
  - `wa-columbia-river-gorge-commission` (Q2b exclusion);
  - `wa-code-reviser` for containers (issues, indexes, sections, calendars, roster).

  Per-agency coverage units in `run.json` use each filing's first-listed agency.
- **Process IDs** follow the Register section, because the stage within a section is an
  enumeration question:
  - `cr102-proposal-family` (PROP: originals, supplementals, continuances, withdrawals);
  - `cr105-expedited`, `cr101-preproposal`, `misc-filings`;
  - `cr103p-permanent` and `cr103e-emergency` (excluded; inspected as closure evidence and
    exclusion strata only).
- **Content identity.** Each filing's HTML and certified PDF were compared on the WSR number and
  the `[Filed …]` stamp: 0 mismatches. Every interval filing appears in its certified section
  PDF's page headers, and all 54 captured section PDFs match their issue-page rows exactly. All 81
  type indexes match their issue pages except 26-16-026A (above).
- **Statute check.** Read-only and not retained: RCW 34.05.335(3) says the 180-day lapse runs from
  "publication of the text as last proposed". A supplemental therefore restarts the clock, but it
  is itself a Register filing inside the searched window. The backward boundary 25-23…26-10
  (one issue of margin before 2025-12-05) holds.

## Extraction test (no LlamaParse called; 0 credits used)

- Native text is present on every page of every PDF: 1,335 PDF entries, 13,296+ pages, no page
  under 40 native characters. Short pages are filing end-pages.
- **Image regions** (embedded image XObjects found by CoreGraphics) are logged as
  `text-extract-fail:<entry>#page=N region=embedded-image` locators in `expected.evidence_refs`.
  There are 370 locators:
  - 87 on per-filing PDF pages;
  - 49 on section PDFs (duplicates of the filing pages);
  - 117 PNG attachment units (`format: mixed`, `text_layer: none`);
  - 117 matching `<img>` regions in 16 filing HTMLs.

  Affected entries carry `text_layer: partial`: 23 PDFs and 16 HTMLs, for example 26-14-100
  (26 image pages, 33 PNGs), 26-15-073, 26-10-068…072 and 26-09-004. Both passes must use
  `rendered_image` or `both` on these.
- **LlamaParse estimate if needed:** at most ~87 unique filing pages × 10 ≈ 870 credits. That is
  likely far fewer once restricted to pages near deadline or hearing text, since most images are
  figures, maps and fee tables. Note that DECISIONS item 16 reallocated WA's unused envelope to
  MS, so the primary must confirm what WA reserve remains before any dispatch.

## Cross-checks per process (independent lineage)

Agency terms were checked first (non-retained reads, 2026-10-15), per DECISIONS item 5:

| agency | decision | evidence |
|---|---|---|
| L&I | **used** | Privacy and security statement: content "is considered public information … may be copied, downloaded, or distributed" |
| HCA | **used** | No reuse restriction located (website privacy policy; no site terms page found). Owner may wish to confirm |
| DOL | skipped | Conditions of use bar exploiting information "for commercial purposes" |
| WDFW | skipped | Copying limited to informational, non-commercial use with a reproduction disclaimer |
| DOH | skipped | Some content third-party; reuse needs webmaster permission |
| DCYF | skipped | Some photos/text belong to others; reuse requests go to communications |
| Ecology | not collected | Pointer-only (`wa-ecology-pointers` on hold) |

The first attempt was refused by capture.py ("original retention not authorized") under
`surfaces.json` 2026-10-15.2. The primary's correction to 2026-10-15.4 enabled retention, and
seven pages were then captured: six HCA rule-making pages and the L&I rule-making activity index.

**Reverse check.** Every interval WSR number cited on those pages resolves to a Register filing by
the same agency. These include PREP and PERM filings outside the coverage processes. No
agency-only (unlisted) filing was found. Forward results, by `run.json` coverage
(`independent_partial`, `unit_kind: proceeding`, unit = one WSR filing number, state agencies
only):

| process | universe | expected (HCA + L&I) | matched | unresolved | uncovered |
|---|---|---|---|---|---|
| cr101-preproposal | 116 | 21 | 11 (HCA) | 10 | 95 |
| cr102-proposal-family | 106 | 15 | 4 (HCA 26-12-021, 26-13-038, 26-14-055, 26-15-023) | 11 | 91 |
| cr105-expedited | 13 | 3 | 0 | 3 | 10 |

Two limits apply to these matches:

- **Pages are rolling.** Absence from a page is "unresolved", not a mismatch. L&I's index cites AO
  dockets rather than WSR numbers, so all 7 L&I units are unresolved.
- **Matching is on existence and agency only.** Dates were not compared at step 3.

`claim_agency_ids` is empty and completeness is `not_established`. The remaining process rows are
`single_lineage: true` with the placeholder `PENDING-OWNER-REVIEW:wa-single-lineage`:

- `misc-filings`, `cr103p-permanent`, `cr103e-emergency`;
- the local clean-air and Columbia River Gorge Commission exclusion rows;
- `register-accounting`.

## Gaps needing owner review (all `PENDING-OWNER-REVIEW:wa-*`)

1. `sequence-hole-*` (16) plus the matching `issue-incomplete-*` (11 issues): numbers listed
   nowhere, 404 on both URLs. Confirm void numbers with the Code Reviser, or accept as void.
2. `index-discrepancy-26-16-PROP` plus `issue-incomplete-26-16`: 26-16-026A missing from the PROP
   type index.
3. `followup-not-published-26-20` and `-26-21`: publish on 10-21 and 11-04. Capture them, then
   re-run step 3 for the follow-up horizon. The 26-15/26-16 follow-up is incomplete until then.
4. `agency-terms-skip-{doh,dol,wdfw,dcyf}`: skipped on terms. The owner may override if internal
   retention is acceptable under non-commercial terms.
5. `ecology-pointer-only`.
6. `single-lineage`: 7 rows.
7. `holdover-double-publication`: this is not a manifest gap but a step-5 mandatory review, and is
   listed in `run.json mandatory_review_refs`.

## Requests, time and refusals

- **Capture runs.** 9 capture.py batches (`requests/01…09`, `capture-results/01…09`) with 2,857
  requests and 2,868 HTTP attempts, including 11 robots.txt fetches. All were sequential on
  `wa-register` and `wa-agency-rulemaking` surfaces at ≥5 s per host, unattended.
- **Elapsed time.** 2026-10-15T19:02:58Z → 23:37:48Z (4 h 35 m).
- **Outcomes.** All 2,813 non-probe requests were retrieved, along with the 6 holdover section
  PDFs. The 44 sequence probes returned 404 as expected. There were no 403s, 429s, challenges or
  stopped hosts.
- **Storage.** About 367 MB of WA originals are in `~/yokel-captures/state-coverage`. No bodies
  are in git: capture results hold headers and metadata only.
- **Non-retained reads.** 8 WebFetch reads (RCW 34.05.335; agency terms pages) and 8 WebSearch
  queries. None were retained or entered in the manifest.
- **Refused.** One dry-run gate refusal on agency retention under 2026-10-15.2 (above). Nothing was
  worked around.
- **Credit ledger.** WA actual 0, outstanding 0.

## Notes for the primary

- `run.json`:
  - `brief_sha256`, `brief_frozen_at`, `audit.seed` and `audit.frame_hash` are `null`, with
    `frozen_before_seed: false` (protocol r3 planning state).
  - `passes`, `crosswalk` and `temporal_log` are empty.
  - `credits` lists WA/CT/VA/TN at 0. The primary owns the shared ledger.
- The manifest is about 6.6 MB because of per-entry evidence refs and agency cross-check edges.
- `tools/` holds the builder and helpers used here. They are not production code and expect
  scratch inputs under `/tmp/wa-acq`, so they are reproducible only with those regenerated.
- Hint for passes (not a label): several notices open comment windows **before** their
  publication date. For example, 26-09-129's comments begin April 22, but it was published May 6
  and reprinted June 3.
