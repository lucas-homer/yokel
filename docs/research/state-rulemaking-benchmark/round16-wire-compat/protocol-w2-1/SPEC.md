# r16.w2.1 offline revision

Copied from frozen `protocol-w2/` (r16.w2) and changed exclusively in
`protocol-w2-1/`. No commit, network/provider call, credential access, dependency
installation, dispatch, or write outside this folder. `frozen-inputs.json`
pins 74 files in the actual dependency scope: all files under r15.1
`protocol-revised/`, round16 `design/`, `inventory/`, `envelope-check/`,
`testing/`, `review/`, `review-w2/`, and `protocol/` (w1); the loaded R14
`runtime/common.py`; and the R14 prior source plus both r15 sizing corpus
JSON files used by the suites. Changes, removals, or additions inside scoped
directories fail verification. New siblings outside the scope are ignored.
The entire benchmark outside this folder is nevertheless frozen for this task.
Frozen r15.1 and R14 code and manifest pins are unchanged.

## w2.1 deltas from round-2 review

- **SF-W2-1:** `check_frozen()` compares the same dependency scope as `inputs()`;
  the manifest is re-recorded, rather than hashing every benchmark sibling.
  A temporary fixture under this owned folder tests unrelated sibling additions,
  and scoped changes/removals/additions, without modifying any frozen inputs.
- **SF-W2-2 + N-W2-3:** the keyword-only `plan` argument is mandatory. Missing
  it raises Python `TypeError`; explicit `None` raises `plan_shape`. Metadata,
  the supplied table, and originating request hash are bound before response
  parsing. Forged three-key plans and plans for different sources are rejected.
- **N-W2-1:** prompt concatenation means supplied table-array order, not lexical
  ID order. The 108-row prior-source test proves byte-exact array concatenation
  and proves lexical ID sorting does not reconstruct that source.
- **N-W2-2:** preserve input top-level and unit key insertion order in both codec
  directions, matching w1 without changing canonical bytes or alias handling.
  Non-canonical serialization is compared with w1 across all 37 corpus cases.
- **N-W2-4:** double schema lint remains deliberately: `schema()` lints its own
  result and request/response callers also lint, covering a substituted schema
  function. It is harmless and deterministic.

## Versions and unchanged response

`REVISION = "r16.w2.1"` names this implementation revision.
`VERSION = "r16.w1"` remains the RESPONSE wire version, including model-emitted
`v`, the prompt's response-version instruction, and the response-schema enum.
`ENVELOPE_VERSION = "r16.e2"` names the separate REQUEST-envelope contract and
is recorded in plans, measurements, receipt.json, and READY.json. It is plan
metadata, not an extra user-envelope key. The predecessor request envelope
had no separate version identifier.

Reason: removing redundant request content changes request consumers' contract,
while no response field, shape, value, bounds, fragment mapping, hash echo,
deadline representation, or expanded-record semantics changes. Renaming the
response version would needlessly invalidate existing response schemas and
fixtures. Source/table SHA-256 inputs and schema-bound response `h`/`t` echoes
remain exactly as before. The full schema still equals the pinned draft;
full/opaque canonical schema sizes are 5,085/5,056 bytes.

Decode retains frozen r15.1 strict parsing, unchanged R14 instance checks on
the wire, and unchanged r15.1 validate/expand/contract, with canonical compact
and wire inverse checks. The expanded record is returned directly and remains
byte-identical to frozen r15.1. All 37 carried-over corpus cases remain covered:
32 valid round trips and five negatives retaining their codes. The nine
semantic-negative controls remain mechanically accepted, as before; that does
not establish semantic correctness. Key/array ordering, exact Unicode,
uncertainty, no repair/coercion/defaulting, and whole-response rejection remain.

## APIs and review dispositions

Exports: `WireError`, `from_compact`, `to_compact`, `lint_schema`, `schema`,
`validate_response`, `measure`, and `build`.

- **SF-1 fixed.** Conversion constructs new dicts/lists at each occurrence;
  it never mutates a memoized deepcopy. A valid compact with two units sharing
  one deadline dict validates and round-trips. Decode also accepts two units
  sharing a singleton deadline list. Tests check shared fragment lists and
  dimensions in both directions, input immutability, and independent outputs.
- **SF-2 fixed.** `build(source, profile="full")` raises
  `WireError("full_request_overflow")` if `len(common.encode(body)) + 1024 >
  40000`, without returning a plan or body. Exactly 40,000 is accepted and
  40,001 rejected. There is no overflow opt-in. `measure(source, profile)`
  assembles the same request privately and returns ONLY sizes, request digest,
  profile/version identifiers, span count, guard limit/headroom/verdict;
  never body, messages, table, or source text. Both entry points use identical
  reconstruction/schema checks; tests pin both admissible and oversize cases.
  **Any future dispatch adapter must recompute the guard on the actual body
  immediately before transport**, even after a successful build, because a
  caller can mutate a plan. Offline measurement is not dispatch authorization.
- **SF-3, SF-W2-2, N-W2-3 fixed.** Plans and measurements record `profile`,
  response `version`, and request `envelope_version`.
  `validate_response(raw, finish, source, table, profile="full", *, plan)`
  has no default plan or opt-out path. After the finish-reason and profile
  guards, a non-dict plan rejects with `plan_shape`; metadata mismatches or
  absence reject with `plan_profile`, `plan_version`, `plan_envelope_version`.
  Absent `table` or `request_sha256` rejects with `plan_shape`. The validator
  rebuilds `build(source, profile)`, compares canonical bytes of both passed
  `table` and `plan["table"]` with the rebuilt table (`plan_table`), then checks
  `plan["request_sha256"]` against the rebuilt request (`plan_request_sha256`).
  Rebuilding also applies the request guard. All binding checks precede parsing
  the response. Example: `validate_response(raw, finish, source, plan["table"],
  plan["profile"], plan=plan)`. Omitting `profile` still selects full; an opaque
  plan cannot silently switch that default. `plan["body"]` is not trusted as a
  binding input; a dispatch adapter must still recompute its actual-body guard.
  Own fixture callers explicitly pass cached genuine build plans; caches are
  confined to tests. Tests directly exercise the mandatory public API without
  an adapter for missing/None/forged plans, wrong source/table, stale request
  hash, matching profiles and metadata-before-parse precedence.
- **N-1 fixed.** `WireError` subclasses `ValueError` and keeps `.code`, optional
  `.details`, and the code as its string. Frozen r15.1 ValueErrors propagate
  unchanged, without rewrapping.
- **N-2 retained/documented.** Pure checker count violations keep `array_bound`;
  mixed checker failures use `wire_schema`. Schema-before-host precedence can
  differ from r15.1 for mixed failures. No claim of identical error precedence
  on arbitrary malformed input. Caller profile/plan checks now precede parsing
  (after finish reason); valid response processing order is unchanged.
- **N-3 fixed.** Strict T4 lint is runtime `lint_schema`, invoked by `schema`,
  request assembly for both `build`/`measure`, and `validate_response`.
  It checks exact per-type keyword sets, scalar types, closed objects, all
  required properties, bounds/value types, unique nonempty string enums,
  finite numeric bounds, and root-zero depth <=8, then calls unchanged R14
  `check_schema`. Invalid schemas reject with `schema_lint`. Mutation tests
  prove malformed schemas cannot be returned/emitted through the public
  schema/build paths, including a substituted schema function.
- **N-4 fixed.** Every T3 negative now asserts an explicit code. Structural and
  instance failures remain separated from unchanged host-only codes.
- **N-5 fixed.** Direct conversion catches RecursionError and raises controlled
  `WireError("wire_resource")`, never partial output. Both directions are
  tested with 3,000-deep input at the interpreter's default limit (1,000 here)
  and a lowered limit of 180, restored in finally. Raw-response depth/size
  guards continue to be the frozen r15.1 ones.
- **N-6 clarified.** `ERRATA.md` explains why DESIGN §4's pseudocode does not
  admit `[null]`, citing §3 W3 and §5 #25. Frozen DESIGN is untouched.

## Rows-only request and exact prompt diff

The user envelope has exactly three keys:
`{source_text_sha256, span_table, span_table_sha256}`. `source_text` is removed.
Before assembling any body, build/measure call frozen `r15.reconstruct`, which
validates the host table and compares the joined row texts to source UTF-8
bytes. The builder independently checks the returned reconstruction's bytes.
A test substitutes a defective table generator whose regenerated table also
agrees, forcing the explicit byte comparison to catch `source_reconstruction`;
another forces an incorrect reconstruction result. Mixed CR/LF, Unicode line
separators, combining characters, and astral codepoints reconstruct exactly.

Exact r16.w1 sentence before:

```text
The complete source and span table are supplied.
```

Exact r16.w2 sentence before the w2.1 edit:

```text
The complete source is supplied as span-table rows whose exact concatenation in ID order is the full source.
```

Exact r16.w2.1 sentence after:

```text
The complete source is supplied as span-table rows whose exact concatenation in the supplied table array order is the full source.
```

The supplied table array order is the concatenation order. This adds no
extraction instruction. The uniqueness-checked replacement remains the sole
prompt sentence change relative to w1 in both profiles, pinned by exact string
comparison against the frozen w1 prompt builder. Serialized request cost is
+82 bytes versus w1, or +22 bytes versus w2.
All five original DESIGN edits, the additional `y=[]` clarification, and the
opaque-profile instruction are unchanged.

## Exact sizing

Guarded bytes are the unchanged R14 encoding length plus 1,024; limit 40,000.
Both sources are admissible under both schema profiles, including all 24
clauses without narrowing or chunking.

| Source | Profile | Body bytes | Guarded bytes | Headroom | Schema bytes |
|---|---|---:|---:|---:|---:|
| Prior R14 parsed body (108 rows, 7,208 source bytes) | full | 22,989 | 24,013 | 15,987 | 5,085 |
| Prior R14 parsed body | opaque | 23,174 | 24,198 | 15,802 | 5,056 |
| disjoint600-u24 (24 rows, 14,423 source bytes) | full | 28,000 | 29,024 | 10,976 | 5,085 |
| disjoint600-u24 | opaque | 28,185 | 29,209 | 10,791 | 5,056 |

The envelope-check rows-only full measurements were 23,931 / 28,942; add the
82-byte prompt replacement to obtain 24,013 / 29,024. Relative to full w1's
31,374 / 43,432, net reductions are 7,361 / 14,408 bytes. Opaque costs 185 bytes
more than full (its profile instruction outweighs its 29-byte schema saving).
Every sizing block in receipt.json includes profile and both contract versions,
with exact request SHA-256; measurements use the no-body `measure` API.

## Tests carried over and intentional adaptations

All **75** w1 test methods are carried over; **23** new methods (15 in w2, eight in w2.1) bring the own
suite to **98 passing tests**. The original assertions are changed only for
required request behavior and review-requested strengthening:

1. `test_build_exact_R14_bytes_and_preserved_envelope`: three envelope keys;
   exact reconstruction replaces the removed duplicate text assertion;
   retained source/table hashes asserted directly.
2. `test_build_size_profiles_fit_and_overflow`: revised exact sizes and both
   sources now fitting. Its `size_receipt` helper uses `measure` and records
   full plus opaque metadata. True overflow has dedicated new tests.
3. The 21 `test_T3_*` methods now pin codes (N-4):
   `fragment_tuple`, `fragment_missing_key`, `fragment_extra_key`,
   `occurrence_zero`, `occurrence_boolean`, `occurrence_float`, `empty_anchor`,
   `whitespace_anchor`, `deadline_null`, `deadline_two_items`,
   `deadline_one_null`, `old_version`, `span_overlong`, `span_absent_short`,
   `node_overlong`, `node_bad_prefix`, `node_leading_zero`, `node_out_of_range`,
   `missing_envelope_key`, `extra_envelope_key`, `extra_dimension_key`.
   `deadline_two_items` still yields `wire_schema` because its two empty
   objects also violate required keys. Host-only codes are `text_bound`,
   `fragment_span`, `node_id` (prefix/leading zero), and `node_id_range`.
   Other T3 cases retain `wire_schema`.
4. Both existing T4 tests call the moved runtime lint through an alias;
   their bounds, schema equality, and statistics assertions are unchanged.
   All response-validation fixture calls now explicitly supply genuine plans;
   their response assertions are unchanged.

The unedited frozen `testing/test_independent.py` runs through
`run_independent.py`. The runner executes the exact original source bytes,
redirecting its `protocol/wire.py` import to `protocol-w2-1/wire.py`; it
asserts the selected module path and frozen suite digest. It does not rewrite
assertions, mark expectedFailure, skip tests, or modify the frozen file.
Because frozen callers predate the mandatory keyword-only plan, the runner
adds an explicit API adapter around the loaded validator during the suite: it
builds the originating plan for each source/profile and passes `plan=` to the
real validator. It never disables binding. The report records this adaptation
and the 170 plan-bound calls. Missing-plan rejection is tested directly in the
own suite, so this adapter cannot hide an opt-out in the public API.
Result: **55 run, 54 pass, one intended failure, zero errors/skips**.

The complete intended-failure list is one entry:
`frozen_independent.BuildTests.test_user_envelope_is_pinned_and_source_exact`.
It asserts the old four-key request envelope and fails because `source_text`
is absent. The own suite checks exact row reconstruction and retained hashes.
The independent oversize test already accepts `full_request_overflow`, so it
passes; there is no intended overflow-suite failure. The runner exits zero
only for exactly the listed failure with all 55 tests run and no errors/skips;
it records `raw_suite_success:false` honestly. Any other outcome fails verify.

## Reproduce and artifacts

```sh
python3 -I -S -B docs/research/state-rulemaking-benchmark/round16-wire-compat/protocol-w2-1/verify.py
python3 -I -S -B docs/research/state-rulemaking-benchmark/round16-wire-compat/protocol-w2-1/run_independent.py
```

`verify.py --record` runs both suites, checks frozen inputs before/after, then
writes only this folder's combined `test-output.txt`, `receipt.json`, and
`READY.json`. Read-only verify reruns both suites, verifies the exact owned file
set and all READY pins, and compares the receipt. READY pins every payload
file, including this spec, ERRATA, frozen-input snapshot, tests, and runner;
its own hash is excluded to avoid self-reference. No Python bytecode is written.

## Deviations and open issues

The response version intentionally remains r16.w1; r16.w2.1 is the implementation
revision and r16.e2 the separately recorded request version. Mandatory plan-bound
validation intentionally breaks legacy callers; the frozen-suite runner adapts
that call interface explicitly. No unresolved round-2 fix or unexpected test
failure remains.

Offline readiness is not dispatch approval. No transport adapter was requested
or implemented. A future adapter must pass its originating plan to response
validation, recheck the actual request guard immediately before transport, and
pin the raw response, wire/envelope versions, codec, and schema in receipts.
Provider compatibility, model behavior, output-token headroom, and semantic
completeness remain unverified offline. Those inherited research questions are
outside this implementation; the prior 24-clause request-size obstacle is resolved.
