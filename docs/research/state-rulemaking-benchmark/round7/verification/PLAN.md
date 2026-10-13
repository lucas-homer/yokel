# Independent Round 7 verification plan

Prepared before implementation against SPEC.md and immutable R6 failure/audit evidence. Primary and independent review approved specification SHA-256 `cfc6e8847637c3333fcd994649a6349471585d2fd5efb54952b6d75014324406`; independently checked against the file on 2026-10-09. Ownership is only this verification directory. No tests will target hypothetical entry points; executable tests will follow the reviewed public interfaces once the primary declares implementation ready.

## Independent oracles

- Calendar examples use explicitly authored expected dates (2026-07-13, 2026-07-10, 2026-10-05, 2026-10-02), with a contradictory weekday as a negative. No parser-derived expected values.
- Exact literal controls use small source-first authored text and explicit expected spans. Unsupported components, altered evidence, unrelated activity bindings and mutated presentation must remain distinguishable.
- Groups use authored role/event/requirement expectations: contradictory reciprocal membership and mixed purposes fail structurally; source ambiguity survives favorable synthetic replies as review.
- Semantic completeness and disclosure classification use independent authored source-unit mappings. Omission or misclassification may assemble structurally, but must veto useful complete acceptance. Evidence quotes alone receive no recovered-claim credit.
- Counter-based fake transports establish dispatch and operation-intent counts. Rejected inventory bodies cause zero intents/calls. Either rejected verifier body prevents both verifier arms; preserve admitted record and common payload hashes.
- Runtime terminal observations flow directly through the adapter to evaluator. Gates retain not_started/called:false, missing rows remain unserved, true synthetic failure remains called:true, and forged status/hash combinations reject.
- prior-round-hashes.json snapshots every existing file in round1 through round6 before implementation. Verification compares exact file sets and hashes, preserving immutable output/failure denominators.

## Focused adversarial controls after implementation readiness

1. Wrong weekday, leap-day invalidity, missing year, ambiguous numeric dates, clock/prose suffixes and invented normalized values.
2. Supported multiline components versus invented component and semantic misassociation; arbitrary supplied display and tampered derived display.
3. Dangling/nonreciprocal/singleton/mixed-role/cross-event groups; uncertain alternatives and retained qualifications.
4. Independently remove an ancillary endpoint and change disclosure class, modality or scope; confirm structural/semantic distinctions with favorable mock verdicts.
5. Measure actual serialized model-specific requests below/at/over unchanged caps; assert counters, source preservation and exact admission hashes. Retain honest KY rejection.
6. Pre-verifier gate and actual call-failure cases through real runtime/adapter/evaluator; test malformed called flags, unequal paired payloads and missing observation denominator.
7. Run shipped development replay and all public-interface unit checks using bundled Python, record actual commands/results/request/code hashes, then compare the prior-round baseline.

## Execution constraints and reporting

Use standard library only with PYTHONDONTWRITEBYTECODE=1 and bundled Python. No dependencies, builds, provider calls, credential/Keychain reads, source collection or existing artifact edits. Independently block network and credential-process access in test execution where supported; label synthetic transport calls explicitly. Reports will list each observed control outcome and unresolved gaps rather than treating implementation self-tests as independent proof.

Expected entry-point command after readiness:

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 docs/research/state-rulemaking-benchmark/round7/development/replay.py
```

Review notes incorporated: test inherited ambiguous/altered selectors and component/group verdict coverage; exercise Jev total-request and state-plus-longest-probe caps independently; inspect the documented cross-event binding rule and gate/status consistency table. Focused independent cases supplement the author suite; no duplicate full suite is planned.
