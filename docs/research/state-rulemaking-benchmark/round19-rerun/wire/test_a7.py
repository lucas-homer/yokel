"""Exact A7-only delta on all frozen sources-r2, both profiles; offline only."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent.parent
SENTENCE = ('For an exemption or exception, preserve the exact exempted case and exemption '
    'wording in the linked L leaf even when already stated in the unit assertion, using if '
    'when the unit asserts the exemption itself and unless when the clause carves out of '
    'the unit assertion; explanatory reasons alone do not preserve the exempted case.')


def load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


w = load('r19_a7_wire', HERE / 'wire.py')
old = load('r18_a7_baseline', BENCH / 'round18-rerun/wire/wire.py')
SOURCES = BENCH / 'round17-paid-comparison/sources-r2'
SOURCE_IDS = ('26-19-039', '26-19-041', '26-19-106')


def plans():
    ready = json.loads((SOURCES / 'READY.json').read_bytes())
    assert ready['selected'] == list(SOURCE_IDS)
    for sid in SOURCE_IDS:
        raw = (SOURCES / sid / 'parsed-body.txt').read_bytes()
        assert hashlib.sha256(raw).hexdigest() == ready['files'][sid + '/parsed-body.txt']['sha256']
        source = raw.decode('utf-8')
        for profile in ('opaque', 'full'):
            yield sid, profile, old.build(source, profile), w.build(source, profile)


class A7Tests(unittest.TestCase):
    def test_opaque_prompt_exact_normative_append_after_a5(self):
        amendment = (HERE.parent / 'amendments/A7.md').read_text()
        self.assertIn('> "' + SENTENCE + '"\n', amendment)
        before, after = old._system_prompt('opaque'), w._system_prompt('opaque')
        self.assertEqual(after.encode(), before.encode() + (SENTENCE + '\n').encode())
        self.assertTrue(before.endswith('Never emit two links of the same role on one unit.\n'))
        self.assertEqual(after.count(SENTENCE), 1)

    def test_full_prompt_byte_identical_to_r18(self):
        self.assertEqual(w._system_prompt('full').encode(), old._system_prompt('full').encode())

    def test_all_other_body_keys_equal_all_three_sources_both_profiles(self):
        for sid, profile, before, after in plans():
            with self.subTest(source=sid, profile=profile):
                self.assertEqual(before['table'], after['table'])
                expected = copy.deepcopy(before['body'])
                if profile == 'opaque':
                    expected['messages'][0]['content'] += SENTENCE + '\n'
                self.assertEqual(after['body'], expected)
                self.assertEqual(set(after['body']), set(before['body']))
                self.assertEqual(after['body']['messages'][1:], before['body']['messages'][1:])
                self.assertEqual(after['body']['messages'][0]['role'], 'system')
                if profile == 'full':
                    self.assertEqual(w.common.encode(after['body']), old.common.encode(before['body']))

    def test_six_requests_under_40000_guard_with_size_receipt(self):
        measurements = []
        for sid, profile, before, after in plans():
            with self.subTest(source=sid, profile=profile):
                before_raw = old.common.encode(before['body'])
                raw = w.common.encode(after['body'])
                delta = len(raw) - len(before_raw)
                expected_delta = len(w.common.encode(SENTENCE + '\n')) - 2 if profile == 'opaque' else 0
                self.assertEqual(delta, expected_delta)
                self.assertLess(len(raw) + 1024, 40000)
                measurements.append(dict(source_id=sid, profile=profile,
                    r18_body_bytes=len(before_raw), body_bytes=len(raw),
                    guarded_bytes=len(raw) + 1024, guard_limit=40000,
                    residual_guard_bytes=40000 - len(raw) - 1024, body_byte_delta=delta))
        value = dict(prompt_utf8_byte_delta=dict(opaque=len((SENTENCE + '\n').encode()), full=0),
            encoded_prompt_byte_delta=dict(opaque=len(w.common.encode(SENTENCE + '\n')) - 2, full=0),
            requests=measurements, provider_calls=0, network_calls=0)
        (HERE.parent / '_out/request-sizes.json').write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
        print('R19 A7 request sizes:', json.dumps(value, sort_keys=True))


if __name__ == '__main__':
    unittest.main(verbosity=2)
