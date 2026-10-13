# R15.1 small sizing revalidation

Pinned revised READY `dd2bb510254e198589ed50caa6f9a171194a0971c11ae92bde996006267f1f50` (40 artifact pins; primary protocol evidence reports31 tests). All 37 original protocol pins, 11 original sizing-manifest files and 221 frozen R14 files verify unchanged. Original CANDIDATE SHA256 remains `f9c99a2eb7fe3fbd6f9214aa8d3c38a32eb0d69ccfd09aae37878323a2c767a4`.

The actual compact.py AST diff changes only validate/contract and three version constants. validate prefix/suffix is unchanged around its recursive-to-iterative graph walk; contract deep-copies unit d/b and node a. All other functions/constants/schema/build AST are identical. Prompt changes only the envelope version; settings/bound-policy bytes are identical. Full source-bound schemas and paired wire/expanded objects match after only version/hash translation. No wire-shape change was found, so the19-profile original matrix was not rerun. This is host behavioural revalidation, not model extraction or semantic improvement.

## Exact request and paired bytes

Same outcome-exposed public R14 source: 7208 bytes/108 spans, with all text and row ranges unchanged. Exact revised schema=11776 bytes; full request=36884 plus1024=37908 guarded bytes. Delta from R15.0: request +0, schema +0; residual under40000=2092. New request SHA256 `9d8ff82581f6e7a7541ce2cc208f3eef19eddd6b7f6a126a28abef8d5e4a1ec5`; prior `0c6c4a1e38f6bfacb6ad0fc455777bca9875567e4864d1bf00a65043e4cb3a71`. Hash changes reflect explicit versions/bindings; byte sizes stay equal. source-request.json preserves the entire source-only request. This is exposed-input sizing, not a new performance test.

| Translated authored pair | Compact bytes | Delta from R15.0 | Guarded request bytes | Delta |
| --- | ---: | ---: | ---: | ---: |
| paired-opaque-complete-clause | 638 | +0 | 14634 | +0 |
| paired-typed-complete-clause | 868 | +0 | 14634 | +0 |

Typed minus opaque remains **230 bytes (36.05% more)**. Both share the same complete fictional clause/source; typed grouping is authored interpretation, while opaque representation defers it. Exact imported inverse succeeds and expanded fields/evidence match after only version/hash translation. New inverse unit d/b and node a lists are detached from expanded lists. These are labelled authored controls, not model output, semantic-equivalence proof, compression, accuracy or future-fit claims.

## Controlled behavioural stop

One complete399-node authored chain at Python recursion limit600 rejects with **ValueError graph_depth**, with no partial expansion. Prior RecursionError was reported by the separate hardening evidence and is not re-tested here. The complete chain object is retained in authored-controls.json. No cap relaxation, source narrowing, partial-output repair or extra model call follows this stop.

## Compatibility and limits

The unchanged R14 runtime checker still rejects the actual source-bound revised schema. Unsupported forms remain $schema/prefixItems/anyOf/pattern and Boolean items=false; positional tuple/union/pattern semantics require a new reviewed runtime checker. An alternative object-fragment wire redesign would need new codecs/pins, independent equivalence/negative checks and renewed complete sizing. Neither route has demonstrated provider compatibility, and no runtime adapter/native runner/binding changes occurred.

Only R14 observed7231/8192 completion tokens are known; R15.1 model/output-token use is unmeasured. Guard admission does not establish full-output fit, condition completeness or semantic validity. The remaining conservative$0.094009282 still cannot fit an unchanged$0.20 reserve; no paid release or budget change is authorized.

## Read-only reproduction

```sh
/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12 -I -S -B /Users/home/.codex/worktrees/e8f4/yokel/docs/research/state-rulemaking-benchmark/round15-condition-preservation/sizing/revised/revalidate.py
```

Default mode rechecks exact pins/diff/controls/request without writes. --record creates revised artifacts exclusively and refuses existing files. No credentials, provider calls, signer/executor invocation or prior writes. production_eligible/action_ready=false.
