"""R-G (NOTE): recovery trusts receipt files by existence. A recon-N.json that was torn by a
crash mid-write (exists, not valid JSON) makes recover() raise before it writes anything,
so the run can neither be recovered nor advanced by the adapter. put() uses write+fsync but
not write-to-temp+rename, so a torn receipt is possible on power loss. Fakes only."""
import importlib.util, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('_load', Path(__file__).resolve().parent / '_load.py')
L = importlib.util.module_from_spec(spec); spec.loader.exec_module(L)
a, t = L.load()

with L.tempdir() as d:
    h = t.Harness(d)
    def crash(stage, *_):
        if stage == 'after_resolve':
            raise t.Crash()
    try:
        h.execute(hook=crash)
    except t.Crash:
        pass
    (h.run / 'ledger.lock').unlink()
    receipt = h.run / 'job1' / 'recon-0.json'
    raw = receipt.read_bytes()
    receipt.write_bytes(raw[: len(raw) // 2])     # torn receipt
    try:
        a.recover(run_root=h.run, key_info=h.key_info, clock=h.clock)
        print('recover succeeded'); sys.exit(1)
    except Exception as exc:
        print('recover() aborted with', type(exc).__name__, '-', str(exc)[:80])
        print('ledger tail:', [e['type'] for e in h.entries()[-3:]])
        print('lock left behind by recover():', (h.run / 'ledger.lock').exists())
        sys.exit(0)
