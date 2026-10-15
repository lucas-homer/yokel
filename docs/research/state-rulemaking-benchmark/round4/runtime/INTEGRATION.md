# Round-four runtime handoff

`run_pipeline.py` orchestrates the frozen automated proposer: native text → deterministic gates → Jev → conditional Mistral OCR acquisition → the same proposer/gates/Jev → conservative channel merge. `jev_frozen.py` is a byte-identical copy of the final round-three adapter (SHA `8a0069d19f0fda7eaeac690c59749029b3ccea71fc07dfc2f8d311d2d872a59e`). Jev's model, four rubrics and categorical conjunction are unchanged. Only its scoped-excerpt policy prefix changes to the entire acquired notice, without claiming independently verified PDF fidelity or completeness.

This child read no fresh sources or references and made no provider calls. Implementation/source-label freezing and actual execution belong to the primary.

## Source boundary

Use the pipeline's published `SOURCE-INPUT-CONTRACT.md` / `source-input.schema.json` exactly. Manifest keys are `schema_version: round4.sources.v1` and `documents`. Each record has exactly `document_id`, `channel`, `text_path`, `text_sha256`, `pdf_path`, `pdf_sha256`, `pdf_pages`, `scope`, `native_page_map_known`. Paths are relative to the manifest directory and confined to `--source-root`. Opaque IDs are `doc-` plus 12 lowercase hex characters. The runtime begins with native channel only; OCR text becomes a separately recorded fallback proposal. Evaluator labels, scan classifications, expected field counts, decisive reviewer spans and unknown extra keys are rejected, never passed to the model.

The runtime verifies original bytes and actual PDF page count before calls. Available bundled pypdf supplies mechanical per-page embedded-text character counts and image XObject presence. It does not adjudicate content. Fallback triggers below 40 nonspace embedded-text characters on any page, below 200 on a page with an image, unknown inspection signals, missing field candidates, unresolved candidate judgments or structural review routes. Thus some native text does not prevent fallback. Exact thresholds, Python/pypdf versions and issue policy are pinned in the implementation receipt. Image parts never enter Jev. PDF image detection is a bounded XObject/Form traversal; it is a heuristic, not a complete scan classifier.

Fallback decision is written immutably before OCR payload construction/response use, and its hash enters the OCR operation identity. Scope `slice` or `unknown` remains source review: OCR of the same PDF cannot restore missing notice scope. Full acquired notice text enters every Jev case. Text beyond 30,000 code points or the serialized/request limits routes to review without clipping; no large duplicated case bundle is produced for over-limit notices.

## Deterministic and semantic gates

Runtime's decisive issue policy is stricter than the proposer's diagnostic `soft_issues` array. **Only** `submission_role_unverified` and `written_comment_role_unverified` ordinarily clear through Jev. Conditions, competing temporal cues, lifecycle, source scope/corruption/page-count problems, invalid/ambiguous calendar values, unsupported email syntax, multiple date values and unknown issue codes remain hard review, even if a model might favor them. These decisions are encoded in `SOFT_ISSUES`, `HARD_ISSUES` and the receipt; never trust the proposer's field_disposition alone.

The reviewed email exception permits classification of `multiple_email_candidates_require_role_resolution`. Exactly one distinct submission value must pass all four Jev judgments; every alternative candidate must have a completed operation and positive `role=mismatched`. Any insufficient, failed, unprocessed, same-value unresolved or other supported competitor keeps all candidate destinations in review. Final per-case outputs and channel results share the same resolved classification; raw provider judgments remain immutable in the operation ledger. Positively classified other-role addresses do not spuriously request OCR after destination resolution.

Exact value spans and context spans are checked against the complete parser source. The entire value span must lie inside its declared context: a year after a blank line or form-feed cannot complete an earlier date. A single-line wrap within the same paragraph is permitted. Candidate email values must equal the literal extracted span exactly; no local-part normalization/repair. A typo already embedded in the parser text remains a source-fidelity blind spot. Jev confidence remains a diagnostic concentration statistic, not calibrated correctness. No new cutoff is tuned.

Channel merge distinguishes no native candidate from unresolved evidence. Empty native + supported OCR may yield a text-supported observation. Two incompatible supported values force review. Any unresolved candidate in either channel also blocks a supported candidate in the other channel, including identical values when conditions/lifecycle/scope might have been lost. `channel_disagreement_fields` records actual incompatible values; `channel_unresolved_fields` separately records unresolved evidence. Both observations remain retained. Every merge downgrade consistently sets shadow_status/disposition to review and action_readiness to not_ready. Channel-case records are explicitly provisional; only terminal_shadow_observation rows in final shadow-observations.json are scored as terminal decisions. Only a positively completed wrong-role classification removes a candidate from competition. Null normalized values retain raw literals as unresolved evidence.

All records remain `production_eligible=false`, original-source fidelity unverified, document completeness requiring independent source audit, and action readiness false. Text-supported shadow observations never become verified-source or complete-notice claims.

## Freeze and dry run

Use the bundled Python; no installation or .env is needed. Direct Python is used for code preparation/dry runs, without 1Password.

```sh
cd /Users/home/.codex/worktrees/e8f4/yokel
/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -B docs/research/state-rulemaking-benchmark/round4/runtime/offline_checks.py
/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -B docs/research/state-rulemaking-benchmark/round4/runtime/run_pipeline.py --pipeline docs/research/state-rulemaking-benchmark/round4/pipeline/pipeline.py --prepare-implementation docs/research/state-rulemaking-benchmark/round4/runtime/implementation-pins.READY.json
```

The supplied `implementation-pins.READY.json` captures the final implementation as tested. The earlier `implementation-pins.json` and `implementation-pins.final.json` are retained superseded development receipts and must not be executed. It reads only code/package metadata, never corpus sources. If the pipeline changes before the final joint freeze, primary must regenerate to a NEW file and verify policy consistency before collection. Do not silently overwrite a receipt. Pins include exact runtime/ledger/frozen-adapter/proposer hashes and package versions. Any drift blocks execution/resume.

After collection and independent labels freeze, primary dry-runs:

```sh
/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -B docs/research/state-rulemaking-benchmark/round4/runtime/run_pipeline.py --freeze docs/research/state-rulemaking-benchmark/round4/runtime/implementation-pins.READY.json --manifest PATH_TO_FROZEN_MANIFEST --source-root SOURCE_ROOT --output NEW_ROUND4_EXECUTION_DIRECTORY
```

Dry run validates mechanical source identity and proposes native cases without env credential reads, provider calls, or execution output creation. This child did not perform that fresh-corpus dry run.

## Authorized live execution and resume

Primary creates an exact five-key authorization JSON after source labels are frozen: `schema_version: round4.live-authorization.v1`, `implementation_sha256` (receipt file bytes), `manifest_sha256` (exact source manifest bytes), `source_labels_frozen_before_outputs: true`, `nominal_budget_usd: 1.0`. This is an attestation, not access to reference content. No evaluator path or label is accepted by runtime. A modified manifest, budget, authorization or implementation blocks resume.

Invoke `sh runtime/run_with_1password.sh` with the dry-run arguments plus `--authorization PATH --live --max-new N`. The wrapper uses only previously known references for `TYPESAFE_API_KEY` and `OPENROUTER_API_KEY`; it never saves resolved keys. Do not run it merely to test credentials or use resolved secrets in command text. Default `--max-new=1` supports a bounded operational pilot. After primary's authorized pilot, an explicit maximum up to 132 provider operations supports 120 Jev cases plus up to 12 OCR requests. Reuse exactly the same output directory and pins to resume completed cases; completed responses reparse locally and are not resubmitted.

`operations.py` uses a nonblocking run lock and immutable fsynced request/identity/intent/status/response/result artifacts per operation. Pending/uncertain POST, HTTP failure, invalid response or missing usage/cost latches the run before any further call. A received valid response can be parsed locally after interruption; the runner never blindly resubmits it. An interrupted response/status write is conservatively stopped for reconciliation. No automatic HTTP, SDK, model or provider retry/fallback is enabled.

Caps: 12 documents, 120 Jev POST cases, at most 60 retained PDF/OCR pages, 25 MB input PDF and OCR response limits, $1 nominal/accounted budget, 20,000 conservatively estimated Jev input tokens/request. Corpus page cap reserves feasibility before execution. Jev uses the frozen 45-second/2 MB transport; OCR has a separate verified-TLS/no-redirect transport with 180-second/25 MB bounds, an 8-token completion, pinned Gemma 3 27B wrapper, and Mistral parser plugin. OCR starts are paced at least 22 seconds from the prior durable OCR start, with progress logging before waits and per job.

Budget charge is **sum of per-operation max(reservation, observed accounted cost)**; pending and unknown costs retain their reservation. It is not max(sum reservations, sum observed), which can drop mixed unknown costs. Jev observed cost is reported input tokens × pinned rate. OCR accounting conservatively adds $0.002/page to reported wrapper cost (may double-count included fees); missing reported usage or cost stops. Nominal reservation is $0.025/OCR document plus $0.002/page. Maximum planned envelope at 12 documents/60 pages/120 maximal Jev cases is $0.5208. Provider invoices can differ; an unexpectedly expensive single received operation may exceed the nominal envelope, after which execution stops before the next operation. Prices and models are pinned in `ocr-catalog.json`; Mistral's OCR backend version is not exposed beyond its engine alias.

Safe exceptions to exact response retention are credential echo or an oversize/invalid body. Neither exception text nor Authorization headers are logged. All other raw response bytes and input/code hashes are retained. Existing rounds are untouched.

## Outputs and validation

Per document: native pipeline record/final cases, immutable fallback decision, fallback annotation-only text and provenance when acquired, fallback cases, and final `shadow-observations.json`. Per operation: original exact request/response and parsed judgments/usage. `completed.json` contains final document observations and conservative accounting totals. Operation-boundary pauses print progress and preserve completed cases without falsely publishing whole-run completion.

30 offline tests pass with synthetic notices, fake transports and a programmatically created neutral blank PDF. They cover exact model pins/full context, manifest leakage/path/hash rejection, code/version pinning, deterministic hard/soft rules, email exceptions, native-empty OCR recovery, unresolved cross-channel competitors, annotation-only extraction/unknown page mapping, mixed budget accounting, 12/120/60 caps, per-case resume/no rePOST, uncertain and invalid usage latches, OCR timeout/response bound/pacing and preserved unverified source status. No fresh corpus or reference labels entered these tests.

Live API contracts were checked through public documentation/catalog only: [OpenRouter PDF inputs/annotations](https://openrouter.ai/docs/guides/overview/multimodal/pdfs), [OCR pricing announcement](https://openrouter.ai/blog/announcements/universal-pdf-support/), [current model catalog](https://openrouter.ai/api/v1/models). TypeSafe HTTP/Choice contracts are the already checked round-three pinned adapter. Implementation verification is distinct from measured fresh-corpus accuracy, which remains the primary's next stage.

Native extraction provenance is owned by the collector/source freeze: primary must retain the actual extraction command and executable version with the hashed native artifacts. This runner consumes those exact bytes and does not itself run a native extractor or infer its version. The Python/pypdf pins describe mechanical PDF inspection only. Live authorization’s labels-frozen boolean is an attestation; primary must bind the real external Freeze B to it. No label files enter runtime. All 12 scheduled documents must remain in evaluation accounting, including not-started/partial/failed notices, derived from the frozen manifest and durable artifacts. Source isolation here is code/data separation, not an enforced OS filesystem boundary. `reported_cost_usd` is OpenRouter provider-reported charge; Jev cost is a usage/rate estimate; mixed observed_accounted_usd and budget_charge_usd are conservative accounting, never a total actual invoice.
