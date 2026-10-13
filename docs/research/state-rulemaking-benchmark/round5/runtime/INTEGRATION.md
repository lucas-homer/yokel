# Round 5 native-only runtime handoff — runtime READY for independent review

Consumes A's `pipeline.py` with unchanged `round4.sources.v1` manifest and R4 case interfaces. **Round 5 overrides copied R4 fallback language: only native inputs and TypeSafe Jev operations are permitted. No OCR is acquired, no OpenRouter credential is read, and other-provider ledger operations are refused.** Original PDF identity and page count are mechanically checked; no native extraction or source-truth adjudication occurs here. The collector owns extraction provenance and scope declarations.

`routing_policy` pins the pipeline's exact published soft/hard issue sets. Only explicitly approved role/qualification/form-association issues can be soft; unknown issue names remain hard. Exact values, supported calendar normalization, spans, scope, size, source hashes and conditional/relative/lifecycle conflict guards remain mandatory. The historical four Choice rubrics and `jev-1.13.0` adapter are byte-identical to R3. The frozen policy prefix supplies full-notice scope plus the explicit actual-unconditional-DATE projection contract; no confidence cutoff is tuned. A qualified paragraph quotation cannot turn a contingent date into an unconditional projection.

Candidate competition is resolved conservatively for both fields, even if no multiplicity issue flag exists: one distinct value must pass all four judgments, and each competing candidate must either support that same value or have a completed positive `role=mismatched`. An unresolved duplicate, failed/unprocessed alternative, or second supported distinct value holds the field in review. Provisional case judgments never constitute terminal decisions. Final R4-compatible `shadow-observations.json` retains terminal status/disposition/readiness consistently; `production_eligible=false`, `action_ready=false`, source fidelity unverified and completeness requiring independent audit always remain.

Caps: eight documents, 40 original PDF pages, 80 Jev POST cases, $0.10 nominal/accounted budget. Full original native text enters each case. Text >30,000 code points, case >50,000 UTF-8 bytes or request conservatively >20,000 input tokens routes to review without clipping. A maximum 80 × 20,000 input-token reservation is $0.0672 at the pinned $0.042/M input rate; output tokens free. Actual usage × rate is an estimate, not a verified invoice. Budget charge sums per-operation max(reserve, observed estimate), preserving pending unknown-cost reserves. Unexpected received overrun latches before any next operation.

The append-only fsynced ledger retains identity, exact request, intent, HTTP status/latency, raw response, parsed dimensions/usage and costs. No POST retries, redirects, provider/model fallback or SDK retry are enabled. Completed operations reparse locally without POST. Received-but-unparsed valid responses can reparse locally; uncertain intent, HTTP failure, invalid schema/usage, credential echo or drift stops for external reconciliation. A nonblocking file lock prevents concurrent runners. Operation IDs cannot be reused with changed identity/request. Pause boundaries retain completed cases and do not publish a whole-run completion receipt.

## Code freeze and dry run

Bundled runtime only, no installs or `.env`:

```sh
cd /Users/home/.codex/worktrees/e8f4/yokel
/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -B docs/research/state-rulemaking-benchmark/round5/runtime/offline_checks.py
/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -B docs/research/state-rulemaking-benchmark/round5/runtime/run_pipeline.py --pipeline docs/research/state-rulemaking-benchmark/round5/pipeline/pipeline.py --prepare-implementation NEW_IMPLEMENTATION_RECEIPT
```

`implementation-pins.READY.json` is the final runtime receipt after pipeline contract alignment and 26 passing tests. `development-controls.json` and `development-controls/` retain six synthetic full-entrypoint executions: DATE/EMAIL positive, paired real conditional date, clock-qualified date, relative-window explicit email, hearing-role alternative and conflicting windows. All passed their assertions with fake transports; no paid calls. It pins runtime, ledger, frozen adapter, credential wrapper, pipeline, available interface/schema/routing policy and primary contract guidance, plus Python/pypdf versions and complete semantic policy. Changed dependencies block execution/resume. Primary must create a NEW reviewed receipt if integration changes; never overwrite a frozen one.

After collection and independent source-label Freeze B:

```sh
/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -B docs/research/state-rulemaking-benchmark/round5/runtime/run_pipeline.py --freeze READY_RECEIPT --manifest FROZEN_SOURCE_MANIFEST --source-root SOURCE_ROOT --output NEW_EXECUTION_DIRECTORY
```

Dry run validates sources and native proposals without credential/env reads, provider calls or execution output creation.

## Live authorization and resume — primary only

Supply an external label-freeze receipt SHA via `--source-labels-freeze-sha256`; this runtime never reads label files. Authorization must have exactly these six keys:

```json
{"schema_version":"round5.live-authorization.v1","implementation_sha256":"SHA256_OF_READY_RECEIPT","manifest_sha256":"SHA256_OF_MANIFEST","source_labels_frozen_before_outputs":true,"source_labels_freeze_sha256":"SHA256_OF_EXTERNAL_FREEZE_B_RECEIPT","nominal_budget_usd":0.1}
```

The external label receipt hash is checked against the separately supplied CLI hash and bound into immutable run pins. It is an attestation, not independent proof of freeze timing; primary preserves the external evidence. Sources/code/authorization/label binding and budget must match exactly on resume.

Primary invokes `sh runtime/run_with_1password.sh` with the dry-run arguments plus `--authorization AUTHORIZATION --source-labels-freeze-sha256 FREEZE_B_SHA --live --max-new N`. Wrapper resolves the single previously authorized TypeSafe 1Password reference, without saving its value. It must not be run for credential tests. Default N=1 supports a bounded pilot; maximum N=80. Reuse identical run path/pins to resume. This child makes no provider calls.

## Public API verification

Live documentation checked October 7, 2026: [HTTP API](https://docs.typesafe.ai/api), [Choice](https://docs.typesafe.ai/primitives/choice), [models/pricing](https://docs.typesafe.ai/models), [state](https://docs.typesafe.ai/concepts/state), [pre-parsed value extraction](https://docs.typesafe.ai/cookbooks/pre_parsed_value_extraction_cookbook). Endpoint `POST /v1/systemone`, versioned model, state/questions map, Choice criteria, answers/probabilities/confidence and token usage remain compatible with the frozen adapter. Price is $0.042/M input, output free. HTTP docs recommend retry for overload; this authorized experiment deliberately retains failures and makes zero automatic POST retries.

No fresh source/label read, provider call, application change, install, build, or prior-round edit is performed by this child. Synthetic controls establish implementation reachability and safeguards, not model accuracy or fresh-source recovery.
