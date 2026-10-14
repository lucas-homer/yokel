"""Q3: A3 arithmetic, nested deadline semantics, and a runner/shim kill at each stage.

Each kill stage runs the REAL adapter (adapter-r1-4) through the r1.4 synthetic Harness in a
child process; the child dies exactly as the shim's SIGALRM handler would (os._exit(4)) or by
SIGTERM as the native supervisor sends it. The parent inspects the ledger, then performs the
operator's accounting recovery in a fresh child, then attempts the next dispatch.

No network, no credential, no runner. Exit 0 = every expectation held.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
PY = sys.executable
results = []


def check(name, ok, detail=''):
    results.append(ok)
    print(('ok   ' if ok else 'FAIL ') + name + ('  ' + detail if detail else ''))


def entries(run):
    import _load as L
    return [L.a.strict(line) for line in (Path(run) / 'ledger.jsonl').read_bytes().splitlines()]


# ----------------------------------------------------------------------------- child phases
def child(phase, root, how):
    import _load as L
    a = L.a
    root = Path(root)
    if phase == 'kill':
        h = L.Harness(root)
        h.queue = [L.packet(0), L.packet(0), L.packet(0), L.packet(10_000_000)]  # preflight, recon-0, recon-60, ...
        marker = root / 'marker'

        def die():
            marker.write_text(str(os.getpid()))
            if how == 'alarm':
                os._exit(4)            # exactly what native_entry.expired does
            while True:                 # wait for the supervisor's SIGTERM
                time.sleep(0.05)

        if phase_stage == 'pre-mark':
            hook = lambda event, ledger, folder: die() if event == 'after_reserve' else None
            h.execute('S1-OPQ', 'job1', hook=hook)
        elif phase_stage == 'mid-post':
            h.post = lambda url, raw: die()
            h.execute('S1-OPQ', 'job1')
        elif phase_stage == 'mid-recon':
            reads = []
            real = h.key_info

            def key_info(url):
                reads.append(1)
                if len(reads) == 3:     # preflight, recon-0, then die during recon-60
                    die()
                return real(url)
            h.key_info = key_info
            h.execute('S1-OPQ', 'job1')
        os._exit(99)  # should never complete
    if phase == 'recover':
        run = root / 'run'
        lock = run / 'ledger.lock'
        lock_raw = lock.read_bytes()
        lock.unlink()                                   # the operator's step, after proving death
        evidence = root / 'lock-evidence.json'
        evidence.write_bytes(a.encode(dict(owner_gone=True, pid=int((root / 'marker').read_text()),
                                           host=__import__('socket').gethostname(), lock_sha256=a.sha(lock_raw))))
        clock = L.FakeClock()
        calls = []

        def key_info(url):
            calls.append(url)
            return L.packet(10_000_000)
        posts = []
        recovered = a.recover(run_root=run, key_info=key_info, clock=clock, lock_evidence=evidence)
        print(json.dumps(dict(recovered=recovered, key_reads=len(calls), posts=len(posts))))
        return
    if phase == 'next':
        run = root / 'run'
        clock = L.FakeClock()
        posts = []

        def post(url, raw):
            posts.append(url)
            return dict(status=500, raw=b'{}', headers={})
        reads = []

        def key_info(url):
            reads.append(url)
            return L.packet(0)
        try:
            a.execute_once(cell='S1-OPQ', source=L.SOURCE, release_path=run / 'RELEASE.json', run_root=run,
                           attempt_dir=run / 'job2', job_id='job2', post=post, key_info=key_info,
                           clock=clock, artifact_root=root)
            print(json.dumps(dict(outcome='executed', posts=len(posts), reads=len(reads))))
        except a.Refused as exc:
            print(json.dumps(dict(outcome='refused:' + str(exc), posts=len(posts), reads=len(reads))))
        except FileExistsError:
            print(json.dumps(dict(outcome='lock_or_claim_exists', posts=len(posts), reads=len(reads))))
        return


if len(sys.argv) > 1 and sys.argv[1] == '--child':
    phase, root, how, phase_stage = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
    child(phase, root, how)
    sys.exit(0)

import _load as L
d, a = L.d, L.a

# ----------------------------------------------------------------------------- A3 arithmetic
print('# A3 arithmetic')
check('constants: TIMEOUT 600, connect 15, key 15, POST total 615, job deadline 1740',
      (d.TIMEOUT_S, d.CONNECT_WRITE_S, d.KEY_TIMEOUT_S, d.POST_TOTAL_S, d.JOB_DEADLINE_S) == (600, 15, 15, 615, 1740))
sched = a.recon.READ_SCHEDULE_S
normal = d.KEY_TIMEOUT_S + d.POST_TOTAL_S + max(sched) + len(sched) * d.KEY_TIMEOUT_S
check('normal cell worst transport = 15 + 615 + 900 + 4*15 = 1590 (Sol)', normal == 1590, str(normal))
tight = d.KEY_TIMEOUT_S + d.POST_TOTAL_S + max(sched) + d.KEY_TIMEOUT_S
check('tighter bound: reads are absolute offsets, so only the LAST GET adds: 15+615+900+15 = 1545', tight == 1545)
recovery = max(sched) + len(sched) * d.KEY_TIMEOUT_S
check('marked recovery worst case 900 + 4*15 = 960 (no POST)', recovery == 960)
check('1590 < 1740 < 1800', 1590 < d.JOB_DEADLINE_S < 1800)
print('   margin after transport: %d s for Python work; %d s before the native kill' % (d.JOB_DEADLINE_S - normal, 1800 - d.JOB_DEADLINE_S))
print('   NOTE: the native 1800 s clock starts before `op run` secret resolution and the pre-exec pin hashing;')
print('         the shim\'s 1740 s clock starts after them. The 60 s reserve shrinks by that bootstrap time.')

# ----------------------------------------------------------------------------- nesting semantics
print('# nested deadline semantics (real signals)')
code = r'''
import os, signal, sys, time, importlib.util
spec = importlib.util.spec_from_file_location('hd', sys.argv[1]); d = importlib.util.module_from_spec(spec); spec.loader.exec_module(d)
def expired(signum, frame): os._exit(4)
expired.r17_deadline = True
signal.signal(signal.SIGALRM, expired); signal.setitimer(signal.ITIMER_REAL, float(sys.argv[2]))
try:
    with d.deadline(float(sys.argv[3])):
        with d.deadline(float(sys.argv[4])):
            time.sleep(float(sys.argv[5]))
    print('completed', round(signal.getitimer(signal.ITIMER_REAL)[0], 2))
except d.DriverError as e:
    print('driver', e, round(signal.getitimer(signal.ITIMER_REAL)[0], 2))
'''
def nest(outer, a1, a2, sleep):
    r = subprocess.run([PY, '-I', '-S', '-B', '-c', code, str(d.__file__), str(outer), str(a1), str(a2), str(sleep)],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return r.returncode, r.stdout.decode().strip()

rc, out = nest(0.3, 5, 5, 2)
check('shim timer earlier than host deadlines -> shim handler runs -> os._exit(4)', rc == 4 and out == '', out)
rc, out = nest(5, 5, 0.2, 2)
check('inner host deadline fires -> DriverError, shim timer re-armed (remaining < 5)', rc == 0 and out.startswith('driver transport_deadline') and 0 < float(out.split()[-1]) < 5, out)
rc, out = nest(5, 0.2, 5, 2)
check('outer host deadline (615-like) fires through the inner -> DriverError, shim timer re-armed', rc == 0 and out.startswith('driver transport_deadline') and 0 < float(out.split()[-1]) < 5, out)
rc, out = nest(5, 5, 5, 0.1)
check('no expiry: shim timer restored with elapsed time subtracted', rc == 0 and out.startswith('completed') and 4.5 < float(out.split()[-1]) < 5, out)
rc, out = nest(0.5, 0.2, 5, 1)
check('inner fires first, then shim (0.5) fires during the remaining sleep? no: DriverError exits the sleep', rc == 0 and out.startswith('driver'), out)

# a GET inside the job: preflight 15 s nested under a shim timer with 10 s remaining -> shim wins
code2 = r'''
import os, signal, sys, time, importlib.util
from unittest.mock import patch
spec = importlib.util.spec_from_file_location('hd', sys.argv[1]); d = importlib.util.module_from_spec(spec); spec.loader.exec_module(d)
def expired(signum, frame): os._exit(4)
expired.r17_deadline = True
signal.signal(signal.SIGALRM, expired); signal.setitimer(signal.ITIMER_REAL, 0.3)
class Hang:
    def __init__(self, *a, **k): pass
    def request(self, *a, **k): time.sleep(5)
    def close(self): pass
with patch.object(d.os, 'environ', {'OPENROUTER_API_KEY': 'SYNTHETIC'}), patch.object(d.http.client, 'HTTPSConnection', Hang), patch.object(d, '_tls_context', lambda: type('C', (), {'verify_mode': d.ssl.CERT_REQUIRED, 'check_hostname': True, 'r17_ca_sha256': 'x'})()):
    try:
        d.post_once(d.POST_URL, b'{}')
        print('returned')
    except Exception as e:
        print('exc', e)
'''
r = subprocess.run([PY, '-I', '-S', '-B', '-c', code2, str(d.__file__)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
check('shim deadline expiring inside a hung POST send -> os._exit(4), no exception path, no retry', r.returncode == 4 and r.stdout == b'', r.stdout.decode())

# ----------------------------------------------------------------------------- kill stages
print('# kill at each stage against the real adapter (child processes)')
FLOOR = a.recon.FLOOR
for stage in ('pre-mark', 'mid-post', 'mid-recon'):
    for how in ('alarm', 'sigterm'):
        with L.tempdir('kill-' + stage + '-' + how) as tmp:
            root = Path(tmp)
            proc = subprocess.Popen([PY, '-I', '-S', '-B', __file__, '--child', 'kill', tmp, how, stage],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            if how == 'sigterm':
                for _ in range(200):
                    if (root / 'marker').exists():
                        break
                    time.sleep(0.05)
                proc.send_signal(signal.SIGTERM)
            out, _ = proc.communicate(timeout=60)
            rc = proc.returncode
            run = root / 'run'
            led = entries(run)
            types = [e['type'] for e in led]
            label = '%s/%s' % (stage, how)
            check(label + ': child died as expected', rc == (4 if how == 'alarm' else -15), 'rc=%s %s' % (rc, out.decode()[-200:]))
            check(label + ': ledger.lock RETAINED (next run refuses, exit 3)', (run / 'ledger.lock').exists())
            if stage == 'pre-mark':
                check(label + ': last entry RESERVE, no DISPATCH_MARK', types[-1] == 'RESERVE' and 'DISPATCH_MARK' not in types, str(types))
            elif stage == 'mid-post':
                check(label + ': last entry DISPATCH_MARK, no RESOLVE', types[-1] == 'DISPATCH_MARK' and 'RESOLVE' not in types, str(types))
                check(label + ': no response/status receipt yet', not (run / 'job1/status.json').exists())
            else:
                check(label + ': DISPATCH_MARK present, recon-0.json and recon-60 intent claim exist, no RESOLVE',
                      'DISPATCH_MARK' in types and 'RESOLVE' not in types and (run / 'job1/recon-0.json').exists()
                      and (run / 'job1/recon-60.intent.json').exists() and not (run / 'job1/recon-60.json').exists(), str(types))
            # next dispatch WITHOUT recovery: lock exists -> refused before any transport
            r = subprocess.run([PY, '-I', '-S', '-B', __file__, '--child', 'next', tmp, how, stage], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            o = json.loads(r.stdout.decode().strip().splitlines()[-1])
            check(label + ': next dispatch with lock retained -> lock_or_claim_exists, 0 POST 0 GET', o == dict(outcome='lock_or_claim_exists', posts=0, reads=0), str(o))
            # operator recovery
            r = subprocess.run([PY, '-I', '-S', '-B', __file__, '--child', 'recover', tmp, how, stage], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            o = json.loads(r.stdout.decode().strip().splitlines()[-1])
            led = entries(run)
            types = [e['type'] for e in led]
            resolve = [e for e in led if e['type'] == 'RESOLVE']
            if stage == 'pre-mark':
                check(label + ': recovery -> RESOLVE dispatched=False debit 0, 0 key reads, no HALT',
                      o['key_reads'] == 0 and resolve and resolve[-1]['dispatched'] is False and resolve[-1]['debit'] == 0 and 'HALT' not in types, str(o) + ' ' + str(types))
                r = subprocess.run([PY, '-I', '-S', '-B', __file__, '--child', 'next', tmp, how, stage], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                o = json.loads(r.stdout.decode().strip().splitlines()[-1])
                check(label + ': next dispatch after unmarked recovery -> exactly ONE POST (re-admission by design)', o['outcome'] == 'executed' and o['posts'] == 1, str(o))
            else:
                reads_done = len(list((run / 'job1').glob('recon-*.json'))) - len(list((run / 'job1').glob('recon-*.intent.json')))
                check(label + ': recovery -> RESOLVE dispatched=True debit>=FLOOR, HALT, 0 POST',
                      resolve and resolve[-1]['dispatched'] is True and resolve[-1]['debit'] >= FLOOR and 'HALT' in types and o['posts'] == 0, str(o) + ' ' + str(types))
                check(label + ': total reconciliation reads <= 4 across crash + recovery', reads_done <= 4 and o['key_reads'] <= 4, 'receipts=%d recovery_reads=%d' % (reads_done, o['key_reads']))
                r = subprocess.run([PY, '-I', '-S', '-B', __file__, '--child', 'next', tmp, how, stage], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                o = json.loads(r.stdout.decode().strip().splitlines()[-1])
                adm = a.recon.admit(led, 'S2-OPQ', a.last_usage(led))
                check(label + ': next dispatch after marked recovery refused before any POST (%s; admit(S2)=%s)' % (o['outcome'], adm),
                      o['outcome'] in ('refused:admission:halted', 'refused:wrong_cell_order') and o['posts'] == 0 and adm == (False, 'halted'), str(o))
            check(label + ': ledger chain still verifies after recovery', all(
                led[i].get('prev_sha256') == a.sha(a.encode(led[i - 1])) for i in range(1, len(led))))

print('SUMMARY deadline/kill:', sum(results), 'of', len(results), 'checks held')
sys.exit(0 if all(results) else 1)
