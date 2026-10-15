# A6 recon revision

Minimal copy of R17 recon-a4/r17recon.py. key_limit_ok subtracts optional U0
from available capacity while retaining KEY_MAX. reconcile compares observed
absolute usage with U0 plus cumulative reported cost. close_debit subtracts
INIT's U0 from highest absolute usage before retaining excess run cost.

Zero-baseline compatibility is retained for frozen ledger fixtures. Schedules,
tolerance, FLOOR, OPERATING, debit/admission/no-retry and halt rules are fixed.
Exact diff is `../_out/recon.diff`; original fixture engine is never edited.
