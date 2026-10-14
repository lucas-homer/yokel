#!/usr/bin/env python3
"""R17 design-r3 reference scorer: the mechanical half of ADJUDICATION-SPEC.md.

Offline, stdlib only. Run as `python3 -I -S -B r17score.py ...`.

Adjudicators supply only target mappings (which output units assert each
reference target, and in which form). Everything else here is mechanical:
quote and partition checks, claim and witness enumeration, coverage,
reference-relative polarity, verdict precedence, the extra-claim audit,
typed-logic matching, aggregates, bars, outcomes and the binding-checked
decision entry point (`decide`). A rule in this file that disagrees with
ADJUDICATION-SPEC.md is a bug in one of them; neither silently wins.
"""
import hashlib
import json
import sys
import unicodedata
from fractions import Fraction

REF_VERSION = 'r17.ref.v3'
ADJ_VERSION = 'r17.adj.v2'
MANIFEST_VERSION = 'r17.manifest.v1'
CLASSES = ('COND', 'RESTRICT', 'EXCEPT', 'IRRESPECTIVE', 'UNRESOLVED')
LOGIC_OPS = ('PART', 'AND', 'OR', 'NOT', 'EXC')
EXCLUSION_REASONS = ('target_reference', 'citation', 'aside')
ROLES = ('if', 'onlyif', 'unless', 'regardless', 'obj', 'acts', 'qual')
APPLICABILITY_ROLES = ('if', 'onlyif', 'unless', 'regardless')
OPS = ('L', 'R', 'AND', 'OR', 'NOT', 'EXC', 'ALT')
LEAF_OPS = ('L', 'R')
FORMS = ('direct', 'inverse', 'opposite')
ADJUDICATORS = {'A1': 'claude-fable-5-1', 'A2': 'claude-opus-5-5'}
ADJ_EFFORT = 'high'
DEFECT_KINDS = ('missing_relation', 'wrong_target', 'wrong_class', 'segmentation',
                'critical_flag', 'quote', 'other')

# Relation verdicts (precedence in ADJUDICATION-SPEC B5).
HARMFUL = ('absent', 'wrong_target', 'shortened', 'lost_connective',
           'inversion', 'role_loss', 'scope_change', 'contradiction', 'cell_failed')
ACCEPTABLE = ('correct', 'hedged', 'embedded', 'broad')
CRITICAL_MET = ('correct', 'hedged', 'broad')
TEXT_COMPLETE = ACCEPTABLE + ('inversion', 'role_loss', 'scope_change', 'contradiction')
TYPED_HARMFUL = ('swap', 'mismatch', 'exc_reversed', 'invented')
# C3: mutually exclusive, exhaustive categories for Cohen's kappa.
KAPPA_CATEGORY = dict(correct='correct', hedged='hedged_or_broad', broad='hedged_or_broad',
                      embedded='embedded', absent='text_harmful', wrong_target='text_harmful',
                      shortened='text_harmful', lost_connective='text_harmful',
                      inversion='semantic_harmful', role_loss='semantic_harmful',
                      scope_change='semantic_harmful', contradiction='semantic_harmful',
                      cell_failed='cell_failed')

ROLE_RANK = dict(correct=0, hedged=1, embedded=2, scope_change=3, role_loss=4, inversion=5)
TEXT_RANK = dict(complete=0, lost_marker=1, partial=2, absent=3)
BROAD_FACTOR = 2          # broad iff extraneous > BROAD_FACTOR * |K|
HEADROOM_TOKENS = 13926   # D5: 85% of 16,384
MAX_PATHS = 200000


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


def rng(q):
    return (q['start'], q['end'])


def qcps(source, quotes):
    return cps(source, [rng(q) for q in quotes])


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
    need(isinstance(text, str) and any(counted(ch) for ch in text), f'{where}: quote has no counted character')
    need(all(type(v) is int for v in (start, end, occ)), f'{where}: non-integer offset')
    need(0 <= start < end <= len(source), f'{where}: offsets out of range')
    need(source[start:end] == text, f'{where}: source[start:end] != text')
    starts = match_starts(source, text)
    need(1 <= occ <= len(starts) and starts[occ - 1] == start,
         f'{where}: occurrence {occ} does not resolve to start {start}')
    return (start, end)


def disjoint(ranges, where):
    ranges = sorted(ranges)
    need(all(a[1] <= b[0] for a, b in zip(ranges, ranges[1:])), f'{where}: overlapping quotes')


# ---------------------------------------------------------------- reference

REF_KEYS = {'spec_version', 'source_id', 'source_text_sha256', 'targets', 'relations',
            'out_of_scope_notes'}
REL_KEYS = {'rid', 'tid', 'class', 'introducer', 'clause', 'excluded', 'logic', 'rationale',
            'critical', 'critical_reason', 'contested', 'contested_reason'}


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


def _ident(value, prefix):
    return isinstance(value, str) and len(value) > 1 and value[0] == prefix and value[1:].isdigit()


def _check_logic(source, node, rid, nids):
    need(isinstance(node, dict) and node.get('op') in LOGIC_OPS, f'{rid}: logic op')
    need(isinstance(node.get('nid'), str) and node['nid'] not in nids, f'{rid}: logic nid')
    nids.add(node['nid'])
    if node['op'] == 'PART':
        need(set(node) == {'nid', 'op', 'quotes', 'markers'}, f'{rid}: PART shape')
        need(isinstance(node['quotes'], list) and node['quotes'], f'{rid}: PART needs quotes')
        need(isinstance(node['markers'], list), f'{rid}: PART markers must be a list')
    else:
        need(set(node) == {'nid', 'op', 'markers', 'children'}, f'{rid}: operator shape')
        need(isinstance(node['markers'], list) and node['markers'], f'{rid}: operator needs markers')
        kids = node['children']
        need(isinstance(kids, list), f'{rid}: children must be a list')
        arity = {'NOT': (1, 1), 'EXC': (2, 2)}.get(node['op'], (2, 99))
        need(arity[0] <= len(kids) <= arity[1], f'{rid}: operator arity')
        for child in kids:
            _check_logic(source, child, rid, nids)


def validate_reference(ref, source):
    """Mechanical reference check (REFERENCE-SPEC §7.1): schema, field types, quotes,
    occurrences, overlap, the declared-clause partition, orphan targets."""
    need(isinstance(ref, dict) and set(ref) == REF_KEYS, 'reference top-level keys')
    need(ref['spec_version'] == REF_VERSION, 'reference spec_version')
    need(isinstance(ref['source_id'], str) and ref['source_id'].strip(), 'source_id must be a string')
    need(ref['source_text_sha256'] == hashlib.sha256(source.encode('utf-8')).hexdigest(),
         'source_text_sha256 mismatch')
    need(isinstance(ref['targets'], list) and isinstance(ref['relations'], list),
         'targets and relations must be lists')
    need(isinstance(ref['out_of_scope_notes'], list)
         and all(isinstance(n, str) for n in ref['out_of_scope_notes']), 'out_of_scope_notes')
    tids, spans, tq = set(), set(), {}
    for t in ref['targets']:
        need(isinstance(t, dict) and set(t) == {'tid', 'quote', 'gloss'}, 'target keys')
        need(_ident(t['tid'], 'T') and t['tid'] not in tids, f"target id {t['tid']!r}")
        tids.add(t['tid'])
        span = check_quote(source, t['quote'], t['tid'])
        need(span not in spans, f"{t['tid']}: duplicate target span")
        spans.add(span)
        tq[t['tid']] = cps(source, [span])
        need(isinstance(t['gloss'], str) and len(t['gloss']) <= 120, f"{t['tid']}: gloss must be a string <= 120")
    rids, governed = set(), set()
    for r in ref['relations']:
        need(isinstance(r, dict) and set(r) == REL_KEYS, 'relation keys')
        rid = r['rid']
        need(_ident(rid, 'R') and rid not in rids, f'relation id {rid!r}')
        rids.add(rid)
        need(r['tid'] in tids, f'{rid}: unknown tid')
        governed.add(r['tid'])
        need(r['class'] in CLASSES, f'{rid}: class')
        need(isinstance(r['rationale'], str) and r['rationale'].strip(), f'{rid}: rationale')
        need(type(r['critical']) is bool and type(r['contested']) is bool, f'{rid}: flags must be booleans')
        need(isinstance(r['critical_reason'], str) and isinstance(r['contested_reason'], str),
             f'{rid}: reasons must be strings')
        need(bool(r['critical_reason'].strip()) == r['critical'], f'{rid}: critical_reason iff critical')
        need(bool(r['contested_reason'].strip()) == r['contested'], f'{rid}: contested_reason iff contested')
        need(isinstance(r['introducer'], list) and len(r['introducer']) <= 3, f'{rid}: introducer list')
        need(isinstance(r['clause'], list) and r['clause'], f'{rid}: clause must be a non-empty list')
        need(isinstance(r['excluded'], list), f'{rid}: excluded must be a list')
        for e in r['excluded']:
            need(isinstance(e, dict) and set(e) == {'quote', 'reason', 'note'}, f'{rid}: excluded entry keys')
            need(e['reason'] in EXCLUSION_REASONS, f'{rid}: exclusion reason {e["reason"]!r}')
            need(isinstance(e['note'], str) and e['note'].strip(), f'{rid}: exclusion note')
        _check_logic(source, r['logic'], rid, set())
        excluded = [e['quote'] for e in r['excluded']]
        roles = r['introducer'] + logic_quotes(r['logic'], 'parts') + logic_quotes(r['logic'], 'markers') + excluded
        disjoint([check_quote(source, q, f'{rid} quote {i}') for i, q in enumerate(roles)], rid)
        disjoint([check_quote(source, q, f'{rid} clause {i}') for i, q in enumerate(r['clause'])], f'{rid} clause')
        for n in logic_nodes(r['logic']):
            if n['op'] == 'PART':
                need(qcps(source, n['quotes']), f'{rid}: PART {n["nid"]} contains no counted characters')
            for q in n['markers']:
                need(qcps(source, [q]), f'{rid}: marker {q["text"]!r} contains no counted characters')
        clause, covered = qcps(source, r['clause']), qcps(source, roles)
        need(clause == covered, f'{rid}: partition: the clause and introducer/markers/parts/excluded differ by '
                                f'{len(clause ^ covered)} counted codepoints')
        need(not clause & tq[r['tid']], f'{rid}: clause overlaps its target quote')
    orphans = sorted(tids - governed)
    need(not orphans, f'orphan target(s) without a relation: {orphans}')
    return True


def live(r):
    return not r['contested'] and r['class'] != 'UNRESOLVED'


def negation_sources(source, logic):
    """{PART codepoint: [marker codepoint set per negation source above it]} (B4)."""
    out = {}

    def walk(node, srcs):
        if node['op'] == 'PART':
            here = srcs + [frozenset(qcps(source, [q])) for q in node['markers']]
            for x in qcps(source, node['quotes']):
                out[x] = here
            return
        for j, child in enumerate(node['children']):
            flip = node['op'] == 'NOT' or (node['op'] == 'EXC' and j == 1)
            walk(child, srcs + ([frozenset(qcps(source, node['markers']))] if flip else []))
    walk(logic, [])
    return out


def rel_K(source, r):
    parts = qcps(source, logic_quotes(r['logic'], 'parts'))
    markers = qcps(source, r['introducer'] + logic_quotes(r['logic'], 'markers'))
    neg = negation_sources(source, r['logic'])
    return dict(parts=parts, markers=markers, all=parts | markers, clause=qcps(source, r['clause']),
                neg=neg, neg_markers=set().union(*[s for v in neg.values() for s in v]) if neg else set())


def node_parts(source, node):
    return qcps(source, logic_quotes(node, 'parts'))


def compounds(ref):
    """Scored compound items (B7): AND/OR/EXC logic nodes of live relations."""
    return [dict(cid=f"{r['rid']}:{n['nid']}", rid=r['rid'], kind=n['op'], node=n, critical=r['critical'])
            for r in ref['relations'] if live(r)
            for n in logic_nodes(r['logic']) if n['op'] in ('AND', 'OR', 'EXC')]


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
        arity = {'L': (0, 0), 'R': (0, 0), 'NOT': (1, 1), 'EXC': (2, 2)}.get(n['op'], (2, 8))
        need(arity[0] <= len(n['args']) <= arity[1], f"node {n['id']}: arity")
    uids = {u['id'] for u in units}
    for l in links:
        need(l['role'] in ROLES and l['node_id'] in ids and l['unit_id'] in uids, 'link shape')
    return dict(units=units, nodes={n['id']: n for n in nodes}, links=links)


def subtree(nodes, nid):
    seen, stack = [], [nid]
    while stack:
        cur = stack.pop()
        if cur not in seen:
            seen.append(cur)
            stack.extend(reversed(nodes[cur]['args']))
    return seen


def link_paths(nodes, root):
    """Every root-to-node path: (path, flips, uncertain). Flips: edges out of NOT and into an
    EXC carve-out. Uncertain: any node on the path has q != 0 or is ALT (link q added by caller)."""
    out = []

    def walk(path, flips, unc):
        need(len(out) < MAX_PATHS, 'output graph has too many paths')
        out.append((path, flips, unc))
        node = nodes[path[-1]]
        for j, child in enumerate(node['args']):
            need(child not in path, 'output graph has a cycle')
            flip = 1 if node['op'] == 'NOT' or (node['op'] == 'EXC' and j == 1) else 0
            c = nodes[child]
            walk(path + (child,), flips + flip, unc or c['q'] != 0 or c['op'] == 'ALT')
    r = nodes[root]
    walk((root,), 0, r['q'] != 0 or r['op'] == 'ALT')
    return out


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


def text_status(credited, K):
    if K['all'] <= credited:
        return 'complete'
    if K['parts'] <= credited:
        return 'lost_marker'
    return 'partial' if credited else 'absent'


# ---------------------------------------------------------------- scoring

def validate_mapping(ref, out, mappings):
    need(isinstance(mappings, list), 'mappings must be a list')
    tids = [t['tid'] for t in ref['targets']]
    by_tid = {}
    uids = {u['id'] for u in out['units']}
    for m in mappings:
        need(isinstance(m, dict) and set(m) == {'tid', 'units', 'basis'} and m['tid'] in tids
             and m['tid'] not in by_tid, f"mapping entry {m.get('tid') if isinstance(m, dict) else m!r}")
        need(isinstance(m['units'], list) and isinstance(m['basis'], str), f"mapping {m['tid']} shape")
        seen = set()
        for u in m['units']:
            need(isinstance(u, dict) and set(u) == {'unit', 'form'} and u['unit'] in uids
                 and u['form'] in FORMS and u['unit'] not in seen, f"mapping {m['tid']} unit {u}")
            seen.add(u['unit'])
        by_tid[m['tid']] = {u['unit']: u['form'] for u in m['units']}
    need(set(by_tid) == set(tids), 'every reference target needs exactly one mapping entry')
    return by_tid


def normalized_mapping(mappings):
    """C4 agreement: exact on target/unit/form only (never basis or session metadata)."""
    return {m['tid']: sorted((u['unit'], u['form']) for u in m['units']) for m in mappings}


class Scorer:
    def __init__(self, ref, source, raw_output, mappings, arm):
        need(arm in ('OPQ', 'FULL'), 'arm')
        self.ref, self.source, self.arm = ref, source, arm
        self.out = normalize_output(raw_output)
        self.nodes, self.links = self.out['nodes'], self.out['links']
        self.U = validate_mapping(ref, self.out, mappings)
        self.rels = {r['rid']: r for r in ref['relations']}
        self.K = {rid: rel_K(source, r) for rid, r in self.rels.items()}
        self.tq = {t['tid']: cps(source, [rng(t['quote'])]) for t in ref['targets']}
        self.by_tid = {}
        for r in ref['relations']:
            self.by_tid.setdefault(r['tid'], []).append(r)
        self.allowed = {tid: set(self.tq[tid]).union(*[self.K[r['rid']]['clause'] for r in rs])
                        for tid, rs in self.by_tid.items()}
        n = self.nodes
        self.ncps = {nid: cps(source, node['evidence']) for nid, node in n.items()}
        self.sub_all = {nid: set().union(*[self.ncps[m] for m in subtree(n, nid)]) for nid in n}
        self.sub_leaf = {nid: set().union(*[self.ncps[m] for m in subtree(n, nid) if n[m]['op'] in LEAF_OPS])
                         for nid in n}
        self.lcps = [cps(source, l['evidence']) for l in self.links]
        self.paths = [link_paths(n, l['node_id']) for l in self.links]
        self._claims = {}

    # -- B2/B4: one claim per (link, relation, form)
    def claim(self, li, rid, form):
        key = (li, rid, form)
        if key in self._claims:
            return self._claims[key]
        r, k, link, nodes = self.rels[rid], self.K[rid], self.links[li], self.nodes
        flip0 = 0 if form == 'direct' else 1
        par, unc = set(), link['q'] != 0
        for path, flips, punc in self.paths[li]:
            leaf = path[-1]
            if nodes[leaf]['op'] not in LEAF_OPS:
                continue
            ev = self.ncps[leaf]
            hit = ev & k['parts']
            if not hit:
                continue
            unc = unc or punc
            for x in hit:
                srcs = k['neg'][x]
                intact = sum(1 for s in srcs if s <= ev)
                par.add((flip0 + flips + intact - len(srcs)) % 2)
        if r['class'] == 'UNRESOLVED':
            role, polarity = None, None
        elif len(par) > 1:
            role, polarity = 'inversion', 'mixed'
        elif par:
            polarity = next(iter(par))
            role = role_verdict(r['class'], link['role'], polarity, unc)
        else:
            role, polarity = None, None
        best = None
        for path, _, _ in self.paths[li]:
            st, credited, allcov = self.status_at(li, path, rid)
            ext = len(allcov - self.allowed[r['tid']])
            rank = (TEXT_RANK[st], -len(credited), ext, len(allcov), path)
            if best is None or rank < best[0]:
                best = (rank, path, st, credited, allcov, ext)
        _, path, st, credited, allcov, ext = best
        verdict = role
        if (st == 'complete' and role not in ('correct', 'hedged', None)
                and nodes[path[-1]]['op'] == 'L' and self.hosts_correct(li, path, rid, form)):
            verdict = 'embedded'
        c = dict(li=li, unit=link['unit_id'], form=form, role=link['role'], path=path, status=st,
                 credited=credited, allcov=allcov, extraneous=ext, verdict=verdict,
                 polarity=polarity, uncertain=unc)
        self._claims[key] = c
        return c

    def status_at(self, li, path, rid):
        k, v = self.K[rid], path[-1]
        allcov = self.lcps[li].union(*[self.ncps[a] for a in path[:-1]]) | self.sub_all[v]
        credited = (self.sub_leaf[v] & k['parts']) | (allcov & k['markers'])
        return text_status(credited, k), credited, allcov

    def hosts_correct(self, li, path, rid, form):
        """Embedded (B4): the same single leaf completely carries another live relation of the
        same target, which this link states correctly."""
        r = self.rels[rid]
        for h in self.by_tid[r['tid']]:
            if h['rid'] == rid or not live(h):
                continue
            if (self.status_at(li, path, h['rid'])[0] == 'complete'
                    and self.claim(li, h['rid'], form)['verdict'] == 'correct'):
                return True
        return False

    def unqualified_opposites(self, tid):
        """B5.5: units mapped `opposite` that carry no complete clause of any live relation of
        the target through a non-obj/acts link."""
        bad = []
        for unit, form in sorted(self.U[tid].items()):
            if form != 'opposite':
                continue
            qualified = any(self.claim(li, h['rid'], form)['status'] in ('complete', 'lost_marker')
                            for li, l in enumerate(self.links)
                            if l['unit_id'] == unit and l['role'] not in ('obj', 'acts')
                            for h in self.by_tid[tid] if live(h))
            if not qualified:
                bad.append(unit)
        return bad

    def score(self):
        results = {}
        for r in self.ref['relations']:
            results[r['rid']] = self.score_relation(r)
        typed, invented, unscored = {}, [], []
        if self.arm == 'FULL':
            typed, invented, unscored = self.score_typed(results)
        for res in results.values():
            res.pop('_best', None)
        return dict(arm=self.arm, relations=results, compounds=typed, invented=invented,
                    unscored_operators=unscored)

    def score_relation(self, r):
        rid, tid, k = r['rid'], r['tid'], self.K[r['rid']]
        res = dict(rid=rid, cls=r['class'], critical=r['critical'], contested=r['contested'],
                   K_size=len(k['all']), witness=None)
        cands = [self.claim(li, rid, self.U[tid][l['unit_id']])
                 for li, l in enumerate(self.links) if l['unit_id'] in self.U[tid]]
        if r['class'] == 'UNRESOLVED':
            hits = [c for c in cands if c['status'] == 'complete']
            res['verdict'] = 'excluded_unresolved'
            res['calibration'] = ('calibrated' if any(c['uncertain'] or c['role'] == 'qual' for c in hits)
                                  else 'asserted' if hits else 'not_preserved')
            return res
        if not any(c['credited'] for c in cands):
            outside = [self.claim(li, rid, 'direct') for li, l in enumerate(self.links)
                       if l['unit_id'] not in self.U[tid]]
            v = 'wrong_target' if any(c['status'] == 'complete' for c in outside) else 'absent'
            res.update(text_status='absent', verdict=('excluded_contested:' + v) if r['contested'] else v)
            return res
        cands.sort(key=lambda c: (TEXT_RANK[c['status']], -len(c['credited']),
                                  ROLE_RANK.get(c['verdict'], 9), c['extraneous'], len(c['allcov']), c['li']))
        best = cands[0]
        res['witness'] = dict(link_index=best['li'], unit=best['unit'], form=best['form'], role=best['role'],
                              path=list(best['path']), polarity=best['polarity'], uncertain=best['uncertain'])
        res['text_status'], res['extraneous'] = best['status'], best['extraneous']
        audit = [c['li'] for c in cands[1:]
                 if c['status'] in ('complete', 'lost_marker') and c['role'] in APPLICABILITY_ROLES
                 and not c['uncertain'] and c['verdict'] in ('inversion', 'scope_change')]
        opposite = self.unqualified_opposites(tid)
        res['conflicting_links'], res['unqualified_opposite_units'] = audit, opposite
        if best['status'] == 'partial':
            v = 'shortened'
        elif best['status'] == 'lost_marker':
            v = 'lost_connective'
        elif best['verdict'] in ('inversion', 'role_loss', 'scope_change'):
            v = best['verdict']
        elif audit or opposite:
            v = 'contradiction'
        elif best['verdict'] in ('correct', 'hedged') and best['extraneous'] > BROAD_FACTOR * len(k['all']):
            v = 'broad'
        else:
            v = best['verdict']
        res['verdict'] = ('excluded_contested:' + v) if r['contested'] else v
        res['_best'] = best
        return res

    # -- B7 typed logic
    def score_typed(self, results):
        nodes, matched, typed = self.nodes, set(), {}

        def parts_exact(out_child, ref_child, kparts):
            want = node_parts(self.source, ref_child)
            return bool(want) and (self.sub_leaf[out_child] & kparts) == want

        def assign(op_children, ref_children, kparts):
            used = [False] * len(op_children)

            def go(i):
                if i == len(ref_children):
                    return True
                for j, c in enumerate(op_children):
                    if not used[j] and parts_exact(c, ref_children[i], kparts):
                        used[j] = True
                        if go(i + 1):
                            return True
                        used[j] = False
                return False
            return go(0)

        for c in compounds(self.ref):
            rid, n = c['rid'], c['node']
            rres = results[rid]
            if rres['verdict'] not in ACCEPTABLE:
                typed[c['cid']] = dict(verdict='relation_failed', critical=c['critical'], rid=rid, operator=None)
                continue
            kparts, v_node = self.K[rid]['parts'], rres['_best']['path'][-1]
            found = []
            for o in subtree(nodes, v_node):
                on = nodes[o]
                if len(on['args']) != len(n['children']):
                    continue
                v = None
                if n['op'] == 'EXC' and on['op'] == 'EXC':
                    (a0, a1), (k0, k1) = on['args'], n['children']
                    if parts_exact(a0, k0, kparts) and parts_exact(a1, k1, kparts):
                        v = 'correct'
                    elif parts_exact(a0, k1, kparts) and parts_exact(a1, k0, kparts):
                        v = 'exc_reversed'
                elif on['op'] in ('AND', 'OR', 'ALT', 'EXC') and assign(on['args'], n['children'], kparts):
                    v = 'hedged' if on['op'] == 'ALT' else 'correct' if on['op'] == n['op'] else 'swap'
                if v:
                    found.append((('correct', 'hedged', 'swap', 'exc_reversed').index(v), o, v))
            if found:
                _, o, v = min(found)
                matched.add(o)
                typed[c['cid']] = dict(verdict=v, critical=c['critical'], rid=rid, operator=o)
                continue
            Ks = [node_parts(self.source, ch) for ch in n['children']]
            separator = None
            for o in subtree(nodes, v_node):
                if nodes[o]['op'] not in ('AND', 'OR', 'ALT', 'EXC') or separator:
                    continue
                hits = [{i for i, kk in enumerate(Ks) if self.sub_leaf[a] & kk} for a in nodes[o]['args']]
                if any(i1 != i2 for x, h1 in enumerate(hits) for h2 in hits[x + 1:] for i1 in h1 for i2 in h2):
                    separator = o
            if separator:
                matched.add(separator)
            typed[c['cid']] = dict(verdict='mismatch' if separator else 'flattened',
                                   critical=c['critical'], rid=rid, operator=separator)

        inv, scoped = {}, set()
        for r in self.ref['relations']:
            rres = results[r['rid']]
            best = rres.get('_best')
            if best is None:
                continue
            scope = list(best['path'][:-1]) + subtree(nodes, best['path'][-1])
            scoped.update(scope)
            if not live(r) or rres['verdict'] not in ACCEPTABLE:
                continue
            tid = r['tid']
            for o in scope:
                on = nodes[o]
                if on['q'] != 0 or on['op'] not in ('AND', 'OR', 'EXC', 'NOT') or o in matched:
                    continue
                if on['op'] == 'AND' and self.cross_relation(on):
                    continue
                if on['op'] == 'EXC' and self.exc_consistent(on, tid):
                    continue
                if on['op'] == 'NOT' and self.not_supported(o, tid):
                    continue
                entry = inv.setdefault(o, dict(node=o, rid=r['rid'], critical=False, verdict='invented'))
                entry['critical'] = entry['critical'] or r['critical']
        unscored = sorted(o for o, on in nodes.items() if on['op'] not in LEAF_OPS and o not in scoped)
        return typed, sorted(inv.values(), key=lambda e: e['node']), unscored

    def cross_relation(self, on):
        """A conjunction joining separate reference relations (one if/onlyif/unless link per unit):
        every child carries at least one whole live relation, and at least two are carried."""
        carried, every = set(), True
        for a in on['args']:
            here = {r['rid'] for r in self.ref['relations']
                    if live(r) and self.K[r['rid']]['parts'] <= self.sub_leaf[a]}
            every = every and bool(here)
            carried |= here
        return every and len(carried) >= 2

    def exc_consistent(self, on, tid):
        base, carve = on['args']
        rels = [r for r in self.by_tid[tid] if live(r)]
        base_ok = bool(self.sub_all[base] & self.tq[tid]) or any(
            self.K[r['rid']]['parts'] <= self.sub_leaf[base] for r in rels)
        carve_ok = any(r['class'] == 'EXCEPT' and self.K[r['rid']]['parts'] <= self.sub_leaf[carve] for r in rels)
        return base_ok and carve_ok

    def not_supported(self, o, tid):
        """A NOT is supported if its own evidence cites a reference negation word of the target's
        live relations, or the introducer of one of its EXCEPT relations."""
        words = set()
        for r in self.by_tid[tid]:
            if live(r):
                words |= self.K[r['rid']]['neg_markers']
                if r['class'] == 'EXCEPT':
                    words |= qcps(self.source, r['introducer'])
        return bool(self.ncps[o] & words)


def score(ref, source, raw_output, mappings, arm):
    return Scorer(ref, source, raw_output, mappings, arm).score()


# ---------------------------------------------------------------- aggregates and bars

def tally(relations):
    """relations: iterable of dicts with key, verdict, critical (live, uncontested only)."""
    t = dict(N=0, complete=0, correct=0, acceptable=0, harmful_noncritical=0,
             critical_unmet=0, critical_complete=set())
    for r in relations:
        v = r['verdict']
        need(not v.startswith('excluded'), 'excluded verdicts never enter a bar')
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
    """cells: {slot: {'status': 'valid'|..., 'completion_tokens': int, 'relations': [...]}}"""
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
    """Pre-registered futility (PROTOCOL §8): the bar fails even if every unrun item is perfect.
    Evaluated separately under each adjudicator's scores."""
    cells = best_case_cells(observed, unrun)
    if arm == 'OPQ':
        return not bar_D(cells)[0]['pass']
    typed = list(typed_observed) + [dict(verdict='correct', critical=False)] * unrun_compounds
    return not bar_T(cells, opq_cells, typed)['pass']


PHASE_STATES = ('pass', 'fail', 'unreachable', 'reachable')


def _phase(states, name):
    """Classify one phase's per-adjudicator states (PROTOCOL §8, R2-S4). 'pass'/'fail' are
    scored-complete results; 'unreachable'/'reachable' are best-case results at an early
    stop. A best-case 'reachable' is never a pass."""
    a1, a2 = states['A1'], states['A2']
    need(a1 in PHASE_STATES and a2 in PHASE_STATES, f'{name}: unknown phase state')
    complete = {a1, a2} <= {'pass', 'fail'}
    early = {a1, a2} <= {'unreachable', 'reachable'}
    need(complete or early, f'{name}: complete and early-stop states cannot be mixed')
    need(complete or 'unreachable' in (a1, a2), f'{name}: an early stop needs an unreachable bar')
    return complete, a1, a2


def outcome(state):
    """Run-level outcome (PROTOCOL §11). state keys: halted_phase (None|'OPQ'|'FULL'),
    opq_mechanical_fail, opq {A1,A2}, typed_testable, full_mechanical_fail, full {A1,A2}."""
    if state.get('halted_phase') == 'OPQ':
        return 'P'
    if state['opq_mechanical_fail']:
        return 'O3'
    complete, a1, a2 = _phase(state['opq'], 'OPQ')
    good = ('pass', 'reachable')
    if a1 not in good and a2 not in good:
        return 'O3'
    if (a1 in good) != (a2 in good):
        return 'O4'
    need(complete, 'OPQ: early stop without an unreachable bar')
    if not state['typed_testable']:
        return 'O1-untestable'
    if state.get('halted_phase') == 'FULL':
        return 'O1-incomplete'
    if state['full_mechanical_fail']:
        return 'O1'
    complete, f1, f2 = _phase(state['full'], 'FULL')
    if not complete:
        return 'O1'
    if f1 == f2 == 'pass':
        return 'O2'
    if 'pass' in (f1, f2):
        return 'O1-disputed'
    return 'O1'


def kappa(pairs):
    """Item agreement between A1 and A2 (C3). pairs: [(verdict_A1, verdict_A2)]."""
    n = len(pairs)
    need(n > 0, 'kappa needs at least one item')
    cats = [(KAPPA_CATEGORY[a], KAPPA_CATEGORY[b]) for a, b in pairs]
    po = Fraction(sum(a == b for a, b in cats), n)
    labels = sorted({c for pair in cats for c in pair})
    pe = sum(Fraction(sum(a == l for a, _ in cats), n) * Fraction(sum(b == l for _, b in cats), n)
             for l in labels)
    k = None if pe == 1 else (po - pe) / (1 - pe)
    return dict(n=n, exact_agreement=sum(a == b for a, b in pairs), category_agreement=sum(a == b for a, b in cats),
                kappa=None if k is None else str(k), kappa_float=None if k is None else round(float(k), 4))


def drop_relations(cells, keys):
    """E10 sensitivity: the same cells with the named relation keys removed from every
    denominator. Reported only; never changes the primary result."""
    keys = set(keys)
    return {s: dict(c, relations=[r for r in c['relations'] if r['key'] not in keys]) for s, c in cells.items()}


# ---------------------------------------------------------------- binding-checked decision (C5)

def canonical_bytes(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


def sha_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


SLOTS = ('S1', 'S2', 'S3')
ARMS = ('OPQ', 'FULL')


def _json(files, name, what):
    need(isinstance(name, str) and name in files, f'{what}: missing file {name!r}')
    return json.loads(files[name].decode('utf-8'))


UNRUN = ('skipped', 'pending')


def decide(manifest, calls, files, interim=False):
    """The complete decision gate. manifest: frozen scoring manifest (release record part).
    calls: {call_id: record}. files: {name: bytes}. Every binding is checked before any bar
    is computed; denominators come from the manifest, never from the supplied lists.
    interim=True is the staged futility test (PROTOCOL §8): calls not yet released are
    'pending', unrun cells are best-case, and the outcome is None while no stopping state
    has been reached."""
    need(isinstance(manifest, dict) and manifest.get('spec_version') == MANIFEST_VERSION, 'manifest spec_version')
    need(manifest.get('adjudicators') == {a: dict(model=m, effort=ADJ_EFFORT) for a, m in ADJUDICATORS.items()},
         'manifest adjudicators must be exactly A1/A2 with the pinned models')
    need(type(manifest.get('typed_testable')) is bool, 'manifest typed_testable')
    need(set(manifest.get('sources', {})) == set(SLOTS), 'manifest must name exactly S1, S2, S3')
    need(set(calls) == {f'{s}-{a}' for s in SLOTS for a in ARMS}, 'call records must be exactly S1..S3 x OPQ/FULL')
    refs, sources = {}, {}
    for s in SLOTS:
        m = manifest['sources'][s]
        raw_src = files.get(m['source_file'])
        need(raw_src is not None and sha_bytes(raw_src) == m['source_sha256'], f'{s}: source sha256')
        raw_ref = files.get(m['reference_file'])
        need(raw_ref is not None and sha_bytes(raw_ref) == m['reference_sha256'], f'{s}: reference sha256')
        source, ref = raw_src.decode('utf-8'), json.loads(raw_ref.decode('utf-8'))
        validate_reference(ref, source)
        need(ref['source_id'] == m['source_id'], f'{s}: reference source_id')
        live_rel = {r['rid']: r['critical'] for r in ref['relations'] if live(r)}
        need(live_rel == m['relations'], f'{s}: live relation set or critical flags differ from the manifest')
        comp = {c['cid']: c['critical'] for c in compounds(ref)}
        need(comp == m['compounds'], f'{s}: compound set differs from the manifest')
        refs[s], sources[s] = ref, source

    def check_call(cid):
        rec = calls[cid]
        need(isinstance(rec, dict) and rec.get('call_id') == cid, f'{cid}: call record id')
        st = rec['state']
        need(st != 'pending' or interim, f'{cid}: pending calls are allowed only in an interim decision')
        if st in UNRUN:
            need(rec.get('output_file') is None and rec.get('halt') is None, f'{cid}: unrun call has output or halt')
            return rec
        need(type(st) is int and 2 <= st <= 13, f'{cid}: response state {st!r} not allowed in a final record')
        ct = rec.get('completion_tokens')
        need(ct is None or (type(ct) is int and ct >= 0), f'{cid}: completion_tokens must be a nonnegative integer')
        need(st < 10 or ct is not None, f'{cid}: states 10-13 need completion_tokens')
        need(rec.get('halt') is None or isinstance(rec['halt'], str), f'{cid}: halt')
        if st == 13:
            raw = files.get(rec.get('output_file'))
            need(raw is not None and sha_bytes(raw) == rec.get('output_sha256'), f'{cid}: output sha256')
        return rec

    recs = {cid: check_call(cid) for cid in calls}
    if not manifest['typed_testable']:
        need(all(recs[f'{s}-FULL']['state'] in UNRUN for s in SLOTS), 'FULL released although untestable')

    scores = {}

    def adjudicated(cid, s):
        out_raw = files[recs[cid]['output_file']]
        per = {}
        for role, model in ADJUDICATORS.items():
            adj = _json(files, f'{cid}.{role}.json', f'{cid} {role}: missing adjudication')
            need(adj.get('spec_version') == ADJ_VERSION, f'{cid} {role}: spec_version')
            who = adj.get('adjudicator', {})
            need(who.get('role') == role and who.get('model') == model and who.get('effort') == ADJ_EFFORT
                 and isinstance(who.get('session'), str) and who['session'], f'{cid} {role}: adjudicator identity')
            need(adj.get('call_id') == cid and adj.get('source_id') == manifest['sources'][s]['source_id'],
                 f'{cid} {role}: call_id/source_id binding')
            need(adj.get('output_sha256') == sha_bytes(out_raw), f'{cid} {role}: output_sha256 binding')
            need(adj.get('reference_sha256') == manifest['sources'][s]['reference_sha256'],
                 f'{cid} {role}: reference_sha256 binding')
            per[role] = score(refs[s], sources[s], json.loads(out_raw.decode('utf-8')), adj['mappings'],
                              cid.split('-')[1])
        return per

    def cells_for(arm, role):
        cells, typed = {}, []
        for s in SLOTS:
            cid, m = f'{s}-{arm}', manifest['sources'][s]
            rec = recs[cid]
            if rec['state'] in UNRUN:
                continue
            if rec['state'] == 13:
                sc = scores[cid][role]
                rels = []
                for rid, crit in sorted(m['relations'].items()):
                    v = sc['relations'][rid]['verdict']
                    need(not v.startswith('excluded'), f'{cid}: live relation {rid} scored as excluded')
                    rels.append(dict(key=f'{s}:{rid}', verdict=v, critical=crit))
                if arm == 'FULL':
                    need(set(sc['compounds']) == set(m['compounds']), f'{cid}: compound verdicts differ from manifest')
                    typed += [dict(verdict=sc['compounds'][c]['verdict'], critical=crit)
                              for c, crit in sorted(m['compounds'].items())]
                    typed += [dict(verdict='invented', critical=e['critical']) for e in sc['invented']]
                cells[s] = dict(status='valid', completion_tokens=rec['completion_tokens'], relations=rels)
            elif 10 <= rec['state'] <= 12:
                cells[s] = dict(status='failed', completion_tokens=rec['completion_tokens'],
                                relations=[dict(key=f'{s}:{rid}', verdict='cell_failed', critical=crit)
                                           for rid, crit in sorted(m['relations'].items())])
                typed += [dict(verdict='relation_failed', critical=crit) for crit in m['compounds'].values()]
        return cells, typed

    def unrun(arm):
        return {s: [dict(key=f'{s}:{rid}', critical=crit)
                    for rid, crit in sorted(manifest['sources'][s]['relations'].items())]
                for s in SLOTS if recs[f'{s}-{arm}']['state'] in UNRUN}

    def order_ok(arm):
        states = [recs[f'{s}-{arm}']['state'] for s in SLOTS]
        released = [st not in UNRUN for st in states]
        need(released == sorted(released, reverse=True), f'{arm}: a call was released after an unrun call')
        return states

    state = dict(halted_phase=None, opq_mechanical_fail=False, opq=None, typed_testable=manifest['typed_testable'],
                 full_mechanical_fail=False, full=None)
    report = dict(phases={})
    for arm in ARMS:
        states = order_ok(arm)
        halted = any(type(st) is int and st <= 9 or recs[f'{s}-{arm}'].get('halt')
                     for s, st in zip(SLOTS, states))
        mech = any(type(st) is int and (10 <= st <= 12 or recs[f'{s}-{arm}']['completion_tokens'] > HEADROOM_TOKENS)
                   for s, st in zip(SLOTS, states) if type(st) is int and st >= 10)
        released = [s for s, st in zip(SLOTS, states) if st not in UNRUN]
        if arm == 'FULL':
            opq_ok = state['opq'] is not None and state['opq'] == {'A1': 'pass', 'A2': 'pass'}
            if not (opq_ok and manifest['typed_testable'] and state['halted_phase'] is None):
                need(not released, 'FULL released without a complete OPQ pass under both adjudicators')
                break
            need(released or interim, 'FULL phase not run although OPQ passed and typed logic is testable')
            if not released:
                break
        for s in released:
            # A halted cell (row 9 or a RECON halt) is retained and described, never scored.
            if recs[f'{s}-{arm}']['state'] == 13 and not recs[f'{s}-{arm}'].get('halt'):
                scores[f'{s}-{arm}'] = adjudicated(f'{s}-{arm}', s)
        if halted:
            state['halted_phase'] = arm
            report['phases'][arm] = dict(halted=True)
            break
        key = 'opq' if arm == 'OPQ' else 'full'
        state[f'{key}_mechanical_fail'] = mech
        per = {}
        for role in ADJUDICATORS:
            cells, typed = cells_for(arm, role)
            todo = unrun(arm)
            if arm == 'OPQ':
                bar = bar_D(cells)[0] if not todo else None
                fut = futile('OPQ', cells, todo) if todo else None
            else:
                opq_cells, _ = cells_for('OPQ', role)
                bar = bar_T(cells, opq_cells, typed) if not todo else None
                n_unrun_c = sum(len(manifest['sources'][s]['compounds']) for s in todo)
                fut = futile('FULL', cells, todo, opq_cells, typed, n_unrun_c) if todo else None
            st = ('pass' if bar['pass'] else 'fail') if bar else ('unreachable' if fut else 'reachable')
            per[role] = dict(state=st, bar=bar)
        state[key] = {role: per[role]['state'] for role in ADJUDICATORS}
        report['phases'][arm] = per
    if 'FULL' not in report['phases']:
        need(interim or all(recs[f'{s}-FULL']['state'] in UNRUN for s in SLOTS),
             'FULL calls released after the run had stopped')
    if state['opq'] is None and state['halted_phase'] is None:
        raise SpecError('OPQ phase has no result')
    state['opq'] = state['opq'] or {'A1': 'reachable', 'A2': 'reachable'}
    state['full'] = state['full'] or {'A1': 'reachable', 'A2': 'reachable'}
    try:
        report['outcome'] = outcome(state)
    except SpecError:
        if not interim:
            raise
        report['outcome'] = None    # no stopping state yet: release the next call
    report['state'] = state
    pairs = {}
    for cid, per in scores.items():
        for rid in sorted(manifest['sources'][cid.split('-')[0]]['relations']):
            pairs.setdefault(cid.split('-')[1], []).append(
                (per['A1']['relations'][rid]['verdict'], per['A2']['relations'][rid]['verdict']))
    report['agreement'] = {arm: kappa(p) for arm, p in pairs.items()}
    report['scores'] = scores
    return report


# ---------------------------------------------------------------- CLI

def _load(path):
    with open(path, 'rb') as fh:
        return json.loads(fh.read().decode('utf-8'))


def main(argv):
    if len(argv) == 3 and argv[0] == 'validate-reference':
        ref, src = _load(argv[1]), open(argv[2], 'rb').read().decode('utf-8')
        validate_reference(ref, src)
        print(json.dumps(dict(ok=True, relations=len(ref['relations']), live=sum(live(r) for r in ref['relations']),
                              compounds=len(compounds(ref))), sort_keys=True))
        return 0
    if len(argv) in (2, 3) and argv[0] == 'decide' and argv[2:] in ([], ['--interim']):
        # DECISION.json: {"manifest": path, "calls": path, "files": {name: path}}
        spec = _load(argv[1])
        files = {}
        for name, path in spec['files'].items():
            with open(path, 'rb') as fh:
                files[name] = fh.read()
        report = decide(_load(spec['manifest']), _load(spec['calls']), files, interim=argv[2:] == ['--interim'])
        print(json.dumps(report, sort_keys=True, indent=1, default=sorted))
        return 0
    print('usage: r17score.py validate-reference REF SOURCE | decide DECISION.json [--interim]\n'
          '(per-output scoring is internal; the only decision entry point is decide)', file=sys.stderr)
    return 2


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except SpecError as exc:
        print(f'REJECTED: {exc}', file=sys.stderr)
        sys.exit(1)
