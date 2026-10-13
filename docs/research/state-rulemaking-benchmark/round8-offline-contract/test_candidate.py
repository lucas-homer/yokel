import copy,json,unittest
import candidate as c
import fixtures as f
class Controls(unittest.TestCase):
    def test_actual_failure_strict_no_repair(self):
        s,i=c.observed();before=c.a.encode(i);out=c.p.assemble(s,i)
        self.assertEqual(out['validation']['errors'],['t-access-request: dependency ids require a relation','t-access-request: relative/conditional timing requires dependency association or explicit uncertainty'])
        with self.assertRaises(ValueError):c.paired_bodies(s,i)
        self.assertEqual(before,c.a.encode(i));self.assertIsNone(out['record'])
    def test_relationship_cases_keep_exact_evidence(self):
        s,i=f.accessibility();item=next(t for e in i['events'] for t in e['timing'] if t['id']=='asap')
        for relation,anchors,conditions,valid in [('none',[],['aid'],False),('none',[],[],False),('before',[],[],False),('after',[],[],False),('upon',[],[],False),('during',[],[],False),('unless',[],[],False),('other',[],[],False),('other',[],['aid'],True),('uncertain',[],[],True)]:
            with self.subTest(relation=relation,conditions=conditions):
                value=copy.deepcopy(i);timing=next(t for e in value['events'] for t in e['timing'] if t['id']=='asap');timing.update(dependency_relation=relation,anchor_event_ids=anchors,condition_requirement_ids=conditions);before=c.a.encode(value);out=c.p.assemble(s,value)
                self.assertEqual(out['validation']['valid'],valid);self.assertEqual(c.a.encode(value),before);self.assertEqual(timing['raw'],'as soon as possible');self.assertIsNone(timing['value']);self.assertEqual(timing['evidence'],item['evidence'])
                if valid:
                    raw=next(t for e in out['record']['events'] for t in e['timing'] if t['id']=='asap');self.assertEqual(raw['raw'],timing['raw']);self.assertIsNone(raw['value'])
                    if relation=='uncertain':self.assertIn('timing_unresolved',out['validation']['review_reasons'])
        bad=copy.deepcopy(i);bad['events'][1]['timing'][1]['evidence'][0]['quote']='invented deadline';self.assertFalse(c.p.assemble(s,bad)['validation']['valid'])
    def test_no_inferred_asap_calendar_date_or_semantic_certification(self):
        s,i=f.accessibility();bad=copy.deepcopy(i);item=bad['events'][1]['timing'][1];item.update(kind='absolute_date',value='2026-07-12');out=c.p.assemble(s,bad);self.assertFalse(out['validation']['valid'])
        # A supported-span before binding can still be semantically unsupported for ASAP: structure does not certify that interpretation.
        candidate=copy.deepcopy(i);item=candidate['events'][1]['timing'][1];item.update(dependency_relation='before',anchor_event_ids=['hearing']);out=c.p.assemble(s,candidate);self.assertTrue(out['validation']['valid']);self.assertEqual(out['validation']['source_correctness'],'unverified')
    def test_conditional_cross_field_and_dangling_ids(self):
        s,i=f.accessibility()
        for kind in ('relative','conditional'):
            for relation,conditions,valid in [('none',[],False),('none',['aid'],False),('other',['aid'],True),('uncertain',[],True),('other',['missing'],False)]:
                with self.subTest(kind=kind,relation=relation,conditions=conditions):
                    value=copy.deepcopy(i);item=value['events'][1]['timing'][1];item.update(kind=kind,dependency_relation=relation,condition_requirement_ids=conditions);before=c.a.encode(value);out=c.p.assemble(s,value);self.assertEqual(out['validation']['valid'],valid);self.assertEqual(c.a.encode(value),before)
    def test_exact_prompt_only_delta_and_source_only_boundary(self):
        s,_=c.observed();actual=c.a.loads((c.BASE/'round8-cap-probe/execution/run/operations/inventory-8f69eccb0e19f2d6e43cc72d/request.json').read_bytes());candidate=c.inventory_body(s);expected=copy.deepcopy(actual);expected['messages'][0]['content']+=(c.ROOT/'prompt-delta.txt').read_text();self.assertEqual(candidate,expected)
        user=c.a.loads(candidate['messages'][1]['content']);self.assertEqual(user,{'source':s});self.assertEqual(candidate['response_format'],actual['response_format']);self.assertEqual(c.a.LIMITS['OR_input_estimate'],35000);self.assertEqual(c.a.LIMITS['stronger_completion'],4096)
        self.assertNotIn('doc-92211b8c7ba0',(c.ROOT/'prompt-delta.txt').read_text());self.assertNotIn('t-access-request',(c.ROOT/'prompt-delta.txt').read_text())
        self.assertTrue(c.admission(candidate,'inventory')['admitted'])
    def test_serialized_examples_equal_evidence_and_unchanged_bodies(self):
        for name,s,i,label in f.examples():
            with self.subTest(name=name):
                before=c.a.encode(i);out,bodies=c.paired_bodies(s,i);self.assertEqual(before,c.a.encode(i));jev=bodies['jev']['state'];strong=c.a.loads(bodies['stronger']['messages'][1]['content'])['payload'];self.assertEqual(jev,strong);self.assertEqual(jev['source_text'],s['source_text']);self.assertEqual(jev['record'],out['record'])
                digest=c.a.sha(c.a.encode(bodies));base=c.paired_gate(bodies,35000);proposed=c.paired_gate(bodies,40000);self.assertEqual(digest,c.a.sha(c.a.encode(bodies)));self.assertEqual(base['admission']['jev'],proposed['admission']['jev']);self.assertEqual(bodies['stronger']['max_tokens'],4096)
                if name.startswith('paid-diagnostic'):
                    self.assertFalse(base['admission']['stronger']['admitted']);self.assertTrue(all(v['admitted'] for v in proposed['admission'].values()));self.assertFalse(out['action_ready']);self.assertEqual(out['validation']['source_correctness'],'unverified')
                elif name=='existing-authored-size-stress':self.assertFalse(proposed['admission']['stronger']['admitted']);self.assertFalse(proposed['admission']['jev']['admitted'])
                else:self.assertTrue(all(v['admitted'] for v in base['admission'].values()))
    def test_stronger_boundaries_and_invalid_completion(self):
        s,i=f.accessibility();_,bodies=c.paired_bodies(s,i)
        for cap in (35000,40000):
            for delta in (-1,0,1):
                body=copy.deepcopy(bodies['stronger']);body['messages'][0]['content']+='x'*(cap+delta-c.a.estimate_input(body));receipt=c.admission(body,'stronger',cap);self.assertEqual(receipt['estimate'],cap+delta);self.assertEqual(receipt['admitted'],delta<=0)
                if receipt['admitted']:self.assertAlmostEqual(receipt['reservation_usd'],(cap+delta)*.000002+4096*.000010)
            body=copy.deepcopy(bodies['stronger']);body['max_tokens']=4097;self.assertFalse(c.admission(body,'stronger',cap)['admitted'])
    def test_jev_total_and_state_boundaries(self):
        s,i=f.accessibility();_,bodies=c.paired_bodies(s,i)
        for delta in (-1,0,1):
            body=copy.deepcopy(bodies['jev']);needed=64000+delta-c.a.estimate_input(body);keys=list(body['questions']);q,rem=divmod(needed,len(keys))
            for n,k in enumerate(keys):body['questions'][k]['instructions']+='x'*(q+(n<rem))
            receipt=c.admission(body,'jev',40000);self.assertEqual(receipt['estimate'],64000+delta);self.assertLess(receipt['state_longest_estimate'],32000);self.assertEqual(receipt['admitted'],delta<=0)
            body=copy.deepcopy(bodies['jev']);k=max(body['questions'],key=lambda key:len(c.a.encode(body['questions'][key])));before=c.admission(body,'jev');body['questions'][k]['instructions']+='x'*(32000+delta-before['state_longest_estimate']);receipt=c.admission(body,'jev');self.assertEqual(receipt['state_longest_estimate'],32000+delta);self.assertLess(receipt['estimate'],64000);self.assertEqual(receipt['admitted'],delta<=0)
    def test_both_arm_admission_precedes_any_synthetic_dispatch(self):
        s,i=f.accessibility();_,bodies=c.paired_bodies(s,i)
        for failing in ('jev','stronger'):
            body=copy.deepcopy(bodies)
            if failing=='stronger':body['stronger']['messages'][0]['content']+='x'*(40001-c.a.estimate_input(body['stronger']))
            else:
                k=max(body['jev']['questions'],key=lambda key:len(c.a.encode(body['jev']['questions'][key])));before=c.admission(body['jev'],'jev');body['jev']['questions'][k]['instructions']+='x'*(32001-before['state_longest_estimate'])
            calls=[];result=c.paired_gate(body,40000,lambda stage,body:calls.append(stage));self.assertEqual(calls,[]);self.assertEqual(result['synthetic_dispatches'],[])
        calls=[];result=c.paired_gate(bodies,40000,lambda stage,body:calls.append(stage));self.assertEqual(calls,['jev','stronger'])
    def test_coverage_uncertainty_is_not_semantic_success(self):
        s,i=f.accessibility();out=c.p.assemble(s,i);self.assertEqual(out['inventory']['coverage']['status'],'uncertain');self.assertIn('inventory_coverage_uncertain',out['validation']['review_reasons']);self.assertEqual(out['validation']['source_completeness'],'unverified')
        # Existing assembler may structurally accept claimed_complete. Prompt instruction is not model evidence or a new semantic validator.
        i['coverage']['status']='claimed_complete';self.assertTrue(c.p.assemble(s,i)['validation']['valid']);self.assertEqual(c.p.assemble(s,i)['validation']['source_completeness'],'unverified')
    def test_represented_source_ambiguity_and_coverage_are_independent(self):
        s,claimed=f.represented_source_ambiguity('claimed_complete');_,unestablished=f.represented_source_ambiguity('uncertain');before=c.a.encode(claimed);out=c.p.assemble(s,claimed);other=c.p.assemble(s,unestablished)
        self.assertTrue(out['validation']['valid']);self.assertTrue(other['validation']['valid']);self.assertEqual(before,c.a.encode(claimed))
        reasons=out['validation']['review_reasons'];self.assertIn('explicit_source_uncertainties',reasons);self.assertIn('association_unresolved',reasons);self.assertNotIn('inventory_coverage_uncertain',reasons)
        self.assertEqual(set(other['validation']['review_reasons']),set(reasons)|{'inventory_coverage_uncertain'})
        self.assertEqual(out['record']['uncertainties'],other['record']['uncertainties']);self.assertEqual(out['record']['requirements'],other['record']['requirements']);self.assertEqual(out['validation']['source_completeness'],'unverified');self.assertEqual(out['validation']['source_correctness'],'unverified')
        for inv in (claimed,unestablished):
            _,bodies=c.paired_bodies(s,inv);self.assertTrue(all(v['admitted'] for v in c.paired_gate(bodies)['admission'].values()))
    def test_budget_keeps_both_prior_debits_and_boundaries(self):
        self.assertAlmostEqual(c.PRIOR_DEBIT,.100166+.161608)
        for guard,new,total in ((35000,.306528,.568302),(40000,.316528,.578302)):
            report=c.budget(guard);self.assertAlmostEqual(report['new_nominal_reservation_usd'],new);self.assertAlmostEqual(report['aggregate_nominal_usd'],total)
        reserve=.25;charges=2-c.PRIOR_DEBIT-reserve;self.assertTrue(c.budget_admitted(charges,reserve));self.assertFalse(c.budget_admitted(charges+.000001,reserve))
        for bad in (-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):c.budget_admitted(bad,reserve)
if __name__=='__main__':unittest.main(verbosity=2)
