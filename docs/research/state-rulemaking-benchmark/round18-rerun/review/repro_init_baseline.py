"""Offline repro: an operator-supplied INIT baseline is not cross-checked by release_records.py,
but every mismatch is refused by the adapter before RESERVE/dispatch (synthetic harness, no network).
Temp dirs live under review/_out only."""
import argparse
import importlib.util
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
R18 = HERE.parent
s = importlib.util.spec_from_file_location('review_a4_fixture', R18 / 'adapter/test_a4.py')
t4 = importlib.util.module_from_spec(s)
s.loader.exec_module(t4)
t, a = t4.t, t4.a
s = importlib.util.spec_from_file_location('review_release_records', R18 / 'release-prep/release_records.py')
rr = importlib.util.module_from_spec(s)
s.loader.exec_module(rr)
U0 = 59_408_500           # the live R18 keycheck candidate (KEY-MACHINE.json, 2026-10-14 18:44Z)


class Fixture(t4.A4Tests):
    """Same fixture as adapter/test_a4.py, but temp dirs under review/_out."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=HERE / '_out')
        self.addCleanup(self.tmp.cleanup)
        self.h = t.Harness(self.tmp.name)
        h = self.h
        artifacts = h.release['artifacts']
        manifest = a.read(h.root / artifacts['scoring_manifest']['path'])
        manifest['typed_testable'] = False
        for source in manifest['sources'].values():
            source['compounds'] = {}
        artifacts['scoring_manifest'] = h.write(artifacts['scoring_manifest']['path'], manifest)
        h.release['typed_testable'] = False
        h.release['required_calls'] = h.init['required_calls'] = a.CALLS[:3]
        h.release['calls'] = {cell: h.release['calls'][cell] for cell in a.CALLS[:3]}
        h.release['thresholds'].update(N_c=0, T4=0)
        self.bind()

    def machine(self, usage):
        h = self.h
        item = h.release['artifacts']['machine_check']
        m = a.read(h.root / item['path'])
        m.update(usage=usage, limit_remaining=h.init['key_limit'] - usage)
        h.release['artifacts']['machine_check'] = h.write(item['path'], m)

    def runTest(self):
        pass


class InitBaseline(unittest.TestCase):
    def setUp(self):
        self.f = Fixture()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.h = self.f.h

    def test_release_records_accepts_any_nonnegative_int_silently(self):
        for wrong in (0, 5_940_850, 594_085_000, 59, 59_408_500_000):
            record = rr.init_record(a, b'budget', wrong)          # no KEY-MACHINE cross-check here
            self.assertEqual(record['key_initial_usage'], wrong)
        # A USD-looking decimal cannot pass the int argument type.
        p = argparse.ArgumentParser()
        p.add_argument('--key-initial-usage', type=int, required=True)
        with self.assertRaises(SystemExit):
            p.parse_args(['--key-initial-usage', '0.0594085'])
        for bad in (-1, True, 1.5, '59408500', None):
            with self.subTest(bad=bad), self.assertRaises(a.Refused):
                rr.init_record(a, b'budget', bad)

    def test_wrong_init_baseline_refused_at_k3_before_any_read_or_post(self):
        self.f.machine(U0)
        for n, wrong in enumerate((0, 5_940_850, 594_085_000)):
            with self.subTest(wrong=wrong):
                self.h.init['key_initial_usage'] = wrong
                self.f.bind()
                self.h.queue = [t.packet(U0), t.packet(U0 + 10_000_000)]
                with self.assertRaisesRegex(a.Refused, 'K3_machine_check'):
                    self.h.execute('S1-OPQ', f'k3-{n}')
                self.assertEqual(self.h.posts, [])
                self.assertEqual(self.h.entries()[-1]['type'], 'BIND_RELEASE')

    def test_correlated_typo_in_init_and_machine_check_refused_by_live_preflight(self):
        # Even if the hand-authored KEY-MACHINE carries the same wrong number, the first call's
        # pre-dispatch key read must equal U0 exactly (count of DISPATCH_MARK is 0 => tolerance 0).
        for n, wrong in enumerate((0, U0 - 1, U0 + 1, 5_940_850)):
            with self.subTest(wrong=wrong):
                self.h.init['key_initial_usage'] = wrong
                self.f.machine(wrong)
                self.f.bind()
                self.h.queue = [t.packet(U0), t.packet(U0 + 10_000_000)]
                with self.assertRaisesRegex(a.Refused, 'pre_dispatch_pause'):
                    self.h.execute('S1-OPQ', f'pre-{n}')
                self.assertEqual(self.h.posts, [])
                self.assertFalse(any(e['type'] == 'RESERVE' for e in self.h.entries()))

    def test_usd_scale_typo_refused_by_key_limit(self):
        wrong = 59_408_500_000                                    # $59.41: an extra 10^3 factor
        self.h.init['key_initial_usage'] = wrong
        self.f.machine(wrong)
        self.f.bind()
        with self.assertRaisesRegex(a.Refused, 'key_limit'):
            self.h.execute()
        self.assertEqual(self.h.posts, [])

    def test_correct_baseline_dispatches_once_and_debits_only_run_cost(self):
        self.h.init['key_initial_usage'] = U0
        self.f.machine(U0)
        self.f.bind()
        self.h.queue = [t.packet(U0), t.packet(U0 + 10_000_000)]
        result = self.h.execute()
        self.assertEqual((result['state'], result['halt'], len(self.h.posts)), (13, None, 1))
        self.assertEqual(result['aggregate'], a.recon.FLOOR)
        self.assertEqual(result['key_usage_delta'], 10_000_000)
        self.assertEqual(a.last_usage(self.h.entries()), U0 + 10_000_000)


if __name__ == '__main__':
    unittest.main(verbosity=2, defaultTest='InitBaseline')   # Fixture itself is not a test
