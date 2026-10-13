import copy
import sys
import unittest
from compact import *
from fictional_controls import *

class HardeningTests(unittest.TestCase):
    def chain(self, cycle=False):
        nodes=[node(f'c{i}','NOT',[f'c{i+1}'],[]) for i in range(1,399)]
        nodes.append(node('c399','NOT',['c1'],[]) if cycle else node('c399'))
        return envelope(SOURCE,[unit()],nodes,[link(1,'c1','obj')])
    def test_399_chain_controlled_depth_failure_at_1000_and_600(self):
        original=sys.getrecursionlimit()
        try:
            for limit in [1000,600]:
                with self.subTest(recursion_limit=limit):
                    sys.setrecursionlimit(limit)
                    with self.assertRaisesRegex(ValueError,'^graph_depth$'):
                        validate(self.chain(),SOURCE,span_table(SOURCE))
        finally:sys.setrecursionlimit(original)
    def test_399_cycle_controlled_failure_at_600(self):
        original=sys.getrecursionlimit()
        try:
            sys.setrecursionlimit(600)
            with self.assertRaisesRegex(ValueError,'^node_cycle$'):
                validate(self.chain(cycle=True),SOURCE,span_table(SOURCE))
        finally:sys.setrecursionlimit(original)
    def test_absent_deadline_reaches_uncertainty_guard(self):
        v=fixture()
        # Informational modality avoids masking this q0 error with unknown_modality.
        v['u'][3].update(m=0,q=0,r='')
        with self.assertRaisesRegex(ValueError,'^deadline_uncertainty$'):
            validate(v,SOURCE,span_table(SOURCE))
    def test_applicability_links_reached_without_qual_mask(self):
        v=fixture()
        # Preserve c10 reachability as obj; no qual invariant masks p0+onlyif.
        v['l'][1]['w']='obj'
        v['u'][0]['p']=0
        with self.assertRaisesRegex(ValueError,'^applicability_links$'):
            validate(v,SOURCE,span_table(SOURCE))
        v=fixture();v['u'][6]['p']=1
        with self.assertRaisesRegex(ValueError,'^applicability_links$'):
            validate(v,SOURCE,span_table(SOURCE))
    def test_inverse_list_mutations_do_not_alias_expanded_input(self):
        ex=expand(fixture(),SOURCE,span_table(SOURCE))
        original=copy.deepcopy(ex)
        restored=contract(ex,SOURCE,span_table(SOURCE))
        self.assertIsNot(restored['u'][0]['d'],ex['units'][0]['required_unit_ids'])
        self.assertIsNot(restored['u'][0]['b'],ex['units'][0]['relationship_member_ids'])
        self.assertIsNot(restored['g'][0]['a'],ex['nodes'][0]['args'])
        restored['u'][0]['d'].append(2)
        restored['u'][0]['b'].append(2)
        restored['g'][0]['a'].reverse()
        self.assertEqual(ex,original)
        restored_snapshot=copy.deepcopy(restored)
        ex['units'][0]['required_unit_ids'].append(99)
        ex['units'][0]['relationship_member_ids'].append(99)
        ex['nodes'][0]['args'].append('c399')
        self.assertEqual(restored,restored_snapshot)
    def test_deepest_shared_path_is_independent_of_node_order(self):
        base=[node(f'c{i}','NOT',[f'c{i+1}'],[]) for i in range(1,11)]+[node('c11')]
        for depth in [12,13]:
            nodes=base+[node('c12','AND',['c1','c11'],[])]
            if depth==13:nodes.append(node('c13','AND',['c12','c11'],[]))
            for ordered in [nodes,list(reversed(nodes)),[nodes[10]]+nodes[:10]+nodes[11:]]:
                with self.subTest(depth=depth,first_node=ordered[0]['i']):
                    v=envelope(SOURCE,[unit()],ordered,[link(1,f'c{depth}','obj')])
                    if depth==12:
                        self.assertEqual(contract(expand(v,SOURCE,span_table(SOURCE)),SOURCE,span_table(SOURCE)),v)
                    else:
                        with self.assertRaisesRegex(ValueError,'^graph_depth$'):
                            validate(v,SOURCE,span_table(SOURCE))
    def test_shared_diamond_is_not_cycle_and_inverse_exact(self):
        nodes=[node('c1','AND',['c2','c3'],[]),node('c2','AND',['c4','c5'],[]),node('c3','AND',['c4','c6'],[]),node('c4'),node('c5'),node('c6')]
        v=envelope(SOURCE,[unit()],nodes,[link(1,'c1','obj')])
        self.assertEqual(contract(expand(v,SOURCE,span_table(SOURCE)),SOURCE,span_table(SOURCE)),v)

if __name__=='__main__':unittest.main(verbosity=2)
