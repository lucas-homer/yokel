"""R16 wire-compat DESIGN PROBE. Offline, read-only on all inputs, no provider calls, no credentials.

Measures the proposed object-fragment wire (DESIGN.md) against the UNCHANGED R14 runtime checker
and the frozen r15.1 codec. A design aid, not the implementation: an implementer should rewrite the
codec as a pinned, reviewed module. Prints one JSON report to stdout; writes nothing.

    python3 -I -B probe.py > probe-results.json
"""
import copy
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parents[1]
R15 = BENCH / 'round15-condition-preservation'
PROTO = R15 / 'protocol-revised'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


k = load('r15_1_compact', PROTO / 'compact.py')                                        # frozen r15.1
c = load('r14_common', BENCH / 'round14-semantic-contract/runtime/common.py')          # unchanged checker

WIRE_VERSION = 'r16.w1'
FRAG_KEYS = ['a', 'h', 'ho', 'z', 't', 'to']


# ---------------------------------------------------------------- schema (checker dialect only)
def wire_schema(source, table):
    k.validate_table(source, table)
    def obj(properties):
        return dict(type='object', properties=properties, required=list(properties), additionalProperties=False)
    def string(cap, low=0):
        return dict(type='string', minLength=low, maxLength=cap)
    def enum(values):
        return dict(type='string', enum=values)
    def integer(low, high=None):
        return dict(type='integer', minimum=low) if high is None else dict(type='integer', minimum=low, maximum=high)
    def arr(items, low, high):
        return dict(type='array', items=items, minItems=low, maxItems=high)
    sid = string(max(len(row[0]) for row in table['rows']), 2)   # membership: host (compact.py:166,233)
    nid = string(4, 2)                                            # c1..c400 syntax/range: host (compact.py:90-92)
    frag = obj({'a': sid, 'h': string(48, 1), 'ho': integer(1), 'z': sid, 't': string(48, 1), 'to': integer(1)})
    dim = obj({'s': enum(k.STATES), 'x': arr(frag, 0, 4), 'r': string(180)})
    deadline = obj({'c': dim, 'z': dim, 'b': dim})
    unit = obj({'i': integer(1, 160), 'k': integer(0, 8), 's': string(280, 1), 'm': integer(0, 6), 'p': integer(0, 2),
                'y': arr(deadline, 0, 1), 'd': arr(integer(1, 160), 0, 16), 'b': arr(integer(1, 160), 0, 16),
                'e': arr(sid, 1, 6), 'q': integer(0, 3), 'r': string(180)})
    node = obj({'i': nid, 'o': enum(k.OPS), 'a': arr(nid, 0, 8), 'x': arr(frag, 0, 8), 'g': string(120), 'q': integer(0, 3), 'r': string(180)})
    link = obj({'u': integer(1, 160), 'w': enum(k.ROLES), 'n': nid, 'x': arr(frag, 0, 2), 'q': integer(0, 3), 'r': string(180)})
    return obj({'v': enum([WIRE_VERSION]), 'h': enum([k.source_hash(source)]), 't': enum([k.digest(table)]),
                'u': arr(unit, 1, 160), 'g': arr(node, 0, 400), 'l': arr(link, 0, 400), 'z': enum(['END'])})


# ---------------------------------------------------------------- ALTERNATIVE A0 (measured, not recommended)
def tuple_schema(source, table):
    """A0: r15.1 tuples kept; homogeneous string-or-integer items; y nullable via type list.
    Positional typing and y shape become host-only; uses union forms with no repo evidence of provider acceptance."""
    s = wire_schema(source, table)
    unit = s['properties']['u']['items']
    deadline = unit['properties']['y']['items']
    deadline['type'] = ['object', 'null']
    unit['properties']['y'] = deadline
    slot = dict(type=['string', 'integer'], minLength=1, maxLength=48, minimum=1)
    tup = dict(type='array', items=slot, minItems=6, maxItems=6)
    for dim in deadline['properties'].values():
        dim['properties']['x']['items'] = tup
    for key in ['g', 'l']:
        s['properties'][key]['items']['properties']['x']['items'] = tup
    s['properties']['v']['enum'] = ['r16.t1']
    return s


def to_tuple_wire(C):
    W = copy.deepcopy(C)
    W['v'] = 'r16.t1'
    return W


# ---------------------------------------------------------------- bijection wire <-> r15.1 compact
def frag_to_wire(f):
    return dict(zip(FRAG_KEYS, copy.deepcopy(f)))


def frag_from_wire(o):
    k.require(isinstance(o, dict) and set(o) == set(FRAG_KEYS), 'wire_fragment_keys')
    return [copy.deepcopy(o[key]) for key in FRAG_KEYS]


def frags_from_wire(xs):
    k.require(isinstance(xs, list), 'wire_fragment_list')
    return [frag_from_wire(o) for o in xs]


def to_wire(C):
    W = copy.deepcopy(C)
    W['v'] = WIRE_VERSION
    for u in W['u']:
        y = u['y']
        if y is not None:
            for dim in y.values():
                dim['x'] = [frag_to_wire(f) for f in dim['x']]
        u['y'] = [] if y is None else [y]
    for item in W['g'] + W['l']:
        item['x'] = [frag_to_wire(f) for f in item['x']]
    return W


def from_wire(W):
    """Pure structural inverse; every non-mapped field is copied unchanged and judged by r15.1 validate."""
    k.require(isinstance(W, dict) and set(W) == set(k.ENVELOPE_KEYS), 'wire_envelope_keys')
    k.require(W['v'] == WIRE_VERSION, 'wire_version')
    C = copy.deepcopy(W)
    C['v'] = k.VERSION
    for key in ['u', 'g', 'l']:
        k.require(isinstance(C[key], list), 'wire_array')
    for u in C['u']:
        k.require(isinstance(u, dict) and 'y' in u and isinstance(u['y'], list) and len(u['y']) <= 1, 'wire_deadline_slot')
        y = u['y'][0] if u['y'] else None
        if y is not None:
            k.require(isinstance(y, dict) and set(y) == {'c', 'z', 'b'}, 'wire_deadline_keys')
            for dim in y.values():
                k.require(isinstance(dim, dict) and 'x' in dim, 'wire_dimension')
                dim['x'] = frags_from_wire(dim['x'])
        u['y'] = y
    for item in C['g'] + C['l']:
        k.require(isinstance(item, dict) and 'x' in item, 'wire_item')
        item['x'] = frags_from_wire(item['x'])
    return C


# ---------------------------------------------------------------- corpus
def corpus():
    cases = []
    src = (PROTO / 'fixtures/source.txt').read_bytes().decode('utf-8')   # bytes: read_text() would normalize CRLF
    cases.append(('fixtures/positive', src, json.loads((PROTO / 'fixtures/positive.json').read_text())))
    for name, wire in json.loads((PROTO / 'fixtures/semantic-negatives.json').read_text()).items():
        cases.append(('fixtures/semantic-negative/' + name, src, wire))
    for g in sorted((PROTO / 'fixtures').glob('long_*-graph.json')):
        stem = g.name[:-len('-graph.json')]
        cases.append(('fixtures/' + stem, (PROTO / 'fixtures' / (stem + '-source.txt')).read_bytes().decode('utf-8'), json.loads(g.read_text())))
    for p in json.loads((R15 / 'sizing/authored-profiles.json').read_text())['profiles']:
        wire = copy.deepcopy(p['wire'])   # r15.0 -> r15.1: version/table-hash translation only (as sizing/revised did)
        wire['v'] = k.VERSION
        wire['t'] = k.digest(k.span_table(p['source']))
        cases.append(('sizing/' + p['id'], p['source'], wire))
    for ctl in json.loads((R15 / 'sizing/revised/authored-controls.json').read_text())['controls']:
        cases.append(('revised-control/' + ctl['id'], ctl['source'], ctl['wire']))
    return cases


def err(fn, *args):
    try:
        fn(*args)
        return None
    except (ValueError, c.Denied) as exc:
        return str(exc)


def roundtrip(label, source, C):
    table = k.span_table(source)
    ws = wire_schema(source, table)
    c.check_schema(ws)
    direct = err(k.validate, C, source, table)
    W = to_wire(C)
    schema = c.schema_errors(W, ws)
    back = from_wire(W)
    nfrag = sum(len(i['x']) for i in C['g'] + C['l']) + sum(len(d['x']) for u in C['u'] if u['y'] for d in u['y'].values())
    ndead = sum(u['y'] is not None for u in C['u'])
    row = dict(case=label, fragments=nfrag, deadlines=ndead, null_deadlines=len(C['u']) - ndead, r15_valid=direct is None, r15_error=direct, wire_schema_errors=schema[:5],
               compact_bytes=len(k.canonical(C)), wire_bytes=len(k.canonical(W)),
               bijection_exact=k.canonical(back) == k.canonical(C))
    a0 = tuple_schema(source, table)
    c.check_schema(a0)
    row['a0_tuple_schema_errors'] = c.schema_errors(to_tuple_wire(C), a0)[:5]
    row['a0_wire_bytes'] = len(k.canonical(to_tuple_wire(C)))
    via_wire = err(k.validate, back, source, table)
    row['same_host_verdict'] = via_wire == direct
    if direct is None:
        E = k.expand(C, source, table)
        row['expanded_equal'] = k.canonical(k.expand(back, source, table)) == k.canonical(E)
        row['contract_to_wire_equal'] = k.canonical(to_wire(k.contract(E, source, table))) == k.canonical(W)
        row['false_schema_rejection'] = bool(schema)
    return row


# ---------------------------------------------------------------- sizing
PROMPT_EDITS = [   # draft model-facing edits; each `old` must occur exactly once
    ('Emit one complete closed r15.1 envelope', 'Emit one complete closed r16.w1 envelope'),
    ('Every fragment x item is [startSpan,head,headOccurrence,endSpan,tail,tailOccurrence].',
     'Every fragment x item is an object {a,h,ho,z,t,to}: a startSpan ID, h head, ho headOccurrence, z endSpan ID, t tail, to tailOccurrence; all six keys required.'),
    ('y=null unless k3 and assertion is a deadline;', 'y=[] unless k3 and assertion is a deadline;'),
    ('Deadline y has c(clock)', 'A deadline y is a one-item list [{c,z,b}]: c(clock)'),
    ('A null deadline is a claim', 'An empty y is a claim'),
]


def system_prompt(edit):
    text = (PROTO / 'stage-a.system.txt').read_text()
    if edit:
        for old, new in PROMPT_EDITS:
            k.require(text.count(old) == 1, 'prompt_edit_anchor')
            text = text.replace(old, new)
    return text


def request_bytes(source, schema_fn, edit, rows_only=False):
    table = k.span_table(source)
    user = dict(source_text=source, source_text_sha256=k.source_hash(source), span_table=table, span_table_sha256=k.digest(table))
    if rows_only:   # OUT-OF-SCOPE envelope option, measured only: rows already concatenate to the exact source
        del user['source_text']
    body = k.strict_load((PROTO / 'request-settings.json').read_text())
    body.update(messages=[dict(role='system', content=system_prompt(edit)), dict(role='user', content=k.canonical(user).decode('utf-8'))],
                response_format=dict(type='json_schema', json_schema=dict(name='condition_inventory', strict=True, schema=schema_fn(source, table))))
    raw = c.encode(body)
    schema = schema_fn(source, table)
    return dict(spans=len(table['rows']), source_bytes=len(source.encode()), schema_bytes=len(c.encode(schema)),
                user_message_bytes=len(c.encode(body['messages'][1]['content'])), system_prompt_bytes=len(c.encode(body['messages'][0]['content'])),
                body_bytes=len(raw), guarded_bytes=len(raw) + 1024, under_guard=len(raw) + 1024 <= 40000,
                r14_checker_accepts_schema=err(c.check_schema, schema) is None)


def sizing():
    exposed = (BENCH / 'round14-semantic-contract/source/parsed-body.txt').read_bytes().decode()
    profiles = {p['id']: p['source'] for p in json.loads((R15 / 'sizing/authored-profiles.json').read_text())['profiles']}
    out = {}
    for label, source in [('prior_source_R14_parsed_body', exposed), ('disjoint600-u24', profiles['disjoint600-u24']),
                          ('disjoint160-u24', profiles['disjoint160-u24']), ('disjoint600-u8', profiles['disjoint600-u8'])]:
        out[label] = dict(r15_1=request_bytes(source, k.schema, False),
                          wire_schema_r15_prompt=request_bytes(source, wire_schema, False),
                          wire_schema_draft_prompt=request_bytes(source, wire_schema, True),
                          a0_tuple_schema_r15_prompt=request_bytes(source, tuple_schema, False),
                          envelope_option_rows_only_wire_draft_prompt=request_bytes(source, wire_schema, True, rows_only=True))
    return out


# ---------------------------------------------------------------- negative wire checks
def negatives():
    source = (PROTO / 'fixtures/source.txt').read_bytes().decode('utf-8')
    table = k.span_table(source)
    ws = wire_schema(source, table)
    W = to_wire(json.loads((PROTO / 'fixtures/positive.json').read_text()))
    first_node_with_frag = next(n for n in W['g'] if n['x'])
    def mutate(fn):
        X = copy.deepcopy(W)
        fn(X)
        return X
    def frag(X):
        return next(n for n in X['g'] if n['x'])['x'][0]
    cases = {
        'fragment_as_r15_tuple': lambda X: next(n for n in X['g'] if n['x'])['x'].__setitem__(0, frag_from_wire(first_node_with_frag['x'][0])),
        'fragment_missing_to': lambda X: frag(X).pop('to'),
        'fragment_extra_key': lambda X: frag(X).__setitem__('n', 1),
        'occurrence_zero': lambda X: frag(X).__setitem__('ho', 0),
        'occurrence_bool': lambda X: frag(X).__setitem__('ho', True),
        'occurrence_float': lambda X: frag(X).__setitem__('to', 1.0),
        'blank_head_empty': lambda X: frag(X).__setitem__('h', ''),
        'deadline_null_not_list': lambda X: X['u'][0].__setitem__('y', None),
        'deadline_two_items': lambda X: X['u'][0].__setitem__('y', [{}, {}]),
        'r15_version_on_wire': lambda X: X.__setitem__('v', k.VERSION),
        'span_id_overlong': lambda X: frag(X).__setitem__('a', 's' + '9' * 8),
        'span_id_absent_but_short': lambda X: frag(X).__setitem__('a', 's99'),
        'node_id_overlong': lambda X: X['l'][0].__setitem__('n', 'c0001'),
        'node_id_bad_prefix_short': lambda X: X['l'][0].__setitem__('n', 'x1'),
        'node_id_leading_zero_short': lambda X: X['l'][0].__setitem__('n', 'c01'),
        'node_id_out_of_range_short': lambda X: X['l'][0].__setitem__('n', 'c401'),
        'whitespace_head': lambda X: frag(X).__setitem__('h', '   '),
    }
    out = {}
    for name, fn in cases.items():
        X = mutate(fn)
        schema = c.schema_errors(X, ws)
        host = err(lambda: k.validate(from_wire(X), source, table))
        out[name] = dict(r14_checker_errors=schema[:3], host_error=host, rejected=bool(schema) or host is not None)
    return out


def main():
    exposed = (BENCH / 'round14-semantic-contract/source/parsed-body.txt').read_bytes().decode()
    t = k.span_table(exposed)
    rows = [roundtrip(*case) for case in corpus()]
    report = dict(
        label='R16 wire-compat design probe; authored fixtures only; no model output, provider call or semantic claim',
        r15_1_schema_rejected_by_r14_checker=err(c.check_schema, k.schema(exposed, t)) is not None,
        wire_schema_accepted_by_r14_checker=err(c.check_schema, wire_schema(exposed, t)) is None,
        roundtrip=dict(cases=len(rows),
                       valid=sum(r['r15_valid'] for r in rows),
                       all_bijective=all(r['bijection_exact'] for r in rows),
                       all_same_host_verdict=all(r['same_host_verdict'] for r in rows),
                       all_valid_expanded_equal=all(r.get('expanded_equal', True) for r in rows),
                       all_valid_contract_to_wire_equal=all(r.get('contract_to_wire_equal', True) for r in rows),
                       valid_false_schema_rejections=[r['case'] for r in rows if r.get('false_schema_rejection')],
                       a0_valid_false_schema_rejections=[r['case'] for r in rows if r['r15_valid'] and r['a0_tuple_schema_errors']],
                       invalid_cases=[(r['case'], r['r15_error'], r['wire_schema_errors'][:2]) for r in rows if not r['r15_valid']],
                       rows=rows),
        negatives=negatives(),
        sizing=sizing(),
        provider_calls=0)
    json.dump(report, sys.stdout, ensure_ascii=False, indent=1, sort_keys=True)
    print()


if __name__ == '__main__':
    main()
