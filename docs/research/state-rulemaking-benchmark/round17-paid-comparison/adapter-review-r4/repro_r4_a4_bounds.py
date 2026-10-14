"""Q4: with KEY_MAX = $50, what still bounds spend, and exactly what the old $1.73 ceiling blocked.

Pure engine comparison (design-r3-1 recon vs recon-a4) over a grid, plus the adapter's
INIT/attestation/machine gates. No I/O beyond the two pinned engine files.
"""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import _load as L
a = L.a
old = L.load('r4_recon_old', L.R17 / 'design-r3-1/fixtures/r17recon.py')
new = L.load('r4_recon_new', L.R17 / 'recon-a4/r17recon.py')
results = []
USD = 1_000_000_000


def check(name, ok, detail=''):
    results.append(ok)
    print(('ok   ' if ok else 'FAIL ') + name + ('  ' + detail if detail else ''))


check('only KEY_MAX differs between engines',
      old.KEY_MAX == 1_730_000_000 and new.KEY_MAX == 50 * USD and
      all(getattr(old, n) == getattr(new, n) for n in ('CAP', 'OPERATING', 'FLOOR', 'TOL_PER_CALL', 'READ_SCHEDULE_S', 'RELEASE_POLICIES')))
check('adapter imports recon-a4 (KEY_MAX $50) and KEY_LABEL DocketClock', a.recon.KEY_MAX == 50 * USD and a.KEY_LABEL == 'DocketClock')

# INIT-level key_limit_ok for a 3-call plan
print('# key_limit_ok(limit, 3): old vs new')
for usd in (0.80, 0.81, 1.73, 1.74, 49.99, 50.0, 50.000000001, 100):
    lim = int(round(usd * USD))
    print('   $%-14s old=%-5s new=%s' % (usd, old.key_limit_ok(lim, 3), new.key_limit_ok(lim, 3)))
check('new admits INIT key limits in [$0.81, $50]; old admitted [$0.81, $1.73]',
      new.key_limit_ok(810_000_000, 3) and new.key_limit_ok(50 * USD, 3) and not new.key_limit_ok(50 * USD + 1, 3)
      and not new.key_limit_ok(809_999_999, 3) and not old.key_limit_ok(1_730_000_001, 3))

# admission grid: for a 3-call plan with key_limit = $50 (new) and $1.73 (old), vary aggregate and reconciled usage
def ledger(aggregate_done, usage, key_limit, done_calls=0, up=0):
    calls = ['S1-OPQ', 'S2-OPQ', 'S3-OPQ']
    e = [dict(type='INIT', required_calls=calls, key_limit=key_limit, release_policy='P-ACCEPT'),
         dict(type='BIND_RELEASE', release_policy='P-ACCEPT')]
    per = aggregate_done // max(done_calls, 1) if done_calls else 0
    for c in calls[:done_calls]:
        e += [dict(type='RESOLVE', call=c, dispatched=True, debit=per), dict(type='RECONCILED', call=c, U=usage)]
    if up:
        e.append(dict(type='RECONCILE_UP', debit=up))
    return e, calls[done_calls] if done_calls < 3 else None

print('# admission for the NEXT call (new engine, key_limit $50)')
for done, agg_usd in ((0, 0), (1, 0.27), (1, 1.50), (1, 1.53), (1, 1.54), (2, 1.26), (2, 1.26 + 0.01), (2, 1.53), (2, 1.54)):
    e, nxt = ledger(int(round(agg_usd * USD)), int(round(agg_usd * USD)), 50 * USD, done)
    print('   done=%d aggregate=$%.2f usage=$%.2f -> %s' % (done, agg_usd, agg_usd, new.admit(e, nxt, int(round(agg_usd * USD)))))
e, nxt = ledger(1_530_000_000, 1_530_000_000, 50 * USD, 1)
check('OPERATING binds: 1 done at $1.53 -> remaining 2 x FLOOR = $0.54 -> $2.07 > $1.80 refused', new.admit(e, nxt, 1_530_000_000) == (False, 'operating limit'))
e, nxt = ledger(1_260_000_000, 1_260_000_000, 50 * USD, 2)
check('OPERATING binds: 2 done at $1.26 -> +$0.27 = $1.53 <= $1.80 admitted', new.admit(e, nxt, 1_260_000_000) == (True, None))
e, nxt = ledger(1_540_000_000, 1_540_000_000, 50 * USD, 2)
check('OPERATING binds: 2 done at $1.54 -> +$0.27 = $1.81 > $1.80 refused', new.admit(e, nxt, 1_540_000_000) == (False, 'operating limit'))
e, nxt = ledger(0, 0, 50 * USD, 0, up=1_000_000_000)
check('all-remaining reservation: RECONCILE_UP $1.00 before any call -> 1.00 + 3 x 0.27 = 1.81 refused', new.admit(e, nxt, 0) == (False, 'operating limit'))
e, nxt = ledger(0, 0, 50 * USD, 0, up=990_000_000)
check('                           RECONCILE_UP $0.99 -> 0.99 + 0.81 = 1.80 admitted (boundary)', new.admit(e, nxt, 0) == (True, None))

# exhaustive diff of admit() between engines over a grid (what the $50 key lets through that $1.73 blocked)
diffs = []
grid = [x * 10_000_000 for x in range(0, 181)]  # $0.00 .. $1.80 in cents
for done in (0, 1, 2):
    for agg in grid:
        for usage in grid:
            # ledger-consistent states only: no RECONCILED usage before a completed call; each completed call
            # debited at least FLOOR; aggregate >= highest reconciled usage (close_debit's RECONCILE_UP).
            if done == 0 and (usage or agg):
                continue
            if done and (agg < done * new.FLOOR or usage > agg):
                continue
            e_old, nxt = ledger(agg, usage, 1_730_000_000, done)
            e_new, _ = ledger(agg, usage, 50 * USD, done)
            ro, rn = old.admit(e_old, nxt, usage), new.admit(e_new, nxt, usage)
            if ro != rn:
                diffs.append((done, agg, usage, ro, rn))
band = {(d_, usage + (3 - d_) * new.FLOOR) for d_, agg, usage, ro, rn in diffs}
print('# admit() differences old($1.73 key) vs new($50 key) over the grid: %d states' % len(diffs))
for d_, agg, usage, ro, rn in diffs[:6]:
    print('   done=%d aggregate=$%.2f usage=$%.2f old=%s new=%s' % (d_, agg / USD, usage / USD, ro, rn))
check('every difference is the old "key capacity" refusal where usage + remaining x FLOOR lies in ($1.73, $1.80]',
      diffs and all(ro == (False, 'key capacity') and rn == (True, None) and 1_730_000_000 < usage + (3 - d_) * new.FLOOR <= new.OPERATING
                    for d_, agg, usage, ro, rn in diffs))
print('   i.e. the $50 key admits a next call when reconciled usage is up to $0.07 higher than before; the OPERATING $1.80 and')
print('   CAP $2.00 bounds, FLOOR reservation of all remaining calls, no-retry and debit>FLOOR halts are unchanged.')

# adapter INIT gate: key_limit must equal the live limit; attestation + machine check must agree
with L.tempdir('a4') as tmp:
    h = L.Harness(tmp)
    h.release['required_calls'] = h.init['required_calls'] = a.CALLS[:3]
    h.release['calls'] = {c: h.release['calls'][c] for c in a.CALLS[:3]}
    h.release['typed_testable'] = False
    import json
    man = a.read(h.root / h.release['artifacts']['scoring_manifest']['path'])
    man['typed_testable'] = False
    for s in man['sources'].values():
        s['compounds'] = {}
    h.release['artifacts']['scoring_manifest'] = h.write(h.release['artifacts']['scoring_manifest']['path'], man)
    h.release['thresholds'].update(N_c=0, T4=0)

    def bind():
        h.init['key_limit'] = h.init.get('key_limit', a.recon.KEY_MAX)
        h.release['init_sha256'] = a.sha(a.encode(h.init))
        h.save_release()
        h.rewrite_ledger([h.init, dict(type='BIND_RELEASE', release_policy='P-HARD',
                                     release_sha256=a.sha(h.release_path.read_bytes()))])
    bind()
    # live preflight GET reports a $1.73 limit while INIT says $50 -> refused before POST
    h.queue = [L.packet(0, limit=1_730_000_000), L.packet(0, limit=1_730_000_000)]
    try:
        h.execute('S1-OPQ', 'j1')
        check('live key limit != INIT key_limit refused', False)
    except a.Refused as exc:
        check('live key limit ($1.73) != INIT key_limit ($50) -> refused pre_dispatch_pause, 0 POST', str(exc) == 'pre_dispatch_pause' and h.posts == [])
    # live limit resets -> refused
    h.queue = [L.packet(0, reset='monthly'), L.packet(0, reset='monthly')]
    try:
        h.execute('S1-OPQ', 'j2')
        check('resetting live key refused', False)
    except a.Refused as exc:
        check('live key with limit_reset -> refused pre_dispatch_pause, 0 POST', str(exc) == 'pre_dispatch_pause' and h.posts == [])
    # live usage already nonzero at S1 -> refused (pre_key_usage: cumulative reported 0, tolerance 0)
    h.queue = [L.packet(5_000), L.packet(5_000)]
    try:
        h.execute('S1-OPQ', 'j3')
        check('nonzero initial live usage refused', False)
    except a.Refused as exc:
        check('live usage $0.000005 at S1 with 0 marks -> refused (tolerance count*1000 nano = 0), 0 POST', str(exc) == 'pre_dispatch_pause' and h.posts == [])
    # a single call charged far above FLOOR (the residual risk): adapter HALTs after the fact; the charge is the key's
    h.queue = [L.packet(0), L.packet(800_000_000)]
    r = h.execute('S1-OPQ', 'j4')
    check('one call whose key delta is $0.80 (> FLOOR): debit $0.80, HALT debit_exceeds_floor, 1 POST', r['debit'] == 800_000_000 and r['halt'] == 'debit_exceeds_floor' and len(h.posts) == 1, str((r['debit'], r['halt'])))
    adm = a.recon.admit(h.entries(), 'S2-OPQ', a.last_usage(h.entries()))
    try:
        h.execute('S2-OPQ', 'j5', staged_path=h.stage())
        check('after HALT nothing dispatches', False)
    except a.Refused as exc:
        check('S2 after that HALT -> refused (%s; CLI probe admit(S2)=%s), still 1 POST total' % (exc, adm),
              adm == (False, 'halted') and len(h.posts) == 1)

print('SUMMARY A4 bounds:', sum(results), 'of', len(results), 'checks held')
sys.exit(0 if all(results) else 1)
