# A4 recon authority

This is an exact copy of design-r3-1/fixtures/r17recon.py with ONLY
`KEY_MAX = 1_730_000_000` replaced by `KEY_MAX = 50_000_000_000`.
_out/recon.diff proves one removed line and one added line. The original
file, frozen check.py, cases and design freezes are unchanged. The original
checker remains runnable with its original engine.

SHA-256: 8c98fabdc73fad10336698fa695869966a631d5a7d99b797725f2c711b1b6bb0.
FLOOR, OPERATING, CAP, admission, reconciliation and debit are byte-identical.
The sole changed L-fixture outcome is L18: a $1.74 six-call key passes KEY_MAX.
