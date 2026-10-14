#!/usr/bin/env python3
"""Offline checker for the R17 design-r3 scoring fixtures.

  python3 -I -S -B check.py                       # build from cases.src.json, verify cases.json, run all
  python3 -I -S -B check.py --write               # (re)write cases.json from cases.src.json, then run
  python3 -I -S -B check.py --emit-packets DIR    # write the blind adjudicator packets (gold cases only)
  python3 -I -S -B check.py --adjudications DIR   # P5 gate: DIR/A1/<case>.json and DIR/A2/<case>.json

Exit 0 only if every expectation holds (and, with --adjudications, only if both designated
adjudicators reproduce every gold mapping exactly). Scorer checks and adjudicator checks are
counted separately. Stdlib only; loads r17score.py and r17recon.py by path (no sys.path use).
"""
import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parents[2]


def _load_module(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f'{name}.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


S = _load_module('r17score')
L = _load_module('r17recon')


# ---------------------------------------------------------------- build

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
            clause=[resolve(source, q, sid) for q in r['clause']],
            excluded=[dict(quote=resolve(source, e['quote'], sid), reason=e['reason'], note=e['note'])
                      for e in r.get('excluded', [])],
            logic=build_logic(source, r['logic'], f"{sid}/{r['rid']}"),
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
    return dict(units=[dict(id=u['id'], assertion=u['assertion'], evidence=ev(u['x'])) for u in src['units']],
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


def _resolve_values(value, source, where):
    if isinstance(value, dict) and set(value) == {'$q'}:
        return resolve(source, value['$q'], where)
    if isinstance(value, dict):
        return {k: _resolve_values(v, source, where) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_values(v, source, where) for v in value]
    return value


def apply_patch(ref, source, patch, where):
    for op in patch:
        *head, last = op['path']
        cur = ref
        for p in head:
            cur = cur[p]
        if 'set' in op:
            cur[last] = _resolve_values(op['set'], source, where)
        else:
            cur[last].append(_resolve_values(op['append'], source, where))
    return ref


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
        # Packets never carry the descriptive case id: the packet id and the reference source_id
        # are opaque, so the id cannot hint at the expected answer.
        pid = packet_id(c['id'])
        common = dict(id=c['id'], purpose=c['purpose'], arm=c['arm'], gold=c['gold'],
                      mappings=build_mapping(c['mapping']), expected=c['expected'])
        if 'external' in c:
            # A real frozen expanded record (fictional source) elsewhere in BENCH, pinned by hash.
            ext = c['external']
            source = pinned(ext['source'], ext['source_sha256']).decode('utf-8')
            output = json.loads(pinned(ext['output'], ext['output_sha256']).decode('utf-8'))
            cases.append(dict(common, external=ext, source=source, output=output,
                              reference=build_reference(source, c['reference'], pid)))
            continue
        cases.append(dict(common, source=c['source'],
                          reference=build_reference(c['source'], deref(c, 'reference'), pid),
                          output=build_output(c['source'], deref(c, 'output'), c['id'])))
    built = {c['id']: c for c in cases}
    invalid = []
    for v in src['reference_invalid']:
        base = built[v['base'][1:]]
        ref = apply_patch(copy.deepcopy(base['reference']), base['source'], v['patch'], v['id'])
        invalid.append(dict(id=v['id'], purpose=v['purpose'], source=base['source'], reference=ref,
                            expected_error=v['expected_error']))
    examples = [dict(id=x['id'], purpose=x['purpose'], source=x['source'], expected=x['expected'],
                     reference=build_reference(x['source'], x['reference'], x['id']))
                for x in src['reference_examples']]
    for c in cases:
        c['packet'] = packet_hashes(c)
    return dict(fixture_version=src['fixture_version'], note=src['note'], cases=cases,
                reference_invalid=invalid, reference_examples=examples, decisions=src['decisions'],
                ledger=src['ledger'], assembly=src['assembly'])


def packet_id(case_id):
    return 'fx-' + hashlib.sha256(case_id.encode('utf-8')).hexdigest()[:10]


def packet_hashes(case):
    """Bindings an adjudicator must echo (ADJUDICATION-SPEC A4): canonical-JSON hashes."""
    return dict(packet_id=packet_id(case['id']),
                output_sha256=S.sha_bytes(S.canonical_bytes(case['output'])),
                reference_sha256=S.sha_bytes(S.canonical_bytes(case['reference'])),
                source_id=case['reference']['source_id'])


# ---------------------------------------------------------------- scorer checks

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
    if set(got['relations']) != set(exp['relations']):
        fails.append(f"{label} {case['id']}: relation ids {sorted(got['relations'])} != expected")
    for rid, v in exp['relations'].items():
        if got['relations'].get(rid, {}).get('verdict') != v:
            fails.append(f"{label} {case['id']} {rid}: expected {v}, got {got['relations'].get(rid, {}).get('verdict')}")
    for rid, v in exp.get('calibration', {}).items():
        if got['relations'][rid].get('calibration') != v:
            fails.append(f"{label} {case['id']} {rid} calibration: expected {v}, got {got['relations'][rid].get('calibration')}")
    if case['arm'] == 'FULL':
        gc = {cid: c['verdict'] for cid, c in got['compounds'].items()}
        if gc != exp.get('compounds'):
            fails.append(f"{label} {case['id']} compounds: expected {exp.get('compounds')}, got {gc}")
        gi = [e['node'] for e in got['invented']]
        if gi != exp.get('invented'):
            fails.append(f"{label} {case['id']} invented: expected {exp.get('invented')}, got {gi}")
    return fails


def gold_checks(data):
    """Feasibility of the blind gate (R2-B4): gold units carry assertion and evidence, every
    mapped unit obeys M2 mechanically, and identical packets have one gold mapping."""
    fails, seen = [], {}
    for c in data['cases']:
        if not c['gold']:
            continue
        units = c['output']['units']
        if any(not isinstance(u.get('assertion'), str) or not u['assertion'].strip() or not u.get('evidence')
               for u in units):
            fails.append(f"gold {c['id']}: every unit needs a non-empty assertion and evidence")
            continue
        ev = {u['id']: S.cps(c['source'], [S._range(e) for e in u['evidence']]) for u in units}
        ref = c['reference']
        touch = {t['tid']: S.cps(c['source'], [S.rng(t['quote'])]) for t in ref['targets']}
        for r in ref['relations']:
            touch[r['tid']] |= S.qcps(c['source'], r['clause'])
        for m in c['mappings']:
            for u in m['units']:
                if not ev[u['unit']] & touch[m['tid']]:
                    fails.append(f"gold {c['id']}: unit {u['unit']} mapped to {m['tid']} violates M2")
        ref_key = copy.deepcopy(ref)
        ref_key.pop('source_id')
        key = S.sha_bytes(S.canonical_bytes([c['source'], ref_key, c['output']]))
        norm = S.normalized_mapping(c['mappings'])
        if key in seen and seen[key][1] != norm:
            fails.append(f"gold {c['id']}: same packet as {seen[key][0]} but a different gold mapping")
        seen.setdefault(key, (c['id'], norm))
    return fails


def run_decisions(data):
    n, fails = 0, []
    for d in data['decisions']:
        n += 1
        if d.get('bar') == 'D':
            got = S.bar_D(cells(d['cells']))[0]
        elif d.get('bar') == 'T':
            got = S.bar_T(cells(d['full']), cells(d['opq']), typed(d['typed']))
        elif 'futility' in d:
            unrun = {sid: [dict(key=f'{sid}:{i}', critical=c) for i, c in enumerate(v)]
                     for sid, v in d['unrun'].items()}
            got = S.futile(d['futility'], cells(d['observed']), unrun,
                           opq_cells=cells(d['opq']) if 'opq' in d else None,
                           typed_observed=typed(d.get('typed_observed', [])),
                           unrun_compounds=d.get('unrun_compounds', 0))
        elif 'kappa' in d:
            got = S.kappa([tuple(p) for p in d['kappa']])
        elif 'sensitivity' in d:
            cs = cells(d['sensitivity']['cells'])
            got = dict(primary=S.bar_D(cs)[0]['pass'],
                       dropped=S.bar_D(S.drop_relations(cs, d['sensitivity']['drop']))[0]['pass'])
        else:
            for state, want in d['outcomes']:
                try:
                    have = S.outcome(state)
                except S.SpecError:
                    have = 'error'
                if have != want:
                    fails.append(f"{d['id']}: {state} expected {want}, got {have}")
            continue
        if got != d['expected']:
            fails.append(f"{d['id']}: expected {d['expected']}, got {got}")
    return n, fails


# ---------------------------------------------------------------- ledger semantics (r17recon)

CALLS6 = [f'S{i}-OPQ' for i in (1, 2, 3)] + [f'S{i}-FULL' for i in (1, 2, 3)]


def ledger_entries(spec, key_limit):
    out = []
    for e in spec:
        if e == 'INIT':
            out.append(dict(type='INIT', required_calls=CALLS6, key_limit=key_limit))
        elif e == 'BIND_RELEASE':
            out.append(dict(type='BIND_RELEASE'))
        elif e[0] == 'RESOLVE':
            out.append(dict(type='RESOLVE', call=e[1], debit=e[2], dispatched=e[3]))
        else:
            out.append(dict(type=e[0], call=e[1]))
    return out


def run_ledger(data):
    n, fails = 0, []
    for c in data['ledger']['cases']:
        n += 1
        k = c['kind']
        if k == 'sequence':
            entries, usage, got = ledger_entries(['INIT', 'BIND_RELEASE'], c['key_limit']), 0, []
            for call in CALLS6:
                ok, _ = L.admit(entries, call, usage)
                got.append(ok)
                if not ok:
                    break
                usage += c['actual_cost']
                entries += [dict(type='RESERVE', call=call), dict(type='DISPATCH_MARK', call=call),
                            dict(type='RESOLVE', call=call, debit=L.FLOOR, dispatched=True),
                            dict(type='RECONCILED', call=call)]
            if L.aggregate(entries) != 6 * L.FLOOR:
                fails.append(f"{c['id']}: aggregate {L.aggregate(entries)}")
        elif k == 'admit':
            limit = c.get('key_limit', L.KEY_MAX)
            got = list(L.admit(ledger_entries(c['entries'], limit), c['call'], c['usage']))
            if 'key_limit' in c and L.key_limit_ok(limit, 6):
                fails.append(f"{c['id']}: key_limit_ok should be false")
        elif k == 'reconcile':
            reads = [(r[0], None if r[1] is None else dict(
                usage=r[1], limit=r[2] if len(r) > 2 else L.KEY_MAX, limit_reset=r[3] if len(r) > 3 else None))
                for r in c['reads']]
            got = list(L.reconcile(c['i'], c['C'], c['prev'], dict(limit=L.KEY_MAX, limit_reset=None), reads))
        elif k == 'close':
            entries = [dict(type='RESOLVE', call=f'x{i}', debit=d, dispatched=True) for i, d in enumerate(c['debits'])]
            got = [L.close_debit(entries, h) for h in c['highest']]
        elif k == 'parse':
            got = []
            for t in c['tokens']:
                try:
                    got.append(L.parse_usd(t))
                except L.LedgerError:
                    got.append('error')
        elif k == 'keylimit':
            got = [L.key_limit_ok(lim, req) for lim, req, _ in c['checks']]
            c = dict(c, expected=[want for _, _, want in c['checks']])
        else:
            fails.append(f"{c['id']}: unknown kind")
            continue
        if got != c['expected']:
            fails.append(f"{c['id']}: expected {c['expected']}, got {got}")
    return n, fails


# ---------------------------------------------------------------- decide() assembly

def adjudication(case, call_id, role, source_id, out_sha, ref_sha, session):
    return dict(spec_version=S.ADJ_VERSION,
                adjudicator=dict(role=role, model=S.ADJUDICATORS[role], effort=S.ADJ_EFFORT, session=session),
                call_id=call_id, source_id=source_id, output_sha256=out_sha, reference_sha256=ref_sha,
                mappings=case['mappings'], notes=dict(mapping_doubts=[], reference_defects=[], other=[]))


def assembly_inputs(data):
    a, by_id = data['assembly'], {c['id']: c for c in data['cases']}
    files, manifest, calls = {}, dict(spec_version=S.MANIFEST_VERSION, typed_testable=True,
                                      adjudicators={r: dict(model=m, effort=S.ADJ_EFFORT)
                                                    for r, m in S.ADJUDICATORS.items()},
                                      sources={}), {}
    for slot, spec in sorted(a['slots'].items()):
        opq = by_id[spec['OPQ']]
        ref = dict(copy.deepcopy(opq['reference']), source_id=spec['source_id'])
        files[f'{slot}.src.txt'] = opq['source'].encode('utf-8')
        files[f'{slot}.ref.json'] = S.canonical_bytes(ref)
        manifest['sources'][slot] = dict(
            source_id=spec['source_id'], source_file=f'{slot}.src.txt', source_sha256=S.sha_bytes(files[f'{slot}.src.txt']),
            reference_file=f'{slot}.ref.json', reference_sha256=S.sha_bytes(files[f'{slot}.ref.json']),
            relations={r['rid']: r['critical'] for r in ref['relations'] if S.live(r)},
            compounds={c['cid']: c['critical'] for c in S.compounds(ref)})
        for arm in S.ARMS:
            case = by_id[spec[arm]]
            assert case['source'] == opq['source']
            cid, name = f'{slot}-{arm}', f'{slot}-{arm}.out.json'
            files[name] = S.canonical_bytes(case['output'])
            calls[cid] = dict(call_id=cid, state=13, completion_tokens=a['tokens'][arm], output_file=name,
                              output_sha256=S.sha_bytes(files[name]), halt=None)
            for role in S.ADJUDICATORS:
                files[f'{cid}.{role}.json'] = S.canonical_bytes(adjudication(
                    case, cid, role, spec['source_id'], S.sha_bytes(files[name]),
                    manifest['sources'][slot]['reference_sha256'], f'fixture-{role}-{cid}'))
    return manifest, calls, files


def _set_output(data, files, calls, cid, case_id):
    """Replace one cell's output with another fixture case's output (same source) and rebind
    its adjudications, as an honest run would."""
    case = next(c for c in data['cases'] if c['id'] == case_id)
    files[f'{cid}.out.json'] = S.canonical_bytes(case['output'])
    calls[cid]['output_sha256'] = S.sha_bytes(files[f'{cid}.out.json'])
    for role in S.ADJUDICATORS:
        adj = json.loads(files[f'{cid}.{role}.json'])
        adj.update(output_sha256=calls[cid]['output_sha256'], mappings=case['mappings'])
        files[f'{cid}.{role}.json'] = S.canonical_bytes(adj)


def _skip(calls, files, *cids):
    for cid in cids:
        calls[cid] = dict(call_id=cid, state='skipped', completion_tokens=None, output_file=None,
                          output_sha256=None, halt=None)
        for role in S.ADJUDICATORS:
            files.pop(f'{cid}.{role}.json', None)
        files.pop(f'{cid}.out.json', None)


def mutate(kind, data, manifest, calls, files):
    interim = False
    if kind == 'swap_output':
        files['S1-OPQ.out.json'], files['S2-OPQ.out.json'] = files['S2-OPQ.out.json'], files['S1-OPQ.out.json']
    elif kind == 'wrong_reference_hash':
        adj = json.loads(files['S2-OPQ.A1.json'])
        adj['reference_sha256'] = '0' * 64
        files['S2-OPQ.A1.json'] = S.canonical_bytes(adj)
    elif kind == 'omit_relation':
        manifest['sources']['S3']['relations'] = {}
    elif kind == 'drop_a2':
        del files['S3-FULL.A2.json']
    elif kind == 'wrong_model':
        adj = json.loads(files['S1-OPQ.A2.json'])
        adj['adjudicator']['model'] = S.ADJUDICATORS['A1']
        files['S1-OPQ.A2.json'] = S.canonical_bytes(adj)
    elif kind == 'negative_tokens':
        calls['S2-FULL']['completion_tokens'] = -5
    elif kind == 'pending_final':
        _skip(calls, files, 'S3-FULL')
        calls['S3-FULL']['state'] = 'pending'
    elif kind == 'interim_after_opq1':
        _skip(calls, files, 'S2-OPQ', 'S3-OPQ', 'S1-FULL', 'S2-FULL', 'S3-FULL')
        for cid in ('S2-OPQ', 'S3-OPQ', 'S1-FULL', 'S2-FULL', 'S3-FULL'):
            calls[cid]['state'] = 'pending'
        interim = True
    elif kind == 'early_opq_stop':
        _set_output(data, files, calls, 'S1-OPQ', 'F15f-opq-inversion')
        _skip(calls, files, 'S2-OPQ', 'S3-OPQ', 'S1-FULL', 'S2-FULL', 'S3-FULL')
    elif kind == 'recon_halt_opq2':
        calls['S2-OPQ']['halt'] = 'KEY_USAGE_UNRECONCILED'
        for role in S.ADJUDICATORS:
            del files[f'S2-OPQ.{role}.json']
        _skip(calls, files, 'S3-OPQ', 'S1-FULL', 'S2-FULL', 'S3-FULL')
    elif kind == 'recon_halt_full2':
        calls['S2-FULL']['halt'] = 'KEY_USAGE_UNRECONCILED'
        for role in S.ADJUDICATORS:
            del files[f'S2-FULL.{role}.json']
        _skip(calls, files, 'S3-FULL')
    elif kind == 'early_full_stop':
        _set_output(data, files, calls, 'S1-FULL', 'F15e-false-not-under-and')
        _skip(calls, files, 'S2-FULL', 'S3-FULL')
    return interim


def run_assembly(data):
    n, fails = 0, []
    for run in data['assembly']['runs']:
        n += 1
        manifest, calls, files = assembly_inputs(data)
        interim = mutate(run.get('mutate'), data, manifest, calls, files)
        try:
            report = S.decide(manifest, calls, files, interim=interim)
        except S.SpecError as exc:
            if 'expected_error' not in run or run['expected_error'] not in str(exc):
                fails.append(f"{run['id']}: unexpected rejection: {exc}")
            continue
        if 'expected_error' in run:
            fails.append(f"{run['id']}: accepted, expected rejection {run['expected_error']!r}")
        elif report['outcome'] != run['expected_outcome']:
            fails.append(f"{run['id']}: outcome {report['outcome']} != {run['expected_outcome']}")
    return n, fails


# ---------------------------------------------------------------- adjudicator gate (C4)

def adjudicator_gate(data, adjs):
    """adjs: {dir_name: {case_id: parsed adjudication}}. Requires exactly A1 and A2, each with
    exactly the gold cases, correct identity, echoed bindings, one fresh session per case,
    and the exact gold mapping (target/unit/form only). Returns (checks, failures)."""
    gold = {c['packet']['packet_id']: c for c in data['cases'] if c['gold']}
    fails, n = [], 0
    if set(adjs) != set(S.ADJUDICATORS):
        return 1, [f'adjudicator directories must be exactly {sorted(S.ADJUDICATORS)}, got {sorted(adjs)}']
    sessions = {}
    for role in sorted(S.ADJUDICATORS):
        files = adjs[role]
        if set(files) != set(gold):
            missing, extra = sorted(set(gold) - set(files)), sorted(set(files) - set(gold))
            fails.append(f'{role}: case set differs (missing {missing}, extra {extra})')
        for cid in sorted(set(files) & set(gold)):
            n += 1
            adj, case = files[cid], gold[cid]
            who = adj.get('adjudicator', {}) if isinstance(adj, dict) else {}
            if adj.get('spec_version') != S.ADJ_VERSION:
                fails.append(f'{role} {cid}: spec_version')
                continue
            if (who.get('role') != role or who.get('model') != S.ADJUDICATORS[role]
                    or who.get('effort') != S.ADJ_EFFORT or not isinstance(who.get('session'), str) or not who['session']):
                fails.append(f'{role} {cid}: adjudicator identity')
            elif who['session'] in sessions:
                fails.append(f"{role} {cid}: session reused (also {sessions[who['session']]})")
            else:
                sessions[who['session']] = f'{role} {cid}'
            p = case['packet']
            if (adj.get('call_id') != cid or adj.get('source_id') != p['source_id']
                    or adj.get('output_sha256') != p['output_sha256'] or adj.get('reference_sha256') != p['reference_sha256']):
                fails.append(f'{role} {cid}: packet binding (call_id/source_id/output_sha256/reference_sha256)')
            try:
                S.validate_mapping(case['reference'], S.normalize_output(case['output']), adj.get('mappings'))
            except S.SpecError as exc:
                fails.append(f'{role} {cid}: invalid mappings: {exc}')
                continue
            have, want = S.normalized_mapping(adj['mappings']), S.normalized_mapping(case['mappings'])
            if have != want:
                fails.append(f'{role} {cid}: mapping {have} != gold {want}')
                continue
            fails += compare_case(case, adj['mappings'], role)
    return n, fails


def synthetic_adjs(data, mutate_fn=None):
    adjs = {}
    for role in sorted(S.ADJUDICATORS):
        adjs[role] = {}
        for c in data['cases']:
            if c['gold']:
                pid = c['packet']['packet_id']
                adjs[role][pid] = adjudication(c, pid, role, c['packet']['source_id'],
                                               c['packet']['output_sha256'], c['packet']['reference_sha256'],
                                               f'{role}-{pid}')
    if mutate_fn:
        mutate_fn(adjs)
    return adjs


def gate_selftest(data):
    """The gate itself must reject every incomplete or unbound submission (R2-B4)."""
    gold = [c['packet']['packet_id'] for c in data['cases'] if c['gold']]
    first, other = gold[0], gold[1]

    def m(fn):
        return lambda adjs: fn(adjs)

    def wrong_form(adjs):
        mp = adjs['A2'][first]['mappings'] = copy.deepcopy(adjs['A2'][first]['mappings'])
        mp[0]['units'] = []

    def new_basis(adjs):
        for mp in adjs['A1'][first]['mappings']:
            mp['basis'] = 'different free text'

    def setattr_(role, cid, path, value):
        def f(adjs):
            adjs[role][cid] = copy.deepcopy(adjs[role][cid])
            cur = adjs[role][cid]
            for p in path[:-1]:
                cur = cur[p]
            cur[path[-1]] = value
        return f

    scenarios = [
        ('complete A1+A2', None, True),
        ('basis text differs', new_basis, True),
        ('zero adjudicators', lambda a: a.clear(), False),
        ('only A1', lambda a: a.pop('A2'), False),
        ('extra adjudicator', lambda a: a.update(A3=dict(a['A1'])), False),
        ('missing case', lambda a: a['A2'].pop(first), False),
        ('wrong model', setattr_('A2', first, ['adjudicator', 'model'], S.ADJUDICATORS['A1']), False),
        ('reused session', setattr_('A2', other, ['adjudicator', 'session'], f'A1-{first}'), False),
        ('wrong output hash', setattr_('A1', first, ['output_sha256'], '0' * 64), False),
        ('wrong mapping', m(wrong_form), False),
    ]
    n, fails = 0, []
    for name, fn, ok in scenarios:
        n += 1
        _, gf = adjudicator_gate(data, synthetic_adjs(data, fn))
        if ok and gf:
            fails.append(f'gate self-test {name!r}: expected pass, got {gf[:2]}')
        if not ok and not gf:
            fails.append(f'gate self-test {name!r}: accepted')
    return n, fails


def part_a():
    text = (HERE.parent / 'ADJUDICATION-SPEC.md').read_text(encoding='utf-8')
    start, end = text.index('## Part A'), text.index('## Part B')
    return text[start:end].rstrip() + '\n'


def emit_packets(data, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=False)
    brief = part_a()
    for c in data['cases']:
        if not c['gold']:
            continue
        pid = c['packet']['packet_id']
        packet = dict(part_a=brief, part_a_sha256=S.sha_bytes(brief.encode('utf-8')),
                      source=c['source'], reference=c['reference'], output=c['output'], call_id=pid,
                      **{k: v for k, v in c['packet'].items() if k != 'packet_id'})
        (out / f'{pid}.json').write_bytes(S.canonical_bytes(packet) + b'\n')
    return sum(1 for c in data['cases'] if c['gold'])


def load_adjs(root):
    root = Path(root)
    adjs = {}
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        adjs[d.name] = {f.stem: json.loads(f.read_bytes().decode('utf-8')) for f in sorted(d.glob('*.json'))}
    return adjs


# ---------------------------------------------------------------- main

def run(data):
    counts, fails = {}, []
    counts['scorer_cases'] = len(data['cases'])
    for case in data['cases']:
        fails += compare_case(case, case['mappings'], 'scorer')
    gf = gold_checks(data)
    counts['gold_cases'] = sum(c['gold'] for c in data['cases'])
    fails += gf
    for v in data['reference_invalid']:
        try:
            S.validate_reference(v['reference'], v['source'])
            fails.append(f"{v['id']}: invalid reference accepted")
        except S.SpecError as exc:
            if v['expected_error'] not in str(exc):
                fails.append(f"{v['id']}: wrong error {exc}")
    counts['reference_invalid'] = len(data['reference_invalid'])
    for x in data['reference_examples']:
        try:
            S.validate_reference(x['reference'], x['source'])
            got = dict(live=sum(S.live(r) for r in x['reference']['relations']), compounds=len(S.compounds(x['reference'])))
            if got != x['expected']:
                fails.append(f"{x['id']}: expected {x['expected']}, got {got}")
        except S.SpecError as exc:
            fails.append(f"{x['id']}: canonical example rejected: {exc}")
    counts['reference_examples'] = len(data['reference_examples'])
    for name, fn in (('decisions', run_decisions), ('ledger', run_ledger), ('assembly', run_assembly),
                     ('gate_selftest', gate_selftest)):
        k, f = fn(data)
        counts[name] = k
        fails += f
    return counts, fails


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
    data = json.loads(encoded.decode('utf-8'))
    if '--emit-packets' in argv:
        k = emit_packets(data, argv[argv.index('--emit-packets') + 1])
        print(json.dumps(dict(packets=k, part_a_sha256=S.sha_bytes(part_a().encode('utf-8'))), sort_keys=True))
        return 0
    counts, fails = run(data)
    adj_counts = None
    if '--adjudications' in argv:
        k, f = adjudicator_gate(data, load_adjs(argv[argv.index('--adjudications') + 1]))
        adj_counts = dict(checked=k, failures=len(f))
        fails += f
    for f in fails:
        print('FAIL', f)
    print(json.dumps(dict(scorer_checks=counts, adjudicator_gate=adj_counts or 'not run (P5 requires --adjudications)',
                          failures=len(fails),
                          cases_json_sha256=hashlib.sha256(encoded).hexdigest(),
                          scorer_sha256=hashlib.sha256((HERE / 'r17score.py').read_bytes()).hexdigest(),
                          recon_sha256=hashlib.sha256((HERE / 'r17recon.py').read_bytes()).hexdigest()),
                     sort_keys=True))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
