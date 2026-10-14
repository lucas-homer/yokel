"""R-E (NOTE): recover() is not idempotent for a cell that already ended normally with a
KEY_USAGE_UNRECONCILED halt (RESOLVE + HALT, stop.json present). missing_recon selects it,
recover() appends a second HALT and writes recovered.json claiming a recovered dispatch.
Harmless for money, but it muddies the evidence trail. Fakes only."""
import importlib.util, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('_load', Path(__file__).resolve().parent / '_load.py')
L = importlib.util.module_from_spec(spec); spec.loader.exec_module(L)
a, t = L.load()

with L.tempdir() as d:
    h = t.Harness(d)
    h.queue = [t.packet(0)]                        # stale zero forever -> UNRECONCILED halt
    r = h.execute()
    print('cell ended normally: halt =', r['halt'], '; stop.json exists =', (h.run / 'job1/stop.json').exists())
    before = [e['type'] for e in h.entries()]
    recovered = a.recover(run_root=h.run, key_info=h.key_info, clock=h.clock)
    after = [e['type'] for e in h.entries()]
    print('recover() returned', recovered)
    print('entries before:', before)
    print('entries after :', after)
    print('recovered.json:', (h.run / 'job1/recovered.json').read_bytes().decode())
    sys.exit(0 if after.count('HALT') == 2 else 1)
