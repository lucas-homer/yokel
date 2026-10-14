#!/usr/bin/env python3
"""Self-tests for gate_batched.py (amendment A1), mirroring check.py's gate_selftest.

  python3 -I -S -B test_gate_batched.py

Submissions are built in memory from the gold mappings in the frozen cases.json (via check.py's
own adjudication() constructor), never from or into a packet. Each rejecting scenario must fail
for its intended reason (a substring of the failure), not merely fail. Writes nothing.
"""
import copy
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('gate_batched', HERE / 'gate_batched.py')
G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G)
C, S = G.C, G.S

DATA = G.load_data()
PARTS = G.partition(DATA)
GOLD = {c['packet']['packet_id']: c for c in DATA['cases'] if c['gold']}


def sess(role, b):
    return f'{role}-batch{b}'


def valid_adjs():
    """A correct batched submission: every A1/A2 file carries the gold mapping and its batch session."""
    adjs = {}
    for role in sorted(S.ADJUDICATORS):
        adjs[role] = {}
        for b, ids in PARTS:
            for pid in ids:
                p = GOLD[pid]['packet']
                adjs[role][pid] = C.adjudication(GOLD[pid], pid, role, p['source_id'], p['output_sha256'],
                                                 p['reference_sha256'], sess(role, b))
    return adjs


def batch_ids(b):
    return dict(PARTS)[b]


def set_field(role, pid, path, value):
    def f(adjs):
        adjs[role][pid] = cur = copy.deepcopy(adjs[role][pid])
        for p in path[:-1]:
            cur = cur[p]
        cur[path[-1]] = value
    return f


def set_batch_session(role, b, value):
    def f(adjs):
        for pid in batch_ids(b):
            set_field(role, pid, ['adjudicator', 'session'], value)(adjs)
    return f


def per_packet_sessions(adjs):
    for role, files in adjs.items():
        for pid in files:
            set_field(role, pid, ['adjudicator', 'session'], f'{role}-{pid}')(adjs)


def wrong_form(adjs):
    pid = batch_ids(2)[3]
    set_field('A2', pid, ['mappings'], copy.deepcopy(adjs['A2'][pid]['mappings']))(adjs)
    adjs['A2'][pid]['mappings'][0]['units'] = []


def new_basis(adjs):
    for files in adjs.values():
        for pid in files:
            files[pid] = copy.deepcopy(files[pid])
            for mp in files[pid]['mappings']:
                mp['basis'] = 'different free text'


first, mid, last = batch_ids(1)[0], batch_ids(4)[5], PARTS[-1][1][-1]
EXCLUDED = ['ref-author-S1', 'ref-reviewer-S1']

# (name, mutation, excluded sessions, expected: None = pass, else a required failure substring)
SCENARIOS = [
    ('valid A1+A2, one session per (role, batch)', None, (), None),
    ('valid with excluded list that it avoids', None, EXCLUDED, None),
    ('basis text differs', new_basis, (), None),
    ('zero adjudicators', lambda a: a.clear(), (), 'must be exactly'),
    ('only A1 (A2 missing)', lambda a: a.pop('A2'), (), 'must be exactly'),
    ('only A2 (A1 missing)', lambda a: a.pop('A1'), (), 'must be exactly'),
    ('extra adjudicator A3', lambda a: a.update(A3=dict(a['A1'])), (), 'must be exactly'),
    ('missing packet', lambda a: a['A2'].pop(mid), (), 'case set differs'),
    ('extra non-gold file', lambda a: a['A1'].update({'fx-0000000000': a['A1'][first]}), (), 'case set differs'),
    ('session reused across batches (A1 batch 2 = A1 batch 1)',
     set_batch_session('A1', 2, sess('A1', 1)), (), 'reused (also A1 batch 1)'),
    ('session reused across roles (A2 batch 3 = A1 batch 3)',
     set_batch_session('A2', 3, sess('A1', 3)), (), 'reused (also A1 batch 3)'),
    ('session reused across roles and batches (A2 batch 7 = A1 batch 1)',
     set_batch_session('A2', 7, sess('A1', 1)), (), 'reused (also A1 batch 1)'),
    ('wrong session within a batch (fresh id)',
     set_field('A1', mid, ['adjudicator', 'session'], 'A1-stray'), (), 'does not match the batch session'),
    ('wrong session within a batch (a neighbour batch id)',
     set_field('A2', last, ['adjudicator', 'session'], sess('A2', 6)), (), 'does not match the batch session'),
    ('per-packet sessions (the unamended rule) are not batches',
     per_packet_sessions, (), 'does not match the batch session'),
    ('batch session is a reference author/reviewer session',
     set_batch_session('A2', 5, EXCLUDED[1]), EXCLUDED, 'reference author/reviewer session'),
    ('empty session', set_field('A1', first, ['adjudicator', 'session'], ''), (), 'adjudicator identity'),
    ('wrong model', set_field('A2', first, ['adjudicator', 'model'], S.ADJUDICATORS['A1']), (), 'adjudicator identity'),
    ('wrong role', set_field('A1', mid, ['adjudicator', 'role'], 'A2'), (), 'adjudicator identity'),
    ('wrong effort', set_field('A1', mid, ['adjudicator', 'effort'], 'medium'), (), 'adjudicator identity'),
    ('wrong spec version', set_field('A2', last, ['spec_version'], 'r17.adj.v1'), (), 'spec_version'),
    ('binding: wrong output hash', set_field('A1', first, ['output_sha256'], '0' * 64), (), 'packet binding'),
    ('binding: wrong reference hash', set_field('A2', mid, ['reference_sha256'], '0' * 64), (), 'packet binding'),
    ('binding: wrong call_id', set_field('A1', last, ['call_id'], first), (), 'packet binding'),
    ('binding: wrong source_id', set_field('A2', first, ['source_id'], 'src-other'), (), 'packet binding'),
    ('mapping mismatch (wrong form)', wrong_form, (), 'mapping'),
]


def partition_checks():
    fails = []
    ids = [pid for _, chunk in PARTS for pid in chunk]
    if ids != sorted(GOLD):
        fails.append('partition is not the sorted gold packet ids')
    if [b for b, _ in PARTS] != list(range(1, len(PARTS) + 1)):
        fails.append('batches are not numbered 1..n')
    if any(len(chunk) != G.BATCH_SIZE for _, chunk in PARTS[:-1]) or not 1 <= len(PARTS[-1][1]) <= G.BATCH_SIZE:
        fails.append('batch sizes are not 10,...,10,(<=10)')
    if G.BATCHES_JSON.read_bytes() != G.manifest_bytes(DATA):
        fails.append('BATCHES.json is stale')
    return fails


def main():
    fails = partition_checks()
    for name, fn, excluded, want in SCENARIOS:
        adjs = valid_adjs()
        if fn:
            fn(adjs)
        _, gf = G.batched_gate(DATA, adjs, excluded)
        if want is None and gf:
            fails.append(f'{name!r}: expected pass, got {gf[:2]}')
        elif want is not None and not any(want in f for f in gf):
            fails.append(f'{name!r}: expected a failure containing {want!r}, got {gf[:2] or "pass"}')
        print(('ok   ' if not fails or not fails[-1].startswith(repr(name)) else 'FAIL ') + name)
    print(f'{len(SCENARIOS)} scenarios + partition checks; batches={len(PARTS)} '
          f'sizes={[len(c) for _, c in PARTS]}; failures={len(fails)}')
    for f in fails:
        print('FAIL', f)
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
