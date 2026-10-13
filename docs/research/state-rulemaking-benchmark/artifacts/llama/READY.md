# LlamaParse lane readiness

Status: prepared; waiting for parent's frozen corpus manifest. No uploads, signed upload URL requests, or vendor parse jobs have been started for this round. Reference answers have not been read.

## Frozen execution rules

- Exactly A01–A10 and B01–B10, excluding the previous Mississippi calibration PDF hash.
- Validate every retained input PDF hash, byte length and 1–4 page count against parent-frozen metadata; sum at most 80 pages per tier. Use identical local input bytes for both tiers and Firecrawl, including any retained excerpts.
- Upload once per input with getUploadUrl(purpose=parse), then a multipart POST of that local file. Keep signed URLs in memory only; record sanitized upload attempt timing, local SHA, byte length, HTTP outcome and returned file ID. Never retain the upload bearer URL or token. No fetch-by-source-URL fallback.
- For each of 20 file IDs call parseFile twice, once agentic and once agentic_plus, with markdown=true and version=latest. Omit pages to process the complete bounded input; no page-number indexing ambiguity. No hints, custom prompts, reference labels, schema extraction, indexes or new credentials.
- Batch at most two active parse calls, then inspect and persist both outcomes before the next batch. Record completion order and count all operational failures across tiers. Stop and latch provider suspension after three consecutive failures; pending calls remain unattempted. With at most two already active, a failure may arrive while the paired call is in flight; do not start a new call after the threshold.
- No retry of a timed-out potentially billed parse; backend state and billing remain unknown. Only one recovery for a proven pre-job upload/network failure is allowed, logged separately. Unknown outcomes are not asserted failures of parsing accuracy.

## Tool/version limitation

Live callable schemas are retained in capabilities.json. parseFile accepts an arbitrary version string or latest, but this plugin exposes no released-version listing or version-discovery metadata operation. No verified released identifier is available to select without speculation. Use latest consistently for the complete run; preserve any actual returned version/job/usage metadata and otherwise mark it unknown. Do not infer price from credits or invent backend versions. The tool also does not expose form enrichment or bounding-box options.

## Offline capture harness

harness.py uses only the Python standard library. It makes no network calls. After parent authorization, adapt only frozen fixture IDs/input paths/hashes/page counts into an input-list JSON (no reference_fields), then run:

    python3 harness.py prepare input-list.json --freeze-manifest /path/to/parent-frozen-manifest.json

This creates an immutable 40-call execution plan with its parent freeze-manifest hash. Actual physical-page counts should be cross-checked with existing bundled pypdf before upload; the standard-library planner validates the declared frozen counts and byte hashes.

For each completed tool attempt, capture an envelope with fixture_id, tier, request, uncorrected response, started_at, ended_at, elapsed_ms, input_sha256, input_page_count, file_id and outcome (completed, operational_failure, timeout_backend_unknown). Preserve returned metadata inside response; normalized reported_usage/job_id/version fields may be null when absent. Feed the JSON through stdin to:

    python3 harness.py record A01 agentic

Each capture path is write-once under runs/fixture/tier. Successful text blocks are saved byte-for-byte separately; the full raw tool response remains authoritative. Inspect whether the block is markdown versus an error/status message before classifying completed. Record rejects known signed-token URL forms. No raw signed upload response is retained.

    python3 harness.py status

Status reports recorded/completed/pending counts and a latched three-failure stop. The agent-controlled tool loop enforces the two-call concurrency cap and the stop condition before scheduling each batch; the offline helper is not an unattended vendor scheduler.

## Validation and readiness gaps

Status command passed with zero planned and recorded calls. No source corpus is ready or has been frozen, so input-list adaptation, PDF page-count verification and provider execution remain pending. No new vendor calls are needed to establish readiness. Historical absolute paths will be retained as acquisition provenance; captured result inspection is local to this lane. No installs or runtime setup occurred.
