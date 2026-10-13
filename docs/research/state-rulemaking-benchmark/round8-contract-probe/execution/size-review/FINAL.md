# Final size-analysis reconciliation

2026-10-11. **PASS for the final offline diagnosis and candidate recommendation.**
Owner READY states edits stopped. All eight artifact hashes/sizes in HANDOFF.json
match current files; all 25 original Freeze E entries remain hash/size matched.
No material blocker to freezing these diagnostic artifacts. This final receipt
supplements REVIEW.md and grants no live/provider/schema/runtime authorization.

Final hashes:

- `analyze.py`: `73bc13bee5615c294bc5ecf21a86c4f730708c1e7b1cefd783391b46a6484104`.
- `REPORT.json`: `dd2f6c85f0e6a7efca8e24731a9070b66fb80166318763a82f5ac8903a27490e`.
- `HANDOFF.json`: `459ca29ed19f3edae5839fec2a5f69bc24055632b77e3d8f832efb08f44bd294`.

The analyzer/report hashes already match the earlier reviewed hashes: owner additions
were present by the earlier hash capture. Independently rechecked final bytes anyway,
without executing the owner's artifact-writing program. AST-extracted pure functions
passed 31 assertion groups. Owner report contains 11 passing controls. All three
saved diagnostic wires exactly match independently generated wires, restore original
canonical payload/full-request bytes, and reproduce all reported body measurements.
Repeated quotes at distinct offsets, astral/combining Unicode, duplicate uses, retained
event/route/group associations, invalid reference types/bounds and quote tampering
were checked again.

A valid-index reference swap remains syntactically decodable but changes the restored
canonical payload hash. Detection requires comparing that restored hash with the
independently pinned original; the decoder alone does not establish semantic identity.
The final candidate correctly requires this check, unchanged record validation and
both exact body admissions. Its future requirements are not implemented live here.

The quote-and-offset table still saves **2817 Jev body bytes / 4798 stronger body
bytes**, with decoder instructions included. Jev state-plus-longest is 28708 against
32000; stronger estimate is 35755 against 40000. Exact quotes and offsets are explicit,
avoiding model codepoint reconstruction. Table-reference comprehension remains
unmeasured. All preservation claims here refer to canonical JSON bytes, not arbitrary
serialization whitespace. Provider compatibility and model correctness remain untested.

Candidate budget arithmetic independently matched: prior conservative debit $0.428936;
at most two new verifier operations, zero inventory; guard maximum new reservation
$0.123648 and aggregate $0.552584. Current exact table bodies imply nominal reservation
$0.114057054. These retain the prior debit, use existing byte-based estimates/prices,
and do not establish actual provider tokens, invoices or authorization. Candidate
metadata explicitly records `authorized: false`.

Recommend the explicit-quote table for separate contract review and a separately
authorized measured pair, with unchanged source/record/evidence/associations and
independent semantic audit. No guard increase, new extraction, runner implementation,
retry or live experiment is approved by this diagnostic review.

Changed only this new size-review receipt. No owner/old/frozen artifacts were written,
no original analyze.py execution, credentials, provider/network calls or live changes.
