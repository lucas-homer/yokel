# Automated date/email proposer — frozen development handoff

Research-only native-first vertical slice: propose an explicit absolute written-comment closing date and literal submission-email candidates from full notice text. No provider calls, application changes, contract changes, fresh-notice reads or reference-answer reads were performed. The old 28 notices are development data, with 17 mechanically identified retained slices; they do not constitute fresh full-notice evaluation.

## Source integration

`SOURCE-INPUT-CONTRACT.md` and `source-input.schema.json` are the collector boundary. Use opaque document IDs; separate evaluator mappings/labels from the runtime manifest. Source URLs, acquisition records and publisher metadata may be retained by the collector separately, but are not runtime label fields. Each input invocation declares one channel only. Native is default; acquired fallback must use a distinct manifest and `--channel fallback`. No native miss causes a hidden fallback read. PDF/text bytes must match their manifest hashes and resolve within the explicit source root. PDFs are identity-checked, not parsed by this CLI.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s docs/research/state-rulemaking-benchmark/round4/pipeline -v
PYTHONDONTWRITEBYTECODE=1 python3 docs/research/state-rulemaking-benchmark/round4/pipeline/pipeline.py \
  --manifest docs/research/state-rulemaking-benchmark/round4/pipeline/development-inputs.json \
  --source-root docs/research/state-rulemaking-benchmark \
  --output /private/tmp/round4-new-development-replay
```

Output directories must be new; frozen runs are never overwritten. Python standard library only, no installations or application builds. `development-id-map.json` is an external audit mapping, not runtime input; the CLI never reads it. Old corpus scope declarations use only frozen original/input page counts. Native page mapping is conservatively unknown in that development manifest, so PDF page locators remain null.

## Automatic proposals and evidence

Generic patterns extract calendar-date literals associated with comment-close language, plus all email literals (including contacts). Date-only ISO normalization requires an explicit four-digit year and valid calendar day. Missing years, numeric-order ambiguity, ranges, malformed merged days and invalid calendars retain null value/review; no timezone or UTC timestamp is inferred. The bounded lexical role proposer checks explicit written-comment/deadline language and competing temporal cues. It does not silently turn a hearing date into a comment close. Email values copy the exact source slice, including local-part/domain case; no correction or address repair is performed. Contact-only addresses receive a role-unverified signal for semantic rejection/abstention.

Every emitted case includes the **entire unchanged retained notice text**. Paragraph selection locates evidence automatically; it does not replace source input with decisive reviewer-selected windows. The candidate value, paragraph and qualifying participation passages retain exact global Unicode-code-point spans. Conditional/historical/relative/lifecycle words and stated clocks preserve full relevant paragraph quotations in conditions/claim. Remote qualifying comment/hearing/deadline paragraphs are retained conservatively. This can overinclude qualifications and exceed case limits; no text is truncated to force a request through. Conditions not recognized by generic cues may still escape; full source reaches semantic verification and source audit remains necessary.

`traces.json` records each literal/normalized value, exact context and condition map, precision, null timezone, page locator when known, hard/soft issues and field disposition. `cases.jsonl` follows the existing round-three Jev four-dimension shape (`support`, `role`, `condition`, `conflict`) with a document-level opaque target. Automatic discovery is now part of this experiment; **the existing round-three verifier's excerpt-only POLICY must be replaced/pinned by the runtime owner before live round-four use**. Input-shape compatibility does not authorize reuse of that old discovery-excluded question. The pipeline itself invokes no verifier or provider.

## Routing integration

`ROUTING-POLICY.json` explicitly lists hard and soft issues. Unknown issues default to hard review. Scope unknown/slice, corrupted/incomplete text, lifecycle ambiguity and multiple rule/notice scopes block field acceptance. Distinct date proposals remain hard unresolved scope. Empty/missing field or wrapped-token signals request parser fallback/source review and do not independently block an otherwise supported other field. Full-notice completeness always remains subject to source audit; it is separate from per-field shadow eligibility.

Several email literals are **role candidates**, not automatically established same-role conflicts. A runtime may clear email multiplicity only for a unique matched submission email after every competing address is positively mismatched for that role. Insufficient/failed/unclassified competitors keep review; several matched submission addresses remain review under this bounded slice. Soft issues require completed valid semantic judgments (`supported`, `matched`, `preserved`, `absent`); hard issues remain blockers. This pipeline publishes these signals without implementing provider execution or final cross-arm policy.

`shadow_eligible_text_only` means no deterministic field issue was detected; it is not verified PDF fidelity, an accepted document, a live participation window or production action-readiness. Cases with hard issues are retained for audit/development comparisons; the runtime must not promote them or spend calls on them without its frozen experimental policy. Oversized cases are kept only in traces with `emit_case=false`.

## Development validation

- 28 old documents, 59 automatic candidates (date/email), 31 emitted verifier cases.
- 1 field initially shadow-eligible; 58 fields require review. This low yield is descriptive, not a fresh coverage/correctness claim.
- 28 candidate cases exceed existing claim/condition/evidence/serialized limits and remain untruncated in traces, without verifier emission.
- 3 empty native inputs; 17 retained slices; 16 documents lack a supported-format comment-date candidate; 9 lack an email candidate. Route categories overlap; missing extraction is not proof of absent source evidence.
- 18 synthetic/offline behavior tests passed, including clean field eligibility despite another field missing; contact-vs-submission role; exact email literals; invalid/missing-year dates; no timezone inference; trailing/remote qualifiers and clock retention; full-notice context with supplementary Unicode; conflicting dates/rules/lifecycle; incompleteness/page checks; explicit fallback channels; containment/hash/label guards; source/case overlimits; and deterministic replay.
- All 31 emitted cases passed the existing verifier's strict input boundary and exact evidence-slice checks. All 56 old PDF/text hashes were checked on execution. A separate replay matched cases, traces and summary byte-for-byte.

`freeze.json` pins the ready pipeline, contracts, tests, development manifest/map and run outputs. Do not tune these against the later fresh notices. Remaining limitations include regex coverage, textual role/target ambiguity, overbroad lifecycle/rule-reference detection, overincluded conditions, unsupported date formats, wrapped addresses, OCR omissions and unavailable visual marks. Text alone cannot establish original-PDF fidelity. Fresh collection must follow the frozen source contract, with independently retained source audit and no reviewer-selected runtime windows.
