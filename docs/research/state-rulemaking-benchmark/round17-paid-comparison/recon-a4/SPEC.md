# recon-a4 — A4 / r1.4 delta

Only KEY_MAX changes from $1.73 to $50.00. NOTE.md and _out/recon.diff record
the byte-exact proof. Non-resetting/zero-initial-usage/label evidence remains
adapter-enforced. No function changes. FLOOR $0.27, OPERATING $1.80 and CAP
$2.00 remain unchanged. Original full check.py fixtures are validated without
repointing or writing them. The adapter's test_a4.py compares all 25 unchanged
ledger cases; only L18 changes, False -> True for a $1.74/six-call key.

Run `<python> -I -S -B recon-a4/test_recon.py` on each required interpreter.
Three tests verify exact one-line bytes, all original fixture categories, and
unchanged constants. See READY.json and _out/{system,python312}-tests.txt.
Final all-folder pin verification: adapter-r1-4/verify_ready.py.
