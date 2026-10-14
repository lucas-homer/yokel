# R18 design selection

Reuse `round17-paid-comparison/design-r3-1-paccept/` byte-for-byte, including its
original fixture/check pair, scoring rules, thresholds and P-ACCEPT evidence.
The adapter design-freeze gate excludes the separately pinned recon artifact,
so a changed design copy is unnecessary. R18 recon is an A6 runtime amendment;
the original recon stays in the design fixtures for historical gate evidence.

`amendments/A5-A6.md` is normative: A5 changes both prompts only; A6 records
machine-checked U0 at INIT. Account usage is U0 plus cumulative reported costs;
run accounting retains conservative debits and excludes U0. R17's dedicated-key
attestation remains historical evidence; A6 authorizes reuse for R18. No fresh
key state or review acceptance is asserted by this implementation.

Namespace `r18.paid-rerun.v1`; scope
`docketclock-research-r18-authorized-20261014`. Three fresh OPQ calls; no FULL,
no retry, no repaired R17 scoring. FLOOR 270000000, OPERATING 1800000000,
CAP 2000000000 nanoUSD; user's accepted $3 tolerance remains evidence.
