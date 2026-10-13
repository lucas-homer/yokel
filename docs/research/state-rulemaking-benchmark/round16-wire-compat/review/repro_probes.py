"""Throwaway review probes. Run: python3 -I -S -B repro_probes.py (read-only, no network)."""
import copy, importlib.util, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
PROTO = HERE.parent / 'protocol'
spec = importlib.util.spec_from_file_location('wire_rv', PROTO / 'wire.py')
wire = importlib.util.module_from_spec(spec); spec.loader.exec_module(wire)
r15, common = wire.r15, wire.common
R15 = wire.R15_ROOT
SOURCE = (R15 / 'fixtures/source.txt').read_bytes().decode()
POS = json.loads((R15 / 'fixtures/positive.json').read_bytes())
TABLE = r15.span_table(SOURCE)

def tryit(label, fn):
    try:
        out = fn()
        print(f'{label:55s} -> OK {str(out)[:90]}')
    except Exception as e:
        print(f'{label:55s} -> {type(e).__name__}: {e} {getattr(e, "details", "") or ""}'[:220])

print('=== A. y:[null] handling (item 2)')
w = wire.from_compact(POS); w['u'][0]['y'] = [None]
tryit('to_compact y:[null]', lambda: wire.to_compact(w))
tryit('validate_response y:[null]', lambda: wire.validate_response(r15.canonical(w).decode(), 'stop', SOURCE, TABLE))
w2 = wire.from_compact(POS); w2['u'][0]['y'] = None
tryit('validate_response y:null', lambda: wire.validate_response(r15.canonical(w2).decode(), 'stop', SOURCE, TABLE))

print('=== B. internal aliasing sensitivity of in-place _map')
# B1: two units sharing one deadline dict (valid as JSON; different unit ids)
c = copy.deepcopy(POS)
dl_units = [u for u in c['u'] if u['y'] is not None]
assert len(dl_units) >= 2, len(dl_units)
shared = dl_units[0]['y']; dl_units[1]['y'] = shared            # alias
tryit('from_compact: shared deadline dict between 2 units', lambda: wire.from_compact(c))
tryit('  same data via JSON round-trip (no aliasing)', lambda: wire.from_compact(json.loads(json.dumps(c))) and 'accepted')
tryit('  r15.validate on aliased compact', lambda: r15.validate(c, SOURCE, TABLE) and 'valid')
# B2: two nodes sharing one x list object
c2 = copy.deepcopy(POS)
xs = [n for n in c2['g'] if n['x']]
xs[1]['x'] = xs[0]['x']
tryit('from_compact: shared x list between 2 nodes', lambda: wire.from_compact(c2) and 'accepted')
# B3: same unit dict appearing twice (r15 would reject duplicate_unit anyway)
c3 = copy.deepcopy(POS); c3['u'].append(c3['u'][0])
tryit('from_compact: same unit object twice', lambda: wire.from_compact(c3))
# B4: decode direction, two units sharing one y list [D]
w3 = wire.from_compact(POS)
wu = [u for u in w3['u'] if u['y']]
wu[1]['y'] = wu[0]['y']
tryit('to_compact: shared y list between 2 units', lambda: wire.to_compact(w3))

print('=== C. coercion / typing probes through validate_response')
def mut(f):
    v = wire.from_compact(POS); f(v); return v
def frag(v): return next(n for n in v['g'] if n['x'])['x'][0]
cases = {
 'ho: true': lambda v: frag(v).__setitem__('ho', True),
 'ho: 1.0': lambda v: frag(v).__setitem__('ho', 1.0),
 'ho: "1"': lambda v: frag(v).__setitem__('ho', '1'),
 'ho: 10**30 (no maximum)': lambda v: frag(v).__setitem__('ho', 10**30),
 'unit i: 1.0': lambda v: v['u'][0].__setitem__('i', 1.0),
 'unit k: true': lambda v: v['u'][0].__setitem__('k', True),
 'unit q: false': lambda v: v['u'][0].__setitem__('q', False),
 'h: 64-char but wrong': lambda v: v.__setitem__('h', '0'*64),
 'v: "r15.1"': lambda v: v.__setitem__('v', 'r15.1'),
 'unit extra key': lambda v: v['u'][0].__setitem__('c', 1),
 'node extra key': lambda v: v['g'][0].__setitem__('zz', 1),
 'link extra key': lambda v: v['l'][0].__setitem__('zz', 1),
 'deadline extra key': lambda v: next(u for u in v['u'] if u['y'])['y'][0].__setitem__('d', {}),
 'deadline missing b': lambda v: next(u for u in v['u'] if u['y'])['y'][0].pop('b'),
 'y:[deadline] on k!=3 unit': lambda v: v['u'][0].update(k=1, y=[copy.deepcopy(next(u for u in v['u'] if u['y'])['y'][0])]),
 'span id cyrillic s1': lambda v: frag(v).__setitem__('a', 'ѕ' + frag(v)['a'][1:]),
 'anchor NFD vs source': lambda v: frag(v).__setitem__('h', frag(v)['h'] + '́'),
 's: whitespace only': lambda v: v['u'][0].__setitem__('s', '   '),
 'e: ["s1","s1"] dup': lambda v: v['u'][0].__setitem__('e', ['s1', 's1']),
 'u: [] (pure size)': lambda v: v.__setitem__('u', []),
 'd 17 ints (pure size) + dup unit id': lambda v: (v['u'][1].__setitem__('d', list(range(1, 18))), v['u'][1].__setitem__('i', v['u'][0]['i'])),
}
for label, f in cases.items():
    v = mut(f)
    tryit(label, lambda v=v: wire.validate_response(r15.canonical(v).decode(), 'stop', SOURCE, TABLE) and 'ACCEPTED')

print('=== D. build() oversize plan contents (item 1)')
prof = next(p for p in json.loads((wire.BENCH / 'round15-condition-preservation/sizing/authored-profiles.json').read_bytes())['profiles'] if p['id'] == 'disjoint600-u24')
plan = wire.build(prof['source'])
print('keys:', sorted(plan), 'under_guard:', plan['under_guard'], 'guarded:', plan['guarded_bytes'], 'body present+dispatchable:', 'messages' in plan['body'])
tryit('r15.build same source', lambda: r15.build(prof['source']))
print('plan records profile?', 'profile' in plan, '| records version?', 'version' in plan)

print('=== E. prompt edits (item 3)')
base = (R15 / 'stage-a.system.txt').read_bytes().decode()
full = wire._system_prompt('full'); opq = wire._system_prompt('opaque')
print('base endswith newline:', base.endswith('\n'), '| full len chars:', len(full), 'base:', len(base), 'delta chars:', len(full) - len(base))
print('serialized delta vs base+DESIGN-edits:', len(json.dumps(full, ensure_ascii=False).encode()) - len(json.dumps(wire._system_prompt.__globals__['_r15_bytes']('stage-a.system.txt').decode() if False else base, ensure_ascii=False).encode()))
import difflib
for i, (a, b) in enumerate(zip(base.split('. '), full.split('. '))):
    pass
print('--- remaining "null" mentions in edited prompt:')
for m in __import__('re').finditer(r'.{40}null.{40}', full): print('   ', repr(m.group(0)))
print('--- tail of edited prompt:'); print(repr(full[-260:]))
print('--- opaque addition:'); print(repr(opq[len(full):]))
# verify the 62-byte claim precisely
added = '\ny=[] claims non-deadline function; it never means unknown.\n'
print('added text chars:', len(added), 'serialized bytes (inside JSON string):', len(json.dumps(added)) - 2)

print('=== F. unreachable WireError after D2? (schema implies structural checks)')
# every structural check in to_compact is implied by the schema; probe a few schema-passing shapes
ok = wire.from_compact(POS)
print('schema_errors on positive wire:', common.schema_errors(ok, wire.schema(SOURCE, TABLE)))

print('=== G. WireError is not a ValueError')
print('issubclass(WireError, ValueError):', issubclass(wire.WireError, ValueError))

print('=== H. depth / recursion on direct to_compact (bypassing strict_load)')
deep = wire.from_compact(POS)
node = deep['u'][0]['s'] = 'x'
nested = []
cur = nested
for _ in range(3000):
    cur.append([]); cur = cur[0]
deep['u'][0]['s'] = nested
tryit('to_compact with 3000-deep leaf (direct call)', lambda: wire.to_compact(deep) and 'accepted')
