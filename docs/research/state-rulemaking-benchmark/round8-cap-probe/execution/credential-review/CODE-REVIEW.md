# Updated cap-probe service code review

2026-10-09. This supersedes the obsolete copied-adapter snapshot in
`PREBUILD-CHECKS.md`; its final generated-artifact gates remain applicable.

Current adapter SHA-256:
`ddb95a946ee46623012d4eea4cb38d0f0a85a5a3bd4b404e84f4834ab13b5cac`.
Current preparer SHA-256:
`3b7eabf65c9ffbc84110a2e4dd3c670296c73c310e352411c30e9a0bc848fe32`.

## Preparation manifest key mismatch: resolved

An earlier in-progress read of `execution/service-account/prepare_manifest.py` used
`json.loads(manifest.read_bytes())['units']`. The released cap-probe source manifest
has exactly `schema_version` and `documents`; `runtime/run_pipeline.py:load_sources`
also requires and iterates `documents`. A subsequent current-file read confirms
line 24 now uses `['documents']`; the source issue is resolved. The preparer hash
listed above belongs to this corrected file: the prior content read and later hash
were separate checks during implementation, so the earlier report incorrectly
associated that hash with the stale lookup. No generator was executed in this review.
The actual final-shape preparation test remains pending; a passing service mock
suite does not alone exercise the metadata generator.

## Updated boundaries confirmed

The adapter now requires cap-probe binding/dependency/auth schemas, three new
operations, one call per stage, inventory allowance 12288, the $2 shared guard and
immutable $0.100166 prior-debit hash. Check requires one document/two pages. Check
and live runtime invocations and receipts all use three operations, with separate
cap-probe output/intent paths and unchanged no-existing-run guard. Original R8 B is
directly bound and hash-verified as opaque entries under the original R8 root;
local A/S are separately confined to the probe root. No stale R8-copy scope rejection
applies to this updated adapter.

The preparer now includes original B/E freeze records and their file targets, plus
the reused text/PDF targets, implementation code and existing Python/package closure.
No new service-code import requires an additional package beyond the earlier reviewed
closure. Final review must still verify every external B/E target is canonical,
confined to original R8 and matches its freeze hash/size; source targets must be the
two exact reviewed files. The old freeze loop does not itself enforce confinement,
so final artifact validation remains necessary. This is not a request to modify
frozen original files or expand provider scope.

No other material service-boundary issue was found in this code inspection. Final
policy-v4/generated-manifest approval remains pending finalized artifacts and their
hash validation. No current code blocker remains from the manifest-key finding.
Runtime extraction/ledger semantics are owned by the independent runtime
reviewer and were not duplicated here.

Changed only this report. No runtime edits, sources/reference truth, provider output,
credentials, enrollment, native builds or op/provider calls were used. Source-manifest
top-level field names/schema were inspected; source documents were not read.
