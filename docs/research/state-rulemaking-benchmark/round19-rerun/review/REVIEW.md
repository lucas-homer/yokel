# R19 safety review (A7 on top of R18 A5 + A6) against frozen R18 — 2026-10-14

Reviewer: Claude (review sub-agent). Scope: the six review questions in the brief, i.e. the R19 wire,
adapter, recon, keycheck and release-prep deltas against `round18-rerun`, namespace isolation, the
A7 sentence, and a full independent re-run of the offline suites. Offline only: no network, provider,
native runner, release/sign/run command, credential or signing-key access. Writes confined to this
folder (`review/`). Repros run with the bundled Codex Python 3.12.14 and the system Python 3.13.7,
both with `-I -S -B` and an empty environment (`env -i PATH=/usr/bin:/bin`); outputs in `_out/`.

## Verdict: **ready-with-notes**. No BLOCKER. One SHOULD-FIX (a pin-scope bookkeeping issue the
implementer introduced, not a spend, dispatch or leakage path). Eight NOTEs.

Frozen inputs: `git status` shows exactly one entry, the untracked `round19-rerun/` tree; no tracked
change under round14–round18 before or after my runs. Pins recomputed by me: R19 `wire/wire.py` =
`f17af019…c0ffb` (adapter `WIRE_SHA`, `wire/READY.json`, stage manifest); R19 `adapter/READY.json` =
`6023fbca…88e9f`; R18 `recon/r17recon.py` = `64794fdd…27140` (unchanged pin, now referenced across
rounds); `keycheck/keycheck.py` R18 = R19 = `95959912…aad55` (byte-identical). `pin_ready.py --verify`
passed before and after my test runs (`_out/pin_ready_verify_before_review.txt`, `…_after_tests.txt`).

## 1. Wire: `round18-rerun/wire/wire.py` → `round19-rerun/wire/wire.py` — prompt-only, confirmed
My diff (`_out/mydiff-wire.diff`) has three hunks in `wire.py`: docstring, `REVISION` r16.w2.2→r16.w2.3
and `ENVELOPE_VERSION` r16.e3→r16.e4 (wire.py:15-16), and a two-line conditional append after A5
(wire.py:319-320). `R15_READY_SHA256`, `COMMON_SHA256`, `_pinned_bytes`, `schema()`, `lint_schema()`,
`validate_response()`, `_request()` and the 40000 guard (wire.py:340-347, 356-359) are untouched.
Repro `repro_wire_prompt_only.py` (`_out/repro_wire_prompt_only.txt`):
- The R19 source equals the R18 source after exactly the version relabel plus the conditional append,
  where the appended sentence is read from the normative `amendments/A7.md` quote, not from `wire.py`.
- FULL system prompt: byte-identical to R18. OPAQUE system prompt: R18 prompt + A7 sentence + `\n`,
  appended after the A5 sentence; 329 UTF-8 bytes, 330 bytes JSON-encoded.
- For sources-r2 039/041/106, both profiles: identical body key order, every non-`messages` key equal,
  user message equal, `response_format` equal, span table equal, plan metadata equal. FULL request
  bodies byte-identical to R18; OPAQUE bodies differ by exactly 330 bytes.
- Guarded sizes (body + 1024) opaque/full: 039 21406/20891; 041 22700/22185; 106 21132/20617; all under
  40000 with ≥ 17300 bytes of headroom. Matches the implementer's `_out/request-sizes.json`.
The wire suite's `test_a7.py` rewrites `round19-rerun/_out/request-sizes.json` on every run; the bytes
were identical after my runs (tree hash unchanged for that file).

## 2. Adapter, recon, keycheck, release-prep: only the allowed deltas
I regenerated every component diff myself (`diff -ruN -x _out`, `_out/mydiff-*.diff`) and compared
the +/- content lines with the implementer's `_out/*.diff`: wire 134/134, adapter 94/94, keycheck 8/8,
release-prep 103/103 identical (READY.json and STAGE-MANIFEST.json compared separately; see below).
Recon differs only because my `-N` diff lists the whole removed `r17recon.py` that R19 no longer copies.

**Adapter (`r17_adapter.py`, two hunks):** roots `R19/BENCH/R18` (:20-22), `WIRE_SHA` (:26), `NAMESPACE`
(:28), and in `dependencies()` the wire pin read from R19 `wire/READY.json` with label `r19_wire_pin`
and the wire module loaded from R19 (:157-162). `RECON_SHA`, the R18 recon READY pin and the R17
`sources-r2` upstream wire pin are unchanged. No hunk touches `post()`/`DISPATCH_MARK`, ledger shapes
or transitions, `admit`/`reconcile`/`close_debit`, the A6 U0 sites (`init_constants`, `K3_machine_check`,
`last_usage`, `pre_key_usage`), the transport guard (`dispatched`, `immediate_transport_guard`), key
reads or env handling. `host_driver.py`, `native_entry.py`, `fake_http.py` and every inherited test
are byte-identical to R18; `pin_ready.py`/`verify_ready.py`/`run_tests.sh` change only the r18→r19
labels/env var. New `test_a7.py` (3 tests). `adapter/READY.json` differs only in pins, counts
(211→214), revision r1.5→r1.6, namespace and scope.
**Recon:** no executable in R19; `test_recon.py` loads `../round18-rerun/recon/r17recon.py` by path
and still asserts the exported constants (`CAP`, `OPERATING`, `FLOOR`, `TOL_PER_CALL`, schedules,
policies) equal the original fixture engine. `recon/READY.json` now lists the R18 engine and READY
as dependencies with the unchanged hash.
**Keycheck:** `keycheck.py`, `measure_bootstrap.py`, `test_a6.py`, `test_keycheck.py`, `SPEC.md`
byte-identical; `make_keycheck_proposal.py` changes only the job-id prefix and stage schema label;
README scope string. The R18 live evidence/proposal/primary-review folders and `LIVE-VARS.txt` were
deliberately not copied.
**Release-prep:** path roots `round18-rerun`→`round19-rerun`, scope default, job-id prefix
(`r19-<cell>-<batch>`), stage parent `.r19-stage`, `A7.md` added to the pin closure, test path
updates; `release_records.py` changes only the two staged path roots. `normalize_evidence.py`,
`A3-TIMEOUT.md`, `LIVE-DISPOSITION.md`, `test_findings.py` and both evidence files are byte-identical.

## 3. Namespace isolation and replay — `repro_namespace_isolation.py` (`_out/repro_namespace_isolation.txt`)
Using the adapter's own synthetic harness (fake transport/clock, temp dirs under `review/_out`, removed):
- Positive control dispatches once (state 13).
- R18 ledger (INIT namespace `r18.paid-rerun.v1`) with a release bound to it → `init_namespace_key`
  (r17_adapter.py:406); same for `r17.paid-comparison.v1`. Ledger bytes unchanged, 0 key reads, 0 POST,
  no attempt dir.
- R19 ledger with an R18 release's `init_sha256` → `release_init_hash` (:417); same zero effects.
- R18 call pins (plan/dispatched hashes computed with the frozen R18 wire) in an otherwise valid R19
  release → `release_body_hashes` (:967) after RESERVE, surfaced as `pre_dispatch_pause` (:1108): 1 key
  preflight read, 0 POST, ledger tail RESERVE → RESOLVE(dispatched=false, debit=0), no DISPATCH_MARK,
  no request/intent receipt. A7 therefore also makes every R18 OPQ call pin unusable in R19.
- FULL cell: refused before any read under an OPQ-only release and, as first cell, by
  `wrong_cell_order`. FULL pins are identical across R18/R19 (prompt unchanged) but FULL is not in
  `required_calls` (CALLS[:3], `typed_testable` false; :414).
- R18 adapter bytes offered as the release's adapter artifact → `adapter_self_pin` (:455).
The recon pin is intentionally shared with R18 (N5); isolation rests on namespace, INIT/release hash
and the wire-derived call pins, all of which differ.

## 4. Release-prep contents — `repro_release_prep.py` (`_out/repro_release_prep.txt`)
- `make_proposals.CELLS` = S1-OPQ, S2-OPQ, S3-OPQ (ordered; non-draft requires exactly one `--cell`);
  no FULL. Order at run time is enforced by the adapter (`wrong_cell_order`) and per-cell gates.
- `release_records.init_record`: namespace `r19.paid-rerun.v1`, FLOOR 270000000, OPERATING 1800000000,
  CAP 2000000000, KEY_MAX = key_limit 50000000000, reset null, P-ACCEPT, `required_calls` = CALLS[:3],
  `recon_sha256` = 64794fdd…; non-int/negative/bool U0 refused. Matches `recon` constants.
- Default scope `docketclock-research-r19-authorized-20261014`; job ids `r19-s<n>-opq-<batch>`.
- Scoring manifest slots S1/S2/S3 = 26-19-039/041/106 in order, `typed_testable` false (N_c 4).
- `prepare_manifest.build()` rebuilt in memory equals the committed `STAGE-MANIFEST.json` byte for
  byte. Its frozen part (every entry outside round18/round19) is identical to the R18 manifest. Every
  artifact pinned by the accepted R17 `run-live/stage-run/RELEASE.json` for the design (`design-r3-1-paccept`
  protocol/budget/reference-spec/adjudication-spec/scorer/cases/check/READY*), the A1/A2 fixture gates,
  reference ACCEPTANCE, scoring MANIFEST, sources-r2 READY, roles auth, KEY-ATTESTATION and
  CAP-ACCEPTANCE is present with the identical hash. R17 adapter/recon/tests/host_driver and the
  historical KEY-MACHINE are absent; no `run-live/`, `content.body` or KEY-MACHINE path is staged.
  The only `round18-rerun/` entries are the recon engine and its READY.

## 5. A7 sentence semantics — advisory
The sentence is gated to "an exemption or exception" and prescribes the roles the frozen B4 table
already scores as correct for EXCEPT: `if` on a unit that itself asserts the exemption (adjudicated
`inverse`, so odd polarity) and `unless` on a carve-out against a positive assertion (even polarity).
It does not touch COND/RESTRICT/IRRESPECTIVE guidance, A5 cardinality, uncertainty or `qual`. Risks:
- **Convention dependence.** The `if` prescription assumes the adjudicators map the exemption-asserting
  unit as `inverse` (both did in R18). A `direct` mapping of such a unit would score `if` as inversion;
  that risk pre-exists A7 and is a mapping question, not a prompt one.
- **Over-application of `unless`.** "Except/unless" phrasings that the reference classes as COND or
  RESTRICT (e.g. "unless otherwise provided", "except as provided in…") could be pushed to `unless`
  and score inversion. The gating language limits this but does not eliminate it; S2/S3 are the test.
- **Leaf breadth.** "Preserve the exact exempted case" could lead to leaves that also keep the reason
  clause. B6 extraneous counting only reaches `broad` above 2×|K(r)|, and reason text inside the target's
  own quote is never extraneous, so mis-measurement in the strict direction is unlikely; in the lenient
  direction the scorer is unchanged, so A7 cannot inflate scores except by genuinely covering clauses.
- **Volume.** Extra leaves/links for every exception raise completion tokens slightly; the D5 futility
  threshold (13926) and the 400-node sentinel are far from the R18 S1 scale. Prompt grows ~330 bytes.
The pre-registered interpretation constraint in `A7.md` (S1 is weak evidence; S2/S3 carry weight) is
the right framing; nothing in the sentence names a source, offset or reference.

## 6. Suites re-run and frozen inputs
Run directly with `unittest discover` (not via `offline_tests.py`, which writes outside `review/`):

| suite | 3.12.14 (codex runtime) | 3.13.7 (system) |
|---|---|---|
| wire | 104 OK | 104 OK |
| recon | 3 OK | 3 OK |
| adapter | 214 OK | 214 OK |
| keycheck | 46 OK | 46 OK |
| release-prep | 23 OK | 23 OK |
| total | 390 | 390 |

Logs: `_out/tests-{python312,system}-<suite>.txt`. The independent wire suite (54/55 with its one
historical expected failure) is only run by `offline_tests.py`; I did not re-run it, I accept the
implementer's recorded result. `git status` after all runs: only `?? …/round19-rerun/`, no tracked
change under round14–round18. Tree hashes of `round19-rerun` (excluding `review/`) before and after
my runs (`_out/tree-hashes-{before,after}-tests.txt`) differ in exactly one file, `adapter/_out/repro-r1-4.txt`
(N2).

## SHOULD-FIX
- **S1** The root `READY.json` pins `review/REVIEW.md` (pin_ready.py:97), which at pin time held the
  implementer's self-check. R18 did not pin the review path. Any independent review, including this
  one, therefore invalidates `pin_ready.py --verify` at the root (`_out/pin_ready_verify_after_review.txt`).
  Fix either way before release prep: drop `review/REVIEW.md` from the root pin list (the primary pins
  the accepted review externally, as the `self_pin` field already says for READY itself), or re-run
  `pin_ready.py` once the review is accepted. Component READYs and the stage manifest are unaffected
  and still verify. The implementer's self-check text is preserved at `_out/implementer-self-check.md`.

## NOTEs
- **N1** `release_body_hashes` is surfaced to the operator as `pre_dispatch_pause` with a `stop.json`
  receipt but the inner reason is not written to any receipt (only state 1, debit 0). Inherited R18
  behaviour; fail-closed. A diagnostic field would help an operator who stages the wrong release.
- **N2** `adapter/test_repros.py:23` rewrites `adapter/_out/repro-r1-4.txt` on every run and the content
  is nondeterministic (a temp-dir name inside a traceback; two 3.12 runs differ, `_out/repro-r1-4.run{1,2}.txt`).
  My runs changed that file's bytes. It is excluded from the READY payload, so pins still verify.
- **N3** `keycheck.py` keeps the `r18.key-machine.v3` / `r18.keycheck-failure.v3` schema labels
  (byte-identical executable by design). The adapter's K3 check validates fields, not the label.
- **N4** Scope (`docketclock-research-r19-authorized-20261014`) is enforced only at the native
  proposal layer (`make_proposals.py` default, keycheck README); the adapter never sees it. Same as R18.
- **N5** INIT `recon_sha256` and the release `recon` artifact hash are identical in R18 and R19 (shared
  frozen engine); not an isolation boundary, by design.
- **N6** Cosmetic residual "r18" strings in R19: module labels `r18_wire_regression` (wire/test_r18.py:14),
  `r18_verify_pins` (wire/verify.py:41), and `test_r18.py` keeping its name while now testing A7.
- **N7** The A7 text in `wire.py` is a literal; it is not read from `A7.md` at run time. My repro and
  the implementer's test both check it equals the normative quote.
- **N8** Operational, carried from R18: the first call's preflight tolerance is 0, so any DocketClock
  key use between the fresh keycheck and S1's preflight refuses dispatch; re-baseline, never edit
  the ledger. Expected U0 ≈ 118,819,500 nanoUSD per `A7.md` is a forecast only; the fresh keycheck is
  authoritative.

## Files written (all under `review/`)
`REVIEW.md`; `repro_wire_prompt_only.py`; `repro_namespace_isolation.py`; `repro_release_prep.py`;
`_out/repro_wire_prompt_only.txt`, `_out/repro_namespace_isolation.txt`, `_out/repro_release_prep.txt`;
`_out/mydiff-{wire,adapter,recon,keycheck,release-prep}.diff`; `_out/tests-{python312,system}-{wire,recon,adapter,keycheck,release-prep}.txt`;
`_out/tests-python312-adapter-test_repros-rerun.txt`; `_out/tree-hashes-{before,after}-tests.txt`;
`_out/repro-r1-4.run{1,2}.txt`; `_out/pin_ready_verify_{before_review,after_tests,after_review}.txt`;
`_out/{opaque,full}-system-prompt-r19.txt`; `_out/implementer-self-check.md`.
