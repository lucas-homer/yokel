"""A4 offline regressions: synthetic evidence/transports and original L01–L25."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('a4_harness', HERE / 'test_adapter.py')
t = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)
a = t.a


class A4Tests(unittest.TestCase):
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

    def bind(self):
        h = self.h
        h.release['init_sha256'] = a.sha(a.encode(h.init))
        h.save_release()
        h.rewrite_ledger([h.init, dict(type='BIND_RELEASE', release_policy='P-HARD',
                                     release_sha256=a.sha(h.release_path.read_bytes()))])

    def refused_init(self, field, value, reason):
        self.h.init[field] = value
        self.bind()
        with self.assertRaisesRegex(a.Refused, reason):
            self.h.execute()
        self.assertEqual(self.h.posts, [])

    def refused_artifact(self, role, field, value, reason):
        h = self.h
        artifact = h.release['artifacts'][role]
        data = a.read(h.root / artifact['path'])
        data[field] = value
        h.release['artifacts'][role] = h.write(artifact['path'], data)
        self.bind()
        with self.assertRaisesRegex(a.Refused, reason):
            h.execute()
        self.assertEqual(h.posts, [])

    def test_50_nonresetting_zero_usage_three_call_plan_admitted(self):
        h = self.h
        self.assertEqual(a.KEY_LABEL, 'DocketClock')
        self.assertEqual(h.init['key_limit'], 50_000_000_000)
        self.assertIsNone(h.init['key_limit_reset'])
        self.assertEqual(h.init['key_initial_usage'], 0)
        for index, cell in enumerate(a.CALLS[:3]):
            gate = h.stage() if index else None
            h.queue = [t.packet(index * 10_000_000), t.packet((index + 1) * 10_000_000)]
            result = h.execute(cell, f'a4-{index}', staged_path=gate)
            self.assertEqual(result['state'], 13)
        self.assertEqual(len(h.posts), 3)
        self.assertEqual(result['aggregate'], 810_000_000)

    def test_above_50_refused(self):
        self.refused_init('key_limit', 50_000_000_001, 'key_limit')

    def test_resetting_key_refused(self):
        self.refused_init('key_limit_reset', 'monthly', 'init_constants')

    def test_negative_initial_usage_refused(self):
        self.refused_init('key_initial_usage', -1, 'init_constants')

    def test_wrong_label_refused(self):
        self.refused_init('key_label', 'yokel-r17-paid-comparison', 'init_namespace_key')

    def test_wrong_attestation_label_refused(self):
        self.refused_artifact('key_attestation', 'key_label', 'wrong', 'K3_attestation')

    def test_resetting_machine_key_refused(self):
        self.refused_artifact('machine_check', 'limit_reset', 'daily', 'K3_machine_check')

    def test_nonzero_machine_usage_refused(self):
        self.refused_artifact('machine_check', 'usage', 1, 'K3_machine_check')

    def test_operating_bound_refuses_seventh_floor_regardless_of_key_limit(self):
        self.assertEqual((a.recon.FLOOR, a.recon.OPERATING, a.recon.CAP),
                         (270_000_000, 1_800_000_000, 2_000_000_000))
        for limit in (1_730_000_000, 50_000_000_000, 500_000_000_000):
            with self.subTest(limit=limit):
                calls = [f'call-{i}' for i in range(7)]
                entries = [dict(type='INIT', required_calls=calls, key_limit=limit,
                                release_policy='P-ACCEPT'),
                           dict(type='BIND_RELEASE', release_policy='P-ACCEPT')]
                self.assertEqual(a.recon.admit(entries, calls[0], 0), (False, 'operating limit'))
                # Six completed FLOOR debits + a seventh remaining reservation.
                for cell in calls[:6]:
                    entries += [dict(type='RESOLVE', call=cell, dispatched=True, debit=a.recon.FLOOR),
                                dict(type='RECONCILED', call=cell)]
                self.assertEqual(a.recon.admit(entries, calls[6], 0), (False, 'operating limit'))
                # A three-call plan still reserves every remaining call, not only the next.
                entries = [dict(type='INIT', required_calls=calls[:3], key_limit=limit,
                                release_policy='P-ACCEPT'),
                           dict(type='BIND_RELEASE', release_policy='P-ACCEPT'),
                           dict(type='RECONCILE_UP', debit=1_000_000_000)]
                self.assertEqual(a.recon.admit(entries, calls[0], 0), (False, 'operating limit'))

    def test_original_L01_L25_only_L18_changes(self):
        checker = t.checker
        original = checker.L
        changes = []
        try:
            for case in t.cases:
                checker.L = original
                count, failures = checker.run_ledger(dict(ledger=dict(cases=[copy.deepcopy(case)])))
                self.assertEqual((count, failures), (1, []), case['id'])
                checker.L = a.recon
                count, failures = checker.run_ledger(dict(ledger=dict(cases=[copy.deepcopy(case)])))
                self.assertEqual(count, 1)
                if failures:
                    changes.append(case['id'])
                    self.assertEqual(failures, [
                        'L18-key-limit-bounds: expected [True, False, True, False], got [True, True, True, False]'])
            self.assertEqual(changes, ['L18-key-limit-bounds'])
            print('L01–L25: only L18 changes; $1.74 / six calls: False -> True. Other 24 unchanged.')
        finally:
            checker.L = original


if __name__ == '__main__':
    unittest.main(verbosity=2)
