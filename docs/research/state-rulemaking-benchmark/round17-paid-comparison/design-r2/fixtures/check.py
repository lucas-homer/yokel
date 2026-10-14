#!/usr/bin/env python3
"""Offline checker for the R17 design-r2 scoring fixtures.

  python3 -I -S -B check.py                 # build from cases.src.json, verify cases.json, run all
  python3 -I -S -B check.py --write         # (re)write cases.json from cases.src.json, then run
  python3 -I -S -B check.py --adjudications DIR
        # DIR/<adjudicator>/<case_id>.json are adjudication files (ADJUDICATION-SPEC §3) produced
        # blind by an adjudicator on the fixture packets; each must reproduce the expected mapping
        # and therefore the expected verdicts exactly (PROTOCOL P5).

Exit 0 only if every expectation holds. Stdlib only; loads r17score.py by path (no sys.path use).
"""
import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parents[2]
_spec = importlib.util.spec_from_file_location('r17score', HERE / 'r17score.py')
S = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(S)


def resolve(source, q, where):
    text, occ = q
    starts = S.match_starts(source, text)
    if not 1 <= occ <= len(starts):
        raise SystemExit(f'{where}: {text!r} occurrence {occ} not in source ({len(starts)} matches)')
    return dict(text=text, start=starts[occ - 1], end=starts[occ - 1] + len(text), occurrence=occ)


def build_logic(source, node, where):
    out = dict(nid=node['nid'], op=node['op'])
    if node['op'] == 'PART':
        out['quotes'] = [resolve(source, q, where) for q in node['quotes']]
        out['markers'] = [resolve(source, q, where) for q in node.get('markers', [])]
    else:
        out['markers'] = [resolve(source, q, where) for q in node['markers']]
        out['children'] = [build_logic(source, c, where) for c in node['children']]
    return out


def build_reference(source, src, sid):
    targets = [dict(tid=t['tid'], quote=resolve(source, t['quote'], sid), gloss=t.get('gloss', ''))
               for t in src['targets']]
    rels = []
    for r in src['relations']:
        critical = r.get('critical', False)
        contested = r.get('contested', False)
        rels.append(dict(
            rid=r['rid'], tid=r['tid'], **{'class': r['class']},
            introducer=[resolve(source, q, sid) for q in r['introducer']],
            logic=build_logic(source, r['logic'], f"{sid}/{r['rid']}"),
            carves_out_of=r.get('carves_out_of'),
            rationale=r.get('rationale', 'fixture'),
            critical=critical,
            critical_reason=r.get('critical_reason', 'fixture: changes who must act' if critical else ''),
            contested=contested, contested_reason=r.get('contested_reason', '')))
    return dict(spec_version=S.REF_VERSION, source_id=sid,
                source_text_sha256=hashlib.sha256(source.encode('utf-8')).hexdigest(),
                targets=targets, relations=rels, out_of_scope_notes=[])


def build_output(source, src, sid):
    def ev(xs):
        return [[q['start'], q['end']] for q in (resolve(source, x, sid) for x in xs)]
    return dict(units=[dict(id=u) for u in src['units']],
                nodes=[dict(id=n['id'], op=n['op'], args=n['args'], evidence=ev(n['x']), q=n['q'])
                       for n in src['nodes']],
                links=[dict(unit_id=l['u'], role=l['w'], node_id=l['n'], evidence=ev(l['x']), q=l['q'])
                       for l in src['links']])


def build_mapping(src):
    return [dict(tid=tid, units=[dict(unit=u, form=f) for u, f in units], basis='fixture expectation')
            for tid, units in sorted(src.items())]


def pinned(rel, sha):
    raw = (BENCH / rel).read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha:
        raise SystemExit(f'pinned input changed: {rel}')
    return raw


def build(src):
    by_id = {c['id']: c for c in src['cases']}

    def deref(case, key):
        value = case[key]
        if isinstance(value, str) and value.startswith('@'):
            base = by_id[value[1:]]
            if base['source'] != case['source']:
                raise SystemExit(f"{case['id']}: {key} borrowed from a case with a different source")
            return deref(base, key)
        return value

    cases = []
    for c in src['cases']:
        if 'external' in c:
            # A real frozen expanded record (fictional source) elsewhere in BENCH, pinned by hash.
            ext = c['external']
            raw_src, raw_out = (pinned(ext['source'], ext['source_sha256']),
                                pinned(ext['output'], ext['output_sha256']))
            source, output = raw_src.decode('utf-8'), json.loads(raw_out.decode('utf-8'))
            cases.append(dict(id=c['id'], purpose=c['purpose'], arm=c['arm'], external=ext,
                              source=source, reference=build_reference(source, c['reference'], c['id']),
                              output=output, mappings=build_mapping(c['mapping']),
                              expected=c['expected']))
            continue
        cases.append(dict(id=c['id'], purpose=c['purpose'], arm=c['arm'], source=c['source'],
                          reference=build_reference(c['source'], deref(c, 'reference'), c['id']),
                          output=build_output(c['source'], deref(c, 'output'), c['id']),
                          mappings=build_mapping(c['mapping']), expected=c['expected']))
    built = {c['id']: c for c in cases}
    invalid = []
    for v in src['reference_invalid']:
        ref = copy.deepcopy(built[v['base'][1:]]['reference'])
        p = v['patch']
        rel = next(r for r in ref['relations'] if r['rid'] == p['relation'])
        if 'set_occurrence' in p:
            for n in S.logic_nodes(rel['logic']):
                for q in n.get('markers', []):
                    if q['text'] == p['quote_text'] and q['occurrence'] == p['quote_occurrence']:
                        q['occurrence'] = p['set_occurrence']
        if 'add_part_quote' in p:
            part = next(n for n in S.logic_nodes(rel['logic']) if n['op'] == 'PART')
            part['quotes'].append(resolve(v['source'], p['add_part_quote'], v['id']))
        invalid.append(dict(id=v['id'], purpose=v['purpose'], source=v['source'], reference=ref,
                            expected_error=v['expected_error']))
    return dict(fixture_version=src['fixture_version'], note=src['note'], cases=cases,
                reference_invalid=invalid, decisions=src['decisions'])


def cells(spec):
    return {sid: dict(status=c['status'], completion_tokens=c['completion_tokens'],
                      relations=[dict(key=f'{sid}:{i}', verdict=v, critical=crit)
                                 for i, (v, crit) in enumerate(c['relations'])])
            for sid, c in spec.items()}


def typed(items):
    return [dict(verdict=v, critical=c) for v, c in items]


def compare_case(case, mappings, label):
    fails = []
    S.validate_reference(case['reference'], case['source'])
    got = S.score(case['reference'], case['source'], case['output'], mappings, case['arm'])
    exp = case['expected']
    for rid, v in exp['relations'].items():
        if got['relations'][rid]['verdict'] != v:
            fails.append(f"{label} {case['id']} {rid}: expected {v}, got {got['relations'][rid]['verdict']}")
    for rid, v in exp.get('calibration', {}).items():
        if got['relations'][rid].get('calibration') != v:
            fails.append(f"{label} {case['id']} {rid} calibration: expected {v}, got {got['relations'][rid].get('calibration')}")
    if case['arm'] == 'FULL':
        gc = {cid: c['verdict'] for cid, c in got['compounds'].items()}
        if 'compounds' in exp and gc != exp['compounds']:
            fails.append(f"{label} {case['id']} compounds: expected {exp['compounds']}, got {gc}")
        gi = [e['node'] for e in got['invented']]
        if 'invented' in exp and gi != exp['invented']:
            fails.append(f"{label} {case['id']} invented: expected {exp['invented']}, got {gi}")
    return fails


def run(data, adjudications=None):
    fails, n = [], 0
    for case in data['cases']:
        n += 1
        fails += compare_case(case, case['mappings'], 'scorer')
    for v in data['reference_invalid']:
        n += 1
        try:
            S.validate_reference(v['reference'], v['source'])
            fails.append(f"{v['id']}: invalid reference accepted")
        except S.SpecError as exc:
            if v['expected_error'] not in str(exc):
                fails.append(f"{v['id']}: wrong error {exc}")
    for d in data['decisions']:
        n += 1
        if 'bar' in d and d['bar'] == 'D':
            got = S.bar_D(cells(d['cells']))[0]
        elif 'bar' in d:
            got = S.bar_T(cells(d['full']), cells(d['opq']), typed(d['typed']))
        elif 'futility' in d:
            unrun = {sid: [dict(key=f'{sid}:{i}', critical=c) for i, c in enumerate(v)]
                     for sid, v in d['unrun'].items()}
            got = S.futile(d['futility'], cells(d['observed']), unrun,
                           opq_cells=cells(d['opq']) if 'opq' in d else None,
                           typed_observed=typed(d.get('typed_observed', [])),
                           unrun_compounds=d.get('unrun_compounds', 0))
        else:
            for state, want in d['outcomes']:
                if S.outcome(state) != want:
                    fails.append(f"{d['id']}: {state} expected {want}, got {S.outcome(state)}")
            continue
        if got != d['expected']:
            fails.append(f"{d['id']}: expected {d['expected']}, got {got}")
    if adjudications:
        root = Path(adjudications)
        by_id = {c['id']: c for c in data['cases']}
        for adj_dir in sorted(p for p in root.iterdir() if p.is_dir()):
            for case_id, case in sorted(by_id.items()):
                path = adj_dir / f'{case_id}.json'
                if not path.exists():
                    fails.append(f'{adj_dir.name}: missing {case_id}')
                    continue
                adj = json.loads(path.read_bytes().decode('utf-8'))
                if adj.get('spec_version') != S.ADJ_VERSION:
                    fails.append(f'{adj_dir.name} {case_id}: spec_version')
                    continue
                want = {m['tid']: {(u['unit'], u['form']) for u in m['units']} for m in case['mappings']}
                have = {m['tid']: {(u['unit'], u['form']) for u in m['units']} for m in adj['mappings']}
                if have != want:
                    fails.append(f'{adj_dir.name} {case_id}: mapping {have} != expected {want}')
                fails += compare_case(case, adj['mappings'], adj_dir.name)
    return n, fails


def main(argv):
    src = json.loads((HERE / 'cases.src.json').read_bytes().decode('utf-8'))
    data = build(src)
    encoded = (json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + '\n').encode('utf-8')
    target = HERE / 'cases.json'
    if '--write' in argv:
        target.write_bytes(encoded)
    elif not target.exists() or target.read_bytes() != encoded:
        print('cases.json is missing or stale; run with --write', file=sys.stderr)
        return 1
    adjudications = argv[argv.index('--adjudications') + 1] if '--adjudications' in argv else None
    n, fails = run(json.loads(encoded.decode('utf-8')), adjudications)
    for f in fails:
        print('FAIL', f)
    print(json.dumps(dict(checked=n, failures=len(fails),
                          cases_json_sha256=hashlib.sha256(encoded).hexdigest(),
                          scorer_sha256=hashlib.sha256((HERE / 'r17score.py').read_bytes()).hexdigest()),
                     sort_keys=True))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
