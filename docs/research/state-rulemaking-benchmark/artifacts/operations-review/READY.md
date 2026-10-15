# Operations audit preparation

Status: final audit completed after the primary's run-complete notice. See `FINAL-REPORT.md` and `final-review.json`: 151 of 152 checks pass, with the recovery-1 timestamp-based stop finding retained. Earlier preparation text below remains historical. This is an operations and reproducibility review, with no extraction scoring or new vendor calls.

The primary-provided freeze digest is `900f21e8a75d50444f12a0e3814d665a4f401a0d689194465d0b00467a762946`. All 141 frozen files match their declared hashes and byte counts. The 20 inputs have distinct hashes and total 34 page instances. The shared parser-input list matches the freeze. Llama's plan contains 20 matching inputs for each of agentic and agentic_plus; Firecrawl plans the same 20 inputs.

The preparation snapshot found a Firecrawl preflight schema mismatch: `verify_freeze.py` expects a passing `corpus.fixtures` object, while the immutable manifest supplies top-level `units`, `files`, and `counts`. This is a static preparation finding, not evidence that a vendor call failed. The final review will assess the execution lane's actual corrected code and receipts without changing frozen files.

## Artifacts

- `audit-schema.json`: report contract, evidence categories, statuses, and final checklist.
- `audit.py`: offline preparation verifier and final artifact inventory helper. Its `complete` command produces a preflight inventory only; provider-specific final checks still require receipt inspection and a final report.
- `preparation.json`: timestamped preparation findings and limitations.
- `expected-inputs.json`: expected fixture IDs, hashes, byte counts, and page counts for final receipt matching.

## Final review after the completion notice

1. Recheck the immutable manifest and all frozen files.
2. Match upload receipts and parse requests to the expected 20 input hashes in each arm; account separately for skipped or failed calls.
3. Compare actual settings to the plans, including full bounded input, requested versions, tier, page limits, and absence of hints.
4. Verify response and derived text integrity. Distinguish preserved JSON tool response objects from HTTP transport bytes, sanitized upload envelopes, and any explicitly sanitized parse response exceptions. Compare derived text byte-for-byte with its source response strings.
5. Extract actual returned usage, reported backend versions, and request IDs where present. Keep published price assumptions separate from actual usage and costs. Identify unavailable measurements explicitly.
6. Reconstruct start/end intervals and completion order. Verify the global maximum of two concurrent pipelines/calls under the lane's declared scope, and that three consecutive failures in completion order stop new dispatches while already-running calls may finish.
7. Check artifact handling for sensitive fields without copying their values. Report only the artifact path, JSON field path, and category when a finding exists.

Unfinished calls are pending until the primary supplies the run-complete notice. No repeated polling is required. Final conclusions must identify any evidence gaps rather than infer success or failure from absence.

## Authorized execution amendment

The primary notified this reviewer that the Firecrawl preflight was corrected and passed before submissions. A local stdin transport failure then affected A01-A04 before HTTP upload or final parse, and the original phase stopped. `execution-amendment-1.json` authorizes a new recovery directory with one corrected pre-job recovery for each affected input, first attempts for the remaining inputs, unchanged corpus/settings, and a fresh failure counter for the repaired phase. These statements remain subject to final artifact verification.

`amendment-1-acknowledgment.json` records the amendment digest and added checks. Review original and recovery phases separately, preserve the original failure-stop history, include setup overhead, and distinguish local transport failures from vendor availability and content results. The historical preparation mismatch remains in `preparation.json`; corrected final preflight evidence will determine the final finding.

## Rate-limit clarification and Llama status

The primary supplied `execution-note-2.json` and separately identified final-endpoint rate rejections for A05/A06/B01/B02 and setup-stage rejections for B03/B04. The notice authorizes paced continuation for never-submitted B05-B10 followed by one separate recovery for each of those six explicit pre-job rejections. Both setup and final requests count against the observed ten-per-minute budget. Original stops and attempts remain evidence; timeout or unknown-acceptance calls must not be retried.

`execution-note-2-acknowledgment.json` records the note digest, the distinct primary notice, and added checks. Verify the first sweep, paced continuation, and rate recovery separately, including rejection evidence, request pacing, and recovery counts. The primary also reports that Llama settled with four actual timeouts, zero parse outputs, and 36 unattempted calls. Read-only dashboard recovery awaits user sign-in; any retrieved artifacts must be distinguished from new parse jobs. These operational statements remain pending final verification.
