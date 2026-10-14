# R17 P3 dispatch adapter — independent correctness and safety review

Reviewer: Claude Fable 5.1 (review sub-agent), 2026-10-13. Scope: `adapter/r17_adapter.py`
(sha256 `ef26fd3f…85b3`), `adapter/test_adapter.py` (`eca2fc4d…3808`), `adapter/SPEC.md`,
`adapter/READY.json`, against `design-r3-1/PROTOCOL.md`, `design-r3-1/BUDGET.md`,
`design-r3-1/fixtures/r17recon.py` and `PRIMARY-DECISIONS.md` Q2.

Method: full read of the adapter and tests; line-by-line trace of the dispatch path, the
exception paths and `recover()`; pin verification by `shasum`; the suite re-run under
`python3 -I -S -B` (102 tests OK, 2.8 s); eight offline repro scripts using the suite's own
fakes (`run_all.sh`). No network, no provider or key call, no credential, no real transport;
`sources-r2/*/parsed-body.txt` and `original.htm` were not opened. Nothing outside
`adapter-review/` was written; the adapter was not edited.

## Verdict

**Fix first, then pin.** No BLOCKER was found under the documented host/operator contract:
I could not construct a double POST, a dispatch past a refusing admission, a POST before a
durably fsynced RESERVE + DISPATCH_MARK, a debit below `max(FLOOR, …)`, or a key leak
*while the host driver and the operator obey SPEC.md and BUDGET §4 rule 10*. Three
SHOULD-FIX items (S1–S3) are cheap, and each closes a path that depends only on a
contract violation by the host driver or the operator rather than on the adapter itself.
Because pinning freezes the adapter hash and any later fix forces re-review, fix them
before P7 pins the bytes.

## Findings

### SHOULD-FIX

**S1. Response headers are written verbatim to a durable receipt; no allowlist.**
`r17_adapter.py:857` accepts any `headers` dict and `:864-865` writes it into
`status.json`. The adapter's only defence against a credential reaching a receipt is the
promise in SPEC.md that the driver sanitizes. A driver bug that merges request headers
into the packet, or a proxy that echoes `Authorization`, writes the bearer token to disk
next to the ledger. The brief's standard is that the interface should make this
impossible, not unlikely. Fix: keep an allowlist (for example `content-type`, `date`,
`x-request-id`, `content-length`), lower-case keys, drop everything else, cap value
length, and refuse the packet (row 2 is wrong here, so record and HALT) if
`authorization`, `cookie`, `set-cookie` or a `sk-or-` prefix appears.
Repro: `repro_headers_leak.py` — reproduces (synthetic token found in `status.json`).

**S2. `Ledger.append` never re-checks the on-disk tail, so a stale writer can append
DISPATCH_MARK onto an advanced ledger and POST a cell another process already POSTed.**
`r17_adapter.py:246-258`. The last `ledger.verify(expected)` is at `:839`; between it and
the DISPATCH_MARK append at `:850` the code re-runs `release_gate` and `staged_gate`
(`:844-845`), re-reads `request.json` (`:847`) and recomputes `dispatched(plan)`, a window
of tens to hundreds of milliseconds of file I/O. Precondition: the lock was removed while
its owner was alive, which BUDGET §4 rule 10 forbids and which the adapter correctly never
does itself, so this is procedural. But the brief's rule-10 evidence step is a human
judgment ("owner gone"), the lock file records a PID that may be reused, and the cost of
closing the window is a few lines: in `append`, `os.fstat` the file, compare its size with
the byte offset recorded at the last `load`/`append`, and compare the last line's hash with
`sha(encode(self.entries[-1]))`; refuse with a fresh code if either differs. With that
check the stale writer fails closed at `:850` instead of posting.
Repro: `repro_double_post_lock_break.py` — reproduces (2 POSTs for S1-OPQ; chain then
fails `ledger_chain`). The interleaving is injected by wrapping the second `staged_gate`
call; nothing in the adapter is modified.

**S3. The post-RESERVE `staged_gate` re-check can append SKIP entries while a RESERVE is
pending and brick the ledger.** `staged_gate` is called before RESERVE (`:795`) and again
after it (`:845`). If the primary rewrites the staged-gate and report files in between
(for example re-running `decide --interim`), the second call takes the `stopped` branch,
appends SKIPs for every remaining cell including the current one (`:482-486`) and raises;
the except branch then appends `RESOLVE(dispatched=False)` (`:933-936`). `ledger_shapes`
(`:167-170`) rejects SKIP-while-pending, so every later `execute_once` **and** `recover()`
refuse with `ledger_impossible_skip`. No money is spent, but the experiment is dead and
the only way forward is manual ledger surgery, which is exactly what the chain is meant to
prevent. Fix: make the second call read-only (compare the gate/report hashes captured by
the first call and refuse on change, as `intent_changed` already does for the release), or
never append SKIP while `recon.pending(entries)` is non-empty.
Repro: `repro_gate_change_bricks_ledger.py` — reproduces.

### NOTE

**N1. `execute_once` ignores incomplete receipts that `recover()` treats as terminal.**
`recover()` HALTs any marked cell lacking `completed.json`/`stop.json`/`recovered.json`
(`:968-970`), but `execute_once` (`:790-799`) checks only `recon.pending`. A crash between
`result.json` and `completed.json` (accounting already durable) lets the next cell be
admitted and POSTed; running `recover()` afterwards would HALT the run. No overspend; the
two entry points disagree about whether the run is terminal. Repro:
`repro_incomplete_cell_allows_next.py` — reproduces.

**N2. `marked` lags the durable state.** `marked = True` is set after `append` returns
(`:850-852`). If the DISPATCH_MARK bytes reach the file but fsync raises, the except branch
believes the cell is unmarked and appends `RESOLVE(dispatched=False, debit=0)`. No POST
can have happened (the call site is after the flag), so no money is at risk, but the next
load refuses forever (`ledger_chain`, or `ledger_dispatch_debit` had the in-memory tail
been updated). Set `marked = True` before the append, or treat any exception from that
append as marked. Repro: `repro_mark_fsync_failure.py` — reproduces.

**N3. `recover()` is not idempotent for a normally halted cell.** `missing_recon`
(`:966-967`) selects a cell that ended with `KEY_USAGE_UNRECONCILED` (RESOLVE + HALT,
`stop.json` present); recovery appends a second HALT (`:1002`) and writes a
`recovered.json` claiming a recovered dispatch. Evidence-trail noise only. Repro:
`repro_recover_rehalts_completed.py` — reproduces.

**N4. Torn receipt bricks recovery.** `put` (`:104-111`) writes in place with fsync but not
write-temp-then-rename, so a power loss can leave a partially written `recon-N.json` or
`status.json`. `recover()` reads receipts by existence (`:729-731`, `:990`) and aborts on
the JSON error before writing anything. Fail closed, but no adapter path out. Repro:
`repro_partial_receipt_bricks_recover.py` — reproduces.

**N5. Negative sleep in the production clock.** `Clock.wait_until` (`:124-126`) calls
`now()` twice per iteration; if the wall clock crosses the deadline between the `while`
test and the sleep argument, `time.sleep` gets a negative value and raises `ValueError`,
which inside `poll` after a dispatch becomes an unexpected post-dispatch failure and a HALT
on an otherwise good cell. Microsecond window, so very unlikely; fix is `max(0, …)`.
Repro: `repro_negative_sleep.py` — reproduces with a patched `time.time`.

**N6. Wall clock drives the reconciliation schedule.** Elapsed seconds come from
`time.time()`; a forward NTP step shortens the real wait while `elapsed` still satisfies
`recon.reconcile`. Harmless for money (lag just means another read), but `time.monotonic()`
for the schedule with wall-clock only in metadata would be more faithful given the Mini's
recorded clock-skew history.

**N7. FULL-arm mechanical futility is labelled with OPQ rule ids.** `:906-910` writes
`rule_id` `D1`/`D5` for rows 10–12 or `completion_tokens > 13926` on a FULL cell, where
PROTOCOL §8 describes a FULL mechanical futility (T1-type, outcome O1). The SKIP vocabulary
in `ledger_shapes` (`:168-169`) has no FULL-arm id. Reporting only; the stop is correct.

**N8. Unbounded parse before the size check.** `strict(raw)` at `:617` runs before the
`MAX_RAW` test at `:656`. A multi-megabyte body is parsed in full first. The host driver
must bound the body (see H5); the adapter should test `len(raw)` first.

**N9. `raw_usage` assumes UTF-8.** `json.loads(bytes)` accepts UTF-16/32, but `:546`
decodes as UTF-8; a non-UTF-8 200 body that parses would raise inside `response_state`,
become an unexpected post-dispatch failure and HALT. Fail closed; a `try` → row 8 is
cleaner.

**N10. `hook` is a public seam on the production entry point** (`:777`, `:817`, `:836`,
`:898`, `:902`). `main()` never passes it, so the CLI is unaffected, but a host driver that
imports `execute_once` directly could. Consider stripping it or asserting `hook is None`
unless a test flag is set.

**N11. macOS fsync.** `fsync_dir`/`put`/`append` use `os.fsync`, which on Darwin does not
force the platter write; `fcntl(fd, F_FULLFSYNC)` does. SPEC already disclaims a power-loss
guarantee; worth doing on the Mini anyway.

**N12. SPEC wording.** SPEC says the wire pin is checked "against the source READY";
the code checks `sources-r2/READY.json` `upstream.wire.sha256` (`:87`), not
`round16-wire-compat/protocol-w2-1/READY.json`. Both agree (see Verified), so this is a
documentation precision point.

**N13. Diagnosability.** `main()` swallows every exception into one generic line
(`:1041-1043`), including `FileExistsError` for an existing lock and `Refused` codes. Good
for secrets; the operator cannot tell a stale lock from a refusal without reading
receipts. Printing the `Refused` code (static strings) is safe.

## Verified (no finding)

- **One POST call site**, `:855`, outside every loop; callback exceptions become row 2 and
  cannot re-enter it. `recover()` has no transport parameter. `grep "post("` confirms.
- **Order of operations**: lock `:790` → load `:791` → pending refusal `:792` →
  `release_gate` `:793` → `staged_gate` `:795` → job-id reuse `:796` → `recon.admit` `:797`
  → exclusive claim `:799` → key preflight `:803-812` → RESERVE `:813` → plan/dispatched
  body/release pin `:820-825` → intent `:835` → chain + aggregate verify `:839` →
  determinism `:840` → intent/release unchanged `:841` → gates again `:844-845` →
  immediate guard `:847-849` → DISPATCH_MARK `:850` → POST. `append` fsyncs file then
  directory before returning. The harness's `post` re-reads the ledger from disk and
  asserts the last entry is DISPATCH_MARK.
- **Guarded bytes are the sent bytes**: `actual` is an immutable `bytes` read back from
  `request.json`, required equal to `dispatched(plan)`, equal in hash to the intent and
  the release's `dispatched_body_sha256`, and `len(actual)+1024 ≤ 40000`, then handed to
  `post` unchanged. `dispatched()` changes only `max_tokens` 8192→16384, verifies the
  originating plan hash, and `validate_response` receives the unmodified plan (`:668`).
  The adapter's `encode` is byte-identical to r14 `common.encode`.
- **Admission refusals** all route through the pinned `recon.admit` (`:797`) and are
  additionally enforced earlier: UNSET/mismatched policy at `:306`, `:308`, `:330`
  (BUDGET literal slot), `:336-337` (both READY records), BIND_RELEASE at `:320-324`,
  order at `:442`, HALT via `admit`, unreconciled prior call via `admit`, unfundable
  remainder via `admit` (operating and key capacity). Key preflight additionally requires
  usage ≥ last reconciled and within `count×1000` of Σ reported (`:810-811`).
- **Debit** is `recon.debit(reported, p, c, key_delta)` on every dispatched path
  (`:890`, `:993`); money arrives only as exact JSON tokens via `Number`/`parse_usd`
  (`:53-67`, `:512-514`), never floats; bools are excluded by `type(...) is int`;
  `recover_terms` walks the whole body including error envelopes; rows 2–9 and plain-text
  error bodies fall back to `FLOOR` and the attributable key delta; any term above FLOOR
  halts (`:894-895`).
- **RECON** reuses `recon.reconcile` and `READ_SCHEDULE_S` (`:726`, `:752`); stale zero
  consumes four reads then halts; regression, limit change, reset and unlimited halt on
  the first read; `previous` excludes the cell's own RECONCILED (`:722`); the delta is
  attributed to the current cell (`:759`); unexplained later usage makes the next cell's
  preflight refuse with zero debit, so delayed usage is never charged to a later cell.
  Read claims (`recon-N.intent.json`) make a crashed GET consume its slot on recovery.
- **Pins**: `fixtures/r17recon.py` = `5295a667…e33ff` (file, `RECON_SHA`,
  `READY.primary.json`); `wire.py` = `662268ba…8375ab1` (file, `WIRE_SHA`,
  `sources-r2/READY.json` upstream, `round16-wire-compat/protocol-w2-1/READY.json`
  `sha256["wire.py"]`). `adapter/READY.json` hashes for `r17_adapter.py` and
  `test_adapter.py` match the files. Admission, aggregate, pending, debit, reconcile,
  close_debit and parse_usd are imported, not reimplemented; `ledger_shapes` and the key
  preflight are stricter additions, not divergences.
- **Secrets**: the adapter reads no environment variable and accepts no credential
  argument (`grep environ|getenv` → none); `key_info` packets must contain exactly
  `fields` + `response_sha256` and the fields exactly `usage, limit, limit_remaining,
  limit_reset` (`:687-691`); `Refused` codes are static strings; `main()` prints no
  traceback. The one gap is S1.
- **Tests**: 102 OK reproduced under `-I -S -B`; temp dirs only under `adapter/`.

## Test-quality notes

- `ReferenceLedgerTests` (test_adapter.py:855-872) are tautological as adapter coverage:
  `checker.L = a.recon` points check.py's own harness at the byte-identical pinned module,
  so L01–L25 prove the pin, not `ledger_shapes`, `poll`, `execute_once` or `recover`.
  READY.json should not count them as adapter integration tests.
- `Harness.post` asserting durable state from disk is a good fake. Missing fakes: a
  malformed transport packet (`status` as str, `raw` as str), a body over `MAX_RAW`, a
  UTF-16/BOM body, a slow transport (nothing exercises the real `Clock`), a header dict
  with sensitive names, a gate file rewritten mid-invocation (S3), a lock broken while the
  owner lives (S2), an fsync failure (N2), a torn receipt (N4), and `main()` itself
  (python flags, `driver_sha256` pin, driver exports) is untested.
- `test_directory_fsync_and_dispatch_mark_before_transport` checks the last two sync events
  before POST; combined with `Harness.post`'s disk re-read it does establish
  MARK-before-POST.

## Host-driver requirements (P7 must review and pin)

- **H1 single request.** `post_once(url, exact_bytes)` performs exactly one HTTP POST of
  `exact_bytes` verbatim: no re-serialization, no compression, `Content-Length =
  len(exact_bytes)`, `Content-Type: application/json`. No redirect following (return a 3xx
  as a status), no client retries at any layer (urllib3 `Retry(0)` or raw `http.client`),
  no connection-pool re-send on a broken connection, no streaming, no fallback host.
- **H2 timeouts map to exceptions**, never to a second attempt. A timeout after the
  request was written is row 2 and the adapter HALTs; the driver must not "check whether
  it went through" by re-sending.
- **H3 packet shape.** Return exactly `{status: int, raw: bytes, headers: dict}` with
  `headers` reduced to an allowlist, lower-cased, never including `authorization`,
  `cookie`, `set-cookie` or any request header (until S1 lands, the driver is the only
  guard).
- **H4 credential.** Read `OPENROUTER_API_KEY` only inside `post_once`/`key_info`, never at
  import; refuse (raise) if unset; no fallback to another variable, file, keychain or key
  label. Never log, print or embed it in an exception message; wrap transport exceptions
  into a generic exception before they cross into the adapter. Use `ProxyHandler({})` (or
  equivalent) so `HTTPS_PROXY` cannot route the request; TLS verification on; host pinned
  to `openrouter.ai`.
- **H5 bounded body.** Read at most `MAX_RAW` (2,000,000) bytes plus one and stop; the
  adapter parses before it measures (N8).
- **H6 key_info.** One GET to `/api/v1/key` per call. Unwrap OpenRouter's `data` envelope,
  emit exactly `{usage, limit, limit_remaining, limit_reset}` as JSON bytes whose numeric
  values are the original decimal tokens (slice the raw text or use `parse_float=str`
  then re-emit unquoted); never round-trip through `float`. Drop `label`,
  `is_free_tier`, `rate_limit` and every other field. `response_sha256` is over the
  original response bytes. The adapter cannot confirm that `usage` is cumulative USD; the
  P1 documentation step must.
- **H7 source.** `source(cell)` returns the exact UTF-8 text of
  `sources-r2/<id>/parsed-body.txt` and does nothing else; module import is side-effect
  free; no network before `post_once`/`key_info` are called.
- **H8 invocation discipline.** `python3 -I -S -B`; one invocation per cell; unique
  `--job-id` and a fresh `--attempt-dir` directly under `run/`; after any post-mark failure
  run `recover()` before anything else; never run two invocations or an invocation and
  `recover()` concurrently; never remove `ledger.lock` without first recording owner-death
  evidence that checks the recorded PID and host (S2 shows what a wrong call costs); do not
  rewrite staged-gate/report/OPQ-freeze/release files while an invocation runs (S3).
- **H9 release.** Pin `driver_sha256` in the release and list the driver file among the
  signed artifacts (the adapter verifies the former only); pin `adapter/READY.json`'s file
  hash externally.
- **H10 clock.** Confirm NTP sync on the Mini before the run (N5/N6).

## Files written

- `adapter-review/REVIEW.md` (this file)
- `adapter-review/_load.py` — loads the adapter and the suite's fakes by absolute path
- `adapter-review/run_all.sh` — runs every repro under `python3 -I -S -B`
- `adapter-review/repro_headers_leak.py` (S1)
- `adapter-review/repro_double_post_lock_break.py` (S2)
- `adapter-review/repro_gate_change_bricks_ledger.py` (S3)
- `adapter-review/repro_incomplete_cell_allows_next.py` (N1)
- `adapter-review/repro_mark_fsync_failure.py` (N2)
- `adapter-review/repro_recover_rehalts_completed.py` (N3)
- `adapter-review/repro_partial_receipt_bricks_recover.py` (N4)
- `adapter-review/repro_negative_sleep.py` (N5)

All repros exit 0 when the finding reproduces; `sh run_all.sh` showed 8/8 reproducing on
2026-10-13. Temporary directories are created under `adapter-review/` and removed.
