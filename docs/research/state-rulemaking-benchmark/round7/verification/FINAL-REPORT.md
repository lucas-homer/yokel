# Final independent Round 7 verification

Outcome: PASS, 18 independent test methods with authored subcontrols. The 8 pipeline and 10 runtime/evaluator methods passed the actual commands below after owner fixes. No remaining observed control failures. Only verification/ artifacts were authored by this child.

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 docs/research/state-rulemaking-benchmark/round7/verification/test_pipeline_independent.py
PYTHONDONTWRITEBYTECODE=1 /Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 docs/research/state-rulemaking-benchmark/round7/verification/test_runtime_independent.py
```

| Controls | Expected and observed |
| --- | --- |
| Date grammar and values | Four weekday controls normalize to independently authored ISO values; wrong weekday, bad day, missing year, numeric ambiguity, prose/clock suffix, invented value reject whole record. |
| Components, selectors and envelope | Invented/altered/ambiguous components, extra display, empty components, ID collision and mutated envelope reject before request creation. |
| Groups and item cap | Dangling/nonreciprocal/singleton/duplicate/mixed-role/cross-event/missing-evidence groups reject; uncertain binding remains review; 200 items admit and 201 reject counting components. |
| Stronger coverage | Explicit authored component and group IDs require assessments; missing either rejects. |
| Semantic boundary | Structural assembly preserves unverified semantics; independent omission/mismatch mappings veto useful complete acceptance under favorable mock responses. |
| Final request identity | Same full source+record payload across arms; receipts match exact body bytes/hash and source hash. |
| Request caps | Independent inventory and stronger 35000-byte-estimate boundaries, Jev total 64000 and state+longest 32000 tested below/at/over. Below/at admit; over rejects without limit changes. |
| Dispatch gates | Source and inventory rejection produce zero transport calls; assembly/verifier rejection produce inventory-only calls. A valid assembled verifier-size rejection retains record/payload hashes and blocks both arms. |
| Negative/failed judgments | Full validated question/assessment schedule sets coverage true even with negative dimensions. Actual synthetic failure is called; later arm remains uncalled. |
| Forged observations | False called flag, unequal hashes, accepted pre-gate, false coverage, missing inventory, favorable status with negative dimension, missing/extra/wrong-arm judgment reject. |
| Reported evaluator bugs | Failed arm under completed-pair gate and stronger called after Jev failed both reject on final run; retained independent regressions first failed before owner repair. |
| Numeric/page boundary fixes | Valid floating/integer costs accepted, negative costs reject; 40 pages pass admission and 41 gate before any synthetic dispatch. |
| Missing observations | Scheduled denominator remains one; absent row stays unserved, missing count one, no invented runtime gate; zero-acceptance ratios and costs remain null. |
| Frozen lineage | Exact file set and SHA-256 content match the 3487-file prior-round baseline. R6 inventory discriminator rejects. |

All controls use explicitly authored source/expectation/mapping and synthetic transport responses; no owner fixture module is imported. Python audit hooks block network/process dispatch and credential-like file reads during controls. Provider calls: zero. No dependency installation, builds or fresh collection. Request receipts are retained in runtime-results.json; final-results.json lists exact checked code/artifact hashes and commands.

The owner development replay was not rerun by this child because it writes owner artifacts. These separate independent end-to-end controls supplement its replay. Synthetic results demonstrate internal admission/routing and runtime/evaluator compatibility only; they do not establish provider context acceptance, new extraction recall, real notice completeness, human-gold accuracy or comparative verifier performance. Independent authored audit mappings are development controls, not an unseen source cohort.
