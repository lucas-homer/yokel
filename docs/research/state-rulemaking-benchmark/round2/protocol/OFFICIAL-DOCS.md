# Parser access and capture findings

Checked October 6, 2026 Pacific through public official documentation only. No authenticated API request or parsing job was made.

## OpenRouter Mistral access

`mistral-ocr` is an engine under `plugins[].id = "file-parser"`, not the downstream conversational `model`. OpenRouter documents PDF processing through chat completions, forwarding parsed results to that model. Its file annotations contain ordered text/image content; success responses carry them in message annotations, while certain downstream failures retain them at `error.metadata.file_annotations`. The documented image forwarding cap and model-dependent image removal can affect wrapper behavior. The page does not specify a selectable or resolved Mistral OCR release. [Official PDF Inputs documentation](https://openrouter.ai/docs/guides/overview/multimodal/pdfs).

Selected round-two path: OpenRouter. Score only retained annotation text, preserve raw annotations and part pointers, and name the arm `mistral_ocr_openrouter_annotations`. Direct OCR would offer tighter parser control but is not selected for this execution. Exclude assistant prose. Freeze the downstream model/prompt/settings and report its cost separately. Missing annotations cannot be replaced by asking the assistant to reproduce the PDF. Do not equate OpenRouter's file hash with the locally computed input SHA256. Keep backend-version identity unresolved absent returned evidence.

The PDF documentation retrieved through the text interface had blank numeric pricing placeholders. Do not infer today's price from an older announcement. Resolve a dated price and spend ceiling before execution; retain actual returned charges separately.

## Direct Mistral OCR

The official OCR processor accepts a PDF URL, uploaded file or base64 PDF, and returns per-page Markdown, image/table information, model and usage metadata. `mistral-ocr-latest` is an alias. Optional table/header/footer separation can move text out of the primary Markdown; default tables are inline and headers/footers remain in main content unless separation is requested. [Official OCR processor documentation](https://docs.mistral.ai/studio/document-processing/basic_ocr).

Recommendation: use a verified fixed OCR model where exposed, with document/bounding-box annotations disabled for this parsing-only arm. Keep text components inline or freeze an explicit lossless assembly adapter. Retain returned model and usage without claiming the alias resolution from request spelling. This access path can isolate OCR without a downstream conversational answer; it is a distinct arm configuration from OpenRouter.

## Docling

The official CLI distinguishes standard, native and VLM pipelines; configurable OCR backends, table extraction, forced OCR, and optional enrichments affect what is being compared. [Official CLI reference](https://docling-project.github.io/docling/reference/cli/).

Recommendation: freeze one local standard-pipeline configuration with OCR and tables, and disable generative enrichments. Pin the installed release and model artifacts, verify flags against that release, and record hardware/cache state. Do not use auto backend selection without recording its resolved backend. The primary selected the actual Docling2.134.0 macOS OCR configuration recorded in `../docling/runtime.json`; the earlier RapidOCR suggestion is not the executed arm.

## LlamaParse

Official documentation distinguishes Parse from Extract and exposes Cost-effective as a parse tier; Auto routing may mix tiers. The pricing page lists Cost-effective parsing at three credits per page, an estimate for planning rather than observed billing. [Parse overview](https://developers.llamaindex.ai/llamaparse/parse/), [tier documentation](https://developers.llamaindex.ai/llamaparse/parse/guides/tiers/), [pricing](https://developers.llamaindex.ai/llamaparse/general/pricing/).

Recommendation: explicit `cost_effective` Parse, Auto routing disabled, no Extract request, and raw returned Markdown. At the proposed maximum 58 pages, the published-rate estimate is 174 credits before any separately approved setup/recovery activity; actual returned usage controls the report. Verify and pin the request schema/version before running, and do not assume legacy dashboard flags map to v2.
