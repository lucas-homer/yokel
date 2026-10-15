# Mississippi PDF lane

This is a selected one-page research fixture, not a complete proposal package. The form says the full rule is attached, but this PDF contains only the notice form. Source search coverage is untested.

## Acquisition

The inherited official PDF bytes are retained and SHA-256 hashed. Direct fresh curl initially failed at sandbox DNS (exit 6). An authorized escalated retry succeeded; fresh PDF bytes are SHA-256 identical to the inspected inherited original. Both original files, HTTP headers and failed/successful attempt evidence are retained. Firecrawl returned HTTP 200 metadata with one total page on both bounded maxAge=0/maxPages=1 calls. Firecrawl itself returned transformed content, not PDF bytes; the independent successful curl retry establishes byte identity for this retrieval.

## Parsing versus interpretation

Native pypdf text has an existing imperfect OCR layer: filing stamp and submit date disappear, spacing degrades, EVEP becomes EVER, and amendment X drifts away from its option. Firecrawl recovered readable clauses, the stamp and the amendment mark, but dropped oral-proceeding checkbox associations. It also emitted both economic-impact alternatives without their marks. A separate visual review of the rendered original supplies four explicitly manual observations: proposal event, amendment rule action, hearing not scheduled, filing date.

The fresh prompt-only JSON trial is retained uncorrected. No schema-enforced API behavior was tested. It distinguished 20-day hearing requests from 25-day public comment and did not invent closing or effective dates. Its public_comment_anchor repeats the period clause rather than identifying an anchor. Unknowns are strings instead of nulls, evidence is not associated with each field, and two of four evidence quotes fail exact-substring matching. A correct hearing-status answer does not establish checkbox extraction reliability because the markdown loses the mark.

## Offline fixture

Run `python3 normalize.py` from any working directory. It checks manifest hashes, parses captured Firecrawl clauses with guards, and loads only explicitly reviewed visual assertions. It does not read expectations or model output as answers. Eight observations: agency, rule citations, two separate relative durations, proposal event, amendment rule action, hearing status and filing date. Four are deterministic clause extractions; four are manual_visual. Canonical values are event_type=proposal, rule_action=amendment and hearing_status=not_scheduled. There is no comment_close assertion and neither duration has a computed date. The hearing-request anchor is the captured filing clause; public-comment anchor and day basis remain null.

## Tool value and remaining comparison

Firecrawl earned limited use here as a readable PDF conversion and bounded extraction tool (one reported credit for markdown, five for JSON). It does not replace original-byte retention, checkbox review, exact evidence validation or temporal interpretation. The trial does not establish unattended publication readiness. LlamaParse was unavailable, not tested and not judged inaccurate. A competing parser must improve checkbox association, stamp/handwriting recovery, field-level exact provenance and abstention on unresolved date roles; attachment coverage is a separate acquisition problem.

The primary clarified canonical event/hearing enums and added the rule_action predicate; this lane follows that shared clarification. Model outputs are retained as trial artifacts rather than admitted to normalized observations. All work stays in this lane, without installs, environment creation, app builds or repository changes.

Missing critical template clauses or reviewed assertions produce an explicit normalization-diagnostics.json, partial observations marked needs_review, and a nonzero exit. No value is fabricated for a missing clause. Raw model/parse captures and the pre-extraction expectations remain unchanged.

Final eligibility correction: the hearing-request observation includes the exact conditional sentence restricting a required oral proceeding to a request by a political subdivision, an agency, or ten or more persons when no proceeding is scheduled. A scope warning makes clear that eligibility is retained in evidence, not yet in a separately typed field; no unconditional individual right to require a hearing is asserted. Missing this eligibility clause now also prevents emission of the duration observation and triggers explicit review failure. Both duration-removal checks and the eligibility-removal check passed. Final shared validation: 13 artifacts, 8 observations, 5 exact-text evidence items, 4 visual evidence items.
