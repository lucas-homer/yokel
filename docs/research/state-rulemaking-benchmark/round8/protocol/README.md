# R8 protocol handoff

Protocol and synthetic tests are ready for primary freeze review. **No collection, labeling or paid release is implied.** See PROTOCOL.md and CONTRACT.json. Only round8/protocol/ and reviewer artifacts are owned here; prior rounds and fresh source material are untouched.

Runtime imports `observed.py` by explicit path and calls `validate_observed(observed)` for the complete `round8.observed.v1` envelope. `observed_schema()` returns its closed schema. `evaluate.py` exposes the same functions plus `evaluate(schedule, truth, audit, observed)` and a file CLI. Use R8 top-level schedule/truth/matching-audit/observed versions; preserve R7 inventory/record/verdict/payload versions and exact artifact hashes.

Required per-document extension to R7: `failure` is null for normal/local review/not-started states, otherwise `{stage,kind,intent_recorded,operation_id,http_status,evidence_sha256}`. Stages: inventory/jev/stronger. Kinds: http_error/transport_uncertain/invalid_response/budget_stop/operator_pause/local_error. Receipt hash is mandatory for a failure/pause; `operation_id` is nonnull for attempted calls. Only `http_error` has a nonnull non-200 HTTP status and provider_service_error=true. Transport uncertainty stays false for that flag and remains a conservatively called/charged attempt. Runtime review verifies ledger binding, not merely hash shape.

Gates: source_review, request_size_review, assembly_review, inventory_failed, paired_verification_completed, verification_failed, **operation_pause**, **not_started**, **postresponse_budget_stop**. Not-started and local review states have uncalled arms, never fabricated judgments. `inventory_failed` permits confirmed HTTP error with true service flag; verifier failure preserves earlier completed Jev. A safe operation_pause has intent_recorded=false with local receipt and stage naming the next call: inventory has no artifacts; Jev has assembled record/payload and no verifier call; stronger preserves completed Jev and uncalled stronger. All review reasons and judgment consistency checks remain strict.

Scoring reuses a hash-pinned isolated R7 evaluator instance. Only its observation validator is explicitly replaced, and input/report top-level version tags are projected. Original states, service flags, judgments, costs and hashes are not rewritten. The report carries original/projected canonical hashes and the scorer hash, plus operational failure counts. Read-only dependencies fail import if pins change. The original supplied input objects are preserved.

Truth and matching-audit fields retain the definitions in ../../round6/protocol/EVALUATION-CONTRACT.md under R8 versions and the tighter R7 semantic requirements; independent AI all-page image references must be frozen before model outputs. Empty synthetic test references demonstrate mechanics only, never real notice truth. Every real source unit and every available-artifact claim must be independently reviewed after execution.

Run from this directory:

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m unittest -v test_evaluate
```

Eight synthetic tests pass: actual HTTP versus uncertain transport, partial failures, safe pauses, inconsistent service/serial states, judgment/hash consistency, cohort shortfall/missing rows/version projection, numeric versus unknown costs. Runtime independent review and paid release are separate pending gates.

Postresponse budget overrun uses `postresponse_budget_stop` with failure.kind=budget_stop, intent_recorded=true and stage identifying the successfully completed operation. Inventory hash must remain; an inventory-stage stop has both arms uncalled, a Jev-stage stop preserves its accepted/review judgment and leaves stronger uncalled, and a stronger-stage stop preserves both completed judgments. The receipt must bind the valid retained result and observed-budget latch. This is a global spend stop, not a provider/response failure; no next call is allowed. The runtime may deterministically assemble the retained inventory without making another model call.
