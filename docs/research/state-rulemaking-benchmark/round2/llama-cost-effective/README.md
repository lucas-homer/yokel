# Round2 LlamaParse Cost-effective runner

Offline preparation is complete: 20 frozen exact input PDFs, 34 pages, nominal 102 credits. Eighteen fake-API state-machine checks pass. No key access, authenticated requests, uploads or parse jobs were made. The original runner and all 629 retained baseline files are unchanged. All outputs for this arm stay beneath this directory; other round2 arms and prior references/results are outside its write scope.

The standalone run_cost_effective.py defaults to dry-run. It reads the shared artifacts/corpus-freeze.json and verifies its fixed digest, all 141 frozen files, exact input hashes/bytes and the 20/34-page bounds. It uses source-a/source-b input.pdf bytes directly, including bounded excerpts, never full-register originals. plan.json records the immutable order, candidate IDs/provenance, settings and estimate.

All 20 fixtures have historical file-ID candidates: preferentially the previous REST verified files, then dashboard captures, then original recovered-job configuration. Candidates are not currently verified live. Before reuse, the runner checks selected project metadata and SHA256 of downloaded remote bytes; signed URLs remain transient and receive no API Authorization header. Inaccessible, expired or mismatched candidates pause execution rather than silently upload a replacement. Primary may explicitly reconcile an externally known uploaded file with --attach-file after byte verification; uncertain uploads/submits are never repeated blindly.

Parsing configuration matches the prior REST runner except tier=cost_effective and a separate round2-llama-cost-effective reconciliation tag. This tag is bookkeeping, not a prompt. latest, cache enabled, cost optimizer disabled, screenshot output, HTML-table output, and other nested options are retained. There are no instructions, target-page limits or expected-answer hints. Current [create documentation](https://developers.llamaindex.ai/reference/resources/parsing/methods/create/) supports cost_effective; [pricing](https://developers.llamaindex.ai/llamaparse/general/pricing/) lists 3 credits/page. Requested latest is retained for comparison; documentation's dated mapping is not claimed as the actual resolved backend version.

Execution state, HTTP receipts and exact Markdown/expanded JSON/usage captures live in execution/ only. Unique persistent intent tokens and job IDs prevent duplicate submits across restarts. Lost parse responses reconcile through paginated GET listings; zero/multiple matches pause without a new POST. Lost upload responses pause for explicit reconciliation. At most two accepted jobs run, pairs drain before replacements, and three consecutive terminal operational failures latch a stop while existing jobs are retained. No blind timeout retry or automatic stop reset exists. A process lock prevents simultaneous runner instances. Finite invocation budgets preserve active IDs.

Output Markdown preserves the exact whole provider markdown_full UTF-8 string. Page count, identities/success and available returned tier/file/version fields are checked; missing direct metadata is recorded honestly. Expanded JSON/HTTP bodies are supplementary and record any transient-URL sanitization. Actual returned usage and provider/backend timing are retained separately from request wall times. Default authenticated invocation submits at most one new job for the primary's pilot; the complete 20-job plan remains durable.

Offline use (no environment key read):

```sh
python3 run_cost_effective.py ../../artifacts
python3 offline_checks.py
```

After primary authorization, execute using the bundled trusted Python and the existing non-secret 1Password reference. This example is deliberately a one-job A01 Cost-effective pilot, not a preparation action:

```sh
PYTHON_BIN=/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
sh run_with_1password.sh 'op://Private/LlamaParse API Key/credential' \
  ../../artifacts --execute --project-id VERIFIED_PROJECT_ID \
  --ack-api-v2-differences --max-new-jobs 1 --max-run-seconds 300
```

Primary checks accepted job/file mapping, page evidence, exact Markdown, actual usage and configuration/version limits before expanding. Then the same command can use --max-new-jobs 20; completed/pending state controls eligibility and no completed job is resubmitted. --execute --reconcile-only performs GET-only reconciliation/polling against existing state and never uploads/submits. The wrapper resolves a key only into the process environment with op run, disables shell tracing and never prints or writes the key. Do not disable TLS verification.

READY.json records readiness and baseline validation; offline-checks.json records the 18 tests and runner SHA; api-documentation.json records verified public documentation links and limitations. Live account access, candidate accessibility, successful Cost-effective output and measured usage remain pending the primary's pilot.
