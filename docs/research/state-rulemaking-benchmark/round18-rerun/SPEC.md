# R18 offline implementation

Owned scope is this directory only. Frozen R16/R17 inputs are copied or reused,
never modified. `implement_offline.py` records their complete SHA256 inventory
before copying. Generated historical proposals/logs are not current R18 evidence.

Wire r16.w2.2 / request envelope r16.e3 changes only A5 prompt text and version
labels. Response r16.w1, schema, codec, r15.1 validator and cardinality are fixed.
Adapter r1.5 and recon apply A6's non-negative integer nanoUSD baseline U0;
keycheck v3 records its candidate without asserting primary acceptance.
Release preparation reuses the P-ACCEPT design and frozen R17 gates/sources.

Run `python3 -I -S -B offline_tests.py` with each authorized interpreter; then
`python3 -I -S -B pin_ready.py` and `python3 -I -S -B pin_ready.py --verify`.
These commands perform local tests and hashing only. Tests inject synthetic
transports/environments; no actual credentials, native tools, provider or
network calls. Logs and test counts are under each folder's `_out/`.

READY means offline implementation only. Fresh keycheck, machine baseline,
independent review, bootstrap evidence and primary release remain outstanding.
