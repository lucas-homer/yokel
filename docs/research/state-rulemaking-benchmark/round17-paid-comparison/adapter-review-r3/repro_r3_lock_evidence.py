"""--lock-evidence (S5) against r1.2: can the route break a live lock, or dispatch?

Real PIDs, no os.kill mocking: this process = alive owner, PID 1 = EPERM, a reaped child
= dead owner. Runs through the adapter CLI (a.main) and the host CLI (host_driver.main)
with the real r1.2 driver bytes pinned as the release's host_driver artifact, real
http.client over fake sockets, synthetic environment. Exit 0 = every check holds.
"""
import contextlib
import importlib.util
import io
import os
import subprocess
import sys
import traceback
import types
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I drops the script dir
from _load import (load, install_fake_env, install_fake_transport, FakeSocket, http_response,
                   SYNTHETIC_KEY, tempdir, banner, ADAPTER, mod)

a, t, d = load()
env = install_fake_env()
problems = []


def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond:
        problems.append(what)


def dead_pid():
    proc = subprocess.Popen(['/usr/bin/true'])
    proc.wait()                                   # reaped: the PID is gone
    try:
        os.kill(proc.pid, 0)
    except ProcessLookupError:
        return proc.pid
    raise RuntimeError('child PID unexpectedly alive')


class Setup:
    def __init__(self, tmp):
        self.h = h = t.Harness(tmp)
        drv_dir = h.root / 'drv'
        drv_dir.mkdir()
        self.driver_path = drv_dir / 'host_driver.py'
        self.driver_path.write_bytes((ADAPTER / 'host_driver.py').read_bytes())
        self.pin = a.sha(self.driver_path.read_bytes())
        src_root = h.root / 'sources-r2'
        src_root.mkdir()
        (src_root / 'READY.json').write_bytes(a.encode(dict(selected=['synthetic-001', 'synthetic-002', 'synthetic-003'])))
        for s in ('synthetic-001', 'synthetic-002', 'synthetic-003'):
            (src_root / s).mkdir()
            (src_root / s / 'parsed-body.txt').write_bytes(t.SOURCE.encode('utf-8'))
        h.release['driver_sha256'] = self.pin
        h.release['artifacts']['host_driver'] = dict(path='drv/host_driver.py', sha256=self.pin)
        h.save_release()
        entries = h.entries()
        entries[1]['release_sha256'] = a.sha(h.release_path.read_bytes())
        h.rewrite_ledger(entries)
        self.hd = mod('r3_host_copy_' + Path(tmp).name, self.driver_path)   # host CLI from the pinned copy
        self.key0 = b'{"data":' + t.packet(0)['fields'] + b'}'
        self.key1 = b'{"data":' + t.packet(10_000_000)['fields'] + b'}'

    def evidence(self, name='LOCK-EVIDENCE.json', **changes):
        lock = self.h.run / 'ledger.lock'
        value = dict(owner_gone=True, pid=0, host=a.socket.gethostname(),
                     lock_sha256=a.sha(lock.read_bytes()) if lock.exists() else self.last_lock_sha)
        value.update(changes)
        path = self.h.run / name
        path.write_bytes(a.encode(value))
        return path

    def remove_lock(self):
        lock = self.h.run / 'ledger.lock'
        self.last_lock_sha = a.sha(lock.read_bytes())
        lock.unlink()

    def cli(self, extra=(), job='job', attempt='S1-OPQ-x', host=False, hook=None):
        h = self.h
        base = ['--cell', 'S1-OPQ', '--release', str(h.release_path), '--run-root', str(h.run),
                '--attempt-dir', str(h.run / attempt), '--job-id', job] + list(extra)
        real_execute = a.execute_once
        def execute(**kw):
            kw['artifact_root'] = h.root
            kw['clock'] = h.clock
            if hook:
                kw['hook'] = hook
            return real_execute(**kw)
        real_sfl, real_mfs = importlib.util.spec_from_file_location, importlib.util.module_from_spec
        dummy = types.SimpleNamespace(loader=types.SimpleNamespace(exec_module=lambda m: None))
        def sfl(name, path, *args, **kw):   # the host CLI's adapter import -> our patched module
            return dummy if name == 'r17_host_adapter' else real_sfl(name, path, *args, **kw)
        def mfs(spec):
            return a if spec is dummy else real_mfs(spec)
        out, err = io.StringIO(), io.StringIO()
        with patch.object(a, 'BENCH', h.root), patch.object(a, 'execute_once', execute), \
             patch.object(a, 'Clock', lambda: h.clock), contextlib.redirect_stdout(out), \
             contextlib.redirect_stderr(err):
            if host:
                with patch.object(importlib.util, 'spec_from_file_location', sfl), \
                     patch.object(importlib.util, 'module_from_spec', mfs):
                    code = self.hd.main(base)
            else:
                code = a.main(base + ['--driver', str(self.driver_path), '--driver-sha256', self.pin],
                              recover_first=True)
        return code, out.getvalue(), err.getvalue()

    def types(self):
        return [e['type'] for e in self.h.entries()]


with tempdir() as tmp:
    s = Setup(tmp)
    h = s.h
    lock = h.run / 'ledger.lock'

    banner('1. unmarked crash after RESERVE (BaseException): lock retained')
    def crash(stage, *_):
        if stage == 'after_reserve':
            raise t.Crash()
    tr = install_fake_transport([FakeSocket(http_response(200, s.key0))])
    try:
        s.cli(job='job-crash', attempt='S1-OPQ-a', hook=crash)
        check(False, 'Crash should propagate')
    except t.Crash:
        pass
    check(lock.exists() and s.types()[-1] == 'RESERVE', 'lock retained, tail RESERVE: %r' % s.types())
    before = h.entries()
    lock_bytes = lock.read_bytes()

    banner('2. --lock-evidence while the lock is PRESENT (live or not): refused, lock untouched')
    ev = s.evidence(pid=dead_pid())
    tr = install_fake_transport([])
    code, out, err = s.cli(['--lock-evidence', str(ev)], host=True, job='job-ev', attempt='S1-OPQ-ev')
    check(code == 2 and 'lock_recovery_lock_present' in err, 'host route exit 2: %r' % err.strip())
    check(lock.read_bytes() == lock_bytes, 'lock bytes unchanged')
    check(h.entries() == before and tr.wire() == [], 'ledger unchanged, no transport use')
    check(not (h.run / 'S1-OPQ-ev').exists(), 'dummy --attempt-dir never claimed')

    banner('3. operator removed the lock but the owner PID is ALIVE / EPERM / foreign host')
    s.remove_lock()
    for change, want in ((dict(pid=os.getpid()), 'lock_recovery_owner_alive'),
                         (dict(pid=1), 'lock_recovery_owner_alive'),
                         (dict(host='synthetic-foreign-host'), 'lock_recovery_evidence'),
                         (dict(pid=0), 'lock_recovery_evidence'),
                         (dict(pid=-1), 'lock_recovery_evidence'),
                         (dict(pid=True), 'lock_recovery_evidence'),
                         (dict(owner_gone='true'), 'lock_recovery_evidence'),
                         (dict(lock_sha256=s.last_lock_sha.upper()), 'lock_recovery_evidence')):
        ev = s.evidence(**change)
        code, out, err = s.cli(['--lock-evidence', str(ev)], host=(len(problems) % 2 == 0), job='job-ev', attempt='S1-OPQ-ev')
        check(code == 2 and want in err, '%r -> %s' % (change, err.strip()))
        check(h.entries() == before and not lock.exists() and tr.wire() == [], '    ledger unchanged, no lock created, no transport')

    banner('4. race: another owner takes the lock between the existence check and recover()')
    ev = s.evidence(pid=dead_pid())
    real_read = a.read
    state = {'armed': True}
    def racing_read(path):
        value = real_read(path)
        if state['armed'] and Path(path) == ev:
            state['armed'] = False
            a.put(lock, dict(pid=424242, host='racer', started='0', run_id='racer'))
        return value
    with patch.object(a, 'read', racing_read):
        code, out, err = s.cli(['--lock-evidence', str(ev)], host=True, job='job-ev', attempt='S1-OPQ-ev')
    check(code == 3 and 'lock/claim exists' in err, 'exit 3: %r' % err.strip())
    check(a.read(lock)['run_id'] == 'racer' and h.entries() == before, "racer's lock intact, ledger unchanged")
    lock.unlink()

    banner('5. valid evidence (reaped child PID): accounting-only recovery, no dispatch')
    ev = s.evidence(pid=dead_pid())
    code, out, err = s.cli(['--lock-evidence', str(ev)], host=True, job='job-ev', attempt='S1-OPQ-ev')
    check(code == 0 and 'no dispatch' in out and err == '', 'host route exit 0: %r' % out.strip())
    check(s.types()[len(before):] == ['LOCK_RECOVERED', 'RESOLVE'], 'appended exactly LOCK_RECOVERED, RESOLVE: %r' % s.types())
    resolve = h.entries()[-1]
    check(resolve['dispatched'] is False and resolve['debit'] == 0, 'RESOLVE dispatched=False debit=0')
    check(h.entries()[-2]['evidence_sha256'] == a.sha(ev.read_bytes()), 'evidence hash recorded')
    check(not lock.exists(), 'recovery lock released on clean exit')
    check(tr.wire() == [], 'no POST and no GET for an unmarked recovery')
    check(not (h.run / 'S1-OPQ-ev').exists() and not any(e.get('job_id') == 'job-ev' for e in h.entries()),
          'dummy --attempt-dir/--job-id unused')
    check(a.read(h.run / 'S1-OPQ-a/recovered.json')['dispatched'] is False, 'recovered.json for the crashed attempt')

    banner('6. the same evidence again: nothing pending, yet another LOCK_RECOVERED is appended (note)')
    n = len(h.entries())
    code, out, err = s.cli(['--lock-evidence', str(ev)], host=False, job='job-ev', attempt='S1-OPQ-ev')
    check(code == 0, 'exit 0 again')
    print('     appended:', s.types()[n:], '| LOCK_RECOVERED count:', s.types().count('LOCK_RECOVERED'))

    banner('7. normal host CLI afterwards: S1-OPQ dispatches once (unmarked recovery is not a completion)')
    tr = install_fake_transport([FakeSocket(http_response(200, s.key0)),
                                 FakeSocket(http_response(200, h.response['raw'])),
                                 FakeSocket(http_response(200, s.key1))])
    code, out, err = s.cli(host=True, job='job-fresh', attempt='S1-OPQ-b')
    check(code == 0 and '"state":13' in out, 'exit 0 state 13: %r' % out.strip())
    check(sum(w.startswith(b'POST ') for w in tr.wire()) == 1, 'exactly one POST')
    check(a.read(h.run / 'S1-OPQ-b/status.json')['tls_ca_sha256'] == a.sha(d.CA_BUNDLE.read_bytes()), 'status.json carries the bundle hash')
    for p in h.run.rglob('*'):
        if p.is_file() and SYNTHETIC_KEY.encode() in p.read_bytes():
            check(False, 'key found in %s' % p.name)
    print('ok   key absent from every receipt under run/')

with tempdir() as tmp:
    s = Setup(tmp)
    h = s.h
    lock = h.run / 'ledger.lock'
    banner('8. marked crash: SIGINT while the POST is written, through the host CLI')
    tr = install_fake_transport([FakeSocket(http_response(200, s.key0)),
                                 FakeSocket(b'', fail_send=KeyboardInterrupt())])
    try:
        s.cli(host=True, job='job-sigint', attempt='S1-OPQ-a')
        check(False, 'KeyboardInterrupt should propagate')
    except KeyboardInterrupt:
        text = traceback.format_exc()
        frames = [l.strip() for l in text.splitlines() if l.strip().startswith('File')]
        check(SYNTHETIC_KEY not in text, 'traceback carries no key')
        check(not any('http/client.py' in f for f in frames), 'N16: no http.client frames (fresh re-raise): %s' % frames[-1])
    check(lock.exists() and s.types()[-1] == 'DISPATCH_MARK', 'lock retained, tail DISPATCH_MARK')
    check(sum(w.startswith(b'POST ') for w in tr.wire()) == 1, 'one interrupted POST')

    banner('9. --lock-evidence on the marked cell: 4 GETs, 0 POSTs, FLOOR, terminal HALT')
    s.remove_lock()
    ev = s.evidence(pid=dead_pid())
    tr = install_fake_transport([FakeSocket(http_response(200, s.key0)) for _ in range(4)])
    code, out, err = s.cli(['--lock-evidence', str(ev)], host=True, job='job-ev', attempt='S1-OPQ-ev')
    check(code == 0 and 'no dispatch' in out, 'exit 0: %r' % out.strip())
    types_ = s.types()
    check(types_[types_.index('DISPATCH_MARK') + 1:] == ['LOCK_RECOVERED', 'RESOLVE', 'HALT'], 'LOCK_RECOVERED, RESOLVE, HALT: %r' % types_)
    resolve = next(e for e in h.entries() if e['type'] == 'RESOLVE')
    check(resolve['dispatched'] is True and resolve['debit'] == a.recon.FLOOR, 'RESOLVE dispatched=True debit=FLOOR')
    check(sum(w.startswith(b'GET ') for w in tr.wire()) == 4 and not any(w.startswith(b'POST ') for w in tr.wire()), '4 GETs, no POST')
    check(all(a.read(h.run / 'S1-OPQ-a' / f'recon-{due}.json')['tls_ca_sha256'] == a.sha(d.CA_BUNDLE.read_bytes())
              for due in a.recon.READ_SCHEDULE_S), 'every reconciliation receipt carries the bundle hash')
    check(not lock.exists(), 'lock released')

    banner('10. normal CLI after the halt: refused with the printable admission reason, no transport')
    tr = install_fake_transport([])
    code, out, err = s.cli(host=True, job='job-after', attempt='S1-OPQ-c')
    check(code == 2 and 'admission:halted' in err, 'exit 2: %r' % err.strip())
    check(tr.wire() == [], 'no transport use')
    for p in h.run.rglob('*'):
        if p.is_file() and SYNTHETIC_KEY.encode() in p.read_bytes():
            check(False, 'key found in %s' % p.name)
    print('ok   key absent from every receipt under run/')

print()
print('problems:', problems)
sys.exit(0 if not problems else 1)
