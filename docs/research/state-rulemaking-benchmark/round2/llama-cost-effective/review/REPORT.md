# Independent diagnostic Cost-effective Markdown review

All 20 returned Markdown files were reviewed against all 34 frozen source-page images and the unchanged 174-field reference. This is bounded evidence preservation, not automated normalization or provider schema-extraction accuracy. Output JSON was not inspected to rescue Markdown evidence.

- Strict participation-evidence gate: **17/19 eligible documents pass**; A01 and A03 fail; A07 is insufficient_reference.
- Determinate critical fields: **139/141 pass** (116 supported, 23 correctly preserved absences); one partial_ambiguous, one incorrect. One uncertain critical field is excluded.
- All determinate fields: **171/173 pass** (148 supported, 23 safe abstentions).
- All 20 captures report operational completion. Operations are a separate result from these content judgments.
- Full-output/source review found **zero critical extra assertions** outside reference fields. Two noncritical proposed-rule-body formatting defects are retained separately; a participation gate pass does not certify all rule text.

## Failures and uncertainty

**A01 — filing_stamp, partial_ambiguous.** Markdown lines104–107 include `FILED` and `<s>MAR 19 2026</s>`. Source page1 has a clean, unstruck filing date. The literal date survives, but HTML `<s>` renders deleted text and changes its evidentiary presentation. The conservative strict gate flags this ambiguity; it does not infer an explicit canceled filing or invented alternate date. Primary adjudication can inspect this isolated judgment without changing the raw artifact.

**A03 — rule_identity, incorrect.** Markdown line25 changes source title “Subpart 1 to S” to “Subpart 1 to 5.” Source body references to new Subpart5 and list1–5 are correct source facts and are not counted as false assertions.

**A07 — original_notice_date, not_assessable.** Source page1 prints October31,2025; page2 prints October31,2026. Both remain in Markdown. The frozen conflict is unresolved, excluded from determinate field denominators, and prevents an unqualified document pass. Faithful reproduction of that source conflict is not a parser error.

## Other observations

B06 line107 falsely strikes “actively” in an added broker-member eligibility clause that is underlined, not struck, in source. B07 line82 leaves some interior words unstruck inside a wholly struck, bracketed proposed repeal subsection. These are recorded in extra-assertions.jsonl as noncritical to the benchmark's participation identity/lifecycle/window dimensions.

B04's selected amendment, hearing and date roles remain intact in this lane. Literal Markdown delimiters inside raw HTML must not automatically be interpreted as deleted dates; this output did not require that inference. Absence judgments cover complete retained target notices/forms, not hypothetical missing publication pages or unrelated neighboring notices. Relative durations, receipt requirements, conditions and publication/effective/filing roles are retained without calculating new dates or supplying timezones.

## Reproducibility

judgments.json contains manual decisions and line ranges. score.py performs bookkeeping only; field-scores.jsonl stores exact text/character locators, source-input/image hashes, frozen-reference hash and explicit absence scope. document-scores.jsonl and operation-records.jsonl retain the same core schema as prior reviews, with arm llama_cost_effective. Paths in these round2 files are relative to the benchmark directory declared in artifact_path_base.

validation.json/checks.json report **1,067 passed checks**, including 174 exact nonempty quotes, all20 output hashes/capture statuses/input identities, all34 page-image hashes, all141 frozen files and all629 original baseline files unchanged. No execution files, runner, source/reference artifacts, baseline scores, Docling artifacts or other child directories were modified.

The sample is diagnostic, nonrandom and template-heavy. latest is not a verified released-version identity. Do not use this review to establish national error rates, end-to-end normalization accuracy, production readiness, discovery recall or equivalence between tiers/interfaces.
