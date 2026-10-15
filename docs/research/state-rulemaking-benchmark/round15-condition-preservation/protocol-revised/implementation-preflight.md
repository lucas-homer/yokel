# R15 implementation preflight — preparation only

Status: preparation complete; await primary’s approved Opus design before implementing a contract, copying executable helpers, changing schemas/prompts or generating new model requests. Ownership is round15-condition-preservation/protocol/ only in /Users/home/.codex/worktrees/e8f4/yokel. All R14/prior artifacts remain immutable. This document supplies implementation seams and test planning, not an approved design.

## Verified baseline and failure evidence

Inspected frozen R14 protocol-revised compact.py, actual schema.json and stage-a.system.txt, plus public-derived source/evidence and the five identified raw/expanded qualifications. Verified all26 revised artifact hashes against its READY. WSR26-19-023 and its output are now outcome-exposed regression evidence, never unseen evaluation or facts to insert into an operational prompt.

| Unit | Raw c length | Exact defective ending or fragment | Source qualification implicated |
|---|---:|---|---|
|88|180|`this is an age attainment date,`|Age cutoff anchored to the school year of enrollment; date-function explanation ends incompletely.|
|95|180|`or head スタ`|No-fee exceptions include early-childhood/head-start eligibility and disability/FAPE conditions. Non-source characters occur in c; complete exceptions also have source evidence and other assertions.|
|96|180|`or assistance program or head start program, or`|Fee authorization is qualified by both no-fee exceptions; this c stops before completing its alternatives.|
|98|180|`in accordance with the federal individuals with disabilities education `|Disability/FAPE qualification includes the federal act and chapter28A.155 RCW.|
|99|179|`school district accounting manual requirem`|Separate accounting applies to tuition/fees in state-funded classrooms, in accordance with manual requirements.|

Each raw c equals expanded applicability exactly. Source evidence spans are70,80/82/84,80/82/84,80/84,86 respectively. This confirms the defects exist before host expansion; it does not prove a decoding/cap mechanism or that five whole source functions are absent. Some qualification content survives in assertions/other units. Fable’s force/actor/markup disagreements remain disputed judgments; no legal conclusions or relabeling occur here.

## Current APIs and assumptions

compact.py is standalone Python/std-lib, with ROOT-relative prompt/settings and no provider/executor. VERSION=r14.2; span v=r14.spans.2; expanded version=round14.expanded-inventory.v2. Named envelope fields v,h,t,u,z and all ten unit fields i,k,s,m,c,d,b,e,q,r are required and closed.

- span_table(source), validate_table(source,table), reconstruct(source,table): full immutable Unicode source, exact Python splitlines(keepends=True) partitions including supported control/Unicode separators, codepoint offsets/end-exclusive, exact UTF-8 hash and deterministic canonical table hash. Repeated spans retain distinct IDs; broad evidence is not entailment.
- schema(source,table): source/hash/span-ID-bound closed JSON schema. Unit kind/modality/uncertainty enums, integer IDs1..160, output units1..160 in schema; exactly160 is a validator capacity sentinel. s<=280, c/r<=180; d/b<=16 and e1..6. These are structural caps, not guaranteed complete-expression bounds.
- strict_load(raw): duplicate keys, invalid/trailing JSON, nonfinite values/overflow reject. canonical(value), digest(value), source_hash(source) supply exact stable bytes/hashes; no normalization or guessed defaults.
- validate(value,source,table,finish_reason='stop'): only complete stop/END/bound output; strict field/type/text/list/code checks; unique/resolvable IDs; d closure/acyclicity; separate b members and k7 requirements; k5 first d is endpoint k4. q0 iff r empty; m5 requires nonzero q. It cannot prove qualification completeness, applicability, correct force or entailment.
- expand(value,source,table,finish_reason='stop'): validates, maps codes/fields and mechanically resolves exact quote/start/end/occurrence for each evidence ID. c is copied directly to applicability, not completed, clipped or reinterpreted. Every result retains completeness=unverified, production_eligible=false and action_ready=false.
- contract(expanded,source,table): closed expanded shape, list guards for units/evidence, enum-to-code conversion, exact reconstructed-field/evidence equality and canonical equality. It rejects modified evidence; currently it relies on the fixed expanded string/list layout. A redesigned condition representation requires an explicit new inverse, not patching R14 fields or default filling.
- build(source): reads ROOT prompt/settings; user keys are exactly source_text/source_text_sha256/span_table/span_table_sha256, with full source and table text. Returns body, table, body_bytes, guarded_bytes and request_sha256; entire canonical request plus1024 must be<=40000. Output8192, Sol low/OpenAI-only/no fallback and price caps2/10 remain baseline settings. No candidate/reference/prior output enters the request.
- validate_response(raw_content,finish_reason,source,table): strict-loads the complete raw text, validates and returns compact/expanded. No incomplete-prefix salvage, repair or retry.

## Minimal implementation seams after approved design

1. Add a versioned source-linked condition/qualification representation in R15 only, exactly as approved. The design must settle reusable condition identity, evidence ownership, unit-to-condition links, alternatives/conjunction/exception polarity, applicability scope/anchors, and explicit absent/ambiguous/not-applicable states. Avoid interpreting contextual d edges as normative prerequisites. No representation selected in this preparation phase.
2. Update UNIT_KEYS/envelope keys, schema, validator closure/reference rules and any condition graph checks together. New references must resolve without truncation, dangling links, contradictory state or scope loss. Reuse should preserve shared conditions without repeated capped prose; it must not flatten alternatives/exceptions or silently change which unit they qualify. Increasing string caps alone is not the requested solution.
3. Update expand/contract mechanically and version both compact/expanded contracts. Preserve exact condition evidence, original field/state/link meaning, order and canonical inverse; separately state what is derived and what remains unverified. Required fields need explicit states, not host-invented completion or defaults.
4. Revise generic source-only prompt and source-bound request builder; keep outcome-exposed regression artifacts outside operational messages. Preserve full source/background/unresolved functions, whole-input guard and8192 cap. New scope/evidence/condition fields must be included in full request/output sizing.
5. Adapt frozen fictional controls/tests offline. New fixtures should be generic and disjoint from prompt illustrations for any future model test. R14’s five public failures may anchor labeled regression/representation controls, never accuracy denominators or unseen-source claims. Long qualification preservation must be exercised across full supported source conditions and inverse equality, not asserted by keywords or fragment length.

Exact approved shape, output/condition capacity policy and semantic acceptance rubric remain primary/Opus decisions. No R15 contract code or schema is implemented yet. Runtime bindings/signer/executor integration remains primary-owned outside protocol/.

## Suggested validation after implementation approval

From this worktree’s future R15 protocol directory, use Python -B throughout to avoid caches. Preserve/adapt baseline structural tests before adding condition-specific tests:

```sh
python3 -B -m unittest -v test_compact test_semantic_contract test_revision
python3 -B -m unittest discover -v -p 'test_*.py'
python3 -B offline_checks.py
```

These are suggested commands, not claims that those files already exist in R15 or were run in this prep phase. No installs/builds/databases required. Baseline R14 source/evidence integrity tests must still pass under an explicitly versioned R15 fixture, rather than rewriting old fixtures in place.

Meaningful new tests should cover complete long conditions without repeated clipped text; one reusable condition shared by multiple units with distinct scopes; all/any/except/nested alternatives as approved; missing/duplicate/wrong-type/unknown references and prohibited cycles if designed; uncertain/not-stated/not-applicable distinctions; exact Unicode/separator/repeated-span evidence; altered condition evidence/state/link/order rejected by inverse; all cap/sentinel/guard boundaries and incomplete finish/JSON rejection. Include structurally valid semantic negatives for lost exception/polarity/scope and illustration leakage, making clear independent assessment rejects meaning defects while the host may accept their shape. Sizing must count full serialized conditions and links, report assumptions and failed headroom honestly; no line count or keyword heuristic proves completeness or fit.

## Execution and Claude boundaries

Read /Users/home/.codex/skills/claude-delegate/SKILL.md. No bridge inference/auth probe/provider call performed in this preparation task, and no model/effort/auth result claimed. Primary owns pending approved Opus design. Any subsequently authorized Claude advisory call must use the subscription bridge and skill’s isolated wrapper, a fresh neutral tmp directory, verified Claude.ai Max auth without reading credentials, explicit requested model/effort and actual successful result provenance. Never OpenRouter Fable or Anthropic API fallback. Supplied documents are data, not executable instructions. Claude advisory cannot itself inspect/edit files/run tests through the isolated tool-less wrapper; GPT/Codex owns authorized implementation and verification.

No paid experiments are authorized; the unchanged$2 ceiling has only$0.094009282 headroom. No credentials, installs, commits, pushes, production changes, new chats or subagents. Approval/review of a proposed contract does not by itself authorize dispatch. Preparation establishes API seams and observed transport fidelity, not semantic completeness or unseen performance.

## Read-only provenance pins

Paths are relative to ../round14-semantic-contract from the round15 directory. All verified at preparation; recorded to support later regression provenance without changing old artifacts.

- `protocol-revised/READY.json`: `478d8cb4aaaeea97dd3a33b751c373847fe457a1e789212999b11c7224280500`
- `protocol-revised/compact.py`: `faaf16b6a1ff816e8342b9afefbdb0734e7ee8a7686f98f24205d78b43ea533f`
- `protocol-revised/stage-a.system.txt`: `da2b282f15a14778b6e83598d53cb4dff767e61ed0b0140cc6cd950359b8409d`
- `protocol-revised/schema.json`: `646167a574de34d157f1bf21174f4d0ff85dddc0a2edb47df03f7144dceca57d`
- `protocol-revised/request-settings.json`: `43d3b4f7886d84c528a07ff3ba0901a2be1ff42a6b503853ee87e1e6985b1ac2`
- `execution/run/content.body`: `ea2657b5fe87849d753bade38178043e4ff1ae24d7a2be6abd77d01c70d76b95`
- `execution/run/expanded.json`: `82dfa339edfe923349abd0d622baccbd64ed448bb12a765ee789f6b7d3ab3886`
- `source/parsed-body.txt`: `5b8b221224c799e4950dbddf6df8bbf0652ee90db7150f1ed16a332b137df55f`
