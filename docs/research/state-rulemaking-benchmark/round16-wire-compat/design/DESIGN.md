# R16 wire compatibility: object-fragment wire for the r15.1 condition inventory

Advisory design (Opus, Claude Code subscription session). It covers BLOCKER 1 only: the r15.1 schema is not accepted by the unchanged R14 runtime checker. Nothing outside this folder was edited. No provider call, credential read, install or commit was made.

Files in this folder:

- `DESIGN.md`: this document.
- `schema.draft.json`: the proposed wire schema, instantiated for the prior (R14 parsed-body) source. Its `h`/`t` enums and span-ID `maxLength` depend on the source.
- `probe.py`: an offline design probe. It imports the frozen r15.1 `compact.py` and the unchanged R14 `common.py`, with read-only inputs, and prints JSON. It is a measuring aid, not the codec.
- `probe-results.json`: the probe output these numbers come from. Reproduce it with `python3 -I -B probe.py`.

Labels used below: **VERIFIED** means read in code or reproduced by the probe, with a citation. **PROPOSAL** is a design choice. **ESTIMATE** is arithmetic or an assumption. **UNVERIFIED** means no repo evidence.

---

## 1. What the R14 checker accepts and enforces (VERIFIED)

File: `round14-semantic-contract/runtime/common.py` (63 lines, unchanged).

**Meta-check `check_schema` (L49–53).**
- Every schema node must be a `dict` whose keys are a subset of `{type, properties, required, additionalProperties, enum, minimum, maximum, minLength, maxLength, items, minItems, maxItems}` (L50–51).
- Nesting depth must be ≤ 16 (L51). Depth increases only through `properties` values (L52) and `items` (L53).
- Consequences:
  - `$schema`, `anyOf`/`oneOf`/`allOf`, `prefixItems`, `pattern`, `const`, `$ref`/`$defs`, `uniqueItems`, `format`, `description` and `title` are all rejected.
  - Boolean schemas are rejected (`items: false` fails `isinstance(node, dict)`, L51).
  - Keyword values are **not** checked. For example, `additionalProperties: {…}` passes the meta-check and is then silently unenforced, and `required` entries are not checked against `properties`.

**Instance check `schema_errors` (L25–40).**

| Keyword | Enforcement | Line |
|---|---|---|
| `type` (string **or list**) | Actual type: `null`/`boolean`/`integer`/`number`/`string`/`array`/`object`. `bool` is never an integer, and `1.0` is `number`, not `integer`. `integer` satisfies `number`. A mismatch returns early. If no `type` is declared, the type is not checked. | L26–28 |
| `enum` | Python `value in list`, which uses equality: without a declared `type`, `1 == True == 1.0`. | L29 |
| `required` | Key presence on objects | L31 |
| `additionalProperties` | Enforced **only if it is literally `False`** | L32 |
| `properties` | Recurses for keys present in both | L33–34 |
| `minItems`/`maxItems` | Array length | L36 |
| `items` | A single homogeneous schema for every element. The default `{}` accepts anything. | L37 |
| `minLength`/`maxLength` | Python `len()`, which counts Unicode codepoints | L38 |
| `minimum`/`maximum` | Integer and number only | L39 |

**How the R14 runtime uses it (VERIFIED).**
- `contract.py:15` runs `check_schema` at build. `contract.py:20` runs `check_schema` and requires `not schema_errors(compact, schema)` on the response.
- The guard is `len(encode(body)) + 1024 <= 40000` (`contract.py:16`, `adapter.py:129`).
- `contract.py:14` pins the user envelope keys `{source_text, source_text_sha256, span_table, span_table_sha256}`.

**Reproduced.** The probe confirms that `check_schema` rejects the source-bound r15.1 schema and accepts `schema.draft.json` (`probe-results.json`: `r15_1_schema_rejected_by_r14_checker`, `wire_schema_accepted_by_r14_checker`).

Type lists (for example `["object","null"]`) **are** supported by this checker (L26–28). That makes a nullable form possible without `anyOf`. The proposal below still avoids it, for the provider-evidence reasons in §6.

---

## 2. Route decision

**Chosen: Route A (A1, object fragments). The checker stays unchanged and loosens nothing.**

There is no concrete obstacle to A:
- Every r15.1 schema construct has a checker-dialect equivalent.
- Every invariant that a removed keyword expressed is already enforced by the frozen r15.1 host validator.
- Every keyword form in A1 also appears in the one request the provider route actually accepted (R14 live run; see §6).

Route B, a new checker dialect, would mean a new reviewed validator and still would not show that the provider accepts `prefixItems`/`anyOf`/`pattern`. No repo evidence shows that it does. B stays the fallback only if the primary wants positional tuples at schema level.

**Measured alternative A0, not recommended by default.**
- A0 keeps r15.1 tuples, typed by one homogeneous union item schema `{"type":["string","integer"],minLength:1,maxLength:48,minimum:1}`, and makes `y` nullable through `type:["object","null"]`.
- The R14 checker accepts it, and A0 adds about 0 output bytes.
- Positional typing becomes host-only, though r15.1 already checks it at `compact.py:163-170`.
- It depends on type-list unions, which have no repo evidence of provider acceptance.
- A0 is the right switch if output headroom turns out to be the binding constraint and the provider inventory confirms type-list support (§8, Q1).

---

## 3. The A1 wire format (PROPOSAL)

Rule: **the wire is the r15.1 compact object with exactly four syntactic changes**. Every other key, value, type, order and ID string is identical, including span IDs `"sN"` and node IDs `"cN"`.

| # | r15.1 compact | A1 wire | Schema (checker dialect) |
|---|---|---|---|
| W1 | `v: "r15.1"` | `v: "r16.w1"` | `enum:["r16.w1"]` |
| W2 | Fragment tuple `[a, head, headOcc, z, tail, tailOcc]` | Object `{"a":…, "h":…, "ho":…, "z":…, "t":…, "to":…}` | Closed object, all 6 required. `a`,`z`: string 2..W (W = longest span ID). `h`,`t`: string 1..48. `ho`,`to`: integer ≥1. |
| W3 | Unit `y: null` or `y: {c,z,b}` | `y: []` or `y: [{c,z,b}]` | Array of the closed deadline object, `minItems 0`, `maxItems 1` |
| W4 | Span-ID `enum` (repeated 11× per schema) | Same strings, `type:string, minLength:2, maxLength:W` | Membership is checked on the host |
| — | Node ID `pattern ^c[1-9][0-9]{0,2}$` | Same strings, `type:string, minLength:2, maxLength:4` | Syntax and range ≤400 are checked on the host |
| — | `$schema` | Removed | (metadata only) |

Envelope `{v,h,t,u,g,l,z}`, unit `{i,k,s,m,p,y,d,b,e,q,r}`, node `{i,o,a,x,g,q,r}`, link `{u,w,n,x,q,r}` and dimension `{s,x,r}` are unchanged. All keys are required and `additionalProperties:false` applies at every object level. There are no defaults, optional keys or type unions.

Design notes:

- **Span and node IDs keep their r15.1 strings on purpose.** Integers would make the schema enforce range, but they would put span, unit and node references in one integer namespace that differs only by key. For example, node `a` (children) and fragment `a` (start span) would both be integer-like. Keeping `s…`/`c…` means the model sees no ID change and the codec maps IDs by identity. The probe's integer-free design still cuts the schema from 11,776 to 5,085 bytes.
- **`y: []` means the same as r15.1 `y: null`.** It is a positive claim that the unit is not a deadline. It never means "unknown". The prompt must say so (draft edits are in §9).
- **Complete clauses are the default, and typed logic is an optional layer.** The wire carries both without change.
  - A complete clause is one `L` leaf with 1..8 whole fragments plus an `if`/`onlyif`/`unless`/`qual` link.
  - Typed logic is `AND`/`OR`/`NOT`/`EXC`/`ALT` nodes.
  - **Optional PROPOSAL, "opaque profile" schema:** the same wire with `o` enum `["L","R"]` and node `a` `maxItems:0`. The checker can then enforce a clause-only dispatch, and the result decodes to the same r15.1 object. The schema size change is negligible.
  - Unresolved states stay explicit and are copied verbatim: `p:2`, `q`/`r`, `qual` links, `R` nodes, `ALT`, and dimension `absent`/`ambiguous`/`na`.

Example. The r15.1 fragment `["s3","Comments must",1,"s4","p.m.",1]` becomes `{"a":"s3","h":"Comments must","ho":1,"z":"s4","t":"p.m.","to":1}`.

---

## 4. Inverse mapping, wire to r15.1 expanded (PROPOSAL, precise enough to implement)

Let `R` be the **pinned, unchanged** r15.1 `compact.py`. Decode never repairs, coerces, defaults, sorts, deduplicates or trims. Any failure rejects the whole response with a controlled error and no partial expansion.

```
decode_response(raw, finish_reason, source, table):
  D0  require finish_reason == "stop"                       (before parsing)
  D1  W = R.strict_load(raw)                                 (raw ≤600000 B, nesting ≤64, dup keys,
                                                              nonfinite, unpaired surrogates)
  D2  S = wire_schema(source, table); common.check_schema(S); require common.schema_errors(W, S) == []
  D3  C = from_wire(W)
  D4  R.validate(C, source, table)                           (ALL r15.1 host invariants)
  D5  E = R.expand(C, source, table)                         (round15.expanded-inventory.v2)
  D6  require R.contract(E, source, table) == C and to_wire(R.contract(E,…)) == W  (canonical bytes)
  return {wire: W, compact: C, expanded: E}

from_wire(W):                         # pure structure; all leaf values copied by value (deep copy)
  require W is dict, keys(W) == {v,h,t,u,g,l,z}; require W.v == "r16.w1"
  C = deepcopy(W); C.v = "r15.1"
  require C.u, C.g, C.l are lists
  for u in C.u (in order):
      require u is dict with "y", u.y is list, len(u.y) ≤ 1
      Y = u.y[0] if u.y else None
      if Y is not None: require keys(Y) == {c,z,b}; for each dim: dim.x = [F(o) for o in dim.x]
      u.y = Y
  for item in C.g ++ C.l (in order): item.x = [F(o) for o in item.x]
  return C
F(o): require o is dict and keys(o) == {a,h,ho,z,t,to}; return [o.a, o.h, o.ho, o.z, o.t, o.to]

to_wire(C):                           # exact inverse of from_wire on any r15.1-shaped C
  W = deepcopy(C); W.v = "r16.w1"
  for u in W.u: (map dim.x tuples → objects if u.y not None); u.y = [] if u.y is None else [u.y]
  for item in W.g ++ W.l: item.x = [dict(zip([a,h,ho,z,t,to], f)) for f in item.x]
```

Expanded to wire (for round-trip tests): `W = to_wire(R.contract(E, source, table))`. `R.contract` already proves `E` equals the canonical re-expansion.

**Losslessness argument.**
- `from_wire`/`to_wire` changes only three things: the version constant, the `y` wrapper (`[]`↔`null`, `[Y]`↔`Y`), and fragment container shape. Those three have the same positional content, the same order and exact key sets.
- IDs and all other values pass through unchanged.
- So for every r15.1-shaped `C`, `from_wire(to_wire(C)) ≡ C`, and for every wire `W` that `from_wire` accepts, `to_wire(from_wire(W)) ≡ W`.
- `E` is produced by the unchanged `R.expand`, so the expanded record is **byte-identical** to the r15.1 expanded record for the same content. It does not record the wire version; see R7.

**Required equivalence tests** (for the implementer). The probe already runs T1–T3 on authored fixtures:

- **T1.** For every valid r15.1 fixture `C`:
  - `schema_errors(to_wire(C), S) == []`, meaning no false schema rejection
  - `canonical(from_wire(to_wire(C))) == canonical(C)`
  - `canonical(R.expand(from_wire(to_wire(C)))) == canonical(R.expand(C))`
  - `canonical(to_wire(R.contract(R.expand(C)))) == canonical(to_wire(C))`
- **T2.** For every invalid r15.1 fixture: `R.validate(from_wire(to_wire(C)))` fails with the **same error code** as `R.validate(C)`.
- **T3.** Wire negatives, rejected by the checker and/or the host:
  - tuple-shaped fragment; missing or extra fragment key
  - `ho` set to 0, `true` or `1.0`
  - empty or whitespace anchor
  - `y: null`; `y` with 2 items
  - `v:"r15.1"`
  - span ID too long, or short but absent
  - node ID too long, bad prefix, leading zero, `c401`
- **T4.** Schema lint, which closes the checker meta-semantics gap in §1:
  - every node declares `type`
  - every object has `required == keys(properties)` and `additionalProperties is False`
  - no type lists (A1)
  - the keyword set is a subset of the R14-accepted set (§6)
  - depth ≤ 16
- **T5.** No aliasing: mutating the returned `C` or `E` does not mutate `W`, and the reverse (as in the r15.1 hardening tests).
- **T6.** `R.strict_load` limits are applied to the raw **wire** text.

**Probe results (VERIFIED by running it; authored fixtures only, no model output).**
- 37 cases: r15.1 `fixtures/positive`, 9 semantic negatives, 5 `long_*` graphs, 19 sizing profiles translated r15.0→r15.1 the way `sizing/revised` did, and 3 revised controls.
  - All 32 valid cases: bijective, expanded-equal and contract→wire-equal, with **0 false schema rejections**.
  - All 5 invalid cases keep their r15.1 error code (`array_bound`, `graph_depth` ×2, `capacity_review_g`, `capacity_review_l`).
- All 17 T3 negatives reject. The checker catches 13. Four are host-only, and these are exactly the cases expected from §5: whitespace anchor and three short malformed node IDs.

---

## 5. r15.1 invariants and where each is enforced in A1

Key: **S** means the R14 checker enforces it on `W`. **A** means the `from_wire` adapter. **V** means the unchanged r15.1 `validate` (`compact.py` line numbers). "r15.1 schema" shows what the old schema expressed.

| # | Invariant | r15.1 schema | A1 enforcement |
|---|---|---|---|
| 1 | Envelope closed `{v,h,t,u,g,l,z}`; `z=END` | yes | S, A, V209/211 |
| 2 | Version binding | enum | S (`r16.w1`), A (→`r15.1`), V210 |
| 3 | `h` = source SHA-256, `t` = table digest | enum | S (unchanged), V210 |
| 4 | Counts `u` 1..160, `g`/`l` 0..400, plus sentinel rejection at 160/400 | bounds | S bounds; sentinels V212–214 |
| 5 | Closed unit/node/link/dimension/deadline keys | yes | S, A (deadline, fragment), V218/237/264/285/193 |
| 6 | Integer fields and ranges; no bool-as-int, no float-as-int | yes | S (`common.py:27` separates bool/float), V70–71 |
| 7 | Unique unit IDs, unique node IDs | no | V221, V266 |
| 8 | `s` 1..280 **nonblank**; `r` ≤180; `g` ≤120; anchors 1..48 **nonblank** | lengths only | S lengths; nonblank V74–77 |
| 9 | `q=0` ⇔ `r==""`; `m=5`⇒`q≠0`; `p=2`⇒`q≠0` | no | V84–87, V225–226 |
| 10 | `d`/`b` ≤16, int 1..160, unique; `d` acyclic/closed; `b` members exist; k7 ≥2 non-self; otherwise empty; k5 first `d` is k4 | bounds | S bounds; V227–261 |
| 11 | **`e` span IDs exist in the table** | **enum** | **moves to host only:** V233. S keeps the count 1..6 and string length. |
| 12 | `e` unique | no | V234 |
| 13 | **`y` is null or a closed deadline** | **`anyOf`** | S (array 0..1 of the closed object), A (`[]`↔null), V237 |
| 14 | `y` non-null only when `k=3` | no | V236 |
| 15 | Dimension state ∈ STATES; absent → 0 fragments, else 1..4; ambiguous/na need a nonblank `r`; `na` only on `b`; absent/ambiguous ⇒ unit `q≠0` | partly | S enum and 0..4; V193–202, V240 |
| 16 | **Node ID syntax `c1..c400`, no leading zero (`g.i`, `g.a[]`, `l.n`)** | **`pattern`** | **moves to host only:** V90–92 (called at V265/273/287). S keeps string length 2..4. |
| 17 | Operator ∈ OPS; arity (L/R 0, NOT 1, EXC 2, AND/OR/ALT 2..8); no dup/self child; R⇒q=2; ALT⇒q=1; leaf fragments 1..8, operator 0..4 | enum, counts | S enum and bounds; V268–280 |
| 18 | Link role ∈ ROLES; `u`/`n` exist; `qual`⇒link `q≠0` and unit `p=2`; link fragments 0..2; `(u,w,n)` unique; ≤1 if/onlyif/unless/obj per unit; p0/p1/p2 applicability counts | enum, bounds | S enum and bounds; V284–304 |
| 19 | Graph: no dangling/cyclic children; depth ≤12 from link roots; no orphans; iterative walk | no | V305–335 |
| 20 | **Fragment: exactly 6 positional slots with types** | **`prefixItems` + `items:false`** | **Still schema-enforced:** S closed 6-key object with per-key types. Also A (exact key set) and V163–170 (arity 6, types, positive occurrences). |
| 21 | Fragment resolution: spans exist; end row ≥ start row; indexed head; conditional tail; ascending non-overlapping lists | span enum | V161–189. Span existence is host-only, as in #11. |
| 22 | Raw ≤600,000 B, nesting ≤64, dup keys, nonfinite, unpaired surrogates | no | V95–135 on the **wire raw**. Conservative: the wire is about 26 B/fragment larger. Probe max nesting is 8 levels. |
| 23 | Expanded flags: completeness/condition_coverage/semantic_validity `unverified`, evaluation `not_performed`, production_eligible/action_ready `false`, evidence_match `exact` | n/a | Unchanged V390–391 |
| 24 | Exact inverse retains the selected tuple; no reconstruction defaults | n/a | Unchanged V394–435 plus D6 |
| 25 | Finish reason `stop`; no clipping/retry/repair/prefix salvage | n/a | D0. A never normalizes: tuple, `null` `y` and extra keys **reject**. |

**What actually moves host-side.** Only #11/#21 (span-ID membership, previously a schema `enum`) and #16 (node-ID syntax and range, previously `pattern`). r15.1's `validate` already enforced both in the same validation step, so the authoritative check is unchanged.

#13 (`anyOf`) and #20 (`prefixItems`/`items:false`) **remain schema-enforced** in an equivalent form. `$schema` carried no invariant.

The checker never had to enforce nonblankness, uniqueness, or cross-reference and graph rules. Those were host-only in r15.1 as well.

---

## 6. Provider-side constructs

**Repo evidence (VERIFIED, limited).** The R14 live request, `round14-semantic-contract/execution/run/request.json`:
- Its canonical SHA-256 `91ed8a79…54c4f` equals `request_sha256` in `execution/run/result.json`.
- It sent `response_format.type=json_schema` with `strict:true`.
- Its schema used only `{type, properties, required (= all properties), additionalProperties:false, enum, minimum, maximum, minLength, maxLength, items, minItems, maxItems}`, with depth 4, 2 objects, 15 properties, 1,790 bytes, a 108-value string enum and two single-value 64-character hash enums.
- `execution/run/status.json` shows `http_status 200`. `result.json` shows `finish_reason "stop"`, provider `OpenAI`, model `openai/gpt-6.1-sol`.

This shows the route **accepted** such a request once. It does **not** show that the provider **enforced** any keyword: a conforming output could be prompt-driven. It also says nothing about larger or deeper schemas.

| Construct used | Status |
|---|---|
| A1: closed objects with all properties required, `additionalProperties:false` | Accepted in R14 request; enforcement **UNVERIFIED** |
| A1: string/integer/array/enum with min/max bounds; single-value string enums | Accepted in R14 request; enforcement **UNVERIFIED** |
| A1: integer with `minimum` only (`ho`/`to`) | **UNVERIFIED** (R14 always paired min and max) |
| A1: array `minItems 0`/`maxItems 1` of objects (`y`) | **UNVERIFIED** as a specific form; arrays of objects were accepted in R14 |
| A1: depth 8, 13 object schemas, 73 properties, 5,085 B | **UNVERIFIED** (R14: depth 4, 2 objects, 15 properties, 1,790 B) |
| A0: type-list unions `["string","integer"]`, `["object","null"]` | **UNVERIFIED**; no repo evidence |
| r15.1: `anyOf`, `prefixItems`, `items:false`, `pattern`, `$schema` | **UNVERIFIED**; never dispatched |

These rows should go to the separate provider-inventory task. `request-settings.json` has `require_parameters:true`. That is routing configuration, not evidence about schema features.

---

## 7. Sizing

**Measured offline by `probe.py`** (`probe-results.json` → `sizing`). Values are guarded bytes, meaning canonical body plus 1,024, against the 40,000 guard. The probe reproduces the frozen r15.1 figures of **37,908** and **44,323** exactly, which anchors the method.

| Profile (spans / source bytes) | r15.1 | A1, r15.1 prompt | **A1 + draft prompt edits** | A0, r15.1 prompt | A1 + rows-only envelope (§8 Q2) |
|---|---:|---:|---:|---:|---:|
| Prior source, R14 parsed body (108 / 7,208) | 37,908 | 31,217 | **31,312** (8,688 headroom) | 29,910 | 23,869 |
| disjoint600-u24 (24 / 14,423) | 44,323 ✗ | 43,275 ✗ | **43,370 ✗** (+3,370 over) | 41,968 ✗ | 28,880 |
| disjoint160-u24 (24 / 3,863) | 23,178 | 22,130 | 22,225 | 20,823 | 18,295 |
| disjoint600-u8 (8 / 4,807) | 23,568 | 23,565 | 23,660 | 22,258 | 18,818 |

**Schema bytes.**
- r15.1: 11,776 for the prior source and 6,133 for the 24-span profile. The span enum is repeated 11×, so the size grows with span count.
- A1: **5,085 for both**. It is now essentially independent of span count; only the `maxLength` digit changes.
- A0: 3,778.

**Draft prompt edits** add 95 bytes (§9). The real reviewed prompt will differ, so treat these columns as ±a few hundred bytes (ESTIMATE).

**24-clause conclusion (VERIFIED by measurement).** No schema change alone admits disjoint600-u24.
- Its user message is 29,871 B for a 14,423 B source, because the envelope carries the source twice (`source_text` plus every row's text) and is double-serialized as a JSON string.
- The A1 schema is only 5,085 B of the total.
- Removing `source_text` measures 28,880, but that changes the request envelope. The R14 runtime pins that envelope (`contract.py:14`), and the change alters what the model sees. It is out of this wire's scope (Q2).

**Output size (measured on fixtures; token figures are ESTIMATES).**
- Exact canonical delta: A1 − r15.1 = **26·F − 2·U_nondeadline + 2·U_deadline + 1** bytes, where F is the fragment count.
- The formula checks out on four fixtures, e.g. `positive`: 22 fragments, 4 deadline units, 3 null: +575.
- Paired controls: opaque 638 → 663 (+25) and typed 868 → 1,023 (+155). Typed goes from 36% to 54% larger than opaque, because object fragments tax connective fragments.
- R14's aggregate 22,686 B / 7,231 tokens ≈ 3.14 B/token (frozen observation, not a per-construct tokenizer). At that ratio a fragment costs about **+8 tokens, likely more** for punctuation-dense keys (ESTIMATE). Illustration: 150 fragments ≈ +3.9 KB ≈ +1,240 tokens, against an 8,192 cap that R14 already ran at 7,231.
- Output headroom was unestablished in R15 and A1 makes it worse. A0 costs about +1 B in total.

---

## 8. Risks and open questions for the primary

**Risks**
- **R1. Output budget (main risk).** A1 adds 26 B/fragment (§7). A variant `{"s":[a,z],"x":[h,t],"o":[ho,to]}` with three homogeneous pair arrays would cost about 18 B/fragment (ESTIMATE, not probed), but it is less readable and the field names would need care.
- **R2. Model behaviour is unmeasured.** Object fragments and `y` lists are a model-facing change. No extraction evidence exists.
- **R3. Two IDs lose schema-level guarding.** If a provider does enforce `enum`/`pattern` (UNVERIFIED), a bad span or node ID that was previously impossible now produces an intact whole-output rejection, with no repair. Middle option: keep the span enum only on unit `e` (1 occurrence, about +650 B for 108 spans; ESTIMATE).
- **R4. Checker meta-semantics.** `check_schema` does not validate keyword values (§1), so test T4 is mandatory. Without it, a future schema edit such as `additionalProperties:{}` or an omitted `type` would silently stop being enforced.
- **R5. The checker is not JSON Schema.** It rejects `1.0` for integers and counts lengths in codepoints. A provider-valid output can therefore fail. That is a conservative, intact stop, but it should be expected.
- **R6.** The raw 600 KB limit now applies to a slightly larger encoding. This is conservative and unreachable at 8,192 output tokens.
- **R7. Provenance.** The expanded record is identical to r15.1 and does not name the wire version. Runtime receipts must pin the raw wire, its digest, the `r16.w1` version and the codec/schema hashes.
- **R8. Key-name overloading.** `a`, `h`, `t` and `z` mean different things at different levels, as `z` already did in r15.1. Longer names cost output bytes.
- **R9. Route A still needs runtime work.** The R14 `contract.py` imports the R14 protocol. R16 needs a new, versioned, pinned adapter that **imports the unchanged `common.py`** for `check_schema`/`schema_errors` and applies them to `W`, not `C`.

**Open questions**
- **Q1.** Is a 26 B/fragment output overhead (A1) acceptable, compared with A0 (about 0 overhead, but type-list unions and host-only positional typing)? Recommendation: A1, unless the provider inventory confirms type-list unions **and** output headroom is shown to be binding.
- **Q2.** The 24-clause profile cannot be admitted by the wire alone. The choices are: a reviewed envelope change (rows-only, measured at 28,880), a guard-policy change, or declaring such sources out of scope. Chunking or narrowing stays forbidden.
- **Q3.** Should the opaque-profile schema (`o ∈ {L,R}`, `a` max 0) be the default dispatch profile, with typed logic as a separately measured opt-in?
- **Q4.** Should the `h`/`t` echo stay (about 150 output B)? Default: keep it, since dropping it weakens binding.
- **Q5.** Should the wire version be named `r16.w1`, and should provenance live only in receipts? Adding it to the expanded record would break byte-identity with r15.1.
- **Q6.** Results needed from the provider inventory: depth-8 nesting, the 73-property/13-object schema size, minimum-only integers, 0..1 object arrays, whether strict-mode enforcement happens at all, and type lists (for A0).
- **Q7.** The prompt needs a reviewed rewrite. §9 is a byte-measurement draft only.

---

## 9. Draft prompt edits (measured for bytes only; not reviewed)

These are applied by `probe.py:PROMPT_EDITS` to `protocol-revised/stage-a.system.txt` (+95 B):

1. `Emit one complete closed r15.1 envelope` → `… r16.w1 envelope`
2. `Every fragment x item is [startSpan,head,headOccurrence,endSpan,tail,tailOccurrence].` → `Every fragment x item is an object {a,h,ho,z,t,to}: a startSpan ID, h head, ho headOccurrence, z endSpan ID, t tail, to tailOccurrence; all six keys required.`
3. `y=null unless k3 and assertion is a deadline;` → `y=[] unless …`
4. `Deadline y has c(clock)` → `A deadline y is a one-item list [{c,z,b}]: c(clock)`
5. `A null deadline is a claim` → `An empty y is a claim`

A reviewed prompt should also state explicitly that `y:[]` is a non-deadline claim and never "unknown".
