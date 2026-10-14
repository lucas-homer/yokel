"""Offline repro (R19 review Q3): R17/R18 ledgers, releases and call pins cannot bind to or replay
into R19 cells. Uses the adapter's own synthetic Harness (fake transport, fake clock); every refusal
is checked for zero POSTs, zero key reads where applicable, no attempt directory and unchanged ledger
bytes. Temp dirs are created under review/_out and removed. Positive control first."""
import copy
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parents[1]
ADAPTER = BENCH / 'round19-rerun/adapter'


def load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    sys.modules[name] = m
    s.loader.exec_module(m)
    return m


t = load('test_adapter', ADAPTER / 'test_adapter.py')
a = t.a
w18 = load('wire_r18_for_replay', BENCH / 'round18-rerun/wire/wire.py')
assert a.NAMESPACE == 'r19.paid-rerun.v1'
assert a.wire.REVISION == 'r16.w2.3' and w18.REVISION == 'r16.w2.2'


def fresh():
    tmp = tempfile.TemporaryDirectory(prefix='.review-iso-', dir=HERE / '_out')
    return tmp, t.Harness(tmp.name)


def rebind(h, entries):
    """Rewrite ledger entries and refresh the BIND_RELEASE hash to the current RELEASE.json."""
    entries[1]['release_sha256'] = a.sha(h.release_path.read_bytes())
    h.rewrite_ledger(entries)


def refused(h, cell='S1-OPQ', job='job1', **kw):
    before = (h.run / 'ledger.jsonl').read_bytes()
    try:
        h.execute(cell, job, **kw)
    except a.Refused as exc:
        reason = str(exc)
    else:
        raise AssertionError('expected Refused')
    return reason, before == (h.run / 'ledger.jsonl').read_bytes(), (h.run / job).exists()


results = []

# 0. Positive control: the unmodified synthetic R19 release dispatches exactly once.
tmp, h = fresh()
r = h.execute()
assert r['state'] == 13 and r['halt'] is None and len(h.posts) == 1
results.append(('control', 'state 13, posts=1'))
tmp.cleanup()

# 1. R18 ledger (INIT namespace r18.paid-rerun.v1) + release bound to that INIT.
for legacy_ns in ('r18.paid-rerun.v1', 'r17.paid-comparison.v1'):
    tmp, h = fresh()
    entries = h.entries()
    entries[0]['namespace'] = legacy_ns
    h.release['init_sha256'] = a.sha(a.encode(entries[0]))
    h.save_release()
    rebind(h, entries)
    reason, ledger_same, job_dir = refused(h)
    assert reason == 'init_namespace_key', reason
    assert ledger_same and not job_dir and h.posts == [] and h.key_reads == []
    results.append((f'legacy ledger+release ns={legacy_ns}', reason + ' (ledger unchanged, 0 key reads, 0 POST, no attempt dir)'))
    tmp.cleanup()

# 2. R19 ledger, but RELEASE.json carries an R18 INIT hash (R18 release re-pointed at an R19 ledger).
tmp, h = fresh()
legacy_init = copy.deepcopy(h.entries()[0])
legacy_init['namespace'] = 'r18.paid-rerun.v1'
h.release['init_sha256'] = a.sha(a.encode(legacy_init))
h.save_release()
rebind(h, h.entries())
reason, ledger_same, job_dir = refused(h)
assert reason == 'release_init_hash', reason
assert ledger_same and not job_dir and h.posts == [] and h.key_reads == []
results.append(('R18 release init hash on R19 ledger', reason + ' (ledger unchanged, 0 key reads, 0 POST)'))
tmp.cleanup()

# 3. Replayed R18 call pins: release calls computed with the frozen R18 wire (no A7) for the OPQ cell.
tmp, h = fresh()
p18 = w18.build(t.SOURCE, 'opaque')
h.release['calls']['S1-OPQ'] = dict(plan_request_sha256=p18['request_sha256'],
                                    dispatched_body_sha256=a.sha(a.dispatched(p18)))
assert h.release['calls']['S1-OPQ'] != dict(plan_request_sha256=a.wire.build(t.SOURCE, 'opaque')['request_sha256'],
                                             dispatched_body_sha256=a.sha(a.dispatched(a.wire.build(t.SOURCE, 'opaque'))))
h.save_release()
rebind(h, h.entries())
reason, ledger_same, job_dir = refused(h)
# The inner 'release_body_hashes' refusal fires after RESERVE and is surfaced as the generic
# pre-dispatch pause; the attempt receipt records the underlying reason and state 1 (never marked).
assert reason == 'pre_dispatch_pause', reason
assert h.posts == [] and len(h.key_reads) == 1
receipts = sorted(q.name for q in (h.run / 'job1').iterdir())
res = json.loads((h.run / 'job1/result.json').read_bytes())
assert res['state'] == 1 and res['debit'] == 0 and res['halt'] is None, res
assert receipts == ['key-preflight.json', 'result.json', 'stop.json'], receipts
print('  scenario 3 result.json:', json.dumps(res, sort_keys=True)[:400])
tail = [(e['type'], e.get('call'), e.get('dispatched'), e.get('debit')) for e in h.entries()[2:]]
assert tail == [('RESERVE', 'S1-OPQ', None, None), ('RESOLVE', 'S1-OPQ', False, 0)], tail
assert not (h.run / 'job1/request.json').exists() and not (h.run / 'job1/intent.json').exists()
results.append(('R18-wire call pins in R19 release', reason + f' [inner release_body_hashes] (0 POST, 1 key preflight read, ledger tail {tail}; no DISPATCH_MARK, no request/intent receipt; receipts {receipts})'))
tmp.cleanup()

# 3b. FULL-profile pins are unaffected by A7, so an R18 FULL pin equals an R19 FULL pin: that cell
# is not runnable in R19 anyway (release.required_calls = CALLS[:3], typed_testable False) — show both.
p18f, p19f = w18.build(t.SOURCE, 'full'), a.wire.build(t.SOURCE, 'full')
assert p18f['request_sha256'] == p19f['request_sha256']
tmp, h = fresh()
h.release['typed_testable'] = False
h.release['required_calls'] = a.CALLS[:3]
entries = h.entries()
entries[0]['required_calls'] = a.CALLS[:3]
h.release['init_sha256'] = a.sha(a.encode(entries[0]))
h.save_release()
rebind(h, entries)
reason, ledger_same, job_dir = refused(h, 'S1-FULL', 'jobF')
# The synthetic manifest declares typed_testable=True (6 compounds), so the gate refuses at
# manifest_slots before reaching required_calls/release_call_set; either way nothing is read or sent.
# The real R17 scoring manifest has typed_testable=False and N_c=4 (checked in repro_release_prep.py).
assert h.posts == [] and h.key_reads == [] and ledger_same and not job_dir
results.append(('FULL cell against OPQ-only release', reason + ' (0 key reads, 0 POST, ledger unchanged)'))
tmp.cleanup()
tmp, h = fresh()
reason, ledger_same, job_dir = refused(h, 'S1-FULL', 'jobF')
assert reason == 'wrong_cell_order', reason
assert h.posts == [] and h.key_reads == [] and ledger_same and not job_dir
results.append(('FULL cell before any OPQ cell', reason + ' (0 key reads, 0 POST, ledger unchanged)'))
tmp.cleanup()

# 4. R18 adapter bytes offered as the release's adapter artifact (adapter replay).
tmp, h = fresh()
old_adapter = (BENCH / 'round18-rerun/adapter/r17_adapter.py').read_bytes()
pin = h.write('adapter/r17_adapter.py', old_adapter)
h.release['artifacts']['adapter'] = pin
ready = dict(status='READY_OFFLINE_IMPLEMENTATION', sha256={'r17_adapter.py': pin['sha256'],
             'test_adapter.py': h.release['artifacts']['tests']['sha256']})
h.release['artifacts']['adapter_ready'] = h.write('adapter/READY.json', ready)
h.save_release()
rebind(h, h.entries())
reason, ledger_same, job_dir = refused(h)
assert reason == 'adapter_self_pin', reason
assert ledger_same and h.posts == [] and h.key_reads == []
results.append(('R18 adapter bytes as release artifact', reason + ' (ledger unchanged, 0 key reads, 0 POST)'))
tmp.cleanup()

# 5. Recon pin is intentionally shared with R18 (same frozen engine): not an isolation boundary.
assert a.RECON_SHA == '64794fdda2f345559a5399ccd8e83142a93e621fcb5c6e79842209a4d4c27140'
assert Path(a.recon.__file__) == BENCH / 'round18-rerun/recon/r17recon.py'
results.append(('recon pin', 'shared with R18 by design (64794fdd…); isolation rests on namespace + release/init hash + wire call pins'))

for name, outcome in results:
    print(f'{name}: {outcome}')
print('OK: no R17/R18 ledger, release, call pin or adapter artifact can bind to or dispatch an R19 cell')
