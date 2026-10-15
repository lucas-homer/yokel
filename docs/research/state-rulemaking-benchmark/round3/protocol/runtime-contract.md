# Pilot verifier contract

Use ../verifiers/INPUT-CONTRACT.json and verifier.py as the pilot wire interface. runtime-input.schema.json mirrors its source_text/candidate/evidence shape. runtime-output.schema.json is an internal evaluation wrapper, not an alternative provider response. Keep source artifact hashes, page maps, case-family mapping, routing history and evaluator labels in separate sidecars. Do not pass extra metadata or gold labels through an adapter that rejects unknown fields.

## Shared state and exact values

All arms see the same source_text, candidate field/value/claim/target/role/conditions and exact evidence. candidate.value is bounded JSON: string, null, finite number, boolean, list or object, with at most four nested levels, 16 entries per container and 4,000 serialized UTF-8 bytes. Preserve compound values as JSON, not flattened strings. A separate code-owned typed normalization record can retain date components or relative units. Models do not generate repaired strings or replace the candidate. Preserve raw email local parts and date precision.

Offsets are zero-based, half-open Unicode code-point indexes into source_text, and source_text[start:end] must equal quote exactly. These are context-local offsets in the actual pilot, not whole-artifact offsets. Preserve a separate mapping from each context segment to retained artifact hash and original offsets/pages. JavaScript code must handle UTF-16 versus code-point indexing explicitly. Reviewer-selected windows are legitimate semantic challenges but not automated retrieval evidence.

The adapter enforces at most 30,000 source-text code points, 50,000 serialized case UTF-8 bytes and 12 evidence spans. It permits at most 20 pilot cases. Do not truncate to fit; record ineligibility or correct and re-freeze before execution. Case IDs stay out of model state where possible; keep target metadata provenance explicit. A short snippet may be declared scoped to a target by the common challenge setup, but that assumption must not be mistaken for successful target segmentation or PDF verification.

## Four independent judgments

The actual rubric has four dimensions. Support asks whether the actual structured value and claim are supported together. Role asks whether that actual value has the proposed target/role. Condition requires relevant qualifications in both candidate.conditions and claim. Conflict asks whether the supplied relevant source contains unresolved incompatibility for that role. Do not conflate unsupported values with conflicting source passages.

The fixed primary gate is text_supported_only iff there are no deterministic blocking issues, response/schema validation succeeds, and the labels are supported, matched, preserved and absent respectively. Every other tuple escalates; any insufficient does so. Confidence and probability are diagnostics, not thresholds. A model cannot override code checks or promote source verification. A tied Jev distribution is converted to insufficient under the adapter's frozen rule. TypeSafe provides independent Choice answers; the general model returns the same four labels. [Choice documentation](https://docs.typesafe.ai/primitives/choice).

Text_supported_only is not action-readiness. A faithfully quoted corrupted email can pass the four text judgments and remain false to the original source. Record that escape honestly. A source-conflict case must escalate. Do not use its known case ID to force that outcome.

## Eligibility and failure accounting

Before calls freeze the exact per-provider eligible list produced by common deterministic checks. Empty evidence or a null value produces a recorded abstention without provider calls. A malformed input must be corrected/re-frozen rather than silently excluded. Missing, duplicate or invalid response dimensions, fabricated quotes, invalid probability values and incomplete provider completions are operational/schema failures. Preserve originals; no hidden retries or second-model repairs. Operational escalation does not count as semantic error detection.

Cases with nonunique dimension labels may still have a unique gate outcome; score that gate and report set-valued dimension diagnostics. A case whose text-support gate itself is ambiguous is retained but excluded from the primary resolved-gate denominator, with conservative/optimistic bounds shown. The source-fidelity safety table remains separate and includes text-supported blind spots. Never change eligibility because of a model's observed response.

## Implementation checks

Validate current runtime files with adapter state_for/build_request without live calls; bind hashes of inputs, labels, adapter, rubrics and policy. Verify exact evidence spans, bounded candidate value type, no unexpected fields, no gold-label access and identical semantic state across arms. Preserve enough conditions for the chosen target field without importing unrelated deadlines. Test injected source instructions, role swaps, changed dates/email characters, conflicts, unknown scope, invalid schemas, empty candidates and supplementary-character offsets. These checks require no provider calls.
