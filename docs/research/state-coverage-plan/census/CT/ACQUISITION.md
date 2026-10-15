# CT acquisition: census protocol step 3 (2026-10-15)

Operator: research child (Claude, acquisition operator), attended run. Owner review: **pending**.
Inputs: `UNIVERSE.md` v0.1 as signed through `../SCOPE-DECISIONS.md` (CT answers 1, 2, 4, 6–9; interval
option A `[2024-10-14, 2026-10-12)` America/New_York), `../../rights/DECISIONS.md` items 1–13,
`../../rights/surfaces.json` (`ct-rendered@2026-10-15.1`, `ct-json@2026-10-15.2`,
`ct-policy-reference@2026-10-15.2`, `ct-law-journal@2026-10-15.1`).
Manifest `universe_version`: `ct-v0.1-signed-2026-10-15`. Enumeration (step 4) has **not** started.

> **Round 2 (same day) supersedes the gap, cross-check, validator and owner-item sections below.**
> Round 1 is kept as written. Current state: see "Round 2" at the end and "Owner sign-offs needed".

Every capture went through `census/capture.py` (rights gate, robots, ≥5 s per host, stop on
403/429/challenge). Originals and sidecars are only in `~/yokel-captures/state-coverage/`. Git holds
the manifest, requests (`requests/`), capture results (`capture-results/`, metadata only) and this file.
No comments or commenter data were requested. LlamaParse was not called; 0 credits were used.

## Result in one paragraph

All 11 notice-search slices and all 175 notice documents they list were retrieved and verified
(`--verify-bytes`: hash, length and sidecar linkage clean). That is 274 PDF pages and 69.3 MB. The
interval holds **71 NOIs and 53 NODs on 68 proceedings**, the same counts the scoping run found
independently. Everything below the notice level is still a gap. That covers RMR history and notes,
hearing details, extensions and the open-period list. It also covers the independent agency-page
cross-check. The reason is that `surfaces.json` grants those surfaces collection but not retention,
so `capture.py` refuses them before making any network call. Every process is therefore
`single_lineage: true` with an owner-review placeholder. The validator's only errors are the 146
review references this step can't sign (see "Validator").

## Expected-count derivation

**Notice search (`portal_slice`).** `POST Search/PublicNoticesResults` (form fields taken from the
captured form `ct-form-public-notices`; there is no anti-forgery token). The rows are a complete JSON
array embedded in server HTML. There is no server pagination or cursor (Kendo pages on the client).
- **Slicing:** 13-week Monday-aligned slices covering `[2024-01-15, 2026-10-12)`. That is 8 interval
  slices, the 26-week carry-in window (2 slices) and one extra backward step.
- **Padding and boundaries:** query dates are padded 2 days on each side (1 day for the first slice,
  which was the format test). `PublishedDateBefore` proved date-inclusive: rows on the padded
  boundary dates appear in both neighbouring slices.
- **Expected children:** the data-array rows whose `PublishDate` (epoch ms → America/New_York) falls
  inside the slice's own half-open range.
- **Terminal proof per slice:** the array parsed completely, the row count is ≤ 32 (well under the
  200-row result seen in scoping req 8), and every row in an overlap zone was present in the
  neighbouring slice (10/10 neighbour pairs agree).
- **Dedupe:** 176 distinct GUIDs. 175 belong to a slice. The other, PR2024-008's NOI posted
  2026-10-13 11:38 NY, is after the interval end and more than 24 h past the boundary. It is
  follow-up outside the interval and has no unit. No row falls within 24 h of either boundary.

| Slice | Range | Owned rows | NOI | NOD | Text layer native/partial/none |
|---|---|---|---|---|---|
| `ct-slice-2024-01-15` | [2024-01-15,2024-04-15) backward step | 14 of 14 | 6 | 8 | 12/0/2 |
| `ct-slice-2024-04-15` | [2024-04-15,2024-07-15) carry-in | 15 of 18 | 10 | 5 | 13/1/1 |
| `ct-slice-2024-07-15` | [2024-07-15,2024-10-14) carry-in | 22 of 23 | 10 | 12 | 20/2/0 |
| `ct-slice-2024-10-14` | [2024-10-14,2025-01-13) | 31 of 32 | 17 | 14 | 27/4/0 |
| `ct-slice-2025-01-13` | [2025-01-13,2025-04-14) | 14 of 14 | 8 | 6 | 12/1/1 |
| `ct-slice-2025-04-14` | [2025-04-14,2025-07-14) | 7 of 8 | 4 | 3 | 6/0/1 |
| `ct-slice-2025-07-14` | [2025-07-14,2025-10-13) | 22 of 23 | 15 | 7 | 20/0/2 |
| `ct-slice-2025-10-13` | [2025-10-13,2026-01-12) | 15 of 15 | 4 | 11 | 13/1/1 |
| `ct-slice-2026-01-12` | [2026-01-12,2026-04-13) | 9 of 9 | 6 | 3 | 7/0/2 |
| `ct-slice-2026-04-13` | [2026-04-13,2026-07-13) | 11 of 11 | 6 | 5 | 6/4/1 |
| `ct-slice-2026-07-13` | [2026-07-13,2026-10-12) | 15 of 16 | 11 | 4 | 12/2/1 |
| **Interval total** | | **124** | **71** | **53** | |

**Documents (`attachment`).** There is one `getDocument?guid=` PDF per row. All 175 were retrieved as
`application/pdf`. The page count comes from the original (PDFKit). One manifest entry per document
holds the page range. There are no separate page entries, because a page entry would need its own
sidecar capture record, which the validator checks. Failed pages are logged as locators in
`expected.evidence_refs` instead.

**Same-day duplicate NOIs.** PR2024-025 has two NOI GUIDs posted 2024-07-26, and PR2025-016 has two
posted 2025-08-05. Both documents are retained in each case. Enumeration must decide whether each
pair is a re-post, a correction or a duplicate.

**JSON lifecycle routes (`history_slice`, gaps).** The route signatures were verified from the
proceeding page's own script in `ct-shell-rmrview-PR2024-059`:
- `Search/getRMRHistory?trackingNumber=`
- `Search/getRMRNotes?trackingNumber=`
- `Search/getRMRSummaryInformation?trackingNumber=`
- `Search/getPublicHearingDetails?guid=`, where the guid comes from history rows' `AssociatedDetails`.

The manifest has one history entry and one notes entry for each of 69 proceedings: the 68 with an
interval notice plus PR2024-003 (the undetermined carry-in below). That is 138 entries. A history
entry's `expected_children` is `null`, because hearing-detail GUIDs can only be discovered from the
history response. One more gap entry covers `Browse/getOpenCommentPeriods`. Summary information was
not modelled, because it carries status rather than participation events.

**Older-proceeding updates without a notice.** These include extensions, or hearings scheduled on a
proceeding with no notice in the interval. They are visible only through the JSON routes, so the
history universe is **unbounded**. `run.json` therefore has `history_bounded: false`.

## Carry-in backward search (UNIVERSE rule)

All 26 NOIs posted in `[2024-01-15, 2024-10-14)` were captured. Their native text was scanned for
any full calendar date on or after 2024-10-14. This is an acquisition-level screen; the passes make
the final calls.
- **Candidates (dates ≥ start):** PR2024-025 (both NOIs, 2024-10-24), PR2023-031 (2024-10-15) and
  PR2024-017 (dates up to 2024-11-13). All three proceedings also have interval notices.
- **`[2024-04-15, 2024-07-15)`:** no NOI has a date on or after the start (latest 2024-08-12).
- **`[2024-01-15, 2024-04-15)` (extra step):** no native-text NOI is active at the start. One NOI is
  undetermined: PR2024-003, posted 2024-02-09. It is image-only (2 pages with no text layer), so its
  dates can't be read without rendered inspection. Same-lineage hint: a NOD on PR2024-003 was posted
  2024-04-05. **Review case:** the backward search stops at 2024-01-15 only if this NOI is confirmed
  closed.
- Relative closes ("within thirty days") produce no calendar date and could hide an active round. The
  passes must read each pre-interval NOI's close role rather than rely on this screen.

## Extraction test (during acquisition; no LlamaParse)

The test used PDFKit through a locally compiled Swift helper (macOS system framework; nothing was
installed). The text went to `/tmp` only. Every page carries a system text stamp ("Connecticut
eRegulations System — Tracking Number … — Posted m/d/yyyy"), so the stamp is removed before counting.
Classification rules:
- **Page failure:** a page with fewer than 300 body characters is a failed locator.
- **`none`:** every page has fewer than 50 characters.
- **`partial`:** some pages fail, but not all.

| text_layer | format | documents |
|---|---|---|
| native | text_pdf | 148 |
| partial | mixed | 15 |
| none | scan_pdf | 12 |

- **Failed page locators:** 29 pages across 27 documents. Both passes must use `rendered_image` or
  `both` for these.
- **Image-only documents (12):** PR2015-132 NOD, PR2024-003 NOI (2024-02-09), PR2022-026 NOD,
  PR2024-043 NOD, PR2025-012 NOI and NOD, PR2025-009 NOD, PR2025-011 NOD, PR2026-005 NOI and NOD,
  PR2026-007 NOD, and PR2024-032 NOI (2026-09-22).
- **Region-locator failures (9 NOIs):** no native sentence pairs "comment" with a full calendar date,
  so the close must be read from the rendered page. These are PR2024-003, PR2024-058, PR2025-012,
  PR2023-021, PR2026-005, PR2025-036 (both GUIDs), PR2026-014 and PR2024-032.
- **LlamaParse estimate:** if all 29 failed pages go to LlamaParse, that is about 290 credits against
  CT's 2,000 envelope. Nothing has been reserved.

## Cross-checks per process

| Process (run.json) | Universe rows covered | Same-lineage checks | Different-lineage check | Status |
|---|---|---|---|---|
| `noi` | NOI comment window; notice-stated hearing-request window; definite/conditional hearings; reopened rounds | slice ↔ neighbouring slice overlap (10/10 match); NOI body ↔ search row: stamp tracking number and Posted date = row tracking number and `PublishDate` (NY), and the body names the notice type. 93/97 NOIs match (all 175 documents, including carry-in slices); the other 4 are image-only NOIs, `unresolved` | agency pages `portal.ct.gov/deep`, `/deepfishing` and `/seec` (cited in 16 NOI bodies) recorded as `gap` cross-checks; not fetched | `single_lineage: true`, owner review pending |
| `nod` | NOD lifecycle / withdrawal-type | NOD body ↔ search row: 70/78 match; the other 8 are image-only NODs, `unresolved` | none identified | `single_lineage: true`, owner review pending |
| `rmr-lifecycle` | extensions, hearing scheduled after request, reschedule/cancel, corrections | none (routes not fetched) | none | `single_lineage: true`, owner review pending; all units are gaps |

There were no stamp or date discrepancies on any document with a text layer. These are
same-lineage consistency checks, not corroboration.

**Agency terms were not checked.** `ct-policy-reference` has `retention: not_authorized`, so
`capture.py` cannot fetch even the terms pages, and nothing on that surface could be retained if
they were checked. That skip is recorded on each `ct-xchk-portal-*` entry.

## Gaps (all `completeness: gap`, `human_review_ref` = placeholder `owner-review-pending/ct-acq-2026-10-15/<topic>`)

| Topic | Entries | Reason |
|---|---|---|
| `ct-json-retention` | 139 (138 RMR history/notes + open periods) | `ct-json` grants collection (DECISIONS item 7) but `retention: not_authorized`; `capture.py` refuses with "original retention not authorized" (b05, 0 network attempts) |
| `agency-xchk-retention` | 3 | `ct-policy-reference` same mismatch: DECISIONS item 5 says "originals internal only" (implies internal retention) but the record says `not_authorized` |
| `law-journal-blocked` | 1 | `collection_rule: blocked`; refused by the gate. Host root used as locator (exact notice paths unverified) |
| `single-lineage-{noi,nod,rmr-lifecycle}` | 3 process rows | no lawful, fetchable independent lineage under current records |

## Requests, elapsed time, refusals

- **Network requests:** 195, all to `eregulations.ct.gov`, sequential at ≥5 s.
  - 7 × `robots.txt` (404; one per `capture.py` run)
  - 1 form GET
  - 1 RMRView shell GET
  - 11 notice-search POSTs
  - 175 `getDocument` GETs
- **Not reached:** 0 requests to `portal.ct.gov`, `jud.ct.gov`, or any JSON route.
- **Host behaviour:** no 403, 429 or challenge, and no host was stopped. F5 `TS…` cookies were not
  stored or replayed (`capture.py` has no cookie jar).
- **Elapsed time:** capture window 19:03:28Z–19:26:48Z (23 min 20 s). The whole operator session,
  including reading inputs and building outputs, took about 35 min.
- **Refusals:** 143 requests in `requests/b05-gated-surfaces.jsonl` were refused at the rights gate
  with no network attempt. 139 were `ct-json` and 3 `ct-policy-reference` ("original retention not
  authorized"); 1 was `ct-law-journal` ("collection_rule=blocked").
- **Batches:** b01 scoping (form, RMRView), b02 slice format test, b03 slices, b04-01…04 documents,
  b05 gated surfaces.

## run.json notes

- **Processes:** the agency row is `ct-uapa-agencies`. The roster is defined by the § 4-168 posting
  duty: the union of posting agencies seen in the slices. The agency picklist's data source was not
  identified and not fetched. Process IDs group the UNIVERSE rows as in the cross-check table, and
  slices are filed under `noi`.
- **Flags:** `scope_resolved: true` (signed scope); `history_bounded: false` (JSON gap);
  `attended: true`.
- **Credits:** the credit ledger is 0 for all four states. Pass, crosswalk and temporal arrays are
  empty.
- **Placeholders:** run.schema has no pre-freeze state, so schema-shaped placeholders are used.
  `brief_sha256`, `audit.seed` and `audit.frame_hash` are 64 zeros. `brief_frozen_at` is
  `1970-01-01T00:00:00Z`, and `brief.txt` doesn't exist yet. These are **not frozen values**;
  replace them at step 4.

## Validator

`python3 census/validate.py census/CT --stage manifest --verify-bytes` exits with 146 errors. jsonschema
is not installed, so schema checks were skipped; a stdlib required-field, enum and pattern check of
the manifest and run.json found 0 issues.
- 143 × `C03: <entry> gap/pending needs human review`: the gap entries above.
- 3 × `C03: <process> needs independent lineage or reviewed single_lineage` (`noi`, `nod`,
  `rmr-lifecycle`).
- 0 C01/C02/C10 errors. Rights, URL patterns, hashes, lengths and sidecar linkage all verified
  against the external store.

Both error classes need a human-reviewer adjudication record, which this step can't create (an agent
can't sign as the owner).

## Owner items

1. **Retention for `ct-json` and `ct-policy-reference`.** DECISIONS items 5 and 7 allow reading, and
   item 5 says "originals internal only". But `surfaces.json` 2026-10-15.2 sets
   `retention: not_authorized`, so `capture.py` refuses both. If internal retention is intended, bump
   the records to `internal_originals`. Re-running `requests/b05-gated-surfaces.jsonl` (about 142
   requests, ~25 min) plus hearing-detail follow-ups would then close the lifecycle gap and allow the
   agency cross-check. Check each agency's terms first.
2. **Pattern overlap.** `getDocument` matches both `ct-rendered` and `ct-json` patterns. It was
   collected as `ct-rendered` (linked public notice PDFs). Confirm, or tighten the patterns.
3. **Sign the review placeholders.** Sign or edit the gap reviews and the three single-lineage
   reviews (topics above).
4. **Carry-in review case.** PR2024-003's 2024-02-09 image-only NOI decides whether the backward
   search can stop at 2024-01-15.
5. **Universe header.** `UNIVERSE.md` still reads "v0.1-proposed / not frozen" although
   SCOPE-DECISIONS is signed. Update the header, or confirm the manifest label
   `ct-v0.1-signed-2026-10-15`.
6. **Run-schema pre-freeze state.** Accept the zero-hash placeholders, or add a nullable/pre-freeze
   state to run.schema.

---

# Round 2: gated surfaces after the rights correction (2026-10-15)

Operator: research child (Claude), attended run. Rights: `surfaces.json` 2026-10-15.4 (`ct-json` and
`ct-policy-reference` now `internal_originals`; `getDocument` belongs only to `ct-rendered`; see
`../../rights/DECISIONS.md` "Correction"). Every request went through `census/capture.py`. No CT
objection to the JSON routes is on record (`outreach/CT.md` is still unsent). No LlamaParse, 0 credits.

## What changed in the manifest (331 → 352 entries)

- **Gaps replaced (142):** 138 `getRMRHistory`/`getRMRNotes` entries, `ct-json-open-comment-periods`,
  and the agency pages `ct-xchk-portal-{deep,deepfishing,seec}`. Each keeps its entry ID and now has
  the round-2 retrieval and current rights version. Its `expected.evidence_refs` cites the round-1
  refusal (`capture-results/b05-gated-surfaces.jsonl`, refused under `@2026-10-15.2`) and the new
  capture result. Every JSON response parsed as a complete array; the routes take no paging
  parameters (terminal proof on each entry).
- **Added (21):**
  - 4 hearing-detail records (`ct-json-hearing-*`, from DetailType-0 history rows).
  - 10 lifecycle PDFs that only the history lists, not the notice search:
    - 3 extension notices (`ct-doc-*-ext-*`; PR2023-056's two history rows point to byte-identical files)
    - 1 revised NOI
    - 1 corrected NOD
    - 5 "Other Document – Notice of Decision" PDFs
  - 7 agency entries (terms, 3 DEEP discovery pages, DEEP pending regulations × 2 processes, 1 missing page).
- **History entries** now have `expected_children` set. The children are the hearing records plus
  participation-lifecycle documents posted in `[2024-01-15, 2026-10-12)`. Excluded by rule: comment
  files, summaries of comments, transcripts, hearing-officer reports, AG/LRRC paperwork. 14 children
  in total. All 138 notice-search documents of these 69 proceedings appear in their histories (138/138
  same-lineage matches).
- **Excluded by the no-commenter-data rule:** PR2024-016's "Notice of Decision & Summary of Comments"
  (recorded on its history entry, not requested). The "View Comments" route was never called.
  `CommentsDocumentList` is null in all 76 comment-period details.
  - **Caveat:** the retained history JSON (external store only) does list comment-document *file
    names* in its rows.
- **Documents' agency cross-checks:** the 17 `gap` checks against agency homepages are now
  `unresolved`. The homepages were fetched but carry no notice content.

## Requests

171 network attempts, 19:33:33Z–19:53:25Z. There was no 403, 429 or challenge, and no host was stopped.
- `eregulations.ct.gov`: 153 requests plus 2 robots fetches (404).
  - b06: 139 JSON routes, all 200
  - b08: 14 lifecycle and hearing requests, all 200
- `portal.ct.gov`: 11 requests plus 5 robots fetches (200; allows `/`).
  - b07: terms
  - b09: 4 agency pages; the RBCR page answered 302 to the 404 page
  - b10–b12: 5 DEEP pages
- **Not retried:** `ct-law-journal` (still `blocked`) and `seec.ct.gov` (no rights record; skipped).

## Lifecycle events found in the histories (posted 2024-01-15 … 2026-10-11)

| Kind | Proceedings (posted) | Note |
|---|---|---|
| Extension | PR2023-056 (2024-08-02) | Comment period +14 days to 2024-08-26 17:00, plus an extra hearing 2024-08-19 10:30 (Zoom). Closed before the interval start, so not a carry-in. Notice not in search. |
| Extension | **PR2026-021** (2026-09-23) | Close moved 2026-09-25 → **2026-10-12**, which is the interval end date. History stores the end as `2026-10-12 00:00` while the notice says "to October 12, 2026" (precision conflict for the passes). Notice not in search; the PDF is complete (`%%EOF`) followed by null padding. |
| Revised NOI | **PR2024-053** (2024-11-26) | Close moved 2024-12-27 → 2025-01-10 5:00 pm. **Not in the notice search**: a search omission exposed by the history. |
| Hearing only in history | **PR2025-020** (2025-08-28) | Hearing 2025-09-17 12:30 (55 Farmington Ave). The NOI never mentions a hearing; it was scheduled 7 minutes after the NOI. |
| Hearing records | PR2025-016 (2025-09-03 11:31), PR2025-021 (2025-09-11 and 2025-10-02 17:00) | Both are stated in the NOIs. PR2025-016's NOI says 11:30 a.m., so the 1-minute difference is a same-lineage discrepancy, not resolved here. |
| Early close by withdrawal | PR2023-031 (2024-09-04, pre-interval), PR2025-014 (2025-10-08), PR2025-036 (2026-05-15; re-noticed 2026-05-19, which explains its two NOIs) | Comment period closed the day of withdrawal. |
| Correction / other NOD | PR2024-037 corrected NOD (2024-12-02); PR2024-017 revised NOD (in search); Other-Document NODs for PR2024-003 (2024-12-03), PR2024-016 (2025-08-07), PR2024-056 (2025-06-24), PR2025-008 (2025-12-05) | |
| Withdrawn permanently | PR2024-031, PR2024-050, PR2024-053, PR2025-016, PR2025-020, PR2025-027 | After the comment period (NOD lifecycle). |
| Reopened rounds | PR2022-002, PR2024-003 (3 rounds), PR2024-023 (3), PR2024-059, PR2025-036 | Every round has its own NOI in the search. |
| Second NOI, no new period | PR2024-033, -035, -036, -037, -038 (each 2024-12-26) | The history has no "Comment Period Opened" row for them. Review case for enumeration. |
| After interval end | PR2026-014 NOD (2026-10-15) | Follow-up, no unit. |

- **No later hearings or requests:** no hearing was scheduled more than one day after its NOI, so no
  "hearing scheduled after a request" case appears in these 69 histories. Another 35 hearings are
  stated inside "Contains Hearing Information" NOIs, which are already in the manifest.
- **Open-periods list** (7 rows at 2026-10-15) agrees with the slices: 6 have their NOI in the
  manifest, and PR2024-008 (NOI 2026-10-13) is post-interval as round 1 found. None is flagged
  `Extended`.

## Round-1 open items

- **PR2024-003 carry-in: resolved at acquisition level.** I inspected a local PDFKit render (no
  LlamaParse).
  - The 2024-02-09 NOI's comment period "shall end on March 11, 2024". It adds that the comment
    period "shall be extended upon posting a copy of the proposed regulation".
  - The history shows that round closed 2024-03-11, a NOD followed on 2024-04-05, and a re-notice
    on 2024-05-22 closed 2024-06-23. The next round opened 2025-07-29.
  - So no round was active at 2024-10-14, and the backward search can stop at 2024-01-15. This rests
    on a decisive visual mark, so it is listed for owner confirmation.
- **Same-day duplicate NOIs:**
  - **PR2024-025:** the 11:56 posting says written comments are due "October 4, 2024", while the
    same notice says the period ends October 24. The 14:31 posting corrects this to October 24. The
    history has a single period ending 2024-10-24 17:00. This is a candidate correction re-post.
  - **PR2025-016:** the 14:41 born-digital file and the 15:14 signed scan ("Final2") have the same
    text apart from OCR noise. This is a candidate duplicate re-post.
  - Both annotations are recorded on the document entries. The passes decide.
- **Rights and pattern overlap (round-1 owner items 1–2):** fixed by the owner in v2026-10-15.4.
- **UNIVERSE header (item 5):** status line set to "signed 2026-10-15 (see SCOPE-DECISIONS.md)".
- **Run-schema placeholders (item 6):** still open.

## Cross-checks per process (round 2)

| Process | Same lineage | Different lineage (agency-published) | run.json |
|---|---|---|---|
| `noi` | Slices, NOI body ↔ row, history lists every search document, open-periods ↔ slices | **DEEP pending-regulations page** (`ct-xchk-portal-deep-pending-regs`). Close dates match for PR2025-028 (8/3/26 5 pm), PR2025-034 (7/31/26 5 pm) and PR2024-054 (3/27/25). Closed status is consistent for PR2025-035 and PR2025-036. 5 of 68 proceedings, DEEP only. Homepages (DEEP, DEEPFishing, SEEC) carry no notice content, so those checks are `unresolved`. DEEP's RBCR page is gone (gap). | `single_lineage: false`, partial-coverage review ref |
| `nod` | NOD body ↔ row | Same DEEP page, captured separately for this process. Step-9 "Final Approved" is consistent with the NODs of PR2025-008, PR2025-026 and PR2023-056 (status only). 3 proceedings. | `single_lineage: false`, partial-coverage review ref |
| `rmr-lifecycle` | Hearing record ↔ history detail (4/4); lifecycle PDF stamp ↔ history row (10/10); notes ↔ history close (6/6) | None. Agency pages show current status, not extensions, hearings or corrections. | `single_lineage: true` (unchanged) |

- **Lineage note:** the JSON routes are the same eRegulations backend as the search slices, so these
  are consistency checks that exposed omissions (PR2024-053, PR2025-020). They are not
  corroboration.
- **Independence:** the DEEP page is agency-authored with its own stated dates, but it links to
  eRegulations.
- **Coverage gap:** whether other agencies publish comparable lists was not tested. Sampling about
  10 more agency pages would take roughly 20 requests and 5 minutes, each checked against its terms.

## Validator (round 2)

`python3 census/validate.py census/CT --stage manifest --verify-bytes` exits with **3 errors**.
jsonschema is not installed, so schema checks were skipped. A stdlib subset check (required, enum,
pattern, if/then) of the manifest and run.json found 0 issues. All 350 retrieved entries
byte-verified (C10 clean).

```
FAIL C03: ct-gap-law-journal gap/pending needs human review
FAIL C03: ct-xchk-portal-deep-rbcr gap/pending needs human review
FAIL C03: rmr-lifecycle needs independent lineage or reviewed single_lineage
```

## Owner sign-offs needed

**Validator-blocking (3).** Each needs a human-reviewer adjudication record at the ref shown.

| # | Reason | Entry / process | Review ref |
|---|---|---|---|
| 1 | Blocked surface (AI-crawler exclusion; `ct-law-journal` blocked) | `ct-gap-law-journal` | `owner-review-pending/ct-acq-2026-10-15/law-journal-blocked` |
| 2 | Agency page removed (302 → 404); cited only by PR2024-025's NOIs, whose dates the history confirms | `ct-xchk-portal-deep-rbcr` | `owner-review-pending/ct-acq-r2-2026-10-15/agency-page-missing` |
| 3 | No independent lineage for lifecycle events (extensions, hearing records, corrections) | process `rmr-lifecycle` | `owner-review-pending/ct-acq-2026-10-15/single-lineage-rmr-lifecycle` |

**Decisions that don't block the validator but affect completeness (4):**

4. **Partial independent lineage.** `noi` and `nod` pass only through the DEEP page (5 NOI and 3 NOD
   proceedings out of 68). Accept this, or order the agency sampling above. Refs:
   `…/ct-acq-r2-2026-10-15/partial-independent-lineage-{noi,nod}`.
5. **Decisive visual mark.** Confirm that PR2024-003's 2024-02-09 NOI closes on March 11, 2024
   (rendered page 1). This decides the 2024-01-15 backward-search stop.
6. **`history_bounded: false`.** Updates on proceedings with no NOI since 2024-01-15 remain
   undiscoverable without per-proceeding history calls.
   - **Evidence for bounding:** in these 69 histories, every comment period opened since 2024-01-15
     has a search-visible NOI, and extensions only occur on open periods.
   - **Gap:** an older proceeding with a conditional extension could still be missed.
   - **Options:** accept the bound, or sweep PR2023-001…~060 histories (about 55 requests, about
     10 minutes).
7. **Run-schema placeholders** (round-1 item 6), unchanged.
