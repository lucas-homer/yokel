"""T1–T6, frozen fixture equivalence, schema lint and exact offline sizing."""
import copy
import hashlib
import importlib.util
import json
import re
import sys
import tempfile
from types import SimpleNamespace
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


# Fixture callers explicitly supply genuine plans; the codec has no default plan.
_FIXTURE_PLANS = {(SOURCE, p): wire.build(SOURCE, p) for p in ('full', 'opaque')}


def fixture_plan(source, profile='full'):
    selected = profile if profile in ('full', 'opaque') else 'full'
    key = (source, selected)
    if key not in _FIXTURE_PLANS:
        _FIXTURE_PLANS[key] = wire.build(source, selected)
    return _FIXTURE_PLANS[key]


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


lint_schema = wire.lint_schema

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
                wire.validate_response(r15.canonical(encoded).decode(), 'stop', source, table, plan=fixture_plan(source, 'full'))
            self.assertEqual(str(exc.exception), expected_code)
            if not common.schema_errors(encoded, wire.schema(source, table)):
                self.assertIs(type(exc.exception), ValueError)  # r15 error not rewrapped
        else:
            self.assertEqual(common.schema_errors(encoded, wire.schema(source, table)), [])
            direct = r15.expand(compact, source, table)
            expanded = wire.validate_response(r15.canonical(encoded).decode(), 'stop', source, table, plan=fixture_plan(source, 'full'))
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


    def test_review_shared_deadline_dict_valid_compact(self):
        compact = copy.deepcopy(POSITIVE)
        units = [u for u in compact['u'] if u['y'] is not None]
        units[1]['y'] = units[0]['y']
        r15.validate(compact, SOURCE, self.table)
        expected = r15.canonical(compact)
        encoded = wire.from_compact(compact)
        self.assertEqual(r15.canonical(wire.to_compact(encoded)), expected)
        self.assertEqual(r15.canonical(compact), expected)
        encoded_units = [u for u in encoded['u'] if u['y']]
        self.assertIsNot(encoded_units[0]['y'][0], encoded_units[1]['y'][0])
        self.assertEqual(r15.canonical(wire.validate_response(
            r15.canonical(encoded).decode(), 'stop', SOURCE, self.table, plan=fixture_plan(SOURCE, 'full'))),
            r15.canonical(r15.expand(compact, SOURCE, self.table)))

    def test_review_shared_deadline_list_valid_wire(self):
        units = [u for u in self.value['u'] if u['y']]
        units[1]['y'] = units[0]['y']
        expected = r15.canonical(self.value)
        compact = wire.to_compact(self.value)
        r15.validate(compact, SOURCE, self.table)
        self.assertEqual(r15.canonical(wire.from_compact(compact)), expected)
        self.assertEqual(r15.canonical(self.value), expected)
        compact_units = [u for u in compact['u'] if u['y'] is not None]
        self.assertIsNot(compact_units[0]['y'], compact_units[1]['y'])

    def test_review_build_refuses_overflow_as_valueerror(self):
        with self.assertRaises(ValueError) as exc:
            wire.build('a' * 40000)
        self.assertEqual(str(exc.exception), 'full_request_overflow')
        self.assertEqual(exc.exception.code, 'full_request_overflow')

    def test_review_deep_direct_input_controlled_at_two_limits(self):
        original_limit = sys.getrecursionlimit()
        try:
            for limit in [original_limit, 180]:
                for convert, value in [(wire.to_compact, self.value),
                                       (wire.from_compact, POSITIVE)]:
                    with self.subTest(limit=limit, convert=convert.__name__):
                        deep = copy.deepcopy(value)
                        cur = deep['u'][0]['s'] = []
                        for _ in range(3000):
                            child = []
                            cur.append(child)
                            cur = child
                        sys.setrecursionlimit(limit)
                        with self.assertRaises(wire.WireError) as exc:
                            convert(deep)
                        self.assertEqual(exc.exception.code, 'wire_resource')
                        sys.setrecursionlimit(original_limit)
        finally:
            sys.setrecursionlimit(original_limit)


    def test_review_shared_fragments_and_dimensions_both_directions(self):
        for convert, inverse, initial in [(wire.from_compact, wire.to_compact, POSITIVE),
                                          (wire.to_compact, wire.from_compact, self.value)]:
            with self.subTest(direction=convert.__name__):
                value = copy.deepcopy(initial)
                nodes = [n for n in value['g'] if n['x']]
                nodes[1]['x'] = nodes[0]['x']
                deadline = next(u['y'] for u in value['u'] if u['y'])
                if isinstance(deadline, list):
                    deadline = deadline[0]
                deadline['z'] = deadline['c']
                before = r15.canonical(value)
                result = convert(value)
                self.assertEqual(r15.canonical(inverse(result)), before)
                self.assertEqual(r15.canonical(value), before)
                self.assertTrue(mutable_ids(value).isdisjoint(mutable_ids(result)))
                result['g'][0]['x'].clear()
                self.assertTrue(result['g'][1]['x'])
                out_deadline = next(u['y'] for u in result['u'] if u['y'])
                if isinstance(out_deadline, list):
                    out_deadline = out_deadline[0]
                out_deadline['c']['x'].clear()
                self.assertTrue(out_deadline['z']['x'])

    def test_review_measure_never_returns_body_even_on_overflow(self):
        allowed = {'version', 'envelope_version', 'profile', 'body_bytes', 'guarded_bytes',
                   'request_sha256', 'source_bytes', 'spans', 'schema_bytes', 'guard_limit',
                   'residual_guard_bytes', 'under_guard'}
        for profile in ['full', 'opaque']:
            for source in [SOURCE, 'a' * 40000]:
                with self.subTest(profile=profile, over=source != SOURCE):
                    measured = wire.measure(source, profile)
                    self.assertEqual(set(measured), allowed)
                    self.assertNotIn('body', measured)
                    self.assertNotIn('messages', measured)
                    self.assertNotIn('table', measured)
                    self.assertEqual(measured['profile'], profile)
                    self.assertEqual(measured['guarded_bytes'], measured['body_bytes'] + 1024)
                    if source == SOURCE:
                        plan = wire.build(source, profile)
                        self.assertEqual({k: plan[k] for k in allowed}, measured)
                    else:
                        self.assertFalse(measured['under_guard'])
                        with self.assertRaises(wire.WireError) as exc:
                            wire.build(source, profile)
                        self.assertEqual(exc.exception.code, 'full_request_overflow')

    def test_review_build_guard_exact_inclusive_boundary(self):
        measured = wire.measure('a' * 30000)
        # Keep the row end offset at five decimal digits while varying source size.
        exact = 'a' * (30000 + 40000 - measured['guarded_bytes'])
        self.assertEqual(len(str(len(exact))), 5)
        self.assertEqual(wire.build(exact)['guarded_bytes'], 40000)
        self.assertEqual(wire.measure(exact + 'a')['guarded_bytes'], 40001)
        with self.assertRaises(wire.WireError) as exc:
            wire.build(exact + 'a')
        self.assertEqual(exc.exception.code, 'full_request_overflow')

    def test_w21_plan_is_required(self):
        with self.assertRaises(TypeError):
            wire.validate_response('{}', 'stop', SOURCE, self.table)
        with self.assertRaisesRegex(wire.WireError, '^plan_shape$'):
            wire.validate_response('{}', 'stop', SOURCE, self.table, plan=None)

    def test_w21_forged_three_key_plan(self):
        plan = dict(profile='full', version=wire.VERSION, envelope_version=wire.ENVELOPE_VERSION)
        with self.assertRaisesRegex(wire.WireError, '^plan_shape$'):
            wire.validate_response('{', 'stop', SOURCE, self.table, plan=plan)

    def test_w21_plan_from_different_source(self):
        plan = wire.build(SOURCE + 'Different source.\n')
        with self.assertRaisesRegex(wire.WireError, '^plan_table$'):
            wire.validate_response('{', 'stop', SOURCE, self.table, plan=plan)

    def test_w21_mismatched_table(self):
        plan = wire.build(SOURCE)
        table = copy.deepcopy(self.table)
        table['rows'][0][3] += 'changed'
        with self.assertRaisesRegex(wire.WireError, '^plan_table$'):
            wire.validate_response('{', 'stop', SOURCE, table, plan=plan)
        plan['table'] = table
        with self.assertRaisesRegex(wire.WireError, '^plan_table$'):
            wire.validate_response('{', 'stop', SOURCE, table, plan=plan)

    def test_w21_request_hash_binding(self):
        for digest in ('0' * 64, None):
            plan = wire.build(SOURCE)
            plan['request_sha256'] = digest
            with self.assertRaisesRegex(wire.WireError, '^plan_request_sha256$'):
                wire.validate_response('{', 'stop', SOURCE, self.table, plan=plan)
        plan = wire.build(SOURCE)
        del plan['request_sha256']
        with self.assertRaisesRegex(wire.WireError, '^plan_shape$'):
            wire.validate_response('{', 'stop', SOURCE, self.table, plan=plan)
        # Even a forged matching table must not hide a different originating request.
        plan = wire.build(SOURCE + 'Different source.\n')
        plan['table'] = self.table
        with self.assertRaisesRegex(wire.WireError, '^plan_request_sha256$'):
            wire.validate_response('{', 'stop', SOURCE, self.table, plan=plan)

    def test_w21_prior_108_rows_array_concatenation(self):
        source = (BENCH / 'round14-semantic-contract/source/parsed-body.txt').read_bytes().decode()
        for profile in ('full', 'opaque'):
            plan = wire.build(source, profile)
            user = r15.strict_load(plan['body']['messages'][1]['content'])
            rows = user['span_table']['rows']
            self.assertEqual(len(rows), 108)
            self.assertEqual(''.join(row[3] for row in rows).encode(), source.encode())
            self.assertNotEqual(''.join(row[3] for row in sorted(rows)).encode(), source.encode())
            self.assertIn('in the supplied table array order', plan['body']['messages'][0]['content'])

    def test_w21_codec_preserves_w1_key_order(self):
        old = wire._load('w21_frozen_w1_order', BENCH / 'round16-wire-compat/protocol/wire.py',
                         (BENCH / 'round16-wire-compat/protocol/wire.py').read_bytes())
        for label, source, compact in corpus():
            with self.subTest(case=label):
                compact = copy.deepcopy({key: compact[key] for key in reversed(list(compact))})
                for unit in compact['u']:
                    unit['y'] = unit.pop('y')
                expected = old.from_compact(compact)
                actual = wire.from_compact(compact)
                self.assertEqual(json.dumps(actual, ensure_ascii=False), json.dumps(expected, ensure_ascii=False))
                self.assertEqual(list(wire.to_compact(actual)), list(old.to_compact(expected)))

    def test_w21_frozen_scope(self):
        verify = wire._load('w21_verify_scope', ROOT / 'verify.py',
                            (ROOT / 'verify.py').read_bytes())
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            bench = Path(temporary) / 'benchmark'
            round16 = bench / 'round16-wire-compat'
            owned = round16 / 'protocol-w2-1'
            owned.mkdir(parents=True)
            proto = bench / 'round15-condition-preservation/protocol-revised'
            sizing = bench / 'round15-condition-preservation/sizing'
            common_path = bench / 'round14-semantic-contract/runtime/common.py'
            singles = [common_path, bench / 'round14-semantic-contract/source/parsed-body.txt',
                       sizing / 'authored-profiles.json', sizing / 'revised/authored-controls.json']
            scoped = [proto] + [round16 / name for name in
                ('design', 'inventory', 'envelope-check', 'testing', 'review', 'review-w2', 'protocol')]
            for path in singles + [directory / 'payload.txt' for directory in scoped]:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('original')
            tests = SimpleNamespace(BENCH=bench, PROTO=proto, SIZING=sizing,
                                    wire=SimpleNamespace(COMMON_PATH=common_path))
            with patch.object(verify, 'ROOT', owned):
                manifest = verify.inputs(tests)
                (owned / 'frozen-inputs.json').write_text(json.dumps(manifest))
                self.assertEqual(len(manifest), 12)
                before = verify.check_frozen(tests)
                sibling = round16 / 'new-review/payload.txt'
                sibling.parent.mkdir()
                sibling.write_text('unrelated')
                self.assertEqual(verify.check_frozen(tests), before)
                for directory in scoped:
                    payload = directory / 'payload.txt'
                    payload.write_text('modified')
                    with self.assertRaises(SystemExit):
                        verify.check_frozen(tests)
                    payload.write_text('original')
                    payload.unlink()
                    with self.assertRaises(SystemExit):
                        verify.check_frozen(tests)
                    payload.write_text('original')
                    extra = directory / 'new.txt'
                    extra.write_text('new scoped input')
                    with self.assertRaises(SystemExit):
                        verify.check_frozen(tests)
                    extra.unlink()
                for path in singles:
                    path.write_text('modified')
                    with self.assertRaises(SystemExit):
                        verify.check_frozen(tests)
                    path.write_text('original')
                    path.unlink()
                    with self.assertRaises(FileNotFoundError):
                        verify.check_frozen(tests)
                    path.write_text('original')
                self.assertEqual(verify.check_frozen(tests), before)

    def test_review_plan_profile_mismatch_before_parse(self):
        plan = wire.build(SOURCE, 'opaque')
        self.assertEqual(plan['profile'], 'opaque')
        self.assertEqual(plan['version'], wire.VERSION)
        self.assertEqual(plan['envelope_version'], wire.ENVELOPE_VERSION)
        with patch.object(r15, 'strict_load', side_effect=AssertionError('must not parse')):
            with self.assertRaises(wire.WireError) as exc:
                wire.validate_response('not json', 'stop', SOURCE, self.table, 'full', plan=plan)
        self.assertEqual(exc.exception.code, 'plan_profile')
        # A typed response must also fail when a caller selects full against an opaque plan.
        with self.assertRaises(wire.WireError) as exc:
            wire.validate_response(r15.canonical(self.value).decode(), 'stop', SOURCE,
                                   self.table, 'full', plan=plan)
        self.assertEqual(exc.exception.code, 'plan_profile')
        plan = wire.build(SOURCE)
        self.assertEqual(wire.validate_response(r15.canonical(self.value).decode(), 'stop',
                         SOURCE, self.table, plan=plan), r15.expand(POSITIVE, SOURCE, self.table))

    def test_review_plan_versions_and_missing_metadata_rejected(self):
        for key, wrong, code in [('profile', 'opaque', 'plan_profile'),
                                 ('version', 'r16.w2', 'plan_version'),
                                 ('envelope_version', 'r16.e1', 'plan_envelope_version')]:
            for missing in [False, True]:
                with self.subTest(key=key, missing=missing):
                    plan = wire.build(SOURCE)
                    if missing:
                        plan.pop(key)
                    else:
                        plan[key] = wrong
                    with self.assertRaises(wire.WireError) as exc:
                        wire.validate_response(r15.canonical(self.value).decode(), 'stop',
                                               SOURCE, self.table, plan=plan)
                    self.assertEqual(exc.exception.code, code)

    def test_review_opaque_response_with_matching_plan(self):
        _, source, compact = next(p for p in corpus()
                                 if p[0] == 'revised-control/paired-opaque-complete-clause')
        plan = wire.build(source, 'opaque')
        self.assertEqual(wire.validate_response(r15.canonical(wire.from_compact(compact)).decode(),
                         'stop', source, plan['table'], 'opaque', plan=plan),
                         r15.expand(compact, source, plan['table']))

    def test_review_wireerror_valueerror_compatibility(self):
        exc = wire.WireError('sentinel', ['details'])
        self.assertIsInstance(exc, ValueError)
        self.assertEqual((str(exc), exc.code, exc.details), ('sentinel', 'sentinel', ['details']))

    def test_review_runtime_schema_lint_rejects_malformed_schemas(self):
        mutations = [lambda s: s.pop('type'), lambda s: s.update(type=['object']),
                     lambda s: s.update(additionalProperties={}),
                     lambda s: s.update(required=['v']), lambda s: s.update(extra=True),
                     lambda s: s['properties']['u'].update(maxItems=True),
                     lambda s: s['properties']['h'].update(enum=['x', 'x']),
                     lambda s: s['properties']['u'].update(minItems=161)]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                response_schema = wire.schema(SOURCE, self.table)
                mutate(response_schema)
                with self.assertRaises(wire.WireError) as exc:
                    wire.lint_schema(response_schema)
                self.assertEqual(exc.exception.code, 'schema_lint')
                # Even if a replacement schema() bypasses its own lint, build rechecks.
                with patch.object(wire, 'schema', return_value=response_schema):
                    for entry in [wire.build, wire.measure]:
                        with self.assertRaises(wire.WireError) as exc:
                            entry(SOURCE)
                        self.assertEqual(exc.exception.code, 'schema_lint')
        # schema itself invokes runtime lint; an invalid operator enum cannot escape.
        with patch.object(r15, 'OPS', ['L', 'L']):
            with self.assertRaises(wire.WireError) as exc:
                wire.schema(SOURCE, self.table)
        self.assertEqual(exc.exception.code, 'schema_lint')

    def test_review_reconstruction_mismatch_hard_guard(self):
        real_span_table = r15.span_table
        def wrong_table(source):
            table = real_span_table(source)
            table['rows'][0][3] += 'tampered'
            return table
        # Patch the generator so validate_table's regenerated table also agrees:
        # only reconstruct's explicit byte check can catch this defect.
        with patch.object(r15, 'span_table', side_effect=wrong_table):
            for entry in [wire.build, wire.measure]:
                with self.assertRaisesRegex(ValueError, '^source_reconstruction$'):
                    entry(SOURCE)
        with patch.object(r15, 'reconstruct', return_value=SOURCE + 'tampered'):
            with self.assertRaises(wire.WireError) as exc:
                wire.build(SOURCE)
        self.assertEqual(exc.exception.code, 'source_reconstruction')

    def test_review_rows_only_exact_unicode_line_endings(self):
        for source in ['one\r\ntwo\rthree\n', 'Ω é 🫧\u2028tail\x85last', 'single row']:
            with self.subTest(source=source):
                plan = wire.build(source)
                user = r15.strict_load(plan['body']['messages'][1]['content'])
                self.assertEqual(''.join(r[3] for r in user['span_table']['rows']).encode(),
                                 source.encode())
                self.assertEqual(user['source_text_sha256'], r15.source_hash(source))
                self.assertEqual(user['span_table_sha256'], r15.digest(user['span_table']))
                bound = plan['body']['response_format']['json_schema']['schema']['properties']
                self.assertEqual(bound['h']['enum'], [user['source_text_sha256']])
                self.assertEqual(bound['t']['enum'], [user['span_table_sha256']])

    def test_review_only_one_prompt_sentence_changed(self):
        old_wire = wire._load('frozen_w1_prompt', BENCH / 'round16-wire-compat/protocol/wire.py',
                             (BENCH / 'round16-wire-compat/protocol/wire.py').read_bytes())
        old = 'The complete source and span table are supplied.'
        new = ('The complete source is supplied as span-table rows whose exact concatenation '
               'in the supplied table array order is the full source.')
        for profile in ['full', 'opaque']:
            before = old_wire._system_prompt(profile)
            after = wire._system_prompt(profile)
            self.assertEqual(before.count(old), 1)
            self.assertEqual(after, before.replace(old, new) + 'If a unit has several conditions of the same role (if, onlyif, unless or obj), emit a single link of that role to one L leaf whose fragments cover each condition in source order (up to 8). Never emit two links of the same role on one unit.\n')
            self.assertEqual(len(common.encode(after)) - len(common.encode(before)), 82 + len('If a unit has several conditions of the same role (if, onlyif, unless or obj), emit a single link of that role to one L leaf whose fragments cover each condition in source order (up to 8). Never emit two links of the same role on one unit.') + 2)

    def test_T4_both_profiles_lint_and_checker(self):
        for profile, count in [('full', 30), ('opaque', 25)]:
            stats = lint_schema(wire.schema(SOURCE, self.table, profile))
            self.assertEqual(stats['depth'], 8)
            self.assertEqual(stats['objects'], 13)
            self.assertEqual(stats['properties'], 73)
            self.assertEqual(stats['enum_values'], count)

    def test_T4_exact_pinned_draft_schema(self):
        source = (BENCH / 'round14-semantic-contract/source/parsed-body.txt').read_bytes().decode()
        draft = json.loads((BENCH / 'round16-wire-compat/design/schema.draft.json').read_bytes())
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
            wire.validate_response(r15.canonical(self.value).decode(), 'stop', SOURCE, self.table, 'opaque', plan=fixture_plan(SOURCE, 'opaque'))
        self.assertEqual(exc.exception.code, 'wire_schema')

    def test_opaque_valid_authored_whole_clause(self):
        control = next(p for p in corpus() if p[0] == 'revised-control/paired-opaque-complete-clause')
        _, source, compact = control
        table = r15.span_table(source)
        value = wire.from_compact(compact)
        self.assertEqual(common.schema_errors(value, wire.schema(source, table, 'opaque')), [])
        self.assertEqual(wire.validate_response(r15.canonical(value).decode(), 'stop', source, table, 'opaque', plan=fixture_plan(source, 'opaque')),
                         r15.expand(compact, source, table))

    def test_invalid_profiles(self):
        for profile in ['', 'typed', None, 1]:
            with self.subTest(profile=profile):
                with self.assertRaises(ValueError):
                    wire.schema(SOURCE, self.table, profile)
                with self.assertRaises(ValueError):
                    wire.build(SOURCE, profile)
                with self.assertRaises(ValueError):
                    wire.validate_response(r15.canonical(self.value).decode(), 'stop', SOURCE, self.table, profile, plan=fixture_plan(SOURCE, profile))

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
                wire.validate_response('invalid', 'length', SOURCE, self.table, plan=fixture_plan(SOURCE, 'full'))
        self.assertIs(type(exc.exception), ValueError)

    def test_T6_raw_byte_boundary_on_wire(self):
        raw = r15.canonical(self.value).decode()
        size = len(raw.encode())
        self.assertEqual(wire.validate_response(raw + ' ' * (r15.RAW_LIMIT - size), 'stop', SOURCE, self.table, plan=fixture_plan(SOURCE, 'full')),
                         r15.expand(POSITIVE, SOURCE, self.table))
        with patch.object(common, 'schema_errors', side_effect=AssertionError('must not check')):
            with self.assertRaisesRegex(ValueError, '^raw_size$'):
                wire.validate_response(raw + ' ' * (r15.RAW_LIMIT + 1 - size), 'stop', SOURCE, self.table, plan=fixture_plan(SOURCE, 'full'))

    def test_T6_depth_boundary_and_quoted_brackets(self):
        raw = '[' * 64 + '0' + ']' * 64
        r15.strict_load(raw)
        with self.assertRaises(wire.WireError):
            wire.validate_response(raw, 'stop', SOURCE, self.table, plan=fixture_plan(SOURCE, 'full'))
        with patch.object(common, 'schema_errors', side_effect=AssertionError('must not check')):
            with self.assertRaisesRegex(ValueError, '^parser_depth$'):
                wire.validate_response('[' * 65 + '0' + ']' * 65, 'stop', SOURCE, self.table, plan=fixture_plan(SOURCE, 'full'))
        value = copy.deepcopy(self.value)
        value['u'][0]['s'] = '[' * 100 + '"\\[]'
        self.assertEqual(wire.validate_response(r15.canonical(value).decode(), 'stop', SOURCE, self.table, plan=fixture_plan(SOURCE, 'full'))['units'][0]['assertion'],
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
                        wire.validate_response(raw, 'stop', SOURCE, self.table, plan=fixture_plan(SOURCE, 'full'))
                self.assertIs(type(via_wire.exception), type(direct.exception))
                self.assertEqual(str(via_wire.exception), str(direct.exception))

    def test_wire_schema_checked_before_host_validate(self):
        self.value['u'][0]['i'] = True
        with patch.object(r15, 'validate', side_effect=AssertionError('must not validate compact')):
            with self.assertRaises(wire.WireError) as exc:
                wire.validate_response(r15.canonical(self.value).decode(), 'stop', SOURCE, self.table, plan=fixture_plan(SOURCE, 'full'))
        self.assertEqual(exc.exception.code, 'wire_schema')
        self.assertTrue(exc.exception.details)

    def test_T6_escaped_astral_pair_and_exact_codepoints(self):
        self.value['u'][0]['s'] = '🫧' * 280
        expanded = wire.validate_response(json.dumps(self.value, ensure_ascii=True), 'stop', SOURCE, self.table, plan=fixture_plan(SOURCE, 'full'))
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
            self.assertEqual(set(user), {'source_text_sha256', 'span_table', 'span_table_sha256'})
            self.assertEqual(r15.reconstruct(SOURCE, user['span_table']).encode(), SOURCE.encode())
            self.assertEqual(user['source_text_sha256'], r15.source_hash(SOURCE))
            self.assertEqual(user['span_table_sha256'], r15.digest(self.table))
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
        self.assertEqual(measurements['prior_source']['guarded_bytes'], 23931 + 82 + 241)
        self.assertEqual(measurements['disjoint600_u24']['guarded_bytes'], 28942 + 82 + 241)
        self.assertTrue(measurements['prior_source']['under_guard'])
        self.assertTrue(measurements['disjoint600_u24']['under_guard'])

    def test_all_frozen_dependency_and_design_pins(self):
        for directory in [PROTO, BENCH / 'round16-wire-compat/design']:
            manifest = json.loads((directory / 'READY.json').read_bytes())
            for name, digest in manifest['sha256'].items():
                with self.subTest(file=str(directory / name)):
                    self.assertEqual(hashlib.sha256((directory / name).read_bytes()).hexdigest(), digest)
        self.assertEqual(hashlib.sha256(wire.COMMON_PATH.read_bytes()).hexdigest(), wire.COMMON_SHA256)


NEGATIVE_CODES = {name: 'wire_schema' for name in NEGATIVES}
NEGATIVE_CODES.update(whitespace_anchor='text_bound',
                      span_absent_short='fragment_span', node_bad_prefix='node_id',
                      node_leading_zero='node_id', node_out_of_range='node_id_range')


def negative_test(name, mutate):
    def test(self):
        mutate(self.value)
        schema_errors = common.schema_errors(self.value, wire.schema(SOURCE, self.table))
        with self.assertRaises(ValueError) as exc:
            wire.validate_response(r15.canonical(self.value).decode(), 'stop', SOURCE, self.table, plan=fixture_plan(SOURCE, 'full'))
        self.assertEqual(str(exc.exception), NEGATIVE_CODES[name])
        if not schema_errors:
            with self.assertRaises(ValueError) as host:
                r15.validate(wire.to_compact(self.value), SOURCE, self.table)
            self.assertEqual(str(host.exception), NEGATIVE_CODES[name])
    return test


for _name, _mutate in NEGATIVES.items():
    setattr(WireTests, 'test_T3_' + _name, negative_test(_name, _mutate))


def size_receipt():
    prior = (BENCH / 'round14-semantic-contract/source/parsed-body.txt').read_bytes().decode()
    profile = next(p for p in json.loads((SIZING / 'authored-profiles.json').read_bytes())['profiles']
                   if p['id'] == 'disjoint600-u24')
    results = {}
    for name, source in [('prior_source', prior), ('disjoint600_u24', profile['source'])]:
        results[name] = wire.measure(source)
        results[name]['profiles'] = {p: wire.measure(source, p) for p in ['full', 'opaque']}

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
    return dict(revision=wire.REVISION, version=wire.VERSION, envelope_version=wire.ENVELOPE_VERSION,
                provider_calls=0, credentials_accessed=False,
                corpus=dict(cases=len(outcomes), valid=sum(o['r15_error'] is None for o in outcomes),
                            invalid=[o for o in outcomes if o['r15_error'] is not None]),
                schema={p: lint_schema(wire.schema(SOURCE, r15.span_table(SOURCE), p)) for p in ['full', 'opaque']},
                sizing=size_receipt())


if __name__ == '__main__':
    unittest.main(verbosity=2)
