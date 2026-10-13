# R8 final independent runtime/protocol review

**Approved for primary precollection freeze. No remaining blocking findings in the reviewed code.** This supersedes the two open findings in RUNTIME-EARLY-REVIEW.md. Collection, image labeling, native-job preparation and paid release remain primary's distinct preregistered gates; this is not a substitute for frozen source/label bindings or live authorization.

The reviewed runtime preserves valid completed extraction and verifier judgments when a response-reported cost trips the after-call budget guard. Independent inventory and stronger-overrun controls retain those results, emit postresponse_budget_stop with the exact ledger receipt, leave the next scheduled notice not_started, and refuse another POST/resume while the budget latch remains. The $2 guard remains conservative reservation/stop accounting, not an invoice guarantee.

The observation validator now loads and validates before any operation intent. Independent forced validator unavailability produces zero synthetic dispatch. All read-only protocol dependencies are included transitively in implementation pins; the fixed allowlist excludes READY, mutable reports and its own generated implementation file. Stable repeated pin generation was checked.

Receipt verification resolves the exact evidence hash and operation identity, verifies retained request/pins and status/response/cause bindings, and reparses completed budget-stop responses against retained results and total charge. Independent edits to referenced stop bytes, request bytes, receipt hash and operation identity all reject. Legitimate uncertain calls and safe partial progress remain distinct from confirmed HTTP errors and completed judgments.

## Validation evidence

- **23 tests pass:** 12 runtime, 3 fixed service-adapter and 8 protocol tests.
- **5 independent controls pass:** inventory overrun preservation/global stop; stronger overrun preservation/global stop; unavailable validator zero dispatch; complete/stable transitive pins; four receipt/ledger tamper cases.
- **27 exact code/interface/dependency hashes unchanged during verification**, recorded in [FINAL-VERIFICATION.json](FINAL-VERIFICATION.json).
- **967/967 prior baseline hashes match**, with no mismatches.
- Guarded execution used a Python audit hook blocking sockets, subprocesses and credential-file access; all transports and PDF/native inputs were synthetic. No provider calls, fresh source reading or credential reads occurred.

Reproduction: run `final_verify.py` in this review directory with the bundled Python and PYTHONDONTWRITEBYTECODE=1. It writes only review evidence; [final-test-output.txt](final-test-output.txt) retains the detailed test output. The reviewer changed no runtime, service-account or prior-round implementation files.

The fixed native adapter's check path remains free of credential access, imports only after reviewed input bindings, and refuses reuse of a prior run/intent. Actual environment enrollment/build/credential injection, source/image-label freeze timing, fresh-source quality, provider admission and model accuracy are outside this offline approval. Primary can freeze the exact reviewed code and proceed to the next authorized collection gate.
