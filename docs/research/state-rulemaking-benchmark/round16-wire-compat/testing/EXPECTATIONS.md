# Expected-behaviour choices where DESIGN.md was ambiguous

Each item names the choice the suite enforces and why. The implementer or primary can overrule any of
these by editing the test; none was picked silently.

1. **Return shape of `validate_response`.** The brief says "expanded record"; DESIGN §4 `decode_response`
   returns `{wire, compact, expanded}`. The suite accepts both: a dict with an `expanded` key and no
   `schema_version` is unwrapped, anything else is treated as the expanded record itself. If a `compact` key is
   present it is additionally checked for canonical equality with the r15.1 compact.
2. **How r15.1 errors propagate.** "r15.1 errors propagate with their r15.1 codes" does not fix the exception
   type. The suite accepts any exception whose `.code` attribute or `str()` equals the r15.1 code
   (e.g. `head_not_found`). Checker rejections must be `WireError` specifically.
3. **`WireError.code` values.** DESIGN assigns no code strings to wire violations, so only a non-empty `str`
   `.code` is asserted, never a particular value.
4. **`to_compact` on `y: [null]`.** §4's pseudo-code (`Y = u.y[0] if u.y else None; if Y is not None: …`) would
   let `[null]` decode to "not a deadline". §3 W3 says the wire `y` is `[]` or `[{c,z,b}]`, and the design note
   says `[]` is a positive claim. I treat §3 as normative: `to_compact` must raise `WireError` on `[null]`,
   because silently reading it as a non-deadline claim is exactly the lossy behaviour the format forbids. Through
   `validate_response` the checker catches it anyway (`items.type=object`).
5. **Opaque schema equality.** §3 describes the opaque profile as "the same wire with `o` enum `["L","R"]` and node
   `a` `maxItems:0`". The suite asserts strict equality with the full schema after patching exactly those two
   keywords. A legitimately different opaque schema (say, also dropping `x` bounds) would fail and should be argued
   in DESIGN first.
6. **Full schema pinned to `schema.draft.json`.** The draft is frozen in `design/READY.json` and documented as
   source-dependent only in `h`, `t` and the span-ID `maxLength` W. The suite therefore asserts
   `schema(source, table, 'full')` equals the draft with those three substitutions, and 5,085 canonical bytes for any
   table below 1,000 rows. Node-ID bounds stay 2..4 regardless of table size (§3 "Node ID" row).
7. **`build` on an oversize source.** r15.1 raised `full_request_overflow`; DESIGN §7 instead *measures* over-guard
   profiles and marks them ✗. The suite accepts either: a raise carrying `full_request_overflow`, or a returned plan
   whose `guarded_bytes` is honestly `body + 1024 > 40000` and whose boolean fields are all `False`. For a
   within-guard plan all boolean fields must be `True`. The implementation observed at run time takes the report
   route (`under_guard: False`), so the dispatch guard must be enforced by the runtime adapter (§8 R9); the primary
   should confirm that. Plan key names `body`, `body_bytes`, `guarded_bytes`, `request_sha256` are assumed from
   r15.1 `build`; `table` is optional and checked only if present.
8. **System prompt.** §3 W1 and §9 edit 1 make the prompt ask for an `r16.w1` envelope. The suite requires the
   substring `r16.w1` and forbids `r15.1 envelope`. Nothing else about the (unreviewed) prompt is asserted.
9. **"Nesting depth ≤ 10 under OpenAI counting".** OpenAI does not define its counting in the inventory. The suite
   counts like the checker (root 0, +1 per `properties` value or `items` hop) and asserts the design's figure of 8
   plus the ≤ 10 limit. If OpenAI counts the root as 1 the schema is at 9, still within limit.
10. **Scalar coercion in `to_compact`.** §4 calls `from_wire` "pure structure"; type checking belongs to the checker
    (D2) and r15.1 (D4). So `to_compact` may either raise `WireError` on `ho: true` or pass the value through; what
    it must never do is coerce (`True`→`1`, `1.0`→`1`, `"1"`→`1`). The suite checks identity of type and value when
    no error is raised.
11. **Bad profile.** The brief says `schema()` raises `ValueError`; the suite requires that strictly (including for
    `None`, `''`, `'FULL'`). For `validate_response` and `build` any exception is accepted, since a `WireError` would
    also be defensible there.
12. **Pipeline order.** Assertions assume D0→D1→D2→D3→D4: `non_stop` fires on unparsable raw; a duplicate key inside
    a fragment object is reported with the r15.1 `duplicate_key` code (D1 precedes the checker); `y: null` is a
    `WireError` (D2) rather than r15.1 `closed_keys`.
13. **Short-but-absent span IDs.** On the 9-row authored source W = 2, so `s0`, `S1`, Cyrillic `ѕ1` and fullwidth
    `s１` are the schema-passing absent IDs; `s99`, `s00`, `s01` are tested on a 10-row source where W = 3.
14. **No `r16.w1` string in the expanded record.** §8 R7/Q5 keep provenance out of the expanded record to preserve
    byte identity; the suite asserts the canonical expanded bytes do not contain `r16.w1`.
15. **`schema()` freshness.** Not stated in DESIGN, but in the spirit of T5: mutating a returned schema must not
    change the next call's result (a cached, shared dict would be a correctness hazard for `build`).
16. **Stale table / wrong source.** Only "raises" is asserted, not a code: the failure could surface as r15.1
    `exact_host_table` from D2's `wire_schema(source, table)` or from D4.
17. **Malformed raw JSON** (trailing data, truncation, top-level array): r15.1 raises `json`'s own `ValueError`
    with no code, so only "raises" is asserted.
18. **Opaque fixture.** DESIGN gives no opaque fixture; the suite authors a two-unit clause-only inventory (one `L`
    leaf, one `R` leaf, `onlyif` and `if` links) that validates under r15.1.
