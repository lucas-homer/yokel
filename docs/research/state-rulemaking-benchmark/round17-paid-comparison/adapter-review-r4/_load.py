"""Round-4 loader: adapter-r1-4 modules and the r1.4 synthetic Harness, nothing else.

Temporary directories live only under adapter-review-r4/_tmp. No network, no credential,
no runner. Importing test_adapter.py only mkdir(exist_ok)s adapter-r1-4/_out (already present).
"""
import importlib.util
from pathlib import Path
import tempfile

HERE = Path(__file__).resolve().parent
R17 = HERE.parent
ADAPTER = R17 / 'adapter-r1-4'
TMP = HERE / '_tmp'
TMP.mkdir(exist_ok=True)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


t = load('r4_test_adapter', ADAPTER / 'test_adapter.py')
a = t.a
d = load('r4_host_driver', ADAPTER / 'host_driver.py')
shim_path = ADAPTER / 'native_entry.py'
Harness, FakeClock, packet, SOURCE = t.Harness, t.FakeClock, t.packet, t.SOURCE


def tempdir(prefix):
    return tempfile.TemporaryDirectory(prefix='.r4-' + prefix + '-', dir=TMP)
