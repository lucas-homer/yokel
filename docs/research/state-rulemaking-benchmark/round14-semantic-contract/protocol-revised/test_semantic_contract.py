import copy
import unittest
from compact import *
from fictional_controls import SOURCE, fixture, semantic_negative_controls

class SemanticContractTests(unittest.TestCase):
    def setUp(self): self.v=fixture();self.t=span_table(SOURCE)
    def test_deadline_dimensions_preserved_without_defaults(self):
        ex=expand(self.v,SOURCE,self.t)
        self.assertEqual(ex['units'][0]['applicability'],'Cutoff clock unknown; timezone unknown; receipt-versus-dispatch unknown.')
        self.assertEqual(ex['units'][2]['applicability'],'Cutoff clock 5 p.m.; timezone Eastern; timeliness basis receipt.')
        self.assertEqual(ex['units'][6]['applicability'],'Cutoff clock unknown; timezone unknown; timeliness basis dispatch.')
        self.assertEqual([ex['units'][i]['uncertainty'] for i in [0,2,6]],['source_ambiguous','none','source_ambiguous'])
        self.assertEqual(contract(ex,SOURCE,self.t),self.v)
    def test_rule_identity_historical_filing_and_dates_remain_separate(self):
        ex=expand(self.v,SOURCE,self.t)
        self.assertEqual([u['id'] for u in ex['units'][8:13]],[9,10,11,12,13])
        self.assertEqual(ex['units'][10]['required_unit_ids'],[9,10])
        self.assertEqual(ex['units'][10]['assertion'],'The amendment affects Rule Q-8; F-17 is the previous filing context.')
        self.assertEqual([u['required_unit_ids'] for u in ex['units'][11:13]],[[10],[10]])
        self.assertEqual([u['evidence'][0]['quote'] for u in ex['units'][8:13]],[self.t['rows'][3][3]]*5)
    def test_atomic_city_province_background_and_unresolved_survive(self):
        ex=expand(self.v,SOURCE,self.t)
        self.assertEqual([u['assertion'] for u in ex['units'][13:15]],['The office city is Alder City.','The office province is North Province.'])
        self.assertEqual(ex['units'][16]['uncertainty'],'function_unresolved')
        self.assertEqual(ex['units'][17]['assertion'],'The commission was founded in 1964.')
        self.assertEqual(''.join(row[3] for row in self.t['rows']).encode(),SOURCE.encode())
    def test_ambiguous_directive_preserved_and_unknown_requires_reason(self):
        ex=expand(self.v,SOURCE,self.t)
        self.assertEqual(ex['units'][1]['modality'],'unknown')
        self.assertEqual(ex['units'][15]['modality'],'advisory')
        v=copy.deepcopy(self.v);v['u'][1].update(q=0,r='')
        with self.assertRaisesRegex(ValueError,'unknown modality'):validate(v,SOURCE,self.t)
    def test_absent_ambiguous_and_inapplicable_states_survive_distinctly(self):
        ex=expand(self.v,SOURCE,self.t)
        self.assertEqual(ex['units'][18]['applicability'],'Cutoff clock 09:00; timezone UTC; receipt-versus-dispatch not applicable: in-person arrival.')
        self.assertEqual(ex['units'][19]['applicability'],'Cutoff clock stated but ambiguous: 12:00 or 13:00; timezone UTC; receipt-versus-dispatch not stated (unknown).')
        self.assertEqual(contract(ex,SOURCE,self.t),self.v)
    def test_semantic_failures_are_not_structural_rejections(self):
        for name,v in semantic_negative_controls().items():
            with self.subTest(name=name):
                self.assertEqual(validate(v,SOURCE,self.t),v)
                ex=expand(v,SOURCE,self.t)
                self.assertEqual(ex['source_inventory_completeness'],'unverified')
                self.assertFalse(ex['production_eligible']);self.assertFalse(ex['action_ready'])
                self.assertEqual(contract(ex,SOURCE,self.t),v)
        v=semantic_negative_controls()['background_dropped_but_all_spans_still_cited']
        self.assertEqual({sid for u in v['u'] for sid in u['e']},{row[0] for row in self.t['rows']})

if __name__=='__main__':unittest.main(verbosity=2)
