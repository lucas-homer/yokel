"""R-F (NOTE): execute_once does not check that every marked cell has a completed.json or
stop.json. A crash between result.json and completed.json (accounting already durable) lets
the next cell be admitted and POSTed, while recover() would have HALTed the same run as
'crash before final completion'. No overspend (RESOLVE/RECONCILED exist), but the two
entry points disagree about whether the run is terminal. Fakes only."""
import importlib.util, sys
from pathlib import Path
from unittest.mock import patch
spec = importlib.util.spec_from_file_location('_load', Path(__file__).resolve().parent / '_load.py')
L = importlib.util.module_from_spec(spec); spec.loader.exec_module(L)
a, t = L.load()

with L.tempdir() as d:
    h = t.Harness(d)
    real_put = a.put
    def put(path, value):
        if Path(path).name == 'completed.json':
            raise t.Crash()
        return real_put(path, value)
    with patch.object(a, 'put', put):
        try:
            h.execute()
        except t.Crash:
            pass
    (h.run / 'ledger.lock').unlink()
    print('job1 has completed.json:', (h.run / 'job1/completed.json').exists(),
          '| ledger:', [e['type'] for e in h.entries()])
    stage = h.stage()
    h.queue = [t.packet(10_000_000), t.packet(20_000_000)]
    r = h.execute('S2-OPQ', 'job2', staged_path=stage)
    print('S2-OPQ admitted and dispatched: state', r['state'], '| POSTs:', len(h.posts))
    sys.exit(0 if len(h.posts) == 2 else 1)
