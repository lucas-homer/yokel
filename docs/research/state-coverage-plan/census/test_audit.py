"""Offline audit-freeze regression tests; no real capture store or network access."""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HOME = Path(__file__).resolve().parent


def module(name):
    spec = importlib.util.spec_from_file_location(name, HOME / (name+'.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


freeze = module('audit_freeze')
validator = module('validate')


def fixture():
    manifest, completion = [], []
    for prefix, n, accepts in [('u', 20, True), ('r', 30, False)]:
        for i in range(n):
            uid = f'{prefix}{i:02}'
            manifest.append({'entry_id': uid, 'source_id': 'source', 'agency_id': 'agency',
                             'process_id': 'process', 'format': 'text_pdf',
                             'text_layer': 'native', 'publication_cycle': f'cycle-{i%2}',
                             'retrieval': {'result': 'retrieved', 'sha256': 'a'*64},
                             'accounting': {'pagination_or_page_range': 'pages 1–2'},
                             'expected': {'selector': 'whole notice'}})
            completion.extend({'pass': p, 'manifest_entry_id': uid,
                               'candidate_count': int(accepts and p == 'pass_B'),
                               'rejected_count': int(not accepts)}
                              for p in ('pass_A', 'pass_B'))
    return manifest, completion


class AuditTests(unittest.TestCase):
    def test_freeze_before_entropy_reproduce_and_refuse_redraw(self):
        manifest, completion = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            run_path = directory/'run.json'
            original = '{\n    "state": "XX",\n    "audit": {"seed": null},\n    "untouched": [1,  2]\n}\n'
            run_path.write_text(original)
            for name, rows in [('manifest', manifest), ('completion', completion)]:
                (directory/(name+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in rows))
            argv = ['audit_freeze.py', str(directory), '--level', '3',
                    '--minutes-native', '2', '--minutes-scan', '3', '--mandatory', '10']

            def entropy(n):
                frozen = json.loads(run_path.read_text())['audit']
                self.assertEqual(n, 32)
                self.assertIsNone(frozen['seed'])
                self.assertTrue(frozen['frozen_before_seed'])
                self.assertEqual(frozen['frame_hash'], freeze.digest(freeze.canonical(freeze.frame(frozen))))
                self.assertTrue(all(not s['selected_ids'] for s in frozen['strata']))
                return 'b'*64

            with patch.object(sys, 'argv', argv), patch.object(freeze.secrets, 'token_hex', side_effect=entropy) as random:
                with contextlib.redirect_stdout(io.StringIO()):
                    freeze.main()
                random.assert_called_once()
            written = run_path.read_text()
            self.assertTrue(written.startswith('{\n    "state": "XX",\n    "audit": {\n        '))
            self.assertTrue(written.endswith(',\n    "untouched": [1,  2]\n}\n'))
            audit = json.loads(written)['audit']
            self.assertEqual(audit['actual_minutes'], 0)
            self.assertEqual(audit['estimate_minutes'], 26)
            self.assertEqual(len(audit['unit_coverage']), 50)
            for s in audit['strata']:
                sid = s['stratum_id']
                ranked = sorted(s['unit_ids'], key=lambda uid: (
                    hashlib.sha256(('b'*64+'\n'+sid+'\n'+uid).encode()).hexdigest(), uid))
                self.assertEqual(s['selected_ids'], ranked[:s['sample_size']])
                self.assertEqual(s['sample_size'], 2 if s['disposition'] == 'inclusion' else 6)
                self.assertEqual(s['completed_ids'], [])
            reproduced = copy.deepcopy(audit)
            for s in reproduced['strata']:
                s['selected_ids'] = []
            freeze.select(reproduced)
            self.assertEqual(reproduced, audit)
            with patch.object(sys, 'argv', argv), patch.object(freeze.secrets, 'token_hex') as random:
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    freeze.main()
                random.assert_not_called()
            self.assertEqual(run_path.read_text(), written)

    def test_risk_and_coarsening_floors(self):
        self.assertEqual([freeze.required(100, True, n) for n in range(4)], [20]*4)
        self.assertEqual([freeze.required(30, True, n) for n in range(4)], [20, 20, 20, 6])
        self.assertEqual([freeze.required(30, False, n) for n in range(4)], [6, 6, 3, 3])
        self.assertEqual(freeze.required(2, True, 3), 2)
        manifest, completion = fixture()
        manifest[0]['text_layer'] = 'partial'
        strata = freeze.build_strata(manifest, completion, 3, 2, 3)
        scan = next(s for s in strata if 'u00' in s['unit_ids'])
        self.assertTrue(scan['high_risk'])
        self.assertEqual(scan['minutes_per_unit'], 3)
        self.assertEqual(scan['sample_size'], 1)

    def test_validator_default_budget_and_explicit_override(self):
        # Use only the synthetic example, with real C08 validation of estimate AND actual.
        original_load = validator.load
        run_path = HOME/'examples'/'run.json'
        original_run = original_load(run_path)
        for actual_overrun in (False, True):
            run = copy.deepcopy(original_run)
            if actual_overrun:
                run['audit']['actual_minutes'] = 241
            else:
                run['audit']['mandatory_minutes_estimate'] = 235
                run['audit']['estimate_minutes'] = 241

            def load(path):
                return run if path == run_path else original_load(path)

            original_lines = validator.lines

            def lines(path):
                rows = original_lines(path)
                if actual_overrun and path.name == 'adjudications.jsonl':
                    rows = copy.deepcopy(rows)
                    rows[0]['payload']['minutes'] += 211
                return rows

            with patch.object(validator, 'load', side_effect=load), patch.object(validator, 'lines', side_effect=lines):
                with contextlib.redirect_stdout(io.StringIO()):
                    errors = validator.validate(HOME/'examples')
                self.assertTrue(any(e.startswith('C08: review estimate/actual budget') for e in errors), errors)
                run['audit']['review_budget_minutes'] = 600
                with contextlib.redirect_stdout(io.StringIO()):
                    errors = validator.validate(HOME/'examples')
                self.assertFalse(any(e.startswith('C08:') for e in errors), errors)
                # C10's separate shared-ledger limit is intentionally outside this change.


if __name__ == '__main__':
    unittest.main()
