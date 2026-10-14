"""3-call plan (E8: typed logic untestable, FULL omitted; R0 = 3) through the r1.1 adapter.

Builds a release with typed_testable=False, required_calls = S1/S2/S3-OPQ and a manifest
with 4 pooled compounds (1/2/1 like E8-SUFFICIENCY) and checks:
 A. happy path: three cells, three POSTs, aggregate 3*FLOOR, nothing further admitted;
 B. admission R values: key_limit exactly 3*FLOOR admits all three; 3*FLOOR-1 is refused
    at release_gate (key_limit) and by recon.admit (key capacity);
 C. semantic futility after S1: SKIPs exactly S2-OPQ and S3-OPQ (no FULL ids);
 D. mechanical futility on S1 (finish=length): SKIPs exactly S2-OPQ, S3-OPQ with D1;
 E. a 6-call release or INIT against a 4-compound manifest is refused (P6_E8_counts /
    required_calls), a FULL cell is refused, typed_testable mismatch refused.
Exit 0 = all expectations held.
"""
import copy
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # -I drops the script dir
from _load import load, tempdir, banner

a, t, _ = load()
problems = []


def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond:
        problems.append(what)


def three_call(h, key_limit=a.recon.KEY_MAX, compounds=(1, 2, 1)):
    artifacts = h.release['artifacts']
    manifest = a.read(h.root / artifacts['scoring_manifest']['path'])
    manifest['typed_testable'] = False
    for (slot, source), n in zip(sorted(manifest['sources'].items()), compounds):
        source['compounds'] = {f'c{j}': False for j in range(n)}
    artifacts['scoring_manifest'] = h.write(artifacts['scoring_manifest']['path'], manifest)
    nc = sum(compounds)
    counts = [len(manifest['sources'][s]['relations']) for s in ('S1', 'S2', 'S3')]
    h.release['typed_testable'] = False
    h.release['required_calls'] = h.init['required_calls'] = a.CALLS[:3]
    h.release['calls'] = {cell: h.release['calls'][cell] for cell in a.CALLS[:3]}
    h.release['thresholds'].update(N_c=nc, T4=(9 * nc + 9) // 10)
    h.init['key_limit'] = key_limit
    for name in ('key_attestation', 'machine_check'):
        rec = a.read(h.root / artifacts[name]['path'])
        rec['limit'] = key_limit
        if name == 'machine_check':
            rec['limit_remaining'] = key_limit
        artifacts[name] = h.write(artifacts[name]['path'], rec)
    h.release['init_sha256'] = a.sha(a.encode(h.init))
    h.save_release()
    h.rewrite_ledger([h.init, dict(type='BIND_RELEASE', release_policy='P-HARD',
                                 release_sha256=a.sha(h.release_path.read_bytes()))])
    return nc, counts


def pk(usage, limit):
    return t.packet(usage, limit=limit)


banner('A. happy path, three cells')
with tempdir() as tmp:
    h = t.Harness(tmp)
    three_call(h)
    for index, cell in enumerate(a.CALLS[:3]):
        gate = h.stage() if index else None
        h.queue = [t.packet(index * 10_000_000), t.packet((index + 1) * 10_000_000)]
        ok, reason = a.recon.admit(h.entries(), cell, a.last_usage(h.entries()))
        result = h.execute(cell, f'p9-{index}', staged_path=gate)
        check(ok and result['state'] == 13 and result['halt'] is None, '%s admitted and valid (R=%d)' % (cell, 3 - index))
    check(len(h.posts) == 3, 'three POSTs')
    check(result['aggregate'] == 3 * a.recon.FLOOR, 'aggregate 3*FLOOR')
    entries = h.entries()
    check(not any(e['type'] == 'SKIP' for e in entries), 'no SKIP entries after a clean 3-call run')
    for cell in a.CALLS:
        ok, reason = a.recon.admit(entries, cell, a.last_usage(entries))
        check(not ok, 'post-run admit(%s) refused: %s' % (cell, reason))
    for cell, job in (('S1-FULL', 'f1'), ('S1-OPQ', 'again')):
        try:
            h.execute(cell, job, staged_path=h.stage())
            check(False, cell + ' should be refused')
        except a.Refused as exc:
            check(True, '%s refused: %s' % (cell, exc))
    check(len(h.posts) == 3, 'still three POSTs')

banner('B. admission R values at the key limit boundary')
with tempdir() as tmp:
    h = t.Harness(tmp)
    L = 3 * a.recon.FLOOR
    three_call(h, key_limit=L)
    check(a.recon.key_limit_ok(L, 3) and not a.recon.key_limit_ok(L - 1, 3) and not a.recon.key_limit_ok(L, 6),
          'key_limit_ok(3*FLOOR,3) true; (3*FLOOR-1,3) false; (3*FLOOR,6) false')
    for index, cell in enumerate(a.CALLS[:3]):
        gate = h.stage() if index else None
        h.queue = [pk(index * 10_000_000, L), pk((index + 1) * 10_000_000, L)]
        result = h.execute(cell, f'b-{index}', staged_path=gate)
        check(result['state'] == 13 and result['halt'] is None, '%s dispatched with L = 3*FLOOR' % cell)
    check(len(h.posts) == 3, 'three POSTs at the exact key limit')
with tempdir() as tmp:
    h = t.Harness(tmp)
    L = 3 * a.recon.FLOOR - 1
    three_call(h, key_limit=L)
    h.queue = [pk(0, L), pk(1_000, L)]
    try:
        h.execute('S1-OPQ', 'under')
        check(False, 'should refuse')
    except a.Refused as exc:
        check(str(exc) == 'key_limit', 'L = 3*FLOOR-1 refused at release_gate: %s' % exc)
    ok, reason = a.recon.admit(h.entries(), 'S1-OPQ', 0)
    check(not ok and reason == 'key capacity', 'recon.admit also refuses: %s' % reason)
    check(h.posts == [], 'no POST')

banner('C. semantic futility after S1 skips exactly the two remaining OPQ cells')
with tempdir() as tmp:
    h = t.Harness(tmp)
    three_call(h)
    h.execute('S1-OPQ', 'c-0')
    gate = h.stage(state='unreachable')
    h.queue = [t.packet(10_000_000), t.packet(20_000_000)]
    try:
        h.execute('S2-OPQ', 'c-1', staged_path=gate)
        check(False, 'should stop')
    except a.Refused as exc:
        check(str(exc) == 'semantic_futility_stop', 'refused: %s' % exc)
    skips = [(e['call'], e['rule_id']) for e in h.entries() if e['type'] == 'SKIP']
    check(skips == [('S2-OPQ', 'OPQ-semantic-futility'), ('S3-OPQ', 'OPQ-semantic-futility')], 'SKIPs: %r' % skips)
    check(len(h.posts) == 1, 'one POST')
    ok, reason = a.recon.admit(h.entries(), 'S3-OPQ', a.last_usage(h.entries()))
    check(not ok, 'S3-OPQ refused afterwards: %s' % reason)

banner('D. mechanical futility on S1 (finish=length) skips exactly S2-OPQ, S3-OPQ with D1')
with tempdir() as tmp:
    h = t.Harness(tmp)
    three_call(h)
    h.mutate_response(lambda v: v['choices'][0].update(finish_reason='length', native_finish_reason='length'))
    result = h.execute('S1-OPQ', 'd-0')
    check(result['state'] == 11 and result['halt'] is None, 'state 11, no halt')
    skips = [(e['call'], e['rule_id']) for e in h.entries() if e['type'] == 'SKIP']
    check(skips == [('S2-OPQ', 'D1'), ('S3-OPQ', 'D1')], 'SKIPs: %r' % skips)
    try:
        h.execute('S2-OPQ', 'd-1', staged_path=h.stage())
        check(False, 'should refuse')
    except a.Refused as exc:
        check(str(exc) in ('wrong_cell_order', 'futility_ended_run') or str(exc).startswith('admission:'), 'S2 refused: %s' % exc)
    check(len(h.posts) == 1, 'one POST')

banner('E. plan/manifest consistency refusals')
with tempdir() as tmp:
    h = t.Harness(tmp)
    three_call(h)
    # 6-call release against the same 4-compound manifest
    h.release['typed_testable'] = True
    h.release['required_calls'] = h.init['required_calls'] = a.CALLS
    h.release['init_sha256'] = a.sha(a.encode(h.init))
    h.save_release()
    h.rewrite_ledger([h.init, dict(type='BIND_RELEASE', release_policy='P-HARD',
                                 release_sha256=a.sha(h.release_path.read_bytes()))])
    try:
        h.execute('S1-OPQ', 'e-0')
        check(False, 'should refuse')
    except a.Refused as exc:
        check(str(exc) in ('manifest_slots', 'P6_E8_counts', 'release_call_set', 'typed_testable'), '6-call plan with 4 compounds refused: %s' % exc)
    check(h.posts == [], 'no POST')
with tempdir() as tmp:
    h = t.Harness(tmp)
    three_call(h, compounds=(2, 2, 1))   # 5 compounds but release says untestable
    try:
        h.execute('S1-OPQ', 'e-1')
        check(False, 'should refuse')
    except a.Refused as exc:
        check(str(exc) == 'P6_E8_counts', '3-call plan with 5 compounds refused: %s' % exc)
with tempdir() as tmp:
    h = t.Harness(tmp)
    three_call(h)
    # INIT says 6 calls while the release says 3
    h.init['required_calls'] = a.CALLS
    h.release['init_sha256'] = a.sha(a.encode(h.init))
    h.save_release()
    h.rewrite_ledger([h.init, dict(type='BIND_RELEASE', release_policy='P-HARD',
                                 release_sha256=a.sha(h.release_path.read_bytes()))])
    try:
        h.execute('S1-OPQ', 'e-2')
        check(False, 'should refuse')
    except a.Refused as exc:
        check(str(exc) == 'required_calls', 'INIT/release call-set disagreement refused: %s' % exc)

print()
print('problems:', problems)
sys.exit(0 if not problems else 1)
