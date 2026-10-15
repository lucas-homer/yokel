# Independent LlamaParse comparison review

**Verdict: partial semantic/evidence benefit on the selected fixture.** Both
LlamaParse modes preserve hearing and economic-impact checkbox associations
missing from the retained Firecrawl parse. `agentic_plus` additionally preserves
unchecked alternatives explicitly. **Both omit the official filing-stamp date.**
This blocks a complete evidence-preserving parse claim. The separate vendor
structured extraction returned only an MCP timeout, so its quality is
**not demonstrated**, not inaccurate and not successful abstention.

This is an independent agent review against the frozen 12-case RUBRIC.md,
not independent human gold labels or a blind benchmark. The rubric was not
changed after seeing new outputs; its hash remains
`edc5a78be798a9e59e108e9d2a3ea2820ea88513c588ad2778bfcd7dd0fc608f`.
Original PDF SHA-256 was reverified as
`ac95c240653690261eb7a6fef83bd80a04310cf49c15c37256569bbc70315955`.
Local bytes, the common upload file ID and paired requests are retained; the
vendor did not return a server checksum.

## Case matrix

`case-matrix.json` is the authoritative independent case-by-case record, with
six separate columns: native text, Firecrawl parse, Firecrawl extraction,
Llama agentic parse, Llama agentic_plus parse, and Llama extraction. Each
reviewed parse case includes exact raw text and reviewer-created offsets.
Those offsets are **not vendor field-citation metadata**. No aggregate accuracy
percentage is computed, and lexical successes cannot offset critical misses.

- **Hearing/economic marks (M1/M3):** both Llama outputs explicitly pair selected
  and unselected states with the correct labels. This is actual parse evidence,
  not the reviewer supplying checkbox repairs.
- **Proposed action (M2):** agentic explicitly marks amendment, but leaves the
  other alternatives implicit; the full case is partial. Plus explicitly marks
  amendment and identifies the other proposed actions as unchecked.
- **Blank final/effective choices (B1/B2):** plus retains unchecked states and
  blank values, supporting safe abstention. Agentic retains columns and labels
  but loses explicit negative option-state encoding. Neither asserts an
  effective date or final action in the retained parse.
- **Date roles (D1/D2):** both preserve handwritten SUBMIT DATE 12/27/2023 but
  omit the visible FILED stamp's DEC 27 2023. Equal date values do not permit
  substituting submit evidence for filing-stamp evidence. Firecrawl's retained
  parse preserves the stamp date, so this is a mixed result rather than a
  uniform Llama improvement.
- **Relative conditions (T1–T3):** both Llama parses retain the separate 20-day
  filing-anchored hearing-request condition, full requester eligibility/no-hearing
  circumstance, and 25-day comment clause. Neither adds a starting event for the
  public-comment clause or computes an absolute close. Rule 5.29 and EVEP also
  survive; these lexical successes are reported separately.
- **Vendor extraction:** configuration creation succeeded, but extractFile
  produced no structured fields/citations. Every Llama extraction case is
  not_demonstrated. No agent-authored object is substituted for vendor output.

The trial author's summary and independent matrix use a few categories
differently. Use the independent matrix consistently rather than mixing counts:
it treats native EVER as a transcription error, native preserved 20/25/eligibility
clauses as useful text/role recovery despite spacing, and Firecrawl's duration
phrase inside public_comment_anchor as a role/type error. The latter still
abstained on an absolute close; no computed deadline was fabricated. Unequal
prompt/schema coverage is explicit: older Firecrawl extraction did not request
a separate submit date or economic-impact field. No comparative failure is
inferred from such an unrequested field alone.

## Normalization and replay

`normalizer-audit.json` records code/validator hashes and actual results:

- Shared validation passes **19 artifacts, 7 observations, 9 exact quotes,
  0 visual repairs**. All seven observations remain `needs_review`.
- Both derived Markdown files exactly equal `/content/0/text` of their raw
  responses. **No trailing newline was added.** A markdown-only alteration is
  explicitly rejected even after its manifest hash is updated.
- Two isolated offline replays reproduce observations and diagnostics exactly.
  Code consumes the retained agentic_plus representation, not expected answers,
  Firecrawl model answers, or a visual-label repair file.
- Missing hearing duration, comment duration or eligibility in synthetic
  raw/derived-consistent fixtures yields nonzero exit and six partial
  `needs_review` observations with an explicit missing predicate.
- `filing_date` is withheld; the submit date is not substituted. No computed
  comment close or asserted effective date is introduced. Deterministic local
  mapping is explicitly distinguished from its model-assisted vendor input.

### P2 bounded limits to disclose, not actual-record errors

`/private/tmp/docketclock-llamaparse-comparison-2026-10-05/trial/normalize.py:22-27`
searches globally for checked labels and checks only that a proposed-action
heading exists somewhere. Two raw/derived-consistent synthetic mutations
therefore still exit 0 with seven observations and no special conflict diagnostic:

1. Mark both scheduled and not-scheduled hearing choices as checked: mapping
   still emits not_scheduled without surfacing the contradictory selection.
2. Move the checked Amendment cell into the TEMPORARY RULES column while leaving
   the proposed-action heading: mapping still emits proposal/amendment.

Neither condition occurs in the actual returned fixture. All outputs already
remain `needs_review`, so these limits do not invalidate the bounded comparison.
They **do** rule out describing the mapper as validating checkbox exclusivity,
table-section association, or general template safety. Disclose them in the
final narrative; broader production implementation is not required here.
The mapper intentionally contains no reusable filing-stamp extractor; its
withheld-date diagnostic is specific to these inspected outputs.

## Tool and measurement claims

Recorded wrapper intervals match their timestamps: **23,729 ms agentic**,
**36,086 ms agentic_plus**, and **123,877 ms until extraction timeout**. These
are single call wall times, not isolated service processing times or a speed
ranking. Upload time is separate. Timeout does not reveal backend completion
or charges; there was no retry.

No consumed credits, resolved parser version, job ID or field bounding boxes
were returned in these parse responses. `latest` is the requested version,
not a pinned resolved version. The exposed parse tool schema lacks form-enrichment
and bbox controls; that is a **connector/trial limitation**, not evidence that
the broader vendor platform lacks those capabilities. Extraction-tier prices
in tool descriptions are not observed billing. Page/region fields requested in
the extraction schema cannot be reported as delivered citations after timeout.

No source refetch, vendor call, installation, baseline/trial modification,
subagent, or additional task was performed by this review. Only reviewer-owned
files and isolated temporary copies were written. A broader corpus, stable
version/configuration, field-level citation support and a completed extraction
run remain untested. No overall vendor ranking or unattended readiness follows.

## Integrated draft review

Reviewed the parent draft at
`/Users/home/.codex/worktrees/e8f4/yokel/docs/research/state-rulemaking-spike/llamaparse-comparison/README.md`
and its sources.json. The nine checked integrated trial files (normalizer,
manifest, observations, both raw parses, both Markdown files, source PDF and
results) match the audited temporary trial byte-for-byte; hashes are in
`integration-check.json`.

The main partial-benefit verdict, adaptive-tier caveat, timeout interpretation,
seven review-required observations, timing numbers and separation of parser
output from local mapping are supported. Published pricing arithmetic is
correct given the rates recorded by the primary in sources.json. The draft
explicitly distinguishes published rates from billed usage and documented form/
region APIs from tested connector capabilities. Those external documentation
claims were compared against the primary's retained notes, **not independently
refetched** by this reviewer.

Final integrated follow-up:

- README now expressly discloses both checkbox-conflict/table-column mutation
  limits, their absence from the actual fixture and the review-required state,
  in addition to linking this review. The limits remain accurately bounded.
- **Earlier P2 wording resolved:** the consequences paragraph now separates
  Firecrawl link discovery/HTML processing from fetching and retaining original
  PDF bytes. It no longer implies this connector trial delivered original bytes.
- Inspected final verify.py and executed `python3 -B verify.py` in an isolated
  reviewer-owned copy of the integrated comparison and required baseline files.
  It passes: **22 baseline files unchanged, 28 copied files verified**, exact
  raw-to-Markdown identity, byte-identical normalizer/guard outputs, three
  omission guards, and shared validation of seven review-required observations
  with nine exact quotes and zero visual repairs. This independent rerun is
  recorded in `final-integration-verification.json`, including script/README
  hashes. No integrated file was modified.

**Final report verdict: no remaining material correction or blocker.** No
incorrect actual normalized record was found. The report preserves the partial
result, timeout uncertainty, unknown billing/resolved versions, agent-inspection
basis and untested broader API features. The two synthetic mapping limitations
remain disclosed; no broad production implementation or additional vendor run
is needed for this result. Published documentation claims were checked against
the primary's source notes, not independently refetched, as stated above.
