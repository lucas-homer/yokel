"""Offline one-line amendment proof and frozen original fixture validation."""
import importlib.util
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
ORIGINAL = HERE.parent / 'design-r3-1/fixtures'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class ReconTests(unittest.TestCase):
    def test_exact_one_line_change(self):
        old = (ORIGINAL / 'r17recon.py').read_bytes()
        new = (HERE / 'r17recon.py').read_bytes()
        self.assertEqual(old.count(b'KEY_MAX = 1_730_000_000'), 1)
        self.assertEqual(new, old.replace(b'KEY_MAX = 1_730_000_000', b'KEY_MAX = 50_000_000_000'))
        self.assertEqual(sum(x != y for x, y in zip(old.splitlines(), new.splitlines())), 1)
        self.assertEqual(len(old.splitlines()), len(new.splitlines()))

    def test_frozen_check_full_suite_original_engine(self):
        c = load('a4_frozen_checker', ORIGINAL / 'check.py')
        self.assertEqual(c.L.KEY_MAX, 1_730_000_000)
        data = json.loads((ORIGINAL / 'cases.json').read_bytes())
        counts, failures = c.run(data)
        self.assertEqual(failures, [])
        self.assertEqual(counts['ledger'], 25)
        print('Frozen original check.py full suite:', json.dumps(counts, sort_keys=True))

    def test_only_exported_constant_changes(self):
        original = load('recon_original', ORIGINAL / 'r17recon.py')
        amended = load('recon_a4', HERE / 'r17recon.py')
        self.assertEqual(amended.KEY_MAX, 50_000_000_000)
        for name in ('CAP', 'OPERATING', 'FLOOR', 'TOL_PER_CALL', 'READ_SCHEDULE_S', 'RELEASE_POLICIES'):
            self.assertEqual(getattr(original, name), getattr(amended, name), name)


if __name__ == '__main__':
    unittest.main(verbosity=2)
