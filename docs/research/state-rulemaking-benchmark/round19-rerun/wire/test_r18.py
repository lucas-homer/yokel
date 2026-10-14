"""A7 prompt-only proof and mechanical regression; never score the R17 output."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
def load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m
w = load('r18_wire_regression', HERE/'wire.py')
old = load('r17_frozen_wire', w.BENCH/'round18-rerun/wire/wire.py')
SENTENCE = ('If a unit has several conditions of the same role (if, onlyif, unless or obj), '
    'emit a single link of that role to one L leaf whose fragments cover each condition in '
    'source order (up to 8). Never emit two links of the same role on one unit.')
PAID = w.BENCH/'round17-paid-comparison/run-live/stage-run/r17-s1-opq-20261014t180207z-89a07a81'

class A5Tests(unittest.TestCase):
    def test_only_prompt_and_version_text_changes(self):
        original = Path(old.__file__).read_text()
        expected = original.replace('r16.w2.2', 'r16.w2.3').replace('r16.e3', 'r16.e4')
        expected = expected.replace('    return prompt\n', "    if profile == 'opaque':\n        prompt += 'For an exemption or exception, preserve the exact exempted case and exemption wording in the linked L leaf even when already stated in the unit assertion, using if when the unit asserts the exemption itself and unless when the clause carves out of the unit assertion; explanatory reasons alone do not preserve the exempted case.\\n'\n    return prompt\n")
        self.assertEqual((HERE/'wire.py').read_text(), expected)
        for profile in ('opaque', 'full'):
            before = old.build('Operators must file notices.', profile)
            after = w.build('Operators must file notices.', profile)
            self.assertEqual(after['body']['messages'][0]['content'], before['body']['messages'][0]['content'] + ('For an exemption or exception, preserve the exact exempted case and exemption wording in the linked L leaf even when already stated in the unit assertion, using if when the unit asserts the exemption itself and unless when the clause carves out of the unit assertion; explanatory reasons alone do not preserve the exempted case.\n' if profile == 'opaque' else ''))
            self.assertEqual(after['body']['response_format'], before['body']['response_format'])
            self.assertEqual(after['table'], before['table'])

    def test_merged_unit51_validates_original_still_role_cardinality(self):
        raw = (PAID/'content.body').read_bytes()
        original = json.loads(raw)
        prior_plan = json.loads((PAID/'plan.json').read_bytes())
        source = ''.join(row[3] for row in prior_plan['table']['rows'])
        plan = w.build(source, 'opaque')
        self.assertEqual(plan['table'], prior_plan['table'])
        with self.assertRaisesRegex(ValueError, '^role_cardinality$'):
            w.validate_response(raw.decode(), 'stop', source, plan['table'], 'opaque', plan=plan)
        merged = copy.deepcopy(original)
        links = [l for l in merged['l'] if l['u'] == 51 and l['w'] == 'if']
        self.assertEqual(len(links), 2)
        leaves = {n['i']: n for n in merged['g']}
        left, right = (leaves[l['n']] for l in links)
        self.assertEqual((left['o'], right['o']), ('L', 'L'))
        self.assertEqual((len(left['x']), len(right['x'])), (1, 1))
        left['x'] += right['x']
        merged['l'].remove(links[1])
        self.assertFalse(any(l['n'] == right['i'] for l in merged['l']))
        merged['g'].remove(right)
        result = w.validate_response(json.dumps(merged), 'stop', source, plan['table'], 'opaque', plan=plan)
        self.assertIsInstance(result, dict)
        self.assertEqual((PAID/'content.body').read_bytes(), raw)

if __name__ == '__main__':
    unittest.main(verbosity=2)
