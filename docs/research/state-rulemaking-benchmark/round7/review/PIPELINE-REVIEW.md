# R7 pipeline-only implementation review

Reviewed 2026-10-09 against approved spec SHA-256 `cfc6e8847637c3333fcd994649a6349471585d2fd5efb54952b6d75014324406`. Runtime/protocol and the final replay are still outside this review. **One bounded prompt-alignment fix is required; no structural/evidence enforcement blocker reproduced.**

## Finding

**P2 — Add the specified consideration-policy disclosure guidance to the generated inventory and both verifier requests.** `pipeline.py` lines 298–300, 319–320 and 366 retain the R6 public-posting/publication/confidentiality guidance but never identify consideration policies as separately typed disclosures where supported. SPEC.md line 37 explicitly requires this distinction, grounded in the two R6 consideration-policy classification mismatches. The shipped requests still provide no guidance resolving that observed ambiguity; broad “disclosure” wording is the same boundary that failed in R6. This is a prompt-contract omission, not a claim that future models will necessarily misclassify it.

The public `inventory_request`, `verification_request` and `jev_question_specs` outputs were inspected; all omit consideration-policy classification guidance. Add a short source-qualified instruction to inventory, stronger and the relevant Jev dimension(s), without automatically forcing modality or class in assembly, and verify the resulting public request strings. Recompute admission on the changed final bodies in the runtime review. No schema redesign or new classifier is requested.

## Verified enforcement

- Existing `test_pipeline` suite: **4/4 pass**, using bundled Python with `PYTHONDONTWRITEBYTECODE=1`.
- **14 independent narrow negative controls passed** through public APIs: empty/absent component evidence; empty literal; false exact quote; zero occurrence; component/group ID collision; duplicate group members; dangling group route; dangling group requirement; role-purpose mismatch; cross-event member; arbitrary display; missing group assessment; missing component assessment.
- Positive grouped phone/email fixture assembles, retains actual information-contact roles and exact components, and validates a full synthetic stronger verdict.
- Code inspection confirms groups/components participate in `all_items`, global uniqueness and the unchanged 200-item cap; record schemas preserve resolved spans; source/evidence and assembled-envelope checks remain strict; group uncertainty becomes a review reason. Relationship meaning and completeness remain semantic claims, as approved, rather than being falsely proven by exact spans.

Command for existing tests (run from `round7/pipeline`):

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m unittest -v test_pipeline
```

Negative controls were an in-memory, standard-library-only script importing `pipeline` and `development_fixtures`: construct a valid hearing/help two-route group, mutate one field per control, require `assemble(...).validation.valid == false`; then remove group/component assessments separately from a full synthetic verdict and require `validate_verdict(...).valid == false`. No implementation files, providers or credentials were used or modified.

Full runtime/evaluator compatibility, final request-size counters, zero-dispatch routing, semantic omission controls, and the 967-file baseline comparison remain for the integrated review. This report does not approve those unfinished parts.
