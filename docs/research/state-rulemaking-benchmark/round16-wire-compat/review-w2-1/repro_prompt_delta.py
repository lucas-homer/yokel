"""Round-3 review repro: prompt delta w2 -> w2.1, its byte cost, and the truthfulness of the new sentence."""
import difflib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUND = HERE.parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


w1 = load('w1_prompt', ROUND / 'protocol/wire.py')
w2 = load('w2_prompt', ROUND / 'protocol-w2/wire.py')
w21 = load('w21_prompt', ROUND / 'protocol-w2-1/wire.py')
r15, common = w21.r15, w21.common
OLD_W2 = 'The complete source is supplied as span-table rows whose exact concatenation in ID order is the full source.'
NEW = 'The complete source is supplied as span-table rows whose exact concatenation in the supplied table array order is the full source.'
print('sentence length delta (chars):', len(NEW) - len(OLD_W2))

for profile in ('full', 'opaque'):
    a, b = w2._system_prompt(profile), w21._system_prompt(profile)
    print(f'\n[{profile}] w2 vs w2.1 prompt: identical after sentence swap? {b == a.replace(OLD_W2, NEW)}; '
          f'old-sentence count in w2={a.count(OLD_W2)}, in w2.1={b.count(OLD_W2)}; new count in w2.1={b.count(NEW)}')
    diff = [l for l in difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm='', n=0) if l.startswith(('+', '-')) and not l.startswith(('+++', '---'))]
    print('   unified diff lines:', len(diff))
    for line in diff:
        print('   ', line[:160])
    print('   encoded delta vs w2:', len(common.encode(b)) - len(common.encode(a)), ' vs w1:', len(common.encode(b)) - len(common.encode(w1._system_prompt(profile))))
    print('   other mentions of "order" in w2.1 prompt:', [l[:120] for l in b.splitlines() if 'order' in l.lower() and NEW not in l])

# Body-byte deltas on the sizing sources, both profiles
prior = (w21.BENCH / 'round14-semantic-contract/source/parsed-body.txt').read_bytes().decode()
profiles = json.loads((w21.BENCH / 'round15-condition-preservation/sizing/authored-profiles.json').read_bytes())['profiles']
u24 = next(p for p in profiles if p['id'] == 'disjoint600-u24')['source']
print('\nbody_bytes / guarded_bytes (w2 -> w2.1):')
for name, source in (('prior_source', prior), ('disjoint600-u24', u24)):
    for profile in ('full', 'opaque'):
        m2, m21 = w2.measure(source, profile), w21.measure(source, profile)
        print(f'   {name:16} {profile:7} body {m2["body_bytes"]:6} -> {m21["body_bytes"]:6} (+{m21["body_bytes"] - m2["body_bytes"]}), '
              f'guarded {m2["guarded_bytes"]} -> {m21["guarded_bytes"]} (+{m21["guarded_bytes"] - m2["guarded_bytes"]})')

# Truthfulness: in every built request, concatenating row[3] in array order reproduces the source byte-for-byte,
# and the array order is the order the model actually sees (parse the user message back).
sources = {'fixtures/source.txt': (w21.R15_ROOT / 'fixtures/source.txt').read_bytes().decode(), 'prior parsed-body': prior, 'disjoint600-u24': u24}
for path in sorted((w21.R15_ROOT / 'fixtures').glob('long_*-source.txt')):
    sources[path.name] = path.read_bytes().decode()
for p in profiles:
    sources['profile:' + p['id']] = p['source']
for c in json.loads((w21.BENCH / 'round15-condition-preservation/sizing/revised/authored-controls.json').read_bytes())['controls']:
    sources['control:' + str(c.get('id', c.get('name', '?')))] = c['source']
print('\nconcatenation claim per source (array order == source bytes; lexical-ID order == source bytes):')
bad = []
for name, source in sources.items():
    try:
        plan = w21.build(source)
    except Exception as exc:  # over-guard sources can't be built; measure the table directly
        rows = r15.span_table(source)['rows']
        note = f'(build rejected: {getattr(exc, "code", exc)}; table checked directly)'
    else:
        user = r15.strict_load(plan['body']['messages'][1]['content'])
        rows = user['span_table']['rows']
        assert rows == plan['table']['rows'] == r15.span_table(source)['rows']
        note = ''
    array_ok = ''.join(r[3] for r in rows).encode() == source.encode()
    lexical_ok = ''.join(r[3] for r in sorted(rows, key=lambda r: r[0])).encode() == source.encode()
    if not array_ok:
        bad.append(name)
    print(f'   {name:40} rows={len(rows):4} array_order_ok={array_ok} lexical_id_order_ok={lexical_ok} {note}')
print('\nsources where the array-order claim is FALSE:', bad or 'none')
