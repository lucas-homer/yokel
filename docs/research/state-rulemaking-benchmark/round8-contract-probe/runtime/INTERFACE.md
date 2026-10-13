# Contract-probe preparation interface

Primary owns scope, authorization, freezes A/S, native v5 policy/build and live execution. This namespace only implements the reviewed candidate. Preparation CLI (bundled Python, offline): `runtime/run_pipeline.py --prepare-implementation runtime/implementation.json`. Live runtime path arguments remain --manifest, --source-root, --freeze, --output, --authorization, --source-labels-freeze-sha256, --live and --max-new 3. Fixed adapter modes are --check and --live-initial, under isolated -I -S -B Python. prepare_manifest.py only generates offline metadata after freezes and authorization; it does not build or run native jobs.

Exact authorization object:

```json
{
  "schema_version": "round8-contract-probe.live-authorization.v1",
  "implementation_sha256": "PRIMARY_FINAL_IMPLEMENTATION_HASH",
  "manifest_sha256": "PRIMARY_SOURCE_MANIFEST_HASH",
  "source_labels_frozen_before_outputs": true,
  "source_labels_freeze_sha256": "60b1e0f8c6321cee6407cfa04ad02af92a7546b059dd5235868746115cc5b792",
  "nominal_budget_usd": 2.0,
  "prior_budget_debit_usd": 0.261774,
  "prior_debit_sha256": "PRIMARY_HASH_OF_RUNTIME_PRIOR_DEBIT_JSON",
  "max_new_operations": 3,
  "calls_per_stage": 1,
  "inventory_completion": 12288,
  "stronger_completion": 4096,
  "inventory_input_guard": 35000,
  "stronger_input_guard": 40000,
  "jev_total_input_guard": 64000,
  "jev_state_longest_guard": 32000,
  "prompt_delta_sha256": "90a6f51531f5e26c9e1530a9b7b6c9feebde3b0742e238303839b8c975bf70b6"
}
```

The original R8 B reference remains opaque and verified at its original root; no truth is duplicated or passed to providers. The exact WI source native text/PDF remains read-only at original R8 paths. Both earlier intents/responses/status files and both Freeze E artifacts are pinned, including the cap-probe parsed result. Debit verification recomputes max(reservation, reported cost) for each, retaining .100166 + .161608 = .261774, with no refund/reset. Maximum new nominal reserve .316528 gives aggregate .578302 under shared $2. Source/shape/evidence/schema/models/reasoning/acceptance remain unchanged. Both exact verifier bodies must admit before either is dispatched. Failure/uncertainty permanently latch; parsed postresponse budget overrun preserves the result then stops.
