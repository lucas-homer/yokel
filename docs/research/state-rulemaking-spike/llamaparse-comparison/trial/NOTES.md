# LlamaParse comparison: selected Mississippi form

Partial semantic/evidence benefit. Both modes preserve hearing and economic-impact marks omitted by Firecrawl. agentic_plus also explicitly preserves unchecked final-action/effective-date options. Both omit the visible DEC 27 2023 filing stamp, although the distinct upper submit date survives. No overall vendor ranking follows.

Original retained PDF bytes were uploaded, not converted markdown: 401742 bytes, SHA-256 ac95c240653690261eb7a6fef83bd80a04310cf49c15c37256569bbc70315955. The connector returned a file ID, but no server-side digest.

| Case | Native parse | Firecrawl parse | Firecrawl extraction | agentic parse | agentic_plus parse |
|---|---|---|---|---|---|
| M1 | text_only_or_partial | text_only_or_partial | correct_but_ungrounded | recovered_supported | recovered_supported |
| M2 | text_only_or_partial | recovered_supported | correct_but_ungrounded | text_only_or_partial | recovered_supported |
| M3 | text_only_or_partial | text_only_or_partial | not_demonstrated | recovered_supported | recovered_supported |
| B1 | text_only_or_partial | safe_abstention | safe_abstention | text_only_or_partial | safe_abstention |
| B2 | text_only_or_partial | safe_abstention | safe_abstention | text_only_or_partial | safe_abstention |
| D1 | not_demonstrated | recovered_supported | not_demonstrated | recovered_supported | recovered_supported |
| D2 | not_demonstrated | recovered_supported | correct_but_ungrounded | not_demonstrated | not_demonstrated |
| T1 | text_only_or_partial | recovered_supported | correct_but_ungrounded | recovered_supported | recovered_supported |
| T2 | text_only_or_partial | recovered_supported | correct_but_ungrounded | recovered_supported | recovered_supported |
| T3 | text_only_or_partial | recovered_supported | text_only_or_partial | recovered_supported | recovered_supported |
| X1 | text_only_or_partial | recovered_supported | correct_but_ungrounded | recovered_supported | recovered_supported |
| X2 | text_only_or_partial | recovered_supported | recovered_supported | recovered_supported | recovered_supported |

Case meanings and exact new-parser evidence are in comparison.json; reviewer RUBRIC.md defines cases. This table is agent-authored assessment, not vendor output. Native and Firecrawl classifications are baseline summaries; retained baseline files support inspection. No aggregate percentage is computed.

The actual vendor extraction used a saved explicit schema with nullable fields, per_doc target and agentic tier. The extractFile call timed out with no structured result. Configuration creation succeeded, but extraction success, backend status and billing are unknown. No synthetic extraction result or automatic retry was substituted.

parseFile exposes fileId, markdown, pages, projectId, tier and version. It cannot express forms=enrich or expand=forms; these options were not requested. Their absence here is a connector exposure limitation, not a claim that the vendor lacks form enrichment. Both parse calls requested latest; resolved versions, job IDs and actual credits were not returned. Timings are connector wall-clock latency, not pure service processing time.

Run python3 normalize.py for the retained agentic_plus mapping. It emits seven exact-evidence observations with needs_review, identifies the upstream model parser, and withholds filing_date rather than substituting SUBMIT DATE. There is no visual repair. Missing clause/eligibility matches cause a nonzero exit with explicit diagnostics; no comment closing date, anchor or effective date is invented. Economic impact and submit date remain in source artifacts because the common envelope lacks those predicates.

Raw responses, requests and capability schemas are retained uncorrected. Source and captured artifact hashes and the shared validator passed. This is not a complete proposal package, discovery test, production approval, or general accuracy benchmark.

Portability: normalize.py and test_guards.py resolve all offline inputs relative to their own location. Original absolute source paths in historical request/expectation artifacts are provenance only, not replay dependencies. Each markdown is exactly its paired raw response content[0].text, with no added newline or correction; replay enforces this relation as well as hashes.
