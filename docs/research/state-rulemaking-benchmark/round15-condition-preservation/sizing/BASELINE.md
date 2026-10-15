# R15 sizing baseline: frozen R14.2 observations

Measured from the unchanged R14.2 request and completed provider receipts. BASELINE.json contains exact pins, additive byte accounting, cap distributions, repeated-qualification groups and integration constraints. This is an offline observed baseline, not an R15 candidate or an improvement claim. All 221 files in the primary R14-FREEZE manifest verify before and after measurement. No provider calls, credentials, signing, runner invocation, installs or prior writes.

## Exact observed output and usage

| Measurement | Observed value |
| --- | ---: |
| Units | 110 |
| Original provider content UTF-8 bytes | 22694 |
| Canonical compact bytes | 22686 |
| Original minus canonical bytes | 8 |
| Native response-envelope bytes | 29722 |
| Expanded inventory bytes | 82741 |
| Provider-reported prompt tokens | 6730 |
| Provider-reported completion tokens | 7231 |
| Output cap | 8192 |
| Completion fraction of cap | 88.2690% |
| Observed completion residual | 961 tokens |
| Reported reasoning tokens | 57 |
| Finish reason | stop |

Original content is preserved separately from canonical JSON; both hash back to the immutable native/validated receipts. The exact source build matches the recorded request, and imported validate_response/expand/contract reproduce every expanded field/evidence and compact canonical bytes. Those checks establish provenance/structural roundtrip only. They do not establish complete or faithful conditions, semantic accuracy or future fit.

Completion minus reported reasoning is 7174; this is arithmetic, not a separately tokenized visible-content measurement. The raw-content/completion ratio is 3.138432 bytes/token and the canonical-content ratio is 3.137325. Both are retrospective ratios for this one request, not a matched tokenizer or a transferable conversion. No model call or authored replacement output was produced here.

## Qualifications and capped fields

| Field | Character cap | Observed max chars | P95 chars | Sum UTF-8 value bytes | Sum key/colon/JSON-value bytes | Empty units | Units at cap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `s` | 280 | 230 | 154 | 8642 | 9302 | 0 | 0 |
| `c` | 180 | 180 | 159 | 4180 | 4840 | 57 | 4 |
| `r` | 180 | 93 | 71 | 914 | 1574 | 95 | 0 |

`c` has 53 nonempty occurrences and 40 distinct nonempty strings. 8 exact repeated-string groups cover 21 occurrences. Repetition beyond the first occurrence totals **892 literal UTF-8 bytes**. Group hashes and unit IDs in BASELINE.json make this count traceable without inventing a condition classification. These duplicated bytes are not achievable savings, semantically redundant conditions or permission to delete attachments: dictionary/reference/scope encoding overhead and semantic preservation require separate candidate evaluation.

Caps are Unicode character counts, not UTF-8 bytes or tokens. JSON-value bytes include quotes/escaping; key/colon/value contributions add the four bytes for each one-letter key. Unit commas/braces and other fields remain separate. Maximum observed list lengths are d=5/16, b=5/16, e=6/6. The schema permits160 as a capacity sentinel; host validation accepts fewer than160 and IDs1..160. Neither count establishes a safe output fit or authorizes fact omission.

## Actual input and schema overhead

| Component or layer | UTF-8 bytes |
| --- | ---: |
| Full canonical request | 28307 |
| Guard allowance | 1024 |
| Guarded request | 29331 |
| Residual under40000 guard | 10669 |
| Entire immutable source | 7208 |
| Source serialized as JSON string | 7317 |
| Exact span table (108 spans) | 9619 |
| Inner source-only user envelope | 17141 |
| Outer serialized user-content string | 17813 |
| System content | 8268 |
| Source-instantiated schema | 1790 |
| Whole response_format wrapper | 1879 |
| Schema evidence-ID enum | 649 |

Nested layers overlap; this table must not be summed. BASELINE.json separately proves exact additive top-level and inner-envelope accounting. Complete source text appears in source_text and exact span rows; double serialization adds escaping. Nothing was removed to produce a smaller request. An R15 candidate must regenerate the full source-instantiated schema/request/table and remeasure the complete guard.

## Estimates are separate from observations

The following are illustrative divisions of 22686 canonical bytes by assumed bytes/token, with an optional256-token allowance inherited from sizing sensitivity work. They are not measured token counts or guaranteed bounds.

| Assumed bytes/token | Estimated content tokens (ceil) | Plus illustrative256 allowance | Residual under8192 |
| --- | ---: | ---: | ---: |
| 2 | 11343 | 11599 | -3407 |
| 3 | 7562 | 7818 | 374 |
| 4 | 5672 | 5928 | 2264 |

The actual provider reported 7231 completion tokens; the byte estimates can disagree materially. A candidate byte reduction cannot be reported as measured token reduction, semantic improvement, altered model behavior or generalization. Any edited R14 output must remain a separately labelled authored fixture with original output immutable.

## Budget and runtime integration

R14 reserve/conservative charge=$0.20; reported provider cost=$0.0891335; nominal2/10 usage-rate estimate=$0.0857700. Reported-minus-nominal=$0.0033635. Usage reports 6727 cache-write prompt tokens. This difference is not independently verified cache-write premium or an invoice; preserve the reported usage/cost details and all three accounting quantities separately.

Cumulative conservative debit=$1.905990718 against$2, leaving **$0.094009282**. Another unchanged$0.20 reservation does not fit; shortfall=$0.105990718. Do not retroactively substitute lower reported cost for conservative debit or silently reduce reservation. R15 is offline only. A future paid proposal requires explicit primary/user admission and sufficient approved budget; this baseline authorizes none.

The pure imported protocol is r14.2 (r14.spans.2; round14.expanded-inventory.v2). Relevant callable interfaces:

- `canonical(value)`
- `digest(value)`
- `source_hash(source)`
- `span_table(source)`
- `reconstruct(source, table)`
- `schema(source, table)`
- `validate(value, source, table, finish_reason='stop')`
- `expand(value, source, table, finish_reason='stop')`
- `contract(value, source, table)`
- `build(source)`
- `validate_response(raw_content, finish_reason, source, table)`

Build returns body/table/body_bytes/guarded_bytes/request_sha256; validate_response returns compact/expanded. Preserve exact reviewed import pins and direct use of these functions. Unit fields i/k/s/m/c/d/b/e/q/r are closed and required; unknown modality requires uncertainty and q0 iff r empty. Essential conditions remain attached with exact evidence; new dictionary/reference/condition structures need explicit versioned schema/codec/scope validation and review, not inferred defaults or silent condition scopes. The runtime's closed-schema keyword checker must explicitly support any new schema form.

Keep Sol low/8192, OpenAI-only/no fallback and full40000 guard until a separately reviewed scope changes them. A complete stop output and exact inverse are required; truncation/capacity/bound failures stop intact. No clipping, retry, fallback, prefix repair or source/unit dropping. Preserve unchanged native executor/core, primary-only prepare_bindings --scope-id/--expires-unix/--review CLI, yokel.research-job.v1 manifest, isolated six-argument entry point and exact dependency closure<=10000. Neutral charge ledger and separate completion/stop outcomes stay distinct. R15 bindings/IDs/authorizations must be new artifacts rather than edits to R14. No live job or experiment proposal is released here.

## Reproduction

Run with the bundled interpreter, no installation:

```sh
/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12 -I -S -B /Users/home/.codex/worktrees/e8f4/yokel/docs/research/state-rulemaking-benchmark/round15-condition-preservation/sizing/measure_baseline.py
```

Default mode remeasures and compares BASELINE.json/BASELINE.md without writing. --record exclusively creates them and refuses existing baseline files. Exact source/code/receipt pins and the measurement script hash are in BASELINE.json. Future primary-supplied R15 implementations and offline sizing/experiment proposals remain pending; no semantic/structural improvement claim follows from this baseline.
