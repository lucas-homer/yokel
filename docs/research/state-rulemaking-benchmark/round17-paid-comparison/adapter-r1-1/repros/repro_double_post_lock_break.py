"""R-B (SHOULD-FIX): Ledger.append never re-checks the on-disk tail, so an invocation
whose lock was removed while it was still alive can append DISPATCH_MARK onto a ledger
that another process has already advanced, and POST a cell that the other process also
POSTed. Precondition: a human breaks the lock while the owner is alive (forbidden by
BUDGET §4 rule 10), so this is procedural, but the window between ledger.verify (line 839)
and the DISPATCH_MARK append (line 850) is open and cheap to close.
Interleaving is injected by wrapping staged_gate's second call (line 845), which runs
after the last ledger.verify and before the DISPATCH_MARK append. Fakes only."""
import importlib.util, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('_load', Path(__file__).resolve().parent / '_load.py')
L = importlib.util.module_from_spec(spec); spec.loader.exec_module(L)
a, t = L.load()

with L.tempdir() as d:
    h = t.Harness(d)
    real_gate = a.staged_gate
    state = dict(calls=0, busy=False)
    def interleaved_gate(*args, **kwargs):
        state['calls'] += 1
        if state['calls'] == 2 and not state['busy']:
            state['busy'] = True
            # --- the forbidden operator action: break the live lock, "recover", re-run ---
            (h.run / 'ledger.lock').unlink()
            evidence = h.run / 'lock-evidence.json'
            evidence.write_bytes(a.encode(dict(owner_gone=True, evidence='WRONG: owner alive')))
            a.recover(run_root=h.run, key_info=h.key_info, clock=h.clock, lock_evidence=evidence)
            h.queue = [t.packet(0), t.packet(10_000_000)]
            h.execute(job='job-second')          # POST #1 for S1-OPQ by the second process
            # second process removed its own lock on exit; recreate so A's finally unlink works
            (h.run / 'ledger.lock').write_bytes(b'{}')
        return real_gate(*args, **kwargs)
    a.staged_gate = interleaved_gate
    real_post = h.post
    posts = []
    def counting_post(url, raw):
        posts.append(url)
        # Skip the harness's disk assertions for the stale writer; just return a response.
        import copy
        return copy.deepcopy(h.response)
    h.post = counting_post
    h.queue = [t.packet(0), t.packet(10_000_000)]
    try:
        h.execute(job='job-first')                # POST #2 for S1-OPQ by the original process
    except Exception as exc:
        print('original invocation ended with', type(exc).__name__, exc)
    a.staged_gate = real_gate
    kinds = [e['type'] + ':' + str(e.get('call', '')) + ':' + str(e.get('attempt_dir', e.get('job_id', ''))) for e in h.entries()]
    print('POSTs for S1-OPQ:', len(posts))
    print('ledger entries:'); print('\n'.join('  ' + k for k in kinds))
    # Chain state after the stale append:
    try:
        lg = a.Ledger(h.run, h.clock)
        with lg.lock('inspect'):
            lg.load()
        print('ledger chain loads cleanly: True')
    except Exception as exc:
        print('ledger chain loads cleanly: False ->', exc)
    sys.exit(0 if len(posts) == 2 else 1)
