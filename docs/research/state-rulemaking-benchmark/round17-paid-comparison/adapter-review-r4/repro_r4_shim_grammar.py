"""Q2: the native shim's argv grammar, config surface and host resolution (offline, synthetic host).

Exit 0 = every expectation held. Prints one line per probe.
"""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _load as L

PY = sys.executable
results = []


def check(name, ok, detail=''):
    results.append(ok)
    print(('ok   ' if ok else 'FAIL ') + name + ('  ' + detail if detail else ''))


HOST = b"import sys, signal, os\ndef main(args):\n    print('HOST', args, signal.getitimer(signal.ITIMER_REAL)[0] > 1700, sorted(k for k in os.environ if k.startswith('R17')))\n    return 42 if args == ['SYNTHETIC'] else 43\n"


def make_tree(root, host_bytes=HOST, config=None, job='native-jobs/test-id'):
    jobdir = root / job
    jobdir.mkdir(parents=True)
    host = root / 'adapter-r1-4/host_driver.py'
    host.parent.mkdir(exist_ok=True)
    host.write_bytes(host_bytes)
    if config is None:
        config = {'schema_version': 'r17.native-args.v1',
                  'host_sha256': hashlib.sha256(host_bytes).hexdigest(), 'args': ['SYNTHETIC']}
    (jobdir / 'arguments.json').write_text(json.dumps(config))
    shim = jobdir / 'adapter.py'
    shim.write_bytes(L.shim_path.read_bytes())
    return shim, host


with L.tempdir('shim') as tmp:
    root = Path(tmp)
    shim, host = make_tree(root)

    # --- real subprocess, exact runner grammar, synthetic host -------------------------
    env = {'HOME': tmp, 'PATH': '/usr/bin:/bin', 'LANG': 'en_US.UTF-8', 'R17_PROBE': 'x'}
    r = subprocess.run([PY, '-I', '-S', '-B', str(shim), '--live-initial'], env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = r.stdout.decode()
    check('exact grammar runs host once, exit = host return', r.returncode == 42, out.strip())
    check('shim arms >1700 s before host runs', 'True' in out)
    check('host sees no R17* environment influence beyond what the runner sets', "['R17_PROBE']" in out,
          '(the shim passes the environment through untouched; the runner supplies only HOME/PATH/LANG/key)')
    for argv in ([], ['--live-initial', '--live-initial'], ['--live-initial', '--cell', 'S1-OPQ'],
                 ['--LIVE-INITIAL'], ['--live-initial=1'], ['--cell', 'S1-OPQ'], ['-h'], ['--live-initial', '']):
        r = subprocess.run([PY, '-I', '-S', '-B', str(shim)] + argv, env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        check('argv %r refused (exit 2, host never ran)' % (argv,), r.returncode == 2 and b'HOST' not in r.stdout)
    for flags in (['-I', '-S'], ['-I', '-B'], ['-S', '-B'], []):
        r = subprocess.run([PY] + flags + [str(shim), '--live-initial'], env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        check('interpreter flags %r refused (exit 2)' % (flags,), r.returncode == 2 and b'HOST' not in r.stdout)

    # --- config surface --------------------------------------------------------------
    good = json.loads((shim.parent / 'arguments.json').read_text())
    bad_configs = {
        'extra key': {**good, 'extra': 1},
        'missing args': {k: v for k, v in good.items() if k != 'args'},
        'wrong schema': {**good, 'schema_version': 'r17.native-args.v2'},
        'host hash drift': {**good, 'host_sha256': '0' * 64},
        'host hash upper-case': {**good, 'host_sha256': good['host_sha256'].upper()},
    }
    for name, cfg in bad_configs.items():
        (shim.parent / 'arguments.json').write_text(json.dumps(cfg))
        r = subprocess.run([PY, '-I', '-S', '-B', str(shim), '--live-initial'], env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        check('config %s refused before host (exit 2)' % name, r.returncode == 2 and b'HOST' not in r.stdout)
    (shim.parent / 'arguments.json').write_text(json.dumps({**good, 'args': 'SYNTHETIC'}))
    r = subprocess.run([PY, '-I', '-S', '-B', str(shim), '--live-initial'], env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    check('config args not a list: host still called with the raw value (NOTE: shim does not type-check args)',
          r.returncode == 43 and b"HOST SYNTHETIC" in r.stdout, r.stdout.decode().strip())
    (shim.parent / 'arguments.json').write_text(json.dumps(good))
    (shim.parent / 'arguments.json').write_text('{"schema_version":"r17.native-args.v1","host_sha256":"%s","args":["SYNTHETIC"],"args":["OTHER"]}' % good['host_sha256'])
    r = subprocess.run([PY, '-I', '-S', '-B', str(shim), '--live-initial'], env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    check('duplicate "args" key: json.loads keeps the LAST value (NOTE: shim uses plain json.loads, not strict)',
          r.returncode == 43 and b"['OTHER']" in r.stdout, r.stdout.decode().strip())
    (shim.parent / 'arguments.json').write_text(json.dumps(good))

    # host bytes drift after signing -> refused
    host.write_bytes(HOST + b'# drift\n')
    r = subprocess.run([PY, '-I', '-S', '-B', str(shim), '--live-initial'], env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    check('host_driver drift refused (exit 2)', r.returncode == 2 and b'HOST' not in r.stdout)
    host.write_bytes(HOST)

    # host raising -> 4; host returning adapter code passes through
    host.write_bytes(b"def main(args):\n    raise RuntimeError('boom')\n")
    cfg = {**good, 'host_sha256': hashlib.sha256(host.read_bytes()).hexdigest()}
    (shim.parent / 'arguments.json').write_text(json.dumps(cfg))
    r = subprocess.run([PY, '-I', '-S', '-B', str(shim), '--live-initial'], env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    check('host exception -> exit 4 with fixed message, timer disarmed', r.returncode == 4 and b'primary must inspect ledger' in r.stdout)

    # --- host resolution is positional: ../../adapter-r1-4/host_driver.py from the shim's own dir ----
    other = root / 'elsewhere/native-jobs/x'
    other.mkdir(parents=True)
    (other / 'adapter.py').write_bytes(L.shim_path.read_bytes())
    (other / 'arguments.json').write_text(json.dumps(good))
    r = subprocess.run([PY, '-I', '-S', '-B', str(other / 'adapter.py'), '--live-initial'], env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    check('shim copied elsewhere cannot find a host -> exit 4 (FileNotFoundError is a generic shim failure; host never ran)', r.returncode == 4 and b'HOST' not in r.stdout)
    (root / 'elsewhere/adapter-r1-4').mkdir()
    (root / 'elsewhere/adapter-r1-4/host_driver.py').write_bytes(b"def main(a):\n    return 7\n")
    r = subprocess.run([PY, '-I', '-S', '-B', str(other / 'adapter.py'), '--live-initial'], env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    check('a different host next to a relocated shim is refused by the signed hash (exit 2)', r.returncode == 2)

    # --- pre-armed timer refused -------------------------------------------------------
    shim_mod = L.load('r4_shim_unit', L.shim_path)
    make_tree(root / 'unit')
    with patch.object(shim_mod, '__file__', str(root / 'unit/native-jobs/test-id/adapter.py')):
        old = signal.signal(signal.SIGALRM, lambda *x: None)
        signal.setitimer(signal.ITIMER_REAL, 30)
        try:
            check('pre-armed ITIMER_REAL refused (exit 2)', shim_mod.main(['--live-initial']) == 2)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old)
        check('unit: exact grammar OK with synthetic host', shim_mod.main(['--live-initial']) == 42)
        check('timer disarmed after return', signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0))

    # --- what the real host does with signed args: --driver override and --lock-evidence routing ---
    real_host = L.d
    import io, contextlib
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        code = real_host.main(['--driver=/x', '--cell', 'S1-OPQ'])
    check('real host refuses a signed --driver override (exit 2)', code == 2 and 'driver_override' in err.getvalue())
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        code = real_host.main(['--driver-sha256', 'abc'])
    check('real host refuses a signed --driver-sha256 (exit 2)', code == 2 and 'driver_override' in err.getvalue())
    # A signed arguments.json may carry --lock-evidence or --opq-freeze: the shim/host do not forbid
    # them; the adapter's argparse accepts them. Only the signing discipline prevents it (NOTE).
    import argparse
    parser_src = (L.ADAPTER / 'r17_adapter.py').read_text()
    check('adapter CLI exposes --lock-evidence and --opq-freeze (signed args could select them; NOTE)',
          "'--lock-evidence'" in parser_src and "'--opq-freeze'" in parser_src)

print('SUMMARY shim grammar:', sum(results), 'of', len(results), 'checks held')
sys.exit(0 if all(results) else 1)
