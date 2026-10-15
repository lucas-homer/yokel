# R18 keycheck v3

Offline copy of keycheck-job-v2. Future primary-owned metadata job uses the same
fixed GET, TLS/diagnostic rules, timeout and native grammar. PASS accepts a
masked or DocketClock label, $50 limit, null reset and any finite usage >= 0,
with exact remaining = limit - usage. Record the USD and ceil-nanoUSD U0
candidate; retain masked-name limitations and primary acceptance=false.

Prepare only unsigned proposals with make_keycheck_proposal.py using a fresh
reviewed stage containing adapter.py (keycheck.py bytes) and accepted REVIEW.md.
Use scope docketclock-research-r18-authorized-20261014, fresh expiry and the
existing authorized native credential route; do not include credential values.
Primary owns review/sign/check/run and baseline acceptance. No such command
was executed by this offline implementation. See ../release-prep/README.md.

Tests: python3 -I -S -B -m unittest discover -s <this-folder> -p 'test_*.py' -v.
Pin and verify through ../pin_ready.py after both interpreter suites pass.
