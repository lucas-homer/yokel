"""Synthetic A6 admission, preflight, accounting and K3 regressions."""
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
s = importlib.util.spec_from_file_location('a6_fixture', HERE/'test_a4.py')
t = importlib.util.module_from_spec(s)
s.loader.exec_module(t)
a = t.a
U0 = 59_408_500

class A6Tests(unittest.TestCase):
    def setUp(self):
        self.base = t.A4Tests()
        self.base.setUp()
        self.addCleanup(self.base.doCleanups)
        self.h = self.base.h
        self.set_baseline(U0)

    def set_baseline(self, u0):
        h = self.h
        h.init['key_initial_usage'] = u0
        item = h.release['artifacts']['machine_check']
        machine = a.read(h.root/item['path'])
        machine.update(usage=u0, limit_remaining=h.init['key_limit']-u0)
        h.release['artifacts']['machine_check'] = h.write(item['path'], machine)
        self.base.bind()

    def test_positive_baseline_admitted_and_excluded_from_debit(self):
        self.h.queue = [t.t.packet(U0), t.t.packet(U0+10_000_000)]
        result = self.h.execute()
        self.assertEqual((result['state'], result['halt']), (13, None))
        self.assertEqual(result['aggregate'], a.recon.FLOOR)
        self.assertEqual(a.last_usage(self.h.entries()), U0+10_000_000)

    def test_three_cell_admission_walk_r17_spend_baseline(self):
        h = self.h
        self.assertEqual(a.last_usage(h.entries()), U0)
        for index, cell in enumerate(a.CALLS[:3]):
            gate = h.stage() if index else None
            h.queue = [t.t.packet(U0+index*10_000_000), t.t.packet(U0+(index+1)*10_000_000)]
            result = h.execute(cell, 'a6-'+str(index), staged_path=gate)
            self.assertEqual((result['state'], result['halt']), (13, None))
            self.assertEqual(result['aggregate'], (index+1)*a.recon.FLOOR)
        self.assertEqual(len(h.posts), 3)
        self.assertEqual(a.last_usage(h.entries()), 89_408_500)
        self.assertEqual(result['aggregate'], 810_000_000)

    def test_usage_below_baseline_refused_before_dispatch(self):
        self.h.queue = [t.t.packet(U0-1)]
        with self.assertRaisesRegex(a.Refused, 'pre_dispatch_pause'):
            self.h.execute()
        self.assertEqual(self.h.posts, [])
        self.assertEqual(self.h.entries()[-1]['type'], 'BIND_RELEASE')

    def test_usage_below_baseline_after_dispatch_halts(self):
        self.h.queue = [t.t.packet(U0), t.t.packet(U0-1)]
        self.assertEqual(self.h.execute()['halt'], 'usage regressed or invalid')

    def test_unexplained_usage_above_baseline_and_cost_halts(self):
        self.h.queue = [t.t.packet(U0), t.t.packet(U0+10_000_000+1001)]
        self.assertEqual(self.h.execute()['halt'], 'usage exceeds reported cost')

    def test_preflight_unexplained_above_baseline_refused(self):
        self.h.queue = [t.t.packet(U0+1)]
        with self.assertRaisesRegex(a.Refused, 'pre_dispatch_pause'):
            self.h.execute()
        self.assertEqual(self.h.posts, [])
        self.assertEqual(self.h.entries()[-1]['type'], 'BIND_RELEASE')

    def test_k3_usage_mismatch_refused(self):
        self.base.refused_artifact('machine_check', 'usage', U0+1, 'K3_machine_check')

    def test_k3_remaining_mismatch_refused(self):
        self.base.refused_artifact('machine_check', 'limit_remaining', self.h.init['key_limit'], 'K3_machine_check')

    def test_invalid_baselines_refused(self):
        for value in (-1, True, 1.5, '1', None):
            with self.subTest(value=value):
                self.base.refused_init('key_initial_usage', value, 'ledger_noncanonical' if type(value) is float else 'init_constants')

    def test_baseline_must_leave_capacity_for_all_remaining_calls(self):
        self.set_baseline(a.recon.KEY_MAX-3*a.recon.FLOOR+1)
        with self.assertRaisesRegex(a.Refused, 'key_limit'):
            self.h.execute()
        self.assertEqual(self.h.posts, [])

    def test_close_retention_excludes_even_large_baseline(self):
        entries = [dict(type='INIT', key_initial_usage=40_000_000_000),
                   dict(type='RESOLVE', call='S1-OPQ', dispatched=True, debit=a.recon.FLOOR)]
        self.assertEqual(a.recon.close_debit(entries, 40_010_000_000), 0)
        self.assertEqual(a.recon.close_debit(entries, 40_300_000_000), 30_000_000)

if __name__ == '__main__':
    unittest.main(verbosity=2)
