# Review finding — resolved

Resolved P2: `runtime/operations.py:raw_reported_cost` catches ValueError/TypeError/AttributeError, but the module's strict `j.loads` raises its own RuntimeError-derived Stop for duplicate JSON keys and nonfinite constants. After `operation()` records invalid_response_or_usage, `ledger.totals()` re-parses the raw body and raises Stop again. The runner uses totals to emit its terminal snapshot, so this malformed-response class cannot complete the intended failure reporting. `run_pipeline.py:ledger_raw_reported` repeats the same exception mismatch.

Reproduced with synthetic HTTP200 bodies `{"usage":{"cost":1,"cost":2}}` and `{"usage":{"cost":NaN}}`: operation rejects and latches correctly; a subsequent totals() raises Stop `duplicate JSON key` or `nonfinite JSON`. No providers/credentials or old writes.

The raw-cost reader should treat strict-JSON rejection as unavailable raw cost while retaining the full reservation and failed state; it must not salvage an ambiguous cost or create a result/judgment. Add focused malformed-native-cost controls. This is independent of the still-in-progress stronger-only runner conversion. Reviewer owns no implementation edits.

Resolution verified: both raw-cost readers now catch the strict Stop exception. Independent full-run cases for duplicate keys, NaN, Infinity, null usage and invalid JSON retain the failed response/reservation, report zero recoverable cost operations, and emit truthful failure observations. The combined suite passed 24 controls. Final stopped handoff reconciled; all 24 controls passed and hashes bound in FINAL-REVIEW.json.
