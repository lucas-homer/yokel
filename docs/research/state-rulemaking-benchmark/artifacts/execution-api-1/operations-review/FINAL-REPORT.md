# Final REST operations and usage audit

All **779 checks pass**. The REST phase has 28 completed jobs, no failures, pending jobs, or active jobs. The independently checked evidence is ready for the primary's final integration. This audit made no provider/UI calls, credential accesses, submissions, or retries, and wrote only execution-api-1/operations-review.

All 141 frozen artifacts and all 629 files in the original retention manifest match their recorded hashes and sizes. The prior eight-job dashboard audit still has its 110 passing checks and unchanged inventoried files. Original connector, Firecrawl, recovery and review baselines remain intact, including their historical operational findings.

The 28 REST fixture/tier pairs complement the 12 prior completed pairs, with 40 distinct job IDs and no duplicate completed-job reparse. The 15 REST input file IDs are distinct across fixtures; sharing a file across its two tiers is intentional. Actual local bytes, input hashes and expected page counts match the frozen units. Remote file verification proofs retain matching downloaded hashes; downloaded remote PDF bytes are not independently retained.

Each completed REST capture reconciles accepted POST job ID and durable intent/hash/tier metadata, file proof, durable request config, state, terminal HTTP response, successful page evidence, and exact output hashes/bytes. All 28 Markdown outputs match the whole provider markdown_full UTF-8 string exactly, without joining pages or using supplementary JSON to repair content. Page ordinals cover the full expected input. No operation anomalies are recorded or found.

The audit checked 223 main-phase HTTP receipts, plus the 12 historical GET refresh receipts and corresponding bodies. Retained response JSON bodies equal receipt objects, with consistent unchanged-body versus transient-URL-sanitized flags. Headers and complete HTTP request bodies are not retained; durable request config and echoed POST intent metadata provide the request evidence. Sanitized expanded results remain explicitly distinct from unchanged response bodies.

Amendment5 adoption precedes the pilot and the runner SHA matches its recorded pre-pilot SHA. The successful A06 Plus pilot reports 90 credits and precedes the continuation gate. Actual dispatch/terminal-observation bounds support maximum concurrency of two. The pilot runs alone; every later pair starts after prior terminal observations. Completion-consumption order matches durable observation timestamps. No live failures occurred, so the three-consecutive-failure stop was not exercised; retained code/offline checks supply separate stop-policy evidence.

| Provider-returned usage | Credits |
|---|---:|
| New REST jobs: 28 | 1,555 |
| Historical jobs: 12 | 315 |
| Full comparison: 40 | **1,870** |
| Agentic across 20 fixtures | 340 |
| Agentic Plus across 20 fixtures | 1,530 |

All 40 jobs return usage credits with no missing values. The new 1,555-credit subtotal matches the nominal REST estimate independently; each returned job agrees with its page count and nominal tier credit rate. The original four-job subtotal is 110 credits and matches the prior export by job ID. Historical refresh IDs and input hashes match the four original recovered jobs plus eight unchanged dashboard captures. These are measured returned job-usage credits, not a currency invoice or proof of all account charges. full40-usage.json lists the reconciliation by job.

Historical refreshes are GET-only and retain raw job_metadata timing/latency and transitions. These newly retrieved fields remain separate from older dashboard header/parser-breakdown durations; old captures are not relabeled or edited. Backend job timing, actual HTTP latency, and wrapper observation elapsed remain distinct in the audit evidence.

The REST nested configuration and legacy dashboard configuration are not claimed equivalent. Undocumented legacy high_res_ocr and header/footer fields are omitted. Requests use latest with no prompt or page subset; returned resolved versions and direct terminal job file_id are unavailable in observed results. Mapping therefore relies on durable requests, verified files and accepted POST metadata; no backend release pin is inferred. Separate interfaces and execution dates limit causal comparisons.

Runner inspection confirms default verified HTTPS, nonredirecting signed-download handling, and no TLS weakening. The runtime CA repair is primary-reported rather than reexecuted. Scoped artifact secret-pattern scans found no matching sensitive values; this does not establish behavior of transient memory or external logs.

Evidence: final-review.json contains all 779 checks, 28 job records, 12 historical usage/timing records, pair barriers and limitations. final-artifact-inventory.json records inspected artifact hashes. full40-usage.json records the per-job credit reconciliation. audit_final.py reproduces the offline final checks and writes only this review directory. Earlier snapshot reports remain retained.
