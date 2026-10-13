"""Round-2 throwaway probes against protocol-w2/wire.py. Run: python3 -I -S -B repro_probes_w2.py (read-only, offline)."""
import copy, importlib.util, json, sys, hashlib
from pathlib import Path
HERE = Path(__file__).resolve().parent
R16 = HERE.parent

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

W1 = load('wire_w1', R16 / 'protocol/wire.py')
W2 = load('wire_w2', R16 / 'protocol-w2/wire.py')
r15, common = W2.r15, W2.common
R15 = W2.R15_ROOT
BENCH = W2.BENCH
SOURCE = (R15 / 'fixtures/source.txt').read_bytes().decode()
POS = json.loads((R15 / 'fixtures/positive.json').read_bytes())
TABLE = r15.span_table(SOURCE)
SIZING = BENCH / 'round15-condition-preservation/sizing'

def tryit(label, fn):
    try:
        out = fn()
        print(f'{label:60s} -> OK {str(out)[:100]}')
        return out
    except Exception as e:
        print(f'{label:60s} -> {type(e).__name__}: {e} {getattr(e, "details", "") or ""}'[:230])
        return e

def corpus():
    cases = [('fixtures/positive', SOURCE, POS)]
    for name, value in json.loads((R15 / 'fixtures/semantic-negatives.json').read_bytes()).items():
        cases.append(('fixtures/semantic-negative/' + name, SOURCE, value))
    for path in sorted((R15 / 'fixtures').glob('long_*-graph.json')):
        stem = path.name[:-len('-graph.json')]
        source = (R15 / 'fixtures' / (stem + '-source.txt')).read_bytes().decode('utf-8')
        cases.append(('fixtures/' + stem, source, json.loads(path.read_bytes())))
    for profile in json.loads((SIZING / 'authored-profiles.json').read_bytes())['profiles']:
        compact = copy.deepcopy(profile['wire']); compact['v'] = r15.VERSION
        compact['t'] = r15.digest(r15.span_table(profile['source']))
        cases.append(('sizing/' + profile['id'], profile['source'], compact))
    for control in json.loads((SIZING / 'revised/authored-controls.json').read_bytes())['controls']:
        cases.append(('revised-control/' + control['id'], control['source'], control['wire']))
    return cases

print('=== 1. Round-1 repros against w2')
print('--- SF-1 aliasing')
c = copy.deepcopy(POS); dl = [u for u in c['u'] if u['y'] is not None]; dl[1]['y'] = dl[0]['y']
tryit('from_compact: shared deadline dict between 2 units', lambda: W2.from_compact(c) and 'accepted')
c2 = copy.deepcopy(POS); xs = [n for n in c2['g'] if n['x']]; xs[1]['x'] = xs[0]['x']
tryit('from_compact: shared x list between 2 nodes', lambda: W2.from_compact(c2) and 'accepted')
w3 = W2.from_compact(POS); wu = [u for u in w3['u'] if u['y']]; wu[1]['y'] = wu[0]['y']
tryit('to_compact: shared y list between 2 units', lambda: W2.to_compact(w3) and 'accepted')
w4 = W2.from_compact(POS); wu = [u for u in w4['u'] if u['y']]; wu[1]['y'][0] = wu[0]['y'][0]
tryit('to_compact: shared deadline dict inside two y lists', lambda: W2.to_compact(w4) and 'accepted')
# same fragment object reused in two nodes (compact direction) and in two wire nodes
c5 = copy.deepcopy(POS); xs = [n for n in c5['g'] if n['x']]; xs[1]['x'][0] = xs[0]['x'][0]
tryit('from_compact: same fragment list object in two nodes', lambda: W2.from_compact(c5) and 'accepted')
w5 = W2.from_compact(POS); xs = [n for n in w5['g'] if n['x']]; xs[1]['x'][0] = xs[0]['x'][0]
tryit('to_compact: same fragment dict object in two nodes', lambda: W2.to_compact(w5) and 'accepted')
# input immutability after conversion
c6 = copy.deepcopy(POS); before = r15.canonical(c6); W2.from_compact(c6); print('input unchanged after from_compact:', r15.canonical(c6) == before)
print('--- SF-2 build oversize')
prof = next(p for p in json.loads((SIZING / 'authored-profiles.json').read_bytes())['profiles'] if p['id'] == 'disjoint600-u24')
plan = tryit('w2 build(disjoint600-u24) (now fits)', lambda: sorted(W2.build(prof['source'])))
tryit("w2 build('a'*40000)", lambda: W2.build('a' * 40000))
tryit("w2 measure('a'*40000) keys", lambda: sorted(W2.measure('a' * 40000)))
print('--- SF-3 plan metadata:', {k: W2.build(SOURCE)[k] for k in ('profile', 'version', 'envelope_version')})
print('--- N-1 WireError is ValueError:', issubclass(W2.WireError, ValueError))
print('--- N-5 recursion')
deep = W2.from_compact(POS); nested = []; cur = nested
for _ in range(3000): cur.append([]); cur = cur[0]
deep['u'][0]['s'] = nested
tryit('to_compact 3000-deep leaf', lambda: W2.to_compact(deep))
print('--- [null] still rejected')
w = W2.from_compact(POS); w['u'][0]['y'] = [None]
tryit('to_compact y:[null]', lambda: W2.to_compact(w))
tryit('validate_response y:[null]', lambda: W2.validate_response(r15.canonical(w).decode(), 'stop', SOURCE, TABLE))

print('\n=== 2. Regression: w1 vs w2 codec outputs across the full corpus')
n = 0; diffs = []
order_diffs = 0
for label, src, compact in corpus():
    n += 1
    e1 = W1.from_compact(compact); e2 = W2.from_compact(compact)
    if r15.canonical(e1) != r15.canonical(e2): diffs.append(('from_compact', label))
    if json.dumps(e1, ensure_ascii=False) != json.dumps(e2, ensure_ascii=False): order_diffs += 1
    b1 = W1.to_compact(e1); b2 = W2.to_compact(e2)
    if r15.canonical(b1) != r15.canonical(b2) or r15.canonical(b2) != r15.canonical(compact): diffs.append(('to_compact', label))
    tbl = r15.span_table(src)
    try:
        r15.validate(compact, src, tbl); valid = True
    except ValueError: valid = False
    if valid:
        raw = r15.canonical(e2).decode()
        x1 = W1.validate_response(raw, 'stop', src, tbl); x2 = W2.validate_response(raw, 'stop', src, tbl)
        direct = r15.expand(compact, src, tbl)
        if not (r15.canonical(x1) == r15.canonical(x2) == r15.canonical(direct)): diffs.append(('expanded', label))
        # also r15.1's own validate_response output
        r = r15.validate_response(r15.canonical(compact).decode(), 'stop', src, tbl)
        if r15.canonical(r['expanded']) != r15.canonical(x2): diffs.append(('vs r15 validate_response', label))
    else:
        try: W2.validate_response(r15.canonical(e2).decode(), 'stop', src, tbl); diffs.append(('ACCEPTED invalid', label))
        except (ValueError,) as ex2:
            try: W1.validate_response(r15.canonical(e1).decode(), 'stop', src, tbl)
            except Exception as ex1:  # w1 WireError was not a ValueError (N-1)
                if str(ex1) != str(ex2): diffs.append(('code', label, str(ex1), str(ex2)))
print(f'cases: {n}; canonical/expanded diffs w1 vs w2 vs r15.1: {diffs}; non-canonical key-order diffs: {order_diffs}/{n}')
e1 = W1.from_compact(POS); e2 = W2.from_compact(POS)
print('top-level key order w1:', list(e1), '| w2:', list(e2))
print('unit key order w1:', list(e1['u'][0]), '| w2:', list(e2['u'][0]))
print('schema() identical w1 vs w2 (full, opaque):', [common.encode(W1.schema(SOURCE, TABLE, p)) == common.encode(W2.schema(SOURCE, TABLE, p)) for p in ('full', 'opaque')])

print('\n=== 3. source_text removal')
for p in ('full', 'opaque'):
    b1 = W1.build(SOURCE, p)['body']; b2 = W2.build(SOURCE, p)['body']
    u1 = r15.strict_load(b1['messages'][1]['content']); u2 = r15.strict_load(b2['messages'][1]['content'])
    print(p, 'user keys w1:', sorted(u1), '| w2:', sorted(u2))
    print(p, 'hash fields equal:', all(u1[k] == u2[k] for k in ('source_text_sha256', 'span_table_sha256')), '| span_table equal:', r15.canonical(u1['span_table']) == r15.canonical(u2['span_table']))
    s1 = b1['response_format']['json_schema']['schema']; s2 = b2['response_format']['json_schema']['schema']
    print(p, 'schema identical:', common.encode(s1) == common.encode(s2), '| h/t enums:', s2['properties']['h']['enum'] == [r15.source_hash(SOURCE)], s2['properties']['t']['enum'] == [r15.digest(TABLE)])
    other = {k: (b1[k] == b2[k]) for k in b1 if k != 'messages'}
    print(p, 'non-message body fields equal:', other, '| key sets equal:', set(b1) == set(b2))
    p1 = b1['messages'][0]['content']; p2 = b2['messages'][0]['content']
    old = 'The complete source and span table are supplied.'
    new = 'The complete source is supplied as span-table rows whose exact concatenation in ID order is the full source.'
    print(p, 'prompt == w1 prompt with one sentence replaced:', p2 == p1.replace(old, new), '| old count in w1:', p1.count(old))
print('--- residual prompt mentions of "source" in w2 prompt:')
import re
for m in re.finditer(r'[^.]*\bsource\b[^.]*\.', W2._system_prompt('full')):
    s = m.group(0).strip()
    if 'suppl' in s or 'span' in s.lower() and 'row' in s.lower(): print('   ', repr(s[:170]))
print('--- "ID order" ambiguity: lexical vs array order of row IDs for the 108-row source')
prior = (BENCH / 'round14-semantic-contract/source/parsed-body.txt').read_bytes().decode()
ids = [r[0] for r in r15.span_table(prior)['rows']]
print('   first 12 IDs sorted lexically:', sorted(ids)[:12], '| array order equals lexical order:', ids == sorted(ids))
print('--- reconstruct guard edge sources (build + measure)')
edge = {
 'CRLF': 'a\r\nb\r\n', 'lone CR': 'a\rb\rc', 'CR then LF split?': 'a\r\n\rb', 'U+2028': 'a b', 'U+2029': 'a b',
 'NEL U+0085': 'a\x85b', 'VT/FF/FS/GS/RS': 'a\x0bb\x0cc\x1cd\x1de\x1ef', 'no final newline': 'line1\nline2',
 'trailing newlines': 'x\n\n\n', 'empty': '', 'whitespace only': ' \n\t', 'astral': '🫧\n𝔘𝔫𝔦\r\n😀',
 'combining': 'é\nñ', 'lone surrogate': 'bad\ud800', 'BOM': '﻿x\ny', 'NUL': 'a\x00b\n',
 'mixed all': 'A\r\nB\rC\nD E F\x85G\x0bH\x0cI\x1cJ\x1dK\x1eL',
}
for name, src in edge.items():
    def go(src=src):
        plan = W2.build(src)
        user = r15.strict_load(plan['body']['messages'][1]['content'])
        rows = user['span_table']['rows']
        joined = ''.join(r[3] for r in rows)
        offs_ok = all(rows[i][2] == rows[i+1][1] for i in range(len(rows)-1)) and rows[0][1] == 0 and rows[-1][2] == len(src)
        return f"rows={len(rows)} bytes_exact={joined.encode()==src.encode()} offsets_contiguous={offs_ok} h_ok={user['source_text_sha256']==r15.source_hash(src)} t_ok={user['span_table_sha256']==r15.digest(user['span_table'])}"
    tryit(f'build {name!r}', go)
print('--- guard ordering: does reconstruct run before any body is assembled?')
from unittest.mock import patch
calls = []
real_recon = r15.reconstruct; real_load = r15.strict_load; real_prompt = W2._system_prompt
with patch.object(r15, 'reconstruct', side_effect=lambda *a: (calls.append('reconstruct'), real_recon(*a))[1]), \
     patch.object(r15, 'strict_load', side_effect=lambda *a: (calls.append('strict_load(settings)'), real_load(*a))[1]), \
     patch.object(W2, '_system_prompt', side_effect=lambda *a: (calls.append('_system_prompt'), real_prompt(*a))[1]):
    W2.measure(SOURCE)
print('   call order:', calls)
with patch.object(r15, 'reconstruct', return_value=SOURCE + '!'):
    tryit('build with reconstruct returning wrong text', lambda: W2.build(SOURCE))
    tryit('measure with reconstruct returning wrong text', lambda: W2.measure(SOURCE))
# what does the guard compare? it compares reconstructed vs source; is the serialized table the same object?
with patch.object(r15, 'reconstruct', side_effect=lambda s, t: (t['rows'].__setitem__(0, [t['rows'][0][0], 0, t['rows'][0][2], t['rows'][0][3]]), real_recon(s, t))[1]):
    tryit('reconstruct mutating table harmlessly (same object serialized?)', lambda: W2.build(SOURCE)['spans'])
print('--- build with a mutated table AFTER reconstruct (schema still rechecks exact_host_table):')
real_schema = W2.schema
def bad_schema(source, table, profile='full'):
    table['rows'][0][3] += 'X'; return real_schema(source, table, profile)
with patch.object(W2, 'schema', side_effect=bad_schema):
    tryit('schema() given tampered table', lambda: W2.build(SOURCE))

print('\n=== 4. plan/profile/version binding')
plan_opq = W2.build(SOURCE, 'opaque'); raw = r15.canonical(W2.from_compact(POS)).decode()
tryit('typed response, opaque plan, plan omitted (default full)', lambda: 'ACCEPTED' if W2.validate_response(raw, 'stop', SOURCE, TABLE) else 'x')
tryit('typed response, opaque plan, plan=None explicit', lambda: 'ACCEPTED' if W2.validate_response(raw, 'stop', SOURCE, TABLE, plan=None) else 'x')
tryit('typed response, opaque plan passed, caller profile full', lambda: W2.validate_response(raw, 'stop', SOURCE, TABLE, 'full', plan=plan_opq))
tryit("typed response, opaque plan, caller passes plan['profile'] (tautology)", lambda: W2.validate_response(raw, 'stop', SOURCE, TABLE, plan_opq['profile'], plan=plan_opq))
tryit('typed response, opaque plan, positional profile omitted', lambda: W2.validate_response(raw, 'stop', SOURCE, TABLE, plan=plan_opq))
# plan from a different source: binding does not cover table/source/request hash
other_src = prof['source']; plan_other = W2.build(other_src)
tryit('plan built for a DIFFERENT source, validated against fixture source/table', lambda: 'ACCEPTED' if W2.validate_response(raw, 'stop', SOURCE, TABLE, plan=plan_other) else 'x')
print('   plan-bound fields checked:', [k for k in ('profile', 'version', 'envelope_version', 'table', 'request_sha256', 'body') if k in plan_other], '-> only the first three are compared')
# forged/minimal plan
tryit('forged minimal plan dict', lambda: 'ACCEPTED' if W2.validate_response(raw, 'stop', SOURCE, TABLE, plan=dict(profile='full', version='r16.w1', envelope_version='r16.e2')) else 'x')
tryit('plan is a list', lambda: W2.validate_response(raw, 'stop', SOURCE, TABLE, plan=[]))
tryit('plan check precedes parse? (raw not json, bad plan)', lambda: W2.validate_response('{', 'stop', SOURCE, TABLE, plan=plan_opq))
tryit('non_stop precedes plan check', lambda: W2.validate_response(raw, 'length', SOURCE, TABLE, plan=plan_opq))
tryit('bad profile string with plan', lambda: W2.validate_response(raw, 'stop', SOURCE, TABLE, 'typed', plan=plan_opq))

print('\n=== 5. measure/build body handling')
m = W2.measure(SOURCE)
print('measure keys:', sorted(m)); print('any str value of measure contains source text or prompt?', any(isinstance(v, str) and (SOURCE[:20] in v or 'Inventory' in v) for v in m.values()))
# body exists in memory before the guard fires: demonstrate by capturing common.encode's argument
seen = {}
real_encode = common.encode
with patch.object(common, 'encode', side_effect=lambda v: (seen.__setitem__('had_messages', isinstance(v, dict) and 'messages' in v) if isinstance(v, dict) and 'messages' in v else None, real_encode(v))[1]):
    tryit("build('a'*40000) with encode spy", lambda: W2.build('a' * 40000))
print('   a full body dict was assembled and encoded before refusal:', seen)
print('   refusal is on sizing dict, computed from the same raw:', 'sizing[\'under_guard\']' in open(R16 / 'protocol-w2/wire.py').read())
m30 = W2.measure('a' * 30000); exact = 'a' * (30000 + 40000 - m30['guarded_bytes'])
print('   boundary: build(exact) guarded =', W2.build(exact)['guarded_bytes'], '| measure(exact+a) =', W2.measure(exact + 'a')['guarded_bytes'])
tryit('   build(exact+a)', lambda: W2.build(exact + 'a'))
print('   _request is reachable directly (private):', callable(getattr(W2, '_request', None)))

print('\n=== 6. frozen-suite leniency: which w1->w2 behavior changes would the frozen suite notice?')
ind = (R16 / 'testing/test_independent.py').read_text()
checks = {
 'prompt sentence replaced': ('The complete source and span table are supplied' in ind, 'exact sentence pinned?'),
 'build raises on oversize (vs reports)': ('except Exception as exc' in ind and 'full_request_overflow' in ind, 'accepts either branch'),
 'plan key set grew (8 new keys)': (('set(plan)' in ind) or ('sorted(plan)' in ind), 'plan key set asserted?'),
 'WireError now ValueError': ('issubclass(WIRE.WireError, Exception)' in ind, 'asserts only Exception'),
 'validate_response gained plan kwarg': ('plan=' in ind, 'kwarg used?'),
 'new exports measure/lint_schema/REVISION/ENVELOPE_VERSION': (any(s in ind for s in ('WIRE.measure', 'WIRE.lint_schema', 'ENVELOPE_VERSION')), 'referenced?'),
 'user envelope keys': ("{'source_text', 'source_text_sha256', 'span_table', 'span_table_sha256'}" in ind, 'pinned (the one failure)'),
 'from_compact key order': ('json.dumps(' in ind and 'sort_keys=False' in ind, 'non-canonical order asserted?'),
}
for k, (v, note) in checks.items(): print(f'   {k:55s} frozen-suite coverage={v!s:5s} ({note})')

print('\n=== 7. verify.py frozen-input scope: does it pin sibling folders (so a new review folder breaks it)?')
fi = json.loads((R16 / 'protocol-w2/frozen-inputs.json').read_bytes())
print('   entries:', len(fi), '| includes review/:', any(k.startswith('round16-wire-compat/review/') for k in fi), '| check_frozen walks all of BENCH minus protocol-w2:', 'tests.BENCH.rglob' in (R16 / 'protocol-w2/verify.py').read_text())
