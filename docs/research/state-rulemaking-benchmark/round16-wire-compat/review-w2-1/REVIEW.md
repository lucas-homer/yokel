# Round 3 review: r16.w2.1 (`protocol-w2-1/`) versus r16.w2 (`protocol-w2/`)

Reviewer: Claude Fable 5.1 (review sub-agent), 2026-10-13. Offline, read-only outside this
folder. No network, provider, or credential access. All Python run as `python3 -I -S -B`.

Scope: the full `diff -ru protocol-w2 protocol-w2-1` (wire.py, verify.py, run_independent.py,
test_wire.py, SPEC.md, READY/receipt/test-output/frozen-inputs; ERRATA.md unchanged), plus the
frozen `testing/test_independent.py` and the frozen r15.1 helpers the binding relies on.

## Verdict

**Freeze r16.w2.1 as the offline candidate: YES.** No BLOCKER, no SHOULD-FIX. Every round-2 item
is FIXED (N-W2-4 is addressed by documentation, which round 2 allowed). The `run_independent.py`
adapter is sound. Three NOTEs below, none of which need a change before freezing.

Independently reproduced: own suite 98/98, verify.py exit 0 (also with this new sibling folder
present), frozen suite 55 run / 54 pass / 1 intended failure / 0 errors / 0 skips, 170
plan-bound calls, guarded bytes 24,013 / 24,198 / 29,024 / 29,209.

## Round-2 items

| Item | Status | Evidence |
|---|---|---|
| SF-W2-1 whole-tree hash | **FIXED** | `verify.py:inputs()` now enumerates a declared scope and `check_frozen()` compares that same scope. `protocol-w2/verify.py` fails with "Frozen benchmark payloads changed" once `review-w2-1/` exists; `protocol-w2-1/verify.py` exits 0 with it present. Runtime audit (`repro_scope_audit.py`, `sys.addaudithook('open')` around a full verify run): 74 benchmark files opened outside the owned folder, 74 pinned, 0 unpinned, 0 pinned-but-unused. Pin constants (`R15_READY_SHA256`, `COMMON_SHA256`) and every by-path load (`READY.json`, `compact.py`, `stage-a.system.txt`, `request-settings.json`, `common.py`, fixtures, sizing JSON, `design/schema.draft.json`, w1 `protocol/wire.py`) are inside the scope. |
| SF-W2-2 binding ignored table / request hash | **FIXED** | `wire.py:261-275`. 60 attack cases in `repro_binding_attacks.py`; all rejected with the documented code (table below). Binding precedes parsing: with `r15.strict_load`, `to_compact`, `r15.validate`, `r15.expand` all patched to assert, every binding failure still raises its `plan_*` code, and only the genuine-plan control reaches the parser. |
| N-W2-1 "in ID order" | **FIXED** | Sole prompt delta (unified diff: one line per profile). Truthful for all 30 sources available offline (`repro_prompt_delta.py`): array-order concatenation reproduces the source byte-for-byte in every case; lexical-ID order fails for the 5 sources with >9 rows, which is exactly why the w2 wording was unsafe. The rows the model sees (re-parsed from the user message) equal `plan['table']['rows']` equal `r15.span_table(source)['rows']`. |
| N-W2-2 key order | **FIXED** | `repro_key_order.py`: w2.1 `from_compact`/`to_compact` top-level and unit key order equals w1 on reversed-key input (w2 differed); non-canonical `json.dumps` identical to w1; canonical bytes identical across w1/w2/w2.1. |
| N-W2-3 binding opt-in | **FIXED** | `plan` is keyword-only with no default. Omitted or positional (either slot) raises `TypeError`; `None`/list/str raise `plan_shape`. |
| N-W2-4 double lint | **Documented, left in place** | SPEC "w2.1 deltas" explains both lints (self-lint plus caller-lint against a substituted `schema`). Deterministic and harmless; acceptable. |

### Binding attack results (w2.1, `repro_binding_attacks.py`)

| Attack | Result |
|---|---|
| genuine plan (control), also with `table=plan['table']` | ACCEPT, expanded bytes equal r15.1 |
| same source, opaque plan with caller `full` / full plan with caller `opaque` | `plan_profile` |
| `request_sha256` flipped hex / uppercased / bytes / None / 0 / other source's hash | `plan_request_sha256` |
| table genuine, `version` = r16.w2 / r16.w2.1 / r15.1 | `plan_version` |
| table genuine, `envelope_version` = r16.e1 | `plan_envelope_version` |
| plan positional (6th arg, or in profile slot), plan omitted | `TypeError` (documented) |
| `plan=None`, `[]`, `"x"` | `plan_shape`; `{}` → `plan_profile` |
| forged 3-key; 3-key + table; 3-key + sha | `plan_shape` |
| other-source plan (caller table genuine or other); other-source plan with table swapped to genuine | `plan_table`; `plan_request_sha256` |
| stale table in caller only / plan only / both; rows reversed; table extra key | `plan_table` |
| plan table list / None / int-keyed / set / lone surrogate / circular / 70-deep | `plan_table` or an r15 ValueError code (`canonical_encoding`, `unpaired_surrogate`, `parser_depth`) |
| `non_stop` or bad profile with a forged plan | `non_stop` / profile ValueError first (finish and profile guards still precede binding) |
| oversize source with a forged plan | `full_request_overflow` (from the rebuild) |
| extra-keys plan (genuine + 2 unknown keys) | ACCEPT (see NOTE 2) |
| forged 5-key plan with table and sha recomputed from `build` | ACCEPT (see NOTE 2) |
| body mutated, sha untouched | ACCEPT (documented in SPEC: body is not a binding input) |
| plan table `{'rows': nan}` | `ValueError: Out of range float values are not JSON compliant: nan` (see NOTE 1) |

## Adapter ruling (`run_independent.py` patching `validate_response`)

**Sound.** The adapter only supplies `plan=build(source, profile)` for the test's own
`(source, profile)` and then calls the real, mandatory validator. Because the w2.1 validator body
after the binding block is byte-identical to w2's, the adapter can only add a constraint, never
remove one, so the set of accepted responses under w2.1+adapter is a subset of w2's.

Empirical check (`repro_adapter_codes.py`): the frozen suite was run three ways with every
`validate_response` call's outcome recorded per test. (a) w2 native, (b) w2.1 with the adapter,
(c) w2.1 native. (a) and (b) both give 55 run, the single intended failure, 0 errors. (c) gives
the same intended failure plus 22 tests erroring or failing on `TypeError` (missing `plan`),
which is what the adapter shims and what the own suite's `test_w21_plan_is_required` pins.

Across the 23 frozen tests that call `validate_response` (173 calls under (a)):

- **No call that was a rejection under (a) is an ACCEPT under (b), and no ACCEPT under (a) is a
  rejection under (b).** Injecting a freshly built plan never makes a should-reject case pass.
- **21 tests have identical per-call outcomes** (same exception type and code, same counts):
  `AliasingTests.test_validate_response_result_parts_do_not_alias`; all 11 `PipelineAcceptTests`;
  `PipelineRejectTests.test_capacity_sentinels_and_depth_keep_r15_1_codes`,
  `test_checker_rejections_are_wire_errors`, `test_host_only_invariants_keep_their_r15_1_codes`,
  `test_no_partial_expansion_on_final_node_error`, `test_non_stop_finish_reason_rejects_before_parsing`,
  `test_opaque_profile_rejects_typed_nodes_and_children`, `test_r15_1_compact_shape_is_not_accepted_on_the_wire`,
  `test_raw_guards_apply_to_the_wire_text`, `test_raw_size_boundary_is_inclusive`,
  `test_short_but_absent_span_ids_with_wider_tables`.
- **2 tests still pass but via a different code path:**
  1. `PipelineRejectTests.test_stale_table_and_wrong_source_reject` (both sub-cases): w2 raised
     r15 `ValueError('exact_host_table')` from `schema()`; w2.1 raises `WireError('plan_table')`
     from the binding block, earlier. The test asserts only `Exception`, so it passes either way.
     The property it documents ("a tampered table or a different source must not validate")
     still holds and is now enforced one stage earlier; the r15 `exact_host_table` path remains in
     the pipeline but is no longer reachable through `validate_response` once binding gates it.
     This is defence in depth, not masking: the own suite covers the same cases directly
     (`test_w21_mismatched_table`, `test_w21_plan_from_different_source`).
  2. `PipelineRejectTests.test_unknown_profile_rejected_on_validate_response` (3 sub-cases): the
     same `ValueError('profile must be full or opaque')` is now raised by `build()` inside the
     adapter before the validator is reached, rather than by the validator's own `_profile`.
     The validator's own check is pinned directly by `test_invalid_profiles` in the own suite.

Call-count reconciliation: 173 calls in (a); the runner reports 170 plan-bound calls because it
counts after a successful `build`, and the 3 unknown-profile calls fail inside `build`.

One semantic consequence of the adapter (not a defect, worth knowing): under the adapter,
`build()` runs before the `non_stop` guard, so an over-guard source would surface
`full_request_overflow` ahead of `non_stop`. No frozen test exercises that, and the real
validator's ordering (finish, profile, plan metadata, rebuild, table, hash, parse) is unchanged.

## Prompt delta and size

- Per profile, w2.1 prompt equals w2 prompt with the one sentence replaced; old sentence count
  1 → 0, new sentence count 1; unified diff is exactly one changed line. No other "order"
  wording in the prompt conflicts with it.
- Encoded delta +22 bytes versus w2 ("ID" → "the supplied table array"), +82 versus w1, in both
  profiles. Measured body and guarded bytes move by exactly +22 on all four sizing rows
  (22,967→22,989; 23,152→23,174; 27,978→28,000; 28,163→28,185). SPEC table, receipt.json and
  READY.json agree. READY.json differs from w2 only in revision, these sizes, the request hashes,
  and 90→98 tests.

## New findings

No BLOCKER. No SHOULD-FIX.

**NOTE 1 (pre-existing, not introduced by w2.1): a NaN inside a table surfaces a raw json
ValueError.** `r15.canonical` catches `TypeError/OverflowError/UnicodeError/RecursionError` but
`json.dumps(allow_nan=False)` raises a plain `ValueError` whose message is not a code. Repro:
`validate_response(RAW, 'stop', SOURCE, {'rows': float('nan')}, plan=build(SOURCE))` →
`ValueError: Out of range float values are not JSON compliant: nan`. Identical under w2 (via
`schema()` → `validate_table`) and when calling frozen `r15.validate_table` directly, so this is
frozen r15.1 behaviour now additionally reachable through `plan['table']`. It is still a
rejection and still a `ValueError`; the plan is trusted caller data. Optional hardening in a later
revision: wrap the two `canonical` calls in the binding block and re-raise as `plan_table`.

**NOTE 2 (design property, documented): binding proves equivalence to `build(source, profile)`,
not identity with a particular dispatch.** A 5-key plan whose `table` and `request_sha256` are
recomputed from `build` is accepted, extra keys are ignored, and a mutated `body` with an untouched
hash is accepted. All three follow from the stateless offline design and the SPEC's explicit
"body is not a binding input / adapter must recompute its guard" caveat. No change needed for the
offline freeze; a dispatch adapter must carry its own transport-side binding.

**NOTE 3: the lineage parent `protocol-w2/` is not in the frozen scope.** w2.1 pins
`review-w2/` but not `protocol-w2/`, from which it was copied. Nothing loads `protocol-w2/` at
runtime (audit confirms), so this is provenance only. A later revision may want to add it, and
should add `review-w2-1/` for the same reason.

## Files written (all under `review-w2-1/`)

- `REVIEW.md` (this file)
- `repro_binding_attacks.py` — 60 binding attacks plus ordering proof
- `repro_adapter_codes.py` — frozen suite run three ways with per-test outcome recording
- `repro_prompt_delta.py` — prompt diff, byte deltas, concatenation-claim check on 30 sources
- `repro_scope_audit.py` — audit-hook record of every file opened during verify.py vs. manifest
- `repro_key_order.py` — N-W2-2 key-order comparison across w1/w2/w2.1

Nothing outside `review-w2-1/` was modified. Nothing committed.
