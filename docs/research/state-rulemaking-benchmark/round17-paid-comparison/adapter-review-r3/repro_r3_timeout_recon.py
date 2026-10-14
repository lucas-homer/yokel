"""TIMEOUT_S = 900 (S4) against the frozen reconciliation schedule (0, 60, 300, 900 s).

Fake clock: a callback that "hangs" advances the clock by TIMEOUT_S before failing, the
way a blocked socket read returns after the envelope. Shows where resolved_at lands, that
no read is ever 'before its scheduled time', that a hung GET consumes its slot and the
later reads run immediately with elapsed >= due, and that a late provider charge is still
debited through the key delta. Exit 0 = every check holds.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I drops the script dir
from _load import load, tempdir, banner

a, t, d = load()
FLOOR, SCHED = a.recon.FLOOR, a.recon.READ_SCHEDULE_S
problems = []


def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond:
        problems.append(what)


def receipts(h, job='job1'):
    out = []
    for due in SCHED:
        p = h.run / job / f'recon-{due}.json'
        out.append(a.read(p) if p.exists() else None)
    return out


banner('A. POST blocks for the full %d s envelope, then fails; provider charged meanwhile' % d.TIMEOUT_S)
with tempdir() as tmp:
    h = t.Harness(tmp)
    def hanging_post(url, raw):
        h.posts.append((url, raw))
        h.clock.t += d.TIMEOUT_S
        raise RuntimeError('transport_failed')          # the driver's key-free fixed error
    h.post = hanging_post
    X = 500_000_000                                      # > FLOOR: what the key shows afterwards
    h.queue = [t.packet(0), t.packet(X)]
    t0 = h.clock.now()
    result = h.execute()
    status = a.read(h.run / 'job1/status.json')
    resolved_at = float(status['resolved_at'])
    check(resolved_at == t0 + d.TIMEOUT_S, 'resolved_at is AFTER the envelope (t0+%d): %s' % (d.TIMEOUT_S, status['resolved_at']))
    check(status['http_status'] is None, 'status None (transport-uncertain)')
    rs = receipts(h)
    check(all(r and r['scheduled_s'] == due and r['elapsed_s'] >= due for r, due in zip(rs, SCHED)),
          'four reads, each elapsed_s >= due, measured from resolved_at: %s' % [(r['scheduled_s'], r['elapsed_s']) for r in rs])
    check(h.key_reads == [t0] + [resolved_at + due for due in SCHED], 'GET times = preflight, then resolved_at + schedule: %s' % h.key_reads)
    verdict = a.read(h.run / 'job1/reconciliation.json')['verdict']
    check(verdict == ['HALT', 'KEY_USAGE_UNRECONCILED'], 'verdict %s (no reported cost to match)' % verdict)
    check(result['state'] == 2 and result['halt'] == 'debit_exceeds_floor', 'row 2; halt %r (the floor-exceeding key delta outranks the reconciliation verdict in the HALT reason)' % result['halt'])
    check(result['debit'] == X and a.recon.aggregate(h.entries()) == X, 'debit = key delta %d (> FLOOR %d)' % (X, FLOOR))
    check(len(h.posts) == 1, 'one POST')
    ok, reason = a.recon.admit(h.entries(), 'S2-OPQ', a.last_usage(h.entries()))
    check(not ok and reason == 'halted', 'next cell refused: halted')

banner('B. good POST; the FIRST reconciliation GET blocks for the envelope, then fails')
with tempdir() as tmp:
    h = t.Harness(tmp)
    original = h.key_info
    n = {'calls': 0}
    def hanging_first_read(url):
        n['calls'] += 1
        if n['calls'] == 2:                               # preflight is call 1
            h.clock.t += d.TIMEOUT_S
            h.key_reads.append(h.clock.now())
            raise RuntimeError('transport_failed')
        return original(url)
    h.key_info = hanging_first_read
    result = h.execute()
    rs = receipts(h)
    check(rs[0]['read_failed'] is True and rs[0]['elapsed_s'] == 0, 'slot 0 consumed as a failed read (elapsed recorded before the GET)')
    check(rs[1] is not None and rs[1]['elapsed_s'] >= d.TIMEOUT_S and rs[1]['parsed'] is not None,
          'slot 60 runs immediately after the hang with elapsed %s >= 60' % rs[1]['elapsed_s'])
    check(rs[2] is None and rs[3] is None, 'reconciled at slot 60; no further reads')
    check(result['state'] == 13 and not result['halt'], 'state 13, no halt')
    recon = a.read(h.run / 'job1/reconciliation.json')
    check(recon['verdict'][0] == 'RECONCILED' and recon['reads'] == 2, 'RECONCILED after 2 reads, no "read before its scheduled time"')
    check(len(h.posts) == 1, 'one POST')

banner('C. good POST; ALL four reconciliation GETs block and fail: bounded at four')
with tempdir() as tmp:
    h = t.Harness(tmp)
    original = h.key_info
    n = {'calls': 0}
    def hanging_reads(url):
        n['calls'] += 1
        if n['calls'] >= 2:
            h.clock.t += d.TIMEOUT_S
            h.key_reads.append(h.clock.now())
            raise RuntimeError('transport_failed')
        return original(url)
    h.key_info = hanging_reads
    result = h.execute()
    rs = receipts(h)
    check(all(r and r['read_failed'] for r in rs) and n['calls'] == 5, 'four failed reads, five GETs in total (preflight + 4)')
    check(result['state'] == 13 and result['halt'] == 'KEY_USAGE_UNRECONCILED' and result['debit'] == FLOOR,
          'valid response (state 13) but halt KEY_USAGE_UNRECONCILED, debit FLOOR (reported 0.01 USD < FLOOR)')
    check([e['type'] for e in h.entries()][-2:] == ['RESOLVE', 'HALT'], 'ledger ends RESOLVE, HALT')
    check(len(h.posts) == 1, 'one POST')
    print('     worst-case wall clock per cell with every operation at the envelope: POST %d + schedule %d + 4 x %d GET = %d s (%.1f h); the lock is held throughout'
          % (d.TIMEOUT_S, SCHED[-1], d.TIMEOUT_S, d.TIMEOUT_S + SCHED[-1] + 4 * d.TIMEOUT_S, (d.TIMEOUT_S + SCHED[-1] + 4 * d.TIMEOUT_S) / 3600))

banner('D. preflight GET blocks and fails: zero-debit pause, no POST')
with tempdir() as tmp:
    h = t.Harness(tmp)
    def hanging_preflight(url):
        h.clock.t += d.TIMEOUT_S
        h.key_reads.append(h.clock.now())
        raise RuntimeError('transport_failed')
    h.key_info = hanging_preflight
    try:
        h.execute()
        check(False, 'should refuse')
    except a.Refused as exc:
        check(str(exc) == 'pre_dispatch_pause', 'refused: %s' % exc)
    check(h.posts == [] and a.recon.aggregate(h.entries()) == 0, 'no POST, aggregate 0')
    types = [e['type'] for e in h.entries()]
    stop = a.read(h.run / 'job1/result.json')
    check(types == ['INIT', 'BIND_RELEASE'] and stop['state'] == 1 and stop['debit'] == 0,
          'no RESERVE written (preflight precedes the reservation); result.json state 1 debit 0')

print()
print('problems:', problems)
sys.exit(0 if not problems else 1)
