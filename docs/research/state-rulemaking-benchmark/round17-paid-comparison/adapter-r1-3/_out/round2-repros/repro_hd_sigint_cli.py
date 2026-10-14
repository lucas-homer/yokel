"""SIGINT (KeyboardInterrupt) while the POST bytes are being written, through the full
adapter CLI with the REAL host_driver bytes pinned as the release's host_driver artifact
and the real http.client over a fake socket. Then: what the operator sees, what the next
CLI invocation does, and how recovery proceeds. Exit 0 = observations match the summary
printed at the end (lock retained, no RESOLVE, no key in traceback, next CLI exit 3,
library recover() with evidence needed, then terminal).
"""
import contextlib
import io
import sys
import traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I drops the script dir
from _load import (load, install_fake_env, install_fake_transport, FakeSocket, http_response,
                   SYNTHETIC_KEY, tempdir, banner, ADAPTER)
from unittest.mock import patch

a, t, d = load()
env = install_fake_env()
problems = []


def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond:
        problems.append(what)


with tempdir() as tmp:
    h = t.Harness(tmp)
    # Real driver bytes as the pinned artifact; synthetic sources-r2 next to it for source().
    drv_dir = h.root / 'drv'
    drv_dir.mkdir()
    driver_path = drv_dir / 'host_driver.py'
    driver_path.write_bytes((ADAPTER / 'host_driver.py').read_bytes())
    pin = a.sha(driver_path.read_bytes())
    src_root = h.root / 'sources-r2'
    src_root.mkdir()
    (src_root / 'READY.json').write_bytes(a.encode(dict(selected=['synthetic-001', 'synthetic-002', 'synthetic-003'])))
    for s in ('synthetic-001', 'synthetic-002', 'synthetic-003'):
        (src_root / s).mkdir()
        (src_root / s / 'parsed-body.txt').write_bytes(t.SOURCE.encode('utf-8'))
    h.release['driver_sha256'] = pin
    h.release['artifacts']['host_driver'] = dict(path='drv/host_driver.py', sha256=pin)
    h.save_release()
    entries = h.entries()
    entries[1]['release_sha256'] = a.sha(h.release_path.read_bytes())
    h.rewrite_ledger(entries)

    def cli(job, attempt, recover_first=True):
        args = ['--cell', 'S1-OPQ', '--release', str(h.release_path), '--run-root', str(h.run),
                '--attempt-dir', str(h.run / attempt), '--job-id', job,
                '--driver', str(driver_path), '--driver-sha256', pin]
        real_execute = a.execute_once
        def execute(**kw):
            kw['artifact_root'] = h.root
            kw['clock'] = h.clock
            return real_execute(**kw)
        out, err = io.StringIO(), io.StringIO()
        with patch.object(a, 'BENCH', h.root), patch.object(a, 'execute_once', execute), \
             patch.object(a, 'Clock', lambda: h.clock), contextlib.redirect_stdout(out), \
             contextlib.redirect_stderr(err):
            code = a.main(args, recover_first=recover_first)
        return code, out.getvalue(), err.getvalue()

    banner('1. SIGINT arrives while the POST is being written')
    key_raw = b'{"data":' + t.packet(0)['fields'] + b'}'
    tr = install_fake_transport([FakeSocket(http_response(200, key_raw)),             # preflight GET
                                 FakeSocket(b'', fail_send=KeyboardInterrupt())])      # POST interrupted
    err = io.StringIO()
    try:
        with contextlib.redirect_stderr(err):
            cli('job-sigint', 'S1-OPQ-a')
        check(False, 'KeyboardInterrupt should propagate out of main()')
    except KeyboardInterrupt:
        text = traceback.format_exc()
        check(SYNTHETIC_KEY not in text, 'default traceback text carries no key')
        check(SYNTHETIC_KEY not in err.getvalue(), 'nothing on stderr carries the key (stderr=%r)' % err.getvalue()[:80])
        print('     traceback frames:', [l.strip() for l in text.splitlines() if l.strip().startswith('File')][-3:])
    posts = [w for w in tr.wire() if w.startswith(b'POST ')]
    check(len(posts) == 1 and len(tr.sockets) == 0, 'one (interrupted) POST attempt, no re-send')
    check(tr.connections[-1].fake.closed, 'connection closed in finally')
    check((h.run / 'ledger.lock').exists(), 'ledger.lock RETAINED (crash evidence; adapter never unlinks on BaseException)')
    types = [e['type'] for e in h.entries()]
    check(types[-1] == 'DISPATCH_MARK', 'ledger tail is DISPATCH_MARK, no RESOLVE: %r' % types)
    check(not (h.run / 'S1-OPQ-a/unexpected-halt.json').exists(), 'no unexpected-halt sidecar (BaseException skips except-branch)')
    check(not (h.run / 'S1-OPQ-a/response.body').exists(), 'no response receipt')

    banner('2. next CLI invocation (recover-first) with the lock still present')
    code, out, errtxt = cli('job-next', 'S1-OPQ-b')
    check(code == 3 and 'lock/claim exists' in errtxt, 'exit 3, lock untouched: %r' % errtxt.strip())
    check((h.run / 'ledger.lock').exists(), 'lock still present')
    check(not (h.run / 'S1-OPQ-b').exists(), 'no attempt dir claimed')
    check(len([w for w in tr.wire() if w.startswith(b'POST ')]) == 1, 'still one POST ever')

    banner('3. operator records owner-death evidence, removes lock, runs library recover()')
    evidence = h.run / 'LOCK-EVIDENCE.json'
    evidence.write_bytes(a.encode(dict(owner_gone=True, pid=a.read(h.run / 'ledger.lock')['pid'],
                                       host=a.read(h.run / 'ledger.lock')['host'], method='synthetic ps check')))
    (h.run / 'ledger.lock').unlink()
    # The CLI has NO flag for lock evidence: recover(lock_evidence=...) is library-only.
    import inspect
    check('--lock-evidence' not in inspect.getsource(a._main), 'CLI exposes no lock-evidence option (library call required)')
    tr = install_fake_transport([FakeSocket(http_response(200, key_raw)) for _ in range(4)])
    recovered = a.recover(run_root=h.run, key_info=d.key_info, clock=h.clock, lock_evidence=evidence)
    types = [e['type'] for e in h.entries()]
    check(recovered == ['S1-OPQ'], 'recovered S1-OPQ')
    check(types[types.index('DISPATCH_MARK') + 1] == 'LOCK_RECOVERED', 'LOCK_RECOVERED is the next entry after the crash')
    resolve = next(e for e in h.entries() if e['type'] == 'RESOLVE')
    check(resolve['dispatched'] and resolve['debit'] == a.recon.FLOOR, 'RESOLVE dispatched=True debit=FLOOR')
    check(types[-1] == 'HALT', 'terminal HALT: %r' % types)
    check(len([w for w in tr.wire() if w.startswith(b'GET ')]) == 4 and not any(w.startswith(b'POST ') for w in tr.wire()),
          'recovery made 4 GETs and no POST')
    check(a.read(h.run / 'S1-OPQ-a/recovered.json')['dispatched'] is True, 'recovered.json written')

    banner('4. CLI after recovery')
    tr = install_fake_transport([])
    code, out, errtxt = cli('job-after', 'S1-OPQ-c')
    check(code == 2, 'exit 2 refusal (halted run): %r' % errtxt.strip())
    check(tr.wire() == [], 'no transport use')
    for p in h.run.rglob('*'):
        if p.is_file():
            check(SYNTHETIC_KEY.encode() not in p.read_bytes(), 'no key in %s' % p.name) if SYNTHETIC_KEY.encode() in p.read_bytes() else None
    print('ok   key absent from every receipt under run/')

print()
print('problems:', problems)
sys.exit(0 if not problems else 1)
