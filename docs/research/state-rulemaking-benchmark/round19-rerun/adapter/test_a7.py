"""Namespace isolation and exact adapter retarget proof; synthetic transports only."""
import copy
from pathlib import Path
import tempfile
import unittest
import test_adapter as t

a = t.a
HERE = Path(__file__).resolve().parent


class R19IsolationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=t.OUT)
        self.addCleanup(self.tmp.cleanup)
        self.h = t.Harness(self.tmp.name)

    def legacy_release(self, *, legacy_ledger):
        h = self.h
        entries = h.entries()
        legacy_init = copy.deepcopy(entries[0])
        legacy_init['namespace'] = 'r18.paid-rerun.v1'
        h.release['init_sha256'] = a.sha(a.encode(legacy_init))
        h.save_release()
        if legacy_ledger:
            entries[0] = legacy_init
        entries[1]['release_sha256'] = a.sha(h.release_path.read_bytes())
        h.rewrite_ledger(entries)

    def refused_without_effects(self, reason):
        before = (self.h.run / 'ledger.jsonl').read_bytes()
        with self.assertRaisesRegex(a.Refused, reason):
            self.h.execute()
        self.assertEqual((self.h.run / 'ledger.jsonl').read_bytes(), before)
        self.assertEqual(self.h.posts, [])
        self.assertEqual(self.h.key_reads, [])
        self.assertFalse((self.h.run / 'job1').exists())

    def test_r18_namespace_ledger_release_pair_refused_before_reads_or_reserve(self):
        self.legacy_release(legacy_ledger=True)
        self.refused_without_effects('^init_namespace_key$')

    def test_r18_release_cannot_bind_r19_init_even_with_updated_bind_hash(self):
        self.legacy_release(legacy_ledger=False)
        self.refused_without_effects('^release_init_hash$')

    def test_adapter_only_paths_wire_pin_namespace_change(self):
        baseline = (a.BENCH / 'round18-rerun/adapter/r17_adapter.py').read_text()
        old_pin = a.sha((a.BENCH / 'round18-rerun/wire/wire.py').read_bytes())
        expected = baseline.replace('R18 = HERE.parent\nBENCH = R18.parent',
            "R19 = HERE.parent\nBENCH = R19.parent\nR18 = BENCH / 'round18-rerun'")
        expected = expected.replace("R18 / 'wire/", "R19 / 'wire/")
        expected = expected.replace("'r18_wire_pin'", "'r19_wire_pin'")
        expected = expected.replace("NAMESPACE = 'r18.paid-rerun.v1'", "NAMESPACE = 'r19.paid-rerun.v1'")
        expected = expected.replace("WIRE_SHA = '" + old_pin + "'", "WIRE_SHA = '" + a.WIRE_SHA + "'")
        self.assertEqual((HERE / 'r17_adapter.py').read_text(), expected)
        self.assertEqual(a.RECON_SHA, '64794fdda2f345559a5399ccd8e83142a93e621fcb5c6e79842209a4d4c27140')
        self.assertEqual(Path(a.recon.__file__), a.BENCH / 'round18-rerun/recon/r17recon.py')


if __name__ == '__main__':
    unittest.main(verbosity=2)
