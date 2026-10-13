# Dashboard operations snapshot

All 110 checks pass for the eight retained complete jobs: A03–A05 both tiers and A06/A07 Agentic. The other 28 planned pairs are pending in this snapshot, not failures. No vendor, browser, or task calls were made, and no captures, references, results, or other review directories were modified.

The immutable manifest digest matches the primary-provided freeze. All 18 staged PDFs and 17 batch copies match frozen input hashes, byte counts, and physical page counts. The eight visible job IDs and fixture/tier pairs are unique. Captures equal dashboard ledger entries and map to the corresponding input metadata, submission events, successful status, file IDs, and tier/latest settings. The pilot precedes subsequent submissions and all submissions follow amendment4 adoption.

All 16 retained output files match their declared hashes and byte counts and the available original local downloads. JSON page counts, ordered page numbers, and page success flags match expected input pages. Output bytes are downloaded artifacts; configuration, status, and timing metadata are UI transcriptions rather than raw API responses. No exact HTTP transport provenance is claimed.

Submission-to-terminal-observation ordering passes. Retained download timestamp transcriptions provide earlier completion upper bounds for jobs whose later UI observations overlap subsequent submissions. Using these bounds, the maximum possible overlap is two. Actual provider start/end timestamps and exact completion order are unavailable; this is a conditional bound from the retained UI/artifact record, not a direct provider concurrency measurement. All observed statuses are successful, so the failure-stop threshold was not exercised. The primary-reported lock/pause state was not independently inspected through UI.

Five jobs include full dashboard timing text. Their queue, processing, full total, and smaller parser breakdown remain separate in the JSON report. A03 both tiers and A04 Agentic lack full timing. The existing dashboard_duration_seconds values describe the smaller breakdown and must not be relabeled full service duration. Submission-to-success-observation elapsed also includes user/interface delay.

The pilot lacks a full per-job configuration object; its configuration evidence is the primary note and preflight. Other captured UI configurations show empty parsing instructions and latest, with cache booleans differing by tier. save_images_screenshot=true despite the visible checkbox state is already disclosed. Exact setting equivalence across interfaces is not independently established.

The refreshed usage export is unavailable. The 1760-credit whole-phase estimate remains nominal; this snapshot makes no measured new-phase billing or currency-cost claim. Scoped secret-pattern scans found no matching sensitive values in the 65 inventoried files.

Evidence: snapshot-review.json records all checks, job timing fields, pending pairs, provenance gaps, and limitations. snapshot-artifact-inventory.json freezes inspected artifact hashes. audit_snapshot.py reproduces the offline checks and writes only this operations-review directory. Final refresh awaits the primary request after all 36 jobs settle.
