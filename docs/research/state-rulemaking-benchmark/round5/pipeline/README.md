# Round-five native-only proposer — READY handoff

Bounded research revision; earlier rounds untouched. Compatible `round4.sources.v1` source manifest and four-dimension verifier case format are published in `INTERFACE.md`. `ROUTING-POLICY.json` pins explicit module soft/hard issue names; unknown issues remain hard. Fresh round-five sources remain inaccessible until implementation freeze. No providers or OCR were called.

The proposer adds generic “on or before” close language and adjacent form-label/date proposals without borrowing a year, date, clock or timezone. Demonstrative “following [address/rule]” does not itself become a timing qualification. Regulation-subject lifecycle cues remain full-source/provenance evidence rather than automatically becoming a participation-window event. Asserted participation/notice lifecycle changes remain hard. Qualifier selection uses intact candidate-paragraph sentences and adjacent form headers, retaining exact literal spans; unrelated whole paragraphs are not copied into the claim. All notice text remains unchanged in every emitted verifier case, including remote conditions and other events, with qualification/lifecycle cue maps for audit.

DATE claims explicitly assert an actual **unconditional absolute written-comment close**, date precision only. An actual conditional close, relative anchor, invalid/ambiguous/missing-year date, incomplete scope, corruption or genuine distinct explicit close proposals remains review. Appending a conditional quote cannot salvage a bare DATE. Printed clock/zone stays raw evidence without UTC normalization. EMAIL remains an exact source literal with applicable local route qualifications; relative timing alone does not prevent verification of an independently explicit route. Staff/contact/form associations remain semantic questions, never deterministic source truth. Potential lifecycle statements remain visible; favorable model confidence cannot override actual hard blockers.

Ambiguous temporal/form-role alternatives use the published role-resolution signals. The runtime must keep only a unique all-four-supported value after every alternative is positively classified as another role; failed, unknown or unprocessed alternatives remain blockers. Identical unresolved duplicates must not be erased. Actual competing confirmed windows stay review. No whole-notice/action-ready label is generated.

## Validation and development reachability

Twelve proposer synthetic tests passed. Runtime B's 25 offline integration/ledger tests passed using the bundled Python dependency runtime, including full notice context, positive actual entrypoint, hard conditional DATE despite favorable fake responses, independent relative-window EMAIL, exact literal/context guards, no year borrowing, competitors, native-only operation, resume/no retry and request/budget limits. No real transport was used.

`development-inputs.json` allowlists exactly the five full_notice units from round four, now development evidence. It contains no reference labels. `development-reachability.json` checks input byte hashes and exact spans against the actual runtime's `local_gate`, not only the proposer's eligibility flag:

| Measure | DATE | EMAIL | Total |
| --- | ---: | ---: | ---: |
| Native candidates | 3 | 6 | 9 |
| Pass actual local dispatch gate | 3 | 4 | 7 |

Arkansas date/email, South Carolina date/email, and New Hampshire date/two repeated email rows reach the gate. Idaho still has no supported-format written-close/email proposal. Two Hawaii email rows retain their qualifications but fail `request_overlimit_no_truncation`; no context was shortened. This is neither original-source candidate recall nor correct acceptance coverage. There were no model calls on these old notices.

The retained report also runs three controls through runtime B's actual production entrypoint with its fake transport: ordinary in-scope DATE/EMAIL plus incidental accessibility contact reaches terminal shadow fields; a genuinely conditional DATE makes zero requests and stays review even with favorable response machinery; a relative window permits independently explicit EMAIL with one fake request. Full text, source-verification requirement and action_ready=false are retained. Fake choices demonstrate wiring and safety rules, not semantic model quality.

## Reproduce offline

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s docs/research/state-rulemaking-benchmark/round5/pipeline -v
PYTHONDONTWRITEBYTECODE=1 /Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  docs/research/state-rulemaking-benchmark/round5/pipeline/reachability.py \
  --output /private/tmp/round5-new-reachability.json
```

Proposer/CLI use standard-library Python. The reachability helper reuses runtime B's offline fixtures and needs bundled pypdf for neutral synthetic PDF generation; no installation is needed. A separate CLI `pipeline.py --manifest ... --source-root ... --output NEW_DIRECTORY --channel native` emits cases/traces with no provider execution; output directories must be new. The copied source contract has an explicit round-five native-only override: fallback channels are rejected, never acquired silently.

`freeze.json` pins code, contracts, controls and development report. This is READY for primary integration/reviewer freeze, not permission to start fresh collection or publish results. Known limits remain heuristic role/condition association, form-boundary coverage, noisy native text, incomplete scopes and strict size limits. Full-source semantic verification and independent PDF audit are still required before any source-correctness claim. No new extraction features beyond this bounded revision were attempted.
