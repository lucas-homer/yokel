import copy
import hashlib
import unittest
from scope_codec import encode, decode, digest

class ScopeTransportTests(unittest.TestCase):
    def setUp(self):
        self.source='🫧é aaa aa e\u0301'
        self.ids=['u002','u001']
        self.ih='a'*64
        self.c=dict(schema_version='round12.source-scope.v1',source_text_sha256=hashlib.sha256(self.source.encode()).hexdigest(),inventory_sha256=self.ih,scopes={'u001':dict(category='unresolved_scope',basis='uncertain_source_function',reason='Uncertain function, retained.',evidence=[dict(quote='aa',occurrence=2)]),'u002':dict(category='required_participation',basis='participation_function',reason='Unchanged reason\nwith "quotes" and é.',evidence=[dict(quote='é',occurrence=1),dict(quote='aa',occurrence=3)])})
        self.w=encode(self.c,self.source,self.ih,self.ids)
    def decode(self,w):return decode(w,self.source,self.ih,self.ids,self.c)
    def test_exact_roundtrip_order_unicode_overlap(self):
        self.assertEqual(self.decode(self.w),self.c)
        self.assertEqual(digest(self.decode(self.w)),digest(self.c))
        self.assertEqual([r[0] for r in self.w['scopes']],self.ids)
    def test_closed_envelope_and_row_width(self):
        for mutate in [lambda w:w.update(extra=1),lambda w:w['scopes'][0].append(1),lambda w:w.update(schema_version='other'),lambda w:w.update(columns=['other'])]:
            w=copy.deepcopy(self.w);mutate(w)
            with self.assertRaises(ValueError):self.decode(w)
    def test_schedule_totality_and_order(self):
        for rows in [self.w['scopes'][:1],list(reversed(self.w['scopes'])),[self.w['scopes'][0]]*2,self.w['scopes']+[self.w['scopes'][0]]]:
            w=copy.deepcopy(self.w);w['scopes']=copy.deepcopy(rows)
            with self.assertRaises(ValueError):self.decode(w)
    def test_enum_types_and_correspondence(self):
        for value in [True,-1,4,'0',0.0]:
            w=copy.deepcopy(self.w);w['scopes'][0][1]=value
            with self.assertRaises(ValueError):self.decode(w)
        w=copy.deepcopy(self.w);w['scopes'][0][2]=1
        with self.assertRaises(ValueError):self.decode(w)
    def test_span_types_bounds_and_occurrence(self):
        for span in [[True,2,1],[1,2,True],[-1,2,1],[1,1,1],[1,999,1],[1,2,2],[1,3,1],['1',2,1]]:
            w=copy.deepcopy(self.w);w['scopes'][0][4][0]=span
            with self.assertRaises(ValueError):self.decode(w)
    def test_reason_and_selector_mutation_rejected_by_frozen_equality(self):
        w=copy.deepcopy(self.w);w['scopes'][0][3]='A different valid reason.'
        with self.assertRaisesRegex(ValueError,'frozen C'):self.decode(w)
        w=copy.deepcopy(self.w);w['scopes'][0][4].reverse()
        with self.assertRaisesRegex(ValueError,'frozen C'):self.decode(w)
    def test_source_inventory_and_scope_bindings(self):
        for key in ['source_text_sha256','inventory_sha256']:
            w=copy.deepcopy(self.w);w[key]='0'*64
            with self.assertRaises(ValueError):self.decode(w)
        c=copy.deepcopy(self.c);c['schema_version']='other'
        with self.assertRaises(ValueError):encode(c,self.source,self.ih,self.ids)
    def test_encode_rejects_missing_fields_or_bad_c(self):
        for mutate in [lambda c:c.update(extra=1),lambda c:c['scopes']['u001'].pop('reason'),lambda c:c['scopes']['u001'].update(basis='participation_function'),lambda c:c['scopes']['u001']['evidence'][0].update(occurrence=True)]:
            c=copy.deepcopy(self.c);mutate(c)
            with self.assertRaises(ValueError):encode(c,self.source,self.ih,self.ids)
if __name__=='__main__':unittest.main(verbosity=2)
