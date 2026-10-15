# Expanded LlamaParse execution: stopped by protocol

All 20 frozen inputs were validated: 34 physical pages per tier, matching SHA256s and byte lengths, normal PDF headers, and frozen manifest SHA256 900f21e8a75d50444f12a0e3814d665a4f401a0d689194465d0b00467a762946. No reference answers were read and no custom parsing hints were supplied.

A01 and A02 were each uploaded once from exact retained local bytes. Both agentic/latest and agentic_plus/latest were submitted for each, using markdown=true and no page filter. All four connector calls returned MCP request timed out. The third consecutive timeout (A02 agentic) latched the provider stop; its already-running agentic_plus partner was allowed to settle and also timed out. No A03 or later uploads/jobs were launched; no retries occurred.

Operations: 4 attempted of 40 planned calls, 0 returned parse results, 4 timeout/backend-unknown outcomes, 36 unattempted because the provider stopped. The maximum observed active call count was two. Failure elapsed times are retained individually; no successful latency statistics exist. Backend completion, job IDs, resolved released versions and actual usage/cost are unknown. These are connector operational outcomes, not judgments that document parsing was inaccurate.

The plugin exposes no parse-job status/result retrieval operation. Any later recovery by the primary must remain a separately attributed recovery with explicit file/job mapping, preserving these original timeout records and the planned denominator. No new credentials, purchases, indexes, extraction calls or additional tiers were used.

Each runs/fixture/tier folder contains immutable tool-envelope.json and capture.json, plus exact response-text-00.txt error text without an added newline. uploads retains returned file IDs and sanitized acquisition records; no signed bearer URL is stored. execution-plan.json retains 40 planned calls; call-ledger.json distinguishes attempted timeout from unattempted stopped entries. operations.json and artifact-hashes.json summarize execution and retained artifacts.

Run python3 verify_captures.py offline to recheck raw-envelope equality, frozen input metadata pairing, uploaded file IDs, completion order, concurrency and stop rules. Existing captured inputs are referenced by hash; result verification does not contact a vendor or need the source PDF paths. harness.py status reports the latched stop. All validation passed.
