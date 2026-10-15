# Observed implementation cycles

These are the actual sequential public-interface runs performed during authoring; no claim of paid extraction or complete test exhaustiveness.

1. Weekday tracer: R7 assembly copied from R6 failed with `close: absolute date must normalize from explicit complete literal`. Adding optional weekday grammar and consistency validation made the same test pass (1 test).
2. Multiline components: next test failed with missing literal/alternative_group and unknown components/description/alternative_group_id schema keys. Adding exact component transport, projection and item enumeration made both tests pass (2 tests).
3. Ancillary alternatives: next test failed with `$.alternative_groups: unknown key`. Adding scoped groups, reciprocal membership, role/event/qualification checks made all three pass. Verdict/evidence controls then passed (4 tests).
4. Runtime tracer: actual request/admission/zero-dispatch test failed because run_pipeline.py did not exist. Thin actual serializers, unchanged-cap receipts and synthetic routing made it pass (1 test); additional cap/failure controls passed (3 tests).
5. Observation tracer: evaluator integration failed at missing runtime_gates. Adding strict schema/gate adapter validation, invocation counts and dynamic cohort reporting exposed an optional-cost schema required-list defect; fixing optional unknown-cost shape made it pass. Independent semantic/partial dispatch controls then passed (3 tests).
6. Independent review regression: completed_failed state did not raise; PDF pages=41 reached inventory dispatch. Tightening serial gate/retained judgment consistency and enforcing the existing page cap made the owner suites pass (4 protocol, 4 runtime). JSON integer costs were corrected in the inherited schema validator; float/null/boolean controls also pass. Independent runtime assertions subsequently passed 9/9; reviewer reproductions confirmed all previous malformed rows reject.

Commands used the bundled Python executable documented in README.md, with PYTHONDONTWRITEBYTECODE=1, and `-m unittest discover -s .../round7/pipeline -v`, `-m unittest discover -s .../round7/runtime -p offline_checks.py -v`, or `-m unittest discover -s .../round7/protocol -v`. Final replay regenerates current test-output.txt and hashes; earlier failure logs remain in the chat tool outputs.
