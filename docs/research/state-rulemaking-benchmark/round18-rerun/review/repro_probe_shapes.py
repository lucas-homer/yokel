"""Offline repro: last_usage() now indexes INIT['key_initial_usage'] directly; a ledger whose INIT
lacks the field is rejected by a KeyError (fail-closed, but not a Refused) on the probe path
(r17_adapter.py main, admission-check) which runs before release_gate validates INIT."""
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
R18 = HERE.parent
s = importlib.util.spec_from_file_location('review_adapter_probe', R18 / 'adapter/r17_adapter.py')
a = importlib.util.module_from_spec(s)
s.loader.exec_module(a)


class ProbeShapes(unittest.TestCase):
    def test_init_without_baseline_is_a_keyerror_not_refused(self):
        with self.assertRaises(KeyError):
            a.last_usage([dict(type='INIT', required_calls=a.CALLS[:3], key_limit=50_000_000_000)])

    def test_reconciled_entries_take_precedence_over_baseline(self):
        entries = [dict(type='INIT', key_initial_usage=7), dict(type='RECONCILED', call='S1-OPQ', U=9)]
        self.assertEqual(a.last_usage(entries), 9)
        self.assertEqual(a.last_usage(entries[:1]), 7)

    def test_empty_ledger_is_a_clean_refusal_before_last_usage(self):
        # Ledger.load refuses an empty file ('empty_ledger') so last_usage([]) is unreachable there.
        import tempfile
        with tempfile.TemporaryDirectory(dir=HERE / '_out') as tmp:
            run = Path(tmp)
            (run / 'ledger.jsonl').write_bytes(b'')
            ledger = a.Ledger(run)
            with ledger.lock('review-probe'):
                with self.assertRaisesRegex(a.Refused, 'empty_ledger'):
                    ledger.load()


if __name__ == '__main__':
    unittest.main(verbosity=2)
