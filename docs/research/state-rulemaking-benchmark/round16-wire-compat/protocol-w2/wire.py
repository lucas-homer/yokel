"""Offline r16.w2 revision: unchanged r16.w1 response, r16.e2 request envelope."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BENCH = ROOT.parents[1]
R15_ROOT = BENCH / 'round15-condition-preservation/protocol-revised'
COMMON_PATH = BENCH / 'round14-semantic-contract/runtime/common.py'
R15_READY_SHA256 = 'dd2bb510254e198589ed50caa6f9a171194a0971c11ae92bde996006267f1f50'
COMMON_SHA256 = 'a341e11b6b0d49b130c28d8881ef4b71748161bcfc0d15c41384bc150f35bdc5'
VERSION = 'r16.w1'
REVISION = 'r16.w2'
ENVELOPE_VERSION = 'r16.e2'
FRAGMENT_KEYS = ('a', 'h', 'ho', 'z', 't', 'to')


class WireError(ValueError):
    """A wire-level rejection. Frozen r15.1 ValueErrors pass through unchanged."""
    def __init__(self, code: str, details=None):
        self.code = code
        self.details = details
        super().__init__(code)


def _require(ok, code):
    if not ok:
        raise WireError(code)


def _pinned_bytes(path, expected):
    raw = path.read_bytes()
    _require(hashlib.sha256(raw).hexdigest() == expected, 'dependency_pin')
    return raw


_r15_ready = json.loads(_pinned_bytes(R15_ROOT / 'READY.json', R15_READY_SHA256))


def _r15_bytes(name):
    return _pinned_bytes(R15_ROOT / name, _r15_ready['sha256'][name])


def _load(name, path, raw):
    # Execute the verified bytes rather than reopening a potentially changed path.
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


r15 = _load('r16_frozen_r15_1', R15_ROOT / 'compact.py', _r15_bytes('compact.py'))
common = _load('r16_unchanged_r14_common', COMMON_PATH,
               _pinned_bytes(COMMON_PATH, COMMON_SHA256))


def _closed(value, keys, code):
    _require(isinstance(value, dict) and set(value) == set(keys), code)


def _array(value, code):
    _require(isinstance(value, list), code)


def _fragment_to_compact(value):
    _closed(value, FRAGMENT_KEYS, 'wire_fragment_keys')
    return [_fresh(value[key]) for key in FRAGMENT_KEYS]


def _fragment_from_compact(value):
    _require(isinstance(value, list) and len(value) == 6, 'compact_fragment_shape')
    return {key: _fresh(child) for key, child in zip(FRAGMENT_KEYS, value)}


def _fresh(value):
    # Deliberately no memo: each occurrence gets independent containers.
    if isinstance(value, dict):
        return {key: _fresh(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_fresh(child) for child in value]
    return copy.deepcopy(value)


def _map_fragments(item, convert):
    _array(item['x'], 'wire_fragment_list')
    return {key: ([convert(fragment) for fragment in child] if key == 'x'
                  else _fresh(child)) for key, child in item.items()}


def _map(value, to_wire):
    _closed(value, r15.ENVELOPE_KEYS, 'wire_envelope_keys')
    _require(value['v'] == (r15.VERSION if to_wire else VERSION), 'wire_version')
    result = {key: _fresh(child) for key, child in value.items()
              if key not in ('u', 'g', 'l')}
    result['v'] = VERSION if to_wire else r15.VERSION
    for key in ('u', 'g', 'l'):
        _array(value[key], 'wire_array')
        result[key] = []
    convert = _fragment_from_compact if to_wire else _fragment_to_compact
    for unit in value['u']:
        _closed(unit, r15.UNIT_KEYS, 'wire_unit_keys')
        mapped_unit = {key: _fresh(child) for key, child in unit.items() if key != 'y'}
        deadline = unit['y']
        if not to_wire:
            _require(isinstance(deadline, list) and len(deadline) <= 1,
                     'wire_deadline_slot')
            # [null] is not [] and cannot silently normalize to it.
            if deadline:
                _require(isinstance(deadline[0], dict), 'wire_deadline_keys')
            deadline = deadline[0] if deadline else None
        if deadline is not None:
            _closed(deadline, ('c', 'z', 'b'), 'wire_deadline_keys')
            mapped_deadline = {}
            for key, dimension in deadline.items():
                _closed(dimension, ('s', 'x', 'r'), 'wire_dimension_keys')
                mapped_deadline[key] = _map_fragments(dimension, convert)
            deadline = mapped_deadline
        mapped_unit['y'] = ([] if deadline is None else [deadline]) if to_wire else deadline
        result['u'].append(mapped_unit)
    for key, keys in (('g', r15.NODE_KEYS), ('l', r15.LINK_KEYS)):
        for item in value[key]:
            _closed(item, keys, 'wire_item_keys')
            result[key].append(_map_fragments(item, convert))
    return result


def to_compact(wire: dict) -> dict:
    """Structural inverse only; schema and semantic validation belong to decode."""
    try:
        return _map(wire, False)
    except RecursionError as exc:
        raise WireError('wire_resource') from exc


def from_compact(compact: dict) -> dict:
    """Map r15.1-shaped data without repairing or judging semantic validity."""
    try:
        return _map(compact, True)
    except RecursionError as exc:
        raise WireError('wire_resource') from exc


def _profile(profile):
    if profile not in ('full', 'opaque'):
        raise ValueError('profile must be full or opaque')


def lint_schema(value):
    """T4 runtime lint: closed, fully typed R14-dialect schema, depth <= 8."""
    stats = dict(depth=0, enum_values=0, objects=0, properties=0, nodes=0)

    def check(ok):
        _require(ok, 'schema_lint')

    def walk(node, depth):
        check(type(node) is dict and depth <= 8)
        kind = node.get('type')
        check(type(kind) is str and kind in ('object', 'array', 'string', 'integer'))
        stats['depth'] = max(stats['depth'], depth)
        stats['nodes'] += 1
        if kind == 'object':
            check(set(node) == {'type', 'properties', 'required', 'additionalProperties'})
            check(type(node['properties']) is dict)
            check(all(type(k) is str for k in node['properties']))
            check(type(node['required']) is list)
            check(all(type(k) is str for k in node['required']))
            check(node['required'] == list(node['properties']))
            check(node['additionalProperties'] is False)
            stats['objects'] += 1
            stats['properties'] += len(node['properties'])
            for child in node['properties'].values():
                walk(child, depth + 1)
        elif kind == 'array':
            check(set(node) == {'type', 'items', 'minItems', 'maxItems'})
            check(type(node['items']) is dict)
            walk(node['items'], depth + 1)
        elif kind == 'string':
            check(set(node) in ({'type', 'enum'}, {'type', 'minLength', 'maxLength'}))
            if 'enum' in node:
                values = node['enum']
                check(type(values) is list and bool(values))
                check(all(type(v) is str for v in values))
                check(len(set(values)) == len(values))
                stats['enum_values'] += len(values)
        else:
            check(set(node) in ({'type', 'minimum'}, {'type', 'minimum', 'maximum'}))
        for key in ('minLength', 'maxLength', 'minItems', 'maxItems'):
            if key in node:
                check(type(node[key]) is int and node[key] >= 0)
        for key in ('minimum', 'maximum'):
            if key in node:
                check(type(node[key]) in (int, float))
                # Also reject NaN/infinity without changing schema bounds.
                if type(node[key]) is float:
                    check(float('-inf') < node[key] < float('inf'))
        for low, high in (('minimum', 'maximum'), ('minLength', 'maxLength'), ('minItems', 'maxItems')):
            if low in node and high in node:
                check(node[low] <= node[high])

    walk(value, 0)
    common.check_schema(value)
    return stats


def schema(source: str, table, profile: str = 'full') -> dict:
    _profile(profile)
    r15.validate_table(source, table)

    def obj(properties):
        return dict(type='object', properties=properties, required=list(properties),
                    additionalProperties=False)

    def string(cap, low=0):
        return dict(type='string', minLength=low, maxLength=cap)

    def enum(values):
        return dict(type='string', enum=list(values))

    def integer(low, high=None):
        result = dict(type='integer', minimum=low)
        if high is not None:
            result['maximum'] = high
        return result

    def arr(items, low, high):
        return dict(type='array', items=items, minItems=low, maxItems=high)

    sid = string(max(len(row[0]) for row in table['rows']), 2)
    nid = string(4, 2)
    fragment = obj({'a': sid, 'h': string(48, 1), 'ho': integer(1),
                    'z': sid, 't': string(48, 1), 'to': integer(1)})
    dimension = obj({'s': enum(r15.STATES), 'x': arr(fragment, 0, 4), 'r': string(180)})
    deadline = obj({'c': dimension, 'z': dimension, 'b': dimension})
    unit = obj({'i': integer(1, 160), 'k': integer(0, 8), 's': string(280, 1),
                'm': integer(0, 6), 'p': integer(0, 2), 'y': arr(deadline, 0, 1),
                'd': arr(integer(1, 160), 0, 16), 'b': arr(integer(1, 160), 0, 16),
                'e': arr(sid, 1, 6), 'q': integer(0, 3), 'r': string(180)})
    node = obj({'i': nid, 'o': enum(['L', 'R'] if profile == 'opaque' else r15.OPS),
                'a': arr(nid, 0, 0 if profile == 'opaque' else 8),
                'x': arr(fragment, 0, 8), 'g': string(120),
                'q': integer(0, 3), 'r': string(180)})
    link = obj({'u': integer(1, 160), 'w': enum(r15.ROLES), 'n': nid,
                'x': arr(fragment, 0, 2), 'q': integer(0, 3), 'r': string(180)})
    result = obj({'v': enum([VERSION]), 'h': enum([r15.source_hash(source)]),
                  't': enum([r15.digest(table)]), 'u': arr(unit, 1, 160),
                  'g': arr(node, 0, 400), 'l': arr(link, 0, 400), 'z': enum(['END'])})
    # No mutable aliases within a returned schema, or with imported enum constants.
    def fresh(value):
        if isinstance(value, dict):
            return {key: fresh(child) for key, child in value.items()}
        if isinstance(value, list):
            return [fresh(child) for child in value]
        return value
    result = fresh(result)
    lint_schema(result)
    return result


def validate_response(raw_content: str, finish_reason: str, source: str, table,
                      profile: str = 'full', *, plan=None) -> dict:
    r15.require(finish_reason == 'stop', 'non_stop')
    _profile(profile)
    if plan is not None:
        _require(isinstance(plan, dict), 'plan_shape')
        _require(plan.get('profile') == profile, 'plan_profile')
        _require(plan.get('version') == VERSION, 'plan_version')
        _require(plan.get('envelope_version') == ENVELOPE_VERSION, 'plan_envelope_version')
    value = r15.strict_load(raw_content)
    response_schema = schema(source, table, profile)
    lint_schema(response_schema)
    errors = common.schema_errors(value, response_schema)
    if errors:
        # Preserve the historical array_bound verdict for pure count violations
        # (notably the invalid nine-fragment sizing fixture), while still rejecting
        # at D2. No host validation is run before the wire schema check.
        code = 'array_bound' if all(e.endswith(': size') for e in errors) else 'wire_schema'
        raise WireError(code, errors)
    compact = to_compact(value)
    r15.validate(compact, source, table, finish_reason)
    expanded = r15.expand(compact, source, table, finish_reason)
    restored = r15.contract(expanded, source, table)
    _require(r15.canonical(restored) == r15.canonical(compact)
             and r15.canonical(from_compact(restored)) == r15.canonical(value),
             'wire_inverse')
    return expanded


PROMPT_EDITS = (
    ('Emit one complete closed r15.1 envelope', 'Emit one complete closed r16.w1 envelope'),
    ('Every fragment x item is [startSpan,head,headOccurrence,endSpan,tail,tailOccurrence].',
     'Every fragment x item is an object {a,h,ho,z,t,to}: a startSpan ID, h head, ho headOccurrence, z endSpan ID, t tail, to tailOccurrence; all six keys required.'),
    ('y=null unless k3 and assertion is a deadline;', 'y=[] unless k3 and assertion is a deadline;'),
    ('Deadline y has c(clock)', 'A deadline y is a one-item list [{c,z,b}]: c(clock)'),
    ('A null deadline is a claim', 'An empty y is a claim'),
    ('The complete source and span table are supplied.',
     'The complete source is supplied as span-table rows whose exact concatenation in ID order is the full source.'),
)


def _system_prompt(profile):
    prompt = _r15_bytes('stage-a.system.txt').decode('utf-8')
    for old, new in PROMPT_EDITS:
        _require(prompt.count(old) == 1, 'prompt_edit_anchor')
        prompt = prompt.replace(old, new)
    prompt += '\ny=[] claims non-deadline function; it never means unknown.\n'
    if profile == 'opaque':
        prompt += ('Opaque profile: only L/R nodes with a=[] are permitted. Preserve complete '
                   'clauses in exact fragments and their source-supported links; use uncertainty '
                   'and qual for unresolved logic. Do not emit typed-logic nodes.\n')
    return prompt


def _request(source, profile):
    """Internal assembly shared by the guarded builder and sizing-only entry point."""
    _profile(profile)
    table = r15.span_table(source)
    reconstructed = r15.reconstruct(source, table)
    _require(reconstructed.encode('utf-8') == source.encode('utf-8'), 'source_reconstruction')
    user = dict(source_text_sha256=r15.source_hash(source),
                span_table=table, span_table_sha256=r15.digest(table))
    body = r15.strict_load(_r15_bytes('request-settings.json').decode('utf-8'))
    response_schema = schema(source, table, profile)
    lint_schema(response_schema)
    body.update(messages=[dict(role='system', content=_system_prompt(profile)),
                          dict(role='user', content=r15.canonical(user).decode('utf-8'))],
                response_format=dict(type='json_schema', json_schema=dict(
                    name='condition_inventory', strict=True, schema=response_schema)))
    raw = common.encode(body)
    guarded_bytes = len(raw) + 1024
    sizing = dict(version=VERSION, envelope_version=ENVELOPE_VERSION, profile=profile,
                  body_bytes=len(raw), guarded_bytes=guarded_bytes,
                  request_sha256=hashlib.sha256(raw).hexdigest(),
                  source_bytes=len(source.encode('utf-8')), spans=len(table['rows']),
                  schema_bytes=len(common.encode(response_schema)), guard_limit=40000,
                  residual_guard_bytes=40000 - guarded_bytes,
                  under_guard=guarded_bytes <= 40000)
    return body, table, sizing


def measure(source: str, profile: str = 'full') -> dict:
    """Sizing metadata only, including over-guard requests; never returns a body."""
    return _request(source, profile)[2]


def build(source: str, profile: str = 'full') -> dict:
    """Return a dispatchable plan only when the complete R14 byte guard passes."""
    body, table, sizing = _request(source, profile)
    _require(sizing['under_guard'], 'full_request_overflow')
    return dict(body=body, table=table, **sizing)
