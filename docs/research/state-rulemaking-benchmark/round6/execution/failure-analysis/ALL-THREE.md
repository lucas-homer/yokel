# Three admitted inventories: assembly stopped before verification

All three admitted source-first inventories terminated at `assembly_review`; their records are null and verifier arms empty. This is evidence of extractor/transport/assembly behavior, not Jev or stronger-verifier accuracy. The unchanged frozen assembler reproduces all 18 retained errors. All 102 inventory evidence selectors resolve exactly to source text, so failed quote matching or offset arithmetic is not the cause. Source-label correctness/completeness matching remains the independent evaluator's job.

| Notice | Date grammar | Nonliteral route value | Non-submission alternative group | Result |
| --- | ---: | ---: | ---: | --- |
| OH `doc-de09ce82c4c7` | 2 | 1 | 0 | 3 errors; no verifier calls |
| OH `doc-7be63f24299e` | 2 | 2 | 0 | 4 errors; no verifier calls |
| NH `doc-03d522cbc19e` | 0 | 3 | 8 | 11 errors; no verifier calls |

Inventories came from `openai/gpt-6.1-sol` through provider OpenAI. Combined response-reported inventory cost is $0.1377235, not invoice verified. Costs and exact per-item source spans are retained in `all-three-inventories.json` with source/run/pipeline hashes. The first Ohio notice also has a separate detailed report.

## Cause distinctions

**Four date failures are an assembler grammar limitation.** Both Ohio notices preserve exact weekday-prefixed complete source literals: Monday July 13 / Friday July 10, and Monday October 5 / Friday October 2, all in 2026. Their ISO values agree with the explicitly printed named-date components. `explicit_date()` requires the raw string to begin with a named month (or be ISO) and rejects the weekday prefix. The inventory request calls for complete printed named-month/ISO dates without explicitly forbidding weekdays in raw. This is not a missing-year or false-date problem. A narrower raw component would satisfy the parser, but the run is frozen and no corrected inventories were produced.

**Six route failures violate the exact-literal transport contract.** The first Ohio header address is a reconstructed street/city string with an inserted semicolon and omitted interleaved layout/name text. The second Ohio hearing address is a comma-joined version of multiline location text, and its oral route literal is the description “Oral presentation at the hearing” rather than the printed “orally.” New Hampshire combines Teams name/meeting ID/passcode, telephone/conference ID, and ancillary name/title/postal components into new semicolon/comma-separated strings. Evidence exists for these components or activities, but the proposed contiguous literals are not in their evidence. The guard correctly rejects these values under the frozen contract. This is not proof that the source activities or component values are false; it exposes a raw-literal versus normalized/composite-value boundary the inventory prompt/schema must make easier to honor.

**Eight New Hampshire groups violate a restrictive role-purpose policy.** Three hearing-access routes have role `other` with `hearing_access`; two technical-help routes have `information_contact` with `hearing_help`; three copies/questions/accessibility contacts have `information_contact` with `copies_questions_accessibility`. The frozen assembler permits `alternative_group` only on `submission` routes. That restriction is documented in the interface but not explicit in the inventory system prompt/schema. More importantly, it cannot express grouped alternatives for ancillary purposes while preserving their actual role. The hearing-help source explicitly says contact the named person by phone “or via email”; both literals resolve, yet both rows fail solely for group/role. Grouping every listed contact is not automatically source-proven interchangeability, and hearing access has applicable qualifications; those are semantic questions for later audit, not grounds to relabel contacts as comment submission.

No single fix would make an observed inventory structurally valid: both Ohio records also contain literal violations, and New Hampshire contains literal violations as well as role/group violations. A single ancillary error prevents verification of the whole record, including its other facts. Whole-record acceptance may properly require all facts to be valid, but the current record-null design offers no paired-verifier evidence about those other facts.

## Recommended next experiment

First use these now-observed failures as development regressions for a **new** frozen version, preserving the current failed notices and denominator:

1. Accept exact weekday-prefixed complete date syntax with a declared weekday/date consistency rule; retain raw text and date-only precision, without year/timezone inference.
2. Separate exact atomic source literals/components from optional normalized display/description fields. Multi-part addresses and meeting credentials need explicit component spans; paraphrased activity labels belong in descriptions, not literal fields. Keep exact evidence resolution unchanged and reject unsupported display components.
3. Scope alternative groups by function (submission, hearing access, ancillary help/copies/accessibility), validating role-purpose compatibility and preserving applicability. Never promote contact roles to submission merely to pass validation. If such groups remain prohibited, tell the extractor explicitly; that would align the contract but leave a representation limitation.

Require offline whole-record assembly reachability on weekday, multiline/composite, ancillary-alternative and negative fabricated-literal controls, plus actual provider request admission proof, before fresh collection. Then freeze and run a fresh bounded paired sample; do not repair these inventories and count repaired outputs as the original experiment. Preserve structural admission, source-correctness/omission scoring and verifier judgment as distinct stages. The current live outcome establishes that this exact contract failed to admit three real inventories; it does not establish comparative verifier quality.

No new provider calls, label reads, data repairs or frozen code/output changes. Only new failure-analysis artifacts were written.
