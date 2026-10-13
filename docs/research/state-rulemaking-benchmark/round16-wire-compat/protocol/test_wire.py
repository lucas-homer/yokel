"""T1–T6, frozen fixture equivalence, schema lint and exact offline sizing."""
import copy
import hashlib
import importlib.util
import json
import re
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('r16_wire_under_test', ROOT / 'wire.py')
wire = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wire)
r15, common = wire.r15, wire.common
BENCH, PROTO = wire.BENCH, wire.R15_ROOT
SIZING = BENCH / 'round15-condition-preservation/sizing'
SOURCE = (PROTO / 'fixtures/source.txt').read_bytes().decode('utf-8')
POSITIVE = json.loads((PROTO / 'fixtures/positive.json').read_bytes())


def corpus():
    cases = [('fixtures/positive', SOURCE, POSITIVE)]
    for name, value in json.loads((PROTO / 'fixtures/semantic-negatives.json').read_bytes()).items():
        cases.append(('fixtures/semantic-negative/' + name, SOURCE, value))
    for path in sorted((PROTO / 'fixtures').glob('long_*-graph.json')):
        stem = path.name[:-len('-graph.json')]
        source = (PROTO / 'fixtures' / (stem + '-source.txt')).read_bytes().decode('utf-8')
        cases.append(('fixtures/' + stem, source, json.loads(path.read_bytes())))
    for profile in json.loads((SIZING / 'authored-profiles.json').read_bytes())['profiles']:
        compact = copy.deepcopy(profile['wire'])
        compact['v'] = r15.VERSION
        compact['t'] = r15.digest(r15.span_table(profile['source']))
        cases.append(('sizing/' + profile['id'], profile['source'], compact))
    for control in json.loads((SIZING / 'revised/authored-controls.json').read_bytes())['controls']:
        cases.append(('revised-control/' + control['id'], control['source'], control['wire']))
    return cases


def lint_schema(value):
    allowed = {'type', 'properties', 'required', 'additionalProperties', 'enum',
               'minimum', 'maximum', 'minLength', 'maxLength', 'items', 'minItems', 'maxItems'}
    stats = dict(depth=0, enum_values=0, objects=0, properties=0, nodes=0)

    def walk(node, depth):
        assert isinstance(node, dict)
        assert not set(node) - allowed
        assert type(node['type']) is str and node['type'] in ('object', 'array', 'string', 'integer')
        stats['depth'] = max(stats['depth'], depth)
        stats['nodes'] += 1
        for key, child in node.items():
            if key in ('minLength', 'maxLength', 'minItems', 'maxItems'):
                assert type(child) is int and child >= 0
            elif key in ('minimum', 'maximum'):
                assert type(child) in (int, float)
            elif key == 'additionalProperties':
                assert child is False
            elif key == 'required':
                assert type(child) is list and all(type(k) is str for k in child)
                assert child == list(node['properties'])
            elif key == 'properties':
                assert type(child) is dict and all(type(k) is str for k in child)
            elif key == 'items':
                assert type(child) is dict
            elif key == 'enum':
                assert type(child) is list and child and all(type(v) is str for v in child)
                assert len(set(child)) == len(child)
                stats['enum_values'] += len(child)
        for low, high in (('minimum', 'maximum'), ('minLength', 'maxLength'), ('minItems', 'maxItems')):
            if low in node and high in node:
                assert node[low] <= node[high]
        if node['type'] == 'object':
            assert set(node) == {'type', 'properties', 'required', 'additionalProperties'}
            assert node['additionalProperties'] is False
            stats['objects'] += 1
            stats['properties'] += len(node['properties'])
            for child in node['properties'].values():
                walk(child, depth + 1)
        elif node['type'] == 'array':
            assert set(node) == {'type', 'items', 'minItems', 'maxItems'}
            walk(node['items'], depth + 1)
        elif node['type'] == 'string':
            assert set(node) in ({'type', 'enum'}, {'type', 'minLength', 'maxLength'})
        elif node['type'] == 'integer':
            assert set(node) in ({'type', 'minimum'}, {'type', 'minimum', 'maximum'})
    walk(value, 0)
    assert stats['depth'] <= 8
    common.check_schema(value)
    return stats


def mutable_ids(value):
    if isinstance(value, dict):
        return {id(value)}.union(*(mutable_ids(v) for v in value.values()))
    if isinstance(value, list):
        return {id(value)}.union(*(mutable_ids(v) for v in value))
    return set()


class CorpusTests(unittest.TestCase):
    """Each authored case is a separately named test in the verbose receipt."""


def fixture_test(label, source, compact):
    def test(self):
        table = r15.span_table(source)
        original = r15.canonical(compact)
        try:
            r15.validate(compact, source, table)
        except ValueError as exc:
            expected_code = str(exc)
        else:
            expected_code = None
        encoded = wire.from_compact(compact)
        restored = wire.to_compact(encoded)
        self.assertEqual(r15.canonical(restored), original, label)
        self.assertEqual(r15.canonical(wire.from_compact(restored)), r15.canonical(encoded))
        if expected_code is not None:
            with self.assertRaises(ValueError) as exc:
                r15.validate(restored, source, table)
            self.assertEqual(str(exc.exception), expected_code)
            with self.assertRaises((ValueError, wire.WireError)) as exc:
                wire.validate_response(r15.canonical(encoded).decode(), 'stop', source, table)
            self.assertEqual(str(exc.exception), expected_code)
            if not common.schema_errors(encoded, wire.schema(source, table)):
                self.assertIs(type(exc.exception), ValueError)  # r15 error not rewrapped
        else:
            self.assertEqual(common.schema_errors(encoded, wire.schema(source, table)), [])
            direct = r15.expand(compact, source, table)
            expanded = wire.validate_response(r15.canonical(encoded).decode(), 'stop', source, table)
            self.assertEqual(r15.canonical(expanded), r15.canonical(direct))
            self.assertEqual(r15.canonical(wire.from_compact(r15.contract(expanded, source, table))),
                             r15.canonical(encoded))
            self.assertTrue(mutable_ids(compact).isdisjoint(mutable_ids(encoded)))
            self.assertTrue(mutable_ids(encoded).isdisjoint(mutable_ids(restored)))
            self.assertEqual(expanded['semantic_validity'], 'unverified')
            self.assertEqual(expanded['condition_coverage'], 'unverified')
            self.assertFalse(expanded['action_ready'])
        self.assertEqual(r15.canonical(compact), original)
    return test


for _label, _source, _compact in corpus():
    setattr(CorpusTests, 'test_T1_T2_' + re.sub(r'[^a-zA-Z0-9_]', '_', _label),
            fixture_test(_label, _source, _compact))


def fragment(value):
    return next(n for n in value['g'] if n['x'])['x'][0]


NEGATIVES = {
    'fragment_tuple': lambda w: next(n for n in w['g'] if n['x'])['x'].__setitem__(0, ['s1', 'AND', 1, 's1', 'AND', 1]),
    'fragment_missing_key': lambda w: fragment(w).pop('to'),
    'fragment_extra_key': lambda w: fragment(w).__setitem__('n', 1),
    'occurrence_zero': lambda w: fragment(w).__setitem__('ho', 0),
    'occurrence_boolean': lambda w: fragment(w).__setitem__('ho', True),
    'occurrence_float': lambda w: fragment(w).__setitem__('ho', 1.0),
    'empty_anchor': lambda w: fragment(w).__setitem__('h', ''),
    'whitespace_anchor': lambda w: fragment(w).__setitem__('h', '   '),
    'deadline_null': lambda w: w['u'][0].__setitem__('y', None),
    'deadline_two_items': lambda w: w['u'][0].__setitem__('y', [{}, {}]),
    'deadline_one_null': lambda w: w['u'][0].__setitem__('y', [None]),
    'old_version': lambda w: w.__setitem__('v', 'r15.1'),
    'span_overlong': lambda w: fragment(w).__setitem__('a', 's999999999'),
    'span_absent_short': lambda w: fragment(w).__setitem__('a', 's0'),
    'node_overlong': lambda w: w['l'][0].__setitem__('n', 'c0001'),
    'node_bad_prefix': lambda w: w['l'][0].__setitem__('n', 'x1'),
    'node_leading_zero': lambda w: w['l'][0].__setitem__('n', 'c01'),
    'node_out_of_range': lambda w: w['l'][0].__setitem__('n', 'c401'),
    'missing_envelope_key': lambda w: w.pop('z'),
    'extra_envelope_key': lambda w: w.__setitem__('legacy', 1),
    'extra_dimension_key': lambda w: w['u'][2]['y'][0]['c'].__setitem__('legacy', 1),
}


class WireTests(unittest.TestCase):
    def setUp(self):
        self.table = r15.span_table(SOURCE)
        self.value = wire.from_compact(POSITIVE)

    def test_T4_both_profiles_lint_and_checker(self):
        for profile, count in [('full', 30), ('opaque', 25)]:
            stats = lint_schema(wire.schema(SOURCE, self.table, profile))
            self.assertEqual(stats['depth'], 8)
            self.assertEqual(stats['objects'], 13)
            self.assertEqual(stats['properties'], 73)
            self.assertEqual(stats['enum_values'], count)

    def test_T4_exact_pinned_draft_schema(self):
        source = (BENCH / 'round14-semantic-contract/source/parsed-body.txt').read_bytes().decode()
        draft = json.loads((ROOT.parent / 'design/schema.draft.json').read_bytes())
        self.assertEqual(wire.schema(source, r15.span_table(source)), draft)

    def test_opaque_rejects_every_typed_operator_at_schema_level(self):
        response_schema = wire.schema(SOURCE, self.table, 'opaque')
        for op in ['AND', 'OR', 'NOT', 'EXC', 'ALT']:
            with self.subTest(op=op):
                value = copy.deepcopy(self.value)
                value['g'][0].update(o=op, a=[])
                self.assertTrue(any('.o: enum' in e for e in common.schema_errors(value, response_schema)))
        value = copy.deepcopy(self.value)
        value['g'][0].update(o='L', a=['c2'])
        self.assertTrue(any('.a: size' in e for e in common.schema_errors(value, response_schema)))
        with self.assertRaises(wire.WireError) as exc:
            wire.validate_response(r15.canonical(self.value).decode(), 'stop', SOURCE, self.table, 'opaque')
        self.assertEqual(exc.exception.code, 'wire_schema')

    def test_opaque_valid_authored_whole_clause(self):
        control = next(p for p in corpus() if p[0] == 'revised-control/paired-opaque-complete-clause')
        _, source, compact = control
        table = r15.span_table(source)
        value = wire.from_compact(compact)
        self.assertEqual(common.schema_errors(value, wire.schema(source, table, 'opaque')), [])
        self.assertEqual(wire.validate_response(r15.canonical(value).decode(), 'stop', source, table, 'opaque'),
                         r15.expand(compact, source, table))

    def test_invalid_profiles(self):
        for profile in ['', 'typed', None, 1]:
            with self.subTest(profile=profile):
                with self.assertRaises(ValueError):
                    wire.schema(SOURCE, self.table, profile)
                with self.assertRaises(ValueError):
                    wire.build(SOURCE, profile)
                with self.assertRaises(ValueError):
                    wire.validate_response(r15.canonical(self.value).decode(), 'stop', SOURCE, self.table, profile)

    def test_T5_no_alias_mutations_both_directions(self):
        original = copy.deepcopy(POSITIVE)
        value = wire.from_compact(original)
        snapshot = copy.deepcopy(value)
        restored = wire.to_compact(value)
        self.assertTrue(mutable_ids(original).isdisjoint(mutable_ids(value)))
        self.assertTrue(mutable_ids(value).isdisjoint(mutable_ids(restored)))
        restored['u'][0]['d'].append(99)
        restored['g'][0]['a'].reverse()
        restored['u'][2]['y']['c']['x'][0][1] = 'changed'
        self.assertEqual(value, snapshot)
        value['u'][0]['b'].append(99)
        fragment(value)['h'] = 'changed'
        self.assertEqual(original, POSITIVE)
        restored_snapshot = copy.deepcopy(restored)
        value['u'][2]['y'][0]['z']['x'].clear()
        self.assertEqual(restored, restored_snapshot)

    def test_schema_has_no_shared_mutable_aliases(self):
        value = wire.schema(SOURCE, self.table)
        expected = copy.deepcopy(value)
        value['properties']['g']['items']['properties']['o']['enum'].clear()
        self.assertEqual(r15.OPS, ['L', 'R', 'AND', 'OR', 'NOT', 'EXC', 'ALT'])
        self.assertEqual(wire.schema(SOURCE, self.table), expected)
        value['properties']['u']['items']['properties']['y']['items']['properties']['c']['properties']['x']['items']['properties']['a']['maxLength'] = 999
        self.assertEqual(value['properties']['u']['items']['properties']['y']['items']['properties']['z'],
                         expected['properties']['u']['items']['properties']['y']['items']['properties']['z'])

    def test_T6_finish_checked_before_parse(self):
        with patch.object(r15, 'strict_load', side_effect=AssertionError('must not parse')):
            with self.assertRaisesRegex(ValueError, '^non_stop$') as exc:
                wire.validate_response('invalid', 'length', SOURCE, self.table)
        self.assertIs(type(exc.exception), ValueError)

    def test_T6_raw_byte_boundary_on_wire(self):
        raw = r15.canonical(self.value).decode()
        size = len(raw.encode())
        self.assertEqual(wire.validate_response(raw + ' ' * (r15.RAW_LIMIT - size), 'stop', SOURCE, self.table),
                         r15.expand(POSITIVE, SOURCE, self.table))
        with patch.object(common, 'schema_errors', side_effect=AssertionError('must not check')):
            with self.assertRaisesRegex(ValueError, '^raw_size$'):
                wire.validate_response(raw + ' ' * (r15.RAW_LIMIT + 1 - size), 'stop', SOURCE, self.table)

    def test_T6_depth_boundary_and_quoted_brackets(self):
        raw = '[' * 64 + '0' + ']' * 64
        r15.strict_load(raw)
        with self.assertRaises(wire.WireError):
            wire.validate_response(raw, 'stop', SOURCE, self.table)
        with patch.object(common, 'schema_errors', side_effect=AssertionError('must not check')):
            with self.assertRaisesRegex(ValueError, '^parser_depth$'):
                wire.validate_response('[' * 65 + '0' + ']' * 65, 'stop', SOURCE, self.table)
        value = copy.deepcopy(self.value)
        value['u'][0]['s'] = '[' * 100 + '"\\[]'
        self.assertEqual(wire.validate_response(r15.canonical(value).decode(), 'stop', SOURCE, self.table)['units'][0]['assertion'],
                         value['u'][0]['s'])

    def test_T6_strict_raw_rejections_preserve_r15_errors(self):
        for raw in ['{"x":1,"x":2}', '{"x":{"y":1,"y":2}}', '{} trailing',
                    'NaN', 'Infinity', '-Infinity', '1e999', '{"z":"END"',
                    '"\\ud800"', '"\\udc00"', '"\\ud800A"', '"\ud800"', ']', '{}{}']:
            with self.subTest(raw=repr(raw)):
                with self.assertRaises(ValueError) as direct:
                    r15.strict_load(raw)
                with patch.object(common, 'schema_errors', side_effect=AssertionError('must not check')):
                    with self.assertRaises(ValueError) as via_wire:
                        wire.validate_response(raw, 'stop', SOURCE, self.table)
                self.assertIs(type(via_wire.exception), type(direct.exception))
                self.assertEqual(str(via_wire.exception), str(direct.exception))

    def test_wire_schema_checked_before_host_validate(self):
        self.value['u'][0]['i'] = True
        with patch.object(r15, 'validate', side_effect=AssertionError('must not validate compact')):
            with self.assertRaises(wire.WireError) as exc:
                wire.validate_response(r15.canonical(self.value).decode(), 'stop', SOURCE, self.table)
        self.assertEqual(exc.exception.code, 'wire_schema')
        self.assertTrue(exc.exception.details)

    def test_T6_escaped_astral_pair_and_exact_codepoints(self):
        self.value['u'][0]['s'] = '🫧' * 280
        expanded = wire.validate_response(json.dumps(self.value, ensure_ascii=True), 'stop', SOURCE, self.table)
        self.assertEqual(expanded['units'][0]['assertion'], '🫧' * 280)

    def test_structural_adapter_rejects_null_and_extra_keys(self):
        for name in ['fragment_tuple', 'fragment_missing_key', 'fragment_extra_key', 'deadline_null',
                     'deadline_two_items', 'deadline_one_null', 'old_version', 'missing_envelope_key',
                     'extra_envelope_key', 'extra_dimension_key']:
            value = copy.deepcopy(self.value)
            NEGATIVES[name](value)
            with self.subTest(case=name), self.assertRaises(wire.WireError) as exc:
                wire.to_compact(value)
            self.assertIsInstance(exc.exception.code, str)

    def test_build_exact_R14_bytes_and_preserved_envelope(self):
        for profile in ['full', 'opaque']:
            plan = wire.build(SOURCE, profile)
            raw = common.encode(plan['body'])
            self.assertEqual(plan['body_bytes'], len(raw))
            self.assertEqual(plan['guarded_bytes'], len(raw) + 1024)
            self.assertEqual(plan['request_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertTrue(plan['under_guard'])
            user = r15.strict_load(plan['body']['messages'][1]['content'])
            self.assertEqual(set(user), {'source_text', 'source_text_sha256', 'span_table', 'span_table_sha256'})
            self.assertEqual(user['source_text'].encode(), SOURCE.encode())
            self.assertEqual(user['span_table'], r15.span_table(SOURCE))
            settings = r15.strict_load((PROTO / 'request-settings.json').read_bytes().decode())
            self.assertEqual({k: plan['body'][k] for k in settings}, settings)
            prompt = plan['body']['messages'][0]['content']
            self.assertIn('r16.w1', prompt)
            self.assertNotIn('y=null', prompt)
            self.assertIn('never means unknown', prompt)
            common.check_schema(plan['body']['response_format']['json_schema']['schema'])

    def test_build_size_profiles_fit_and_overflow(self):
        measurements = size_receipt()
        # The explicit non-deadline sentence adds 60 text bytes, serialized as
        # 62 bytes because both newlines are JSON-escaped in the system content.
        self.assertEqual(measurements['prior_source']['guarded_bytes'], 31312 + 62)
        self.assertEqual(measurements['disjoint600_u24']['guarded_bytes'], 43370 + 62)
        self.assertTrue(measurements['prior_source']['under_guard'])
        self.assertFalse(measurements['disjoint600_u24']['under_guard'])

    def test_all_frozen_dependency_and_design_pins(self):
        for directory in [PROTO, ROOT.parent / 'design']:
            manifest = json.loads((directory / 'READY.json').read_bytes())
            for name, digest in manifest['sha256'].items():
                with self.subTest(file=str(directory / name)):
                    self.assertEqual(hashlib.sha256((directory / name).read_bytes()).hexdigest(), digest)
        self.assertEqual(hashlib.sha256(wire.COMMON_PATH.read_bytes()).hexdigest(), wire.COMMON_SHA256)


def negative_test(mutate):
    def test(self):
        mutate(self.value)
        schema_errors = common.schema_errors(self.value, wire.schema(SOURCE, self.table))
        with self.assertRaises((wire.WireError, ValueError)):
            wire.validate_response(r15.canonical(self.value).decode(), 'stop', SOURCE, self.table)
        if not schema_errors:
            with self.assertRaises(ValueError):
                r15.validate(wire.to_compact(self.value), SOURCE, self.table)
    return test


for _name, _mutate in NEGATIVES.items():
    setattr(WireTests, 'test_T3_' + _name, negative_test(_mutate))


def size_receipt():
    prior = (BENCH / 'round14-semantic-contract/source/parsed-body.txt').read_bytes().decode()
    profile = next(p for p in json.loads((SIZING / 'authored-profiles.json').read_bytes())['profiles']
                   if p['id'] == 'disjoint600-u24')
    results = {}
    for name, source in [('prior_source', prior), ('disjoint600_u24', profile['source'])]:
        plan = wire.build(source)
        results[name] = {key: plan[key] for key in ['body_bytes', 'guarded_bytes', 'under_guard', 'request_sha256']}
        results[name].update(source_bytes=len(source.encode()), spans=len(plan['table']['rows']),
                             schema_bytes=len(common.encode(plan['body']['response_format']['json_schema']['schema'])),
                             guard_limit=40000, residual_guard_bytes=40000 - plan['guarded_bytes'])
    return results


def receipt():
    outcomes = []
    for label, source, compact in corpus():
        table = r15.span_table(source)
        try:
            r15.validate(compact, source, table)
        except ValueError as exc:
            error = str(exc)
        else:
            error = None
        outcomes.append(dict(case=label, r15_error=error))
    return dict(version=wire.VERSION, provider_calls=0, credentials_accessed=False,
                corpus=dict(cases=len(outcomes), valid=sum(o['r15_error'] is None for o in outcomes),
                            invalid=[o for o in outcomes if o['r15_error'] is not None]),
                schema={p: lint_schema(wire.schema(SOURCE, r15.span_table(SOURCE), p)) for p in ['full', 'opaque']},
                sizing=size_receipt())


if __name__ == '__main__':
    unittest.main(verbosity=2)
