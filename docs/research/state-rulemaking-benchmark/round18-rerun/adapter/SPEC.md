# Adapter r1.5

Copy of R17 adapter-r1-4. Namespace r18.paid-rerun.v1; new wire/recon pins.
Frozen source metadata retains its old wire provenance, while the active wire
is pinned independently through R18 wire READY. Host source lookup uses frozen
R17 sources; native shim loads R18 adapter/host_driver.py. A3 timeout 600 s,
shim 1740 s and native 1800 s remain unchanged.

A6 sites: release_gate init_constants checks integer U0 >= 0 and all-call
capacity after U0; K3 requires usage == U0 and remaining == limit - U0;
last_usage starts at U0; pre_key_usage compares to U0 + reported_sum; poll pins
U0 for reconciliation; close excludes baseline through recon.close_debit.
Conservative debits, FLOOR/OPERATING, all-remaining-call admission, no retry,
HALT and drop-in-usage semantics are retained.

Prior offline suites are adapted, plus test_a6.py's nonzero admission, 3-cell
walk at U0=59408500, regressions, unexplained spend, K3 mismatches and capacity.
No actual provider or credential access is part of these tests.
