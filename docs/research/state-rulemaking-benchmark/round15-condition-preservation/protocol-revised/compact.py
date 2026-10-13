"""R15 offline source-linked condition inventory; no execution or logic evaluation."""
import copy
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERSION = 'r15.1'
SPAN_VERSION = 'r15.spans.2'
EXPANDED_VERSION = 'round15.expanded-inventory.v2'
RAW_LIMIT = 600000
PARSER_DEPTH = 64
KINDS = ['identity', 'rule_transition', 'phase', 'timing', 'endpoint', 'endpoint_role', 'instruction', 'relationship', 'background']
MODALITIES = ['informational', 'mandatory', 'advisory', 'optional', 'prohibited', 'unknown', 'not_applicable']
UNCERTAINTIES = ['none', 'source_ambiguous', 'reference_unresolved', 'function_unresolved']
APPLICABILITY = ['none_reported', 'reported_nonexhaustive', 'unknown']
OPS = ['L', 'R', 'AND', 'OR', 'NOT', 'EXC', 'ALT']
ROLES = ['if', 'onlyif', 'unless', 'regardless', 'obj', 'acts', 'qual']
STATES = ['stated', 'absent', 'ambiguous', 'na']
UNIT_KEYS = ['i', 'k', 's', 'm', 'p', 'y', 'd', 'b', 'e', 'q', 'r']
NODE_KEYS = ['i', 'o', 'a', 'x', 'g', 'q', 'r']
LINK_KEYS = ['u', 'w', 'n', 'x', 'q', 'r']
ENVELOPE_KEYS = ['v', 'h', 't', 'u', 'g', 'l', 'z']


def require(ok, code):
    if not ok:
        raise ValueError(code)


def unicode_depth(value):
    stack = [(value, 0)]
    while stack:
        item, depth = stack.pop()
        if isinstance(item, str):
            require(not any(0xD800 <= ord(c) <= 0xDFFF for c in item), 'unpaired_surrogate')
        elif isinstance(item, (dict, list)):
            depth += 1
            require(depth <= PARSER_DEPTH, 'parser_depth')
            if isinstance(item, dict):
                stack.extend((key, depth) for key in item)
                stack.extend((v, depth) for v in item.values())
            else:
                stack.extend((v, depth) for v in item)


def canonical(value):
    unicode_depth(value)
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    except (TypeError, OverflowError, UnicodeError, RecursionError) as exc:
        raise ValueError('canonical_encoding') from exc


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def source_hash(source):
    require(isinstance(source, str), 'source_type')
    unicode_depth(source)
    return hashlib.sha256(source.encode('utf-8')).hexdigest()


def closed(obj, keys):
    require(isinstance(obj, dict) and set(obj) == set(keys), 'closed_keys')


def integer(value, low, high, code='integer_range'):
    require(type(value) is int and low <= value <= high, code)


def text(value, cap, empty=True):
    require(isinstance(value, str), 'text_type')
    unicode_depth(value)
    require(len(value) <= cap and ((empty and value == '') or bool(value.strip())), 'text_bound')


def array(value, low, high):
    require(isinstance(value, list) and low <= len(value) <= high, 'array_bound')


def uncertainty(obj):
    integer(obj['q'], 0, 3)
    text(obj['r'], 180)
    require((obj['q'] == 0) == (obj['r'] == ''), 'uncertainty_reason')


def node_id(value):
    require(isinstance(value, str) and re.fullmatch(r'c[1-9][0-9]{0,2}', value) is not None, 'node_id')
    require(int(value[1:]) <= 400, 'node_id_range')


def raw_guard(raw):
    require(isinstance(raw, str), 'raw_text_type')
    unicode_depth(raw)
    require(len(raw.encode('utf-8')) <= RAW_LIMIT, 'raw_size')
    depth = 0
    quoted = False
    escaped = False
    for char in raw:
        if quoted:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in '[{':
            depth += 1
            require(depth <= PARSER_DEPTH, 'parser_depth')
        elif char in ']}':
            depth -= 1
            require(depth >= 0, 'json_nesting')


def strict_load(raw):
    raw_guard(raw)
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate_key')
            result[key] = value
        return result
    def constant(_):
        raise ValueError('nonfinite_constant')
    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (RecursionError, OverflowError) as exc:
        raise ValueError('json_resource') from exc
    canonical(value)  # Reject numeric overflow and escaped unpaired surrogates.
    return value


def span_table(source):
    source_hash(source)
    require(bool(source.strip()), 'nonempty_source')
    rows = []
    start = 0
    for index, part in enumerate(source.splitlines(keepends=True), 1):
        rows.append([f's{index}', start, start + len(part), part])
        start += len(part)
    require(start == len(source), 'partition_coverage')
    return dict(v=SPAN_VERSION, h=source_hash(source), rows=rows)


def validate_table(source, table):
    require(canonical(table) == canonical(span_table(source)), 'exact_host_table')


def reconstruct(source, table):
    validate_table(source, table)
    result = ''.join(row[3] for row in table['rows'])
    require(result.encode('utf-8') == source.encode('utf-8'), 'source_reconstruction')
    return result


def resolve_fragment(fragment, source, table):
    """Resolve exact overlapping head occurrence, then tail conditional on that head."""
    array(fragment, 6, 6)
    a, head, head_occ, z, tail, tail_occ = fragment
    rows = {row[0]: (i, row) for i, row in enumerate(table['rows'])}
    require(isinstance(a, str) and a in rows and isinstance(z, str) and z in rows, 'fragment_span')
    text(head, 48, False)
    text(tail, 48, False)
    require(type(head_occ) is int and head_occ >= 1, 'head_occurrence')
    require(type(tail_occ) is int and tail_occ >= 1, 'tail_occurrence')
    ai, A = rows[a]
    zi, Z = rows[z]
    require(zi >= ai, 'fragment_row_order')
    heads = [j for j in range(len(A[3])) if A[3].startswith(head, j)]
    require(head_occ <= len(heads), 'head_not_found')
    start = A[1] + heads[head_occ - 1]
    tails = [k for k in range(len(Z[3])) if Z[3].startswith(tail, k)
             and Z[1] + k >= start and Z[1] + k + len(tail) >= start + len(head)]
    require(tail_occ <= len(tails), 'tail_not_found')
    end = Z[1] + tails[tail_occ - 1] + len(tail)
    return dict(fragment=copy.deepcopy(fragment), a=a, z=z, start=start, end=end, text=source[start:end])


def fragments(value, low, high, source, table):
    array(value, low, high)
    evidence = [resolve_fragment(f, source, table) for f in value]
    for previous, current in zip(evidence, evidence[1:]):
        require(current['start'] > previous['start'] and current['start'] >= previous['end'], 'fragment_order_overlap')
    return evidence


def dimension(value, name, source, table):
    closed(value, ['s', 'x', 'r'])
    require(value['s'] in STATES, 'dimension_state')
    text(value['r'], 180)
    if value['s'] == 'absent':
        fragments(value['x'], 0, 0, source, table)
    else:
        fragments(value['x'], 1, 4, source, table)
    if value['s'] in ['ambiguous', 'na']:
        require(bool(value['r']), 'dimension_reason')
    require(value['s'] != 'na' or name == 'b', 'dimension_na_basis_only')


def validate(value, source, table, finish_reason='stop'):
    require(finish_reason == 'stop', 'non_stop')
    require(len(canonical(value)) <= RAW_LIMIT, 'raw_size')
    validate_table(source, table)
    closed(value, ENVELOPE_KEYS)
    require(value['v'] == VERSION and value['h'] == source_hash(source) and value['t'] == digest(table), 'binding_version')
    require(value['z'] == 'END', 'terminal_marker')
    for key, low, sentinel in [('u', 1, 160), ('g', 0, 400), ('l', 0, 400)]:
        array(value[key], low, sentinel)
        require(len(value[key]) < sentinel, 'capacity_review_' + key)
    span_ids = {row[0] for row in table['rows']}
    units = {}
    for u in value['u']:
        closed(u, UNIT_KEYS)
        for key, low, high in [('i', 1, 160), ('k', 0, 8), ('m', 0, 6), ('p', 0, 2)]:
            integer(u[key], low, high)
        require(u['i'] not in units, 'duplicate_unit')
        units[u['i']] = u
        text(u['s'], 280, False)
        uncertainty(u)
        require(u['m'] != 5 or u['q'] != 0, 'unknown_modality')
        require(u['p'] != 2 or u['q'] != 0, 'unknown_applicability')
        for key in ['d', 'b']:
            array(u[key], 0, 16)
            for uid in u[key]:
                integer(uid, 1, 160)
            require(len(u[key]) == len(set(u[key])), 'duplicate_unit_reference')
        array(u['e'], 1, 6)
        require(all(isinstance(e, str) and e in span_ids for e in u['e']), 'evidence_id')
        require(len(u['e']) == len(set(u['e'])), 'duplicate_evidence')
        if u['y'] is not None:
            require(u['k'] == 3, 'deadline_kind')
            closed(u['y'], ['c', 'z', 'b'])
            for name, dim in u['y'].items():
                dimension(dim, name, source, table)
            require(not any(dim['s'] in ['absent', 'ambiguous'] for dim in u['y'].values()) or u['q'] != 0, 'deadline_uncertainty')
    done = set()
    visiting = set()
    def unit_visit(uid):
        require(uid in units, 'dangling_unit_reference')
        require(uid not in visiting, 'unit_cycle')
        if uid in done:
            return
        visiting.add(uid)
        for dep in units[uid]['d']:
            unit_visit(dep)
        visiting.remove(uid)
        done.add(uid)
    for uid, u in units.items():
        unit_visit(uid)
        require(all(b in units for b in u['b']), 'dangling_member')
        if u['k'] == 7:
            require(len(u['b']) >= 2 and uid not in u['b'], 'relationship_members')
        else:
            require(u['b'] == [], 'members_on_nonrelationship')
        if u['k'] == 5:
            require(bool(u['d']) and units[u['d'][0]]['k'] == 4, 'role_endpoint')
    nodes = {}
    for node in value['g']:
        closed(node, NODE_KEYS)
        node_id(node['i'])
        require(node['i'] not in nodes, 'duplicate_node')
        nodes[node['i']] = node
        require(node['o'] in OPS, 'node_operator')
        uncertainty(node)
        text(node['g'], 120)
        array(node['a'], 0, 8)
        for child in node['a']:
            node_id(child)
        require(len(node['a']) == len(set(node['a'])) and node['i'] not in node['a'], 'duplicate_self_child')
        size = len(node['a'])
        require((node['o'] in ['L', 'R'] and size == 0) or (node['o'] == 'NOT' and size == 1)
                or (node['o'] == 'EXC' and size == 2) or (node['o'] in ['AND', 'OR', 'ALT'] and 2 <= size <= 8), 'node_arity')
        require(node['o'] != 'R' or node['q'] == 2, 'reference_uncertainty')
        require(node['o'] != 'ALT' or node['q'] == 1, 'alternative_uncertainty')
        fragments(node['x'], 1 if node['o'] in ['L', 'R'] else 0, 8 if node['o'] in ['L', 'R'] else 4, source, table)
    triples = set()
    restricted = set()
    applicability_counts = {uid: 0 for uid in units}
    for link in value['l']:
        closed(link, LINK_KEYS)
        integer(link['u'], 1, 160)
        node_id(link['n'])
        require(link['u'] in units and link['n'] in nodes, 'dangling_link')
        require(link['w'] in ROLES, 'link_role')
        uncertainty(link)
        require(link['w'] != 'qual' or (link['q'] != 0 and units[link['u']]['p'] == 2), 'qual_requires_unknown_scope')
        fragments(link['x'], 0, 2, source, table)
        triple = (link['u'], link['w'], link['n'])
        require(triple not in triples, 'duplicate_link')
        triples.add(triple)
        if link['w'] in ['if', 'onlyif', 'unless', 'obj']:
            role = (link['u'], link['w'])
            require(role not in restricted, 'role_cardinality')
            restricted.add(role)
        if link['w'] in ['if', 'onlyif', 'unless']:
            applicability_counts[link['u']] += 1
    for uid, u in units.items():
        A = applicability_counts[uid]
        require(u['p'] == 2 or (u['p'] == 0 and A == 0) or (u['p'] == 1 and A >= 1), 'applicability_links')
    depths = {}
    visiting = set()
    # Explicit DFS enter/exit frames preserve child order and postorder memoization
    # without consuming Python recursion frames for the bounded condition graph.
    for root in nodes:
        if root in depths:
            continue
        walk = [(root, False)]
        while walk:
            nid, exiting = walk.pop()
            require(nid in nodes, 'dangling_child')
            if exiting:
                depths[nid] = 1 + max((depths[child] for child in nodes[nid]['a']), default=0)
                visiting.remove(nid)
                continue
            require(nid not in visiting, 'node_cycle')
            if nid in depths:
                continue
            visiting.add(nid)
            walk.append((nid, True))
            walk.extend((child, False) for child in reversed(nodes[nid]['a']))
    reached = set()
    stack = [link['n'] for link in value['l']]
    for nid in stack:
        require(depths[nid] <= 12, 'graph_depth')
    while stack:
        nid = stack.pop()
        if nid not in reached:
            reached.add(nid)
            stack.extend(nodes[nid]['a'])
    require(reached == set(nodes), 'orphan_node')
    return value


def schema(source, table):
    validate_table(source, table)
    def obj(properties):
        return dict(type='object', properties=properties, required=list(properties), additionalProperties=False)
    def string(cap, low=0):
        return dict(type='string', minLength=low, maxLength=cap)
    def enum(values):
        return dict(type='string', enum=values)
    def integer_schema(low, high):
        return dict(type='integer', minimum=low, maximum=high)
    def arr(items, low, high):
        return dict(type='array', items=items, minItems=low, maxItems=high)
    sid = enum([row[0] for row in table['rows']])
    nid = dict(type='string', pattern=r'^c[1-9][0-9]{0,2}$')
    # Offline JSON Schema 2020-12 positional tuple. Provider dialect support UNVERIFIED.
    frag = dict(type='array', prefixItems=[sid, string(48, 1), dict(type='integer', minimum=1), sid, string(48, 1), dict(type='integer', minimum=1)], items=False, minItems=6, maxItems=6)
    dim = obj({'s': enum(STATES), 'x': arr(frag, 0, 4), 'r': string(180)})
    deadline = obj({'c': dim, 'z': dim, 'b': dim})
    unit = obj({'i': integer_schema(1, 160), 'k': integer_schema(0, 8), 's': string(280, 1), 'm': integer_schema(0, 6),
                'p': integer_schema(0, 2), 'y': {'anyOf': [deadline, {'type': 'null'}]},
                'd': arr(integer_schema(1, 160), 0, 16), 'b': arr(integer_schema(1, 160), 0, 16), 'e': arr(sid, 1, 6), 'q': integer_schema(0, 3), 'r': string(180)})
    node = obj({'i': nid, 'o': enum(OPS), 'a': arr(nid, 0, 8), 'x': arr(frag, 0, 8), 'g': string(120), 'q': integer_schema(0, 3), 'r': string(180)})
    link = obj({'u': integer_schema(1, 160), 'w': enum(ROLES), 'n': nid, 'x': arr(frag, 0, 2), 'q': integer_schema(0, 3), 'r': string(180)})
    result = obj({'v': enum([VERSION]), 'h': enum([source_hash(source)]), 't': enum([digest(table)]), 'u': arr(unit, 1, 160), 'g': arr(node, 0, 400), 'l': arr(link, 0, 400), 'z': enum(['END'])})
    result['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
    return result


def span_evidence(ids, source, table):
    rows = {row[0]: row for row in table['rows']}
    output = []
    for sid in ids:
        _, start, end, quote = rows[sid]
        occurrence = sum(source.startswith(quote, pos) for pos in range(start + 1))
        output.append(dict(span_id=sid, start=start, end=end, quote=quote, occurrence=occurrence))
    return output


def expand(value, source, table, finish_reason='stop'):
    validate(value, source, table, finish_reason)
    def evidence(x):
        return [resolve_fragment(f, source, table) for f in x]
    def deadline(y):
        if y is None:
            return None
        return {key: dict(state=dim['s'], evidence=evidence(dim['x']), reason=dim['r']) for key, dim in y.items()}
    links = [dict(unit_id=l['u'], role=l['w'], node_id=l['n'], evidence=evidence(l['x']), q=l['q'], r=l['r']) for l in value['l']]
    nodes = [dict(id=n['i'], op=n['o'], args=copy.deepcopy(n['a']), evidence=evidence(n['x']), model_gloss=n['g'], q=n['q'], r=n['r'], unresolved_reference=n['o'] == 'R') for n in value['g']]
    units = [dict(id=u['i'], kind=KINDS[u['k']], assertion=u['s'], modality=MODALITIES[u['m']], applicability=APPLICABILITY[u['p']], deadline=deadline(u['y']),
                  required_unit_ids=copy.deepcopy(u['d']), relationship_member_ids=copy.deepcopy(u['b']), evidence=span_evidence(u['e'], source, table),
                  uncertainty=UNCERTAINTIES[u['q']], uncertainty_reason=u['r'], condition_links=copy.deepcopy([l for l in links if l['unit_id'] == u['i']])) for u in value['u']]
    return dict(schema_version=EXPANDED_VERSION, source_text_sha256=value['h'], span_table_sha256=value['t'], units=units, nodes=nodes, links=links, terminal_marker=value['z'],
                completeness='unverified', condition_coverage='unverified', semantic_validity='unverified', evaluation='not_performed', production_eligible=False, action_ready=False, evidence_match='exact')


def contract(value, source, table):
    closed(value, ['schema_version', 'source_text_sha256', 'span_table_sha256', 'units', 'nodes', 'links', 'terminal_marker', 'completeness', 'condition_coverage', 'semantic_validity', 'evaluation', 'production_eligible', 'action_ready', 'evidence_match'])
    require(value['schema_version'] == EXPANDED_VERSION, 'expanded_version')
    for key in ['units', 'nodes', 'links']:
        array(value[key], 0, 400)
    def inverse_evidence(evs):
        array(evs, 0, 8)
        for ev in evs:
            closed(ev, ['fragment', 'a', 'z', 'start', 'end', 'text'])
        return [copy.deepcopy(ev['fragment']) for ev in evs]
    def inverse_deadline(y):
        if y is None:
            return None
        closed(y, ['c', 'z', 'b'])
        result = {}
        for key, dim in y.items():
            closed(dim, ['state', 'evidence', 'reason'])
            result[key] = dict(s=dim['state'], x=inverse_evidence(dim['evidence']), r=dim['reason'])
        return result
    def code(name, values):
        require(isinstance(name, str) and name in values, 'expanded_enum')
        return values.index(name)
    units = []
    for u in value['units']:
        closed(u, ['id', 'kind', 'assertion', 'modality', 'applicability', 'deadline', 'required_unit_ids', 'relationship_member_ids', 'evidence', 'uncertainty', 'uncertainty_reason', 'condition_links'])
        array(u['evidence'], 1, 6)
        for ev in u['evidence']:
            closed(ev, ['span_id', 'start', 'end', 'quote', 'occurrence'])
        units.append(dict(i=u['id'], k=code(u['kind'], KINDS), s=u['assertion'], m=code(u['modality'], MODALITIES), p=code(u['applicability'], APPLICABILITY), y=inverse_deadline(u['deadline']),
                          d=copy.deepcopy(u['required_unit_ids']), b=copy.deepcopy(u['relationship_member_ids']), e=[ev['span_id'] for ev in u['evidence']], q=code(u['uncertainty'], UNCERTAINTIES), r=u['uncertainty_reason']))
    nodes = []
    for n in value['nodes']:
        closed(n, ['id', 'op', 'args', 'evidence', 'model_gloss', 'q', 'r', 'unresolved_reference'])
        nodes.append(dict(i=n['id'], o=n['op'], a=copy.deepcopy(n['args']), x=inverse_evidence(n['evidence']), g=n['model_gloss'], q=n['q'], r=n['r']))
    links = []
    for l in value['links']:
        closed(l, ['unit_id', 'role', 'node_id', 'evidence', 'q', 'r'])
        links.append(dict(u=l['unit_id'], w=l['role'], n=l['node_id'], x=inverse_evidence(l['evidence']), q=l['q'], r=l['r']))
    result = dict(v=VERSION, h=value['source_text_sha256'], t=value['span_table_sha256'], u=units, g=nodes, l=links, z=value['terminal_marker'])
    expected = expand(result, source, table)
    require(canonical(expected) == canonical(value), 'expanded_field_evidence_equality')
    return result


def build(source):
    table = span_table(source)
    user = dict(source_text=source, source_text_sha256=source_hash(source), span_table=table, span_table_sha256=digest(table))
    body = strict_load((ROOT / 'request-settings.json').read_text())
    body.update(messages=[dict(role='system', content=(ROOT / 'stage-a.system.txt').read_text()), dict(role='user', content=canonical(user).decode('utf-8'))],
                response_format=dict(type='json_schema', json_schema=dict(name='condition_inventory', strict=True, schema=schema(source, table))))
    raw = canonical(body)
    require(len(raw) + 1024 <= 40000, 'full_request_overflow')
    return dict(body=body, table=table, body_bytes=len(raw), guarded_bytes=len(raw) + 1024, request_sha256=hashlib.sha256(raw).hexdigest())


def validate_response(raw_content, finish_reason, source, table):
    require(finish_reason == 'stop', 'non_stop')
    value = strict_load(raw_content)
    validate(value, source, table, finish_reason)
    return dict(compact=value, expanded=expand(value, source, table, finish_reason))
