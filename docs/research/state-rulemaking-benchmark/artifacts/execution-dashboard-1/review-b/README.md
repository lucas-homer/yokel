# B01–B10 REST v2 Markdown review

Complete: 20 document-arm reviews and 164 frozen fields. All 19 retained source-page images and all returned Markdown were inspected; every target notice received a critical-extra-assertion audit, including neighboring-notice boundaries. JSON output was not used to rescue Markdown.

Both arms pass 10/10 document gates, each with 64 supported fields and 18 safe abstentions. B04 Agentic was initially classified as a critical citation failure because of unsupported tilde markers. Primary adjudication corrected this: exact citation remains directly beside the selected amendment action in raw HTML, with page2 confirming proposed amendment; no contradictory identity/action is established. Rendering of Markdown inside HTML was not defined or tested. The initial judgment and correction rationale are preserved in correction-history.json; the markers remain a noncritical formatting diagnostic.

Secondary defects are retained in extra-assertions.jsonl: unsupported B04 Agentic tilde markers inside HTML, unsupported B03 notice underlining in both arms, B04 Plus invented unchecked fiscal-note box, and B05 Agentic public-comment navigation URL slash loss. B03 citation is not struck; proposed rule-body underlining is source-supported. Passing the frozen gate does not assert complete typography or legal-text fidelity.

Artifacts: judgments.json contains deliberate manual line spans and exceptions; field-scores.jsonl, document-scores.jsonl, operation-records.jsonl and extra-assertions.jsonl use the common row schema. findings.json and validation.json summarize results. Run python3 score.py for bookkeeping and exact-span/hash/freeze checks; it does not infer semantic judgments.

All 141 frozen artifacts remain unchanged. Captures must report COMPLETED, operational_success=true and no anomalies, with matching input hash/bytes/pages and Markdown hash. Original connector history remains separate and untouched. All review edits are confined to this directory.

Execution source is execution-api-1/runs/B*/tier. Nested REST v2 configuration is retained without claiming equivalence to legacy high_res_ocr/hide_headers/hide_footers settings. Latest remains unresolved. REST polling-inclusive observation times, returned parser metadata and UI timing are distinct. No provider, network or UI execution was performed by this reviewer.
