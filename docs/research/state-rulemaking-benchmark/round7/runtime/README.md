# Offline runtime compatibility

`run_pipeline.py` is a thin synthetic integration harness, with no live runner, POST function, credential resolver, authorization file or resume ledger. `simulate(source, inventory_fixture, synthetic_transport)` requires an explicit transport and checks its inventory reply against the declared development fixture. Its source-first request carries no record/labels. The transport must return that inventory for stage inventory, five valid pass/fail/uncertain dimensions for Jev, and the R7 generative verdict for stronger. All dispatches in receipts are synthetic, not provider calls. Exceptions retain only their class, never arbitrary exception text; provider_service_error stays false because no real service evidence exists.

`requests` creates exact final model-specific bodies. `admission` measures actual serialized UTF-8 bytes plus the frozen 1024 allowance and enforces the unchanged OR=35000, Jev-total=64000, state+longest=32000 caps. The estimate is a conservative internal heuristic, not measured provider token acceptance. Source native-codepoint=30000 and PDF-page=40 caps reject before synthetic dispatch. Both verifier bodies admit before either arm dispatches. Record/payload hashes remain available after a verifier-size rejection. Model/provider/completion/call/budget constants are preserved from R6; no real call, invoice, cost, cohort collection or fresh validation is authorized.

Observation gate table:

| Gate | Artifacts | Arms |
| --- | --- | --- |
| source_review / inventory_failed | no inventory/record/payload | both not_started, called false |
| request_size_review at inventory | no inventory/record/payload | both not_started |
| assembly_review | inventory, no record/payload | both not_started |
| request_size_review at verifiers | inventory/record/payload | both not_started |
| paired_verification_completed | all hashes | both called; accepted_complete or review |
| verification_failed at Jev | all hashes | Jev failed; stronger not_started |
| verification_failed at stronger | all hashes | Jev accepted/review retained; stronger failed |

`source_coverage_complete` means the full source question/assessment schedule was validated, including negative judgments. Invalid stronger assessment coverage makes it false. Each called accepted/review arm retains its judgment. Outer status must agree with all five dimensions, validation errors, deterministic review reasons and shadow decision. Favorable dimensions do not erase unresolved extraction. The direct observation adapter preserves these fields rather than repairing statuses. All outputs remain action_ready=false and production_eligible=false.

Mechanical request/response functions are adapted into this directory from frozen R6 `provider_adapters.py`; the local encoding/strict JSON helpers are bounded equivalents. R7 changes only schema namespace and adds offline construction/admission receipts. Origin file hashes are retained in the development manifest inputs. No R6 runtime module is imported or mutated.
