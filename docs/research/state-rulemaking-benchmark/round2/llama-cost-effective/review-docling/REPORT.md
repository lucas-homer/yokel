# Docling operations audit

All 177 operational/integrity checks pass for 20 completed inputs and 34 pages. The child final README, results and validation manifest are present and remained unchanged during review. This audit wrote only review-docling; no conversion, inference, content scoring, network calls or credential access occurred.

All 141 frozen artifacts and original 629 retained files match their hashes and sizes. Inputs match expected hashes, bytes and independently read PDF page counts. Native copies match the frozen native.txt byte-for-byte. Every output hash/size agrees with its capture; all structured documents validate as DoclingDocument with complete page identities. Independent full-content-layer re-export reproduces every output.md exactly. All 20 Docling Markdown outputs differ bytewise from their native baselines; that difference is not a quality result.

Runtime evidence matches Docling 2.134.0, docling-core 2.100.0, docling-parse 7.22.2, ocrmac 1.0.1 and torch 2.14.1. All resolved package versions match the available isolated runtime. All 42 model/cache files and retained model revision refs match. Retained source specifies Apple Vision/ocrmac accurate en-US adaptive OCR, CPU4 layout/table models, table structure and all Markdown content layers. Runtime serialized OCR base fields omit subtype recognition/kind; use the source alongside runtime metadata for configuration provenance.

Serial observed intervals and completion order agree. A01/A06 operational pilots precede the remaining 18. No failures exercise the three-consecutive-failure stop. First A01 wrapper time is 20,102 ms; remaining 19 median is 1,027 ms. These are one-run wrapper measurements with cold initialization/model/OCR overhead and converter reuse, not a controlled speed comparison. Peak process RSS is a cumulative macOS high-water mark; Apple Vision internal accelerator selection is not controlled by CPU layout/table settings. Installation/model acquisition, energy and full-machine load remain unmeasured.

One portability finding affects all 20 capture.json files: confidence metadata contains NaN, which strict JSON consumers reject. Preserve original captures and use a tolerant parser or explicitly derived strict-JSON sidecar mapping non-finite confidence to null/unknown. No raw capture was altered. The audit output itself is strict JSON.

Model/runtime storage remains temporary. Recorded model hashes/revisions support replay provenance while retained; the layout main alias was not pinned before initial download. Artifact secret-pattern scans found no matching signed URL or bearer values.

Pipeline completion and exact export consistency do not establish evidence quality. Independent content review remains necessary. audit.json contains checks, limitations and byte comparisons; artifact-inventory.json freezes inspected Docling files; audit_docling.py reproduces this read-only verification using the retained isolated runtime with python -B.
