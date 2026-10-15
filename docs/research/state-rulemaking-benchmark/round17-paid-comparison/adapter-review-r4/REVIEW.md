# R17 adapter r1.3 / r1.4 + release preparation — round-4 safety review

Reviewer: Claude Fable 5.1 (review sub-agent), 2026-10-14. Scope: `diff -ru adapter-r1-2 adapter-r1-4`
(`_out/` ignored), `adapter-r1-4/native_entry.py` (sha256 `522e9e6d…e3b2f4`), `host_driver.py`
(`74990ace…e86534`), `r17_adapter.py` (`e3046a9a…02ec7c`), `recon-a4/r17recon.py` (`8c98fabd…b6bb0`),
`release-prep/` + `release-prep-a4/` (`stage.py`, `prepare_manifest.py`, `make_proposals.py`,
`STAGE-MANIFEST.json`, `proposals-draft/`, both READMEs, `A3-TIMEOUT.md`), A4 amendment and run evidence,
and the installed-runner contract (`tools/research-credentials-stable/INTERFACE.md`, `README.md`,
`Manifest.h`, `runner.m`, deployed `core.json`). READY pins at review time: adapter-r1-4 `cb15fca1…9199f0`,
recon-a4 `1648ccc1…b5ef2b`, release-prep-a4 `e074e57b…dbc54c`.

Method: diff read line by line; six new offline repros under `adapter-review-r4/` (runner interpreter
`python3.12 -I -S -B`, synthetic keys, fake transports, child processes killed by `os._exit(4)` exactly as
the shim's alarm handler does and by `SIGTERM` as the native supervisor does). `stage.py` was exercised only
against temporary trees under `adapter-review-r4/_tmp` (its CLI with a temporary `--parent` refuses before
copying, as it should). No network, provider, runner, `release.py`, `release_job.sh`, `check-job`, `run`,
Keychain or credential file was touched; `sources-r2/*/parsed-body.txt` and `reference/` were not opened
(reference members were only hash-listed from the manifest). After the repros every A4 READY payload,
dependency and test-log pin re-verified and the frozen r1.3/release-prep/design-r3-1 inputs are unchanged
(`results.txt`; `~/dev/yokel/.r17-stage` does not exist; `git status` shows only this folder as new).

## Verdict

**Ready for release prep, with four SHOULD-FIX items to close before anything is signed.** No BLOCKER:
I could not construct an overspend, a second POST, an unauthorized dispatch or a key leak from the r1.3/r1.4
diff, the shim, the staging tool or the drafts. Every kill scenario fails closed with the lock retained and
recoverable accounting (repro: 59/59). The four SHOULD-FIX items are documentation/tooling traps on the
operator path; none requires changing `adapter-r1-4` or `recon-a4` bytes (S9 touches
`release-prep-a4/make_proposals.py` if fixed in code rather than by procedure). Notes N29–N42 follow.

## 1. Regressions in the pieces approved in round 3 — none found

- `r17_adapter.py` changes are exactly: `RECON_SHA` → recon-a4 hash, `KEY_LABEL` → `DocketClock`, the
  recon dependency loaded from `recon-a4/` (pinned by hash and by `recon-a4/READY.json`), and `'recon'`
  removed from the design-freeze loop — but `release_recon_pin` (line 436) and `init_static_pins` (438) still
  bind the release artifact and INIT to `RECON_SHA`. `repro_r4_readme_values.py` shows a release that maps
  `recon` to the design engine is refused (`release_recon_pin`), as is an INIT carrying the old hash.
- `host_driver.py`: the only behavioural change is the elapsed-time `deadline()` wrapper around the single
  `connection.request`/`getresponse`/`read` sequence. One call site, no retry, key hygiene unchanged
  (`del key` paths intact; `DriverError` messages fixed strings). `TIMEOUT_S` 900 → 600 is reflected in
  `test_round2.py`.
- Tests: the L01–L25 fixtures now run against the frozen original engine (correct: the frozen `check.py`
  pairs with the design recon); `test_a4.py` proves only L18 changes. `test_repros.py` runs the repros
  with `sys.executable` (fixes N23's shell dependency).
- `pin_ready.py`/`verify_ready.py` were rewritten for the three A4 folders; I re-ran their `verify()` logic
  (not the suites) after my repros: all pins hold.

## 2. The shim (`native_entry.py`) — `repro_r4_shim_grammar.py`, 32/32

- argv must be exactly `['--live-initial']` (list equality): `[]`, duplicates, extra `--cell`, case
  variants, `--live-initial=1`, `-h`, trailing `''` all exit 2 with the host never loaded. Missing any of
  `-I`/`-S`/`-B` exits 2.
- Per-cell arguments come only from `arguments.json` beside the shim, which the signed job pins by hash;
  `host_sha256` binds the host bytes; the host is resolved positionally (`../../adapter-r1-4/host_driver.py`)
  and refused on drift; a relocated shim finds no host (exit 4) or a hash-mismatched one (exit 2).
  So the job cannot be pointed at another cell, attempt dir, run root or ledger than the signed
  `arguments.json` says. Pre-armed `ITIMER_REAL` → exit 2; timer disarmed on every return path.
- One-POST and recover-first are preserved: shim → `host_driver.main(args)` → `adapter.main(args,
  recover_first=True)`; `--driver`/`--driver-sha256` in signed args are refused (`driver_override`). The
  kill repro counts exactly one POST per cell in every path.
- NOTE N32: `arguments.json` is parsed with plain `json.loads` (duplicate `args` keys → last wins; `args`
  not type-checked, a string reaches `host.main`). The bytes are signed, so cosmetic; `adapter.strict`
  would be the symmetric choice.
- NOTE N33: a signed `arguments.json` may carry `--lock-evidence` or `--opq-freeze`; neither shim nor host
  forbids it. That is the designed recovery route; only signing discipline keeps it out of a cell job.

## 3. A3 timing and kills — `repro_r4_deadline_kill.py`, 59/59

- Arithmetic checks: 15 + 615 + 900 + 4×15 = **1,590 s** (Sol); the reads are absolute offsets from
  `resolved_at`, so the tighter bound is 15 + 615 + 900 + 15 = 1,545 s (N30). Marked recovery ≤ 960 s, no
  POST. 1,590 < 1,740 < 1,800. The 1,740 s deadline **is enforced**: the shim arms it before config/imports
  and `os._exit(4)`s on expiry (the repro shows the host seeing >1,700 s remaining at entry).
- Nested deadlines with real signals: shim timer earlier than the host's → shim handler → exit 4 (even
  inside a hung POST send); host inner/outer deadlines → `DriverError('transport_deadline')` with the shim
  timer re-armed minus elapsed; no extension of the outer timer in any case.
- Kill at each stage (alarm and SIGTERM, real adapter through the r1.4 Harness in child processes):
  - **pre-mark** (after RESERVE): lock retained; next run → `lock_or_claim_exists`, 0 GET/POST; operator
    lock-evidence recovery → `RESOLVE dispatched=false, debit 0`, 0 key reads; a fresh run then dispatches
    exactly once (re-admission of an unmarked cell is by design).
  - **post-mark mid-POST**: lock retained, `DISPATCH_MARK` last, no receipts; recovery → 4 key reads,
    `RESOLVE dispatched=true, FLOOR`, `HALT`, 0 POST; next run refused before any transport
    (`admit(S2) = halted`).
  - **mid-reconciliation** (killed inside the slot-60 GET): recovery consumes the claimed slot as a failed
    read, total reads ≤ 4 across crash + recovery, `RESOLVE`, `HALT`, 0 POST; ledger chain verifies.
- NOTE N29: the native 1,800 s clock starts before `op run` secret resolution and the pre-exec hashing of
  111 pinned files; the shim's 1,740 s clock starts after them, so the 60 s reserve shrinks by bootstrap
  time (A3-TIMEOUT.md says so). Measure `op run` latency at the runner's smoke step before release.
- NOTE N31: Python signal handlers run between bytecodes; a blocking `getaddrinfo` is not interrupted, so
  "including DNS" in `deadline()`'s docstring holds only up to the resolver's own timeout. The supervisor's
  SIGTERM/SIGKILL remains the backstop; still fail-closed.
- NOTE N42: `expired` can theoretically fire in the one-bytecode window inside `deadline()`'s own `finally`
  after a successful response; the result is `transport_failed` on a completed POST → reconciliation and
  HALT (fail closed, costs the cell). Negligible probability; mentioned for completeness.

## 4. A4 ($50 key) — `repro_r4_a4_bounds.py`, 14/14

- Engines differ only in `KEY_MAX`; the adapter imports recon-a4 and `KEY_LABEL = 'DocketClock'`.
- With `key_limit = $50`, admission is bounded by OPERATING $1.80 with all remaining calls reserved at
  FLOOR (1 done at $1.53 → refused; 2 done at $1.54 → refused; `RECONCILE_UP` $1.00 before any call →
  refused), by `pre_key_usage` (live usage must match reported cost within `count × 1000` nano, i.e. $0 at S1),
  by the live-limit/reset equality checks, and by `debit > FLOOR → HALT` after any single expensive call
  (a $0.80 key delta → debit $0.80, HALT, and S2 is `halted`).
- Exhaustive `admit()` diff over ledger-consistent states (cent grid): **56 states** differ, all of them the
  old `key capacity` refusal where reconciled usage + remaining × FLOOR ∈ ($1.73, $1.80]. Nothing else
  changes; INIT now accepts limits in [$0.81, $50] instead of [$0.81, $1.73] (L18). What the user has
  accepted is that the provider-side backstop against a failure of the one-POST/ledger invariants is now
  $50 rather than $1.73 — nothing in this diff weakens those invariants.
- NOTE N36 (pre-existing): the adapter never machine-verifies the live key **label**; `_key_fields` keeps
  only usage/limit/limit_remaining/limit_reset. K3 label evidence is the primary's attestation and machine
  check. With a $50 limit the label is the only thing distinguishing this key from any other
  `DocketClock` key, so record the `label` field (nonsecret) in the machine-check artifact.

## 5. `stage.py` and the manifest — `repro_r4_stage.py`, 29/29

- Copies exactly the manifest members (unpinned siblings and `_out` are not copied), under a
  content-addressed target, owner-only modes; source hash checked before write, destination re-hashed, then
  `verify_stage`. Existing target → `FileExistsError` (mkdir-exclusive, so race-safe); partial stage never
  reused. File-symlink member, directory-symlink inside the source, source-ancestor and
  destination-ancestor symlinks all refused (`no_symlinks` + `O_NOFOLLOW` walk). `relative()` rejects
  `..`, `.`, `//`, trailing `/`, absolute and empty. Parent outside the deployed adapter roots (or equal
  to a root) refused. Hardlinked members are copied (regular files; hash-verified) — not a defect.
- The manifest (108 members) matches: every non-reference member re-hashed against this checkout; the
  adapter-r1-4 set equals the READY payload + READY.json; the runtime closure (recon-a4, design-r3-1,
  sources-r2 READY + three bodies, wire + its five pinned runtime files, reference freeze, A4 amendment,
  CAP-ACCEPTANCE, KEY-ATTESTATION) is present. The release-time additions (A1/A2 gates, scoring manifest,
  machine check, roles/auth, RELEASE.json, accepted review) are correctly left to `--evidence`.
- Can the runner execute something other than what was reviewed? Within the signed closure, no: argv[4],
  the interpreter and all 111 files are hash-checked by the runner before exec, the shim re-checks the host,
  the host loads the adapter that self-pins against RELEASE.json, and the adapter loads recon/wire by
  hard-coded hashes. NOTE N35: the signed pins cover the `python3.12` **binary** only; the bundled stdlib
  and dylibs under the same user-owned prefix are unpinned and user-writable, and the runner README already
  states it is not a sandbox. Same-user compromise only; outside this diff's scope. The pin-check/exec race
  the runner README acknowledges applies to `arguments.json` too.
- NOTE N37: `.r17-stage` has no ignore rule in this checkout either; the release-prep README's instruction
  stands.

## 6. Proposals — `repro_r4_proposals.py`, 52/52 (reasoned; check-job not run)

- All three drafts: exact nine top-level keys, schema, project, `job_id` matches `^[a-z][a-z0-9-]{0,63}$`
  and the file stem, OpenRouter-only subset, six-element argv with the exact interpreter, `-I -S -B`,
  `…/adapter.py` under `/Users/home/dev/yokel`, `--live-initial`; 111 pins incl. python, shim and
  `arguments.json`, all under dependency roots, lowercase 64-hex; `timeout_seconds` 1,800 ≤ core max;
  integer budget with prior + 0.27 ≤ 2.00; review path among pins with equal hash; unique IDs per cell;
  S2/S3 carry `--staged-gate run/gates/<cell>.json`.
- Bytes equal an independent port of `Manifest.h`'s `CanonicalJSON` (strcmp key order, compact, slashes
  unescaped); all strings are ASCII, so the NSJSONSerialization escaping question does not arise.
- check-job will **not** accept the drafts as they are, by design: `CanonicalPath` requires the staged
  paths to exist, expiry (+86,400 s at draft time) must be in (now, now+7 d] at check-job **and** again at
  `_stage-job`/`_payload-job`, scope and priors are placeholders. Once staged with real paths, the native
  checks I can read are all satisfied.
- NOTE N34: the draft `review` pin is `adapter-r1-4/SPEC.md` (the implementer's spec). At release pass
  `--review` for the accepted independent review, which must first be added to the stage via `--evidence`
  (this `REVIEW.md`, if accepted, is not in the manifest).

## 7. Release order — `repro_r4_readme_values.py`, 17/17

**S7 — SHOULD-FIX: the only ordered release steps are stale for r1.4.** `release-prep-a4/README.md` has no
step list of its own and defers to `release-prep/README.md`, whose steps say INIT `KEY_MAX:1730000000`,
`key_label:'yokel-r17-paid-comparison'`, `recon_sha256 = 5295a667…`, "map adapter/tests/adapter_ready to
adapter-r1-3", and the **human** step "place the R17-only, nonresetting **$1.73** key". r1.4 refuses every
one of these with 0 POST (`init_constants`, `init_namespace_key`, `init_static_pins`, `release_recon_pin`,
`freeze_pin`), so it fails closed, but the human key instruction contradicts A4 and an operator following
the document will burn a signed job on a refusal. Fix: give `release-prep-a4/README.md` the full ordered
list with r1.4 values (KEY_MAX 50000000000, label `DocketClock`, recon `8c98fabd…`, adapter-r1-4 mapping,
$50 key) and mark the r1.3 list superseded.

**S8 — SHOULD-FIX: the A4 manifest pins evidence the adapter refuses.** `run/KEY-ATTESTATION.json`
(`limit_usd` string, `used_only_for_r17` string, no `creation_date`, `limit_reset: "none"`) fails
`K3_attestation`; `run/CAP-ACCEPTANCE.json` lacks `accepted_by_primary`/`verbatim_acceptance`/
`residual_risk_accepted` and fails `policy_evidence`. The old README lists the normalization as a blocker,
but the A4 manifest and drafts were regenerated with these bytes, and normalizing them changes the stage
content ID and therefore every prospective path in the drafts. Order it explicitly: normalize → re-pin →
`prepare_manifest` → stage → proposals.

**S9 — SHOULD-FIX: `make_proposals.py` non-draft mode defaults to all three cells and applies one
`--gate` to both S2 and S3.** Omitting `--cell` in step 5 with `--gate` yields three signable proposals in
one batch where S3's signed `arguments.json` points at S2's gate (repro). The adapter refuses
(`staged_gate_call_set`, `wrong_cell_order`) and the ledger prevents any double POST, but three live signed
jobs would sit in the registry at once and a mis-ordered `run` consumes a one-shot claim for nothing. Fix:
require exactly one `--cell` when not `--draft` (or document "never omit `--cell`" in bold at step 5).

**S10 — SHOULD-FIX: recovery after a native kill is not in the release order.** After any supervisor kill
or shim expiry the lock is retained (correct). The next signed job then exits 3 and its one-shot claim is
consumed with no work done. The documented route is the adapter CLI's `--lock-evidence` (round 3), which the
operator must run outside the runner: for an unmarked cell it needs no key; for a marked cell it needs key
GETs, which without `OPENROUTER_API_KEY` degrade to four failed reads → FLOOR debit + HALT (conservative,
still fail-closed), and a keyed recovery would need a signed job whose `arguments.json` carries
`--lock-evidence`, which `make_proposals.py` cannot produce. Also state plainly that a **marked** recovery
HALTs the whole run (`recovered_possibly_dispatched`), so one kill mid-POST ends R17 under that ledger and a
new run root/namespace is needed ("refuse an existing ledger" stands). Add the route and this consequence
to the ordered steps before step 7.

Steps 1–4, 6 and 9 are otherwise sound: exclusive INIT/RELEASE/BIND writes, offline `release_gate` before
signing, `release_job.sh` publishing exclusively and invoking check-job, one `run` per cell, no FULL cells.

## Notes (none above NOTE)

N29 bootstrap eats into the 60 s reserve · N30 tighter 1,545 s transport bound · N31 DNS not
alarm-interruptible · N32 shim parses `arguments.json` non-strictly · N33 signed args may select
`--lock-evidence`/`--opq-freeze` · N34 draft review pin is SPEC.md · N35 stdlib unpinned (runner trust
boundary) and `recon-a4/_out/frozen-before.json` is an unpinned baseline (redundant with READY deps) ·
N36 live key label not machine-verified · N37 `.r17-stage` not ignored · N42 alarm-in-finally window.

## Files written

- `adapter-review-r4/REVIEW.md` (this file), `_load.py`, `run_all.sh`, `results.txt` (all six repros, 203/203)
- `repro_r4_shim_grammar.py` — §2 · `repro_r4_deadline_kill.py` — §3 · `repro_r4_a4_bounds.py` — §4 ·
  `repro_r4_stage.py` — §5 · `repro_r4_proposals.py` — §6/§7 · `repro_r4_readme_values.py` — §7

Temporary trees (`_tmp/`) removed; no `__pycache__` (`-B`); nothing outside this folder written.
