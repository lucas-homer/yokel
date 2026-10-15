# Independent mechanical readiness audit

**Mechanically ready with scope limitations.** All 2,053/2,053 checks pass. Twelve source records retain 52 PDF pages. The source manifest has exactly the permitted mechanical keys, no evaluator keys or reviewer spans, and path confinement/hash/page-tree checks match the published contract. No proposer or runtime execution occurred.

Freeze A matches all 42 frozen implementation/protocol files; Freeze S matches all 412 frozen source files. The collector receipt binds the actual Freeze A and final READY receipt. All frozen bytes were rehashed after the audit and remain unchanged. Python 3.12.14 and pypdf 6.10.0 match implementation pins; retained collector metadata reports Poppler pdftotext 26.05.0. No installed native command was invoked by this audit.

## Mechanical input accounting

| Document ID | Actual PDF pages | Declared scope | Native form-feed pages |
| --- | --- | --- | --- |
| doc-0511d79a7aa6 | 3 | unknown | 3 |
| doc-7035335ec6ae | 1 | full_notice | 1 |
| doc-6de1104bdc54 | 2 | full_notice | 2 |
| doc-cc8a5c237cc2 | 4 | full_notice | 4 |
| doc-27f924e9b9d3 | 6 | slice | 6 |
| doc-6d4517336d61 | 10 | unknown | 10 |
| doc-bab42aac1958 | 5 | slice | 5 |
| doc-eb83abf91c18 | 12 | unknown | 12 |
| doc-09c6b865024f | 1 | full_notice | 1 |
| doc-03fab2becee5 | 6 | full_notice | 6 |
| doc-de7ceb52736b | 1 | unknown | 1 |
| doc-b00441b94ff1 | 1 | unknown | 1 |

All 24 listed PDF/native identities match their source-manifest SHA-256 and Freeze S entries. Paths resolve within the sources root and obey byte caps. All actual PDF page trees match declared pages. Known native form-feed mappings match those PDF page counts; native files were read only as opaque bytes for hashing and delimiter counts, never decoded or inspected for notice content. PDF content was not extracted or rendered. These checks establish plumbing, not text fidelity.

The manifest declares **five full_notice, two slice and five unknown** scopes. Those are allowed collection metadata, not truth established by this audit. Under the unchanged frozen runtime, only the five full-notice inputs (14 pages) can receive field-level shadow observations/OCR; seven slice/unknown inputs stay review. Every one of the 12 scheduled inputs must remain in evaluation accounting regardless of outcome. Do not silently improve or discard scopes after results.

## Budget and remaining prerequisites

The broad 12-document/52-page/120 maximal Jev-request nominal reservation envelope is **$0.5048**, below the $1 cap. Given current declared scopes, the eligible OCR envelope is five documents/14 pages and **$0.2538** including all 120 maximal Jev requests. These are conservative admission estimates, not invoices or predictions of actual calls. No proposals were generated, so candidate counts and per-request context lengths remain unknown and must be handled by the frozen runtime caps. No scan/degradation truth or field accuracy was evaluated.

Independent source labels/Freeze B still need to be completed and externally bound by the primary before live authorization. This audit does not open labels, verify source truth, or certify the labels-frozen attestation. It does not establish original-source correctness, complete notice scope, native UTF-8/content quality, or model acceptance readiness. Source isolation is code/data separation; no new filesystem sandbox was established.

## Pins and reproducibility

- Freeze A: `477b88dab5bbc4a6ff999f4c5b1f0efbc38abd59972f65e85c0e06afa3b0c56b`
- Freeze S: `500b9ae205f2c2b04d544a7b5e11c544fbc586ec8ad091af7493f4a064970cc3`
- Runtime READY receipt: `60438e1e1732d6763839f508612674f05d8ce8a69d8f83294d61489ce12c8cc8`
- Source manifest: `01136c91766b1c1eff184f4621846ed3b87971c0fbcaa8779d4307cde8fdcfed`

`audit.py` independently checks metadata and hashes without importing the runtime/proposer. `audit.json` contains the bounded findings, `checks.json` all 2,053 checks, and `frozen-hash-inventory.json` the verified frozen file identities. Sole writes were new files in execution/preflight-audit. No provider, credential, proposer, native-content, image or reference-truth access occurred. Frozen code and source files remain unchanged.
