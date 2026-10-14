# Primary review: R17 zero-cost key-metadata job (keycheck.py)

Reviewer: primary (claudeAgent/claude-opus-5-5), 2026-10-14. Accepted for one signed, zero-reservation run.

Verified by reading keycheck.py and running test_keycheck.py under the runner interpreter (python3.12 -I -S -B: OK, 17 tests):
- The only transport is one `HTTPSConnection('openrouter.ai').request('GET', '/api/v1/key')`. There is no POST, no completions path, no redirect following and no retry.
- TLS uses the explicit cafile=/etc/ssl/cert.pem, shared with the reviewed host driver.
- OPENROUTER_API_KEY is popped from the environment inside the call, validated as printable ASCII, used only in the Authorization header, and deleted in `finally`. Failures re-raise a key-free `Rejected('metadata_failed')` outside the handler.
- The output is allowlisted fields only (label, limit, limit_remaining, limit_reset, usage, usage_*, is_free_tier), parsed as Decimals. Refusal if the key string appears in the raw body or the encoded fields.
- Expected values: label DocketClock, limit 50, limit_remaining 50, limit_reset null, usage 0. status=PASS only if all hold; accepted_by_primary is false in the machine record by design.
- The bootstrap timing record states its own gap (no native start time exposed); the outer run boundaries are captured by the primary wrapper.

Scope: new R17 ledger namespace (user-approved $2.00 cap, P-ACCEPT, amendment A4). Reservation 0; this job makes no completion call.
