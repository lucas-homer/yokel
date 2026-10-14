"""R-H (NOTE): `marked` is set only after append() returns. If the DISPATCH_MARK bytes reach
the file but fsync raises, the except branch believes the cell is unmarked and appends
RESOLVE(dispatched=False, debit=0). No POST happens (good), but the on-disk ledger now
contradicts rule 8 and the next load refuses it forever. (Observed code: `ledger_chain`,
because append() raised before updating the in-memory tail, so the RESOLVE's prev_sha256
points at RESERVE while the on-disk predecessor is the DISPATCH_MARK; had the fsync
succeeded on retry the code would be `ledger_dispatch_debit`.) Setting
`marked = True` before the append (or treating any exception from that append as marked)
would route this to the conservative path instead. Fakes only."""
import importlib.util, sys
from pathlib import Path
from unittest.mock import patch
spec = importlib.util.spec_from_file_location('_load', Path(__file__).resolve().parent / '_load.py')
L = importlib.util.module_from_spec(spec); spec.loader.exec_module(L)
a, t = L.load()

with L.tempdir() as d:
    h = t.Harness(d)
    real_fsync = a.os.fsync
    armed = dict(on=False, fired=False)
    def fsync(fd):
        if armed['on'] and not armed['fired']:
            tail = (h.run / 'ledger.jsonl').read_bytes().splitlines()[-1]
            if b'"type":"DISPATCH_MARK"' in tail:
                armed['fired'] = True
                raise OSError('synthetic fsync failure after DISPATCH_MARK bytes were written')
        return real_fsync(fd)
    def arm(stage, *_):
        if stage == 'before_mark':
            armed['on'] = True
    with patch.object(a.os, 'fsync', fsync):
        try:
            h.execute(hook=arm)
        except a.Refused as exc:
            print('invocation ended with Refused:', exc)
    print('POSTs:', len(h.posts))
    print('ledger tail:', [(e['type'], e.get('dispatched'), e.get('debit')) for e in h.entries()[-3:]])
    try:
        h.execute(job='job2'); print('next load OK'); sys.exit(1)
    except a.Refused as exc:
        print('next invocation refused with:', exc)
        sys.exit(0 if str(exc) in ('ledger_chain', 'ledger_dispatch_debit') else 1)
