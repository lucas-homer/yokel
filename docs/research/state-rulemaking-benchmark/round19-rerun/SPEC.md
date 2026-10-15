# R19 offline implementation

Owned scope is this directory only. `amendments/A7.md` is normative and untouched.
`implement_offline.py` records the complete frozen R14–R18 SHA256 inventory before
copying R18's pinned offline payloads. Historical live proposals/logs are excluded.

Wire r16.w2.3 / envelope r16.e4 adds exactly A7 plus newline after A5, only for
opaque. The full prompt is byte-identical to R18. Schema, codec, validator,
cardinality, guards and dependency pins are unchanged. Adapter r1.6 changes only
active paths, wire pin and namespace; A6 accounting is unchanged. Recon is loaded
directly from frozen R18 by its old pin. Keycheck v3 executable is byte-identical.
Release preparation preserves the R17 P-ACCEPT design, sources, reference/gate/
scoring evidence and normalized historical CAP-ACCEPTANCE; A7 enters its pin closure.

Run `python3 -I -S -B offline_tests.py` and the same command with
`/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12`;
then `python3 -I -S -B pin_ready.py` and `python3 -I -S -B pin_ready.py --verify`.
These are local tests/hashing only, using synthetic transports/environments.
No network, provider, credential, native runner, signing or release command runs.

READY means offline implementation only. Fresh keycheck/U0, independent review,
primary acceptance, bootstrap evidence and release remain primary-owned work.
Component receipts, R18 diffs/hunk summary and six request sizes are under `_out/`.
