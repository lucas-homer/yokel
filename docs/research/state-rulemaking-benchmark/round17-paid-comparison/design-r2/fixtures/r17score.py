#!/usr/bin/env python3
"""R17 design-r2 reference scorer: the mechanical half of ADJUDICATION-SPEC.md.

Offline, stdlib only. Run as `python3 -I -S -B r17score.py ...`.

Adjudicators supply only target mappings (which output units assert each
reference target, and in which form). Everything else here is mechanical:
quote resolution, witness enumeration, coverage, role composition, verdict
precedence, typed-logic matching, aggregates and the decision bars. A rule in
this file that disagrees with ADJUDICATION-SPEC.md is a bug in one of them;
neither silently wins.
"""
import hashlib
import json
import sys
import unicodedata

REF_VERSION = 'r17.ref.v2'
ADJ_VERSION = 'r17.adj.v1'
CLASSES = ('COND', 'RESTRICT', 'EXCEPT', 'IRRESPECTIVE', 'UNRESOLVED')
LOGIC_OPS = ('PART', 'AND', 'OR', 'NOT', 'EXC')
ROLES = ('if', 'onlyif', 'unless', 'regardless', 'obj', 'acts', 'qual')
OPS = ('L', 'R', 'AND', 'OR', 'NOT', 'EXC', 'ALT')
FORMS = ('direct', 'inverse')

# Relation verdicts, in precedence order (first applicable wins; see spec §5).
HARMFUL = ('absent', 'wrong_target', 'shortened', 'lost_connective',
           'inversion', 'role_loss', 'scope_change', 'contradiction')
ACCEPTABLE = ('correct', 'hedged', 'embedded', 'broad')
CRITICAL_MET = ('correct', 'hedged', 'broad')
TEXT_COMPLETE = ACCEPTABLE + ('inversion', 'role_loss', 'scope_change', 'contradiction')
TYPED_HARMFUL = ('swap', 'mismatch', 'exc_reversed', 'wrong_base', 'invented')

ROLE_RANK = dict(correct=0, hedged=1, embedded=2, scope_change=3, role_loss=4, inversion=5)
TEXT_RANK = dict(complete=0, lost_marker=1, partial=2, absent=3)
BROAD_FACTOR = 2          # broad iff extraneous > BROAD_FACTOR * |K|
HEADROOM_TOKENS = 13926   # D5: 85% of 16,384


class SpecError(ValueError):
    pass


def need(ok, message):
    if not ok:
        raise SpecError(message)


# ---------------------------------------------------------------- quotes

def counted(ch):
    """Codepoints that count toward coverage: not whitespace, punctuation or control."""
    cat = unicodedata.category(ch)
    return not (cat[0] in 'ZP' or cat == 'Cc')


def cps(source, ranges):
    return {i for start, end in ranges for i in range(start, end) if counted(source[i])}


def match_starts(source, text):
    """All (overlapping) exact match starts, ascending."""
    starts, i = [], source.find(text)
    while i != -1:
        starts.append(i)
        i = source.find(text, i + 1)
    return starts


def check_quote(source, q, where):
    need(isinstance(q, dict) and set(q) == {'text', 'start', 'end', 'occurrence'},
         f'{where}: quote keys must be text,start,end,occurrence')
    text, start, end, occ = q['text'], q['start'], q['end'], q['occurrence']
    need(isinstance(text, str) and text.strip() != '', f'{where}: blank quote')
    need(all(type(v) is int for v in (start, end, occ)), f'{where}: non-integer offset')
    need(0 <= start < end <= len(source), f'{where}: offsets out of range')
    need(source[start:end] == text, f'{where}: source[start:end] != text')
    starts = match_starts(source, text)
    need(occ >= 1 and occ <= len(starts) and starts[occ - 1] == start,
         f'{where}: occurrence {occ} does not resolve to start {start}')
    return (start, end)


# ---------------------------------------------------------------- reference

def logic_nodes(node):
    yield node
    for child in node.get('children', []):
        yield from logic_nodes(child)


def logic_quotes(node, kind):
    """kind 'parts' -> PART quotes; 'markers' -> markers at every level."""
    out = []
    for n in logic_nodes(node):
        if kind == 'parts' and n['op'] == 'PART':
            out.extend(n['quotes'])
        if kind == 'markers':
            out.extend(n.get('markers', []))
    return out


def validate_reference(ref, source):
    need(isinstance(ref, dict), 'reference must be an object')
    need(set(ref) == {'spec_version', 'source_id', 'source_text_sha256', 'targets',
                      'relations', 'out_of_scope_notes'}, 'reference top-level keys')
    need(ref['spec_version'] == REF_VERSION, 'reference spec_version')
    need(ref['source_text_sha256'] == hashlib.sha256(source.encode('utf-8')).hexdigest(),
         'source_text_sha256 mismatch')
    tids, spans = set(), set()
    for t in ref['targets']:
        need(set(t) == {'tid', 'quote', 'gloss'}, 'target keys')
        need(isinstance(t['tid'], str) and t['tid'].startswith('T') and t['tid'] not in tids,
             f"target id {t['tid']!r}")
        tids.add(t['tid'])
        span = check_quote(source, t['quote'], t['tid'])
        need(span not in spans, f"{t['tid']}: duplicate target span")
        spans.add(span)
        need(isinstance(t['gloss'], str), 'gloss must be a string')
    rids = {}
    for r in ref['relations']:
        need(set(r) == {'rid', 'tid', 'class', 'introducer', 'logic', 'carves_out_of', 'rationale',
                        'critical', 'critical_reason', 'contested', 'contested_reason'},
             'relation keys')
        need(isinstance(r['rationale'], str) and r['rationale'].strip(), f"{r['rid']}: rationale")
        rid = r['rid']
        need(isinstance(rid, str) and rid.startswith('R') and rid not in rids, f'relation id {rid!r}')
        rids[rid] = r
        need(r['tid'] in tids, f'{rid}: unknown tid')
        need(r['class'] in CLASSES, f'{rid}: class')
        need(isinstance(r['introducer'], list) and len(r['introducer']) <= 3, f'{rid}: introducer list')
        nids = set()
        for n in logic_nodes(r['logic']):
            need(isinstance(n, dict) and n.get('op') in LOGIC_OPS, f'{rid}: logic op')
            need(n.get('nid') not in nids and isinstance(n.get('nid'), str), f'{rid}: logic nid')
            nids.add(n['nid'])
            if n['op'] == 'PART':
                need(set(n) == {'nid', 'op', 'quotes', 'markers'} and n['quotes'], f'{rid}: PART shape')
            else:
                need(set(n) == {'nid', 'op', 'markers', 'children'} and n['markers'], f'{rid}: operator shape')
                need(len(n['children']) == {'NOT': 1, 'EXC': 2}.get(n['op'], len(n['children']))
                     and len(n['children']) >= (1 if n['op'] == 'NOT' else 2), f'{rid}: operator arity')
        ranges = []
        for i, q in enumerate(r['introducer'] + logic_quotes(r['logic'], 'parts')
                              + logic_quotes(r['logic'], 'markers')):
            ranges.append(check_quote(source, q, f'{rid} quote {i}'))
        ranges.sort()
        need(all(a[1] <= b[0] for a, b in zip(ranges, ranges[1:])), f'{rid}: overlapping quotes')
        need(rel_K(source, r)['parts'], f'{rid}: PART quotes contain no counted characters')
        need(type(r['critical']) is bool and type(r['contested']) is bool, f'{rid}: flags')
        need(bool(r['critical_reason'].strip()) == r['critical'], f'{rid}: critical_reason iff critical')
        need(bool(r['contested_reason'].strip()) == r['contested'], f'{rid}: contested_reason iff contested')
    for r in ref['relations']:
        h = r['carves_out_of']
        if h is not None:
            need(r['class'] == 'EXCEPT', f"{r['rid']}: carves_out_of needs EXCEPT")
            need(h in rids and h != r['rid'] and rids[h]['tid'] == r['tid'],
                 f"{r['rid']}: carves_out_of must name another relation of the same target")
    need(isinstance(ref['out_of_scope_notes'], list), 'out_of_scope_notes')
    return True


def rel_K(source, r):
    intro = [(q['start'], q['end']) for q in r['introducer']]
    parts = [(q['start'], q['end']) for q in logic_quotes(r['logic'], 'parts')]
    marks = [(q['start'], q['end']) for q in logic_quotes(r['logic'], 'markers')]
    p, m = cps(source, parts), cps(source, intro + marks)
    return dict(parts=p, markers=m, all=p | m)


def node_K(source, node):
    ranges = [(q['start'], q['end']) for q in logic_quotes(node, 'parts') + logic_quotes(node, 'markers')]
    return cps(source, ranges)


def compounds(ref):
    """Scored compound items: AND/OR/EXC logic nodes, plus exception_to links (kind XTO)."""
    out = []
    for r in ref['relations']:
        if r['contested'] or r['class'] == 'UNRESOLVED':
            continue
        for n in logic_nodes(r['logic']):
            if n['op'] in ('AND', 'OR', 'EXC'):
                out.append(dict(cid=f"{r['rid']}:{n['nid']}", rid=r['rid'], kind=n['op'], node=n,
                                critical=r['critical']))
        if r['carves_out_of']:
            out.append(dict(cid=f"{r['rid']}:exc", rid=r['rid'], kind='XTO', node=None,
                            critical=r['critical']))
    return out


# ---------------------------------------------------------------- output

def _range(ev):
    if isinstance(ev, dict):
        return (ev['start'], ev['end'])
    need(isinstance(ev, list) and len(ev) == 2, 'evidence item')
    return (ev[0], ev[1])


def normalize_output(out):
    """Accept the fixture form or an r16 expanded record (validate_response result)."""
    units = [dict(id=u['id']) for u in out['units']]
    nodes = [dict(id=n['id'], op=n['op'], args=list(n['args']), q=n['q'],
                  evidence=[_range(e) for e in n['evidence']]) for n in out['nodes']]
    links = [dict(unit_id=l['unit_id'], role=l['role'], node_id=l['node_id'], q=l['q'],
                  evidence=[_range(e) for e in l['evidence']]) for l in out['links']]
    ids = {n['id'] for n in nodes}
    need(len(ids) == len(nodes), 'duplicate node id')
    for n in nodes:
        need(n['op'] in OPS and all(a in ids for a in n['args']), f"node {n['id']}")
    uids = {u['id'] for u in units}
    for l in links:
        need(l['role'] in ROLES and l['node_id'] in ids and l['unit_id'] in uids, 'link shape')
    return dict(units=units, nodes={n['id']: n for n in nodes}, links=links)


class Witness:
    __slots__ = ('li', 'link', 'path', 'flips', 'alt', 'cov', 'path_uncertain')

    def __init__(self, li, link, path, flips, alt):
        self.li, self.link, self.path, self.flips, self.alt = li, link, tuple(path), flips, alt

    @property
    def node(self):
        return self.path[-1]

    @property
    def unit(self):
        return self.link['unit_id']


def subtree(nodes, nid):
    seen, stack = [], [nid]
    while stack:
        cur = stack.pop()
        if cur not in seen:
            seen.append(cur)
            stack.extend(reversed(nodes[cur]['args']))
    return seen


def subtree_cov(source, nodes, nid, cache):
    if nid not in cache:
        cache[nid] = cps(source, [r for m in subtree(nodes, nid) for r in nodes[m]['evidence']])
    return cache[nid]


def witnesses(source, out):
    nodes, res, cache = out['nodes'], [], {}

    def walk(li, link, path, flips, alt):
        w = Witness(li, link, path, flips, alt)
        anc = [r for a in path[:-1] for r in nodes[a]['evidence']]
        w.cov = cps(source, link['evidence'] + anc) | subtree_cov(source, nodes, path[-1], cache)
        w.path_uncertain = link['q'] != 0 or alt or any(nodes[p]['q'] != 0 for p in path)
        res.append(w)
        node = nodes[path[-1]]
        for j, child in enumerate(node['args']):
            flip = 1 if node['op'] == 'NOT' or (node['op'] == 'EXC' and j == 1) else 0
            walk(li, link, path + [child], flips + flip, alt or node['op'] == 'ALT')

    for li, link in enumerate(out['links']):
        walk(li, link, [link['node_id']], 0, False)
    return res, cache


def role_verdict(cls, role, flips, uncertain):
    if role == 'qual':
        return 'hedged'
    if role in ('obj', 'acts'):
        return 'hedged' if uncertain else 'role_loss'
    pol, strength = {'if': ('+', 'if'), 'onlyif': ('+', 'onlyif'),
                     'unless': ('-', 'unless'), 'regardless': ('0', 'regardless')}[role]
    if flips % 2:
        if pol == '+':
            pol, strength = '-', 'unless'
        elif pol == '-':
            pol, strength = '+', 'indeterminate'
    want_pol, want_strength = {'COND': ('+', 'if'), 'RESTRICT': ('+', 'onlyif'),
                               'EXCEPT': ('-', None), 'IRRESPECTIVE': ('0', None)}[cls]
    if pol != want_pol:
        return 'inversion'
    if want_strength is None or strength == want_strength:
        return 'correct'
    return 'hedged' if uncertain else 'scope_change'


def text_status(cov, K):
    if K['all'] <= cov:
        return 'complete'
    if K['parts'] <= cov:
        return 'lost_marker'
    return 'partial' if cov & K['all'] else 'absent'


# ---------------------------------------------------------------- scoring

def validate_mapping(ref, out, mappings):
    need(isinstance(mappings, list), 'mappings must be a list')
    tids = [t['tid'] for t in ref['targets']]
    by_tid = {}
    uids = {u['id'] for u in out['units']}
    for m in mappings:
        need(set(m) == {'tid', 'units', 'basis'} and m['tid'] in tids and m['tid'] not in by_tid,
             f"mapping entry {m.get('tid')!r}")
        seen = set()
        for u in m['units']:
            need(set(u) == {'unit', 'form'} and u['unit'] in uids and u['form'] in FORMS
                 and u['unit'] not in seen, f"mapping {m['tid']} unit {u}")
            seen.add(u['unit'])
        by_tid[m['tid']] = {u['unit']: u['form'] for u in m['units']}
    need(set(by_tid) == set(tids), 'every reference target needs exactly one mapping entry')
    return by_tid


def score(ref, source, raw_output, mappings, arm):
    need(arm in ('OPQ', 'FULL'), 'arm')
    out = normalize_output(raw_output)
    nodes = out['nodes']
    U = validate_mapping(ref, out, mappings)
    W, cache = witnesses(source, out)
    rels = {r['rid']: r for r in ref['relations']}
    K = {rid: rel_K(source, r) for rid, r in rels.items()}
    tq = {t['tid']: cps(source, [(t['quote']['start'], t['quote']['end'])]) for t in ref['targets']}
    by_tid = {}
    for r in ref['relations']:
        by_tid.setdefault(r['tid'], []).append(r)

    def extraneous(w, tid):
        allowed = set(tq[tid])
        for r2 in by_tid[tid]:
            allowed |= K[r2['rid']]['all']
        return len(w.cov - allowed)

    def verdict_on(w, r, form):
        flips = w.flips + (1 if form == 'inverse' else 0)
        return role_verdict(r['class'], w.link['role'], flips, w.path_uncertain)

    def embedded(w, r, form):
        if nodes[w.node]['op'] != 'L':
            return False
        for h in by_tid[r['tid']]:
            if h is r or h['contested'] or h['class'] == 'UNRESOLVED':
                continue
            if text_status(w.cov, K[h['rid']]) == 'complete' and verdict_on(w, h, form) == 'correct':
                return True
        return False

    index = {(w.li, w.path): w for w in W}

    def minimal(w, k):
        # A witness is the smallest subtree on its path that preserves the same text:
        # a parent cannot take credit for text that one child already carries (no borrowing
        # of a containing structure, e.g. an EXC whose carve-out holds the clause).
        rank, got = TEXT_RANK[text_status(w.cov, k)], len(w.cov & k['all'])
        for child in nodes[w.node]['args']:
            w2 = index[(w.li, w.path + (child,))]
            if TEXT_RANK[text_status(w2.cov, k)] <= rank and len(w2.cov & k['all']) >= got:
                return False
        return True

    results = {}
    for r in ref['relations']:
        rid, tid, k = r['rid'], r['tid'], K[r['rid']]
        res = dict(rid=rid, cls=r['class'], critical=r['critical'], contested=r['contested'],
                   K_size=len(k['all']), witness=None)
        results[rid] = res
        cand = [(w, U[tid][w.unit]) for w in W if w.unit in U[tid] and minimal(w, k)]
        if r['class'] == 'UNRESOLVED':
            hits = [w for w, f in cand if text_status(w.cov, k) == 'complete']
            res['verdict'] = 'excluded_unresolved'
            res['calibration'] = ('calibrated' if any(w.path_uncertain or w.link['role'] == 'qual'
                                                      for w in hits) else
                                  'asserted' if hits else 'not_preserved')
            continue
        if not any(w.cov & k['all'] for w, _ in cand):
            outside = [w for w in W if w.unit not in U[tid]]
            res['verdict'] = ('wrong_target' if any(text_status(w.cov, k) == 'complete' for w in outside)
                              else 'absent')
            res['text_status'] = 'absent'
            if r['contested']:
                res['verdict'] = 'excluded_contested:' + res['verdict']
            continue
        ranked = []
        for w, form in cand:
            st = text_status(w.cov, k)
            rv = verdict_on(w, r, form)
            if st == 'complete' and rv not in ('correct', 'hedged') and embedded(w, r, form):
                rv = 'embedded'
            key = (TEXT_RANK[st], -len(w.cov & k['all']), ROLE_RANK[rv], extraneous(w, tid),
                   len(w.cov), w.li, w.path)
            ranked.append((key, w, form, st, rv))
        ranked.sort(key=lambda item: item[0])
        _, best, form, st, rv = ranked[0]
        res['witness'] = dict(link_index=best.li, unit=best.unit, form=form, role=best.link['role'],
                              path=list(best.path), flips=best.flips, uncertain=best.path_uncertain)
        res['text_status'] = st
        res['extraneous'] = extraneous(best, tid)
        if st == 'partial':
            v = 'shortened'
        elif st == 'lost_marker':
            v = 'lost_connective'
        elif rv in ('inversion', 'role_loss', 'scope_change'):
            v = rv
        elif any(st2 == 'complete' and rv2 == 'inversion' and not w2.path_uncertain
                 for _, w2, _, st2, rv2 in ranked[1:]):
            v = 'contradiction'
        elif rv in ('correct', 'hedged') and res['extraneous'] > BROAD_FACTOR * len(k['all']):
            v = 'broad'
        else:
            v = rv
        res['verdict'] = ('excluded_contested:' + v) if r['contested'] else v
        res['_best'] = best

    typed = {}
    invented = []
    if arm == 'FULL':
        typed, invented = score_typed(ref, source, out, U, W, cache, K, tq, by_tid, results)
    for res in results.values():
        res.pop('_best', None)
    return dict(arm=arm, relations=results, compounds=typed, invented=invented)


def score_typed(ref, source, out, U, W, cache, K, tq, by_tid, results):
    nodes = out['nodes']
    live = [r for r in ref['relations'] if not r['contested']]

    def cov(nid):
        return subtree_cov(source, nodes, nid, cache)

    def bijection(op_children, ref_children):
        Ks = [node_K(source, c) for c in ref_children]
        covs = [cov(c) for c in op_children]
        used = [False] * len(covs)

        def go(i):
            if i == len(Ks):
                return True
            for j, c in enumerate(covs):
                if not used[j] and Ks[i] <= c:
                    used[j] = True
                    if go(i + 1):
                        return True
                    used[j] = False
            return False
        return go(0)

    matched_ops = set()   # operators already judged against a reference compound
    typed = {}
    for c in compounds(ref):
        rid = c['rid']
        rres, r = results[rid], next(x for x in ref['relations'] if x['rid'] == rid)
        if c['kind'] == 'XTO':
            v, node = exc_verdict(out, U, W, K, r, rres, cov)
            if node:
                matched_ops.add(node)
            typed[c['cid']] = dict(verdict=v, critical=c['critical'], rid=rid, operator=node)
            continue
        if rres['verdict'] not in TEXT_COMPLETE:
            typed[c['cid']] = dict(verdict='relation_failed', critical=c['critical'], rid=rid,
                                   operator=None)
            continue
        best = rres['_best']
        n = c['node']
        found = []
        for o in subtree(nodes, best.node):
            on = nodes[o]
            if len(on['args']) != len(n['children']):
                continue
            if n['op'] == 'EXC' and on['op'] == 'EXC':
                k0, k1 = (node_K(source, ch) for ch in n['children'])
                a0, a1 = (cov(a) for a in on['args'])
                v = 'correct' if k0 <= a0 and k1 <= a1 else 'exc_reversed' if k1 <= a0 and k0 <= a1 else None
            elif on['op'] in ('AND', 'OR', 'ALT', 'EXC') and bijection(on['args'], n['children']):
                v = ('hedged' if on['op'] == 'ALT' else 'correct' if on['op'] == n['op'] else 'swap')
            else:
                v = None
            if v:
                found.append((('correct', 'hedged', 'swap', 'exc_reversed').index(v), o, v))
        if found:
            found.sort()
            _, o, v = found[0]
            matched_ops.add(o)
            typed[c['cid']] = dict(verdict=v, critical=c['critical'], rid=rid, operator=o)
            continue
        Ks = [node_K(source, ch) for ch in n['children']]
        separator = None
        for o in subtree(nodes, best.node):
            on = nodes[o]
            if on['op'] not in ('AND', 'OR', 'ALT', 'EXC'):
                continue
            hits = [{i for i, k in enumerate(Ks) if cov(a) & k} for a in on['args']]
            if any(i1 != i2 for x, h1 in enumerate(hits) for h2 in hits[x + 1:] for i1 in h1 for i2 in h2):
                separator = separator or o
        if separator:
            matched_ops.add(separator)
        typed[c['cid']] = dict(verdict='mismatch' if separator else 'flattened',
                               critical=c['critical'], rid=rid, operator=separator)

    inv = {}
    for r in ref['relations']:
        rres = results[r['rid']]
        if r['contested'] or r['class'] == 'UNRESOLVED' or rres['verdict'] not in TEXT_COMPLETE:
            continue
        best = rres['_best']
        scope = list(best.path[:-1]) + subtree(nodes, best.node)
        tid = r['tid']
        for o in scope:
            on = nodes[o]
            if on['q'] != 0 or on['op'] not in ('AND', 'OR', 'EXC') or o in matched_ops:
                continue
            if on['op'] == 'AND' and cross_relation(on, live, K, cov):
                continue
            if on['op'] == 'EXC' and exc_consistent(on, by_tid[tid], K, tq[tid], cov):
                continue
            entry = inv.setdefault(o, dict(node=o, rid=r['rid'], critical=False, verdict='invented'))
            entry['critical'] = entry['critical'] or r['critical']
    invented = sorted(inv.values(), key=lambda e: e['node'])
    return typed, invented


def cross_relation(on, rels, K, cov):
    """A conjunction that joins separate reference relations (the format allows one if/onlyif/
    unless link per unit, so separate conditions must be joined): every child carries at least
    one whole relation and at least two distinct relations are carried."""
    carried, every = set(), True
    for a in on['args']:
        here = {r['rid'] for r in rels if K[r['rid']]['parts'] <= cov(a)}
        every = every and bool(here)
        carried |= here
    return every and len(carried) >= 2


def exc_consistent(on, rels, K, target_K, cov):
    base, carve = cov(on['args'][0]), cov(on['args'][1])
    base_ok = bool(base & target_K) or any(K[r['rid']]['parts'] <= base for r in rels)
    carve_ok = any(r['class'] == 'EXCEPT' and not r['contested'] and K[r['rid']]['parts'] <= carve
                   for r in rels)
    return base_ok and carve_ok


def exc_verdict(out, U, W, K, r, rres, cov):
    """exception_to compound: EXCEPT relation r carves out of relation h (clause parts only;
    introducers may sit on links or operators)."""
    nodes = out['nodes']
    kr, kh = K[r['rid']]['parts'], K[r['carves_out_of']]['parts']
    excs = sorted({w.node for w in W if w.unit in U[r['tid']] and nodes[w.node]['op'] == 'EXC'})
    for e in excs:
        base, carve = nodes[e]['args']
        if kr <= cov(base) and kh <= cov(carve):
            return 'exc_reversed', e
    if rres['verdict'] not in TEXT_COMPLETE:
        return 'relation_failed', None
    for e in excs:
        base, carve = nodes[e]['args']
        if kh <= cov(base) and kr <= cov(carve):
            return 'correct', e
    path = rres['_best'].path
    for i, p in enumerate(path[:-1]):
        if nodes[p]['op'] == 'EXC' and nodes[p]['args'][1] == path[i + 1]:
            return 'wrong_base', p
    return 'flattened', None


# ---------------------------------------------------------------- aggregates and bars

def tally(relations):
    """relations: iterable of dicts with verdict, critical (contested/unresolved already excluded)."""
    t = dict(N=0, complete=0, correct=0, acceptable=0, harmful_noncritical=0,
             critical_unmet=0, critical_complete=set())
    for r in relations:
        v = r['verdict']
        if v.startswith('excluded'):
            continue
        t['N'] += 1
        t['complete'] += v in TEXT_COMPLETE
        t['correct'] += v == 'correct'
        t['acceptable'] += v in ACCEPTABLE
        if r['critical']:
            t['critical_unmet'] += v not in CRITICAL_MET
            if v in TEXT_COMPLETE:
                t['critical_complete'].add(r['key'])
        else:
            t['harmful_noncritical'] += v in HARMFUL
    return t


def bar_D(cells, n_sources=3):
    """cells: {source_id: {'status': 'valid'|..., 'completion_tokens': int, 'relations': [...]}}"""
    pooled = tally(r for c in cells.values() for r in c['relations'])
    per = {s: tally(c['relations']) for s, c in cells.items()}
    res = dict(
        D1=len(cells) == n_sources and all(c['status'] == 'valid' for c in cells.values()),
        D2=pooled['N'] > 0 and pooled['complete'] * 100 >= 90 * pooled['N']
        and all(t['complete'] * 100 >= 75 * t['N'] for t in per.values()),
        D3=pooled['N'] > 0 and pooled['correct'] * 100 >= 75 * pooled['N']
        and pooled['acceptable'] * 100 >= 90 * pooled['N'],
        D4=pooled['critical_unmet'] == 0 and pooled['harmful_noncritical'] <= 1,
        D5=all(type(c['completion_tokens']) is int and c['completion_tokens'] <= HEADROOM_TOKENS
               for c in cells.values()),
    )
    res['pass'] = all(res.values())
    return res, pooled


def bar_T(full_cells, opq_cells, typed_items, n_sources=3):
    """typed_items: list of {'verdict', 'critical'} for compounds plus invented entries."""
    t1, full = bar_D(full_cells, n_sources)
    _, opq = bar_D(opq_cells, n_sources)
    n_c = sum(1 for i in typed_items if i['verdict'] != 'invented')
    typed_correct = sum(1 for i in typed_items if i['verdict'] == 'correct')
    harmful = [i for i in typed_items if i['verdict'] in TYPED_HARMFUL]
    full_ct = sum(c['completion_tokens'] for c in full_cells.values())
    opq_ct = sum(c['completion_tokens'] for c in opq_cells.values())
    res = dict(
        T1=t1['pass'],
        T2=full['complete'] >= opq['complete'] - 1
        and opq['critical_complete'] <= full['critical_complete'],
        T3=full['correct'] >= opq['correct'],
        T4=n_c >= 5 and typed_correct * 100 >= 90 * n_c,
        T5=not any(i['critical'] for i in harmful) and len(harmful) <= 1,
        T6=len(full_cells) == n_sources and len(opq_cells) == n_sources and opq_ct > 0
        and 2 * full_ct <= 3 * opq_ct,
    )
    res['pass'] = all(res.values())
    return res


def best_case_cells(observed, unrun):
    """Unrun cells scored as perfect: valid, zero tokens, every relation correct."""
    cells = dict(observed)
    for sid, rels in unrun.items():
        cells[sid] = dict(status='valid', completion_tokens=0,
                          relations=[dict(key=r['key'], verdict='correct', critical=r['critical'])
                                     for r in rels])
    return cells


def futile(arm, observed, unrun, opq_cells=None, typed_observed=(), unrun_compounds=0):
    """Pre-registered futility (PROTOCOL §6): the bar fails even if every unrun item is perfect.
    Evaluated separately under each adjudicator's scores."""
    cells = best_case_cells(observed, unrun)
    if arm == 'OPQ':
        return not bar_D(cells)[0]['pass']
    typed = list(typed_observed) + [dict(verdict='correct', critical=False)] * unrun_compounds
    return not bar_T(cells, opq_cells, typed)['pass']


def outcome(state):
    """Run-level outcome from per-adjudicator verdicts. See PROTOCOL §9."""
    if state.get('halted_phase') == 'OPQ':
        return 'P'
    if state['opq_mechanical_fail']:
        return 'O3'
    a1, a2 = state['opq_pass']['A1'], state['opq_pass']['A2']
    if not a1 and not a2:
        return 'O3'
    if a1 != a2:
        return 'O4'
    if not state['typed_testable']:
        return 'O1-untestable'
    if state.get('halted_phase') == 'FULL':
        return 'O1-incomplete'
    f = state['full_pass']
    if f['A1'] and f['A2']:
        return 'O2'
    if f['A1'] != f['A2'] and None not in (f['A1'], f['A2']):
        return 'O1-disputed'
    return 'O1'


# ---------------------------------------------------------------- CLI

def _load(path):
    with open(path, 'rb') as fh:
        return json.loads(fh.read().decode('utf-8'))


def main(argv):
    if len(argv) >= 3 and argv[0] == 'validate-reference':
        ref, src = _load(argv[1]), open(argv[2], 'rb').read().decode('utf-8')
        validate_reference(ref, src)
        print(json.dumps(dict(ok=True, relations=len(ref['relations']),
                              compounds=len(compounds(ref))), sort_keys=True))
        return 0
    if len(argv) == 6 and argv[0] == 'score':
        ref, src = _load(argv[1]), open(argv[2], 'rb').read().decode('utf-8')
        validate_reference(ref, src)
        adj = _load(argv[4])
        need(adj.get('spec_version') == ADJ_VERSION, 'adjudication spec_version')
        print(json.dumps(score(ref, src, _load(argv[3]), adj['mappings'], argv[5]),
                         sort_keys=True, indent=1, default=sorted))
        return 0
    print('usage: r17score.py validate-reference REF SOURCE | '
          'score REF SOURCE OUTPUT ADJUDICATION OPQ|FULL', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
