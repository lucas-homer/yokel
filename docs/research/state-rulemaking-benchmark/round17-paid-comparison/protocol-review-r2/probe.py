"""Offline adversarial probes. Reads only design fixtures/specs, never R17 sources.
Run: python3 -I -S -B .../protocol-review-r2/probe.py
Assertions pin observed defects, not desired behavior.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DESIGN = HERE.parent / 'design-r2'
spec = importlib.util.spec_from_file_location('checker', DESIGN / 'fixtures/check.py')
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)
S = C.S
data = json.loads((DESIGN / 'fixtures/cases.json').read_bytes())

def case(prefix):
    return copy.deepcopy(next(c for c in data['cases'] if c['id'].startswith(prefix)))

def score(c):
    S.validate_reference(c['reference'], c['source'])
    return S.score(c['reference'], c['source'], c['output'], c['mappings'], c['arm'])

def show(name, value):
    print(json.dumps({'probe': name, 'observed': value}, sort_keys=True))

pins = json.loads((DESIGN / 'READY.json').read_bytes())['sha256']
assert all(hashlib.sha256((DESIGN / p).read_bytes()).hexdigest() == sha for p, sha in pins.items())
show('ready_hashes', len(pins))

# Reference partition: remove a required negator from the reference and output.
c = case('F09-')
c['reference']['relations'][0]['logic']['markers'] = []
r = score(c)
assert r['relations']['R1']['verdict'] == 'correct'
show('reference_missing_not_accepted', r['relations']['R1']['verdict'])

# A false NOT within one branch of an otherwise correctly matched AND.
c = case('F15b-')
c['output']['nodes'][1]['op'] = 'NOT'
c['output']['nodes'][1]['args'] = ['c4']
c['output']['nodes'][1]['evidence'] = []
c['output']['nodes'].append(dict(id='c4', op='L', args=[], q=0, evidence=[[22,36]]))
r = score(c)
assert r['relations']['R1']['verdict'] == 'correct'
assert r['compounds']['R1:N1']['verdict'] == 'correct' and not r['invented']
show('invented_not_inside_and', r)

# Lift the false-logic case to actual D/T bars: six such critical compounds,
# four relations per source. Five or more compounds is no protection.
cells = {}
for sid in ('S1','S2','S3'):
    cells[sid] = dict(status='valid', completion_tokens=100,
                     relations=[dict(key=f'{sid}:{i}', verdict='correct', critical=True)
                                for i in range(4)])
typed = [dict(verdict=r['compounds']['R1:N1']['verdict'], critical=True) for _ in range(6)]
t = S.bar_T(cells, cells, typed)
assert t['pass']
show('false_not_can_pass_T', t)

# Link evidence holding the whole clause can make an unrelated leaf look complete.
c = case('F01b-')
c['output']['links'][0]['evidence'] = [[38,104]]
c['output']['nodes'][0]['evidence'] = [[0,37]]
r = score(c)
assert r['relations']['R1']['verdict'] == 'correct'
show('whole_clause_link_unrelated_leaf', r['relations']['R1'])

# A faithful explicit NOT for a negative component is punished by comparing
# output polarity only to the relation class, rather than the reference logic.
c = case('F09-')
c['arm'] = 'FULL'
c['output']['nodes'][0].update(op='NOT', args=['c2'], evidence=[[34,37]])
c['output']['nodes'].append(dict(id='c2', op='L', args=[], q=0,
                                evidence=[[22,33],[38,46]]))
r = score(c)
assert r['relations']['R1']['verdict'] == 'inversion'
show('faithful_if_not_penalized', r['relations']['R1'])

# A correct witness masks an extra confidently weaker/stronger role: the
# contradiction rule checks inversion only, not harmful scope changes.
c = case('F10e-')
extra = copy.deepcopy(c['output']['links'][0])
extra['role'] = 'if'
c['output']['links'].append(extra)
r = score(c)
assert r['relations']['R1']['verdict'] == 'correct'
show('critical_extra_scope_change_masked', r['relations']['R1'])

# Fixture packets cannot determine their expected mappings.
a, b = case('F05a-'), case('F05b-')
ra, rb = copy.deepcopy(a['reference']), copy.deepcopy(b['reference'])
ra.pop('source_id'); rb.pop('source_id')
assert a['source'] == b['source'] and a['output'] == b['output'] and ra == rb
assert a['mappings'] != b['mappings']
show('same_meaning_packet_opposite_expected_forms', True)
missing = [c['id'] for c in data['cases']
           if any('assertion' not in u or 'evidence' not in u for u in c['output']['units'])]
show('cases_missing_mapping_inputs', len(missing))

# No actual adjudications exist in this directory. The gate nevertheless passes.
n, failures = C.run(data, str(HERE))
assert not failures
show('zero_adjudicator_directories_gate', {'checked': n, 'failures': len(failures)})

# Reference lacks the promised clause boundary; even nonsensical connective
# markers and orphan targets pass its current mechanical validator.
c = case('F15b-')
c['reference']['targets'].append(dict(tid='T2', gloss='',
                                     quote=c['reference']['relations'][0]['logic']['children'][0]['quotes'][0]))
assert S.validate_reference(c['reference'], c['source'])
show('orphan_target_accepted', True)

# Baseline snapshot must not advance on an unacknowledged, lagged observation.
reported = [100_000_000, 60_000_000]
snapshots = [0, 0, 160_000_000]
ad6 = [0 <= snapshots[i+1]-snapshots[i] <= reported[i]+1000 for i in range(2)]
assert ad6 == [True, False]
show('AD6_lag_then_catchup', ad6)
show('budget', dict(six_floors=6*270_000_000, six_conditional=6*263_840_000,
                   key_limit=1_730_000_000, key_floor_margin=110_000_000,
                   residual_bound=1_730_000_000+263_840_000))

old = HERE.parent / 'sources'
new = HERE.parent / 'sources-r2'
old_ready = json.loads((old / 'READY.json').read_bytes())
expected = old_ready['files']['screen.py']['sha256']
assert all(hashlib.sha256((p / 'screen.py').read_bytes()).hexdigest() == expected for p in (old,new))
show('unchanged_screen_hash', expected)
