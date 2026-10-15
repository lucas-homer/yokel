# Round6 research participation record

Source-first generative inventory → strict quote and relation validation → normalized participation record → paired independent verification. No regex candidate proposer, new framework, production schema, provider calls, or fresh collection in this directory.

See `INTERFACE.md` for runtime coordination. `inventory.schema.json` describes raw model output. `verdict.schema.json` describes stronger generative verification; Jev uses non-generative bounded probes over the common payload. `pipeline.py` is stdlib-only and callable; requests contain prompts/schema, never provider credentials or execution. Runtime pins the generative inventory and stronger verifier models and enforces the conservative $2 experiment cap.

Representation preserves typed phases/events; opening/closing/hearing timing and explicit dependency references; valid alternative routes; mandatory/optional/conditional/informational requirements; instruction/disclosure class; exact references/formats; notice identity uncertainty; exact source spans. Clearly conditional/relative source timing can be represented without an invented absolute date. No field is projected as unconditional merely because a model returns a favorable verdict.

Evidence selectors use exact raw quote, optional occurrence, and optional unique context. Assembly resolves offsets deterministically. Repeated or missing quotes, conflicting selectors, dangling references, malformed shapes, identity/hash mismatches, missing-year normalization and source clipping fail closed. Unique-offset resolution is evidence integrity, not proof of the quote's applicability or completeness.

Structural validity never proves semantic support, correct role, preserved requirements, source identity, or source absence. An empty but valid inventory remains source-completeness unverified; both verification arms must inspect the full source for omissions. The record includes inventory coverage claims as claims. Raw inventory is separately retained and hashed. Common verifier payload stores full text once and normalized inventory facts once, with a canonical hash for arm equality.

## Development validation

Run `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v test_pipeline` here. Controls cover source/quote integrity, ambiguity, missing-year and clock precision, typed temporal dependencies, alternatives, remote filing references, phase distinctions, publication latency, identity discrepancies, role retention, false heading removal, request independence, envelope tampering, and stronger-verdict item coverage/omission consistency.

Old KY/NM/MI/OH sources and synthetic controls are development data, not fresh evaluation. Hand-authored inventories prove representation and deterministic behavior, not extraction-model recall or verifier quality. The large KY fixture uses the entire eight-page, 19,155-codepoint native source and explicit route/hearing/instruction facts; runtime must test actual provider admission against this fixture before freeze.

## Remaining risks and coordination

- Exact source selectors can fail on generated quote transcription; fail closed and record the failure, with no automatic provider retries or fuzzy repair.
- A generative inventory can omit requirements or assign incorrect relationships despite valid evidence. Full-source paired verification and independently frozen image labels test this; agreement is not source truth.
- Jev's bounded judgments cannot cite arbitrary omitted spans, while the stronger verifier can. Compare common dimensions, preserve transport-specific output capabilities, and do not claim identical expressiveness.
- Full source plus facts may exceed actual request admission or output limits. No clipping; runtime measures/reserves worst-case requests and records failures in the denominator.
- Inventory-model and verifier-model family overlap weakens independence; preserve distinct call provenance and report it.
- Assembly does not decide semantic acceptance, confidence thresholds or unconditional deadline readiness. The evaluation/runtime contract owns the preregistered rule; all artifacts here remain shadow and not action-ready.

No further design decision is needed from primary to integrate the v1 callable interface. Runtime/evaluator owners must reconcile acceptance and budget rules, perform actual provider request admission checks, and independently review before the primary freezes and releases fresh collection/live calls.
