# Native evidence baseline (developmental)

This bounded, offline research prototype extracts literal candidates from the 28 retained native texts (56 input PDF pages). It makes no provider calls and produces no production observations. The previously reviewed notices are development data, including the eight notices previously called heldout; these results do not measure fresh accuracy.

Run from the repository root with Python's standard library:

```sh
python3 -m unittest discover -s docs/research/state-rulemaking-benchmark/round3/baseline -v
python3 docs/research/state-rulemaking-benchmark/round3/baseline/extract.py
```

The second command validates every input PDF and native-text SHA-256 against `manifest.json`, then rewrites `results.json` and `summary.json` deterministically. No installations, application build, credentials, networking or PDF reparsing are needed. Optional `--manifest` and `--output` arguments select files; input paths are relative to the benchmark root, two directories above the manifest directory.

## Inputs and provenance

`manifest.json` contains only an allowlist of fixture IDs, source URLs, PDF/text paths, checksums, retained PDF page counts and extraction method. Its source freeze files contain review metadata, but the runtime does not read those files or any reference answer. It reads only its own manifest and the listed PDFs/native texts. The PDFs are checked for identity, not parsed or visually reviewed by this script.

- A01–A10/B01–B10: retained `artifacts/source-*/<id>/native.txt` and corresponding `input.pdf`, selected from `artifacts/corpus-freeze.json`.
- H01–H08: retained `round2/heldout-execution/docling/<id>/native.txt` and `round2/heldout/<id>/input.pdf`, selected from `round2/heldout-execution/freeze.json`. The directory name is historical: these are native pdftotext outputs, not Docling text.
- A01/A02/A03 have empty native text and route to parser fallback. This prototype does not execute fallback.

Candidate spans and cue spans use zero-based, half-open Unicode code point offsets in the unchanged UTF-8 decoded native text. Literal slices, form-feed-based page numbers and line numbers are retained. Candidate IDs depend on fixture, kind, offsets and literal; document text hashes and extractor version are recorded. Extracted emails and URLs remain exact literal candidates, not repaired or asserted working addresses.

## Behavior and safeguards

Generic patterns recognize month-name dates, ISO/numeric dates, clocks, day durations, emails and HTTP(S) URLs. Gregorian validation allows date-only normalization for complete month-name/ISO dates and same-month day ranges. Invalid calendar dates remain unresolved. Numeric date order/century, missing years, relative anchors/counting rules, clock/date binding and missing timezones remain unresolved. The script never calculates a close timestamp or copies a year/timezone from elsewhere.

Bounded left context supplies tentative comment/hearing/effective/filing/publication role cues. Conditional, proposed and historical qualifiers are checked before and after the value on the same line. Cues cannot cross page boundaries. Multiple roles, missing roles and modifiers trigger review. **Every temporal candidate also retains `notice_scope_and_role_binding_unverified`**, even with a locally clean cue. Conditions outside the bounded context can remain unseen; this extractor has no accepted-deadline path. Multiple comment values and mixed calendar/working/business day bases route for scope review; they are not asserted to be a true legal conflict. Form/lifecycle label cues route to source review without claiming that check marks, strikes or stamps were recovered.

`resolved_close_utc` is always null; `production_eligible` is always false. `candidate_only` means that the lexical extractor found no configured routing signal, not that the document or observation was accepted. None of this run's documents receive that state.

## Current run

| Measure | Count |
| --- | ---: |
| Development documents | 28 |
| Literal candidates | 264 |
| Date / time / duration candidates | 146 / 25 / 26 |
| Email / URL candidates | 39 / 28 |
| Escalated documents | 28 |
| Empty native text → suggested parser fallback | 3 |
| Temporal evidence review | 25 |
| Missing explicit comment-close cue | 11 |
| Multiple comment values, unresolved scope | 2 |
| Mixed duration bases, unresolved scope | 2 |
| Visual marks/lifecycle source review | 8 |

Route categories overlap. Missing lexical evidence is not proof of absence. All 28 escalate by design; no reduced-review-load or accuracy claim is supported. `summary.json` pins the input manifest and output hashes.

Sixteen offline tests passed: fifteen synthetic behavior tests plus exact candidate/cue span checks over all 28 retained native texts. Tests cover invalid and merged days, no year/order/timezone guessing, separate clocks, ambiguous roles, relative/conditional durations, ranges, Unicode including a supplementary emoji/pages, neighboring notice scope, page boundaries, proposed/historical qualifiers, trailing conditions, unpunctuated years, complete clock literals, empty native fallback and deterministic research-only output. These are executable behavior/provenance checks, not reference-answer accuracy scoring.

## Integration and limitations

The shared contracts were read for alignment (`Confidence`, `ObservationSource`, `ObservationFields`, `ObservationTarget`). Those contracts require federal OCD IDs and authoritative source enums. This state-notice experiment intentionally defines neither, issues no confidence score, submits no review verdict, and changes no application/schema. A research candidate is not a production `Observation`.

The subsequently added `../protocol/runtime-contract.md` and `../protocol/runtime-input.schema.json` define the canonical provider-neutral boundary; the earlier verifier `../verifiers/INPUT-CONTRACT.json` also uses exact Unicode spans. Its runtime cases require a claim, target, role and conditions. This baseline supplies source-text locations and tentative roles; it does **not** infer target identity or fabricate a full claim/condition statement. The primary can select a bounded source context and separately establish those fields for verifier cases, retaining global→local offset mapping. Reference labels remain separate. This baseline is an upstream extraction artifact, not a canonical verifier payload. Before constructing shared runtime cases, replace local fixture IDs with opaque IDs, freeze the role-specific normalized-value schemas, verify PDF page mapping (or leave source page null), and retain exact artifact offsets plus any bounded-context map. No verifier payloads or paid calls were generated here.

Regex coverage is limited: spelled-out dates, unusual formats, split/wrapped email/URL tokens, OCR omissions, text-order corruption, omitted footnotes, visual marks, strike/underline meaning and inaccessible source text may escape extraction. Form-feed page numbers locate native text, not PDF coordinates. Native text cannot establish original-PDF fidelity. Local cues cannot resolve chronology, scope, supersession, actual lifecycle or legal conditional branches. The intentionally conservative whole-document routing is a starting point for development; any selective acceptance policy needs a frozen protocol and a genuinely fresh, source-verified evaluation.
