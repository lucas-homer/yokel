"""Mutation pass over design-r3.1's built fixtures: flip each expectation in turn (to a plausible
wrong value where one exists) and confirm check.py's run() reports a failure. Offline, in memory;
writes nothing. Run with python3 -I -S -B."""
import copy
import importlib.util
import json
from pathlib import Path

FX = Path(__file__).resolve().parent.parent / 'fixtures'
spec = importlib.util.spec_from_file_location('check_mut', FX / 'check.py')
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)
base = json.loads((FX / 'cases.json').read_bytes())
assert not C.run(base)[1], 'baseline must pass'


def other_verdict(v):
    return 'inversion' if v == 'correct' else 'correct'


def flips(d):
    for i, c in enumerate(d['cases']):
        for rid, v in c['expected']['relations'].items():
            yield 'relation', (i, 'relations', rid), other_verdict(v)
        for rid, v in c['expected'].get('calibration', {}).items():
            yield 'calibration', (i, 'calibration', rid), 'asserted' if v != 'asserted' else 'calibrated'
        if 'compounds' in c['expected']:
            comp = c['expected']['compounds']
            for cid, v in comp.items():
                yield 'compound', (i, 'compounds', cid), 'swap' if v == 'correct' else 'correct'
            if not comp:
                yield 'compound', (i, 'compounds', None), {'R1:N9': 'correct'}
            inv = c['expected']['invented']
            yield 'invented', (i, 'invented', None), [] if inv else ['c1']
    for i, _ in enumerate(d['reference_invalid']):
        yield 'reference_invalid', ('reference_invalid', i, 'expected_error'), 'no such error text'
    for i, x in enumerate(d['reference_examples']):
        yield 'reference_example', ('reference_examples', i, 'expected'), dict(x['expected'], live=x['expected']['live'] + 1)
    for i, x in enumerate(d['decisions']):
        if 'outcomes' in x:
            for j, (_, want) in enumerate(x['outcomes']):
                yield 'outcome', ('outcome', i, j), 'O1' if want != 'O1' else 'O2'
        else:
            yield 'decision', ('decisions', i, 'expected'), {'flipped': True}
    for i, x in enumerate(d['ledger']['cases']):
        if x['kind'] == 'keylimit':
            for j, _ in enumerate(x['checks']):
                yield 'ledger', ('keylimit', i, j), None
        else:
            exp = copy.deepcopy(x['expected'])
            if x['kind'] == 'admit':
                exp[0] = not exp[0]
            elif x['kind'] == 'reconcile':
                exp[0] = 'RECONCILED' if exp[0] == 'HALT' else 'HALT'
            else:
                exp[0] = 'error' if exp[0] != 'error' else 0
            yield 'ledger', ('ledger', i, 'expected'), exp
    for i, r in enumerate(d['assembly']['runs']):
        yield 'assembly', ('assembly', i), None


def apply(d, where, value):
    head = where[0]
    if isinstance(head, int):
        i, key, k = where
        exp = d['cases'][i]['expected']
        if k is None:
            exp[key] = value
        else:
            exp[key][k] = value
    elif head in ('reference_invalid', 'reference_examples', 'decisions'):
        d[head][where[1]][where[2]] = value
    elif head == 'outcome':
        d['decisions'][where[1]]['outcomes'][where[2]][1] = value
    elif head == 'keylimit':
        chk = d['ledger']['cases'][where[1]]['checks'][where[2]]
        chk[2] = not chk[2]
    elif head == 'ledger':
        d['ledger']['cases'][where[1]]['expected'] = value
    elif head == 'assembly':
        run = d['assembly']['runs'][where[1]]
        if 'expected_error' in run:
            run.pop('expected_error')
            run['expected_outcome'] = 'O2'
        else:
            run['expected_outcome'] = 'O2' if run['expected_outcome'] != 'O2' else 'O1'


counts, missed = {}, []
for kind, where, value in list(flips(base)):
    d = copy.deepcopy(base)
    apply(d, where, value)
    caught = bool(C.run(d)[1])
    counts[kind] = counts.get(kind, 0) + 1
    if not caught:
        missed.append((kind, where))
print(json.dumps(dict(flips=sum(counts.values()), by_kind=counts, missed=len(missed)), sort_keys=True))
for m in missed:
    print('MISSED', m)
