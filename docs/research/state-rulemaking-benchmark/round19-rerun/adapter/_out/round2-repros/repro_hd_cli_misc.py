"""host_driver.main() edge behaviour (offline; adapter.main replaced by a recorder).

(1) --driver / --driver-sha256 overrides refused; (2) exactly the adapter argv plus the
derived driver pin, recover_first=True; (3) a renamed copy of the driver file crashes on
its hard-coded 'host_driver.py' name instead of refusing cleanly; (4) a failing adapter
import (pin mismatch) escapes host main() as a raw traceback (no key involved; env never
read); (5) import of the driver reads no env and opens no connection.
Exit 0 = expectations held (notes 3 and 4 are reported, not failed).
"""
import contextlib
import hashlib
import io
import sys
import types
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I drops the script dir
from _load import load, install_fake_env, install_fake_transport, tempdir, banner, ADAPTER, mod

a, t, d = load()
env = install_fake_env()
tr = install_fake_transport([])
problems = []


def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond:
        problems.append(what)


recorded = {}
fake_adapter = types.SimpleNamespace(main=lambda argv, recover_first: recorded.update(argv=argv, rf=recover_first) or 17)
spec = types.SimpleNamespace(loader=types.SimpleNamespace(exec_module=lambda m: None))

banner('1. overrides refused')
for argv in (['--cell', 'S1-OPQ', '--driver', 'x.py'], ['--driver-sha256=00'], ['--cell', 'S1-OPQ', '--driver=x.py']):
    err = io.StringIO()
    with patch.object(d.importlib.util, 'module_from_spec', return_value=fake_adapter), \
         patch.object(d.importlib.util, 'spec_from_file_location', return_value=spec), \
         contextlib.redirect_stderr(err):
        code = d.main(argv)
    check(code == 2 and 'driver_override' in err.getvalue(), 'refused %r' % argv)

banner('2. argv routing and derived pin')
with patch.object(d.importlib.util, 'module_from_spec', return_value=fake_adapter), \
     patch.object(d.importlib.util, 'spec_from_file_location', return_value=spec):
    code = d.main(['--cell', 'S2-OPQ', '--release', 'r.json', '--run-root', 'run', '--attempt-dir', 'run/x', '--job-id', 'j'])
check(code == 17 and recorded['rf'] is True, 'adapter.main called with recover_first=True')
check(recorded['argv'][:10] == ['--cell', 'S2-OPQ', '--release', 'r.json', '--run-root', 'run', '--attempt-dir', 'run/x', '--job-id', 'j'],
      'user argv forwarded verbatim')
check(recorded['argv'][10:] == ['--driver', str(ADAPTER / 'host_driver.py'), '--driver-sha256',
                                hashlib.sha256((ADAPTER / 'host_driver.py').read_bytes()).hexdigest()], 'own path+hash appended')
check(env.reads == [] and tr.wire() == [], 'CLI routing reads no env, opens nothing')

banner('3. renamed driver copy (SPEC example: reviewed-host-driver.py)')
with tempdir() as tmp:
    copy = Path(tmp) / 'reviewed-host-driver.py'
    copy.write_bytes((ADAPTER / 'host_driver.py').read_bytes())
    (Path(tmp) / 'r17_adapter.py').write_bytes(b'def main(argv, recover_first=False):\n    return 17\n')
    renamed = mod('renamed_driver', copy)
    try:
        code = renamed.main(['--cell', 'S1-OPQ'])
        check(False, 'renamed copy returned %r' % code)
    except FileNotFoundError as exc:
        print('note renamed copy raises FileNotFoundError (uncaught, raw traceback, exit 1): %s' % Path(exc.filename).name)
        check(True, 'fails closed (no adapter invocation) but not via a clean refusal code')

banner('4. adapter import failure escapes host main() uncaught')
with tempdir() as tmp:
    copy = Path(tmp) / 'host_driver.py'
    copy.write_bytes((ADAPTER / 'host_driver.py').read_bytes())
    (Path(tmp) / 'r17_adapter.py').write_bytes(b'raise ValueError("dependency_pin:synthetic")\n')
    broken = mod('broken_adapter_driver', copy)
    try:
        broken.main(['--cell', 'S1-OPQ'])
        check(False, 'should raise')
    except ValueError as exc:
        print('note adapter import error propagates raw: %s (exit code would be 1, no fixed refusal line)' % exc)
        check(env.reads == [], 'no env read before/after the failed import')

banner('5. driver import is inert')
reads_before = list(env.reads)
fresh = mod('fresh_driver_r2', ADAPTER / 'host_driver.py')
check(env.reads == reads_before and tr.wire() == [], 'import reads no env, opens no connection')
check(all(callable(getattr(fresh, n)) for n in ('source', 'post_once', 'key_info')), 'exports present')

print()
print('problems:', problems)
sys.exit(0 if not problems else 1)
