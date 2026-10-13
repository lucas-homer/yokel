# Final Firecrawl operational collection

All 20 frozen units have final Markdown captures. canonical-results.json is the canonical all-unit manifest; it points to each final response, exact Markdown, upload receipt, wrapper timing, first provider attempt and any original local failure. This establishes operational completion, not semantic accuracy.

| Outcome | Count |
| --- | ---: |
| First provider-attempt captures | 14 |
| Explicit first-attempt rate-limit rejections | 6 |
| Single authorized rate-limit recoveries, all successful | 6 |
| Final captures | 20 |
| Remaining failures or unsubmitted units | 0 |
| Earlier local upload-harness failures, retained separately | 4 |

The initial local failures involved four successful setup calls and zero HTTP uploads or final parse calls. execution-amendment-1.json authorized one corrected pre-job attempt for those four inputs. recovery-1 then produced eight captures and six explicit rate-limit failures, triggering the stop rule; already-in-flight B04 was retained. execution-note-2.json authorized paced completion and one proven pre-job rate-limit recovery per rejected input. initial-remaining completed B05–B10 successfully. rate-limit-recovery completed A05,A06,B01–B04 once each. No timeout, ambiguous accepted job, or content failure was retried. The primary clarified that fresh upload references were also allowed when earlier transient references were unavailable; that reason is retained in rate-limit-recovery/recovery-eligibility.json. The expiry wait was cancelled before any recovery provider call.

All setup and final parse requests in the two paced runs used one global gate with at least 7 seconds between callable request starts, accounting for both phases against the observed request limit. At most two operational pipelines were active. No purchase, plan upgrade or credential change was made. Existing failed attempts and historical results remain intact; canonical-results-before-rate-recovery.json preserves the earlier stopped-manifest snapshot.

Across all runs: 30 setup requests, 24 successful HTTP uploads, 24 final parse requests, 20 nonempty Markdown captures. Four of the final parse requests were explicit rate-limit rejections; two other rejections occurred at setup. Successful returned creditsUsed values total 34, matching the 34 frozen input pages across the twenty final captures. Setup/failed-call usage was not reported, so total credits charged remain unknown. Per-unit actual reported usage and scrape IDs are retained; no parser version is invented.

Timing limitation: recorded request/capture timestamps precede request pacing. Pipeline elapsed_ms and parse wall_ms values are wrapper wall times; paced values include local request queue delay and capture overhead. They are not isolated API latency. Actual dispatch timestamps are unavailable. Captures were not changed or jobs rerun to repair timing.

Verification passed: every final Markdown matches its retained response byte-for-byte, including terminal newline state; all 141 frozen companion file hashes and the freeze checksum match; every upload receipt matches the frozen input hash; observed parse-wrapper intervals never exceed two; final capture pointers resolve. All twenty successful final tool-response objects remained unmodified. Upload-instruction responses are intentionally sanitized, and credential-pattern scans of JSON captures found no signed upload URLs or raw signing-policy values.

Only the Firecrawl artifact lane changed. Sources, adjudicated references, settings, dependencies, application code and deployments were untouched.
