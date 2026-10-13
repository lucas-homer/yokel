"""Local deterministic hardening checks; no Fable inference or semantic oracle."""
import copy
import sys
import unittest
from run_independent import OLD,NEW as C
SOURCE='Condition.'
TABLE=C.span_table(SOURCE)
X=[['s1','Condition.',1,'s1','Condition.',1]]
def chain(depth,cycle=False):
    nodes=[dict(i='c'+str(i),o='NOT',a=['c'+str(i+1)],x=[],g='',q=0,r='') for i in range(1,depth)]
    nodes.append(dict(i='c'+str(depth),o='NOT',a=['c1'],x=[],g='',q=0,r='') if cycle else OLD.leaf('c'+str(depth),X))
    return OLD.envelope(SOURCE,nodes=nodes,links=[OLD.link(w='obj')])[0]

class TargetedTests(unittest.TestCase):
    def test_399_depth_controlled_at_both_process_limits(self):
        limit=sys.getrecursionlimit()
        try:
            for candidate in [1000,600]:
                sys.setrecursionlimit(candidate)
                v=chain(399);before=copy.deepcopy(v)
                with self.assertRaisesRegex(ValueError,'^graph_depth$'):C.expand(v,SOURCE,TABLE)
                self.assertEqual(v,before)
        finally:sys.setrecursionlimit(limit)

    def test_399_cycle_controlled_at_600(self):
        limit=sys.getrecursionlimit()
        try:
            sys.setrecursionlimit(600)
            with self.assertRaisesRegex(ValueError,'^node_cycle$'):C.validate(chain(399,True),SOURCE,TABLE)
        finally:sys.setrecursionlimit(limit)

    def test_shared_depth_node_order_and_diamond(self):
        for depth in [12,13]:
            v=chain(11)
            v['g'].append(dict(i='c12',o='AND',a=['c1','c11'],x=[],g='',q=0,r=''))
            if depth==13:v['g'].append(dict(i='c13',o='AND',a=['c12','c11'],x=[],g='',q=0,r=''))
            v['l'][0]['n']='c'+str(depth)
            orderings=[v['g'],list(reversed(v['g'])),v['g'][10:]+v['g'][:10]]
            for ordering in orderings:
                w=copy.deepcopy(v);w['g']=copy.deepcopy(ordering)
                if depth==12:self.assertEqual(C.contract(C.expand(w,SOURCE,TABLE),SOURCE,TABLE),w)
                else:
                    with self.assertRaisesRegex(ValueError,'^graph_depth$'):C.validate(w,SOURCE,TABLE)
        nodes=[dict(i='c1',o='AND',a=['c2','c3'],x=[],g='',q=0,r=''),
               dict(i='c2',o='NOT',a=['c4'],x=[],g='',q=0,r=''),
               dict(i='c3',o='NOT',a=['c4'],x=[],g='',q=0,r=''),OLD.leaf('c4',X)]
        for ordering in [nodes,list(reversed(nodes))]:
            v,_=OLD.envelope(SOURCE,nodes=ordering,links=[OLD.link(w='obj')])
            self.assertEqual(C.contract(C.expand(v,SOURCE,TABLE),SOURCE,TABLE),v)

    def test_inverse_detaches_mutable_lists_both_directions(self):
        v=chain(2);v['u'].append(OLD.unit(i=2))
        ex=C.expand(v,SOURCE,TABLE);before=copy.deepcopy(ex);restored=C.contract(ex,SOURCE,TABLE)
        for wire,expanded in [(restored['u'][0]['d'],ex['units'][0]['required_unit_ids']),
                              (restored['u'][0]['b'],ex['units'][0]['relationship_member_ids']),
                              (restored['g'][0]['a'],ex['nodes'][0]['args'])]:
            self.assertIsNot(wire,expanded)
        restored['u'][0]['d'].append(2);restored['u'][0]['b'].append(2);restored['g'][0]['a'].append('c399')
        self.assertEqual(ex,before);snapshot=copy.deepcopy(restored)
        ex['units'][0]['required_unit_ids'].append(99);ex['units'][0]['relationship_member_ids'].append(99);ex['nodes'][0]['args'].append('c400')
        self.assertEqual(restored,snapshot)

    def test_deadline_and_applicability_specific_guards_not_masked(self):
        u=OLD.unit(k=3,m=0,q=0)
        u['y']={key:dict(s='absent',x=[],r='') for key in ['c','z','b']}
        v,_=OLD.envelope(SOURCE,units=[u])
        with self.assertRaisesRegex(ValueError,'^deadline_uncertainty$'):C.validate(v,SOURCE,TABLE)
        v,_=OLD.envelope(SOURCE,nodes=[OLD.leaf('c1',X)],links=[OLD.link(w='if')])
        self.assertEqual(v['u'][0]['p'],0)
        with self.assertRaisesRegex(ValueError,'^applicability_links$'):C.validate(v,SOURCE,TABLE)
        v,_=OLD.envelope(SOURCE,units=[OLD.unit(p=1)])
        with self.assertRaisesRegex(ValueError,'^applicability_links$'):C.validate(v,SOURCE,TABLE)

    def test_new_version_span_binding_rejects_old_envelope(self):
        v,_=OLD.envelope(SOURCE)
        self.assertEqual(v['v'],'r15.1');self.assertEqual(TABLE['v'],'r15.spans.2')
        ex=C.expand(v,SOURCE,TABLE);self.assertEqual(ex['schema_version'],'round15.expanded-inventory.v2')
        v['v']='r15.0'
        with self.assertRaisesRegex(ValueError,'^binding_version$'):C.validate(v,SOURCE,TABLE)
        old_table=copy.deepcopy(TABLE);old_table['v']='r15.spans.1'
        with self.assertRaisesRegex(ValueError,'^exact_host_table$'):C.validate_table(SOURCE,old_table)

if __name__=='__main__':unittest.main(verbosity=2)
