# Keycheck v3

Copy of R17 keycheck-job-v2. Future PASS requires plain DocketClock or the
existing accepted masked-label shape, exact USD limit 50, null limit_reset,
finite non-negative usage, and limit_remaining == limit - usage. Missing
remaining is computed exactly; omitted reset retains the v2 null convention.

Usage is recorded as key_initial_usage_candidate_usd and its ceil-nanoUSD
candidate. Primary must confirm fresh machine evidence and normalize usage to
integer U0 and remaining to key_limit - U0. No primary acceptance is fabricated.
Masked fragments remain omitted and their name-verification limitation remains
recorded. Sanitized diagnostics, no retry, GET timeout and native grammar stay.
