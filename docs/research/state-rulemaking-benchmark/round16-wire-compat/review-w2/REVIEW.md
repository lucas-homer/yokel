# Review round 2: r16.w2 (protocol-w2/wire.py and companions)

Reviewer: Claude Fable 5.1, independent review. Date: 2026-10-13.
Scope: `protocol-w2/` (wire.py, test_wire.py, verify.py, run_independent.py, SPEC.md, ERRATA.md,
receipt.json, READY.json) against the round-1 findings in `review/REVIEW.md`, frozen `design/DESIGN.md`,
`inventory/INVENTORY.md`, `envelope-check/FINDINGS.md`, and the frozen `testing/test_independent.py`.
Only `review-w2/` was written. No network or provider call, no credential access, no commit.
All Python run as `python3 -I -S -B`. Probe script: `review-w2/repro_probes_w2.py` (sections 1-7).

## Verdict

**No BLOCKER. r16.w2 is ready to be frozen as the offline candidate**, with one process defect the
primary should fix before (or as part of) freezing: `verify.py` now exits non-zero simply because
this review folder exists (SF-W2-1). Two small SHOULD-FIX items and four NOTEs follow. Every round-1
finding is FIXED; the fresh-container rewrite of the codec introduced no field drop, reorder or
code change across the full 37-case corpus.

Re-run evidence (my own runs, Python 3.13.7):

| Check | Result |
|---|---|
| `protocol-w2/verify.py` (read-only, before `review-w2/` existed) | exit 0; 90/90; receipt and READY pins match |
| `protocol-w2/run_independent.py` | exit 0; 55 run, 54 pass, exactly the one listed failure, 0 errors/skips |
| `protocol-w2/verify.py` after writing `review-w2/` | **exit 1: "Frozen benchmark payloads changed"** (SF-W2-1) |
| Guarded bytes via `measure()` (full/opaque) | prior 23,991 / 24,176; disjoint600-u24 29,002 / 29,187, all under guard; equal to receipt.json |

## 1. Round-1 findings: status

| Finding | Status | Evidence |
|---|---|---|
| SF-1 deepcopy-then-mutate false rejections | **FIXED** | `wire.py:77-126` builds new containers per occurrence (`_fresh`, no memo). Probe §1: shared deadline dict across two units, shared `x` list, shared fragment object, shared `y` list and shared deadline dict inside two `y` lists are all accepted in both directions; input canonical bytes unchanged after conversion. Pinned by `test_review_shared_*` (3 tests). |
| SF-2 build() returned a dispatchable over-guard body | **FIXED** | `wire.py:347-351` raises `WireError('full_request_overflow')` (a ValueError) and returns nothing; `measure()` (`:342-344`) returns the sizing dict only (12 keys, no body/messages/table/source text; probe §5). Boundary is exact: 40,000 accepted, 40,001 rejected. The disjoint600-u24 profile now fits (29,002), so the old overflow example no longer overflows. |
| SF-3 plan lacked profile/version | **FIXED** (with a weakness, see SF-W2-2) | Plan carries `profile`, `version='r16.w1'`, `envelope_version='r16.e2'` (`:332`); `validate_response(..., plan=)` checks all three before parsing (`:265-269`); probe §4 shows plan_profile raised with `strict_load` never called. |
| N-1 WireError not a ValueError | **FIXED** | `wire.py:20`; `issubclass(WireError, ValueError)` True. |
| N-3 strict lint only in tests | **FIXED** | `lint_schema` at `:150-204`, called from `schema()`, `validate_response` and `_request`; mutation tests cover it. |
| N-4 T3 negatives without codes | **FIXED** | `NEGATIVE_CODES` in `test_wire.py:540+`; every T3 case pins a code. |
| N-5 RecursionError on deep direct input | **FIXED** | `:129-142` catch and raise `wire_resource`; probe §1 confirms at the default limit. |
| N-6 DESIGN §4 `[null]` erratum | **FIXED** | `protocol-w2/ERRATA.md`; `[null]` still rejected (`wire_deadline_keys` direct, `wire_schema` via validate_response). Frozen `design/` untouched (pins pass). |

**Regression check on the codec rewrite** (probe §2): across all 37 corpus cases, `from_compact`,
`to_compact`, the expanded record from `validate_response`, and r15.1's own `validate_response`
expansion are canonical-byte-identical between w1 and w2 and to r15.1; every invalid case yields the
same code in w1 and w2; `schema()` output is byte-identical for both profiles. The only observable
difference is non-canonical key order (N-W2-2 below).

## 2. `source_text` removal

- **Nothing the model needs depends on the removed field.** The request differs from w1 in exactly
  two places (probe §3): the user envelope loses the `source_text` key, and one prompt sentence is
  replaced. `source_text_sha256`, `span_table`, `span_table_sha256`, the response schema (including
  the `h`/`t` single-value enums), and all other body fields are byte-identical to w1 in both profiles.
  Fragments address span IDs plus exact anchors, never global offsets, so the row texts carry all the
  information the model uses. The prompt's hash-echo instruction stays meaningful because `h`/`t`
  remain schema-bound. I agree with envelope-check §3.
- **The reconstruct guard is exact and runs first.** `_request` (`wire.py:318-320`) calls frozen
  `r15.reconstruct` (which itself regenerates and compares the table, then compares UTF-8 bytes) and
  re-compares the returned text's UTF-8 bytes to the source. Spy ordering (probe §3): `reconstruct`
  runs before the settings load and before the system prompt is built, i.e. before any body exists.
  Probed sources all reconstruct byte-exactly with contiguous codepoint offsets and correct hashes:
  CRLF, lone CR, CR followed by LF across rows, U+2028, U+2029, NEL, VT/FF/FS/GS/RS, no final
  newline, trailing blank lines, BOM, NUL, combining marks, astral characters, and a mixed-separator
  string producing 12 rows. Empty and whitespace-only sources are refused by frozen `span_table`
  (`nonempty_source`); a lone surrogate is refused (`unpaired_surrogate`). Both refusals happen inside
  `span_table`, before any body. A table tampered after reconstruction is still caught by
  `schema()`'s `validate_table` (`exact_host_table`). The table object serialized into the user
  message is the same object that was reconstructed.
- **The reworded prompt is truthful.** Old: "The complete source and span table are supplied."
  New: "The complete source is supplied as span-table rows whose exact concatenation in ID order is
  the full source." The next sentence still says each row is `[ID,start,end,exact_text]`. The
  replacement is the only change versus the w1 prompt in both profiles (`after == before.replace(old,
  new)`, old occurs exactly once; +60 serialized bytes). One wording nit: "ID order" (N-W2-1).
- **Hashes and echoes unchanged.** Confirmed byte-identical to w1 (probe §3).

## 3. Plan/profile/version binding (SF-3)

`validate_response` can be called in a way that skips the binding check: omit `plan` or pass
`plan=None` (probe §4: a typed response is ACCEPTED under the default full profile even though the
request was built opaque). This is documented in SPEC as the retained profile-only form for frozen
suites and fixtures. The check is therefore opt-in; the protection in the SF-3 scenario exists only
if the adapter passes the plan. When the plan is passed, the order is non_stop, profile string, plan
shape/profile/version/envelope_version, then parse, as claimed.

What the binding does not cover (SF-W2-2): the plan's `table`, `request_sha256` and `body` are
ignored. A plan built for a different source, or a forged three-key dict
`{profile, version, envelope_version}`, passes the binding (probe §4). This does not accept a wrong
record (the schema is still built from the `source`/`table` actually passed), so it is not a guard
bypass, but "plan-bound validation" currently binds metadata only, not the request.

## 4. `measure()` and `build()`

- `measure()` returns exactly the 12 sizing keys; no string value contains source text or prompt
  text (probe §5).
- `build()` refuses before returning anything. Precisely: `_request` necessarily assembles and
  encodes a body in memory to measure it (an `encode` spy sees a dict with `messages` before the
  refusal), then `build` raises on `sizing['under_guard']` computed from that same encoding. No body
  escapes via return value or exception (`WireError` carries only the code). The private `_request`
  is reachable by name, as any Python private is; SPEC's requirement that the adapter recompute the
  guard on the actual body before transport remains the real last line of defence.

## 5. The one intended independent-suite failure

The failing test (`test_user_envelope_is_pinned_and_source_exact`) is the **only failure**, but it is
**not the only behavior change** that passed through the frozen suite. The frozen suite is lenient on
all of the following (probe §6), and each is intended and documented in SPEC except the last:

| w1 to w2 change | Why the frozen suite did not notice | Documented in SPEC? |
|---|---|---|
| Prompt sentence replaced | Suite checks only `'r16.w1' in prompt` and `'r15.1 envelope' not in prompt` | yes (exact before/after) |
| `build()` raises on oversize instead of reporting | `test_build_guard_reports_or_rejects_oversize` accepts either branch by design | yes |
| Plan gained 8 keys (`version`, `envelope_version`, `profile`, `source_bytes`, `spans`, `schema_bytes`, `guard_limit`, `residual_guard_bytes`) | No plan key-set assertion | yes |
| `WireError` now subclasses `ValueError` | Suite asserts only `issubclass(WireError, Exception)` | yes |
| `validate_response` gained keyword-only `plan` | Suite never passes it | yes |
| New exports `measure`, `lint_schema`, `REVISION`, `ENVELOPE_VERSION` | Suite checks presence of the six original names only | yes |
| `from_compact` top-level key order changed | Suite compares canonical bytes only | **no** (N-W2-2) |

So the ruling is: the frozen suite correctly isolates the envelope change as the single assertion it
can see, and nothing undocumented slipped past except a canonical-invariant key-order change.

## New findings

### SHOULD-FIX

**SF-W2-1. `verify.py` fails as soon as this review folder exists** (`protocol-w2/verify.py:34-42`,
`check_frozen`). It hashes every file under the whole benchmark tree except `protocol-w2/` and
compares to `frozen-inputs.json` (7,491 entries, including `review/`). Any new sibling file, such as
`review-w2/REVIEW.md`, makes it exit 1 with "Frozen benchmark payloads changed". Repro: run
`python3 -I -S -B protocol-w2/verify.py` now (exit 1); it exited 0 before `review-w2/` was written.
`run_independent.py` is unaffected. The "verify.py is clean" claim in the brief is therefore true
only for a tree with no round-2 review in it. Fix options: scope `check_frozen` to the actual
dependency set already computed by `inputs()`, or exclude `review*/` directories, then `--record`
again so READY and the receipt pin the new manifest. The pinned module and both suites are
unaffected; this is a verification-harness defect, not a codec defect.

**SF-W2-2 (small). Plan binding compares metadata only.** `wire.py:265-269` checks `profile`,
`version`, `envelope_version` and ignores `plan['table']` and `plan['request_sha256']`. Repro (probe
§4): `validate_response(raw, 'stop', SOURCE, TABLE, plan=build(other_source))` is accepted, as is a
forged `{profile, version, envelope_version}` dict. Suggested: when `plan` is supplied, also require
`r15.canonical(plan['table']) == r15.canonical(table)` (code `plan_table`), and treat a missing
`table` as `plan_shape`. Cheap, and it makes "pass the originating plan" mean what SPEC says. Can be
deferred to the dispatch-adapter round if the primary prefers; it is not a guard bypass today.

### NOTE

**N-W2-1. "in ID order" is ambiguous for more than nine rows.** Row IDs are `s1..sN`; lexical order
is `s1, s10, s100, ..., s11, ...` and differs from array order for the 108-row prior source (probe
§3). The row `start`/`end` offsets and the array order disambiguate, so a careful reader is not
misled, but "in row order" or "in the order given" would be unambiguous. Changing it costs a prompt
re-pin (`test_review_only_one_prompt_sentence_changed` pins the exact text and the +60 bytes).

**N-W2-2. `from_compact` output key order changed (canonical-invariant).** w1 preserved the input's
top-level key order (deep copy); w2 emits non-`u/g/l` keys first, then `u`, `g`, `l`
(`wire.py:95-100`); unit dicts move `y` to the end. Canonical bytes are identical (probe §2:
0 canonical diffs, 37/37 `json.dumps` order diffs). Only a consumer serializing codec output without
`sort_keys` would see it. Worth one line in SPEC, nothing more.

**N-W2-3. Binding is opt-in by design.** As ruled in §3: the profile-only call silently skips the
plan check. SPEC documents this; the dispatch adapter's acceptance criteria should require the
`plan=` form so the opt-in cannot be forgotten.

**N-W2-4. `lint_schema` runs twice per path** (inside `schema()` and again in `validate_response` /
`_request`). Harmless and deterministic; mention only so nobody "fixes" one call site and leaves the
mutation test's substituted-`schema` case uncovered.

## Areas examined with nothing found

- `_map` rewrite: every structural `_closed`/`_array` check from w1 is still present at the same
  point; `_closed` precedes every `_map_fragments` call so `item['x']` cannot KeyError; `[]` vs
  `[null]` vs `null` handling unchanged; `RecursionError` is caught only around the two public
  entry points and cannot mask another error type.
- `lint_schema` depth: the deepest node (fragment property under
  `u/items/y/items/c/x/items`) is depth 8 with root 0, exactly the limit; both profiles pass.
- Ordering in `validate_response`: non_stop, profile string, plan, parse, schema lint, checker,
  `to_compact`, r15 validate/expand/contract, wire inverse. The expanded record is r15's object,
  byte-identical to r15.1 (probe §2).
- Pins: r15 READY and R14 common.py constants unchanged from w1; design and protocol READY pins
  pass (own suite `test_all_frozen_dependency_and_design_pins`).
- No `try`/`except` other than the two `RecursionError` catches; no network-capable imports.
- No stray writes: no `__pycache__`/`.pyc` anywhere under round16; only `review-w2/` is new.

## Files written

- `review-w2/REVIEW.md` (this report)
- `review-w2/repro_probes_w2.py` (throwaway probes; read-only, offline; loads w1 and w2 side by side)
