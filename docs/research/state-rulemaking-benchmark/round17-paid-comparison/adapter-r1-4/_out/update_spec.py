from pathlib import Path
p = Path(__file__).resolve().parent.parent / 'SPEC.md'
s = p.read_text()
s = s.replace('# R17 P3 dispatch adapter r1.1', '# R17 P3 dispatch adapter r1.2')
s = s.replace('adapter-r1-1/', 'adapter-r1-2/')
s = s.replace('with exactly `status` (integer), `raw` (bytes), and `headers` (sanitized dict).',
    'with `status` (integer), `raw` (bytes), `headers` (sanitized dict), and\n`tls_ca_sha256` (the SHA-256 of the explicitly loaded CA bundle). Legacy synthetic\ncallbacks may omit only this metadata field; the production host driver always returns it.')
s = s.replace('`key_info` performs one GET `/api/v1/key`, returning exactly:', '`key_info` performs one GET `/api/v1/key`, returning:')
s = s.replace('response_sha256: SHA-256 of the original endpoint response bytes}',
    'response_sha256: SHA-256 of the original endpoint response bytes,\n tls_ca_sha256: SHA-256 of the explicitly loaded CA bundle}')
s = s.replace('provided as uninvoked production code, tested solely with fake HTTPS connections',
    'provided as uninvoked production code, tested with fake HTTPS connections and real http.client over fake sockets')
s = s.replace('temporary artifacts stay under `adapter-r1-2/` and are removed. `test-output.txt` retains',
    'temporary artifacts stay under excluded `adapter-r1-2/_out/` and are removed. `_out/test-output.txt` retains')
s = s.replace('The frozen `../adapter/` is unchanged. r1.1 was copied from it into this directory.',
    'The frozen `../adapter/` and `../adapter-r1-1/` are unchanged. This r1.2 directory\nwas copied from r1.1; the following round-1 changes are inherited.')
s = s.replace('final exact counts are in test-output.txt/READY.json', 'final exact counts are in _out/test-output.txt and READY.json')
s = s.replace('with default trust roots, CERT_REQUIRED', 'with the explicit `/etc/ssl/cert.pem` bundle, CERT_REQUIRED')
s = s.replace('An externally removed stale lock still requires primary-recorded PID+host owner-death evidence and the existing recover(lock_evidence=...) interface before dispatch; CLI does not invent evidence.',
    'An externally removed stale lock requires primary-recorded evidence via `--lock-evidence FILE`; this invocation only recovers accounting and returns without dispatch. It checks a matching local host, positive PID, owner_gone true, a recorded lock SHA-256, and os.kill(pid, 0) reporting ProcessLookupError. A live PID, EPERM, unknown error, foreign host or extant lock refuses. The CLI does not invent evidence or remove a lock.')
s = s.replace('READY pins all candidate files and dependencies.', 'READY pins candidate payload files and dependencies; `_out/**` is excluded.')
s = s.replace('Only _load.py\'s adapter import path is changed to this copied directory.',
    "Only _load.py's adapter import path and temporary-output location are changed\nto this copied directory and its excluded _out folder.")
s = s.replace('suite invokes `sh repros/run_all.sh` and retains `repro-r1-1.txt`',
    'suite invokes `sh repros/run_all.sh` and retains `_out/repro-r1-2.txt`')
s += '''

## r1.2 round-2 disposition

The full round-2 REVIEW.md was read. This revision makes targeted changes to the
copied adapter and host; recon/wire authorities and release policy UNSET are unchanged.
No network/provider calls, real connections, credential access, original source-body
reads, reference reads, installs, commits, or writes outside this directory occurred.

| Finding | Disposition / regression evidence |
| --- | --- |
| S4 | Fixed: TIMEOUT_S = 900 seconds, including the POST response/read wait. The same envelope applies to connect/write and GET operations; no retry or timeout recovery resend. Fake-socket regression models 300 seconds of silence without sleeping and verifies one exact POST; beyond-envelope timeout remains transport-uncertain, FLOOR/HALT. Provider/CDN idle-limit documentation remains the primary's external P1 gate. |
| S5 | Fixed: both CLIs accept --lock-evidence FILE using the same release-pinned callbacks. This route verifies evidence/PID before recover(lock_evidence=...), then returns without source lookup, admission, attempt creation or POST. Unmarked recovery resolves zero debit; marked recovery is conservatively terminal. Tests cover dead/live PID, EPERM/unknown error, foreign host, malformed evidence and retained lock. |
| S6 | Fixed: generated logs and temporary fixtures go to excluded _out. pin_ready.py excludes _out/** and READY itself. verify_ready.py runs the entire suite, asserts every payload/dependency pin, unchanged READY bytes and unchanged payload membership before/after. The known stale r1.1 repro pin is left untouched; dependencies record its actual frozen bytes. |
| N14 | Fixed: PROTOCOL_TLS_CLIENT + load_verify_locations(cafile='/etc/ssl/cert.pem') explicitly bypasses SSL_CERT_FILE/SSL_CERT_DIR and default-root discovery. CERT_REQUIRED, check_hostname and no keylog remain. Missing/unreadable bundle, zero x509_ca or bytes changing while loading refuses before connect. The bundle's SHA-256 enters key-preflight, status and each performed reconciliation-GET receipt, including transport failures after context construction. It is never a READY/release CA pin: OS updates may change it. Fake-socket tests exercise real context construction; a separate mock verifies the exact cafile argument and empty-store refusal. |
| N15 | Fixed (trivial): derive self path from __file__; catch import/pin/file failures in host main with key-free host_driver_failure and exit 4. Renamed-copy and failed-import tests pass. |
| N16 | Fixed: del key in both callbacks; del key/headers/connection/response/raw/safe_headers in request finally. Drop original exception traceback/args/context; raise fresh key-free errors or BaseExceptions outside handlers. KeyboardInterrupt/SystemExit preserve interruption semantics and retained-lock handling. Tests inspect every driver traceback frame on transport/TLS/key-GET failures and interrupts. A caller that independently holds a key can still expose its own locals. |
| N17 | Documented/deferred: frozen recon Decimal precision >28 significant digits is unchanged; no recon re-pin. Primary must keep usage evidence within the documented precision range. |
| N18 | Fixed (trivial): explicit allowlist of pinned recon admission reasons is printable. Arbitrary/untrusted reasons still map to gate_refused. |
| N19 | Addressed by validation and runbook: spaces/newlines/controls in keys refuse before any connect with key-free errors. No trimming or repair. |
| N20 | The brief's key-validation request is fixed: reject every ASCII control (0..31 and 127) and whitespace, including leading/trailing characters. The review's distinct N20 interruption note is documented: BaseException after DISPATCH_MARK conservatively ends the experiment after recovery; run detached and avoid Ctrl-C during generation or reconciliation. |
| N21 | Fixed: pinned fake_http.py adopts Fable's real-http.client/fake-socket seam; regressions cover exact framing, one Host/Content-Length, 100 Continue, redirects, disconnect/timeouts, bounded chunked/close-delimited reads, TLS context and per-call CA receipts. |

Evidence schema for the accounting-only CLI route:

```json
{"owner_gone": true, "pid": 12345, "host": "recorded-local-host", "lock_sha256": "<64 lowercase hex>"}
```

The operator preserves the removed lock's exact hash, PID and host in this evidence
file and removes only the proven-dead lock. The adapter never removes it. Hash
authenticity is the operator's evidence responsibility; a removed file cannot be
rehashed by the CLI. os.kill(pid, 0) is rechecked at invocation time; PID reuse
refuses. All normal release/driver pin requirements and existing required CLI
arguments remain in force. Add --lock-evidence FILE to the host CLI example above.
Successful recovery exits 0 and prints that no dispatch occurred. Existing lock on
this explicit route refuses with exit 2; normal invocation still reports exit 3.
A competing owner winning the recover lock still causes exit 3.

### Round-2 repro disposition (unchanged repro assertions)

All seven Fable repros and the eight originals were copied under
_out/round2-repros. Only the two _load.py adapter import paths were adapted; copy
integrity is tested. Raw output is _out/round2-repro-output.txt.

| Repro | Exit | Interpretation |
| --- | --- | --- |
| repro_3call_plan.py | 0 | All good-behavior checks pass. |
| repro_hd_wire.py | 0 | All good-behavior checks pass, timeout now 900 and roots 128. Its unasserted capture_locals note still says True because the repro caller itself holds synthetic key/transport objects; driver-frame regressions independently prove removal. |
| repro_hd_key_fields.py | 0 | All good-behavior checks pass; N17 informational precision limit unchanged. |
| repro_hd_trust_store.py | 1 | Finding does not reproduce: 128 roots before/after synthetic SSL_CERT_FILE; synthetic CA is not trusted. |
| repro_hd_sigint_cli.py | 1 | Only obsolete assertion 'CLI exposes no lock-evidence option' fails. Interrupt, one-send, retained-lock, accounting recovery and terminal refusal checks pass. New tests exercise the actual evidence CLI route. |
| repro_hd_cli_misc.py | 1 | Its two obsolete expectations fail: renamed copy now returns normally; import error is caught. New regressions assert corrected behavior. |
| repro_hd_timeout_row2.py | 0 | Deliberately times out beyond TIMEOUT_S (now 900), so required one-send/FLOOR/HALT still holds. Its static closing text about 60 seconds is obsolete; the new 300-second silent-peer test proves S4 fixed. |
| Eight original repros | all 1 | None of the round-1 findings reproduces; behavioral tests remain passing. |

### Verification

179 suite tests pass: 102 inherited base tests (77 adapter + 25 pinned-engine
fixtures), 26 r1.1 revision/CLI tests, 23 host tests, 9 round-1 repro checks and
19 round-2 targeted tests. The 25 engine fixtures are not adapter coverage.
An additional verify_ready.py integrity test re-runs all 179 and verifies every
payload/dependency hash plus READY.json after that full run (180 distinct tests).

```text
sh adapter-r1-2/run_tests.sh > adapter-r1-2/_out/test-output.txt 2>&1
python3 -I -S -B adapter-r1-2/pin_ready.py
python3 -I -S -B adapter-r1-2/verify_ready.py
```

No CA-bundle bytes/hash are pinned. Logs, repro copies/results and setup helpers
under _out are excluded. The frozen adapter-r1-1 directory is never written.
Remaining primary gates are unchanged, with external CDN idle-limit validation
and Mini trust-bundle availability also requiring confirmation before a paid run.
'''
p.write_text(s)
