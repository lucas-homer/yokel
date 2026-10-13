# Firecrawl recovery result

The primary-authorized bounded recovery in execution-amendment-1.json was executed once, in recovery-1. The original A01–A04 failures and results.json remain intact. No further retries or submissions were made after the second stop.

All twenty frozen units are accounted for in canonical-results.json:

- Captured: A01–A04 and A07–A10 (8).
- Provider rate-limit failures at final parse: A05, A06, B01, B02 (4).
- Provider rate-limit failures at upload-instruction setup: B03, B04 (2).
- Not submitted after stop: B05–B10 (6).

The failure text explicitly says `Rate limit exceeded`; structured error_code is `INVALID_ARGUMENT`. Preserve both rather than interpreting this as a document-content rejection. The recovery completion order was A01,A02,A04,A03,A05,A06,A07,A08,A09,A10,B01,B03,B02,B04. B01,B03,B02 reached three consecutive failures; B04 was already in flight and was retained. Starts followed frozen order with two operational pipelines.

Denominators: original setup calls 4, original HTTP uploads/final parses 0; recovery setup calls 14, successful HTTP uploads 12, final parse calls 12, nonempty Markdown captures 8. Across runs, setup calls total 18 and final parse calls total 12. Every upload succeeded, with exact frozen hash receipts. Successful outputs cover 12 frozen input pages. The 8 captures are operational evidence, not a semantic quality verdict. Neither 8/20 nor 8/14 should be presented as content accuracy; six units were unsubmitted and six were rate limited.

Actual returned creditsUsed values sum to 12 across eight successful responses. Setup and failed responses did not report usage, so the total charge is unknown. Per-call start/end times, pipeline/parse latency, usage and scrape IDs are retained. Parser-version pinning is unavailable in the callable schema; no version is invented.

Validation: all 141 frozen source/reference companion files and the freeze checksum still match; every successful markdown.md matches the response string byte-for-byte, including terminal-newline state; observed final-parse concurrency never exceeded two. Final response objects are retained in parse-response.json, with any credential echo handled by the recorded redaction exception; all eight successful final response objects remained unmodified. Signed upload instructions are absent from local captures; upload setup records are explicitly redacted. The canonical manifest points to each final capture or failure and the initial local attempt where present.

Only the Firecrawl lane was changed. No sources, reference answers, scoring settings, package dependencies, environment files, server code or deployments were changed.
