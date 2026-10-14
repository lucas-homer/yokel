"""R-C (SHOULD-FIX): staged_gate is re-run after RESERVE (line 845). If the primary
replaces the staged-gate/report files between the two calls so the second call sees a stop,
staged_gate appends SKIP entries while a RESERVE is pending, then the pre-dispatch except
branch appends RESOLVE(dispatched=False). ledger_shapes rejects SKIP-while-pending on the
next load, so every later execute_once AND recover() refuses: the ledger is bricked with
no money spent and no adapter path to repair it. Zero-dollar, but it kills the experiment
and invites manual ledger surgery. Fakes only."""
import importlib.util, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('_load', Path(__file__).resolve().parent / '_load.py')
L = importlib.util.module_from_spec(spec); spec.loader.exec_module(L)
a, t = L.load()

with L.tempdir() as d:
    h = t.Harness(d)
    h.execute()                                    # S1-OPQ completes (1 POST)
    stage = h.stage(state='reachable')             # primary accepts: S2 may run
    def swap_gate(stage_name, ledger, folder):
        if stage_name == 'before_mark':
            h.stage(state='unreachable')           # same paths, re-written mid-invocation
    h.queue = [t.packet(10_000_000), t.packet(20_000_000)]
    try:
        h.execute('S2-OPQ', 'job2', staged_path=stage, hook=swap_gate)
    except a.Refused as exc:
        print('second invocation refused with:', exc)
    print('POSTs so far:', len(h.posts))
    print('ledger tail:', [(e['type'], e.get('call'), e.get('dispatched')) for e in h.entries()[-7:]])
    outcomes = {}
    for name, fn in (('execute_once S2-OPQ fresh job', lambda: h.execute('S2-OPQ', 'job3', staged_path=h.stage())),
                     ('recover()', lambda: a.recover(run_root=h.run, key_info=h.key_info, clock=h.clock))):
        try:
            fn(); outcomes[name] = 'OK'
        except Exception as exc:
            outcomes[name] = type(exc).__name__ + ': ' + str(exc)
    for k, v in outcomes.items():
        print(f'{k}: {v}')
    bricked = all('ledger_impossible_skip' in v for v in outcomes.values())
    print('ledger bricked (both paths refuse on ledger_impossible_skip):', bricked)
    sys.exit(0 if bricked else 1)
