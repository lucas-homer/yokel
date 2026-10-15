# R15 offline candidate sizing

Exact frozen protocol r15.0 READY `5979447bc7b0c267da45116258862f4b30e0d633ce352cfea5149887851104e0`. 19 authored dimensional profiles, never model outputs, source gold or a deterministic migration of R14 c text. CANDIDATE.json records full pins/component sizes, source/schema/request hashes, admission results and byte sensitivities; authored-profiles.json preserves complete labelled fixtures. All 221 prior R14 freeze hashes verify unchanged.

## Focused measurements

| Authored profile | Units/nodes/links | DAG depth | Graph bytes | Unbounded repeated-text fixture bytes | Full guarded request bytes | Graph / input admission |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| shared160-u24 | 24/1/24 | 1 | 4142 | 6584 | 13694 | pass / pass |
| disjoint160-u24 | 24/24/24 | 1 | 6471 | 6599 | 23178 | pass / pass |
| shared600-u1 | 1/1/1 | 1 | 440 | 899 | 14574 | pass / pass |
| shared600-u24-shortanchors | 24/1/24 | 1 | 4142 | 17144 | 14574 | pass / pass |
| shared600-u24-longanchors | 24/1/24 | 1 | 4214 | 17144 | 14574 | pass / pass |
| shared600-u110 | 110/1/110 | 1 | 18107 | 77968 | 14574 | pass / pass |
| shared600-u159 | 159/1/159 | 1 | 26192 | 112709 | 14574 | pass / pass |
| disjoint600-u8 | 8/8/8 | 1 | 2239 | 5834 | 23568 | pass / pass |
| disjoint600-u24 | 24/24/24 | 1 | 6471 | 17159 | 44323 | pass / overflow |
| leaf-fragments8 | 1/1/1 | 1 | 762 | 5113 | 23568 | pass / pass |
| leaf-fragments9 | 1/1/1 | 1 | 808 | 5715 | 24853 | array_bound / pass |
| deadline-shared600-u8 | 8/1/8 | 1 | 3105 | 5874 | 14771 | pass / pass |
| depth12 | 1/12/1 | 12 | 1095 | 899 | 14574 | pass / pass |
| depth13 | 1/13/1 | 13 | 1156 | 899 | 14574 | graph_depth / pass |
| nodes399-links399 | 1/399/399 | 1 | 81143 | 899 | 14574 | pass / pass |
| nodes400-links399 | 1/400/399 | 2 | 81206 | 899 | 14574 | capacity_review_g / pass |
| nodes399-links400 | 1/399/400 | 1 | 81191 | 899 | 14574 | capacity_review_l / pass |
| paired-opaque-complete-clause | 1/1/1 | 1 | 638 | 895 | 14634 | pass / pass |
| paired-typed-complete-clause | 1/5/1 | 3 | 868 | 895 | 14634 | pass / pass |

Shared versus disjoint cases use complete160/600-character fictional clauses. Each within-profile comparator attaches the same clause text to the same units. Graph encoding stores source-backed fragments and typed links; the prose comparator repeats the authored complete clause.600-character (and multi-fragment) prose deliberately violates old c180. Its serialization cannot be called valid R14 output, model compression or a tested migration. Version/envelope/p/state/reference overhead differs and is included; exact graph-minus-fixture bytes are merely serialization deltas. Unary-depth and high-count duplicate-leaf profiles stress structure; they do not assert source logical entailment or meaningful condition counts. Deadline y overhead is measured as its JSON value minus null, rather than asserted to be semantically equivalent to a qualification-only prose fixture.

Every admitted graph passes the exact imported validator and byte/hash inverse; intended fragment/depth/node/link boundary controls reject complete objects. All bytes of failed profiles remain labelled fixtures; none are repaired or clipped. Request build overflow is separately recorded. The full accounted body equals the pinned builder on every admitted request; independently counting a rejected body's bytes does not admit or bypass the guard.

## Overheads and limits

CANDIDATE.json separates unit/node/link arrays, fragment tuples, literal anchor bytes, resolved source evidence bytes (including reuse occurrences), deadline dimensions, whole schema/response wrapper and entire guarded request.12-versus48-character anchors measure literal-copy cost. Fragment counts, DAG depth and399/400 sentinels are engineering limits, not full-output fit guarantees. Qualifiers/units/source are never dropped to make a profile pass.

The observed R14 output was110 units/22686 canonical bytes and7231 completion tokens at8192 cap, with4180 c bytes and only892 exact duplicated qualification bytes beyond first occurrences. Those are frozen observations. R15 profiles have **no observed provider tokens**.2/3/4-byte sensitivities plus an illustrative256-token allowance are assumptions, not a matched tokenizer, reasoning measurement or assurance of fit. Authored size deltas establish no semantic/structural improvement, source completeness, model behavior or generalization. Independent assessment must still reject scope leaks, missing final exceptions, wrong roles/connectives, ambiguous references made certain and omitted applicability links.

## Full-schema public R14 input control

The same outcome-exposed7208-byte public R14 source is measured for input overhead only, with no R14 output converted and no model extraction. The exact candidate schema is 11776 bytes; full request 36884 +1024=37908 guarded bytes, versus29331 in R14 (delta +8577). Build admission: True; stop: None. This exposed source is not an unseen pilot. Its candidate request hash is `0c6c4a1e38f6bfacb6ad0fc455777bca9875567e4864d1bf00a65043e4cb3a71`.

## Runtime and provider compatibility

The old R14 closed-schema checker accepts 0/19 candidate profile schemas. Actual unsupported keywords: $schema, anyOf, pattern, prefixItems. Boolean item schemas required: True; maximum observed schema-node depth 8 (old checker limit16).

The old checker only recurses into one homogeneous items dictionary and property schemas; schema_errors cannot enforce tuple positions, union alternatives or node-ID patterns. A NEW reviewed runtime validator must implement the actual schema's positional prefixItems, closed Boolean items and required union/pattern/depth behavior and reject unsupported keywords, or the protocol owner must choose an equally strict reviewed compatible schema/wire. Do not suppress keyword rejection, pretend positional constraints are homogeneous, bypass checker or edit the frozen R14/native runner. Exact source-bound codec/import/request/pins and primary late bindings must belong to distinct R15 artifacts. This child implemented no runtime adapter or release bindings.

**Provider structured-schema/tuple compatibility remains unverified.** Host validation and local schema rejection cannot establish provider acceptance; no provider/API/credential probe occurred.

## Experiment admission

Offline only. Remaining conservative budget$0.094009282 cannot fit the unchanged$0.20 reserve; no paid proposal is admitted. Do not reduce historical charges/reserve or change budget here. Future primary/user authorization and sufficient approved budget would need an exact reviewed source/request/schema, provider compatibility assessment, independent semantic rubric and intact stop conditions. No retries, clipping, source narrowing, fact dropping or fallback. Current allowed work is independent offline review of representation and negative controls; these profiles cannot substitute for new source-only model evidence.

## Reproduction

```sh
/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12 -I -S -B /Users/home/.codex/worktrees/e8f4/yokel/docs/research/state-rulemaking-benchmark/round15-condition-preservation/sizing/measure_candidate.py
```

Default mode verifies the recorded protocol hash, exact inputs and all measurements without writes. --record --protocol-ready-sha256 requires the actual frozen candidate hash and exclusively creates CANDIDATE.json/CANDIDATE.md/authored-profiles.json; existing artifacts refuse overwrite. No installs, provider calls, credentials, signer/executor invocation, prior edits or runtime binding changes. production_eligible/action_ready=false.
