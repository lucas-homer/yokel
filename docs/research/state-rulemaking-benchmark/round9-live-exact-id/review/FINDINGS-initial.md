# Initial finding on the in-progress candidate

P2 — Failed provider responses omit conservative cost accounting. Reproduced against adapter.py SHA `7e6a3e39a9f1a912d22439f3cb3dd4a3e2116401a0b7e1bebbcd417038616374` (owner has not yet frozen READY). Synthetic HTTP 400 with strict native JSON `usage.cost: 3.0` yields retained request/intent/response/status/stop, but no recovered-cost/cumulative-debit receipt. The durable intent reserves 161920000 nanodollars, while the known reported cost requires a 3000000000 new debit and 3696390718 cumulative debit. The same gap is reachable when native/inner response parsing fails before a result is written.

The single-use run directory does prevent another dispatch. This finding concerns truthful conservative carry-forward and failure reporting, not an immediate automatic retry. Preserve exact raw bytes; independently recover only unambiguous finite nonnegative native cost even on HTTP/parser failure; persist max(reservation, recoverable cost) and cumulative debit/overrun without promoting a verdict. Malformed/ambiguous costs must retain at least reservation and explicitly remain unavailable.

Evidence: early_failure_probe.py and early-failure-probe.json. Zero network calls or credentials used. Final review still awaits owner READY and tests against stopped bytes.
