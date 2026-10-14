"""Offline repro: A6 recon semantics with a positive baseline U0 (pure functions, no I/O)."""
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
R18 = HERE.parent
s = importlib.util.spec_from_file_location('r18_recon_under_review', R18 / 'recon/r17recon.py')
r = importlib.util.module_from_spec(s)
s.loader.exec_module(r)
U0 = 59_408_500
PIN = dict(limit=50_000_000_000, limit_reset=None, key_initial_usage=U0)
READS = lambda *us: [(due, dict(usage=u, limit=50_000_000_000, limit_reset=None))
                     for due, u in zip(r.READ_SCHEDULE_S, us)]


class ReconA6(unittest.TestCase):
    def test_admission_exposure_is_still_floor_times_remaining(self):
        calls = ['S1-OPQ', 'S2-OPQ', 'S3-OPQ']
        # Key capacity: absolute usage U0 + FLOOR x remaining must fit the absolute limit.
        tight = U0 + 3 * r.FLOOR
        entries = [dict(type='INIT', required_calls=calls, key_limit=tight, release_policy='P-ACCEPT'),
                   dict(type='BIND_RELEASE', release_policy='P-ACCEPT')]
        self.assertEqual(r.admit(entries, calls[0], U0), (True, None))
        entries[0]['key_limit'] = tight - 1
        self.assertEqual(r.admit(entries, calls[0], U0), (False, 'key capacity'))
        # key_limit_ok subtracts U0 before comparing with FLOOR x required calls.
        self.assertTrue(r.key_limit_ok(tight, 3, U0))
        self.assertFalse(r.key_limit_ok(tight - 1, 3, U0))
        self.assertFalse(r.key_limit_ok(tight, 3, True))     # bool is not an int baseline
        self.assertFalse(r.key_limit_ok(tight, 3, -1))
        # Operating limit stays relative: a large baseline does not consume OPERATING.
        entries[0]['key_limit'] = 50_000_000_000
        self.assertEqual(r.admit(entries, calls[0], 40_000_000_000), (True, None))
        self.assertEqual(r.aggregate(entries), 0)

    def test_reconcile_accepts_only_u0_plus_reported_within_tolerance(self):
        reported = 10_000_000
        self.assertEqual(r.reconcile(1, reported, U0, PIN, READS(U0 + reported)), ('RECONCILED', U0 + reported))
        self.assertEqual(r.reconcile(1, reported, U0, PIN, READS(U0 + reported + 1_000)), ('RECONCILED', U0 + reported + 1_000))
        # Unexplained usage beyond U0 + reported + tol halts.
        self.assertEqual(r.reconcile(1, reported, U0, PIN, READS(U0 + reported + 1_001)), ('HALT', 'usage exceeds reported cost'))
        # Usage that never reaches U0 + reported - tol is never accepted.
        self.assertEqual(r.reconcile(1, reported, U0, PIN, READS(U0, U0, U0, U0)), ('HALT', 'KEY_USAGE_UNRECONCILED'))
        # Reported-but-baseline-sized usage (the pre-A6 reading) is not accepted either.
        self.assertEqual(r.reconcile(1, reported, U0, PIN, READS(reported)), ('HALT', 'usage regressed or invalid'))

    def test_drop_below_last_reconciled_still_halts(self):
        self.assertEqual(r.reconcile(1, 10_000_000, U0, PIN, READS(U0 - 1)), ('HALT', 'usage regressed or invalid'))
        self.assertEqual(r.reconcile(2, 20_000_000, U0 + 10_000_000, PIN, READS(U0 + 9_999_999)),
                         ('HALT', 'usage regressed or invalid'))
        # Drop inside one read sequence (R3-S3) still halts.
        self.assertEqual(r.reconcile(1, 10_000_000, U0, PIN, READS(U0 + 5_000_000, U0 + 4_000_000)),
                         ('HALT', 'usage regressed or invalid'))

    def test_missing_key_initial_usage_fails_closed(self):
        # reconcile: baseline defaults to 0, so a genuine U0 + reported read is treated as unexplained.
        legacy = dict(limit=50_000_000_000, limit_reset=None)
        self.assertEqual(r.reconcile(1, 10_000_000, U0, legacy, READS(U0 + 10_000_000)),
                         ('HALT', 'usage exceeds reported cost'))
        # close_debit: a missing baseline over-retains (never under-retains).
        entries = [dict(type='INIT'), dict(type='RESOLVE', call='S1-OPQ', dispatched=True, debit=r.FLOOR)]
        self.assertEqual(r.close_debit(entries, U0 + r.FLOOR), U0)
        entries[0]['key_initial_usage'] = U0
        self.assertEqual(r.close_debit(entries, U0 + r.FLOOR), 0)
        self.assertEqual(r.close_debit(entries, U0 + r.FLOOR + 1), 1)
        self.assertEqual(r.close_debit(entries, U0), 0)

    def test_close_debit_retains_highest_usage_above_baseline(self):
        entries = [dict(type='INIT', key_initial_usage=U0),
                   dict(type='RESOLVE', call='S1-OPQ', dispatched=True, debit=r.FLOOR),
                   dict(type='RESOLVE', call='S2-OPQ', dispatched=True, debit=r.FLOOR)]
        self.assertEqual(r.close_debit(entries, U0 + 2 * r.FLOOR + 5), 5)
        self.assertEqual(r.close_debit(entries, U0 + r.FLOOR), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
