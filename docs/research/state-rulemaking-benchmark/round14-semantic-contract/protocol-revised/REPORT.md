# R14.2 bounded protocol revision

READY revised offline candidate in protocol-revised/. All21 original protocol artifacts and READY verified unchanged; original-freeze.json pins them. No API calls, credentials, fresh source/gold/provider output, runtime edits or writes outside this new directory.

Corrected unit2 actor uncertainty; split arrival and ambiguous-request clock/timezone facts with linked date context and attached qualifications. Added ValueError guards for expanded units/evidence. Clarified exact Unicode/control splitlines separators and160-item capacity sentinel. Ten-field shape, enums, string caps,8192 output cap and Sol low/OpenAI-only settings retained.

24/24 tests pass: old structural checks plus authored preservation, malformed inverse types, Unicode separators/capacity boundary, full overlong s/c/r rejection without clipping/mutation and data-only illustration-leakage boundary. Leakage deliberately passes shape validation; no semantic parser claimed. New overflow/leakage data never enters operational prompt. Future model semantic tests need facts disjoint from illustrations.

Regenerated R14.2 fictional schema/request/table/outputs/sizing. Request11582 bytes+1024 allowance=12606, below40000. At2bytes/token+256 allowance, representative64=5991/8192 (73.1%,2201 residual), failing70% diagnostic target. Stressed96/128=22788/30344 exceed8192 even at4bytes/token. No tokenizer count or source-specific fit guarantee. Overflow is a representation stop; silently shortened qualifications require independent semantic rejection. Caps unchanged, no clipping/retry/chunking workaround.

Focused Fable findings addressed with documented limitations, not review approval. Primary-requested Fable diff re-review, runtime version/schema update and headroom/release decisions remain pending. READY does not authorize dispatch.

Changed/new files against original snapshot:

- REPORT.md
- SPEC.md
- compact.py
- fictional-negatives.json
- fictional-positive.json
- fictional_controls.py
- illustration-leakage.json
- offline-request.json
- offline-results.json
- offline_checks.py
- original-freeze.json
- overflow-controls.json
- representative32.json
- representative64.json
- revision_controls.py
- schema.json
- semantic-controls.json
- span-table.json
- stage-a.system.txt
- stressed128.json
- stressed96.json
- test-output.txt
- test_compact.py
- test_revision.py

Byte-identical copied file: request-settings.json, test_semantic_contract.py.
