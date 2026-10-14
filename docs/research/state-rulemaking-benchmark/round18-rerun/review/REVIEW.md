# R18 safety review (A5 + A6) against frozen R16/R17 — 2026-10-14

Reviewer: Claude (review sub-agent). Scope: the five diffs named in the brief. Offline only: no
network, provider, runner, executor or release command; no credential or signing-key access.
Writes confined to this folder. Repros run with the bundled Python 3.12 (`-I -S -B`); outputs in `_out/`.

## Verdict: **ready**. No BLOCKER, no SHOULD-FIX. Six NOTEs, none of which opens a spend, dispatch or leakage path.

Frozen inputs: `git status` shows no tracked change under round14/15/16/17. Pins recomputed:
R18 `wire/wire.py` = `0f8e4447…d56bef` (adapter `WIRE_SHA`, `wire/READY.json`), R18 `recon/r17recon.py`
= `64794fdd…27140` (adapter `RECON_SHA`, `recon/READY.json`). Sol's recorded counts: 383 per
interpreter (adapter 211, wire 100, keycheck 46, release-prep 23, recon 3), 3.12 and 3.13, all passed.

## 1. Wire: `protocol-w2-1/wire.py` → `round18-rerun/wire/wire.py` — prompt-only, confirmed
Diff is 27 lines: docstring, `REVISION` r16.w2.1→r16.w2.2, `ENVELOPE_VERSION` r16.e2→r16.e3, and
one `prompt +=` line in `_system_prompt`. `R15_READY_SHA256`, `COMMON_SHA256`, `_pinned_bytes`,
`schema()`, `lint_schema()`, `validate_response()`, `_request()` are byte-identical; the body is
still `request-settings.json` (r15 pin) + `schema(source, table, profile)` + the pinned validator.
Repro `repro_wire_prompt_only.py` builds the same source through both modules for both profiles:
every body key, the user message, `response_format` (schema) and the span table are equal; the only
difference is the system prompt (241 encoded bytes), still under the 40000 guard.
NOTE N4: the sentence is appended unconditionally, i.e. to the full profile too. That matches
A5-A6.md ("matching sentence to the full-profile prompt"); FULL is not run in R18 (E8).

## 2. Recon: `recon-a4/r17recon.py` → `round18-rerun/recon/r17recon.py` (+9/−7) with U0 > 0
Repro `repro_recon_a6.py` (5 tests, pass).
- **Admission exposure unchanged.** `admit()` compares *absolute* reconciled usage (U0 at INIT via
  `last_usage`) + FLOOR×remaining against the absolute limit; the OPERATING check uses relative
  debits only (`aggregate`), so U0 never consumes OPERATING and never buys extra exposure.
  `key_limit_ok` subtracts U0 (`limit − U0 ≥ FLOOR×required`), rejects bool/negative/non-int U0.
- **Unexplained usage halts.** `u > U0 + Σreported + i·1000` → `HALT 'usage exceeds reported cost'`;
  acceptance only within ±tol of `U0 + Σreported`; a read that stays at U0 is `KEY_USAGE_UNRECONCILED`.
- **Drop still halts.** `u < prev_usage` (prev = U0 at INIT, else last RECONCILED absolute U) →
  `'usage regressed or invalid'`, including intra-sequence drops (R3-S3).
- **close_debit** = `max(0, highest − INIT.U0 − Σdebits)`: retains only run cost above baseline
  (40e9 baseline, FLOOR debit, highest 40.3e9 → 30e6; no reads → 0).
- **Missing `key_initial_usage` fails closed.** `reconcile` defaults the baseline to 0 → a genuine
  `U0+reported` read halts as unexplained; `close_debit` over-retains (never under-retains).
  Call sites in the adapter: `poll()` (r17_adapter.py:847-848, passes INIT's field into `pinned`),
  `close()`/:1076 (`close_debit`), `execute_once`/:936 and `main`/:1229 (`admit` with `last_usage`),
  :952 preflight. All `entries[0]['key_initial_usage']` indexes run after `release_gate` requires the
  field to be a non-negative int (:409), except the probe path — see N2.

## 3. Adapter: `adapter-r1-4` → `round18-rerun/adapter` (ignoring _out) — nothing else changed
`r17_adapter.py` has exactly seven hunks: (1) path roots `R18/BENCH/R17`, `RECON_SHA`, `WIRE_SHA`,
`NAMESPACE` r17.paid-comparison.v1→r18.paid-rerun.v1; (2) `dependencies()` loads R18 recon/wire
by pin, re-checks R17 `sources-r2` upstream wire pin (old R16 hash, literal) and the new
`r18_wire_pin`; (3) `init_constants` drops `key_initial_usage: 0`, adds the int ≥ 0 requirement and
passes U0 to `key_limit_ok`; (4) `K3_machine_check` requires int `usage == INIT.U0`,
int `limit_remaining == limit − U0`; (5) `last_usage` default 0→`INIT.U0`; (6) `pinned` gains U0;
(7) preflight `pre_key_usage` compares against `U0 + Σreported` with `count×1000` tolerance.
`host_driver.py`: sources root → `round17-paid-comparison/sources-r2` only. `native_entry.py`:
host path `adapter-r1-4/`→`adapter/` only. `pin_ready.py`/`verify_ready.py`/`run_tests.sh` are now
thin wrappers around the shared R18 `pin_ready.py` (hashing + unittest discovery; no network).
Tests: path updates only, plus `test_nonzero_initial_usage_refused` → `test_negative_initial_usage_refused`
(expected under A6; N6) and new `test_a6.py` (11 tests: baseline admission walk, below/above-baseline
preflight refusals, post-dispatch drop/unexplained halts, K3 mismatches, invalid baselines, capacity,
close retention). The POST path (`DISPATCH_MARK` → single `post()`), transport guard, torn-mark
recovery and re-gating are untouched: no new double-dispatch or unauthorized-dispatch path.
Namespace change means an R17 ledger cannot be bound to an R18 release (`init_namespace_key`).

## 4. Keycheck: `keycheck-job-v2` → `round18-rerun/keycheck` — no new leakage path
`keycheck.py` changes: schema labels v2→v3; `EXPECTED.usage/limit_remaining` → None, replaced by
`checks['usage'] = finite numeric ≥ 0` and `checks['limit_remaining'] = (remaining == limit − usage)`
computed in Decimal with a span-bounded precision; new metadata `key_initial_usage_candidate_usd`
(the USD Decimal) and `…_nanousd` (ceil × 1e9). GET path, TLS, timeout, masked-label handling,
failure stages and `MASKED_LABEL_RE` are unchanged; the masked label is still not persisted
(`test_a6.py::test_masked_positive_usage_candidate_without_persisting_fragments`). The two new
fields carry only usage amounts. `make_keycheck_proposal.py`: job-id/schema labels only.
The live R18 record (`keycheck/evidence-…/KEY-MACHINE.json`, primary-run) shows usage 0.0594085 USD,
candidate 59 408 500 nanoUSD, remaining 49.9405915, `accepted_by_primary: false` — consistent.
NOTE N3: the USD candidate is serialized as a JSON number; the integer nanoUSD candidate is the
authoritative value, and the adapter's K3 check requires integer nanoUSD (`type is int`), so a
primary-authored machine record copied in USD floats is refused, which is the right direction.

## 5. Release-prep: INIT `--key-initial-usage`
`release_records.py init` takes `--key-initial-usage type=int required` and `init_record` requires
int ≥ 0; a USD decimal like `0.0594085` is rejected by argparse. An integer typo (0, a dropped or
extra digit, a ×1000 scale slip) is accepted **silently at INIT** and flows into `init_sha256` and
BIND. Repro `repro_init_baseline.py` (5 tests, pass) shows every such ledger is refused before any
RESERVE, key read or POST:
- INIT U0 ≠ machine record → `K3_machine_check` (release_gate, before `claim()`);
- correlated typo in INIT *and* the hand-authored machine record → `pre_dispatch_pause`
  (`pre_key_usage`: with 0 DISPATCH_MARKs the live key read must equal U0 exactly), 0 posts, no RESERVE;
- ×1000 slip (59 408 500 000) → `key_limit` (capacity for 3×FLOOR fails).
NOTE N1: the brief asks for a cross-check against the accepted KEY-MACHINE at INIT. It exists, but
downstream (K3 + live preflight), not in `release_records.py`. Cost of a typo is a dead R18 ledger
(`open('xb')`; README forbids truncation) → fresh run dir/stage/proposals, not spend. Optional
hardening, not required for this 3-call run: add `--machine-check <path>` to `init` and require
`usage == U0` and `limit_remaining == limit − U0` there too.

## NOTEs (none reach SHOULD-FIX)
- **N1** INIT typo is silent at INIT, refused before dispatch (above). Repro `repro_init_baseline.py`.
- **N2** `last_usage()` now indexes `INIT['key_initial_usage']`; on the `main` probe path (:1229) it
  runs before `release_gate`, so an INIT lacking the field dies with `KeyError` rather than a
  `Refused` — fail-closed, not reachable with a `release_records.py` INIT. Empty ledgers are still a
  clean `empty_ledger` refusal. Repro `repro_probe_shapes.py`.
- **N3** USD candidate serialized as a JSON number; int nanoUSD is authoritative (above).
- **N4** A5 sentence applied to both profiles (matches A5-A6.md; FULL omitted in R18).
- **N5** Operational: the first call's preflight tolerance is 0, so any use of the DocketClock key
  between the keycheck (18:44Z) and S1's preflight refuses dispatch. That is the intended fail-closed
  behaviour; the operator re-baselines (fresh keycheck → fresh INIT) rather than editing the ledger.
- **N6** `test_nonzero_initial_usage_refused` was necessarily removed; its protection is now the K3
  equality and preflight checks in `test_a6.py` and `repro_init_baseline.py`.

## Repros (all pass on the bundled 3.12; outputs in `_out/*.txt`)
- `repro_recon_a6.py` — admission exposure, reconcile accept/halt bands, drop halts, missing-key
  fail-closed, close_debit.
- `repro_wire_prompt_only.py` — R16 w2.1 vs R18 w2.2 builds equal except the system prompt.
- `repro_init_baseline.py` — INIT typo refusal paths; correct U0 dispatches once, debits only run cost.
- `repro_probe_shapes.py` — `last_usage` shapes (N2).
Temp dirs for the harness are created under `review/_out` and removed; nothing outside `review/` was written.
