# VA acquisition: census protocol step 3 (2026-10-15)

Operator: research sub-agent (Claude Opus 5.5), unattended. Scope: `UNIVERSE.md` as signed through
`../SCOPE-DECISIONS.md` (VA Q1–Q11, interval option (a) with its predeclared backward extension).
Rights: `../../rights/surfaces.json`; `va-register` and `va-register-rss` are at `2026-10-15.1`,
`va-agency-rulemaking` at `2026-10-15.4`. The primary's correction raised that surface to
`internal_originals` partway through this run, before any agency page was captured.
No commits were made by this operator. Enumeration (step 4) has not started.

**Round 2 (same day, 19:46–19:57Z)** carried out the primary's decisions: collect 41:25 and 41:26
under the backward stop rule, and attempt an independent cross-check for every remaining process.
Its changes are marked "Round 2" below. The owner sign-off list comes just before "Validator".

**Exit status:** `validate.py census/VA --stage manifest --verify-bytes` reports **10 errors**
(round 1: 12). All of them need owner signatures; none is a byte or linkage failure (see
"Validator"). History is now bounded by the stop rule (owner to confirm the Vol. 41 boundary).
Completeness is still **not established**: 6 process rows are single-lineage, and several
cross-checks are gap or unresolved.

## What was collected

All bytes went through `census/capture.py` (UA `DocketClock-research/0.1`, at least 5 s per host,
robots honoured, one connection at a time) into `~/yokel-captures/state-coverage`. None are in git.

| Batch | Contents | Results |
|---|---|---|
| b01 | RSS feed, Register home | 2 retrieved |
| b02 | stale deadlines page (Vol. 29), archive index, 42:12 TOC + PDF | 4 retrieved |
| b03 | 42:12 sections 4/5/6/8/10 + one details page (structure probe) | 6 retrieved |
| b04 | TOCs 42:04–43:04 (excl. 42:12) | 26 retrieved |
| b05 | interval PDFs + in-scope sections, 42:08–42:24 (excl. 42:12) | 99 retrieved |
| b06, b08 | TOCs 42:02, 42:03, 42:01 | 3 retrieved |
| b07, b09 | PDFs + sections for backward 42:01–42:07 and follow-up 42:25–43:04 | 80 retrieved |
| b10 | **dry-run only** (rights gate): agency route validated; Town Hall `/L/` refused `on_hold` | 0 network |
| b11–b17 | agency cross-check pages (DWR, DHP, DSS, DCJS, VDH, DEQ, MRC, DOE) | 15 retrieved, 3 refused |
| b18–b19 | **Round 2:** 41:25 and 41:26 TOC, PDF and in-scope sections | 14 retrieved |
| b20–b26 | **Round 2:** agency terms and rulemaking pages (DHP, DSS, Governor, virginia.gov policy, DPOR, VDACS, DOLI) | 17 retrieved, 1 HTTP 404 |

Round 2 totals: **51 network requests** including robots.txt and one redirect hop (16 to the
Register host, 35 to agency hosts). **31 originals retrieved** (6.5 MB; 2 PDFs with 270 pages).
0 LlamaParse. No 403, 429 or challenge. The DEQ, DOE and MRC hosts were not contacted again.

Round 1 totals: **254 network requests**, including robots.txt fetches (229 to `register.dls.virginia.gov`,
25 to agency hosts). **232 originals retrieved** (70.7 MB; 30 issue PDFs with 2,776 pages in
total). **0 used LlamaParse** (credit ledger 0). Network activity ran 2026-10-15
19:02:38Z–19:40:22Z (about 38 min). The whole step took about 1 h of agent time.

**Refusals (stopped by capture.py; never worked around):**

- `www.deq.virginia.gov`: **HTTP 403** on robots.txt.
- `www.doe.virginia.gov`: **HTTP 403** on robots.txt.
- `mrc.virginia.gov`: **TLS verification failed** (incomplete certificate chain), so robots
  policy was unknown and the host was stopped.

No 403 or 429 from the Register host. Town Hall `/L/` was never requested (held by robots).

## Unit design (how the expected units were derived)

- **Issue calendar.** RSS lists 472 issue items (25:01 2008-09-15 → 43:04 2026-10-05). They form an
  unbroken biweekly Monday sequence across the scoped range. `archive.aspx` (same lineage) lists the
  same voliss 41:01–43:04, and every PDF's page footer carries the same volume, issue and date. 43:05
  (2026-10-19) is not yet published. The "Publication Deadlines" nav page is stale (Vol. 29, 2012);
  each issue carries its own schedule.
- **Per issue: one `issue` entry plus its children.**
  - The `issue` entry is the official PDF (`volNN/issII/vNNiII.pdf`).
  - Its child is the TOC (`index`).
  - The TOC's children are one `page` entry per in-scope section the TOC links to:
    4 Petitions, 5 NOIRA, 6 Regulations, 7 Governor, 8 General Notices, 10 Periodic Reviews,
    11 Errata. Expected children = the count of those links. Terminal proof = the TOC's closing
    `divErrata` element (empty or linked).
  - Not units: type 1 (an entire-issue HTML duplicate of the sections), 2 (info page), 3 (schedule;
    printed in the PDF), 9 (guidance, out of scope).
  - Not units: per-item `details.aspx` views. Section pages carry the identical full bodies. One
    probe (`va-d-12188`) is kept and matches its section.
  - PDF pages are accounted by page count and locators inside the issue entry. No page-image entries
    were created.
- **Process rows** are Register sections, because one section page cannot be split across
  universe processes. All rows use agency_id `va-register-agencies`; the universe's agency column is
  "all agencies publishing in the Register". Mapping (**owner check**):

  | Process row | Universe processes it carries |
  |---|---|
  | `register-issue` | issue containers (RSS, home, archive, PDFs, TOCs); all processes |
  | `noira` | NOIRA |
  | `regulations` | proposed APA + exempt (incl. SCC orders), fast-track, final (reject), withdrawn, objection/extension notices, Governor additional-comment rounds if placed here |
  | `petitions` | petition initial notice + decision update |
  | `periodic-review` | periodic / small business impact review notices |
  | `general-notices` | early-stage informal comment (Q5), DMAS State Plan (excluded), enforcement/TMDL/permits/funding (excluded) |
  | `governor` | executive orders (excluded); possible Governor comment notices |
  | `errata` | corrections to deadlines or hearings (updates) |

## Interval: predeclared extension applied (owner confirm)

TOC labels for the signed 42:12–42:24 give **80** NOIRA + proposed + fast-track notices. The
universe's projection method adds 1.9 extras per issue, which gives 80 + 13 × 1.9 = **104.7 < 149**.
Applying the signed rule (extend backward by whole issues), counting by TOC labels only, before any
enumeration:

| Start issue | Issues | Notices | Projection |
|---|---|---|---|
| 42:12 | 13 | 80 | 104.7 |
| 42:11 | 14 | 89 | 115.6 |
| 42:10 | 15 | 96 | 124.5 |
| 42:09 | 16 | 118 | 148.4 |
| **42:08** | **17** | **131** | **163.3 ≥ 149** |

**Applied interval: `[2025-12-01, 2026-07-27)` America/New_York, Vol. 42 Iss. 08–24, 34 weeks.**
`UNIVERSE.md` was not edited. The manifest's `universe_version` is
`va-v0.1-signed-2026-10-15/interval-ext-42:08`.

Per-issue TOC label counts (N NOIRA, P proposed, F fast-track, W action withdrawn, Fi final,
O other; PDF pages):

| Issue | Date | N | P | F | N+P+F | W | Fi | O | pp. | Role |
|---|---|---|---|---|---|---|---|---|---|---|
| 41:25 | 2025-07-28 | 0 | 3 | 3 | 6 | 0 | 5 | 2 | 90 | backward (round 2) |
| 41:26 | 2025-08-11 | 1 | 5 | 10 | 16 | 0 | 17 | 7 | 180 | backward (round 2) |
| 42:01 | 2025-08-25 | 11 | 6 | 3 | 20 | 1 | 11 | 0 | 224 | backward |
| 42:02 | 2025-09-08 | 0 | 8 | 2 | 10 | 0 | 6 | 1 | 56 | backward |
| 42:03 | 2025-09-22 | 0 | 10 | 12 | 22 | 0 | 9 | 10 | 200 | backward |
| 42:04 | 2025-10-06 | 0 | 17 | 0 | 17 | 0 | 14 | 1 | 114 | backward |
| 42:05 | 2025-10-20 | 0 | 0 | 2 | 2 | 2 | 20 | 3 | 152 | backward |
| 42:06 | 2025-11-03 | 0 | 1 | 4 | 5 | 0 | 21 | 14 | 66 | backward |
| 42:07 | 2025-11-17 | 3 | 0 | 20 | 23 | 0 | 13 | 0 | 146 | backward |
| 42:08 | 2025-12-01 | 2 | 3 | 8 | 13 | 2 | 27 | 3 | 244 | interval |
| 42:09 | 2025-12-15 | 7 | 8 | 7 | 22 | 0 | 16 | 6 | 144 | interval |
| 42:10 | 2025-12-29 | 2 | 0 | 5 | 7 | 0 | 1 | 0 | 35 | interval |
| 42:11 | 2026-01-12 | 1 | 0 | 8 | 9 | 1 | 33 | 2 | 118 | interval |
| 42:12 | 2026-01-26 | 1 | 2 | 1 | 4 | 0 | 4 | 8 | 76 | interval |
| 42:13 | 2026-02-09 | 5 | 4 | 2 | 11 | 0 | 13 | 1 | 100 | interval |
| 42:14 | 2026-02-23 | 0 | 1 | 5 | 6 | 0 | 2 | 0 | 154 | interval |
| 42:15 | 2026-03-09 | 9 | 1 | 2 | 12 | 0 | 4 | 0 | 23 | interval |
| 42:16 | 2026-03-23 | 0 | 1 | 2 | 3 | 0 | 1 | 3 | 32 | interval |
| 42:17 | 2026-04-06 | 0 | 4 | 0 | 4 | 0 | 1 | 1 | 26 | interval |
| 42:18 | 2026-04-20 | 1 | 0 | 1 | 2 | 0 | 3 | 4 | 59 | interval |
| 42:19 | 2026-05-04 | 1 | 1 | 0 | 2 | 1 | 4 | 1 | 30 | interval |
| 42:20 | 2026-05-18 | 4 | 2 | 1 | 7 | 4 | 10 | 2 | 66 | interval |
| 42:21 | 2026-06-01 | 2 | 0 | 2 | 4 | 0 | 6 | 1 | 26 | interval |
| 42:22 | 2026-06-15 | 5 | 3 | 2 | 10 | 2 | 4 | 4 | 68 | interval |
| 42:23 | 2026-06-29 | 3 | 1 | 2 | 6 | 0 | 2 | 0 | 40 | interval |
| 42:24 | 2026-07-13 | 3 | 5 | 1 | 9 | 0 | 6 | 0 | 74 | interval |
| 42:25 | 2026-07-27 | 4 | 12 | 1 | 17 | 0 | 6 | 0 | 108 | follow-up |
| 42:26 | 2026-08-10 | 0 | 1 | 0 | 1 | 0 | 9 | 1 | 52 | follow-up |
| 43:01 | 2026-08-24 | 2 | 2 | 4 | 8 | 1 | 19 | 2 | 113 | follow-up |
| 43:02 | 2026-09-07 | 12 | 0 | 8 | 20 | 1 | 10 | 6 | 56 | follow-up |
| 43:03 | 2026-09-21 | 2 | 1 | 9 | 12 | 0 | 15 | 1 | 76 | follow-up |
| 43:04 | 2026-10-05 | 4 | 2 | 4 | 10 | 0 | 18 | 2 | 98 | follow-up |

These are TOC labels, not census results. Petitions, periodic reviews, general notices, hearings and
PDF-only items (below) are not in these counts.

## Backward search and follow-up horizon

- **Stop rule (signed):** stop at the first issue older than start − L − one cycle, where L is the
  largest publication→deadline/hearing lag among notices scanned so far.
  - L came from mechanical extraction of labelled fields ("Public Comment Deadline", "begins … and
    ends", petition "from … to", "Public Hearing Information", SCC "on or before") over all
    captured sections. These are accounting helpers, not labels.
  - Interval issues alone gave L = 78 d (SCC order, 42:03 s06, "on or before December 9, 2025").
  - Scanning 42:01 found **L = 99 d**: DHCD NOIRAs 13VAC5-21 and 13VAC5-95 (R26-8400/8401),
    "Public Comment Deadline: December 2, 2025", published 2025-08-25. These are themselves
    carry-ins.
  - Boundary = 2025-12-01 − 99 d − 14 d = **2025-08-10**, so the rule requires **41:26 and 41:25**.
- Round 1 stopped at the Vol. 42 floor and left 41:25 and 41:26 as gap entries.
- **Round 2 — primary decision (owner to confirm):** PROTOCOL step 2 sets the backward boundary by
  authority and archive evidence, not by an arbitrary cutoff. So the signed stop rule governs over
  the Vol. 42 floor, and 41:25 and 41:26 were collected: PDF, TOC and every in-scope section
  (41:26: s04, s05, s06, s08, s10; 41:25: s04, s06, s07, s08, s10; 14 requests).
  - **Carry-ins found: none.** The latest labelled deadline or hearing in either issue (HTML
    sections and full PDF text) is **2025-10-10** (41:26 s06, five proposed regulations, "Public
    Comment Deadline: October 10, 2025"). Nothing falls on or after 2025-12-01.
  - **L is unchanged at 99 d.** The largest lag in Vol. 41 is 60 d: 41:26 s06 (Oct 10) and 41:25
    s06 (Sep 26). Excluded: 41:25 s06's emergency-regulation continuation "through March 12, 2026",
    which is an effective period, not a participation deadline.
  - So the boundary stays **2025-08-10**. 41:25 (2025-07-28) is the first issue older than it, and
    **the rule terminates at 41:25**. No further issues are required, and `history_bounded` is now
    `true`. The owner item is `…/backward-boundary-41:25`.
  - The 41:25 and 41:26 TOCs list nothing missing from their sections, and both `divErrata`
    elements are empty. Their PDFs match the RSS dates (footers "July 28, 2025" and "August 11,
    2025").
  - 41:26 has no PDF-only items (33 = 33 Doc. Nos.). 41:25 has one HTML/PDF divergence (see
    "Cross-checks").
- Text layer: the 41:25 PDF is native (p2 rendered and verified blank). The 41:26 PDF is `partial`,
  and so is its s06 HTML. Failed regions:
  - p75: 3 formula images, 9VAC25-875 fee formula;
  - p134: 7 seal images, 18VAC10-20;
  - p168: 1 stricken seal image, 18VAC130-20.

  All three pages were rendered and inspected. None of the figures carries deadline text. The s06
  HTML embeds the same figures from `ris.dls` and `law.lis`; they were not retained.
- Excluded from L: a VDH funding notice (42:18 s08, 109 d; out of scope) and SCC effective dates
  and petition-decision meeting dates (not participation deadlines).
- **Follow-up horizon** is the second issue after the latest interval close. The latest observed
  is 42:24 + 61 d ≈ 2026-09-12 (SCC 42:23 order: 2026-09-11), so the horizon is 43:03/43:04. Both
  are captured, so the horizon is fully published. Follow-up events stay reported separately.

## Extraction test (text_layer), done during acquisition

macOS PDFKit (compiled Swift helper outside the repo; no installs) gave per-page character
counts, and CoreGraphics listed image XObjects per page.

- All 32 PDFs (30 in round 1, plus 41:25 and 41:26 in round 2) have native text on every content
  page. None is encrypted.
- Zero-text pages (p2 in most issues, some final pages) were **rendered and verified blank**
  layout pages and are listed in each entry's `evidence_refs`.
- p1 carries a decorative masthead image; the cover text is native.
- **9 PDFs are `partial`** (8 in round 1, plus 41:26 in round 2) because in-body figure regions have no text layer. Failed-region
  locators are logged in `expected.evidence_refs`:

  | Issue | Page(s) | Contents |
  |---|---|---|
  | 41:26 | p75, p134, p168 | 3 formula images; 7 seals; 1 stricken seal (round 2) |
  | 42:02 | p37 | seal |
  | 42:04 | p35–36 | small images |
  | 42:09 | p117 | |
  | 42:12 | p16 | 4 images |
  | 42:13 | p56 | 7 images |
  | 42:18 | p44 | sample seal |
  | 42:24 | p29 | Chesapeake Bay DO map |
  | 43:01 | p47 | |

- **9 HTML sections are `partial`**: 41:26 (round 2), 42:02, 42:04, 42:09, 42:12, 42:13, 42:18, 42:24 and 43:01,
  all `s06`. They embed external figure images that are not retained:
  - `ris.dls.virginia.gov` has no rights record;
  - `law.lis` is non-retained;
  - 42:18 s06 links a broken `file:///C:/Users/...` image.

  The figures exist in the official PDF.
- Under §4, both passes must use `rendered_image` or `both` for these 18 entries. Expected
  LlamaParse need is 0. No figure seen carries deadline text.

## Cross-checks

**Same lineage (`va-dlas`); these do not count as independent corroboration.**

- RSS date = TOC header date = PDF footer for all 32 issues.
- RSS and the archive index list the same voliss.
- TOC items vs section bodies: all found. 10 items are listed under a different section type or
  cited differently, and each was found by title.
- PDF vs HTML VA.R. Doc. No. sets: 22 issues match. **10 issues diverge** (9 in round 1, plus
  41:25 in round 2). The HTML views are rendered from the Register database and evidently reflect
  later state. **The official PDF is the controlling original.**
  - None of these is adjudicated here; they are human review items (`…/view-discrepancy-pdf-vs-html`).
  - Round 2 added both-side locators. "Absent" means the item is in no TOC or section entry of
    that issue. The same divergence is recorded as `unresolved` on both the PDF entry and the
    section entry, except for PDF-only rows, which are recorded on the PDF entry only.

  | Issue | Finding | PDF locator | HTML locator |
  |---|---|---|---|
  | 42:09 | **PDF-only Action Withdrawn**: Board of Optometry, R25-8047. Interval update | `va-42-09-pdf` p89 | absent (`va-42-09-toc`, all `va-42-09-s*`) |
  | 42:16 | **PDF-only action withdrawn**: Racing Commission, R24-7958. Interval update | `va-42-16-pdf` p9 | absent (`va-42-16-toc`, all `va-42-16-s*`) |
  | 42:23 | **PDF-only NOIRA**: DEQ, R26-8668, "Public Comment Deadline: July 29, 2026". **Interval opportunity absent from TOC/HTML** | `va-42-23-pdf` p7 | absent (`va-42-23-toc`, all `va-42-23-s*`) |
  | 42:03 | **HTML-only**: 4VAC15-240 Turkey proposed, R26-8442, deadline 2025-10-21. Not in the 42:03 PDF, but printed in the 42:04 PDF. Publication-issue ambiguity | not in `va-42-03-pdf`; printed `va-42-04-pdf` p15 | `va-42-03-s06` (and the 42:03 TOC) |
  | 42:13 | PDF R26-8565/R26-8564 ("Filed January 1, 0001") vs HTML R26-8690/8691 ("Filed January 15, 2026"). 8690/8691 recur in 42:24 and 42:23 | `va-42-13-pdf` p6–7 | `va-42-13-s05` |
  | 42:15 | PDF R24-04 vs HTML R25-7655, same final action, filed 2026-02-17 | `va-42-15-pdf` p20 | `va-42-15-s06` |
  | 42:21 | PDF R26-18 vs HTML R26-8657 | `va-42-21-pdf` p8 | `va-42-21-s05` |
  | 42:22 | PDF R26-8695 vs HTML "R0-8695" | `va-42-22-pdf` p50 | `va-42-22-s06` |
  | 43:04 | PDF R24-12 vs HTML R25-8045 | `va-43-04-pdf` p85 | `va-43-04-s06` |
  | 41:25 | **Round 2.** PDF "PFR21-33." vs HTML R22-7055: Board of Pharmacy final, 18VAC110-20, "Filed July 8, 2025, 1:29 p.m.". A final action, not a participation opportunity | `va-41-25-pdf` p80 | `va-41-25-s06` |

  **Implication for §4:** enumeration from HTML or TOC alone would miss in-scope items. Passes must
  inspect the PDFs.

**Independent lineage (`va-agency-*`).**

Round 2 attempted every remaining process. Terms were checked first on each new host, and the
DEQ, DOE and MRC refusals were left as final gaps. New entries are `va-xa-*` (b20–b26).

| Process | Agency attempts | Result | `single_lineage` |
|---|---|---|---|
| `regulations` | **DWR** (round 1). Terms OK. Its 2026–27 aquatic timeline corroborates the 12 4VAC15 proposals in 42:25 s06 (`matches`). The close dates **conflict** (`unresolved`; locators under "Temporal and source anomalies") | `independent_partial`: 1/58 agency units, unresolved | `false` |
| `general-notices` | **DPOR** (round 2; `coverage` 1/11 agency units matched). Terms OK: Web Policy limits only logo reproduction. The BPOR "Petition to Regulate Radon Professionals" page (`va-xa-dpor-radon`) matches the 42:21 s08 notice (`va-42-21-s08`): hearings June 16 and July 15, 2026; comments "on or before Thursday, July 16, 2026"; the agency open date June 1 equals the Register date. Hearing-room labels differ (location detail, not adjudicated). DPOR Licensees/Regulations has no dated history. DEQ, the most frequent s08 publisher, returned 403 in round 1 | `independent_partial`, 1 agency sample | `false` |
| `noira` | DEQ 403, DCJS and VDH homes (round 1). Round 2: DHP Board of Counseling (target 42:15 18VAC115 NOIRAs), VDACS home, policy and Board meetings (target 2VAC5 NOIRAs in 42:11, 42:20 and 42:21), DOLI home, disclaimer and Regulatory Information (target 42:23 16VAC15). Terms OK on all three. Every page defers to Town Hall and has no dated history | no lawful independent source found | `true` |
| `petitions` | MRC TLS, DOE 403 (round 1). Round 2: DHP Board of Medicine, the most frequent s04 petitioner board (42:08, 42:14, 42:16, 42:23). Terms OK (DHP Web Policy has no reuse restriction). It offers only a petition form and Town Hall pointers | no lawful independent source found | `true` |
| `periodic-review` | **DSS skipped on terms**: its Web Policy reads "You may use content under fair use. For other uses, email webdev@dss.virginia.gov". DSS (State Board of Social Services) is the most frequent s10 publisher. Its licensing periodic-review notices were the intended target and were not requested. DHP Board of Nursing (42:13, 42:16, 42:24 s10): no dated history | no lawful independent source found | `true` |
| `governor` | **Governor skipped on terms.** The home page's only policy link is the Commonwealth portal policy (`va-xa-gov-privacy`): "Permission is granted ... to make fair use of the contents". A guessed `/web-policy/` returned 404 (`va-xa-gov-webpolicy`, gap). The Executive Actions page lists EO-11, EO-12 and EO-16 to EO-18, which appear in 42:13, 42:14, 42:22 and 42:24 s07; it was **not requested** | skipped (fair-use-only terms) | `true` |
| `register-issue` | None possible. The Register is the sole publisher of its issue containers, and Town Hall `/L/` is held | no independent lineage exists | `true` |
| `errata` | None possible. Corrections are Register-internal | no independent lineage exists | `true` |

- **Terms skips (owner item `…/agency-terms-fair-use-skips`).** DSS and the Governor (via the
  virginia.gov policy) limit reuse to fair use. Under DECISIONS item 5 ("skip any that restrict
  reuse"), I treated that as restrictive. If the owner reads internal, non-republished retention
  as fair use, the Governor Executive Actions page is the strongest remaining candidate (one
  request) for `governor`.
  - Round 1 captured `va-xa-dss-home` before DSS terms were read. It is kept and flagged in its
    entry; the owner may direct a purge.
- DHP home, policies and laws/regulations pages (round 1) and the three DHP board pages (round 2)
  carry no dated regulatory history.
- Agency pages show **current** comment periods only, with no interval history. Town Hall `/L/`
  (held) remains the only plausible broad independent lineage.
- Agency-only opportunities exist outside the Register. Example: DWR public input periods
  2026-01-15 → 2026-02-14 and 2026-10-05 → 11-18. They are outside the declared universe, which
  covers Register-published items only. Noted for scope.

## Statute and roster lookups (read-only, not retained; law.lis, sequential)

**VAC agency index:** 24 titles and 152 agency codes, including abolished or repealed bodies.

| Title | Agencies | Title | Agencies | Title | Agencies | Title | Agencies |
|---|---|---|---|---|---|---|---|
| 1 | 11 | 7 | 3 | 13 | 3 | 19 | 3 |
| 2 | 4 | 8 | 19 | 14 | 3 | 20 | 1 |
| 3 | 2 | 9 | 5 | 15 | 2 | 21 | 1 |
| 4 | 9 | 10 | 1 | 16 | 7 | 22 | 10 |
| 5 | 1 | 11 | 4 | 17 | 3 | 23 | 1 |
| 6 | 7 | 12 | 5 | 18 | 37 | 24 | 10 |

The roster is the denominator check for which agencies may publish. It is not an expected-unit
source: the universe is defined by Register publication.

| Section | Verified |
|---|---|
| § 2.2-4007.01 | NOIRA, ≥30-day comment. Also: a hearing is required if **≥25 persons request one before the comment period closes**, which is a statutory-only request window. Under signed principle (count what the source states), it is recorded only when the notice states it |
| § 2.2-4007 | petitions: Register publication, 21-day comment, decision within 90 days after |
| § 2.2-4007.1 | periodic review: Register notice, ≥21-day comment |
| § 2.2-4012.1 | fast-track: comment ≤30 days, objection by 10 persons |
| § 2.2-4007.06 | 25-person request within 30 days of final publication (signed: excluded) |
| § 2.2-4011 | emergency effective on filing; NOIRA within 60 days only if continuing |
| § 2.2-4002 | exempt agencies must still comply with the Register Act (§ 2.2-4103) |

Corrections and notes on the universe's citations:

- § 2.2-4017 as read concerns Governor-directed executive-branch review. Its text does not set
  notice or comment; the Register notices cite it jointly with § 2.2-4007.1.
- The universe's statement that "the PDF version is the official legal resource (§ 2.2-4031 C)"
  comes from the **Register home page**. § 2.2-4031 C itself says only that the Register is
  published by posting on the Code Commission website.
- The § 2.2-4002 A 2 / A 3 reading for SCC and DWR was not confirmed verbatim (A 3 names the
  Department of Wildlife Resources).

## Temporal and source anomalies for the passes

- 18VAC85-80 (42:09 s06, PDF p86): "Public Comment Deadline: January 14, 2025" in an issue
  published 2025-12-15. The year is probably wrong; keep it as `conflicting` or `unknown`.
- 42:13 PDF "Filed January 1, 0001, 12:00 a.m." (placeholder filing time).
- **DWR close-date conflict** (not adjudicated; `…/dwr-close-date-conflict`):
  - Register: "Public Comment Deadline: August 17, 2026" for 12 4VAC15 proposals, all "Filed July
    07, 2026". Locators: `va-42-25-s06` (12 occurrences) and `va-42-25-pdf` p10, 16, 17, 18, 25,
    26, 27, 28, 30, 31 (12 occurrences).
  - Agency: `va-xa-dwr-aquatic-timeline`, "July 7–August 5, 2026 30-Day Public Comment Period on
    Board Proposals"
    (`dwr.virginia.gov/regulations/2026-2027-aquatic-wildlife-non-game-and-boating-regulatory-review-and-amendment-process-timeline/`).
  - The agency opened its period July 7, before Register publication on July 27. Publication is
    still the issue date per signed Q11.
- 41:25 Doc. No. divergence (round 2): Board of Pharmacy final. Locators are in the "Cross-checks"
  table.

## Owner sign-offs needed

Every C03 failure and every mandatory review ref in `run.json` is listed here, grouped so the owner
can sign in one sitting. Signing creates the human adjudication record the validator looks for.
**10 validator errors** and **16 run-level refs** (plus `completeness_review_ref`).

**A. Gap accepted** (validator C03, entry-level)

| Ref / entry | Item | Recommendation |
|---|---|---|
| `…/agency-xcheck-refused` → `va-xa-deq-home` | DEQ robots.txt HTTP 403 | Accept as a final gap. Not worked around; DEQ outreach is the only route |
| `…/agency-xcheck-refused` → `va-xa-doe-home` | DOE robots.txt HTTP 403 | Accept as a final gap |
| `…/agency-xcheck-refused` → `va-xa-mrc-home` | MRC TLS chain incomplete, so robots is unknown | Accept as a final gap. Verification is never disabled |
| `…/gov-terms-probe-404` → `va-xa-gov-webpolicy` | Guessed Governor terms URL returned 404 | Accept. Terms came from the linked portal policy instead |

**B. Single-lineage accepted** (validator C03, process-level)

| Ref | Process | Recommendation |
|---|---|---|
| `…/single-lineage-register-issue` | `register-issue` | Accept. There is no possible second publisher of Register issue containers |
| `…/single-lineage-errata` | `errata` | Accept. Corrections are Register-internal |
| `…/single-lineage-noira` | `noira` | Accept for Phase 1. DHP, VDACS and DOLI defer to Town Hall and DEQ refused. Revisit if VA outreach clears Town Hall `/L/` |
| `…/single-lineage-petitions` | `petitions` | Accept for Phase 1 (same reason; MRC and DOE are unreachable) |
| `…/single-lineage-periodic-review` | `periodic-review` | Accept, or reverse the DSS terms skip in group D, which could give one DSS sample |
| `…/single-lineage-governor` | `governor` | Accept, or reverse the Governor terms skip in group D, which needs one request to Executive Actions |

**C. Interval extension confirmed** (run-level)

| Ref | Item | Recommendation |
|---|---|---|
| `…/interval-extension-42:08` | Signed rule applied: 42:08 is the first start issue whose projection reaches ≥149 (163.3) → `[2025-12-01, 2026-07-27)`, 34 weeks | Confirm. The rule was applied mechanically from TOC labels, before enumeration |

**D. Backward boundary confirmed** (run-level)

| Ref | Item | Recommendation |
|---|---|---|
| `…/backward-boundary-41:25` | Primary decision: the stop rule governs over the Vol. 42 floor. 41:25–41:26 were collected, with no carry-ins and L unchanged at 99 d, so the rule terminates at 41:25 | Confirm. `history_bounded: true` rests on this |

**E. Other owner judgements** (run-level; no validator error, but `completeness_review_ref` waits on them)

| Ref | Item | Recommendation |
|---|---|---|
| `…/process-row-mapping` | Section-based process rows | Confirm. One section page cannot be split across processes |
| `…/regulations-single-agency-independence` | `regulations` is `independent_partial`: 1 of 58 agency units checked (DWR, follow-up issue), unresolved, 0 corroborated | Accept the partial label. It is a lineage-existence check, not coverage evidence |
| `…/general-notices-single-agency-independence` | `general-notices` is `independent_partial`: 1 of 11 agency units corroborated (DPOR, 42:21) | Accept the partial label. DEQ (17 of the notices) is unreachable |
| `…/agency-terms-fair-use-skips` | DSS and Governor skipped on fair-use-only terms; one DSS home page captured before terms were read | Confirm the skips. Decide whether to purge `va-xa-dss-home` |
| `…/view-discrepancy-pdf-vs-html` | 10 issues with PDF/HTML Doc. No. divergences (table above, both-side locators) | Route to the human review pass. Passes must read the PDFs (one PDF-only interval NOIRA, 42:23) |
| `…/dwr-close-date-conflict` | Aug 5 (agency) vs Aug 17 (Register) | Route to temporal review. Do not adjudicate in acquisition |

## Validator

```
$ python3 census/validate.py census/VA --stage manifest --verify-bytes   # round 2
SKIP schema validation: jsonschema not importable; cross-record checks still run.
C03 coverage va-register-agencies/regulations: independent_partial; universe=58 expected=1 matched=0 mismatched=0 unresolved=1 uncovered=57
C03 coverage va-register-agencies/general-notices: independent_partial; universe=11 expected=1 matched=1 mismatched=0 unresolved=0 uncovered=10
FAIL C03: va-xa-deq-home gap/pending needs human review
FAIL C03: va-xa-mrc-home gap/pending needs human review
FAIL C03: va-xa-doe-home gap/pending needs human review
FAIL C03: va-xa-gov-webpolicy gap/pending needs human review
FAIL C03: register-issue needs independent lineage or reviewed single_lineage
FAIL C03: noira needs independent lineage or reviewed single_lineage
FAIL C03: governor needs independent lineage or reviewed single_lineage
FAIL C03: petitions needs independent lineage or reviewed single_lineage
FAIL C03: periodic-review needs independent lineage or reviewed single_lineage
FAIL C03: errata needs independent lineage or reviewed single_lineage
10 error(s).
```

- Round 1 reported 12 errors. Collecting Vol. 41 cleared the 2 Vol. 41 gaps, and DPOR cleared
  `general-notices`. The Governor terms 404 added 1.
- **The validator changed during this round.** The primary's commit `46128d6` (census protocol r3:
  scoped cross-check coverage) changed `validate.py` and `run.schema.json`. It no longer lets one different-lineage edge make a
  whole process independent. Rows that are not single-lineage now need an explicit `coverage`
  block.
  - `regulations` and `general-notices` now carry `coverage.mode: independent_partial` and
    `unit_kind: agency_process`. Their universe is the agencies named in the interval section
    headers: 58 agencies publish in s06 and 11 in s08. These counts are acquisition-time
    accounting, not an enumeration.
  - `regulations`: the DWR unit is **unresolved**, not matched, because the date conflicts and the
    sample is a follow-up issue. That gives 0 corroborated units and no agency claim.
  - `general-notices`: the DPOR unit is matched, and its claim is that one agency.
  - Both rows have `completeness: not_established`.
  - Without these blocks the new validator reports 12 errors. The 2 extra errors are
    "independent claim requires explicit coverage".
- No C01, C02 or C10 failures. All 263 retrieved entries' bytes (267 entries in the manifest) were
  re-hashed and matched against their sidecars.
- Round 2's new entries have the same key set as the existing entries, and every enum value is
  allowed by `manifest.schema.json`.
- jsonschema is not installed. A stdlib structural check of `manifest.schema.json`,
  `run.schema.json` and `sidecar.schema.json` found 0 errors. It caught 3 of 3 errors injected in a
  negative test.
- The 10 failures need human adjudication records. An agent cannot create them.
