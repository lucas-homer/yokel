# R17 P3 dispatch adapter r1.2 + host driver — round-3 review (focused diff check)

Reviewer: Claude Fable 5.1 (review sub-agent), 2026-10-13. Scope: `diff -ru adapter-r1-1 adapter-r1-2`
(`_out/` ignored), i.e. `adapter-r1-2/r17_adapter.py` (sha256 `c9a0ca00…0af3`), `host_driver.py`
(`96b50e21…7bc0`), the new `test_round2.py`, `fake_http.py`, `verify_ready.py`, the `_out` moves in
the older tests, `pin_ready.py`, `SPEC.md` and `READY.json` (`7bd3135c…058a`, 23 payload files,
83 dependency pins). Python 3.13.7, OpenSSL 3.0.16, macOS.

Method: diff read line by line; my round-2 repros copied unchanged into `r2-repros/` with only the
two `_load.py` import paths changed and re-run against r1.2; five new round-3 repros aimed only at
the four bypass questions in the brief; the r1.2 suite run once from a pin-verifying wrapper. All
offline: `os.environ` is a synthetic mapping holding a synthetic key, `http.client.HTTPSConnection`
is replaced at the module seam with a fake socket under the real `http.client`, no real connection
was opened, no provider or credential was touched. `sources-r2/*/parsed-body.txt`, `original.htm`
and `reference/` were not opened. Only `adapter-review-r3/` was written; the one run of
`adapter-r1-2/run_tests.sh` wrote only inside the excluded `_out/` (hash-verified, below).

## Verdict

**Ready to pin.** No BLOCKER and nothing reaching SHOULD-FIX. S4, S5, S6 and N14 are FIXED;
N15, N16, N18, N19, N20, N21 are fixed; N17 is deferred as documented. The diff introduces no new
dispatch path, no lock-breaking path, no trust-store fallback and no key exposure that I could
construct. Seven NOTES follow (N22–N28); none affects money, dispatch count or the secret.

## Round-2 items: status against r1.2

| # | Status | Evidence |
|---|---|---|
| S4 60 s timeout | **FIXED** | `TIMEOUT_S = 900`; `repro_hd_wire.py` now prints `host pinned, port 443, timeout=900`. `repro_r3_timeout_recon.py` checks the interaction with the schedule (below). My round-2 `repro_hd_timeout_row2.py` still exits 0 *by construction* (it models silence beyond whatever `TIMEOUT_S` is); its closing text about 60 s is obsolete. |
| S5 no CLI lock-evidence route | **FIXED** | `--lock-evidence FILE` on both CLIs; `repro_r3_lock_evidence.py` §2–§10 with real PIDs. My round-2 `repro_hd_sigint_cli.py` fails only its now-obsolete assertion "CLI exposes no lock-evidence option"; every interrupt / retained-lock / recovery check still passes. |
| S6 suite rewrote a pinned file | **FIXED** | `repro_r3_s6_pins.py`: all 23 payload pins and 83 dependency pins verify before and after a full `run_tests.sh` (Ran 102/26/23/9/20, OK ×5); byte snapshot of `adapter-r1-2` (outside `_out`), `adapter`, `adapter-review`, `adapter-r1-1`, `adapter-review-r2`, `design-r3-1` unchanged; no stray files; `_out` 32 files before and after. |
| N14 zero anchors / `SSL_CERT_FILE` redirect | **FIXED** | `repro_hd_trust_store.py` now exits 1: 128 anchors before and after `SSL_CERT_FILE=<synthetic CA>`, synthetic CA not trusted. `repro_r3_tls_context.py` goes further (below). |
| N15 renamed copy / raw import error | fixed | `repro_hd_cli_misc.py` fails only its two obsolete "note" expectations: the renamed copy now returns normally (derives its own path), the import failure is caught (`host_driver_failure`, exit 4). |
| N16 key in frame locals | fixed | `repro_r3_key_hygiene.py` §1: 13 failure phases × 2 callbacks, every non-reviewer frame key-free, no chained context, no `http.client` frames in the fresh re-raise. |
| N17 Decimal precision | deferred | Unchanged frozen recon; documented. Acceptable. |
| N18 admission reason printed | fixed | `admission:halted` printed; an untrusted reason still maps to `gate_refused` (`repro_r3_lock_evidence.py` §10, Sol's `test_n18`). |
| N19/N20 key whitespace/controls | fixed | `repro_r3_key_hygiene.py` §2: `None`, `''`, bytes, non-ASCII, leading/trailing space, `\n`, `\x7f`, embedded NUL, int all refused with no connection and a key-free error. |
| N21 real `http.client` seam | fixed | `fake_http.py` adopted; `test_round2.py` runs the wire regressions. |

Round-1 originals: all eight still exit 1 against r1.2 (`r2-repros-vs-r1-2.txt`).

## The four bypass questions

### 1. Can `--lock-evidence` break a live lock, or dispatch? — No.

`repro_r3_lock_evidence.py`, real r1.2 driver bytes pinned as the release artifact, through both the
adapter CLI and the host CLI, real PIDs (no `os.kill` mocking):

- Lock present → `lock_recovery_lock_present`, exit 2, lock bytes untouched, ledger untouched, no
  transport, dummy `--attempt-dir` never claimed. The route never unlinks anything.
- Lock removed but evidence PID is this process (alive) → `lock_recovery_owner_alive`; PID 1
  (EPERM) → same; foreign host, `pid` 0 / −1 / `true` / string, `owner_gone: "true"`, upper-case
  hash → `lock_recovery_evidence`. In every case no lock is created and no GET is made.
- Race: a lock appearing between the existence check and `recover()` → `FileExistsError` → exit 3,
  the racer's lock intact, ledger unchanged.
- Valid (reaped child PID), unmarked crash → exit 0, "no dispatch performed", exactly
  `LOCK_RECOVERED, RESOLVE(dispatched=false, debit=0)` appended, evidence hash recorded, no POST,
  no GET, lock released, dummy job id absent from the ledger. A fresh normal invocation afterwards
  dispatches once (an unmarked recovery is not a completion, as designed).
- Valid, marked crash (SIGINT mid-POST through the host CLI) → exit 0, `LOCK_RECOVERED,
  RESOLVE(dispatched=true, FLOOR), HALT`, 4 GETs, 0 POSTs, bundle hash on every reconciliation
  receipt; the next normal invocation is refused `admission:halted` with no transport.
- The SIGINT traceback has no key and no `http.client` frames (N16 holds end to end).

What the CLI cannot do is verify the evidence against the lock it can no longer read; that is the
operator's documented responsibility, and the PID check is a sanity gate rather than a proof. The
cheap hardening in N25 would narrow the one operator-error case I could think of.

### 2. Does the 900 s timeout interact badly with reconciliation timing? — No.

`repro_r3_timeout_recon.py` with the fake clock advancing by `TIMEOUT_S` inside a "hanging" callback:

- POST blocks the full envelope then fails: `resolved_at` is stamped *after* the envelope, the four
  reads land at `resolved_at + {0, 60, 300, 900}` with `elapsed_s ≥ due`, verdict HALT
  `KEY_USAGE_UNRECONCILED` (no reported cost to match), one POST, and a charge the provider
  posted meanwhile is captured through the key delta: debit = 500,000,000 nanoUSD > FLOOR, HALT
  reason `debit_exceeds_floor` (it outranks the reconciliation verdict; correct and pre-existing).
- First reconciliation GET blocks then fails: slot 0 consumed as `read_failed` with `elapsed_s = 0`
  (measured before the GET, so the frozen "read before its scheduled time" rule cannot fire), slot 60
  runs immediately with `elapsed_s = 900`, RECONCILED after two reads, state 13.
- All four GETs block: four failed receipts, five GETs total, no fifth read, HALT, FLOOR.
- Preflight GET blocks: `pre_dispatch_pause`, no RESERVE, zero debit, no POST.

Nothing in the frozen `reconcile` has an upper bound on elapsed time, so late reads are never
penalised. See N27 for the wall-clock consequence.

### 3. Can the TLS context still fall back to the default store or skip verification? — No.

`repro_r3_tls_context.py`, real `ssl`:

- `/etc/ssl/cert.pem`: regular file, uid 0, `-rw-r--r--`, 128 PEM blocks, `x509_ca = 128`;
  `CERT_REQUIRED`, `check_hostname`, minimum TLS 1.2, no keylog; `r17_ca_sha256 = sha256(file)`.
  A bare `PROTOCOL_TLS_CLIENT` context on the same host has 0 anchors (the round-2 bug).
- With `load_default_certs`, `set_default_verify_paths`, `create_default_context` and
  `_create_default_https_context` all patched to raise, the context still builds with the same
  anchors and `post_once` still succeeds; `HTTPSConnection` receives exactly that context; only
  `OPENROUTER_API_KEY` is read from the environment.
- `SSL_CERT_FILE`/`SSL_CERT_DIR` pointed at a synthetic CA (also set in the real process
  environment for OpenSSL itself): anchors unchanged, synthetic CA not among `get_ca_certs()`.
- Leaf-only bundle (`CA:FALSE`): store stats `x509 = 1, x509_ca = 0` → `tls_no_trust_anchors`;
  the `x509_ca` key is the right one. Missing, empty and mid-load-changed bundles all refuse before
  any connection (`transport_failed` at the seam, `tls_bundle_changed` for the swap).
- A `CERT_NONE` context injected at `_tls_context` is refused (`tls_unverified`) before connecting.

A one-CA bundle loads, so the check is a count: a replaced `/etc/ssl/cert.pem` is detectable only
through the `tls_ca_sha256` receipt (root-owned file; see N28 for the pre-run step).

### 4. Did the key-hygiene changes leave a path where the key reaches an exception or receipt? — No.

`repro_r3_key_hygiene.py`: TLS-context failure, send `OSError`, read timeout, peer close before the
status line, key echoed in the body, key echoed in a permitted header (both an `sk-or-` key, which
`filter_headers` drops before the echo check, and a prefixless key, which trips
`response_sensitive`), oversize body, `close()` raising, and `KeyboardInterrupt` / `SystemExit` /
`BaseException` on send or in `close()`: for both callbacks the raised object is of the expected
type, carries no key in args/attrs, has no `__context__`/`__cause__`, no `http.client` frame, and no
key in any non-reviewer frame's locals (`capture_locals=True`). End to end through the adapter: an
echoing body is never stored (`response.body` empty, status `null`, FLOOR, bundle hash present); a
TLS failure at the POST leaves `status.json` without the hash and makes 0 POSTs; no file under
`run/` and nothing on stdout/stderr contains the key; `status.json` has only the five expected
fields. `del key` in `_request`/`post_once`/`key_info` never raises on any early exit (all names are
pre-bound).

## Notes (none above NOTE)

- **N22 — repeated `--lock-evidence` appends `LOCK_RECOVERED` with nothing pending.** Each
  invocation writes one more entry (`repro_r3_lock_evidence.py` §6 shows two). `ledger_shapes` and
  the frozen `admit` ignore the type, so it is audit noise only. Optional: refuse when
  `recovery_calls()` is empty.
- **N23 — the suite depends on an excluded, unpinned directory.** `test_round2.py`'s S6 copy test
  reads `_out/round2-repros`, which `_out/prepare.py` created and `run_tests.sh` does not create.
  A checkout without `_out` fails the suite and therefore `verify_ready.py`. `_out` is not
  git-ignored, so it will likely be committed, which also versions the "excluded" logs. Suggest
  the test build its own copies under `_out`, or pin them as payload like `repros/`. Related:
  READY now pins `adapter-review-r2/*.py|*.sh` and its `REVIEW.md` as dependencies, so my round-2
  folder must stay frozen (it is; all 83 dependency pins verify).
- **N24 — `--lock-evidence` still demands `--attempt-dir`, `--job-id` and `--cell`.** They are
  unused on that route (verified: no claim, no job id in the ledger). Usability only.
- **N25 — pre-existing, not from the diff:** `Ledger.lock`'s `finally` unlinks `ledger.lock`
  without checking it still owns it. In the operator-error case (lock removed while the owner is
  alive and a dead PID supplied) the live owner can unlink the recovery's lock; both ends then fail
  closed (`ledger_tail_changed` / exit 4), and the ledger stays consistent. Cheap hardening if
  wanted: unlink only when the lock file's `pid` is `os.getpid()`.
- **N26 — specific TLS/credential refusals surface as `transport_failed`.** `credential_unavailable`,
  `tls_no_trust_anchors`, `tls_bundle_changed`, `FileNotFoundError` on the bundle all collapse to
  the generic code at the seam (correct for key hygiene, unchanged from r1.1). On the Mini a
  pre-flight failure is therefore indistinguishable from a network failure at the CLI; keep the
  H11 standalone bundle check in the runbook. `verify_flags` is `VERIFY_X509_TRUSTED_FIRST` only
  (no `STRICT`/`PARTIAL_CHAIN`, which `create_default_context` would add); not a bypass.
- **N27 — wall-clock envelope.** With every operation at the envelope a cell can hold the lock for
  POST 900 + schedule 900 + 4 × 900 GET = 5,400 s (1.5 h); the 900 s also applies to connect. H13
  (run detached, never Ctrl-C) matters more now, and the provider/CDN idle-limit check stays the
  primary's P1 gate as SPEC says.
- **N28 — pre-run bundle evidence.** Record `sha256(/etc/ssl/cert.pem)` and `cert_store_stats()`
  on the Mini before the run so the per-receipt `tls_ca_sha256` can be compared to a value captured
  outside the run (the receipts alone only prove consistency within the run).

## Files written

- `adapter-review-r3/REVIEW.md` (this file)
- `adapter-review-r3/_load.py` — round-2 loader pointed at `adapter-r1-2`; temp dirs under this folder
- `adapter-review-r3/run_all.sh`, `results.txt` — the five round-3 repros (all exit 0)
- `adapter-review-r3/repro_r3_lock_evidence.py` — question 1 (§1–§10)
- `adapter-review-r3/repro_r3_timeout_recon.py` — question 2 (A–D)
- `adapter-review-r3/repro_r3_tls_context.py` — question 3 (needs `openssl` CLI for §3)
- `adapter-review-r3/repro_r3_key_hygiene.py` — question 4 (§1–§3)
- `adapter-review-r3/repro_r3_s6_pins.py`, `suite-output-r3.txt` — S6; runs `adapter-r1-2/run_tests.sh` once
- `adapter-review-r3/r2-repros/` — byte-identical copies of the round-2 repros and round-1
  originals; only the two `_load.py` import paths changed; `r2-repros-vs-r1-2.txt` is their output

Temporary directories (`.review-r3-*`) are removed; no `__pycache__` (`-B`). `adapter-r1-2/_out/`
was written by the suite run only (`repro-r1-2.txt` and temp dirs); nothing outside `_out` changed.
