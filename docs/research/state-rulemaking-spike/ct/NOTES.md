# Connecticut bounded offline spike

The native open-comment route returned four records on October 5, 2026. PR2024-059 was absent. Its fresh detail history explicitly records two opened/closed comment-period cycles. The closed-event rows have Posted Dates of March 27, 2025 and October 2, 2026; those are posting metadata, while native AssociatedDetails supplies the candidate boundary timestamps. Absence did not supply any closure or withdrawal assertion.

## Acquisition

Seven successful public-source calls plus one sandbox DNS failure: four curl GETs and three Firecrawl scrapes. Native curl JSON is retained as original bytes. Direct detail HTML exposes the portal's JSON endpoint wiring but does not populate the dynamic widgets. The initial Firecrawl detail scrape returned HTTP 200 with an incomplete shell; a retry with both `waitFor: 3000` and `onlyMainContent: false` recovered summary/history. Each Firecrawl call reported one credit. Captures contain tool elapsed latency; native server Date headers provide retrieval timestamps. Firecrawl wall-clock times are rounded to the collection minute, explicitly labeled. The inherited preliminary open list was valid and structurally identical to the fresh one; it is retained with unknown retrieval time and is not the primary extraction source.

One extra GET beyond the roughly six-useful-call bound fetched `Search/getRMRHistory?trackingNumber=PR2024-059`, discovered in retained detail HTML. This earned its use: native history contains two distinct period GUIDs and explicit start/end timestamps, so core extraction for that record does not require rendering. The portal route is publicly accessible; this does not establish API documentation, support or stability guarantees. No such documentation was inspected.

## Parsing and interpretation

Run `python3 normalize.py` from any directory, offline. It reads only saved captures and writes 23 `state-spike-v1` candidates. Twelve observations come from the four native open-list rows; native historical window timestamps contribute four; rendered summaries/notes contribute seven. All evidence quotes are exact substrings of retained UTF-8 representations. Firecrawl Markdown/HTML are transformed, not original server bytes.

Native `/Date(milliseconds)/` clocks decode to UTC with their stated precision. PR2024-059 closes decode to `2025-03-28T03:00:00Z` and `2026-10-03T03:00:00Z`; these are the source's clocks, not independent legal corroboration. Rendered history dates are Posted Date metadata, retained in captures and results source-specific checks. They produce no participation-boundary or publication observations. Native exact opening clocks may reflect source processing; interpreting them as legally controlling opening times needs notice review. Historical window IDs use proceeding plus native period GUID. Open-list window IDs are explicitly provisional because that route exposes no period GUID.

PR2026-014's JSON close is `2026-10-12T03:45:00Z`; rendered Notes show October 11 at 11:45 PM. New York would align these, but the displayed text states no timezone, so the rendered observation keeps zone and UTC unresolved. The scrape's timezone metadata is collector metadata. Null citation fields, generic hearing widgets and notice titles containing hearing language produce no hearing/time assertions. The operational policy description's September 1, 2026 date stays a separate instrument assertion; its PDF was not fetched.

## Validation and remaining work

The primary's shared validator passes: 14 retained artifacts, 23 deterministic candidates, 23 exact quotes, zero shape/hash/evidence failures. Additional checks confirm unique IDs, two distinct historical window identities, inspected UTC closes, correct separation of history posting dates from boundary roles, no false hearing/withdrawal, and deterministic offline replay. `expectations.json` records inspected examples, not a blind benchmark. Validation proves research envelope integrity, not semantic entailment or publication readiness.

Firecrawl earned a rendered comparison and exposed a partial-response failure. It is unnecessary for the core native list/history path demonstrated here. Before unattended use, verify native summary/notes and current-period identity, notice authority, overlapping/reopened periods, staleness, field drift and failure monitoring. The current record has no emitted opening observation: its rendered history date is posting metadata and its native history was not fetched. Its closing window identity remains provisional. No shared SPEC change is required: the current envelope can preserve unresolved zones, distinct subjects and precision, while warning about interpretation. No state-coverage or production claim is warranted.

## Integration correction

Removed five rendered RMR History Posted Date observations previously emitted as comment boundaries: 28 candidates before, 23 after. Preserving date-only precision did not correct the date-role mismatch. The five rows remain exact retained captures plus metadata in results; they are neither participation boundaries nor publication dates. Native AssociatedDetails start/end candidates, their warnings, and the unresolved rendered Notes timezone remain unchanged. Shared validation and deterministic offline replay pass again.
