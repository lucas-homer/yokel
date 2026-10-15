# Final bounded Fable R15.1 hardening review

**No material defect found in the reviewed diff.** Requested fable/high, actual claude-fable-5-1, provider firstParty, successful fresh isolated Claude.ai Max result. Fable reviewed only the graph-walk/inverse-copy diffs, test_hardening.py, concise contract context and supplied31-test evidence. It did not inspect or execute the full implementation. Raw opinion remains unedited in review-result.json.

## Outcome and independent verification

The enter/exit LIFO traversal preserves ancestor-cycle detection, dangling checks, shared-node memoization and complete postorder depth. Reversed child scheduling retains original traversal/error precedence. Shared DAGs and leaf-first/root-first ordering produce the same longest-path result. The399-chain now rejects controlled graph_depth at recursion limits1000 and600, and the399-cycle rejects node_cycle at600. Inverse deep copies detach d/b/a from expanded input in both mutation directions. Targeted tests use exact error codes for deadline_uncertainty and applicability_links rather than the formerly masking failures.

Codex independently ran the actual frozen isolated suite:31/31 passed, exit0, bundled Python -I -S -B. Raw receipt is host-test-output.txt. This verifies test/helper-dependent cases which Fable could only accept from the supplied execution evidence. All37 original and40 revised protocol pins remain unchanged; revised READY equals primary's dd2bb510254e198589ed50caa6f9a171194a0971c11ae92bde996006267f1f50. No edits to either protocol were made by this child.

## Limits and nonmaterial observations

Fable flagged a redundant dangling check on exit frames (harmless), and noted the explicit label bumps VERSION r15.1, SPAN_VERSION r15.spans.2, EXPANDED_VERSION round15.expanded-inventory.v2. Codex verified these labels against the frozen code. They version new wire/table/expansion bindings without altering condition semantics or field shapes. No automatic legacy conversion follows.

Pre-traversal IDs/arities/link closure, inverse_evidence freshness and unchanged unit dependency traversal were outside Fable's bounded diff. The31-test suite covers relevant cases but is not comprehensive proof. Unit d remains recursive and bounded159 levels; this review does not claim to have hardened every possible caller-stack path. Provider tuple-schema/runtime compatibility remains unresolved; no provider/runtime code or call was supplied/performed. Structural validation still cannot detect omitted clauses, scope/role/connective mistakes or shorter semantically incomplete graphs. No completeness, output-fit, legal correctness, measured model gain or live approval claim.

## Provenance and route

Fresh session1b4d00f1-2aa2-4fa5-8ff5-3660b96b08bf, neutral cwd /private/tmp/r15-fable-revised-review.WGeHdS. Max authentication probe succeeded. Official advisory wrapper, empty built-in tools, safe-mode and strict empty MCP; bridge does not expose initialization tool inventory. Claude made no edits and ran no tests; Codex wrote artifacts and executed validation. Claude.ai Max subscription bridge only, never OpenRouterClaude/API fallback. No credentials, prior internal reports, source-reference labels, real source, runtime/signing code, paid API experiments or installs. Raw list-price metadata is not evidence of incremental subscription charges.
