import copy
import unittest
from compact import *

class CompactTests(unittest.TestCase):
    def setUp(self):
        self.s='é🫧 first\r\nrepeat\nrepeat\n\nlast e\u0301'
        self.t=span_table(self.s)
        self.v=dict(v=VERSION,h=source_hash(self.s),t=digest(self.t),z='END',u=[dict(i=1,k=4,s='Named endpoint.',m=0,c='',d=[],b=[],e=['s2','s3'],q=0,r=''),dict(i=2,k=5,s='Actor uses endpoint for questions only.',m=2,c='if asking a question',d=[1],b=[],e=['s1'],q=0,r=''),dict(i=3,k=8,s='Source function unresolved.',m=5,c='',d=[],b=[],e=['s5'],q=3,r='Source does not establish function.')])
    def test_source_reconstruction_unicode_linebreaks_no_normalization(self):
        for s in [self.s,'a\r\nb\r\nc','x\n','a\u2028b','aaa','a\n\na']:
            self.assertEqual(reconstruct(s,span_table(s)).encode(),s.encode())
    def test_full_field_roundtrip_preserves_defaults_and_literal_condition(self):
        self.assertEqual(contract(expand(self.v,self.s,self.t),self.s,self.t),self.v)
        self.v['u'][0]['c']='unconditional'
        self.assertEqual(contract(expand(self.v,self.s,self.t),self.s,self.t),self.v)
    def test_repetition_evidence_occurrences_and_host_ids(self):
        ev=expand(self.v,self.s,self.t)['units'][0]['evidence']
        self.assertEqual([e['quote'] for e in ev],['repeat\n','repeat\n'])
        self.assertEqual([e['occurrence'] for e in ev],[1,2])
        self.assertNotEqual(ev[0]['start'],ev[1]['start'])
    def test_unknown_refs_duplicates_and_cycles(self):
        for mutate in [lambda v:v['u'][0].update(e=['missing']),lambda v:v['u'][0].update(e=['s1','s1']),lambda v:v['u'][0].update(d=[99]),lambda v:v['u'][0].update(d=[1]),lambda v:v['u'].append(copy.deepcopy(v['u'][0]))]:
            v=copy.deepcopy(self.v);mutate(v)
            with self.assertRaises(ValueError):validate(v,self.s,self.t)
    def test_type_bounds_closed_keys_defaults_not_omissions(self):
        for mutate in [lambda v:v['u'][0].update(i=True),lambda v:v['u'][0].update(k=9),lambda v:v['u'][0].pop('c'),lambda v:v.update(extra=True),lambda v:v['u'][0].update(s=' '),lambda v:v['u'][0].update(d=[True])]:
            v=copy.deepcopy(self.v);mutate(v)
            with self.assertRaises(ValueError):validate(v,self.s,self.t)
    def test_contradictions_modality_uncertainty_and_roles(self):
        for mutate in [lambda v:v['u'][0].update(q=0,r='unknown'),lambda v:v['u'][0].update(q=1,r=''),lambda v:v['u'][0].update(m=5),lambda v:v['u'][1].update(d=[]),lambda v:v['u'][1].update(d=[3]),lambda v:v['u'][0].update(k=7,d=[])]:
            v=copy.deepcopy(self.v);mutate(v)
            with self.assertRaises(ValueError):validate(v,self.s,self.t)
    def test_truncation_and_marker_cannot_salvage_prefix(self):
        for raw in ['{"u":[','{"z":"END"','{"z":"END"} trailing','{"x":1,"x":2}','{"x":{"i":1,"i":2}}','NaN','1e999']:
            with self.assertRaises(ValueError):strict_load(raw)
        with self.assertRaises(ValueError):validate(self.v,self.s,self.t,'length')
        v=copy.deepcopy(self.v);v['z']=''
        with self.assertRaises(ValueError):validate(v,self.s,self.t)
    def test_stale_source_or_partition_rejected(self):
        t=copy.deepcopy(self.t);t['rows'][0][2]-=1
        with self.assertRaises(ValueError):validate(self.v,self.s,t)
        with self.assertRaises(ValueError):validate(self.v,self.s+' ',self.t)
        v=copy.deepcopy(self.v);v['h']='0'*64
        with self.assertRaises(ValueError):validate(v,self.s,self.t)
    def test_members_distinct_from_acyclic_dependencies(self):
        v=copy.deepcopy(self.v)
        for i,b in [(4,[1,5]),(5,[2,4])]:
            v['u'].append(dict(i=i,k=7,s='Synthetic relation; independent member links.',m=0,c='',d=[],b=b,e=['s1'],q=0,r=''))
        self.assertEqual(contract(expand(v,self.s,self.t),self.s,self.t),v)
        v['u'][-1]['b']=[1,99]
        with self.assertRaises(ValueError):validate(v,self.s,self.t)

    def test_raw_response_and_capacity_boundary(self):
        self.assertEqual(validate_response(canonical(self.v).decode(),'stop',self.s,self.t)['compact'],self.v)
        for raw in ['{"v":"r14.2","v":"r14.2"}',canonical(self.v).decode()[:-1]]:
            with self.assertRaises(ValueError):validate_response(raw,'stop',self.s,self.t)
        v=copy.deepcopy(self.v);v['u']=[dict(i=i,k=8,s='Artificial distinct fixture.',m=0,c='',d=[],b=[],e=['s1'],q=0,r='') for i in range(1,161)]
        with self.assertRaisesRegex(ValueError,'capacity'):validate(v,self.s,self.t)

    def test_public_inverse_rejects_altered_expanded_evidence(self):
        for key,value in [('quote','changed'),('start',0),('end',0),('occurrence',99)]:
            ex=expand(self.v,self.s,self.t);ex['units'][0]['evidence'][0][key]=value
            with self.assertRaises(ValueError):contract(ex,self.s,self.t)
        self.assertEqual(self.t['rows'][1][3],'repeat\n')
        t=copy.deepcopy(self.t);t['rows'][1][3]='modified text'
        with self.assertRaises(ValueError):validate(self.v,self.s,t)

    def test_build_is_source_only_and_guard_enforced(self):
        req=build(self.s);user=strict_load(req['body']['messages'][1]['content'])
        self.assertEqual(set(user),{'source_text','source_text_sha256','span_table','span_table_sha256'})
        self.assertEqual(user['source_text'],self.s)
        self.assertLessEqual(req['guarded_bytes'],40000)
        with self.assertRaises(ValueError):build('a'*40000)
    def test_broad_span_not_atomicity_or_completeness_proof(self):
        v=copy.deepcopy(self.v);v['u'][0]['s']='Two potentially independent assertions bundled together.'
        # Contract cannot prove language atomicity. Acceptance must never certify coverage.
        self.assertEqual(expand(v,self.s,self.t)['source_inventory_completeness'],'unverified')
if __name__=='__main__':unittest.main(verbosity=2)
