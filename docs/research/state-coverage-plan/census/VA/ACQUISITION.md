# VA acquisition: census protocol step 3 (2026-10-15)

Operator: research sub-agent (Claude Opus 5.5), unattended. Scope: `UNIVERSE.md` as signed through
`../SCOPE-DECISIONS.md` (VA Q1–Q11, interval option (a) with its predeclared backward extension).
Rights: `../../rights/surfaces.json`; `va-register` and `va-register-rss` are at `2026-10-15.1`,
`va-agency-rulemaking` at `2026-10-15.4`. The primary's correction raised that surface to
`internal_originals` partway through this run, before any agency page was captured.
No commits were made by this operator. Enumeration (step 4) has not started.

**Exit status:** `validate.py census/VA --stage manifest --verify-bytes` reports **12 errors**. All
of them need owner signatures; none is a byte or linkage failure (see "Validator").
Completeness is **not established**, because history is not bounded, 7 process rows are
single-lineage and several cross-checks are gap or unresolved.

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

Totals: **254 network requests**, including robots.txt fetches (229 to `register.dls.virginia.gov`,
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
- The signed universe says that if the rule cannot terminate inside Vol. 42, carry-in
  completeness is **unresolved**. I did **not** collect Vol. 41. 41:25 and 41:26 are named gap
  entries (`not_attempted`, review ref `…/backward-search-vol41`), and `history_bounded: false`.
  Rights allow collection: about 16 requests for those two issues. Owner item.
- Excluded from L: a VDH funding notice (42:18 s08, 109 d; out of scope) and SCC effective dates
  and petition-decision meeting dates (not participation deadlines).
- **Follow-up horizon** is the second issue after the latest interval close. The latest observed
  is 42:24 + 61 d ≈ 2026-09-12 (SCC 42:23 order: 2026-09-11), so the horizon is 43:03/43:04. Both
  are captured, so the horizon is fully published. Follow-up events stay reported separately.

## Extraction test (text_layer), done during acquisition

macOS PDFKit (compiled Swift helper outside the repo; no installs) gave per-page character
counts, and CoreGraphics listed image XObjects per page.

- All 30 PDFs have native text on every content page. None is encrypted.
- Zero-text pages (p2 in most issues, some final pages) were **rendered and verified blank**
  layout pages and are listed in each entry's `evidence_refs`.
- p1 carries a decorative masthead image; the cover text is native.
- **8 PDFs are `partial`** because in-body figure regions have no text layer. Failed-region
  locators are logged in `expected.evidence_refs`:

  | Issue | Page(s) | Contents |
  |---|---|---|
  | 42:02 | p37 | seal |
  | 42:04 | p35–36 | small images |
  | 42:09 | p117 | |
  | 42:12 | p16 | 4 images |
  | 42:13 | p56 | 7 images |
  | 42:18 | p44 | sample seal |
  | 42:24 | p29 | Chesapeake Bay DO map |
  | 43:01 | p47 | |

- **8 HTML sections are `partial`**: 42:02, 42:04, 42:09, 42:12, 42:13, 42:18, 42:24 and 43:01,
  all `s06`. They embed external figure images that are not retained:
  - `ris.dls.virginia.gov` has no rights record;
  - `law.lis` is non-retained;
  - 42:18 s06 links a broken `file:///C:/Users/...` image.

  The figures exist in the official PDF.
- Under §4, both passes must use `rendered_image` or `both` for these 16 entries. Expected
  LlamaParse need is 0. No figure seen carries deadline text.

## Cross-checks

**Same lineage (`va-dlas`); these do not count as independent corroboration.**

- RSS date = TOC header date = PDF footer for all 30 issues.
- RSS and the archive index list the same voliss.
- TOC items vs section bodies: all found. 10 items are listed under a different section type or
  cited differently, and each was found by title.
- PDF vs HTML VA.R. Doc. No. sets: 21 issues match. **9 issues diverge.** The HTML views are
  rendered from the Register database and evidently reflect later state. **The official PDF is the
  controlling original.**

  | Issue | Finding | Locator |
  |---|---|---|
  | 42:09 | **PDF-only Action Withdrawn**: Board of Optometry, R25-8047. No TOC item, no HTML entry (interval update) | PDF p89 |
  | 42:16 | **PDF-only action withdrawn**: Racing Commission, R24-7958 (interval update) | PDF p9 |
  | 42:23 | **PDF-only NOIRA**: DEQ, R26-8668, "Public Comment Deadline: July 29, 2026" (**interval opportunity absent from TOC/HTML**) | PDF p7 |
  | 42:03 | **HTML-only**: 4VAC15-240 Turkey proposed, R26-8442, deadline 2025-10-21. In the 42:03 TOC/s06 but not the 42:03 PDF; printed in the 42:04 PDF (p15). Publication-issue ambiguity | 42:03 s06; 42:04 PDF p15 |
  | 42:13 | PDF R26-8565/R26-8564 ("Filed January 1, 0001") vs HTML R26-8690/8691 ("Filed January 15, 2026"). 8690/8691 recur in 42:24 and 42:23 | PDF p6–7 |
  | 42:15 | PDF R24-04 vs HTML R25-7655 | PDF p20 |
  | 42:21 | PDF R26-18 vs HTML R26-8657 | PDF p8 |
  | 42:22 | PDF R26-8695 vs HTML "R0-8695" | PDF p50 |
  | 43:04 | PDF R24-12 vs HTML R25-8045 | PDF p85 |

  **Implication for §4:** enumeration from HTML or TOC alone would miss in-scope items. Passes must
  inspect the PDFs.

**Independent lineage (`va-agency-*`).**

| Process | Status |
|---|---|
| `regulations` | **DWR**: terms checked (privacy/linking policy, no reuse restriction). Its 2026–27 aquatic timeline ("July 7–August 5, 2026 30-Day Public Comment Period on Board Proposals") corroborates the existence of the 12 4VAC15 proposals in 42:25 s06 (`matches`, all "Filed July 07, 2026"). But the **close dates conflict**: agency Aug 5 vs Register "Public Comment Deadline: August 17, 2026" (`unresolved`, needs temporal review). One agency's sample, from a follow-up issue, makes this row pass the validator's independence check; whether one sample suffices for an all-agency row is an **owner item**. `single_lineage: false`. |
| `noira` | DEQ 403; DCJS and VDH homes captured, no history pages pursued. `single_lineage: true`, placeholder review |
| `petitions` | MRC TLS failure; DOE 403. `single_lineage: true` |
| `periodic-review` | DSS home only. `single_lineage: true` |
| `register-issue`, `general-notices`, `governor`, `errata` | no independent source attempted. `single_lineage: true` |

- DHP: home, policies and laws/regulations pages carry no dated regulatory history and are not
  usable.
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
- DWR close-date conflict (above). The agency opened its comment period July 7, before Register
  publication on July 27; publication is still the issue date per signed Q11.

## Gaps and owner items (validator failures map 1:1)

1. **Backward search into Vol. 41** (41:25, 41:26). Authorize about 16 requests, or accept that
   carry-in history is unresolved.
2. **Refused agency hosts**: DEQ 403, DOE 403, MRC TLS. Accept them as gaps, or arrange access.
3. **Single-lineage acceptance** for 7 process rows: register-issue, noira, petitions,
   periodic-review, general-notices, governor, errata.
4. Confirm the **predeclared interval extension** to 42:08 (`[2025-12-01, 2026-07-27)`).
5. Confirm the **section-based process-row mapping**, and whether one DWR sample suffices for
   `regulations` independence.
6. Review the **PDF-vs-HTML divergences** (9 issues) and the DWR close-date conflict. These are
   recorded as `gap` or `unresolved` cross-checks, not unit gaps.
7. Housekeeping: the primary's commit `55885f6` (MS) swept in this run's in-progress `requests/`
   and `capture-results/` b01–b09 files. The b10–b17 files, `manifest.jsonl`, `run.json` and this
   file are uncommitted.

## Validator

```
$ python3 census/validate.py census/VA --stage manifest --verify-bytes
SKIP schema validation: jsonschema not importable; cross-record checks still run.
FAIL C03: va-41-26-pdf gap/pending needs human review
FAIL C03: va-41-25-pdf gap/pending needs human review
FAIL C03: va-xa-deq-home gap/pending needs human review
FAIL C03: va-xa-mrc-home gap/pending needs human review
FAIL C03: va-xa-doe-home gap/pending needs human review
FAIL C03: register-issue needs independent lineage or reviewed single_lineage
FAIL C03: noira needs independent lineage or reviewed single_lineage
FAIL C03: governor needs independent lineage or reviewed single_lineage
FAIL C03: general-notices needs independent lineage or reviewed single_lineage
FAIL C03: petitions needs independent lineage or reviewed single_lineage
FAIL C03: periodic-review needs independent lineage or reviewed single_lineage
FAIL C03: errata needs independent lineage or reviewed single_lineage
12 error(s).
```

- No C01, C02 or C10 failures. All 232 retrieved entries' bytes were re-hashed and matched against
  their sidecars.
- jsonschema is not installed. A stdlib structural check of `manifest.schema.json`,
  `run.schema.json` and `sidecar.schema.json` found 0 errors. It caught 3 of 3 errors injected in a
  negative test.
- The 12 failures need human adjudication records. An agent cannot create them.
