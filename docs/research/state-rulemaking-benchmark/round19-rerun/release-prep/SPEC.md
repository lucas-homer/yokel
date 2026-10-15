# R19 release preparation

Adapted from release-prep-a4-r2; active stage/run/adapter/wire point to R19.
Recon points to the unchanged frozen R18 engine and READY.
prepare_manifest reuses frozen R17 P-ACCEPT design, source bytes, references,
scoring manifest and accepted fixture/role gates. Original design metadata and
fixture pair remain staged for offline imports. A5/A6, A7 and DESIGN-NOTE are pinned.
Historical zero-usage machine evidence and paid outputs are excluded.

INIT requires --key-initial-usage in integer nanoUSD; release/bind remain
exclusive durable records. Existing r17.release/stage/native-args schemas are
retained as compatible grammars; only the ledger namespace and scope change.
Fresh R19 machine/review/bootstrap evidence is supplied as explicit manifest
extras. The candidate manifest is prospective until primary installation.

Tests stage synthetic trees only and generate unsigned proposals; they invoke
no signing, runner, executor, release or check-job command.
