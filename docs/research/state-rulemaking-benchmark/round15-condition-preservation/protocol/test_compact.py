import copy
import unittest
from compact import *
from fictional_controls import *

class ContractTests(unittest.TestCase):
    def setUp(self):
        self.v=fixture();self.t=span_table(SOURCE)
    def reject(self, mutate, code=None):
        v=copy.deepcopy(self.v);mutate(v)
        with self.assertRaisesRegex(ValueError,code or '.'):
            validate(v,SOURCE,self.t)
    def test_full_roundtrip_exact_long_source_and_annotations(self):
        ex=expand(self.v,SOURCE,self.t)
        self.assertGreater(len(LONG),600)
        self.assertEqual(ex['nodes'][9]['evidence'][0]['text'],LONG)
        self.assertEqual(contract(ex,SOURCE,self.t),self.v)
        self.assertEqual(canonical(contract(ex,SOURCE,self.t)),canonical(self.v))
        self.assertEqual(reconstruct(SOURCE,self.t).encode(),SOURCE.encode())
        self.assertEqual(ex['evaluation'],'not_performed');self.assertFalse(ex['action_ready'])
    def test_unknown_reference_keeps_mandatory_and_explicit_states(self):
        ex=expand(self.v,SOURCE,self.t)
        self.assertEqual(ex['units'][1]['modality'],'mandatory')
        self.assertEqual(ex['units'][1]['applicability'],'unknown')
        self.assertTrue(ex['nodes'][-1]['unresolved_reference'])
        self.assertEqual(ex['units'][6]['applicability'],'none_reported')
        self.assertEqual([ex['units'][i]['deadline']['c']['state'] for i in [2,3,4,5]],['stated','absent','stated','ambiguous'])
        self.assertEqual(ex['units'][4]['deadline']['b']['state'],'na')
    def test_boolean_types_closed_legacy_unknown_and_uncertainty(self):
        for mutate in [lambda v:v['u'][0].update(i=True),lambda v:v['u'][0].update(k=1.0),lambda v:v['u'][0].update(c='legacy'),lambda v:v.update(v='r14.2'),lambda v:v['u'][0].update(extra=1),lambda v:v['u'][0].update(s=' '),lambda v:v['u'][6].update(m=5,q=0,r=''),lambda v:v['u'][0].update(q=1,r=''),lambda v:v['g'][0].update(o='X'),lambda v:v['l'][0].update(w='normative')]:
            self.reject(mutate)
    def test_graph_duplicates_orphans_cycles_arity(self):
        for mutate in [lambda v:v['g'].append(copy.deepcopy(v['g'][0])),lambda v:v['g'].append(node('c12')),lambda v:v['g'][0].update(a=['c2','c2']),lambda v:v['g'][0].update(a=['c1','c2']),lambda v:v['g'][0].update(a=['c2','c12']),lambda v:v['g'][0].update(a=['c2']),lambda v:v['g'][1].update(a=['c1','c3']),lambda v:v['g'][2].update(a=['c4']),lambda v:v['g'][-1].update(q=0,r=''),lambda v:v['g'][0].update(o='ALT'),lambda v:v['g'][0].update(o='NOT')]:
            self.reject(mutate)
    def test_link_scope_and_applicability_shape_constraints(self):
        for mutate in [lambda v:v['l'].append(copy.deepcopy(v['l'][0])),lambda v:v['l'].append(link(1,'c10','onlyif')),lambda v:v['l'][0].update(n='c399'),lambda v:v['l'][0].update(u=160),lambda v:v['u'][0].update(p=0),lambda v:v['u'][6].update(p=1),lambda v:v['u'][6].update(p=2,q=0,r=''),lambda v:v['u'][0].update(d=[True]),lambda v:v['u'][0].update(d=[1]),lambda v:v['u'][0].update(b=[2]),lambda v:v['u'][0].update(d=[160])]:
            self.reject(mutate)
    def test_role_and_relationship_rules_remain(self):
        v=fixture();v['u']+= [unit(8,k=4,s='Endpoint named.'),unit(9,k=5,s='Endpoint serves questions.',d=[8]),unit(10,k=7,s='Relationship connects two units.')]
        v['u'][-1]['b']=[8,9]
        self.assertEqual(contract(expand(v,SOURCE,self.t),SOURCE,self.t),v)
        for field,value in [('d',[]),('d',[1])]:
            bad=copy.deepcopy(v);bad['u'][-2][field]=value
            with self.assertRaises(ValueError):validate(bad,SOURCE,self.t)
        bad=copy.deepcopy(v);bad['u'][-1]['b']=[8,10]
        with self.assertRaises(ValueError):validate(bad,SOURCE,self.t)
    def test_deadline_invalid_states_and_kind(self):
        for mutate in [lambda v:v['u'][2].update(k=6),lambda v:v['u'][3]['y']['c'].update(x=[frag('s1','residents')]),lambda v:v['u'][5]['y']['c'].update(r=''),lambda v:v['u'][2]['y']['c'].update(s='na',r='Not applicable'),lambda v:v['u'][3].update(q=0,r=''),lambda v:v['u'][4]['y']['b'].update(x=[]),lambda v:v['u'][2]['y']['z'].update(s='invalid')]:
            self.reject(mutate)
    def test_final_node_error_invalidates_complete_response(self):
        v=fixture();v['g'][-1]['x'][0][1]='absent literal'
        with self.assertRaisesRegex(ValueError,'head_not_found'):validate_response(canonical(v).decode(),'stop',SOURCE,self.t)
    def test_accepted_semantic_negatives_do_not_certify_meaning(self):
        for name,v in semantic_negatives().items():
            with self.subTest(case=name):
                ex=expand(v,SOURCE,self.t)
                self.assertEqual(ex['semantic_validity'],'unverified')
                self.assertEqual(ex['condition_coverage'],'unverified')
                self.assertEqual(contract(ex,SOURCE,self.t),v)
    def test_no_condition_inheritance_through_context_or_shared_evidence(self):
        v=fixture();v['u'][6]['d']=[1];v['u'][6]['e']=['s1']
        ex=expand(v,SOURCE,self.t)
        self.assertEqual(ex['units'][6]['condition_links'],[])
        self.assertEqual(ex['units'][6]['applicability'],'none_reported')
    def test_inverse_rejects_changed_exact_evidence_and_scope_copies(self):
        for mutate in [lambda e:e['nodes'][9]['evidence'][0].update(text='shortened'),lambda e:e['nodes'][9]['evidence'][0].update(end=0),lambda e:e['nodes'][9]['evidence'][0].update(a='s1'),lambda e:e['units'][0]['evidence'][0].update(quote='changed'),lambda e:e['units'][0].update(condition_links=[]),lambda e:e['nodes'][-1].update(unresolved_reference=False),lambda e:e.update(action_ready=True),lambda e:e['units'][2]['deadline']['c']['evidence'][0].update(start=0)]:
            ex=expand(self.v,SOURCE,self.t);mutate(ex)
            with self.assertRaises(ValueError):contract(ex,SOURCE,self.t)
        for key in ['units','nodes','links']:
            ex=expand(self.v,SOURCE,self.t);ex[key]=None
            with self.assertRaises(ValueError):contract(ex,SOURCE,self.t)
    def test_source_binding_stale_table_and_isolated_request(self):
        for key in ['h','t']:
            v=fixture();v[key]='0'*64
            with self.assertRaises(ValueError):validate(v,SOURCE,self.t)
        table=copy.deepcopy(self.t);table['rows'][0][3]='changed'
        with self.assertRaises(ValueError):validate(self.v,SOURCE,table)
        req=build(SOURCE);user=strict_load(req['body']['messages'][1]['content'])
        self.assertEqual(set(user),{'source_text','source_text_sha256','span_table','span_table_sha256'})
        self.assertEqual(user['source_text'],SOURCE)
        self.assertLessEqual(req['guarded_bytes'],40000)
        with self.assertRaisesRegex(ValueError,'full_request_overflow'):build('a'*40000)
        with self.assertRaises(ValueError):build('bad\ud800')

class FragmentTests(unittest.TestCase):
    def test_repeated_overlapping_and_conditional_tail_occurrences(self):
        src='head tail head tail head tail\naaa'
        t=span_table(src)
        a=resolve_fragment(frag('s1','head','tail',ho=1),src,t)
        b=resolve_fragment(frag('s1','head','tail',ho=2),src,t)
        self.assertEqual(b['text'],'head tail');self.assertGreater(b['start'],a['start'])
        c=resolve_fragment(frag('s2','aa',ho=2),src,t)
        self.assertEqual(c['text'],'aa');self.assertEqual(c['start'],t['rows'][1][1]+1)
        for f in [frag('s1','Head','tail'),frag('s1','head','missing'),frag('s1','head','tail',ho=4),frag('s1','head','tail',ho=3,to=2),frag('s1','head','tail',ho=True),frag('s2','aa',end='s1')]:
            with self.assertRaises(ValueError):resolve_fragment(f,src,t)
    def test_crossrow_separators_discontinuous_and_exact_unicode(self):
        src='START é🫧\r\nmiddle\x85third\u2029END e\u0301'
        t=span_table(src)
        ev=resolve_fragment(frag('s1','START','END e\u0301',end='s4'),src,t)
        self.assertEqual(ev['text'].encode(),src.encode())
        es=fragments([frag('s1','START'),frag('s4','END e\u0301')],1,8,src,t)
        self.assertEqual([e['text'] for e in es],['START','END e\u0301'])
        self.assertLess(es[0]['end'],es[1]['start'])
        with self.assertRaises(ValueError):resolve_fragment(frag('s4','END é'),src,t)
        for xs in [[frag('s1','START'),frag('s1','START')],[frag('s4','END'),frag('s1','START')]]:
            with self.assertRaisesRegex(ValueError,'fragment_order_overlap'):fragments(xs,1,8,src,t)

class ParserTests(unittest.TestCase):
    def test_duplicate_trailing_nonfinite_truncated_and_finish_first(self):
        for raw in ['{"x":1,"x":2}','{"x":{"y":1,"y":2}}','{} trailing','NaN','1e999','{"z":"END"','{"x":']:
            with self.assertRaises(ValueError):strict_load(raw)
        with self.assertRaisesRegex(ValueError,'non_stop'):validate_response('not json','length',SOURCE,span_table(SOURCE))
    def test_unicode_scalars_and_depth_byte_guards(self):
        self.assertEqual(strict_load('"\\ud83e\\udee7"'),'🫧')
        for raw in ['"\\ud800"','"\\udc00"','"\\ud800A"']:
            with self.assertRaisesRegex(ValueError,'unpaired_surrogate'):strict_load(raw)
        value=strict_load('['*64+'0'+']'*64)
        for _ in range(64):value=value[0]
        self.assertEqual(value,0)
        with self.assertRaisesRegex(ValueError,'parser_depth'):strict_load('['*65+'0'+']'*65)
        with self.assertRaisesRegex(ValueError,'raw_size'):strict_load(' '*(RAW_LIMIT+1))
        self.assertEqual(strict_load('"'+('['*100)+'"'),'['*100)
        self.assertEqual(strict_load(' '*(RAW_LIMIT-2)+'{}'),{})

if __name__=='__main__':unittest.main(verbosity=2)
