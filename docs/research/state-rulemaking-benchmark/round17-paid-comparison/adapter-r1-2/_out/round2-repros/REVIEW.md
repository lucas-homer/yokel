# R17 P3 dispatch adapter r1.1 + host driver — round-2 review

Reviewer: Claude Fable 5.1 (review sub-agent), 2026-10-13. Scope: `adapter-r1-1/r17_adapter.py`
(sha256 `0f04829d…8f1e`), `adapter-r1-1/host_driver.py` (`26e179ec…9366`), the four test files,
`SPEC.md`, `READY.json`, against `design-r3-1/PROTOCOL.md`, `design-r3-1/BUDGET.md`,
`design-r3-1/fixtures/r17recon.py` (`5295a667…e33ff`), `PRIMARY-DECISIONS.md` Q2, my round-1
`adapter-review/REVIEW.md`, and `reference/E8-SUFFICIENCY.json` (the only file read in `reference/`).

Method: `diff -u adapter/r17_adapter.py adapter-r1-1/r17_adapter.py` read line by line; full read of
`host_driver.py` and all tests; Sol's suite re-run under `python3 -I -S -B` (102 + 26 + 23 + 9 = 160
OK); my eight round-1 repros copied unchanged into `orig-repros/` with only the `_load.py` import
path changed and re-run against r1.1; seven new repros. The host driver was attacked through the
**real `http.client` request/response machinery over a fake socket** (`_load.py`), not through a
dummy connection class, so wire bytes, framing, 1xx handling and exception types are the stdlib's.
No network, provider or credential access: `os.environ` is replaced by a synthetic mapping holding
a synthetic key string; `http.client.HTTPSConnection` is replaced at the module seam. Source texts
(`sources-r2/*/parsed-body.txt`, `original.htm`) were not opened. Only `adapter-review-r2/` was
written, with one exception reported below.

**Side effect, disclosed.** Running Sol's own `test_repros.py` rewrites the pinned file
`adapter-r1-1/repro-r1-1.txt` (it is the test's output and embeds a random temp-dir name). My suite
run did that once; I restored the pre-run bytes (same text, temp token `.review-9rzvzrcd`). The file
did **not** match its `READY.json` pin before I touched it either; see S6. Every other r1.1 file
matches its pin.

## Verdict

**Fix first, then pin.** No BLOCKER: I could not construct a second POST, a POST past a refusing
admission or before a durable DISPATCH_MARK, bytes sent that differ from the guarded bytes, a debit
below `max(FLOOR, …)`, or a key reaching a receipt, exception text, traceback, stdout/stderr or argv.
The round-1 SHOULD-FIX items are fixed. Three new SHOULD-FIX items are cheap and each closes a path
that is fail-closed for money but would kill the experiment or send the operator down an unpinned
path: **S4** the 60 s socket timeout against a non-streaming 16,384-token generation (terminal
HALT, FLOOR charged, run dead after cell 1); **S5** no CLI route for lock-evidence recovery after
the SIGINT/crash path the design itself produces; **S6** a stale READY pin that `release_gate` would
refuse, created by a verification step that mutates a pinned file.

## Round-1 findings: status against r1.1

Evidence: `orig-repros-vs-r1-1.txt` (all eight original repros now exit 1 = not reproducing;
baseline 8/8 reproduced against `adapter/` in round 1), plus the diff and the new regression tests.

| # | Status | Evidence in r1.1 |
|---|---|---|
| S1 headers verbatim | **FIXED** | `filter_headers` in both modules (`r17_adapter.py:76-90`, `host_driver.py:29-42`), applied at `:983` before `status.json`; allowlist + `x-ratelimit-*`, lower-case, 1,024 cap, CR/LF and bearer/sk-or-/authorization/set-cookie values dropped. `repro_headers_leak.py` → token absent. Driver also refuses a body/header echoing the key (`:76-77`). |
| S2 no tail re-check | **FIXED** | `Ledger.offset`/`tail_hash` recorded on `load` (`:311-312`), `assert_tail` (`:338-349`) runs on the append descriptor before every write and once more at `:972` before DISPATCH_MARK. `repro_double_post_lock_break.py` → 1 POST, clean chain. Residual: sub-millisecond window between the fstat/read and the write under a deliberately broken lock; documented in SPEC as not a CAS. |
| S3 SKIP while pending bricks ledger | **FIXED** | Gate hash enters RESERVE (`:930-931`), checked on pending reads (`:541-543`), before the mark (`:962`, `:969-971`), and `staged_gate` refuses to SKIP while anything is pending (`:578`). `repro_gate_change_bricks_ledger.py` → zero-debit RESOLVE, `recover()` OK, fresh job dispatches. |
| N1 incomplete receipt | **FIXED** | `recovery_calls` (`:116-130`) shared by `execute_once`, `recover` and the CLI; a valid-JSON `{}` final is not a completion (`final_receipt` shape). Repro → `recovery_required`. |
| N2 `marked` lags | **FIXED** | `marked = True` before the append (`:973`); `append` records bytes after `flush` and before `fsync` (`:331-334`). Repro → 0 POSTs, recoverable, debit ≥ FLOOR. |
| N3 recover re-HALTs | **FIXED** | `normally_stopped` in `recovery_calls`; no duplicate HALT (`:1126`). Repro → `[]`, identical ledger. |
| N4 torn receipt | **FIXED** (as scoped) | `receipt(repair=True)` sidecars + unlinks damaged status/recon/claim/final receipts (`:93-113`); a damaged GET receipt consumes its slot. Interior ledger corruption still refused, as SPEC states. |
| N5 negative sleep | **FIXED** | `max(0, min(60, …))` (`:195`). |
| N6 wall clock | DEFERRED, documented | H10 NTP evidence remains external. |
| N7 FULL rule ids | DEFERRED, documented | Moot for the 3-call plan (no FULL cells). |
| N8 parse before size | **FIXED** | `:714` and `:1105`; driver cap independent. |
| N9 UTF-8 assumption | **FIXED** | `:715`, `:723-726`. |
| N10 `hook` seam | DEFERRED, documented | Neither CLI passes it. |
| N11 F_FULLFSYNC | DEFERRED, documented | |
| N12 SPEC wording | **FIXED** | |
| N13 diagnosability | **FIXED** | Exit codes 0/1/2/3/4; fixed strings only (`:1188-1205`). See N18. |

Diff review (`adapter` → `adapter-r1-1`, 426 lines): no regression found. Points checked: `verify()`
restores offset/tail on failure (`:353`, `:361`); `load(repair_tail)` sets offset before the RECOVER
append; the unmarked-exception branch converts an append refusal into `recovery_required` rather than
leaving a half state (`:1059-1063`); `_main`'s probe/recover/admission phases are lock-free between
each other but `execute_once` re-validates everything under its own lock and a competing invocation
gets `FileExistsError` → exit 3; `recovery_calls` makes a crash after RESOLVE/RECONCILED but before
`completed.json` terminal (SPEC-documented trade-off; also means any Ctrl-C after the mark ends the
experiment, see N20).

## New findings

### SHOULD-FIX

**S4. `TIMEOUT_S = 60` is a per-operation socket timeout against a non-streaming generation of up
to 16,384 tokens.** `host_driver.py:20`, `:62`. With `stream: false` the provider sends no bytes
until the whole completion is generated, so a long generation is indistinguishable from a dead
peer; `getresponse()` raises after 60 s of silence, the driver returns `transport_failed`, the
adapter records row 2 → RECON (15 min of reads) → terminal HALT with debit FLOOR, and admission is
refused for every later cell (`halted`). The request was fully written and is billed. The only
empirical bound we hold is R14: `round14-semantic-contract/runtime/adapter.py:111` used
`timeout=180` for `max_tokens` 8192 and the 7,231-token response completed inside it; R14's job
proposals set `timeout_seconds: 1800`. R17 doubles the output cap and cuts the timeout to a third.
A timeout never causes a retry, so a long timeout costs nothing in safety. Fix: raise to at least
600 s (prefer the 1,800 s job envelope), keep connect bounded separately if desired, and have P1
confirm from provider documentation that the non-streaming route keeps the connection open for
that long (CDN idle limits). Repro: `repro_hd_timeout_row2.py` — reproduces (1 POST on the wire,
state 2, debit 270,000,000, HALT, next cell refused).

**S5. The pinned CLI has no route for lock-evidence recovery; the path the design itself
produces leaves the operator with only an ad-hoc library invocation.** `r17_adapter.py:1136-1185`,
`host_driver.py:168-181`. On SIGINT (or any `BaseException`) after RESERVE, `Ledger.lock` correctly
retains `ledger.lock` as crash evidence (`:262-269`); the next CLI run exits 3 forever. BUDGET §4
rule 10 then requires evidence + `LOCK_RECOVERED` as the next entry, which only
`recover(lock_evidence=…)` can write, and neither CLI exposes it (SPEC H8 says so). The operator must
therefore run unpinned Python under `-I -S -B` that imports the adapter and passes the real
`key_info` — exactly the kind of unreviewed step this design exists to remove — or delete the lock
and re-run the CLI, which recovers *without* `LOCK_RECOVERED` (rule 10 silently unenforced; no money
risk). Fix: `--lock-evidence <path>` on both CLIs, honoured only when no lock file exists, requiring
`owner_gone: true` plus the removed lock's `pid`/`host` and the lock file's sha256. Repro:
`repro_hd_sigint_cli.py` §1–§3 — reproduces (lock retained, exit 3, library-only recovery; also
shows the SIGINT path is otherwise safe: one interrupted send, no re-send, no key in the traceback or
on stderr, LOCK_RECOVERED → RESOLVE(FLOOR) → HALT, then exit 2).

**S6. `READY.json` pins a file the verification procedure rewrites; the pin was already stale on
arrival and `release_gate` would refuse it.** `READY.json` `files["repro-r1-1.txt"].sha256 =
15ba39a1…` versus the file's actual `f29cc8e4…` (same 4,477 bytes; the difference is the random
temp-dir token inside the N3 traceback). `test_repros.py:18` writes `repro-r1-1.txt` on every run,
so running `run_tests.sh` — the documented verification — invalidates the freeze. `release_gate`
(`r17_adapter.py:448`) calls `freeze()` on the `adapter_ready` artifact and rehashes **every**
entry of its `sha256` map (`:378-384`), so a release pointing `adapter_ready` at
`adapter-r1-1/READY.json` fails with `freeze_pin` today. Fail-closed, but it invites hand re-pinning
at P7. Fix: write test output outside the pinned tree or exclude it from `files`/`sha256`; scrub
temp paths; run `pin_ready.py` after the final test run and assert the tree is unchanged by a
re-run; then re-pin. Evidence: `shasum -a 256 adapter-r1-1/repro-r1-1.txt` against `READY.json`
(all 21 other pins verify).

### NOTE

**N14. Trust anchors.** On this python.org 3.13 build `_tls_context().cert_store_stats()['x509']`
is **0**: `load_default_certs()` finds no bundle unless the operator ran "Install Certificates" or
set `SSL_CERT_FILE`. The driver's `tls_unverified` check (`host_driver.py:60`) passes with an empty
store; every handshake then fails → preflight GET fails → `pre_dispatch_pause`, zero debit, generic
exit 2. Conversely OpenSSL honours `SSL_CERT_FILE`/`SSL_CERT_DIR`, invisible to the Python-level
`os.environ` fake in Sol's tests, so an env-supplied bundle silently becomes the only anchor. Fix:
refuse `tls_no_trust_anchors` when the count is 0, and record in the release which bundle the Mini
uses (H11 below). Repro: `repro_hd_trust_store.py` — reproduces (0 anchors; 1 synthetic anchor after
`SSL_CERT_FILE`).

**N15. `host_driver.main` hard-codes its own filename.** `host_driver.py:179-180` hashes
`HERE / 'host_driver.py'`; SPEC's own CLI example names the file `reviewed-host-driver.py`. A renamed
copy dies with `FileNotFoundError` (raw traceback, exit 1) before any adapter call; an adapter import
failure (`dependency_pin:*`) also escapes raw. Fail-closed and key-free (env never read), but outside
the exit-code discipline N13 introduced. Use `Path(__file__).resolve()` and wrap `main()`. Repro:
`repro_hd_cli_misc.py` §3–§4.

**N16. The key survives in the raised exception's frame locals.** `_request` raises `DriverError`
while `key` and `headers` are live locals; `traceback.TracebackException(capture_locals=True)` and
debuggers show them. The default excepthook and `format_exc()` do not (verified in
`repro_hd_sigint_cli.py` and `repro_hd_wire.py` §4). `del key, headers` before `raise`.

**N17. `parse_usd` precision (pinned recon, informational).** Default `Decimal` context is 28
digits; a token with more significant digits is rounded half-even before the ceiling
(`1.0000000000000000000000000000001` → 1,000,000,000 not 1,000,000,001). Never reachable for USD
amounts under $2 reported to ≤ 19 decimals. No action; do not re-pin for this.

**N18. `main()` collapses every `admission:*` refusal to `gate_refused`.** `r17_adapter.py:1196-1200`.
"halted", "operating limit", "key capacity" and "call already completed" print identically; the
strings are static recon literals and safe to print. Add `admission:*` to the safe set.

**N19. Key with trailing newline/space** (typical of `export KEY=$(cat file)`) is refused as
`credential_unavailable` → surfaces only as `pre_dispatch_pause`. Correct and safe; runbook item.

**N20. Any `BaseException` after DISPATCH_MARK is terminal for the experiment**, including Ctrl-C
during the up-to-15-minute reconciliation after a *successful* POST (lock retained → recovery →
HALT by design). Run under `nohup`/`caffeinate`, never interrupt; stated in SPEC only implicitly.

**N21. `test_host_driver.py` never exercises `http.client`.** `Factory` replaces `HTTPSConnection`
with a recorder, so exact wire bytes, duplicate `Content-Length`/`Host`, 1xx handling, chunked
framing and the real exception types are untested by the suite. `_load.py` here drives the real
client over a fake socket; adopt it (or equivalent) before pinning.

## Host driver: attacked and verified (no finding)

All through the real `http.client` (3.13.7) over a fake socket, `repro_hd_wire.py`:

- **Exactly one request per call.** `HTTPConnection.putrequest` raises `CannotSendRequest` after the
  first; `auto_open` only connects on the first `send`; the stdlib has no retry code (grep of
  `http.client.HTTPConnection` source). Broken pipe mid-send, remote disconnect before the status
  line, and body-read timeout each produce one attempt and `transport_failed` with `__context__`
  `None`. The driver discards the connection object; a fresh TLS session per call.
- **Bytes.** Body on the wire is the exact `exact_bytes` object; one `Content-Length` equal to its
  length, one `Host: openrouter.ai`, `Content-Type: application/json`, `Connection: close`,
  `Accept-Encoding: identity`, no `Expect`, no `Transfer-Encoding`.
- **1xx.** A server `100 Continue` preamble is consumed by `HTTPResponse.begin()`; still one POST.
- **Redirects** (302/307) are returned as the status; `Location` is not forwarded.
- **Proxy.** `http.client` has no proxy machinery; with `HTTPS_PROXY`, `ALL_PROXY` and
  `SSLKEYLOGFILE` present, the only environment name read is `OPENROUTER_API_KEY`, once per callback.
- **TLS.** `CERT_REQUIRED`, `check_hostname`, `keylog_filename None`, minimum TLS 1.2; the
  `tls_unverified` self-check is real. Caveat N14.
- **Bounded body.** `read(MAX_RAW + 1)` sentinel across Content-Length, chunked and close-delimited
  framing; 2,000,007-byte bodies refused after one request; exactly 2,000,000 accepted; largest
  single read request 2,000,001.
- **Key hygiene.** Not read at import (`repro_hd_cli_misc.py` §5); refused if non-ASCII, empty or
  containing whitespace before any connection; absent from packet repr, `DriverError` text,
  `format_exc()` output, stdout/stderr of the CLI on failure and every receipt under `run/`
  (SIGINT and timeout paths). Echo of the key in a body or permitted header → `response_sensitive`.
- **`key_info`.** One GET, no body; `data` envelope unwrapped; only the four fields emitted; raw
  numeric tokens preserved verbatim (`0.10`, `1e-9`, `1E-10`, `-0`, `1.730e0`, 19-digit integers,
  `0.3`) and parsed by the pinned `parse_usd` to the expected nanoUSD; `response_sha256` over the
  original bytes; duplicates, NaN, quoted numbers, numeric/over-long `limit_reset`, BOM, missing
  envelope, non-200 all refused without chained context (`repro_hd_key_fields.py`).
- **CLI.** `--driver`/`--driver-sha256` in any spelling refused; user argv forwarded verbatim plus
  the driver's own path and hash; `recover_first=True`; `--cell` restricted to `CALLS`; lock present
  → exit 3 with the lock untouched; after recovery of a marked cell → refusal before any source read
  or POST (`repro_hd_sigint_cli.py` §2, §4).
- **SIGINT mid-POST.** One interrupted send, connection closed in `finally`, no re-send, lock
  retained, tail = DISPATCH_MARK, no `RESOLVE`, no sidecar (the `except Exception` branches are
  skipped), traceback key-free, next CLI exit 3; recovery with evidence writes LOCK_RECOVERED →
  RESOLVE(dispatched, FLOOR) → HALT with 4 GETs and 0 POSTs. See S5 for the operational gap.

## 3-call plan (E8: typed logic untestable, FULL omitted)

`repro_3call_plan.py`, release with `typed_testable: false`, `required_calls = [S1-OPQ, S2-OPQ,
S3-OPQ]`, manifest compounds 1/2/1 (pooled 4) as in `E8-SUFFICIENCY.json`:

- Happy path: admission R = 3, 2, 1; three POSTs; aggregate 3 × FLOOR; no SKIP; afterwards every
  cell refused by `recon.admit` (OPQ "already completed", FULL "not a required call"); `S1-FULL`
  refused at `release_call_set`, a repeat `S1-OPQ` at `wrong_cell_order`.
- Key limit: `key_limit_ok(3·FLOOR, 3)` true and all three cells dispatch at L = $0.81 exactly;
  L = 3·FLOOR − 1 refused at `release_gate` (`key_limit`) and by `recon.admit` ("key capacity").
- Semantic futility after S1: SKIP exactly `S2-OPQ`, `S3-OPQ` with `OPQ-semantic-futility`.
- Mechanical futility on S1 (`finish=length`, state 11): SKIP exactly `S2-OPQ`, `S3-OPQ` with `D1`.
- Consistency: a 6-call release against a 4-compound manifest → `manifest_slots`; a 3-call release
  against a 5-compound manifest → `P6_E8_counts`; INIT listing six calls while the release lists three
  → `required_calls`.

Nothing in the adapter assumes six cells: `required_calls` is read from INIT/release everywhere
(`ledger_shapes`, `staged_gate`, futility SKIP loops, `admit`). Sol's suite also has
`test_p9_omits_full_and_reserves_only_three_calls`.

## Host-driver requirements: H1–H10 status, plus additions

H1 ✓ (verified at the wire) · H2 ✓ · H3 ✓ · H4 ✓ with N14 · H5 ✓ · H6 ✓ (live field/units still P1's)
· H7 ✓ (synthetic tree only; real `sources-r2/READY.json` has `selected` = 039/041/106 and the adapter
cross-checks the hash) · H8 **partial** → S5 · H9 ✓ but S6 blocks the freeze today · H10 external.

- **H11 trust bundle.** Before the run on the Mini: `python3 -I -S -B -c` that builds the driver
  context and prints `cert_store_stats()`; require `x509 > 0`; record which bundle (python.org
  "Install Certificates", or an explicit `SSL_CERT_FILE` path + sha256) in the release; never set
  `SSL_CERT_FILE` to anything unvetted and never disable verification.
- **H12 timeout envelope.** Set `TIMEOUT_S` per S4 and document the provider's non-streaming idle
  limit from the P1 documentation capture.
- **H13 interruption discipline.** No Ctrl-C after the CLI prints nothing for a while; run detached;
  if a lock is ever retained, follow the rule-10 evidence procedure through the (to-be-added)
  `--lock-evidence` route, not an ad-hoc import.
- **H14 verification without mutation.** P7 verifies pins on a tree that `run_tests.sh` has not
  touched since `pin_ready.py` ran (S6).

## Files written

- `adapter-review-r2/REVIEW.md` (this file)
- `adapter-review-r2/_load.py` — loads r1.1 adapter, harness and driver by absolute path; fake
  socket + real `http.client`; synthetic environment
- `adapter-review-r2/run_all.sh` — runs the seven new repros, then the original eight against r1.1
- `adapter-review-r2/results.txt` — output of `run_all.sh` on 2026-10-13
- `adapter-review-r2/repro_hd_wire.py` — wire bytes, one request, 1xx, redirects, broken pipe,
  bounded body, key_info GET, TLS context (asserts good behaviour; exit 0)
- `adapter-review-r2/repro_hd_timeout_row2.py` — S4 (exit 0 = reproduces)
- `adapter-review-r2/repro_hd_sigint_cli.py` — SIGINT mid-POST through the CLI; S5 (asserts; exit 0)
- `adapter-review-r2/repro_hd_trust_store.py` — N14 (exit 0 = reproduces; needs `openssl` CLI)
- `adapter-review-r2/repro_hd_cli_misc.py` — CLI override/routing; N15 (asserts; exit 0)
- `adapter-review-r2/repro_hd_key_fields.py` — H6 decimal/envelope; N17 note (asserts; exit 0)
- `adapter-review-r2/repro_3call_plan.py` — 3-call plan A–E (asserts; exit 0)
- `adapter-review-r2/orig-repros/` — byte-identical copies of the round-1 repros; `_load.py`
  points at `adapter-r1-1`; `orig-repros-vs-r1-1.txt` is their output (all exit 1)

Temporary directories are created under `adapter-review-r2/` and removed; no `__pycache__` (`-B`).
