# Round 6 runtime handoff

Runtime implementation ready for final independent review, source collection and freezes by primary. This child has made **zero provider POSTs**, resolved no credentials, read no source labels and collected no fresh sources. Development inputs are synthetic and the explicitly authorized old round5 full Kentucky notice. All outputs remain research only; `action_ready` and `production_eligible` are always false.

## Final approved schedule

Eight notices, at most forty actual PDF pages. Native text only; no OCR, tools, plugins, external search or repair calls. For each valid admitted source: one OpenRouter source-first inventory, deterministic assembly, then one **five-question batched Jev request** and one independent stronger verification request. Maximum eight inventory + eight Jev + eight stronger calls, twenty-four total. There is no eighty-call schedule. Failure, uncertainty and non-admission stay in the scheduled-document denominator; primary/evaluator must use the source manifest plus retained terminal/stop/plan evidence, including documents interrupted by a global stop.

Both OpenRouter stages request `openai/gpt-6.1-sol`, low reasoning, regular OpenAI provider only, no fallback, strict JSON schema, max-price $2/M input and $10/M completion. Inventory completion cap 6,144; stronger 4,096. Conservative input cap 35,000 per request. Jev pinned `jev-1.13.0`, $0.042/M input, output free; conservative total cap 64,000 and state plus longest question cap 32,000. Estimates use full canonical wire UTF-8 bytes plus 1,024 allowance; these are conservative software bounds, not measured token usage. No silent clipping or question dropping.

Maximum nominal reservation: `16*35000*.000002 + 8*6144*.000010 + 8*4096*.000010 + 8*64000*.000000042 = $1.960704`, under $2. Reservation is checked before each durable POST intent, and reported cost can increase the budget charge. Unexpected cost can halt after the observed call; this is a nominal reservation bound, not an invoice guarantee. Usage missing/invalid, incomplete batches, incomplete completions and provider errors stop without retry. Costs remain response-reported or usage-rate estimates, never invoice verified.

`MODEL-INTERFACE-PROPOSAL.md` and `SIZE-REVISION-PROPOSAL.md` retain historical proposals; this approved schedule and implementation receipt supersede their earlier caps. `MODEL-CATALOG-PROPOSAL.json` retains the public catalog evidence. Catalog alias resolves to canonical slug `openai/gpt-6.1-sol-20260929`; this does **not** verify immutable weights or dated POST support. Raw returned model is retained and restricted to the known alias/canonical IDs. Provider identity is verified only when the optional raw provider field is present and equals OpenAI; routing itself is explicitly constrained. Same-family extraction/self-review creates correlated errors; separate calls do not imply statistical independence.

## Paired interface and gate

Inventory receives full source and schema, without candidates or prior judgments. Exact quote selectors resolve to deterministic codepoint offsets in the assembler; unresolved ambiguous/repeated evidence fails closed. All runtime-loaded schemas including `record.schema.json`, code, model IDs, criteria and caps are implementation-pinned. A duplicate schema is relocated unchanged from the user wrapper to `response_format`, preserving source/record data.

The frozen common payload includes the full source once and the complete normalized record. Jev state equals the stronger request's inner payload exactly. Both requests are persisted before either verdict exists; neither verdict enters the other request. Jev supplies categorical support, association, requirements, source identity and completeness judgments. Each criterion explicitly shares pipeline 1.0.2 and EVALUATION-CONTRACT participation scope: instruction modality/applicability, separately typed public-posting/publication/confidentiality disclosures and ancillary accessibility/copies/query contacts with actual roles; substantive program obligations and irrelevant metadata are excluded. Stronger supplies those dimensions derived from strict structured assessments and can additionally explain omissions; Jev has no generative omission-list capability, and an absent list is never represented as an empty successful list. Ties abstain; no confidence threshold or score arithmetic is used. Favorable judgments require structurally valid output, all five pass dimensions and no deterministic review reason. Exact source correctness and completeness still require the independent image-only audit; fixture/model acceptance is no accuracy result.

## Durable execution

`implementation.json` is the code-only receipt. Primary supplies the `round4.sources.v1` native manifest (strict nine source fields), confined raw PDF/text files, and exact six-key authorization:

```
schema_version: round6.live-authorization.v1
implementation_sha256: SHA256 of implementation.json
manifest_sha256: SHA256 of source manifest
source_labels_frozen_before_outputs: true
source_labels_freeze_sha256: primary's external Freeze B SHA256
nominal_budget_usd: 2.0
```

Primary alone executes `run_with_1password.sh --freeze <implementation.json> --manifest <sources.json> --source-root <source root> --output <new durable run dir> --authorization <authorization.json> --source-labels-freeze-sha256 <Freeze B SHA> --live --max-new 1 --budget 2`. The wrapper resolves the two already-authorized 1Password references only inside `op run`; it has not been executed by this child. Restart the same arguments at operation boundaries until complete; raise `--max-new` only within the twenty-four bound. The runner checks code/source/auth pins and locks the run directory before calls.

Requests, identity metadata and intent are fsynced before POST. The intent binds its source/record identity, request hash, implementation pin hash, pages and exact recomputed reservation through immutable identity metadata and folder digest. Changed reservation, identity, request, pins, response or parsed result stops. Received-but-unparsed responses can reparse locally; missing response after intent, transport timeout, provider HTTP error, invalid usage, credential echo or budget overrun latch a stop. No automatic POST retry or resubmission exists. Primary must reconcile a stopped run outside this runner.

## Validation

`offline_checks.py`: 23/23 owner controls passed under bundled Python 3.12.14 with mocked transports and temporary synthetic PDFs. Covers source-first inputs, blind exact pairing, staged resume without re-POST, schema pin drift, no clipping, complete-record positive gate, each common negative dimension, coverage uncertainty, cited omissions, incomplete batch, probability ties, model/provider/usage failures, eight batched-call ceiling, budget-before-POST, credential echo and durable intent/request/reservation integrity. Independent D `test_runtime_review.py`: 8/8 pass after the two ledger fixes; retained reproduction log is `independent-runtime-repro.log`.

`KY-FINAL-SIZE-PROOF.json`: full eight-page, 19,183-byte old Kentucky source with sixteen record facts and a 25,901-byte common payload. Actual final wire estimates: inventory 32,616, stronger 34,512 (both failed old 30,000 cap and pass approved 35,000); Jev total 34,379, state plus longest question 28,683. Five questions remain in one batch. This proves admission, not successful real-model extraction or correctness. The original failed-cap proposal is preserved.
