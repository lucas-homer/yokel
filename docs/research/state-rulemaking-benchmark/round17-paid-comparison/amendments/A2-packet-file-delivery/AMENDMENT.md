# Amendment A2: reference-author and reviewer packets delivered as one pinned file (2026-10-13)

**Changes:** PROTOCOL E1 and E5 say each packet is "supplied inline in the prompt". Instead, the primary writes each packet as one JSON file, `reference/<source_id>/AUTHOR-PACKET.json`, which holds `source_id`, `source_text_sha256`, the full REFERENCE-SPEC.md text and the exact `parsed-body.txt` text, and pins its SHA-256 here. The author's prompt names that single file and forbids opening, listing or searching any other path, and any browsing. Reading any other path still invalidates the reference (E1), and its tool log is retained.

**Why:** pasting about 24 KB of spec and source by hand risks transcription errors. One wrong character would shift every codepoint offset the reference depends on. Machine-written packets give the exact bytes, pinned by hash, which better meets E1's aims: an exact input that is recorded and isolated.

**Unchanged:** author and reviewer identity, isolation, what the author never sees (E2), the format (E3), the checker (E4), review and exchange (E5, E6), freeze (E7), sufficiency (E8) and everything else.

**Decided by:** the primary. It is a delivery-mechanism change, recorded for audit.
