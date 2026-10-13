import copy
import unittest
from compact import *
from fictional_controls import SOURCE, fixture
from revision_controls import *

class RevisionTests(unittest.TestCase):
    def test_inverse_wrong_units_and_evidence_types_fail_valueerror(self):
        base=expand(fixture(),SOURCE,span_table(SOURCE))
        for bad in [None,0,'text',{},()]:
            with self.subTest(units=bad):
                ex=copy.deepcopy(base);ex['units']=bad
                with self.assertRaisesRegex(ValueError,'units must be a list'):contract(ex,SOURCE,span_table(SOURCE))
            with self.subTest(evidence=bad):
                ex=copy.deepcopy(base);ex['units'][0]['evidence']=bad
                with self.assertRaisesRegex(ValueError,'evidence must be a list'):contract(ex,SOURCE,span_table(SOURCE))
    def test_authored_actor_and_arrival_clock_zone_distinctions_preserved(self):
        v=fixture();ex=expand(v,SOURCE,span_table(SOURCE))
        self.assertEqual(ex['units'][1]['assertion'],'An unspecified actor is directed to send remarks by the deadline.')
        self.assertEqual(ex['units'][1]['uncertainty_reason'],'Actor is not stated; bare directive does not settle mandatory versus advisory force.')
        self.assertEqual([u['assertion'] for u in ex['units'][20:24]],['In-person arrival cutoff clock is 09:00.','In-person arrival cutoff timezone is UTC.','Requests cutoff clock is stated as 12:00 or 13:00, unresolved.','Requests cutoff timezone is UTC.'])
        self.assertEqual([u['required_unit_ids'] for u in ex['units'][20:24]],[[19],[19],[20],[20]])
        self.assertEqual(contract(ex,SOURCE,span_table(SOURCE)),v)
    def test_unicode_separator_partition_and_capacity_sentinel(self):
        source='a\vb\fc\x1cd\x1de\x1ef\x85g\u2028h\u2029i\rj\r\nk\nl'
        table=span_table(source)
        self.assertEqual(len(table['rows']),12)
        self.assertEqual(reconstruct(source,table).encode(),source.encode())
        v=fixture();v['u']=[dict(i=i,k=8,s='Dimensional unit.',m=0,c='',d=[],b=[],e=['s1'],q=0,r='') for i in range(1,161)]
        self.assertEqual(schema(SOURCE,span_table(SOURCE))['properties']['u']['maxItems'],160)
        with self.assertRaisesRegex(ValueError,'capacity'):validate(v,SOURCE,span_table(SOURCE))
    def test_long_qualifications_reject_without_mutation_or_clipping(self):
        for key,v in overflow_controls().items():
            with self.subTest(field=key):
                raw=canonical(v).decode();original=copy.deepcopy(v)
                self.assertGreater(len(v['u'][0][key]),280 if key=='s' else 180)
                with self.assertRaisesRegex(ValueError,'text bound'):validate_response(raw,'stop',LONG_SOURCE,span_table(LONG_SOURCE))
                self.assertEqual(v,original);self.assertEqual(canonical(v).decode(),raw)
    def test_illustration_leakage_is_a_semantic_failure_not_host_detection(self):
        v=leakage_control();ex=expand(v,LEAKAGE_SOURCE,span_table(LEAKAGE_SOURCE))
        self.assertEqual(ex['units'][0]['evidence'][0]['quote'],LEAKAGE_SOURCE)
        self.assertEqual(ex['units'][0]['assertion'],'Remarks deadline date is April 9, 2031.')
        self.assertEqual(ex['source_inventory_completeness'],'unverified')
        self.assertFalse(ex['action_ready'])
        self.assertNotIn(LEAKAGE_SOURCE,(ROOT/'stage-a.system.txt').read_text())
        self.assertNotIn(LONG_SOURCE,(ROOT/'stage-a.system.txt').read_text())
if __name__=='__main__':unittest.main(verbosity=2)
