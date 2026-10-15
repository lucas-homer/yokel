# MS acquisition: census protocol step 3 (2026-10-15)

Operator: research child (Claude, acquisition operator), attended run. Owner review: **pending**.
Inputs: `UNIVERSE.md` v0.1 as signed through `../SCOPE-DECISIONS.md` (MS answers 1–14; interval A
`[2026-05-18, 2026-08-17)` America/Chicago), `../../rights/DECISIONS.md` items 1–16,
`../../rights/surfaces.json` (`ms-sos-admin-search`, `ms-agency-rulemaking` @`2026-10-15.3`), PROTOCOL v1.2
(scoped coverage blocks; null pre-freeze fields). Manifest `universe_version`: `ms-v0.1-signed-2026-10-15`.
Enumeration (step 4) has **not** started.

Every retained capture went through `census/capture.py` (rights gate, robots, ≥5 s per host, stop on
403/429/challenge). Originals and sidecars are only in `~/yokel-captures/state-coverage/`. Git holds the
manifest, `run.json`, requests (`requests/`), capture results (`capture-results/`, metadata only) and this
file. No comments or commenter data were requested. LlamaParse was not called; 0 credits were used.

## Result in one paragraph

The SOS bulletin was read in 19 date-type slices. Their union covers **every integer system number in
the backbone 28374–28965 except one** (591 of 592). The missing one, **28935**, returns 404 for both its
form and full-text paths and is a named gap for owner review. All 621 listed notice forms (591 in the
backbone + 30 older finals returned by the effective-date slices) were retrieved and verified with
`--verify-bytes`: 673 scanned pages, 266 MB, no text layer on any page. The interval holds **229 filings,
109 of them proposals**, matching the scoping projection. Independent agency evidence covers **4 of 17
proposals** at MDEQ, MID and the Fire Personnel Board (all match on identity). Every other process is
`single_lineage: true` with an owner-review placeholder. The validator's only errors are the 12 review
references this step can't sign.

## Collection

| Batch | Host | Requests (+robots) | Result |
|---|---|---|---|
| `b01-slices` | www.sos.ms.gov | 19 POST (+1) | 19 retrieved |
| `b02-forms-01..04` | www.sos.ms.gov | 623 GET (+4) | 621 retrieved, 2 missing (404) |
| `b03-agency-pages` | www.mdeq.ms.gov, www.mid.ms.gov | 2 GET (+2) | 2 retrieved |
| `b03b-agency-linked` | same | 2 GET (+2) | 2 retrieved |
| `b04-agency-docs` | same | 5 GET (+2) | 5 retrieved |

- **Totals:** 662 HTTP exchanges: SOS 647 (5 robots), MDEQ 7 (3 robots), MID 8 (3 robots).
- **Time:** first exchange 19:34:41Z, last 20:36:08Z (61.5 min wall). SOS spacing was ~6.1–6.9 s.
  The agency-host batches ran during the SOS form batch, on different hosts under `capture.py`'s per-host
  limiter (one request at a time per surface).
- **Refusals:** none. No 403, 429 or Cloudflare challenge; no host was stopped.
- **Operator errors:** the first `b04` invocation ran with a mistyped path. `capture.py` exited on the
  missing requests file before any network call, then the batch was rerun.
- **Bytes:** 268 MB of originals. The 649 retrieved entries map to 646 distinct hashes: the four zero-row
  slices return the identical 12-byte empty response, which has one sidecar holding four capture records.
- **Non-retained lookups:** 1 web search and 3 page reads for the statute host (below).

## ID-sequence accounting (SCOPE Q11)

**Service contract (from the scoping log and `Admin.js`):** `BulletinSearch` with `tmpTypeF=0` (all filing
types), `tmpOrder=FilingID` ascending, `pageNum=0`, `numberToDisplay=1000`.

**Slices:** four 13-week Monday-aligned windows (backward step 2, backward step 1 + carry-in, interval,
follow-up through today), each queried by proposed, final, withdrawal and effective date. Three further
effective-date slices run forward to 2030-01-01. Query dates are padded one day each side.

**Terminal proof per slice:** the `|N|0` trailer equals the parsed row count, and N < 1000 (max 209). See
`ms-slice-*` → `accounting.terminal_evidence_refs`.

**Backbone:** the smallest system number with a filing date ≥ 2025-11-17 (28374) through the largest number
returned by any slice (28965, filed 2026-10-15). The upper bound is the sequence head at capture time;
IDs beyond it were not probed.

**Expected children:** each record is the child of exactly one slice, its filing-date slice. The
precedence is withdrawal date > final date > proposed date > effective date; otherwise it falls back to the
first slice that returned it. Slice `expected_children` counts those assignments.

| Window (FILED stamp, else record date) | System numbers | Forms | Provisional class (date fields only) |
|---|---|---|---|
| pre-range (< 2025-11-17; finals returned by effective-date slices) | 28313–28371 (sparse) | 30 | 30 final |
| backward step 2 `[2025-11-17, 2026-02-16)` (precautionary) | 28374–28496 | 123 | 60 proposal, 58 final, 5 withdrawal |
| backward step 1 `[2026-02-16, 2026-04-13)` | 28497–28644 (+28938) | 77 | 38 proposal, 38 final, 1 other |
| carry-in `[2026-04-13, 2026-05-18)` | 28573–28644 | 72 | 39 proposal, 31 final, 2 withdrawal |
| **interval A `[2026-05-18, 2026-08-17)`** | 28645–28905 | **229** | **109 proposal**, 116 final, 4 withdrawal |
| follow-up `[2026-08-17, 2026-10-13)` | 28873–28951 | 76 | 40 proposal, 32 final, 1 withdrawal, 3 other |
| post-freeze `[2026-10-13, capture)` | 28952–28965 | 14 | 6 proposal, 8 final (closure follow-up only, unscored) |
| **Backbone 28374–28965** | **592 integers** | **591 records** | **28935: no record; form and full text 404** |

- System numbers interleave across windows (UNIVERSE: not strictly date-ordered). 28938, the MID record
  with impossible dates, sits in step 1 by its 4/1/2026 proposed date.
- The record class is a provisional grouping for `process_id` only. Type flags are unreliable, and the
  passes classify from the form.
- Scoping's "1,158 of 1,160" check is reproduced for this range: 591/592. 27884 (an earlier omission)
  lies below the backbone.

**Gap for owner review: 28935.**
- `ms-probe-28935-a` and `-b` both returned 404 (1,245-byte HTML error body, not retained).
- The UNIVERSE note suggested MID's Part 101 proposal as a candidate. That proposal is **28934** (Fire
  Personnel Minimum Standards and Certification Board, FILED 2026-09-30), so 28935 is unexplained.
- It is unknown whether this is a voided number, a deleted filing or an unposted filing.
- Ref: `owner-review-pending/ms-acq-2026-10-15/id-gap-28935`.

## Format and text-layer test

- **Native text:** all 623 form entries (621 forms + 2 probes) are `scan_pdf`, `text_layer: none`.
  PDFKit native text is 0 characters on every page.
- **Page counts:** 592 forms are one page. 29 run 2–4 pages: 12 × 2, 11 × 3, 6 × 4, including the MID
  Part 7 proposals 28585/87/88/97/28711 and 28934. That gives **673 pages**, not the one page per form
  UNIVERSE assumed.
- **Failed locators:** every page of every form is logged in `expected.evidence_refs` as needing
  rendered-image inspection.
- **Pages by window:** interval 239, carry-in 88, step 1 81, step 2 130, follow-up 79, post-freeze 14,
  pre-range 42.
- **Agency documents:** native text throughout (MDEQ notice 2 pp and rule text 56 pp; MID PDFs 8–23 pp).

## Operator screen: local OCR, not a pass input

To check content identity and the history boundary, every form was OCR'd **locally** with macOS Vision
(no third party, no LlamaParse). The text stays in `/tmp`, outside git and the hash store. Both passes must
still read rendered images, and this screen must not be given to either pass.

**Identity:** all 621 OCR as SOS APA Form 001.

**FILED stamp vs record date** (UNIVERSE Q14 proxy), read for 534 of 621 (87 unread):
- **462 match.**
- **69 stamp 1–4 days later than the record.** The pattern is next business day (Fri → Mon = +3), so the
  bulletin record date looks like a receipt date, not the stamp. This contradicts the scoping sample
  ("all 8 match").
- **3 implausible** (28905 "SEP 14 2025" vs 08-14-2026; 28728 −10 d; 28927 −2 d), treated as misreads.
  Their cohort window uses the record date.
- Every mismatch is a `cross_checks` `unresolved` same-lineage edge, i.e. a review case.
- **Boundary cases:** 28573 (record 04-10, stamp 04-13: step 1 → carry-in) and 28905 (record Fri 08-14;
  in the interval if the stamp is 08-14, follow-up if 08-17). These are decisive stamp marks for human
  review (DECISIONS item 14).

**Scheduled hearing, backward boundary** (UNIVERSE carry-in rule, SCOPE Q10a):
- Step 1 `[2026-02-16, 2026-04-13)` proposals with a dated hearing: 28503 (3/18), 28524 (4/13) and
  28561–63 (4/23). None is on or after 2026-05-18, and no step-1 proposal has an unreadable field. Under
  the signed rule, the search stops at step 1.
- Step 2 was captured anyway as a precaution (123 forms).
- Carry-in hearings found: **28576** (MDEQ, May 20), **28608** (May 28), **28618** (June 17).
- **Review case:** 28568/28569 (Funeral Service Board, filed 2026-04-01) state a hearing on 11/3/2025,
  before filing.
- Interval proposals 28682 and 28759 have hearing fields the OCR could not read.

**Withdrawal targets:**
- Interval and follow-up withdrawals resolve inside the backbone: 28670 → 28615, 28744 → 28625,
  28892 → 28873, and 28620/28656 → proposals of 2025-12-31.
- **28736** (MSDH, "withdrawing and replacing the complete chapter") names no readable target.

**Result:** `history_bounded` is set **false**. The bound rests on a machine screen until the passes
confirm it and the 28736 target is resolved.

## Attachment scope: full text not collected

- **Listed links:** each bulletin row names `<id>a.pdf` (form), an EIS file (always "Not Found") and
  `<id>b.pdf` (full text, listed for 608 of 621 rows). Each form entry records all three in
  `expected.evidence_refs`.
- **What was collected:** the forms only, following the signed UNIVERSE source map ("full text … only
  where the form refers to them … not needed for dates in any sample").
- **Ambiguity:** every Form 001 ends with "The entire text of the Proposed Rule including the text of any
  rule being amended or changed is attached". Read literally, every form refers to its full text.
- **Status:** the 608 full-text links are therefore an **explicitly scoped-out attachment class pending
  owner decision**, not silent omissions. They aren't manifest entries; the full-text path was probed
  only for 28935.

## Cross-checks per process (PROTOCOL v1.2 coverage)

**Independent sources** (`ms-agency-rulemaking`; terms checked at scoping, accuracy-only disclaimers):
- **MDEQ:** the Regulations page "Proposed Regulation Changes" section (rolling: current item only, 2
  linked documents, both captured) and `wp-sitemap.xml` (verified empty urlset, so no history index).
- **MID:** the Regulations page "Proposed Regulations" list (4 entries, all 4 PDFs captured; the dated
  close is on the list entry, the PDFs are rule text).
- **DOR:** skipped (restrictive terms, UNIVERSE).

| Process (agency/process) | Mode | Universe (proposals in backbone) | Matched | Notes |
|---|---|---|---|---|
| `ms-mdeq/proposal` | independent_partial | 6 (28473, 28524, 28576, 28720, 28873, 28939) | 28720 | Hearing identical (Aug 4 2026 2:00 pm, 515 E. Amite). MDEQ adds a comment close "end of business on August 4, 2026" absent from the form (no 20/25-day boilerplate): Q3/Q4 labelling case. The other 5 have `gap` edges (not on the rolling page) and are uncovered |
| `ms-mid/proposal` | independent_partial | 10 | 28491, 28937 | MID closes: Mar 9 2026 (27 d after filing), Oct 29 2026 (28 d): Q3 cases. 8 uncovered (`gap` edges): the Part 7 Fire Marshal proposals 28585/87/88/97/28711, plus 28567, 28862, 28868 |
| `ms-fire-personnel-board/proposal` | independent_partial | 1 (28934) | 28934 | MID-hosted list entry: close Oct 26 2026 (26 d). Scope partial: MID isn't shown to list all Board proposals |
| `ms-mdeq/final`, `ms-mdeq/withdrawal`, `ms-mid/final`, `ms-mid/other` | single_lineage | — | — | MDEQ's page did not show the 28892 withdrawal |
| `ms-sos-filers-other/{proposal,final,withdrawal,other}` | single_lineage | — | — | Grouped ID covers 57 other filers; legacy single-lineage rows only (signed Q8a: no cross-check outside `*.ms.gov` in Phase 1; Medicaid/MSDH/MDHS/PERS have none, DOR skipped) |
| `ms-sos-bulletin/bulletin-index`, `ms-sos-filers-other/unresolved-id` | single_lineage | — | — | Index slices and the 28935 probes |

- `claim_agency_ids` is empty everywhere and every coverage block is `completeness: not_established`.
- Independent evidence corroborates 4 identified proposals and nothing statewide.

## Statute lookup (DECISIONS item 15): not performed

- **Host:** the official free-access Mississippi Code is LexisNexis. SOS links it via
  `lexisnexis.com/hottopics/mscode/`, which redirects to `advance.lexis.com/container?config=…`. SOS adds
  that the laws are "copyrighted by the State of Mississippi" (§ 1-1-9) and that the link "is not part of
  the Mississippi Secretary of State Office".
- **Why nothing was read:** the Lexis page renders only through JavaScript, and no terms were visible
  without it (reported elsewhere to sit behind a terms-acceptance gate). Item 15 requires checking that
  host's terms first. I could not, and I did not accept a clickwrap on the owner's behalf.
- **Consequence:** § 25-43-3.104 is **not verified**, and the 20/25-day rules remain "per form text".
- No unofficial host was used.

## Validator

`python3 census/validate.py census/MS --stage manifest --verify-bytes` exits with **12 errors**. jsonschema
isn't installed, so schema checks were skipped. A stdlib check of the schema subset (types, enums, required,
`additionalProperties`, if/then/else) found 0 issues in all 651 manifest entries, `run.json` and the 646
sidecars; a negative test confirmed it flags errors.
- 2 × `C03: ms-probe-28935-{a,b} gap/pending needs human review`.
- 10 × `C03: <process> needs independent lineage or reviewed single_lineage` (the single-lineage rows above).
- The 3 coverage blocks pass:
  - `ms-mdeq`: universe 6, matched 1, uncovered 5.
  - `ms-mid`: universe 10, matched 2, uncovered 8.
  - `ms-fire-personnel-board`: universe 1, matched 1.
- 0 C01/C02/C10 errors. Rights, URL patterns, hashes, lengths and sidecar linkage were verified against
  the external store.

Both error classes need a human-reviewer adjudication record, which an agent can't create.

**Ledger:** `run.json` holds all five rows (WA/CT/VA/TN/MS) at 0. `validate.py` C10 (final stage) still
expects exactly WA/CT/VA/TN, so an MS row will fail there until the validator learns the reserve-funded
state.

## Owner items

1. **28935:** reviewed gap (voided, deleted or unposted?). Optionally ask SOS in the `outreach/MS.md` note.
2. **Single-lineage placeholders:** sign or replace the 10 rows (`owner-review-pending/ms-acq-2026-10-15/single-lineage-*`).
3. **Full-text scope:** do the 608 `b.pdf` links stay out of the census, or are they collected (≈608
   requests, large page counts, LlamaParse impact)?
4. **Statute host:** accept Lexis terms, name another official host, or keep citations "per form text".
5. **History bound:** confirm the step-1 hearing stop and the 28736 target, then set `history_bounded`.
6. **Stamp review cases:** 69 business-day-lag mismatches + 3 misreads; boundary cases 28573 and 28905.
   Should the record date be treated as receipt date? (The Q14 proxy is unaffected; the stamp controls.)
7. **Precautionary and extra captures:** backward step 2 (123 forms), the pre-range finals (30) and the
   post-freeze filings (14) are retrieved entries. Passes must cover every retrieved entry, so decide
   whether they stay in the pass frame.
8. **Credits:** full coverage of all forms is 673 pages ≈ 6,730 credits. The interval + carry-in + step 1
   + follow-up subset is 487 pages ≈ 4,870. Both exceed the 3,310 + 150 signed for MS (which assumed one
   page per form and no step 2). Needs a re-tiering decision before any parsing.
9. **Validator:** the C10 four-state ledger (above).
10. **UNIVERSE corrections:**
    - MID's Part 101 proposal is 28934; "no matching bulletin record" was wrong.
    - FILED-stamp agreement is ~87%, not 100%.
    - Forms are not all one page.
