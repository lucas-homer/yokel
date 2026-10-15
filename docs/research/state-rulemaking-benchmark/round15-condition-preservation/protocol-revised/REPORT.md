# R15.1 bounded hardening report

READY offline revised candidate in protocol-revised/. Original37 protocol artifacts and READY verified byte-identical, pinned in original-hardening-evidence.json. No prior edits, API/bridge calls, credentials, installs, commits, runtime compatibility fixes or production changes.

Graph DFS now uses deterministic iterative enter/exit frames with cycle detection and postorder depth memoization.399-node NOT chains reject controlled graph_depth at recursion limits1000 and600;399-node cycle rejects node_cycle at600. Deepest shared paths validate/reject at12/13 under root-first/reversed/leaf-first order; shared diamond stays valid with exact inverse. Returned inverse d/b/a lists are deep-copied; mutations do not alias expanded input in either direction.

31/31 tests pass under bundled Python -I -S -B: original24 retained plus7 hardening tests. Targeted assertRaisesRegex probes reach exact deadline_uncertainty/applicability_links branches with unrelated invariants satisfied. Original1000/600 behavior and masked error codes retained, along with pre-fix test log showing two regression errors. Structural validity remains distinct from semantic completeness.

Versions r15.1/r15.spans.2/round15.expanded-inventory.v2; API/wire semantic shape, settings, primary qual rule, limits and safety flags unchanged. Regenerated fictional schema/request/evidence/outputs/sizing only here. Guarded request16503/40000 bytes; output8192 retained. No tokenizer/live-fit/compression claim. Tuple provider/runtime compatibility remains unresolved; no dispatch authorization.

SPEC clarifies inverse self-consistency versus original-response authenticity, exact codepoint ranges versus grapheme/full-condition coverage, invisible annotation limitations, and removed unit c versus deadline y.c. No new authenticity API, parent-containment rule or broad Unicode redesign. Ready for independent R15.1 diff review; original failures are not erased.

Changed/new files against original snapshot:

- REPORT.md
- SPEC.md
- compact.py
- fixtures/expanded.json
- fixtures/long_disjoint1-graph.json
- fixtures/long_disjoint16-graph.json
- fixtures/long_disjoint8-graph.json
- fixtures/long_shared64-graph.json
- fixtures/long_shared8-graph.json
- fixtures/positive.json
- fixtures/semantic-negatives.json
- offline-request.json
- original-hardening-evidence.json
- pre-fix-test-output.txt
- provenance.json
- schema.json
- span-table.json
- stage-a.system.txt
- test-output.txt
- test_hardening.py
