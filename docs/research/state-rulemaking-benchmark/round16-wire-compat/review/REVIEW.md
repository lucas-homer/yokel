# Review: r16.w1 wire codec (protocol/wire.py and companions)

Reviewer: Claude Fable 5.1, independent code-reading review. Date: 2026-10-13.
Scope: `protocol/wire.py`, `test_wire.py`, `verify.py`, `SPEC.md`, `receipt.json`, against frozen
`design/DESIGN.md` (§§3–5, 8, 9) and `inventory/INVENTORY.md`. Nothing outside `review/` was written.
No network or provider call, no credential access, no commit. All Python run as `python3 -I -S -B`.

## Verdict

**No BLOCKER.** I found no path by which a wrong record is accepted, a valid wire record is rejected
through `validate_response`, or a guard is bypassed inside the codec. Two SHOULD-FIX items (one a real
robustness defect in a public export, one the inherited `build()` guard question) and several NOTEs.

Re-run evidence (my own runs, this machine, Python 3.13.7, `sys.flags.safe_path=True` under `-I`):

| Suite | Command | Result |
|---|---|---|
| protocol | `python3 -I -S -B protocol/verify.py` | 75 tests OK; receipt and READY pins match |
| testing (blind) | `python3 -I -S -B testing/test_independent.py` | 55 tests OK |
| dependency pins | independent sha256 of r15 READY, compact.py, stage-a.system.txt, request-settings.json, R14 common.py | all equal the constants in `wire.py:12-13` and the r15 manifest |

Probe script: `review/repro_probes.py` (sections A–H referenced below).

## Findings by severity

### SHOULD-FIX

**SF-1. In-place conversion is sensitive to internal aliasing of in-memory input; a valid compact can be falsely rejected by `from_compact`.**
`wire.py:83-107`. `_map` deep-copies the input (which preserves shared references, since `copy.deepcopy`
uses a memo) and then mutates `unit['y']`, `dimension['x']`, `item['x']` in place. If two units share one
deadline dict, or two units share one `y` list, the second visit sees already-converted content and raises.

Repro (section B): take `fixtures/positive.json`, set `units[j]['y'] = units[i]['y']` (same object, both
units are k3 deadline units with distinct ids). `r15.validate` accepts it; the JSON round-trip of the same
data is accepted by `from_compact`; but `from_compact` on the aliased object raises
`WireError('compact_fragment_shape')`. Decode direction: two wire units sharing one `[D]` list →
`to_compact` raises `WireError('wire_fragment_keys')`. Shared `x` lists and shared fragment tuples are
fine (read-only use).

Reachability: **not reachable through `validate_response`**. Its input always comes from
`r15.strict_load` (fresh objects, no aliasing) and the D6 inverse operates on `r15.contract` output,
which builds fresh containers. So this cannot cause a wrong acceptance. It is a false rejection in a
public, SPEC-exported function used by tests, receipts and fixture authoring; a programmatically built
fixture (`[deadline] * 2` style) or any future caller that reuses Python objects will hit it.
Neither suite covers it (the blind suite's `* 2`/`* 9` cases are negatives rejected for size anyway).

Fix: build new containers instead of mutating the copy (have the per-unit/node/link converter return a
new dict), or deepcopy each item right before mutating it. Pin with a positive test: a compact with two
units sharing one deadline object, and a wire with two units sharing one `y` list, both round-trip.

**SF-2. `build()` hands back a dispatchable `body` for an inadmissible plan (item 1).**
`wire.py:238-241`. For the disjoint600-u24 profile, `build()` returns `under_guard: False`,
`guarded_bytes: 43432`, and a complete `body` with messages and `response_format` (section D).
`r15.build` on the same source raises `full_request_overflow` (`compact.py:445`). In R14 the guard was
enforced three times: `compact.build`, `contract.py:16`, and `adapter.py:129`
(`plan['guarded_bytes']<=40000` immediately before transport). r16 currently has zero enforcement
points: nothing in the repo consumes the r16 plan, so a future adapter written against the r15.1/R14
habit (`plan = build(source); transport(plan['body'])`) would dispatch an over-guard request.

Recommendation: `build()` should refuse, as r15.1 does, raising `ValueError('full_request_overflow')`
by default. Keep the over-limit sizing receipt by adding a separate `measure(source, profile)` (or a
`build(..., allow_overflow=True)` flag) that returns the sizing fields **without** `body`. An
inadmissible plan should never carry a dispatchable body. Independently of that, the eventual dispatch
adapter must still recompute `len(common.encode(body)) + 1024 <= 40000` before transport, as
`adapter.py:129` did. Pin both with tests: (a) oversize source → raises / no `body`; (b) the existing
`test_build_size_profiles_fit_and_overflow` sizing figures continue to come from the measuring path.
If the primary prefers to keep the current report-only `build()`, then SPEC's "any future caller must
enforce `under_guard`" sentence is the only protection and should be promoted into the dispatch task's
acceptance criteria.

**SF-3 (small). The plan does not record `profile` or wire `version`.**
`wire.py:239-241`. `build(source, 'opaque')` and `build(source, 'full')` return plans distinguishable
only by inspecting the embedded schema and prompt. DESIGN §8 R7 says receipts must pin the wire version
and codec/schema; the plan dict is the natural carrier, and an adapter that dispatched the opaque
profile but validated with the default `'full'` profile would silently accept typed nodes at D2.
Add `version=VERSION` and `profile=profile` to the returned plan (and to `receipt.json` sizing blocks).

### NOTE

**N-1. `WireError` is not a `ValueError`** (`wire.py:18`). r15.1 raises `ValueError`, R14 raises
`Denied(ValueError)`. A dispatcher that follows that convention (`except ValueError:` → write a
controlled-rejection receipt) would crash on a `WireError` instead. That is fail-closed, so not a guard
bypass, but it loses the receipt. `class WireError(ValueError)` is a one-line change and keeps all
current tests passing (`test_wire.py:126` checks exact type, `:122` already accepts both). Also, the
`'array_bound'` WireError at `wire.py:189` string-mimics an r15.1 code by design; `.code` plus type
still distinguishes it, and SPEC documents it.

**N-2. Error precedence differs from r15.1 for mixed failures; both reject.** Section C: a unit with
17 `d` entries plus a duplicate unit id yields `WireError('array_bound')`, r15.1 would say
`duplicate_unit`. SPEC already disclaims identical precedence. Every pure-size bound in the wire schema
equals the r15.1 `array()` bound (`u` 1..160, `g`/`l` 0..400, `d`/`b` 0..16, `e` 1..6, node `a` 0..8,
node `x` 0..8, link `x` 0..2, dimension `x` 0..4), so the reclassification never names a code r15.1
would not also have reached for that array.

**N-3. The strict schema lint (T4) lives only in `test_wire.py:40-89`.** Runtime `validate_response`
and `build` run only the shallow `common.check_schema`. DESIGN R4 calls T4 mandatory; READY pins the
test file, so this is acceptable. Optionally move the lint into `wire.py` and call it from `schema()`.
Lint gaps I looked for and did not find material: it fixes the exact keyword set per node type, rejects
type lists, requires `required == list(properties)` and literal `additionalProperties: False`, requires
non-empty unique string enums, and `test_T4_exact_pinned_draft_schema` pins every bound to the frozen
draft, so bound drift is caught. Not checked by lint, harmless: `h`/`t` enum values being 64-hex,
numeric `minimum` being `int` rather than `float`.

**N-4. T3 negatives assert only "raises (WireError | ValueError)"** (`test_wire.py:358-367`), not the
code. Pipeline order is separately pinned by `test_wire_schema_checked_before_host_validate` and the
blind suite asserts codes more tightly. Fine.

**N-5. Direct `to_compact`/`from_compact` on pathologically deep in-memory input hits `RecursionError`
in `copy.deepcopy`** (section H, 3000-deep leaf). Unreachable via `validate_response` (strict_load caps
depth at 64 on the raw). Only an API-misuse hazard.

**N-6. DESIGN §4 errata suggested.** The pseudocode `Y = u.y[0] if u.y else None; if Y is not None`
reads as admitting `[null]`; SPEC and the blind suite both chose rejection. Recording a one-line erratum
in DESIGN (or its READY notes) would stop the next reader from re-litigating it. No code change.

## Items 1–3

**Item 1 (`build()` oversize).** See SF-2. Verdict: not safe to leave as the only point of enforcement.
`build()` itself should refuse by default (matching r15.1 and R14), with a separate measuring entry
point for the sizing receipt; the dispatch adapter must recompute the guard regardless; both should be
pinned by tests.

**Item 2 (`y:[null]` rejected).** Correct reading, confirmed. DESIGN §3 W3 defines the wire `y` as
exactly `[]` or `[{c,z,b}]` with schema "array of the closed deadline object". §5 #25 says the adapter
"never normalizes" and §4's losslessness argument requires `to_wire(from_wire(W)) ≡ W`, which fails for
`[null]` (it would come back as `[]`). The `if Y is not None` in §4's pseudocode is the `[]` guard, not
a licence for `[null]`. Observed (section A): `validate_response` rejects at D2 with
`WireError('wire_schema', ['$.u/0.y/0: type'])`; direct `to_compact` rejects with
`WireError('wire_deadline_keys')` (`wire.py:95-96`). `y: null` is likewise rejected at D2.

**Item 3 (62-byte prompt addition).** No meaning change. The five DESIGN §9 edits are applied with
uniqueness-enforced anchors (`wire.py:214`), and the appended sentence
`y=[] claims non-deadline function; it never means unknown.` restates edited sentence 5
("An empty y is a claim of non-deadline function, not verified by host semantics") and adds the
"never means unknown" clause that DESIGN §9's final paragraph explicitly asks for. r15.1 has no
"unknown" state for `y` (only null, or a closed deadline whose dimensions carry
stated/absent/ambiguous/na), so nothing is added or removed semantically. Measured (section E): 60
text chars, 62 bytes inside the JSON string (two escaped newlines), total prompt delta 155 chars versus
DESIGN's 95 for the five edits alone; no residual "null" anywhere in the edited prompt; the remaining
`headOccurrence`/`tailOccurrence` prose is consistent with edit 2's key glossary. Cosmetic only: the
base prompt already ends in `\n`, so the addition sits after a blank line at the very end rather than
beside the deadline paragraph. The opaque addition is a separate profile instruction and does not alter
any r15.1 sentence.

## Areas examined with nothing found

- **Decode vs DESIGN §4.** `to_compact` is structurally *stricter* than the §4 pseudocode (closed unit
  keys, closed dimension keys, `x` must be a list), but each extra rejection is also an r15.1 rejection,
  and once D2 passes every structural precondition of `to_compact` is implied by the schema, so it
  cannot fail post-D2. Fragment slot order `a,h,ho,z,t,to` matches `compact.py:164`. No key-order
  dependence (lookup by key; canonical sorts). Duplicate keys die at D1 (`object_pairs_hook`).
- **Coercion / defaulting / typing.** None. `ho: true`, `1.0`, `"1"`, `i: 1.0`, `k: true`, `q: false`
  all rejected at D2 with `: type` (`common.py:27` separates bool/float/int); the host re-checks with
  `type(v) is int`. `ho` has no schema maximum by design; `10**30` is rejected by host `head_not_found`.
- **Unicode.** No normalization anywhere. Codepoint length counting is identical in checker and host.
  Cyrillic `ѕ1` span id → host `fragment_span`; NFD-decomposed anchor → host `head_not_found`;
  astral characters round-trip exactly (`test_T6_escaped_astral_pair_and_exact_codepoints`).
- **§5 invariant table.** Walked all 25 rows. Every schema (S) bound equals the r15.1 bound; the rows
  marked host-only (#11/#16/#21) are reached unchanged via `r15.validate`; nothing is pre-normalized
  except the designed `[]`↔`null` mapping.
- **Checker applied to the wire with the request-bound schema.** Yes: `wire.py:181-184` builds
  `schema(source, table, profile)`, whose `h`/`t` enums are `source_hash(source)` / `digest(table)`,
  and `schema()` calls `r15.validate_table` first (`wire.py:128`), so a stale or foreign table raises
  `exact_host_table` before any checker run. `check_schema` precedes `schema_errors` in both
  `validate_response` and `build`.
- **Pinned loading.** `_pinned_bytes` verifies bytes, then `_load` compiles and executes *those bytes*
  (`wire.py:44-49`), so there is no read-verify-reopen gap. r15 READY is pinned by constant; compact.py,
  prompt and settings are pinned transitively through that manifest; R14 common.py by constant.
  Relocating `protocol/` fails closed (missing READY or `dependency_pin`). `module_from_spec` does not
  touch `sys.modules`. Under `-I`, `sys.flags.safe_path` is True on this interpreter, so a planted
  `json.py` in `protocol/` would not be imported; the documented reproduce command uses `-I`.
- **Mutable aliasing of outputs.** None: input is deep-copied before mutation, `schema()` returns a
  `fresh()` tree each call with copied enum lists, `r15.expand` builds fresh containers. (Input-side
  aliasing is SF-1.)
- **Exception handling.** `wire.py` and `verify.py` contain no `try`/`except`. The test code's catches
  are deliberate and narrow.
- **Network-capable code.** None in `wire.py`, `test_wire.py`, `verify.py`, `compact.py` or
  `common.py` (grep for socket/urllib/http/requests/subprocess/environ: only the `$schema` URL string
  constant in `compact.py:363`, unused by r16).
- **`validate_response` return shape.** Returns `r15.expand` output only; canonical bytes equal
  r15.1's expanded record and contain no `r16.w1` string. The caller must hash the raw wire itself for
  R7 provenance (SPEC says so).

## Files written

- `review/REVIEW.md` (this report)
- `review/repro_probes.py` (throwaway probes; read-only, offline)
