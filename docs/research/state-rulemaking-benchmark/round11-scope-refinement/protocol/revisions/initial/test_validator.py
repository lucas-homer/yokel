import copy
import json
import unittest
from pathlib import Path
from validator import digest, evidence, run_fixtures, strict_load, validate

ROOT = Path(__file__).resolve().parent

class ContractTests(unittest.TestCase):
    def setUp(self):
        self.fixtures = strict_load((ROOT / 'fixtures.json').read_text())
        self.base = copy.deepcopy(self.fixtures[0]['case'])

    def test_adverse_and_positive_annotations(self):
        for row in run_fixtures():
            with self.subTest(fixture=row['id']):
                self.assertTrue(row['pass'], row)

    def test_candidate_changes_do_not_change_frozen_scope(self):
        before = (digest(self.base['inventory']), digest(self.base['scopes']))
        self.base['operative']['d']['value'] = 'June 1'
        self.base['mappings']['d']['status'] = 'mismatched'
        result = validate(self.base)
        self.assertEqual(result['required_defects'], ['d'])
        self.assertEqual(before, (digest(self.base['inventory']), digest(self.base['scopes'])))

    def test_source_addition_requires_expanded_reference(self):
        added = next(x['case'] for x in self.fixtures if x['id'] == 'source_only_new_obligation_unchanged_candidate')
        self.assertEqual(added['operative'], self.base['operative'])
        self.assertNotEqual(digest(added['inventory']), digest(self.base['inventory']))
        self.assertEqual(validate(added)['required_defects'], ['new'])

    def test_classifier_cannot_add_record_access_field(self):
        self.base['scopes']['d']['record_presence'] = False
        with self.assertRaisesRegex(ValueError, 'wrong keys'):
            validate(self.base)

    def test_decisions_cannot_omit_background(self):
        del self.base['scopes']['b']
        with self.assertRaisesRegex(ValueError, 'scope_totality'):
            validate(self.base)

    def test_mappings_cannot_omit_required_unit(self):
        del self.base['mappings']['d']
        with self.assertRaisesRegex(ValueError, 'mapping_totality'):
            validate(self.base)

    def test_cycle_rejected(self):
        self.base['inventory'][2]['dependencies'] = ['q']
        self.base['classified_inventory'] = copy.deepcopy(self.base['inventory'])
        with self.assertRaisesRegex(ValueError, 'dependency cycle'):
            validate(self.base)

    def test_dependency_unknown_does_not_erase_known_defect(self):
        self.base['mappings']['p']['status'] = 'unknown'
        self.base['mappings']['q']['status'] = 'unknown'
        self.base['mappings']['d'] = dict(status='missing', refs=[], reason='Known missing deadline')
        result = validate(self.base)
        self.assertEqual(result['required_scope_status'], 'unverified')
        self.assertEqual(result['required_defects'], ['d'])
        self.assertIn('q', result['required_unknown'])

    def test_reference_must_be_operative(self):
        self.base['mappings']['d']['refs'] = ['evidence/deadline']
        with self.assertRaisesRegex(ValueError, 'unknown operative ref'):
            validate(self.base)

    def test_review_hash_not_self_certification(self):
        self.base['source_review']['inventory_sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'source_review_hash'):
            validate(self.base)

    def test_reverse_audit_requires_all_claims(self):
        self.base['record_audit'].update(status='reviewed', reviewed_refs=['d'])
        with self.assertRaisesRegex(ValueError, 'audit not exhaustive'):
            validate(self.base)

    def test_exact_overlapping_unicode_evidence(self):
        evidence([dict(quote='aa', occurrence=2)], 'aaa')
        evidence([dict(quote='é', occurrence=1)], 'é')
        for item, source in [(dict(quote='aa',occurrence=3),'aaa'),(dict(quote='é',occurrence=1),'e\u0301'),(dict(quote='a',occurrence=True),'a')]:
            with self.assertRaises(ValueError):
                evidence([item],source)

    def test_json_strictness(self):
        for raw in ['{"x":1,"x":2}', '{"nested":{"x":1,"x":2}}', 'NaN', '1e999', '{} {}']:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                strict_load(raw)

if __name__ == '__main__':
    unittest.main(verbosity=2)
