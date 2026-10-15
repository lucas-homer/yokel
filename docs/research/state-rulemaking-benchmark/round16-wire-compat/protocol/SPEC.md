# r16.w1 offline wire adapter

Implements frozen DESIGN.md §§3–5, Route A1. The only compact-data changes
are `v:r16.w1`, fragment objects `{a,h,ho,z,t,to}` replacing six-slot tuples,
and `y:[]` / `y:[{c,z,b}]` replacing null / an object. All other values,
ordering, Unicode codepoints, references and uncertainty are preserved.
Every conversion returns fresh objects. No coercion, normalization, defaults,
repair, clipping, retry, source narrowing or partial expansion is implemented.

`wire.py` exports `WireError(code)` (with `.code` and optional `.details`),
`to_compact`, `from_compact`, `schema`, `validate_response`, and `build`.
The conversions check structure; source-bound schema/semantic checks are the
responsibility of `validate_response`. `schema` accepts `full` and `opaque`;
other profiles raise ValueError. Opaque permits only L/R with zero children.

Decode checks finish reason first, uses frozen r15.1 strict_load including its
raw guard, applies **unchanged R14 check_schema/schema_errors to the wire**,
maps to compact, then calls **unchanged r15.1 validate/expand/contract**.
Canonical compact and wire inverse equality is required before returning.
All errors actually raised by r15.1 propagate unchanged as ValueError with
their original string codes. Schema failures raise WireError; `.details`
contains the unchanged checker diagnostics. Span membership and node syntax
remain authoritative r15.1 host checks.

Dependencies are loaded by path, without modifying/copying the originals.
The r15.1 READY digest is pinned in code; compact.py, prompt and settings bytes
are checked against that manifest before use. R14 common.py has its own
SHA-256 pin. Verified code bytes are executed without reopening the files.
The test runner checks all frozen r15.1/design pins and records hashes of its
read-only inputs before and after testing. No network code or credential access.

Both schemas pass the R14 checker and strict keyword/value-type lint. Maximum
depth is **8** (root=0), with 13 object schemas / 73 properties; total enum
values are **30 full / 25 opaque**. Every object is closed and all properties
required. The full schema matches the pinned design draft exactly.

Reproduce without writes:

```sh
python3 -I -S -B docs/research/state-rulemaking-benchmark/round16-wire-compat/protocol/verify.py
```

`--record` regenerates only this folder's test-output.txt, receipt.json and
READY.json after successful tests. READY pins every payload file, including
the runner, spec, tests and receipts; the manifest excludes its own hash.

## Deviations / ambiguities

- The task's public interface requires `validate_response` to return the
  expanded record directly. This overrides DESIGN §4's illustrative wrapper
  `{wire,compact,expanded}`. Its canonical bytes equal r15.1's expanded record.
- `build` returns r15.1's plan fields plus `under_guard`, even when over 40,000
  guarded bytes. r15.1 build raises `full_request_overflow`; returning an
  explicitly inadmissible offline plan is necessary to satisfy the requested
  over-limit size receipt. No request is dispatched. Any future caller must
  enforce `under_guard` and independently recompute the R14 guard.
- DESIGN's pure inverse pseudocode admits `[null]` as though it were `[]`.
  A1 permits only `[]` or one deadline object; `[null]` is rejected to preserve
  bijection and avoid silent normalization. Exact nested key sets are checked
  by the structural adapter as well as the checker.
- Pure checker array-size failures use WireError code `array_bound`, retaining
  the invalid nine-fragment sizing fixture's r15.1 verdict while rejecting at
  schema step D2. This is checker error classification, **not** a rewrapped
  r15.1 exception. Other schema violations use `wire_schema`. When both schema
  and host rules fail, the specified schema-first order determines rejection;
  no general claim of identical error precedence for arbitrary malformed data.
- The draft prompt edits in DESIGN §9 are used with one explicit sentence:
  `y=[] claims non-deadline function; it never means unknown.` The addition
  costs **62 serialized request bytes**, including escaped newlines. Opaque
  adds a profile instruction. Prompt behavior remains unmeasured.

Measured full-profile requests: prior source **30,350 body / 31,374 guarded
bytes**, 8,626 bytes below the limit; disjoint600-u24 **42,408 body / 43,432
guarded bytes**, **3,432 bytes over the limit**. Both schemas are 5,085 bytes.
These differ from DESIGN's 31,312 / 43,370 by the documented 62 prompt bytes.

Tests cover T1–T6 and all 37 design-probe cases: **32 valid**, byte-identical
compact/expanded round trips, and **5 invalid**, retaining their codes through
the wire path. Nine semantic-negative controls remain mechanically accepted;
that establishes no semantic correctness or completeness. Full-clause sizing
comparators with version `standalone-full-clause-sizing-only` are not r15.1
compact fixtures and are not passed off as codec inputs.

## Open issues for the primary

Offline readiness is not dispatch approval. Provider compatibility, actual
model behavior, prompt review, output-token headroom and semantic completeness
remain unverified. The 24-clause profile remains inadmissible. A future runtime
must pin raw wire/version/codec/schema in receipts because the byte-identical
expanded record intentionally retains the r15.1 expanded version.
