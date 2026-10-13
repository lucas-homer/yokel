# Held-out native and Docling content review

Manual unblinded review of eight held-out notice units, 22 retained pages. Both complete outputs and all source-page images were reviewed against the unchanged independently adjudicated references. No tuning or new parse calls; Docling JSON/images/native did not rescue Markdown scores. Freeze SHA-256: `9947fb211688ba7010e6e0491fadf88296bd2607cfae877e43b9b9782dc176c7`.

| Arm | All-eight strict gates | Eligible-seven passes | Critical positive yield / conditional content | Critical absence scope |
|---|---|---|---|---|
| Fresh native | 7 pass, 1 insufficient reference | 7/7 | 49/49 | 15/15 |
| Docling | 5 pass, 2 content fail, 1 insufficient reference | 5/7 | 47/49 | 13/15 |

All 16 arm-documents have nonempty outputs. One critical uncertain field per arm is excluded from determinate field denominators and prevents H06 from passing the strict reference gate. These are counts for a small purposive held-out set, not national accuracy or extracted-assertion precision.

Docling H03 retains September 8 but moves its prior-hearing bullet after Fiscal Impact, Jobs Impact and Waivers; the decisive association with Regulatory Analysis is unresolved. It receives partial_ambiguous, without reconstructing its role from the source. Native retains the date immediately following the prior-hearing introduction.

Docling H08 changes the source hearing range “July 22-23” to “July 2223.” This is an incorrect critical transcription and one deduplicated extra assertion, also failing the hearing field. The extension condition remains intact. Docling omits the fiscal footnote on page 3; its frozen absence scope explicitly spans the complete four-page notice/form, so both not-stated timezone/effective fields receive missing for incomplete scope. This does not claim that the omitted footnote states a fixed date or zone.

Both arms preserve H06’s unresolved general-box “20 calendar days” versus target “20 working days.” The conditional 25-request hearing, withdrawal/cancellation condition, request cutoff, posthearing five-working-day window, publication and order-date roles survive. No fixed extension deadline or resolved day basis is inferred.

Both arms lose rule-text underline/strikeout in H03 and H06. H03 reproduces a deleted substantive contract-approval requirement (“30 days prior to signing”) without deletion marking; H06 joins old/new NEC editions as “2023 2026.” These limitations are recorded in source-page notes. They do not add a current public-comment/hearing deadline and are outside this bounded participation-evidence gate. A strict pass should not be interpreted as complete-document or substantive-rule-text fidelity. Maine’s decorative SOS heading is represented only as an image placeholder in Docling, while all relevant proposal/participation fields and both form pages survive.

Artifacts: `field-scores.jsonl` (148 rows: 74 per arm), `document-scores.jsonl` (16), `operation-records.jsonl` (16), `extra-assertions.jsonl` (one critical H08 error), `metrics.json`, `source-page-checks.json`, `validation.json`, and rerunnable `score.py`. All artifact paths are relative to the benchmark directory. Native is **fresh pdftotext 26.05.0 -layout output**, not reused diagnostic scores. Eight native copies compare byte-for-byte with the fresh extraction files and capture hashes; native timing is unknown here rather than attributed from Docling.

Validation checks all frozen files, eight inputs/references, output digests, exact quote spans, 148 unique frozen arm-field keys, answerability-specific field gates and recomputed document gates. It validates record integrity, not a second independent semantic reviewer.
