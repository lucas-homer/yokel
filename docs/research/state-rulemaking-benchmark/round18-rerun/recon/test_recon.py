"""Offline one-line amendment proof and frozen original fixture validation."""
import importlib.util
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
ORIGINAL = HERE.parent.parent / 'round17-paid-comparison/design-r3-1/fixtures'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class ReconTests(unittest.TestCase):
    def test_a6_recon_baseline_and_close_retention(self):
        amended = load('recon_a6', HERE / 'r17recon.py')
        u0 = 59_408_500
        pinned = dict(limit=amended.KEY_MAX, limit_reset=None, key_initial_usage=u0)
        def read(u):
            return dict(usage=u, limit=amended.KEY_MAX, limit_reset=None)
        self.assertEqual(amended.reconcile(1, 10_000_000, u0, pinned, [(0, read(u0+10_000_000))]), ('RECONCILED', u0+10_000_000))
        self.assertEqual(amended.reconcile(1, 10_000_000, u0, pinned, [(0, read(u0-1))]), ('HALT', 'usage regressed or invalid'))
        self.assertEqual(amended.reconcile(1, 10_000_000, u0, pinned, [(0, read(u0+10_001_001))]), ('HALT', 'usage exceeds reported cost'))
        self.assertTrue(amended.key_limit_ok(amended.KEY_MAX, 3, u0))
        self.assertFalse(amended.key_limit_ok(amended.KEY_MAX, 3, amended.KEY_MAX-3*amended.FLOOR+1))
        entries = [dict(type='INIT', key_initial_usage=u0)]
        self.assertEqual(amended.close_debit(entries, u0+10_000_000), 10_000_000)

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
