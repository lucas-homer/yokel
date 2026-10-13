"""Offline r16.w1 A1 wire adapter; frozen r15.1 semantics and R14 checker."""
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
FRAGMENT_KEYS = ('a', 'h', 'ho', 'z', 't', 'to')


class WireError(Exception):
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
    return [value[key] for key in FRAGMENT_KEYS]


def _fragment_from_compact(value):
    _require(isinstance(value, list) and len(value) == 6, 'compact_fragment_shape')
    return dict(zip(FRAGMENT_KEYS, value))


def _map_fragments(item, convert):
    _array(item['x'], 'wire_fragment_list')
    item['x'] = [convert(fragment) for fragment in item['x']]


def _map(value, to_wire):
    _closed(value, r15.ENVELOPE_KEYS, 'wire_envelope_keys')
    _require(value['v'] == (r15.VERSION if to_wire else VERSION), 'wire_version')
    result = copy.deepcopy(value)
    result['v'] = VERSION if to_wire else r15.VERSION
    for key in ('u', 'g', 'l'):
        _array(result[key], 'wire_array')
    convert = _fragment_from_compact if to_wire else _fragment_to_compact
    for unit in result['u']:
        _closed(unit, r15.UNIT_KEYS, 'wire_unit_keys')
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
            for dimension in deadline.values():
                _closed(dimension, ('s', 'x', 'r'), 'wire_dimension_keys')
                _map_fragments(dimension, convert)
        unit['y'] = ([] if deadline is None else [deadline]) if to_wire else deadline
    for key, keys in (('g', r15.NODE_KEYS), ('l', r15.LINK_KEYS)):
        for item in result[key]:
            _closed(item, keys, 'wire_item_keys')
            _map_fragments(item, convert)
    return result


def to_compact(wire: dict) -> dict:
    """Structural inverse only; schema and semantic validation belong to decode."""
    return _map(wire, False)


def from_compact(compact: dict) -> dict:
    """Map r15.1-shaped data without repairing or judging semantic validity."""
    return _map(compact, True)


def _profile(profile):
    if profile not in ('full', 'opaque'):
        raise ValueError('profile must be full or opaque')


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
    return fresh(result)


def validate_response(raw_content: str, finish_reason: str, source: str, table,
                      profile: str = 'full') -> dict:
    r15.require(finish_reason == 'stop', 'non_stop')
    value = r15.strict_load(raw_content)
    response_schema = schema(source, table, profile)
    common.check_schema(response_schema)
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


def build(source: str, profile: str = 'full') -> dict:
    """Offline, fully sized request plan; under_guard=False means inadmissible."""
    _profile(profile)
    table = r15.span_table(source)
    user = dict(source_text=source, source_text_sha256=r15.source_hash(source),
                span_table=table, span_table_sha256=r15.digest(table))
    body = r15.strict_load(_r15_bytes('request-settings.json').decode('utf-8'))
    response_schema = schema(source, table, profile)
    common.check_schema(response_schema)
    body.update(messages=[dict(role='system', content=_system_prompt(profile)),
                          dict(role='user', content=r15.canonical(user).decode('utf-8'))],
                response_format=dict(type='json_schema', json_schema=dict(
                    name='condition_inventory', strict=True, schema=response_schema)))
    raw = common.encode(body)
    guarded_bytes = len(raw) + 1024
    return dict(body=body, table=table, body_bytes=len(raw), guarded_bytes=guarded_bytes,
                request_sha256=hashlib.sha256(raw).hexdigest(),
                under_guard=guarded_bytes <= 40000)
