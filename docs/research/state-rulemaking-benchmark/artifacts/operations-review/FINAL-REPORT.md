# Independent operations audit

Final evidence is ready for analysis with the stop-boundary finding and measurement limits below disclosed. The audit ran 152 checks: 151 passed and one timestamp-based stop check failed. No vendor calls, retries, extraction scoring, source changes, or vendor-artifact edits were made.

The primary-provided freeze SHA-256 remains `900f21e8a75d50444f12a0e3814d665a4f401a0d689194465d0b00467a762946`. All 141 frozen files match. The 20 distinct frozen inputs and all actual upload/parse mappings checked match the immutable corpus. Firecrawl's final canonical response, markdown, capture, outcome, upload receipt, and first-attempt paths resolve consistently for every fixture. All 100 raw artifacts inspected in the earlier review remain unchanged.

| Operational evidence | Firecrawl | Llama |
|---|---:|---:|
| Planned parse calls | 20 | 40: 20 per tier |
| Final endpoint attempts | 24 | 4 |
| Returned parse outputs | 20 | 0 |
| Successful HTTP uploads / uploaded units | 24 uploads | 2 units |
| Setup requests including original local failures | 30 | Not comparable to Firecrawl's two-stage setup |
| First provider successes | 14 | 0 |
| Explicit rate rejections recovered once | 6 | 0 |
| Tool timeouts | 0 retained final failures | 4 |
| Unattempted planned calls | 0 | 36 |
| Reported successful-call credits | 34 | Unknown |
| Maximum observed parse concurrency | 2 | 2 |

Firecrawl's original four local upload-stage failures remain separate from provider results. The corrected preflight and all retained passing preflights resolve the historical preparation schema mismatch. Recovery-1 follows the prospective transport amendment. The paced B05-B10 continuation follows the second authorization. The six rate recoveries cover exactly A05/A06/B01/B02/B03/B04, follow the third clarification, and retain their explicit earlier rejections. Each has one recovery pipeline with identical input bytes and parser settings. No inspected earlier rejection returned an accepted job identifier. Fresh uploads for unavailable transient references are authorized by execution-note-3.

All 20 Firecrawl markdown files match the retained response strings byte-for-byte, including hashes, byte lengths, and terminal-newline flags. The 24 final captures declare unmodified response objects with no sanitization exceptions. This declaration is not independently comparable to original HTTP bytes or a separately retained original tool envelope. Upload setup envelopes intentionally sanitize signed URLs, references, headers, and form credentials. Transient references therefore cannot be replayed directly; local hashes, uploaded byte counts, and HTTP receipts support the mapping.

Llama's four captures match their retained tool envelopes and derived response text exactly. Requests use the matching uploaded file IDs, requested tier, `markdown: true`, and `version: latest`, with no page subset or hints. Its ledger accounts for every planned fixture/tier pair. The third completed timeout triggers the stop; the fourth was already in flight. Backend completion and billing remain unknown, so zero returned outputs do not establish parser content quality.

## Retained finding

Recovery-1 B02 ended at `2026-10-06T00:56:57.477Z`, the third consecutive failure; B04 began at `2026-10-06T00:56:57.494Z`, 17 ms later. This fails the timestamp-based no-dispatch-after-threshold check. The harness may have consumed B03's completion and launched B04 before consuming B02's already-completed promise. Completion-consumption timestamps are absent, so that distinction is unresolved. B04's subsequent explicit setup rejection and authorized single recovery are retained and verified; recovery does not erase the stop finding.

For future runs, record actual dispatch and completion-consumption timestamps, and drain already-settled completions before launching replacements. Report this run's stop compliance with the finding, rather than as an unconditional pass.

## Measurement and security limits

Firecrawl paced timestamps precede the pacing wait; recorded durations include queue delay and wrapper overhead. They cannot establish actual endpoint dispatch spacing or isolated vendor latency. Inspection shows a shared 7000 ms gate for setup and final calls in paced phases. Pipeline and parse intervals establish an observed upper concurrency bound of two. No calls were rerun to obtain cleaner timing.

The 34 reported Firecrawl credits are a successful-call subtotal across 34 page instances. Setup and failed-call usage is not reported; total usage and billing cannot be inferred. Published pricing assumptions remain separate from actual usage. Both Llama tiers request `latest`, which is not a verified backend release pin.

The final inventory contains 269 provider files. The JSON/text/code scans found no matching unsanitized credential or signed-upload values. This is a pattern-based artifact check, not proof about transient memory or external logs. Sensitive values were not printed or copied into review outputs.

Evidence: `final-review.json` contains every check and limitation; `final-artifact-inventory.json` records inspected file hashes and sizes. `review_final.py` reproduces the offline final checks and writes only operations-review. Historical preparation and completed-phase reports remain retained.
