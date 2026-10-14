import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
A = HERE.parent / 'A1-p5-batching'
spec = importlib.util.spec_from_file_location('batch_tests', A / 'test_gate_batched.py')
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)
G, C, S = T.G, T.C, T.S
for root, manifest in ((A, A / 'READY.json'), (G.FROZEN, G.FROZEN / 'READY.primary.json')):
    for rel, sha in json.loads(manifest.read_bytes())['sha256'].items():
        assert hashlib.sha256((root / rel).read_bytes()).hexdigest() == sha, rel
print('All amendment and frozen READY.primary file pins match')
count = 0
for c in T.DATA['cases']:
    if not c['gold']:
        continue
    pid = c['packet']['packet_id']
    brief = C.part_a()
    expected = dict(part_a=brief, part_a_sha256=S.sha_bytes(brief.encode()),
                    source=c['source'], reference=c['reference'], output=c['output'], call_id=pid,
                    **{k: v for k, v in c['packet'].items() if k != 'packet_id'})
    assert (G.PACKETS / (pid + '.json')).read_bytes() == S.canonical_bytes(expected) + b'\n', pid
    count += 1
assert count == 70
print('70 packets byte-identical to frozen blind emission; no added gold/expectation fields')
checks = [
    ('minority cross-role reuse', T.set_field('A2', T.first, ['adjudicator', 'session'], T.sess('A1', 7)), (), 'reused'),
    ('minority excluded reuse', T.set_field('A2', T.first, ['adjudicator', 'session'], 'excluded'), ['excluded'], 'reference author/reviewer'),
    ('null session', T.set_field('A1', T.first, ['adjudicator', 'session'], None), (), 'adjudicator identity'),
    ('numeric session', T.set_field('A1', T.first, ['adjudicator', 'session'], 123), (), 'adjudicator identity'),
]
for name, mutation, excluded, reason in checks:
    adjs = T.valid_adjs()
    mutation(adjs)
    _, fails = G.batched_gate(T.DATA, adjs, excluded)
    assert any(reason in f for f in fails), (name, fails)
    print('Rejected:', name)
