# R16 wire codec: independent adversarial test plan

Blind suite for `protocol/wire.py` (r16.w1). The protocol directory was **not read**; `wire.py` is imported
by path at run time only. Oracles: the frozen r15.1 `compact.py` (expansion, error codes), the unchanged
R14 `common.py` checker, the pinned `design/schema.draft.json`, and the text of `design/DESIGN.md`
(frozen 2026-10-13, `design/READY.json`). Section numbers below are DESIGN.md sections.

Run: `python3 -I -S -B test_independent.py` (or `-m unittest discover -s testing -p test_independent.py`).
Without `protocol/wire.py` every codec test skips and the six reference self-tests still run.

## Threat model: what a lossy or loose codec gets wrong

A codec that "mostly works" fails in one of these ways, and each family below is aimed at one of them:

1. **Meaning drift on `y`.** Treating `[]` as "unknown", collapsing an explicit all-absent deadline into `[]`,
   or decoding `[null]` as a non-deadline claim.
2. **Positional sloppiness.** Mapping fragment objects by insertion order instead of key name; swapping
   `a`/`z` or `ho`/`to`; zero-based occurrences.
3. **Openness.** Accepting extra or missing keys, tuples, nulls or wrong scalar types that the schema is
   supposed to close, or normalising them instead of rejecting.
4. **Guarding the wrong object.** Running the checker on the compact instead of the wire, or accepting an
   r15.1-shaped body on the wire.
5. **Losing host-only invariants.** The schema now only length-bounds span and node IDs (§5 rows 11, 16,
   21). `c0`, `c01`, `c401`, `s0`, Unicode lookalikes and whitespace anchors must still die on the host with
   their r15.1 codes.
6. **Schema rot.** The R14 meta-check does not validate keyword values (§1, §8 R4); `additionalProperties:{}`,
   a missing `type`, or a type list would silently stop being enforced.
7. **Profile leakage.** The opaque profile accepting operator nodes or children.
8. **Aliasing.** Returned objects sharing structure with inputs or with each other.
9. **Byte drift.** The expanded record differing in any byte from r15.1 for the same content, or naming the
   wire version.
10. **Guard dishonesty.** Reporting a request as within the 40,000-byte guard when it is not.

## Families

| ID | Family (test class) | Claim under test | DESIGN basis | Adversarial cases |
|---|---|---|---|---|
| R | `ReferenceSelfTests` | The oracle itself is coherent: authored fixture == frozen `positive.json`; every host-only negative passes the expected schema and fails r15.1 with the claimed code; every checker-caught negative fails the expected schema; draft figures (depth 8, 13 objects, 73 properties, 5,085 B) | §4, §5, §6, §7 | runs with or without `wire.py` |
| M | `WireModuleTests` | `wire.py` imports by path under `-I -S -B` and exposes the six interface names; `WireError` is an `Exception` | interface | import failure is a failure, not a skip |
| A | `CodecShapeTests` | `from_compact` produces exactly the §3 shape (four syntactic changes, nothing else); `to_compact` is its exact inverse on every frozen fixture; fragment fields map by key name; `y` `[]`↔`null`, `[Y]`↔`Y`; structural violations raise `WireError` with a `.code`; no scalar coercion; invalid-but-shaped compacts still map (T2) | §3 W1–W3, §4 T1/T2/T3 | reversed key order, tuple fragments, `[null]`, two-item `y`, `y` object, extra/missing keys at every level, bool/float/str/negative/huge in `ho` |
| B | `AliasingTests` | Fresh objects in both directions and between the parts of a `validate_response` result; inputs untouched | §4 T5 | mutate nested fragment, child list, deadline evidence after the call |
| C | `SchemaTests` | `schema()` equals the pinned draft instantiated for the source (only `h`, `t`, span `maxLength` W vary); opaque differs only in `o` enum and `a` `maxItems`; other profiles raise `ValueError`; T4 lint (scalar `type` everywhere, closed and fully-required objects, literal `False`, keyword allowlist, `items` is a dict, integer bounds are ints); provider rules (depth 8 ≤ 10, enum total ≤ 1,000); no false rejection of any valid wire; results fresh per call | §3 table, §4 T4, §6, inventory §3 | tables with W = 2, 3, 4, 5; mutate a returned schema then call again |
| D | `PipelineAcceptTests` | `validate_response` yields an expanded record byte-identical to `R.expand` of the equivalent compact for all 18 frozen/authored fixtures; r15.1 flags and version unchanged, no `r16.w1` string; fragments recorded as tuples; occurrence semantics (`ho`=2/`to`=1 → offset +10, `ho`=1/`to`=3 → whole row, `ho`=3/`to`=1 → offset +20); `a`/`z` direction; `y:[]` is "not a deadline" and an all-absent deadline stays explicit; raw-JSON key order is irrelevant; boundary values accepted (`c400`, unit 160, 159 units, 399 nodes/links, depth 12, 48-codepoint and combining-mark anchors); opaque wires decode identically under both profiles | §3, §4 D0–D6, §5 rows 4/15/16/23, §8 R7 | NFC variant anchors, `b/z/c` dimension order with `na` on `b` |
| E | `PipelineRejectTests` | Pipeline order and codes: `non_stop` before parsing; raw guards on the wire text with r15.1 codes (duplicate keys at three depths, NaN/Infinity, unpaired surrogate, depth 65, 600,001 B; 600,000 B accepted); 51 checker negatives → `WireError`; an r15.1 compact on the wire → `WireError`; 31 host-only negatives keep r15.1 codes; short-but-absent IDs on a 10-row table; sentinels 160/400/400, depth 13, cycle, orphan, dangling link; opaque rejects AND/NOT/children; unknown profile, stale table, wrong source reject; final-node error rejects the whole response | §4 D0–D4, T3, T6; §5 rows 4, 8, 11, 16, 21, 22, 25 | Cyrillic `с`/`ѕ`, Arabic-Indic digit, fullwidth digit, `C1`, `S1`, `c-1`, `c007` |
| F | `BuildTests` | Plan counts (`body_bytes` = canonical body, `guarded` = +1,024 ≤ 40,000, `request_sha256`), strict `json_schema` bound to `schema(source, table, profile)`, pinned user envelope with exact source and `r15.spans.2` table, system prompt names `r16.w1`, default profile full, bad profile raises, oversize source raises or reports honestly, 5,085-byte schema regardless of span count | §1, §3 W1, §7, §9 | 40,000-byte source, unpaired-surrogate source, blank source |

Test counts: 55 test methods (6 reference, 1 module, 8 shape, 3 aliasing, 9 schema, 10 accept, 12 reject, 6 build),
expanding to several hundred sub-tests through the negative tables and fixture loops.

## Deliberately out of scope

- Provider acceptance or enforcement of any keyword (no network, §6 is UNVERIFIED by design).
- Sizing figures for the prior R14 source (§7) and the real reviewed prompt (§9 is a byte draft).
- D6's canonical re-encoding step: it is unobservable from outside while `R.expand` is unchanged.
- Semantic correctness of any inventory (r15.1 semantic negatives are accepted on purpose, §5 row 23).
