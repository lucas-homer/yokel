"""Assert fixed behavior from Fable's unchanged repros (their exit 0 means reproduced)."""
import ast
import hashlib
from pathlib import Path
import subprocess
import unittest

HERE = Path(__file__).resolve().parent
REVIEW = HERE.parent / 'adapter-review'


class ReproTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        result = subprocess.run(['sh', str(HERE / 'repros/run_all.sh')], cwd=HERE,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        cls.output = result.stdout.decode('utf-8')
        (HERE / 'repro-r1-1.txt').write_bytes(result.stdout)
        cls.sections = {}
        for section in cls.output.split('### ')[1:]:
            name, text = section.split('\n', 1)
            cls.sections[name] = text
        if len(cls.sections) != 8:
            raise AssertionError('expected eight review repros')

    def section(self, name):
        return self.sections['repro_' + name + '.py']

    def test_copies_changed_only_adapter_import_path(self):
        for path in (HERE / 'repros').iterdir():
            want = (REVIEW / path.name).read_bytes()
            if path.name == '_load.py':
                want = want.replace(b"HERE.parent / 'adapter'", b'HERE.parent')
            self.assertEqual(path.read_bytes(), want, path.name)

    def test_s1_no_sensitive_headers(self):
        text = self.section('headers_leak')
        self.assertIn('synthetic bearer token: False', text)
        self.assertIn('contains set-cookie: False', text)

    def test_s2_one_post_clean_chain(self):
        text = self.section('double_post_lock_break')
        self.assertIn('POSTs for S1-OPQ: 1', text)
        self.assertIn('ledger chain loads cleanly: True', text)

    def test_s3_recoverable_no_bricked_ledger(self):
        text = self.section('gate_change_bricks_ledger')
        self.assertIn('POSTs so far: 1', text)
        self.assertIn('recover(): OK', text)
        self.assertIn('ledger_impossible_skip): False', text)

    def test_n1_next_cell_refused(self):
        self.assertIn('Refused: recovery_required', self.section('incomplete_cell_allows_next'))
        self.assertNotIn('S2-OPQ admitted and dispatched', self.section('incomplete_cell_allows_next'))

    def test_n2_fsync_failure_no_post_recovery_required(self):
        text = self.section('mark_fsync_failure')
        self.assertIn('POSTs: 0', text)
        self.assertIn('next invocation refused with: recovery_required', text)
        self.assertNotIn('ledger_chain', text)
        self.assertNotIn('ledger_dispatch_debit', text)

    def test_n3_recovery_no_op(self):
        text = self.section('recover_rehalts_completed')
        self.assertIn('recover() returned []', text)
        lines = text.splitlines()
        before = next(line.split(': ', 1)[1] for line in lines if line.startswith('entries before:'))
        after = next(line.split(': ', 1)[1] for line in lines if line.startswith('entries after :'))
        self.assertEqual(ast.literal_eval(before), ast.literal_eval(after))
        self.assertEqual(ast.literal_eval(after).count('HALT'), 1)

    def test_n4_torn_receipt_recovery_succeeds(self):
        self.assertIn('recover succeeded', self.section('partial_receipt_bricks_recover'))

    def test_n5_no_negative_sleep(self):
        self.assertIn('no error', self.section('negative_sleep'))

if __name__ == '__main__':
    unittest.main(verbosity=2)
