# Docling diagnostic20 content review

Manual, unblinded review of the 20 retained Docling Markdown outputs against unchanged frozen adjudicated references. Source-page images (34 retained input pages) were visually checked, including selections, colored stamps, ambiguous characters, blank regions and register boundaries. The complete Markdown was swept for extra critical assertions. JSON, image placeholders and native text did not rescue Docling field scores. No new parsing jobs were run.

## Results

Docling: **15 pass / 4 content fail / 1 insufficient reference**, over all 20 scheduled notices; **15/19** among reference-eligible notices. All 20 operations returned nonempty output; operational success does not imply content completeness.

- Critical positive evidence yield and successful-output content score: **109/118** determinate present/explicit-negative fields.
- Critical negative scope preservation among successful outputs: **21/23** not-stated fields.
- One critical incorrect assertion in one document: A03 title/list **S → 5**, counted once. The separate source-faithful body statement about creating subpart 5 is not an error.
- A01: omitted filing stamp and lost final-effective selection.
- A02: omitted filing stamp, lost amendment selection, and literal X conflicting with unchecked Markdown for the proposed-effective choice.
- A03: omitted filing stamp, title transcription error, and literal X conflicting with unchecked Markdown for final lifecycle. The selected May 8 effective date survives.
- B08: termination reason ends at “re-filed,” omitting “to correct an administrative error.” The full predeclared reason fails; frozen full-notice absence scopes also fail coverage.
- A07: both conflicting source original-notice years survive. Its critical reference remains uncertain, and its strict document gate is insufficient-reference.

Literal X plus an unchecked Markdown box receives partial_ambiguous because the output contradicts its selected-state rendition. Labels alone are not invented actions. B04 preserves selected proposed amendment and hearing; its unfilled automatic-legislative-review form label is not a positive selection. B03 proposal-stage context remains explicit despite lost rule-text underlining. Bracketed deleted Texas rule text retains deletion context and is not treated as a new participation assertion.

## Artifacts and path semantics

- `field-scores.jsonl`: 174 Docling rows, frozen field IDs/groups/answerability, exact quotes and character/line locators, output SHA-256, omission scopes and notes.
- `document-scores.jsonl`: 20 Docling gates and critical counts.
- `operation-records.jsonl`: 20 local operations with capture pointers and timing.
- `extra-assertions.jsonl`: one deduplicated critical transcription assertion.
- `source-page-checks.json`: source-image hashes, viewed pages and notice-wide audit notes.
- `metrics.json`: named denominators, paired document outcomes and reused native diagnostics.
- `validation.json`: ledger/hash/quote integrity and unchanged frozen corpus checks.
- `score.py`: rerunnable materialization of manually selected evidence ranges and decisions; it performs no parsing or automatic semantic scoring.

**Docling artifact paths are relative to the benchmark directory** (`docs/research/state-rulemaking-benchmark/`), including `round2/docling/...`. Input/reference hashes refer to the original frozen artifacts. **Native ledgers retain their original artifact-root semantics** (relative to `artifacts/`) and are kept separately as `native-*.jsonl`. These original native score lines were copied byte-for-byte from `artifacts/review/results-completed-v1/` after verifying all 20 retained native output copies against the originals. `native-reuse.json` records each original/copy/hash plus source ledger hashes. No native extraction or semantic re-scoring was performed.

Native reused gates: 14 pass, 2 content fail, 3 operationally unusable (image-only empty extractions), 1 insufficient-reference. Native critical positive yield is 91/118; conditional on nonempty output it is 91/94. Native negative scope preservation is 22/23. Paired gates: 13 both-pass, 2 Docling-only pass, 1 native-only pass, 3 with unusable native output, 1 reference-insufficient. These are diagnostic counts on a purposive corpus, not national accuracy or extracted-assertion precision.

Validation confirms 141 frozen files unchanged, all 20 reference hashes/input hashes, all score-output hashes and exact quote offsets, 174 unique Docling field keys, 20 document/operation keys, and identical native output bytes. The review has one reviewer; record integrity validation is not an independent semantic review.
