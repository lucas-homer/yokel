"""Round-3 review repro: try to defeat the w2.1 plan binding. Offline, read-only."""
import copy
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
OWNED = HERE.parent / 'protocol-w2-1'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


wire = load('w21_attack', OWNED / 'wire.py')
r15 = wire.r15
PROTO = wire.R15_ROOT
SOURCE = (PROTO / 'fixtures/source.txt').read_bytes().decode()
POSITIVE = json.loads((PROTO / 'fixtures/positive.json').read_bytes())
TABLE = r15.span_table(SOURCE)
RAW = r15.canonical(wire.from_compact(POSITIVE)).decode()
EXPECTED = r15.expand(copy.deepcopy(POSITIVE), SOURCE, TABLE)
V = wire.validate_response
results = {}


def outcome(fn):
    try:
        out = fn()
    except wire.WireError as exc:
        return 'WireError:' + exc.code
    except Exception as exc:  # noqa: BLE001 - we want to see the type
        return type(exc).__name__ + ':' + str(exc)[:60]
    return 'ACCEPT' if r15.canonical(out) == r15.canonical(EXPECTED) else 'ACCEPT(other)'


genuine = wire.build(SOURCE)
opaque = wire.build(SOURCE, 'opaque')
other = wire.build(SOURCE + ' ')

results['control: genuine plan'] = outcome(lambda: V(RAW, 'stop', SOURCE, TABLE, plan=genuine))
results['control: genuine plan, table=plan[table]'] = outcome(lambda: V(RAW, 'stop', SOURCE, genuine['table'], 'full', plan=genuine))
results['same source, opaque plan, caller full'] = outcome(lambda: V(RAW, 'stop', SOURCE, TABLE, 'full', plan=opaque))
results['same source, full plan, caller opaque'] = outcome(lambda: V(RAW, 'stop', SOURCE, TABLE, 'opaque', plan=genuine))
results['same source, opaque plan, caller opaque (typed content)'] = outcome(lambda: V(RAW, 'stop', SOURCE, TABLE, 'opaque', plan=opaque))

sha = genuine['request_sha256']
for label, val in [('last hex flipped', sha[:-1] + ('0' if sha[-1] != '0' else '1')), ('uppercased', sha.upper()),
                   ('bytes', sha.encode()), ('None', None), ('int 0', 0), ('other-source sha', other['request_sha256'])]:
    p = copy.deepcopy(genuine); p['request_sha256'] = val
    results['request_sha256 ' + label] = outcome(lambda p=p: V(RAW, 'stop', SOURCE, TABLE, plan=p))

for key, val in [('version', 'r16.w2'), ('version', 'r16.w2.1'), ('version', 'r15.1'), ('envelope_version', 'r16.e1'),
                 ('profile', 'opaque'), ('profile', None)]:
    p = copy.deepcopy(genuine); p[key] = val
    results[f'table genuine but {key}={val!r}'] = outcome(lambda p=p: V(RAW, 'stop', SOURCE, TABLE, plan=p))

results['plan passed positionally (6th arg)'] = outcome(lambda: V(RAW, 'stop', SOURCE, TABLE, 'full', genuine))
results['plan passed positionally in profile slot'] = outcome(lambda: V(RAW, 'stop', SOURCE, TABLE, genuine))
results['plan omitted'] = outcome(lambda: V(RAW, 'stop', SOURCE, TABLE))
results['plan=None'] = outcome(lambda: V(RAW, 'stop', SOURCE, TABLE, plan=None))
results['plan=[]'] = outcome(lambda: V(RAW, 'stop', SOURCE, TABLE, plan=[]))
results['plan="x"'] = outcome(lambda: V(RAW, 'stop', SOURCE, TABLE, plan='x'))
results['plan={}'] = outcome(lambda: V(RAW, 'stop', SOURCE, TABLE, plan={}))

p = copy.deepcopy(genuine); p.update(dispatch_authorized=True, extra={'a': 1})
results['extra-keys plan (genuine + 2 extra keys)'] = outcome(lambda: V(RAW, 'stop', SOURCE, TABLE, plan=p))

three = dict(profile='full', version=wire.VERSION, envelope_version=wire.ENVELOPE_VERSION)
results['forged 3-key'] = outcome(lambda: V(RAW, 'stop', SOURCE, TABLE, plan=three))
results['forged 3-key + table, no sha'] = outcome(lambda: V(RAW, 'stop', SOURCE, TABLE, plan=dict(three, table=TABLE)))
results['forged 3-key + sha, no table'] = outcome(lambda: V(RAW, 'stop', SOURCE, TABLE, plan=dict(three, request_sha256=sha)))
results['forged 5-key recomputed (table+sha equal to build)'] = outcome(
    lambda: V(RAW, 'stop', SOURCE, TABLE, plan=dict(three, table=TABLE, request_sha256=sha)))
results['forged 5-key with body=None'] = outcome(
    lambda: V(RAW, 'stop', SOURCE, TABLE, plan=dict(three, table=TABLE, request_sha256=sha, body=None)))

results['other-source plan, caller table genuine'] = outcome(lambda: V(RAW, 'stop', SOURCE, TABLE, plan=other))
results['other-source plan, caller table other'] = outcome(lambda: V(RAW, 'stop', SOURCE, other['table'], plan=other))
results['other-source plan, caller source+table other (response h stale)'] = outcome(
    lambda: V(RAW, 'stop', SOURCE + ' ', other['table'], plan=other))
p = copy.deepcopy(other); p['table'] = TABLE
results['other-source plan with table swapped to genuine'] = outcome(lambda p=p: V(RAW, 'stop', SOURCE, TABLE, plan=p))

stale = copy.deepcopy(TABLE); stale['rows'][0][3] += 'x'
p = copy.deepcopy(genuine); p['table'] = stale
results['stale table in both caller and plan'] = outcome(lambda p=p: V(RAW, 'stop', SOURCE, stale, plan=p))
results['stale caller table only'] = outcome(lambda: V(RAW, 'stop', SOURCE, stale, plan=genuine))
results['stale plan table only'] = outcome(lambda p=p: V(RAW, 'stop', SOURCE, TABLE, plan=p))
rev = copy.deepcopy(TABLE); rev['rows'] = rev['rows'][::-1]
results['caller table rows reversed'] = outcome(lambda: V(RAW, 'stop', SOURCE, rev, plan=genuine))
p = copy.deepcopy(genuine); p['table'] = copy.deepcopy(TABLE); p['table']['extra'] = 1
results['plan table with extra key'] = outcome(lambda p=p: V(RAW, 'stop', SOURCE, TABLE, plan=p))

circular = {}; circular['self'] = circular
for label, t in [('list', []), ('None', None), ('set in rows', {'rows': {1}}), ('int key', {1: 2}),
                 ('lone surrogate', {'rows': '\ud800'}), ('NaN', {'rows': float('nan')}), ('circular', circular),
                 ('deep nesting 70', json.loads('[' * 70 + ']' * 70) if False else {'rows': eval('[' * 70 + ']' * 70)})]:
    p = copy.deepcopy(genuine) if label != 'circular' else dict(genuine)
    p['table'] = t
    results['plan table ' + label] = outcome(lambda p=p: V(RAW, 'stop', SOURCE, TABLE, plan=p))
results['caller table None, plan genuine'] = outcome(lambda: V(RAW, 'stop', SOURCE, None, plan=genuine))
results['caller table circular, plan genuine'] = outcome(lambda: V(RAW, 'stop', SOURCE, circular, plan=genuine))

p = copy.deepcopy(genuine); p['body']['messages'][0]['content'] += 'EVIL'
results['body mutated, sha untouched (documented: body not bound)'] = outcome(lambda p=p: V(RAW, 'stop', SOURCE, TABLE, plan=p))

results['non_stop with forged 3-key plan'] = outcome(lambda: V(RAW, 'length', SOURCE, TABLE, plan=three))
results['bad profile with forged 3-key plan'] = outcome(lambda: V(RAW, 'stop', SOURCE, TABLE, 'typed', plan=three))
results['source None, genuine plan'] = outcome(lambda: V(RAW, 'stop', None, TABLE, plan=genuine))
results['source empty, 5-key forged'] = outcome(lambda: V(RAW, 'stop', '', TABLE, plan=dict(three, table=TABLE, request_sha256=sha)))
results['oversize source, 5-key forged'] = outcome(lambda: V(RAW, 'stop', 'a' * 40000, TABLE, plan=dict(three, table=TABLE, request_sha256=sha)))

# Ordering: does every binding failure happen before the response is parsed/converted/validated/expanded?
orig_strict = r15.strict_load


def guarded_strict(raw):
    if raw == RAW:
        raise AssertionError('RESPONSE PARSED')
    return orig_strict(raw)


ordering = {
    'forged 3-key': lambda: V(RAW, 'stop', SOURCE, TABLE, plan=three),
    'other-source plan': lambda: V(RAW, 'stop', SOURCE, TABLE, plan=other),
    'stale caller table': lambda: V(RAW, 'stop', SOURCE, stale, plan=genuine),
    'bad sha': lambda: V(RAW, 'stop', SOURCE, TABLE, plan=dict(genuine, request_sha256='0' * 64)),
    'bad version': lambda: V(RAW, 'stop', SOURCE, TABLE, plan=dict(genuine, version='r15.1')),
    'plan None': lambda: V(RAW, 'stop', SOURCE, TABLE, plan=None),
    'opaque plan caller full': lambda: V(RAW, 'stop', SOURCE, TABLE, plan=opaque),
    'CONTROL genuine (must reach parse)': lambda: V(RAW, 'stop', SOURCE, TABLE, plan=genuine),
}
with patch.object(r15, 'strict_load', side_effect=guarded_strict), \
     patch.object(wire, 'to_compact', side_effect=AssertionError('TO_COMPACT')), \
     patch.object(r15, 'validate', side_effect=AssertionError('VALIDATED')), \
     patch.object(r15, 'expand', side_effect=AssertionError('EXPANDED')):
    for label, fn in ordering.items():
        results['ORDER ' + label] = outcome(fn)

width = max(len(k) for k in results)
for key, value in results.items():
    print(f'{key:<{width}}  ->  {value}')
