# R19 design selection

Reuse frozen `round17-paid-comparison/design-r3-1-paccept/`, references, fixture
gates, scoring manifest and CAP-ACCEPTANCE exactly as R18 did. A5/A6 are retained
verbatim; A7 changes only opaque prompt guidance. No historical paid output is
re-scored. S1 alone is weak evidence: uninspected S2/S3 carry generalization weight.
Call order, futility rule, thresholds and outcomes remain fixed.

Reuse `round18-rerun/recon/r17recon.py` directly at SHA256
`64794fdda2f345559a5399ccd8e83142a93e621fcb5c6e79842209a4d4c27140`.
The R19 staging closure includes that file and its original READY. Fresh keycheck
must measure integer U0; no candidate or expected amount is primary acceptance.

Namespace `r19.paid-rerun.v1`; scope
`docketclock-research-r19-authorized-20261014`. Three fresh OPQ cells S1/S2/S3 =
26-19-039/041/106; no FULL, no retry. FLOOR 270000000, OPERATING 1800000000,
CAP 2000000000 nanoUSD; the existing accepted $3 tolerance remains evidence.
