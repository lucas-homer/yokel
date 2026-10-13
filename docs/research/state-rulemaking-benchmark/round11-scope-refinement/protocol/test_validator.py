import copy
import hashlib
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

    def test_same_relation_known_loss_survives_unknown_member(self):
        c = self.review_case('known-loss-with-unknown-member')
        result = validate(c)
        self.assertEqual(result['required_scope_status'], 'unverified')
        self.assertIn('g', result['required_defects'])
        self.assertEqual(result['known_required_defects']['g'], 'mismatched')
        self.assertEqual(result['effective_mappings']['g'], 'unknown')

    def review_case(self, name):
        c = strict_load((ROOT.parent / 'review/adversarial-initial' / (name + '.json')).read_text())['case']
        if c['record_audit']['status'] == 'not_run':
            c['record_audit'].update(source_sha256='', operative_sha256='')
        return c

    def test_reviewed_audit_requires_current_bindings(self):
        c = self.review_case('stale-reverse-audit')
        with self.assertRaises(ValueError):
            validate(c)  # historical unbound audit is no longer accepted

    def reviewed_audit(self, c):
        c['record_audit'] = dict(status='reviewed', source_sha256=hashlib.sha256(c['source'].encode()).hexdigest(), operative_sha256=digest(c['operative']), reviewed_refs=list(c['operative']), unsupported_refs=[], unknown_refs=[])

    def test_audit_projection_binding_invalidated_by_same_ref_mutation(self):
        c = copy.deepcopy(self.base)
        self.reviewed_audit(c)
        self.assertEqual(validate(c)['record_fidelity'], 'reviewer_attestation_only')
        c['operative']['d']['value'] = 'June 1'
        c['mappings']['d']['status'] = 'mismatched'
        with self.assertRaisesRegex(ValueError, 'record_audit_hash'):
            validate(c)

    def test_audit_source_binding_invalidated_by_changed_source(self):
        c = copy.deepcopy(self.base)
        self.reviewed_audit(c)
        c['source'] += ' Additional retained source context.'
        c['source_review']['source_sha256'] = hashlib.sha256(c['source'].encode()).hexdigest()
        with self.assertRaisesRegex(ValueError, 'record_audit_hash'):
            validate(c)

    def test_uncertain_function_basis_cannot_certify_included_scope(self):
        c = self.review_case('unresolved-basis-positive-category')
        with self.assertRaisesRegex(ValueError, 'scope basis/category'):
            validate(c)

    def test_scope_category_basis_correspondence_both_directions(self):
        for category, basis in [('required_participation','substantive_background_only'), ('retained_background','participation_function'), ('identifying_context','uncertain_source_function'), ('unresolved_scope','identifies_proceeding')]:
            c = copy.deepcopy(self.base)
            c['scopes']['b'].update(category=category, basis=basis)
            with self.subTest(category=category, basis=basis), self.assertRaises(ValueError):
                validate(c)

    def test_unmapped_malformed_facet_rejected(self):
        c = self.review_case('malformed-operative-facet')
        with self.assertRaisesRegex(ValueError, 'operative kind'):
            validate(c)

    def test_unmapped_operative_closed_types_enums_and_shapes(self):
        valid = dict(kind='endpoint', value='invented@example.test', modality='descriptive', condition='unconditional', qualifications=[])
        changes = [dict(kind=[]), dict(kind='bad'), dict(value=None), dict(modality='bad'), dict(condition=[]), dict(qualifications=False), dict(qualifications=['same','same']), dict(kind='endpoint_role',value={'endpoint':5,'purpose':'questions'}), dict(kind='endpoint_role',value={'endpoint':'e','purpose':['questions']}), dict(kind='endpoint_role',value={'endpoint':'e','purpose':'questions','extra':True}), dict(kind='relationship',value={'members':['r'],'purpose':'questions','semantics':'substitution'}), dict(kind='relationship',value={'members':['r','r'],'purpose':'questions','semantics':'substitution'}), dict(kind='relationship',value={'members':['r','s'],'purpose':'questions','semantics':[]}), dict(kind='relationship',value={'members':['r','s'],'purpose':'questions','semantics':'independent_permissions'})]
        c = copy.deepcopy(self.base)
        c['operative']['unmapped'] = valid
        self.assertEqual(validate(c)['record_fidelity'], 'unverified')
        for change in changes:
            c = copy.deepcopy(self.base)
            c['operative']['unmapped'] = dict(valid, **change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate(c)

    def test_json_strictness(self):
        for raw in ['{"x":1,"x":2}', '{"nested":{"x":1,"x":2}}', 'NaN', '1e999', '{} {}']:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                strict_load(raw)

if __name__ == '__main__':
    unittest.main(verbosity=2)
