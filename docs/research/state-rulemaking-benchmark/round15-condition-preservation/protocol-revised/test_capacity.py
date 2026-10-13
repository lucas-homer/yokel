import copy
import unittest
from compact import *
from fictional_controls import *

class CapacityTests(unittest.TestCase):
    def test_primary_qual_refinement(self):
        v=fixture();validate(v,SOURCE,span_table(SOURCE))
        for p in [0,1]:
            bad=copy.deepcopy(v);bad['u'][0]['p']=p
            with self.assertRaisesRegex(ValueError,'qual_requires_unknown_scope'):validate(bad,SOURCE,span_table(SOURCE))
        bad=copy.deepcopy(v);bad['l'][1].update(q=0,r='')
        with self.assertRaisesRegex(ValueError,'qual_requires_unknown_scope'):validate(bad,SOURCE,span_table(SOURCE))
    def test_units_and_node_link_capacity_sentinels(self):
        for count in [158,159,160,161]:
            units=[unit(i=i) for i in range(1,count+1)]
            v=envelope(SOURCE,units)
            if count<160:validate(v,SOURCE,span_table(SOURCE))
            else:
                with self.assertRaises(ValueError):validate(v,SOURCE,span_table(SOURCE))
        for count in [398,399,400,401]:
            v=envelope(SOURCE,[unit()], [node(f'c{i}') for i in range(1,count+1)], [link(1,f'c{i}','regardless') for i in range(1,count+1)])
            if count<400:
                validate(v,SOURCE,span_table(SOURCE))
                self.assertEqual(contract(expand(v,SOURCE,span_table(SOURCE)),SOURCE,span_table(SOURCE)),v)
            else:
                with self.assertRaises(ValueError):validate(v,SOURCE,span_table(SOURCE))
        v=envelope(SOURCE,[unit(i=160)], [node('c400')],[link(160,'c400','regardless')])
        validate(v,SOURCE,span_table(SOURCE))
        for bad in ['c0','c01','c401','c1x','c-1','c1\n']:
            with self.assertRaises(ValueError):node_id(bad)
    def test_dag_depth_11_12_13_and_alt_not(self):
        for depth in [11,12,13]:
            nodes=[node(f'c{i}','NOT',[f'c{i+1}'],[]) for i in range(1,depth)] + [node(f'c{depth}')]
            v=envelope(SOURCE,[unit() ],nodes,[link(1,'c1','obj')])
            if depth<=12:validate(v,SOURCE,span_table(SOURCE))
            else:
                with self.assertRaisesRegex(ValueError,'graph_depth'):validate(v,SOURCE,span_table(SOURCE))
        v=envelope(SOURCE,[unit()], [node('c1','ALT',['c2','c3'],[],q=1,r='Competing source readings.'),node('c2'),node('c3')],[link(1,'c1','obj')])
        validate(v,SOURCE,span_table(SOURCE))
    def test_explicit_known_applicability_and_escaped_astral_cap(self):
        v=envelope(SOURCE,[unit(p=1)], [node('c1')],[link(1,'c1','onlyif')])
        validate(v,SOURCE,span_table(SOURCE))
        v['u'][0]['s']='🫧'*280
        raw=json.dumps(v,ensure_ascii=True)
        self.assertEqual(validate_response(raw,'stop',SOURCE,span_table(SOURCE))['compact'],v)
    def test_codepoint_caps_and_fragment_counts(self):
        for size in [279,280,281]:
            v=envelope(SOURCE,[unit(s='🫧'*size)])
            if size<=280:validate(v,SOURCE,span_table(SOURCE))
            else:
                with self.assertRaisesRegex(ValueError,'text_bound'):validate(v,SOURCE,span_table(SOURCE))
        for key,cap in [('g',120),('r',180)]:
            for size in [cap-1,cap,cap+1]:
                v=envelope(SOURCE,[unit()],[node('c1')],[link(1,'c1','obj')]);v['g'][0][key]='x'*size
                if key=='r':v['g'][0]['q']=1
                if size<=cap:validate(v,SOURCE,span_table(SOURCE))
                else:
                    with self.assertRaisesRegex(ValueError,'text_bound'):validate(v,SOURCE,span_table(SOURCE))
        src='a'*49
        for size in [47,48,49]:
            f=frag('s1','a'*size)
            if size<=48:self.assertEqual(resolve_fragment(f,src,span_table(src))['text'],'a'*size)
            else:
                with self.assertRaisesRegex(ValueError,'text_bound'):resolve_fragment(f,src,span_table(src))
        src=' '.join(f'part{i}' for i in range(9))
        for count in [7,8,9]:
            xs=[frag('s1',f'part{i}') for i in range(count)]
            v=envelope(src,[unit(e=['s1'])],[node('c1',x=xs)],[link(1,'c1','obj')])
            if count<=8:validate(v,src,span_table(src))
            else:
                with self.assertRaises(ValueError):validate(v,src,span_table(src))
    def test_full_long_crossrow_and_adjacent_fragments(self):
        src='BEGIN '+LONG+'\r\nbridge\x85after\u2029END'
        t=span_table(src)
        v=envelope(src,[unit(e=['s1'])],[node('c1',x=[frag('s1','BEGIN','END',end='s4')])],[link(1,'c1','obj')])
        ex=expand(v,src,t)
        self.assertEqual(ex['nodes'][0]['evidence'][0]['text'].encode(),src.encode())
        self.assertEqual(contract(ex,src,t),v)
        src='AB';xs=[frag('s1','A'),frag('s1','B')]
        self.assertEqual([e['text'] for e in fragments(xs,1,8,src,span_table(src))],['A','B'])
    def test_operator_link_dimension_fragment_and_list_bounds(self):
        v=fixture()
        for mutate in [lambda v:v['g'][0].update(x=[frag('s1','residents')]*5),lambda v:v['l'][0].update(x=[frag('s1','residents')]*3),lambda v:v['u'][2]['y']['c'].update(x=[frag('s4','16:00')]*5),lambda v:v['u'][0].update(d=list(range(1,18))),lambda v:v['u'][0].update(e=['s1']*7)]:
            bad=copy.deepcopy(v);mutate(bad)
            with self.assertRaises(ValueError):validate(bad,SOURCE,span_table(SOURCE))
    def test_long_opaque_scope_and_scope_is_not_parent_containment(self):
        v=envelope(SOURCE,[unit(p=2,q=1,r='Scope unresolved.')],[node('c1',x=[frag('s2',LONG[:40],LONG[-40:])],q=1,r='Complete but ambiguous condition.')],[link(1,'c1','qual',q=1,r='Applicability logic unresolved.')])
        self.assertEqual(expand(v,SOURCE,span_table(SOURCE))['nodes'][0]['evidence'][0]['text'],LONG)
        v=envelope(SOURCE,[unit()],[node('c1','AND',['c2','c3'],[frag('s1','AND')]),node('c2',x=[frag('s1','residents')]),node('c3',x=[frag('s3','section Delta')])],[link(1,'c1','obj')])
        validate(v,SOURCE,span_table(SOURCE)) # structural only, distributed scope not inferred

if __name__=='__main__':unittest.main(verbosity=2)
