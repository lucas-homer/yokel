# Round 6 runtime/model proposal — pending primary/pipeline agreement

Propose **OpenRouter `openai/gpt-6.1-sol`** for source-first inventory and the stronger verifier, routed only to the regular `openai` endpoint with `allow_fallbacks:false`, `require_parameters:true`, strict JSON-schema output and no tools/search/OCR. This is a materially stronger class than the prior GPT-4.1 nano arm; target-domain reliability remains to be measured. Official catalog and endpoint metadata were retrieved without credentials on October 7, 2026 and retained in MODEL-CATALOG-PROPOSAL.json. Catalog canonical slug is `openai/gpt-6.1-sol-20260929`; advertised regular-endpoint prices are **$2/M input, $10/M completion**, including reasoning in the completion budget. Proposed reasoning effort low, not pro/fast/flex. Provider/model response drift or unsupported parameters fails closed, without fallback/retry.

The catalog's request ID is the undated ID above. A dated endpoint lookup resolves to the same undated model ID; this does not independently prove the dated slug is a POST-supported immutable snapshot. Do not silently invent that guarantee. Pin catalog/endpoint snapshot and expected canonical slug plus request/response IDs; document that alias-weight immutability remains unverified. Primary may choose a proven snapshot alternative before freeze. No paid test calls or credentials by this child.

## Bounded envelope requiring protocol confirmation

Propose at most eight inventory POSTs, eight stronger-verifier POSTs and 80 Jev POSTs. Entire notices are <=30,000 code points / corpus <=40 pages. No silent context clipping.

- OR request admission: conservatively <=30,000 input tokens from exact serialized body bytes plus 1,024 overhead; no cache discount assumed.
- Inventory completion cap 6,144 tokens per notice, including reasoning; verifier completion cap 4,096.
- Jev request admission <=20,000 conservative input tokens per POST, $0.042/M input, output free.
- Worst admitted OR reservation: `16*30000*0.000002 + 8*6144*0.000010 + 8*4096*0.000010 = $1.7792`.
- Maximum Jev reservation: `80*20000*0.000000042 = $0.0672`.
- **Total maximum nominal reservation $1.8464 < provisional $2 cap.** Charge per operation max(reserve, observed cost), not aggregate max. OR provider-reported usage.cost is separately retained from token/rate estimate. Missing reported cost/usage, truncation, schema failure or received overrun stops; never rePOSTs.

This is an admission envelope, not an invoice promise or expected spend. Large schema/record/full-source payloads may be held in review if they exceed a request bound. Service/size failures remain scheduled outcomes; never silently omit or shrink records. Output/schema capacity must be tested on synthetic multi-phase notices before freeze.

## Shared representation and different answer transports

A owns inventory/schema/record, exact quotation resolution, assembly, common verification payload and shared semantic criteria. Source inventory request is constructed before any record/candidate and contains only original source plus fixed instructions/schema. Inventory model returns exact quotes; A deterministically resolves unique matches or explicit unambiguous occurrence/context to original offsets. No LLM Unicode offset counting, fuzzy matching or whitespace repair.

Both verifier arms receive the **same canonical full-source + frozen inventory + normalized record payload**, pinned by payload SHA. Neither receives the other arm's output. Jev uses narrow direct Choice questions over named items/common dimensions, not generative missing-item JSON. Stronger verifier uses corresponding categorical dimensions and may additionally return source-backed omission/contradiction explanations. Jev's unobservable omission descriptions must be recorded as unavailable, not an asserted empty missing-item list. No claim of identical output expressiveness.

Proposed common dimensions: item support, item phase/route association, material requirement preservation, notice identity resolution and full-source completeness/omissions. Unknown/uncertain in any required dimension forces complete-record review; structured source unresolved states cannot be erased by favorable scores. Exact literal/calendar/span/schema guards remain code. No confidence cutoff imported from a cookbook. Complete-record acceptance requires a preregistered categorical conjunction and all scheduled source coverage; record absence alone is never a source-absence finding.

Jev docs warn about full irrelevant state and indirection. Start with direct named item questions on the common payload; candidate-specific support is separate from source coverage. If A/D agree to block coverage, deterministic blocks must cover **all** original source without gaps and preserve/explicitly review cross-block relations. Such a change requires an explicit common-evidence contract; no lossless filtering assumption or unilateral runtime schema. Otherwise the full-source limitation is measured honestly in this comparison. Runtime question/call caps fail closed.

Same extractor/verifier family means correlated errors/self-review. Calls are blind to other verdicts, not statistically independent. Image-only truth remains primary/reviewer responsibility. Frozen normalized records must be saved before either verifier call, and remain identical for both arms.

## Early callable dependency

Runtime will adapt A's make_source / inventory_request / assemble / verification_request / validate_verdict interfaces, not fork the schema. A must expose shared Choice question meanings and categorical acceptance labels, separate stronger optional explanatory schema, and deterministic quote-to-span resolution. Current draft verdict schema requires generative evidence/missing-items and cannot serve as Jev's raw response contract. This needs alignment before READY.

Reuse the reviewed durable fsynced ledger: exact requests/responses/usage/cost/latency, immutable identities with stage/payload/code/source hashes, no POST retries, request/response/model bounds, fail-closed uncertain resume, concurrent-run lock, source/implementation/label-freeze authorization binding. Only existing two 1Password refs in prior wrappers will be used by primary; no key contents accessed here.

Sources: [OpenRouter catalog](https://openrouter.ai/api/v1/models), [selected endpoints](https://openrouter.ai/api/v1/models/openai/gpt-6.1-sol/endpoints), [structured output](https://openrouter.ai/docs/guides/features/structured-outputs), [provider routing](https://openrouter.ai/docs/guides/routing/provider-selection), [reasoning](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens), [Jev models/pricing](https://docs.typesafe.ai/models), [Jev jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13).
