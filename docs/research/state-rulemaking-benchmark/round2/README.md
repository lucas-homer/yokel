# Cheaper PDF parsing comparison — round two

Completed October 6, 2026 Pacific. This research compares native text, Docling, LlamaParse Cost-effective, and OpenRouter's `mistral-ocr` engine on 20 existing diagnostic notices and eight fresh notices from different publication/template families. All specialist outputs are retained. Production remains federal-only.

**The results support native extraction first and OpenRouter Mistral OCR as the next cloud candidate to validate. They do not yet validate an automatic escalation policy.** The cheaper cloud paths performed well on our bounded evidence questions. Local Docling sometimes recovered evidence absent from native text, but also introduced losses; it does not belong in every document's path by default.

## Results

A strict pass requires the frozen critical evidence, adequate scope for absence claims, and no critical error within the predefined extra-assertion audit. It is not a guarantee of perfect transcription, correct submission instructions, or complete rule-text semantics.

| Method | Diagnostic strict passes | Fresh strict passes | Diagnostic positive evidence | Fresh positive evidence |
| --- | ---: | ---: | ---: | ---: |
| Native text | 14/19 | 7/7 | 91/118 | 49/49 |
| Docling 2.134.0 + Apple Vision OCR | 15/19 | 5/7 | 109/118 | 47/49 |
| LlamaParse Cost-effective | 17/19 | 7/7 | 116/118 | 49/49 |
| OpenRouter Mistral OCR annotations | 18/19 | 7/7 | 117/118 | 49/49 |

One source-conflicted notice in each cohort is excluded from the strict eligible denominator: A07 has inconsistent original-notice years; H06 has calendar-day versus working-day wording. All remain in the scheduled denominators of 20 and eight. The fresh set contains 74 reference questions, including 65 critical questions: 49 determinate positive/explicit-negative, 15 not-stated, and one uncertain.

For context, the earlier Agentic run passed 18/19 diagnostic notices, Plus 16/19, and Firecrawl PDF parsing 10/19. These are historical comparisons with interface/version differences. Agentic and Plus were not run on the fresh eight. Equal strict counts do not imply identical errors, universal equivalence, or proven noninferiority.

[Integrated metrics](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round2/integrated/all-metrics.json) and [verification](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round2/integrated/all-verification.json) provide denominators and recomputed gates. The diagnostic cohort has informed our choices; the fresh cohort was independently source-reviewed and frozen before specialist execution. No settings were tuned against fresh outputs.

## What changed our assessment

- **OpenRouter preserved difficult form selections at low reported cost.** Its diagnostic failure was A03's omitted filing-stamp date. It preserved A03's literal title `S`, which both earlier Llama tiers and the new Cost-effective tier changed to `5`. None of these representations should silently replace the original.
- **Cost-effective was close to the more expensive historical Agentic result.** Its diagnostic failures were A03's title and A01's filing stamp: the date survives, but is wrapped in unsupported HTML `<s>` markup. The source date is not struck out. This is different from ambiguous Markdown markers embedded in raw HTML.
- **Docling is complementary, not a universally safe intermediate step.** It recovered enough evidence to pass the two Washington/North Carolina cases A04 and B04 that native text failed. However, the three Mississippi scans still failed, and B08 lost the end of a termination reason. On fresh H03 it displaced a prior hearing date from its heading; on H08 it rendered a hearing range as `July 2223`.
- **A high benchmark score can coexist with a consequential untested error.** Cost-effective changed H01's comment-submission email from `DNRAdministrativeRulesComments@wisconsin.gov` to `DNRAministrativeRulesComments@wisconsin.gov`. The frozen extra-audit scope enumerated temporal, selection, and lifecycle evidence, not submission destinations. Independent adjudication therefore retained this as an important supplemental error and restored H01's frozen gate pass. The initial failure judgment and correction remain recorded. This error blocks unverified use of that address regardless of the benchmark score; no email was sent or delivery tested.
- **Rule-body fidelity is a separate requirement.** OpenRouter changed a B05 exam-category phrase, and multiple arms lost or altered amendment markup. These were outside the participation-evidence gate. The study cannot certify accurate reproduction of complete proposed rules.

See [Docling diagnostic review](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round2/docling/review/metrics.json), [Cost-effective findings](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round2/llama-cost-effective/review/findings.json), [OpenRouter findings](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round2/openrouter/review/findings.json), and the [email-scope adjudication](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round2/protocol/heldout-execution-audit/scoring-scope-adjudication.json). Passing a frozen benchmark and being ready for deployment are separate decisions.

## Cost and operations

| Cloud path, 28 notices / 56 input pages | Retained usage |
| --- | ---: |
| LlamaParse Cost-effective | 168 credits: 102 diagnostic + 66 fresh |
| OpenRouter, OCR plus minimal chat completion | $0.115847566 reported usage |

At the documented conversion of $1.25 per 1,000 Llama credits, 168 credits have a **$0.21 list-price equivalent**. This is not a cash invoice. OpenRouter's total already includes $0.003847566 in reported upstream inference cost; do not add it again. The remaining $0.112 is consistent with $2 per 1,000 pages for this engine access path. Its OCR release is undisclosed, so this is not a measurement of the separately advertised direct Mistral OCR 4.1 service. [LlamaParse pricing](https://developers.llamaindex.ai/llamaparse/general/pricing/).

One diagnostic OpenRouter request was explicitly rejected as rate-limited, with no generation ID or parsed annotation. The original response is retained. One documented recovery succeeded; later starts were paced at least 22 seconds apart. There were 29 OpenRouter attempts for 28 retained successful parses. The rejected attempt's billing remains unknown; account-key usage was lagging and did not reconcile it. No uncertain timeout was blindly resubmitted, and no held-out retries occurred.

Docling ran locally on the Mini using CPU layout/table models and Apple Vision OCR, with package, options, and model-cache hashes retained. There was no hosted parsing fee, but hardware, installation, maintenance and review are not free. Native diagnostic outputs were reused byte-for-byte and have no new extraction timing. Fresh native outputs used bundled Poppler `pdftotext` 26.05.0 with `-layout -enc UTF-8`. Local timings, provider processing times, pacing and whole-wrapper times are distinct; this is not a throughput benchmark.

All 56 cloud jobs and 28 Docling conversions completed. The eight fresh native conversions also completed. The [independent completion audit](protocol/heldout-execution-audit/COMPLETION-AUDIT.md) verifies input hashes, page evidence, exact output retention, serialization and usage. Page counts alone do not establish content completeness. Some original Docling confidence metadata contains NaN; those captures are preserved and those confidence values are not used as quality scores.

## Configuration repair

`mistral-ocr` is an OpenRouter PDF `file-parser` engine, not the model that should drive Codex. The user's model and provider lines had landed inside the Langfuse MCP table; they were removed there. The raw API key had been placed in `env_key`, which expects an environment-variable name. The key is now in the Private 1Password vault as **OpenRouter API Key**, and the configured OpenRouter provider uses command-backed 1Password authentication. Existing Codex model selection remains `gpt-6.1-sol`.

The comparison calls OpenRouter directly with `plugins: [{id: "file-parser", pdf: {engine: "mistral-ocr"}}]`. A catalog-verified inexpensive vision-capable chat model returns only an acknowledgment. We score the retained file-annotation text, never that generated answer. Images and raw responses are supplementary. No API key is embedded in research code or output artifacts. [OpenRouter PDF API](https://openrouter.ai/docs/guides/overview/multimodal/pdfs), [Codex configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).

## The system I would test next

1. Preserve original bytes, retrieval provenance, publication context and native text. Prefer structured publisher data when available; these PDF results say nothing about state API coverage or HTML discovery.
2. Start with native extraction for validated templates. Route scans, selected forms, graphic stamps, displaced associations, and missing required evidence to a specialist. Abundant readable text alone is not an acceptance signal.
3. Test OpenRouter Mistral OCR as the economical cloud fallback. Keep LlamaParse Agentic available for specific unresolved evidence, without assuming a higher-priced tier will fix it. Do not run every document through every tool in production.
4. Extract typed claims with source locations, temporal roles, conditions, and uncertainty. Compare evidence channels when decisive facts disagree. A faithful source conflict must remain a conflict.
5. Predeclare submission destinations, URLs and relevant amendment semantics in the next quality contract. The H01 email finding demonstrates why date-only success is insufficient for an action product.
6. Evaluate an actual frozen router/normalizer on fresh data, including random audits of cheaply accepted documents. Measure correct automatic acceptance, escaped errors, escalation, reviewer effort, and total cost per usable notice. Those components were **not implemented or measured here**.

Native, Cost-effective and OpenRouter meet the small fresh-set parsing threshold for consideration in a monitored shadow pilot; Docling does not. That is an experimental eligibility result, not blanket approval of outputs. The submission-address defect remains a separate practical reason to require validation before acting on parsed destinations.

## Scope and reproducibility

The diagnostic set has 20 notices from eight states and 34 selected pages. The fresh set adds Wisconsin, Maine, Iowa, Kansas, Oregon, Minnesota, Utah and Alaska: eight distinct source publications/template families and 22 pages. It contains two filled forms, three register notices, two clean standalone notices and one second-hearing lifecycle notice. **There are no image-only fresh scans.** Selection was purposive and its search order was not preregistered. The collector used native text for navigation; the independent reference reviewer inspected all 22 images and matched each to its original PDF page before specialist parsing.

These are agent-adjudicated references, not human gold labels. Parser reviewers were not vendor-blinded. The OpenRouter fresh-output reviewer also collected the sources, while references were independently adjudicated and material decisions were integrated by the primary. No national accuracy, full-register discovery/segmentation recall, legal deadline computation, or automated normalization accuracy is claimed.

The old 141-file freeze and all 629 originally retained files remain unchanged. The new 127-file common freeze covers sources, references and settings; output scoring and correction histories live separately. Integration validates 112 document-arm observations, 992 field rows and exact evidence quotes, recomputing every gate. Entire semantic groups containing uncertainty are excluded from the determinate-group metric. Unscored substantive errors remain explicitly reported.

- [Protocol](protocol/PROTOCOL.md), [independent source review](protocol/heldout-review/REVIEW.md), and [common freeze](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round2/heldout-execution/freeze.json).
- [Docling fresh review](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round2/docling/review-heldout/metrics.json), [Cost-effective fresh review](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round2/llama-cost-effective/review-heldout/findings.json), and [OpenRouter fresh review](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round2/openrouter/review-heldout/findings.json).
- [Prior comparison](../README.md), [task coordination](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round2/coordination.json), and [offline integration script](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round2/aggregate.py).

From this directory, `python3 aggregate.py` revalidates scores and recomputes descriptive metrics without network calls or parsing charges. The original retention check is `python3 ../verify_recovery.py`.
