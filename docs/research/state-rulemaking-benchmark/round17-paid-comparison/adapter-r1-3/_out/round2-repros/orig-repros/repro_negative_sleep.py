"""R-D (NOTE): production Clock.wait_until evaluates now() twice per loop; if the wall clock
crosses the deadline between the `while` test and the sleep argument, time.sleep gets a
negative value and raises ValueError. Inside poll() after a dispatch this becomes an
unexpected post-dispatch failure -> HALT on an otherwise good cell. Window is microseconds
(so very unlikely), fix is max(0, ...). Shown with a patched time.time sequence."""
import importlib.util, sys
from pathlib import Path
from unittest.mock import patch
spec = importlib.util.spec_from_file_location('_load', Path(__file__).resolve().parent / '_load.py')
L = importlib.util.module_from_spec(spec); spec.loader.exec_module(L)
a, t = L.load()

ticks = iter([100.0, 160.5, 160.5, 160.5])   # while-check sees 100 (<160); the sleep argument's now() sees 160.5
def fake_time():
    return next(ticks)
def fake_sleep(s):
    if s < 0:
        raise ValueError(f'sleep length must be non-negative (got {s})')
with patch.object(a.time, 'time', fake_time), patch.object(a.time, 'sleep', fake_sleep):
    try:
        a.Clock().wait_until(160.0)
        print('no error'); sys.exit(1)
    except ValueError as exc:
        print('Clock.wait_until raised:', exc); sys.exit(0)
