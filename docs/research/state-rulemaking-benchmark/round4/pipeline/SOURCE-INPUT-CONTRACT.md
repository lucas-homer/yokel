# Round-four source manifest — v1

Freeze this input contract before fresh collection. The pipeline accepts a JSON manifest with `schema_version: "round4.sources.v1"` and `documents`, an array of the records below. Paths are relative to the manifest directory, resolved within an explicit CLI `--source-root`; files outside that root are rejected. Source IDs must be opaque (`doc-` plus 12 lowercase hex characters), with no fixture IDs, evaluator labels or reviewer-selected decisive spans.

```json
{
  "schema_version": "round4.sources.v1",
  "documents": [{
    "document_id": "doc-0123456789ab",
    "channel": "native",
    "text_path": "sources/document/native.txt",
    "text_sha256": "64 lowercase hex characters",
    "pdf_path": "sources/document/input.pdf",
    "pdf_sha256": "64 lowercase hex characters",
    "pdf_pages": 2,
    "scope": "full_notice",
    "native_page_map_known": true
  }]
}
```

Required keys are exactly those shown. `channel` is `native` or `fallback`; `scope` is `full_notice`, `slice`, or `unknown`. These mechanical declarations must come from collection/extraction, never reference answers. `pdf_pages` is the retained input PDF's positive page count, not a reviewer accuracy label. `native_page_map_known` means the extraction process establishes sequential form-feed page mapping to that PDF; false leaves PDF page locators null. If the retained input is only a slice of a larger notice, declare `slice`, even if it has a PDF.

Each invocation processes one channel only. Native is the default. Newly acquired fallback text must be a separate manifest/channel and separate invocation; it is never read silently after a native miss. Native empty text, unknown/slice scope, page-count disagreement when page mapping is known, replacement characters, or unmatched participation evidence trigger parser-fallback/source-review requests. A successful text parse cannot establish PDF fidelity.

UTF-8 bytes are frozen and hashed without newline/whitespace repair. Candidate and context offsets count Unicode code points in that exact decoded text. Full notice text enters every emitted verifier case; automatic paragraph/context spans only locate candidate evidence, never replace the full source with reviewer-selected windows. Inputs over the existing verifier limit (30,000 code points / 50,000 serialized case bytes) route to review without truncation or provider cases.

The pipeline reads only its manifest and listed PDF/text bytes. It rejects extra record keys (including labels, references and gold spans). PDF bytes are identity-checked, not parsed by this CLI. Output is research-only. Neither this contract nor collector declarations certify source correctness.
