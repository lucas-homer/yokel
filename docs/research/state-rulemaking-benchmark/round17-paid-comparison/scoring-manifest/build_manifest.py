"""Build and validate the R17 scoring manifest (ADJUDICATION-SPEC C5, r17.manifest.v2). Offline.

Run from anywhere: python3 -I -S -B build_manifest.py
Writes MANIFEST.json, VALIDATION.txt and READY.json next to this file. Source texts are only
hashed and handed to r17score's own validate_reference/decide; nothing here inspects them.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
R17 = HERE.parent
BENCH = R17.parent
REL = R17.relative_to(BENCH).as_posix()
SCORER = R17 / 'design-r3-1/fixtures/r17score.py'
SCORER_SHA = '4834cf66eb0019df73b8a5e81bb5b51c43111fe51204b0f01d36b60ed76c163b'
SLOTS = {'S1': '26-19-039', 'S2': '26-19-041', 'S3': '26-19-106'}
ROLES = ('author', 'review', 'response', 'reply')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load_scorer():
    raw = SCORER.read_bytes()
    assert sha(raw) == SCORER_SHA, 'scorer pin'
    module = type(sys)('r17score_frozen')
    exec(compile(raw, str(SCORER), 'exec'), module.__dict__)
    return module


def thresholds(manifest):
    """Exactly r17_adapter.release_gate's threshold_table expression."""
    src = manifest['sources']
    counts = [len(src[s]['relations']) for s in ('S1', 'S2', 'S3')]
    nc = sum(len(src[s]['compounds']) for s in ('S1', 'S2', 'S3'))
    critical = [sum(src[s]['relations'].values()) for s in ('S1', 'S2', 'S3')]
    critical_compounds = sum(sum(src[s]['compounds'].values()) for s in ('S1', 'S2', 'S3'))
    return dict(N=sum(counts), n_s=counts, N_c=nc,
                D2=(9 * sum(counts) + 9) // 10, D3_correct=(3 * sum(counts) + 3) // 4,
                D3_acceptable=(9 * sum(counts) + 9) // 10,
                D2_source=[(3 * n + 3) // 4 for n in counts], T4=(9 * nc + 9) // 10,
                critical=sum(critical), critical_per_source=critical,
                critical_compounds=critical_compounds)


def main():
    S = load_scorer()
    log = []
    ref_ready = json.loads((R17 / 'reference/READY.json').read_bytes())
    e8 = json.loads((R17 / 'reference/E8-SUFFICIENCY.json').read_bytes())
    contested = json.loads((R17 / 'reference/26-19-041/CONTESTED.json').read_bytes())
    sources_ready = json.loads((R17 / 'sources-r2/READY.json').read_bytes())
    sessions = ref_ready['sessions']
    patterns = [sessions['author'], sessions['reviewer'], sessions['author_response'], sessions['reviewer_reply']]
    assert patterns == [f'r17-ref-{r}-<sid>-r1' for r in ROLES], patterns

    manifest = dict(spec_version=S.MANIFEST_VERSION, typed_testable=e8['typed_logic_testable'],
                    adjudicators={r: dict(model=m, effort=S.ADJ_EFFORT) for r, m in S.ADJUDICATORS.items()},
                    excluded_sessions=[], sources={})
    assert manifest['typed_testable'] is False
    files = {}
    for slot, sid in SLOTS.items():
        src_name = f'{REL}/sources-r2/{sid}/parsed-body.txt'
        ref_name = f'{REL}/reference/{sid}/reference.json'
        raw_src, raw_ref = (BENCH / src_name).read_bytes(), (BENCH / ref_name).read_bytes()
        files[src_name], files[ref_name] = raw_src, raw_ref
        assert sources_ready['files'][f'{sid}/parsed-body.txt']['sha256'] == sha(raw_src), f'{sid} sources freeze'
        assert ref_ready['sha256'][f'{sid}/reference.json'] == sha(raw_ref), f'{sid} reference freeze'
        ref = json.loads(raw_ref)
        assert ref['source_id'] == sid
        S.validate_reference(ref, raw_src.decode('utf-8'))
        log.append(f'validate-reference {sid}: ok (relations={len(ref["relations"])}, '
                   f'live={sum(S.live(r) for r in ref["relations"])}, compounds={len(S.compounds(ref))})')
        dropped = [r['rid'] for r in ref['relations'] if not S.live(r)]
        why = {r['rid']: ('contested' if r['contested'] else r['class']) for r in ref['relations'] if not S.live(r)}
        log.append(f'  {sid}: non-live relations excluded: {why or "none"}')
        relations = {r['rid']: r['critical'] for r in ref['relations'] if S.live(r)}
        compounds = {c['cid']: c['critical'] for c in S.compounds(ref)}
        per = e8['per_source'][sid]
        assert (len(relations), len(compounds)) == (per['live'], per['compounds']), f'{sid} vs E8'
        assert not set(dropped) & set(relations)
        manifest['sources'][slot] = dict(
            source_id=sid, source_file=src_name, source_sha256=sha(raw_src),
            reference_file=ref_name, reference_sha256=sha(raw_ref),
            relations=relations, compounds=compounds)
        manifest['excluded_sessions'] += [p.replace('<sid>', sid) for p in patterns]
    # CONTESTED.json items are proposed relations that are NOT in the reference; confirm none slipped in.
    assert contested['source_id'] == '26-19-041'
    assert all(i['kind'] == 'missing_relation' for i in contested['items'])
    log.append(f'26-19-041 CONTESTED.json: {len(contested["items"])} item(s), kind missing_relation; '
               'not present in reference.json, so no live id to drop')
    manifest['excluded_sessions'] += [f'r17-gate-{r}-b{i}' for r in ('A1', 'A2') for i in range(1, 8)]
    assert len(manifest['excluded_sessions']) == len(set(manifest['excluded_sessions'])) == 26
    manifest['thresholds'] = thresholds(manifest)
    t = manifest['thresholds']
    assert min(t['n_s']) >= 2 and t['N'] >= 12 and manifest['typed_testable'] == (t['N_c'] >= 5), 'P6_E8_counts'
    assert t['N'] == e8['pooled_live'] and t['N_c'] == e8['pooled_compounds']
    slots = [manifest['sources'][s]['source_id'] for s in ('S1', 'S2', 'S3')]
    assert slots == sorted(slots) and len(set(slots)) == 3, 'source_order'
    manifest_raw = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode('utf-8')
    (HERE / 'MANIFEST.json').write_bytes(manifest_raw)

    # Synthetic interim decision: every cell pending. decide() runs every manifest check first.
    cid_all = [f'{s}-{a}' for s in S.SLOTS for a in S.ARMS]
    calls = {c: dict(call_id=c, state='pending', output_file=None, halt=None) for c in cid_all}
    report = S.decide(json.loads(manifest_raw), calls, files, interim=True)
    assert report['outcome'] is None, report['outcome']
    log.append('decide --interim (all 6 cells pending, in-process): accepted; '
               f"outcome={report['outcome']}; state={json.dumps(report['state'], sort_keys=True)}")
    try:
        S.decide(json.loads(manifest_raw), calls, files, interim=False)
        raise AssertionError('final decide accepted pending cells')
    except S.SpecError as e:
        log.append(f'decide (final) with pending cells: rejected as expected: {e}')
    # Negative controls: each manifest check must bite.
    for label, mutate in [
        ('drop a live relation', lambda m: m['sources']['S2']['relations'].popitem()),
        ('flip a critical flag', lambda m: m['sources']['S1']['relations'].update(
            {k: not v for k, v in list(m['sources']['S1']['relations'].items())[:1]})),
        ('drop a compound', lambda m: m['sources']['S3']['compounds'].popitem()),
        ('wrong reference sha', lambda m: m['sources']['S1'].update(reference_sha256='0' * 64)),
        ('wrong adjudicator model', lambda m: m['adjudicators']['A2'].update(model='claude-sonnet-5-5')),
        ('excluded_sessions not a list', lambda m: m.update(excluded_sessions='x')),
    ]:
        m = json.loads(manifest_raw)
        mutate(m)
        try:
            S.decide(m, calls, files, interim=True)
            raise AssertionError(f'negative control accepted: {label}')
        except S.SpecError as e:
            log.append(f'negative control "{label}": rejected ({e})')
    # Cross-check the threshold table against PROTOCOL §11 published rows.
    protocol = (R17 / 'design-r3-1/PROTOCOL.md').read_text('utf-8')
    row = re.search(r'^\| %d \| (\d+) \| (\d+) \| (\d+) \|$' % t['N'], protocol, re.M)
    assert row and tuple(map(int, row.groups())) == (t['D2'], t['D3_correct'], t['D3_acceptable']), row
    log.append(f'PROTOCOL §11 row N={t["N"]}: {row.group(0)} matches D2/D3')
    return manifest_raw, log


if __name__ == '__main__':
    raw, log = main()
    print('\n'.join(log))
    print('MANIFEST.json sha256', sha(raw))
