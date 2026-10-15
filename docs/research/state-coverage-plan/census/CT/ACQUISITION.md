# CT acquisition: census protocol step 3 (2026-10-15)

Operator: research child (Claude, acquisition operator), attended run. Owner review: **pending**.
Inputs: `UNIVERSE.md` v0.1 as signed through `../SCOPE-DECISIONS.md` (CT answers 1, 2, 4, 6–9; interval
option A `[2024-10-14, 2026-10-12)` America/New_York), `../../rights/DECISIONS.md` items 1–13,
`../../rights/surfaces.json` (`ct-rendered@2026-10-15.1`, `ct-json@2026-10-15.2`,
`ct-policy-reference@2026-10-15.2`, `ct-law-journal@2026-10-15.1`).
Manifest `universe_version`: `ct-v0.1-signed-2026-10-15`. Enumeration (step 4) has **not** started.

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
