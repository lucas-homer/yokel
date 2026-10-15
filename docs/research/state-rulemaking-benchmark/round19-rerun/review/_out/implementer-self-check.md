# R19 implementation audit against frozen R18 — 2026-10-14

Implementation self-check only; this is not independent or primary-accepted
paid-path review evidence. No live keycheck, release, signing, runner, provider,
network, credential or signing-key access occurred. No commit was made.

Both R18 interpreters pass with `-I -S -B`: system Python 3.13.7 and Codex
runtime Python 3.12.14. Counts per interpreter: wire 104, recon 3, adapter 214,
keycheck 46, release-prep 23; total 390 versus R18's 383 (+7). The inherited
independent wire suite remains accepted at 54/55 with exactly its one historical
source-envelope assertion failure. Logs are in each component's `_out/`.

Wire has three hunks: revision/envelope docstring, version constants, conditional
A7 append after A5. An exact source-transformation test permits no other change.
A7 is copied verbatim from the untouched normative amendment and ends in newline.
Opaque prompt delta is 329 UTF-8 bytes, or 330 bytes after JSON encoding; full
prompt and full request bodies are byte-identical to R18. Tests build all three
pinned sources-r2 under both profiles and compare all other body fields/table.

Body / guarded sizes (guard adds 1024; limit 40000), opaque then full:
- S1 26-19-039: 20382 / 21406; 19867 / 20891.
- S2 26-19-041: 21676 / 22700; 21161 / 22185.
- S3 26-19-106: 20108 / 21132; 19593 / 20617.

Adapter r1.6 has only root/namespace/wire-pin changes. R17 sources-r2 upstream
wire check remains untouched. Exact source-transformation proof covers the entire
adapter. Synthetic R18 namespace ledger/release pairing is refused before key
reads, POST, RESERVE or attempt creation; an R18 release INIT hash cannot bind a
R19 ledger, even after updating the BIND release hash. Ledger bytes remain intact.
All inherited A6 tests remain unchanged and pass.

Decisions: reference R18 recon directly with its original engine/READY pins;
R19 recon contains documentation and path-adapted tests only. Copy keycheck.py
byte-for-byte, retaining `r18.key-machine.v3` and `r18.keycheck-failure.v3` as
compatible evidence grammars. Only proposal job/stage identity labels move to
R19. Host driver, native shim, bootstrap measurement and evidence normalizer are
byte-identical to R18. No dispatch, ledger or key-path logic beyond the listed
deltas was changed.

Release preparation retargets stage/run paths, proposal IDs/default scope and
pin closure; A7 is added to the manifest. Frozen R17 P-ACCEPT design, sources,
references, gates, scoring manifest and normalized CAP-ACCEPTANCE are reused.
No historical machine check or paid output enters the prospective stage.
Fresh U0 remains unmeasured; independent review, machine/bootstrap evidence,
primary acceptance and release remain outstanding.

`_out/frozen-before.json` records R14–R18 before payload copying. Pin verification
checks that complete file inventory and all bytes remain unchanged. `_out/`
contains component/root/READY/manifest diffs and `diff-summary.json` with each
file's hunk ranges. FILES-WRITTEN excludes the pre-existing, untouched A7.
