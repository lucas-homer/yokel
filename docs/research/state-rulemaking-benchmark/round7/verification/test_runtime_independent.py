"""Independent authored runtime/admission/evaluator controls; synthetic transport only."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from test_pipeline_independent import fixture,grouped,positive_verdict,ev

R7=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
r=load('independent_runtime',R7/'runtime/run_pipeline.py')
e=load('independent_evaluator',R7/'protocol/evaluate.py')
RECEIPTS=[]

class Transport:
    def __init__(self,inventory,verdict=None,dimensions=None,fail=None):
        self.inventory=inventory;self.verdict=verdict;self.dimensions=dimensions or {k:'pass' for k in ('support','association','requirements','source_identity','completeness')};self.fail=fail;self.calls=[]
    def __call__(self,stage,body):
        self.calls.append(stage)
        if stage==self.fail:raise RuntimeError('explicit synthetic failure')
        if stage=='inventory':return copy.deepcopy(self.inventory)
        if stage=='jev':return copy.deepcopy(self.dimensions)
        if stage=='stronger' and self.verdict is not None:return copy.deepcopy(self.verdict)
        raise AssertionError('unexpected synthetic dispatch '+stage)


def evaluate(observed,unit_status='matched'):
    # Source-first independently authored unit: the actual policy has disclosure
    # class and informational modality. No production audit helper computes it.
    doc=observed['document_id'];policy='Comments are publicly posted except private identifiers.'
    schedule={'schema_version':'round7.schedule.v1','documents':[{'document_id':doc,'pdf_sha256':'a'*64,'pdf_pages':1,'state':'OH','stratum':'control'}]}
    truth={'schema_version':'round7.truth.v1','documents':[{'document_id':doc,'pdf_sha256':'a'*64,'scope_status':'complete','all_pages_viewed':True,'universe_complete':True,'reviewer':'Independent authored development source mapping','exclusions':[],'domains':{k:'present' if k=='disclosure' else 'absent' for k in e.CATEGORIES},'units':[{'id':'policy','category':'disclosure','subtype':'public_posting','description':'Public comments posted, private identifiers excepted; disclosure, informational','raw_value':policy,'modality':'descriptive','targets':['$notice'],'evidence':[{'page':1,'region':'authored source text','quote':policy}]}],'acceptance_blockers':[]}]}
    audit={'schema_version':'round7.matching-audit.v1','reviewer':'Independent authored development mapping','documents':[]}
    if observed['record_sha256']:
        claims=[] if unit_status=='omitted' else [{'id':'posting','categories':['disclosure'],'status':'correct' if unit_status=='matched' else 'incorrect','evidence_status':'matched','literal_kind':'none','literal_status':'not_applicable','basis':'Independent policy class/modality and exception mapping'}]
        mapping={'sha256':observed['record_sha256'],'review_complete':True,'claims':claims,'source_matches':[{'source_unit_id':'policy','status':unit_status,'claim_ids':[c['id'] for c in claims],'basis':'Independent authored policy comparison'}]}
        audit['documents']=[{'document_id':doc,'inventory':None,'record':mapping}]
    obs={'schema_version':'round7.observed.v1','documents':[observed],'costs':{}}
    return e.evaluate(schedule,truth,audit,obs)


class IndependentRuntime(unittest.TestCase):
    def record(self):
        s,i=grouped();a=r.p.assemble(s,i)
        self.assertTrue(a['validation']['valid'])
        return s,i,a,positive_verdict(s,a)

    def test_final_request_pair_identity_and_full_coverage_is_schedule_not_favorability(self):
        s,i,a,v=self.record();plans=r.requests(s,a)
        self.assertEqual(plans['jev']['body']['state'],r.a.loads(plans['stronger']['body']['messages'][1]['content'])['payload'])
        self.assertEqual(plans['jev']['body']['state']['source_text'],s['source_text'])
        for stage,plan in plans.items():
            receipt=plan['admission'];RECEIPTS.append(receipt)
            self.assertEqual(receipt['body_utf8_bytes'],len(r.a.encode(plan['body'])))
            self.assertEqual(receipt['body_sha256'],r.a.sha(r.a.encode(plan['body'])))
            self.assertEqual(receipt['source_sha256'],s['source_text_sha256'])
        for dim in ('support','association','requirements','source_identity','completeness'):
            with self.subTest(dimension=dim):
                dims={k:'pass' for k in r.CRITERIA};dims[dim]='fail'
                t=Transport(i,v,dims);out=r.simulate(s,i,t)
                self.assertEqual(t.calls,['inventory','jev','stronger'])
                self.assertEqual(out['observed']['arms']['jev']['status'],'review')
                self.assertTrue(out['observed']['arms']['jev']['source_coverage_complete'])
                e.validate_observed({'schema_version':'round7.observed.v1','documents':[out['observed']],'costs':{}})
        v['assessments'][0]['support']='contradicted'
        out=r.simulate(s,i,Transport(i,v))
        self.assertEqual(out['observed']['arms']['stronger']['status'],'review')
        self.assertTrue(out['observed']['arms']['stronger']['source_coverage_complete'])

    def test_source_inventory_and_assembly_gates_do_not_invent_arm_calls(self):
        for stage in ('source','inventory_size','assembly'):
            with self.subTest(stage=stage):
                s,i,a,v=self.record()
                if stage=='source':s['source_text_sha256']='0'*64
                elif stage=='inventory_size':s,i=fixture('漢'*20000)
                else:i['routes'][0]['components'][0]['literal']='invented'
                t=Transport(i,v);out=r.simulate(s,i,t);RECEIPTS.extend(out['admission'].values())
                self.assertEqual(t.calls,[] if stage!='assembly' else ['inventory'])
                self.assertEqual(out['synthetic_dispatches'],t.calls)
                self.assertEqual(out['observed'],r.observation(out['terminal']))
                self.assertTrue(all(x['status']=='not_started' and not x['called'] for x in out['observed']['arms'].values()))
                report=evaluate(out['observed'])
                self.assertEqual(report['scheduled_notices'],1)
                self.assertEqual(report['arm_invocations']['jev'],{'called':0,'uncalled':1})
                self.assertEqual(report['arms']['jev']['review_or_unserved_fraction']['value'],1)
                self.assertIsNone(report['arms']['jev']['unsafe_acceptance_fraction']['value'])
                self.assertIsNone(report['costs']['jev']['scenario_cost_per_correct_complete_record']['usage_estimate_usd'])

    def test_valid_record_large_verifier_gate_preserves_hashes_and_blocks_both(self):
        s,i=fixture('Help: call 555-0100 or email help@example.test.\n'+('x'*2000))
        quote=s['source_text']
        i['identities']=[{'id':f'office{x}','kind':'other','literal':'x','relation':'reference','event_ids':[],'evidence':ev(quote)} for x in range(20)]
        self.assertTrue(r.p.assemble(s,i)['validation']['valid'])
        t=Transport(i);out=r.simulate(s,i,t);RECEIPTS.extend(out['admission'].values())
        self.assertEqual(t.calls,['inventory']);self.assertEqual(out['synthetic_dispatches'],['inventory'])
        self.assertEqual(out['observed']['runtime_gate'],'request_size_review')
        self.assertTrue(out['observed']['record_sha256']);self.assertTrue(out['observed']['payload_sha256'])
        self.assertTrue(any(not out['admission'][stage]['admitted'] for stage in ('jev','stronger')))
        report=evaluate(out['observed'],'omitted')
        self.assertEqual(report['runtime_gates'],{'request_size_review':1})
        self.assertEqual(report['arm_invocations']['stronger']['called'],0)

    def test_independent_actual_body_cap_boundaries(self):
        self.assertEqual((r.a.LIMITS['OR_input_estimate'],r.a.LIMITS['Jev_input_estimate'],r.a.LIMITS['Jev_state_longest_estimate']),(35000,64000,32000))
        s,i,a,v=self.record()
        for stage in ('inventory','stronger'):
            base=r.requests(s,a)[stage]['body']
            for delta in (-1,0,1):
                body=copy.deepcopy(base);pad=35000+delta-r.a.estimate_input(body)
                self.assertGreaterEqual(pad,0);body['messages'][1]['content']+='x'*pad
                receipt=r.a.admission(body,stage);RECEIPTS.append(receipt)
                self.assertEqual(receipt['estimate'],35000+delta)
                self.assertEqual(receipt['admitted'],delta<=0)
        # Isolate total-request cap: five long probes keep the longest bound below 32000.
        base={'model':r.a.j.JEV_MODEL,'state':{'text':''},'questions':{str(n):{'type':'choice','instructions':'x'*10000,'criteria':{'pass':'yes','fail':'no'}} for n in range(5)}}
        for delta in (-1,0,1):
            b=copy.deepcopy(base);b['state']['text']='y'*(64000+delta-r.a.estimate_input(b));receipt=r.a.admission(b,'jev');RECEIPTS.append(receipt)
            self.assertEqual(receipt['estimate'],64000+delta);self.assertLess(receipt['state_longest_estimate'],32000);self.assertEqual(receipt['admitted'],delta<=0)
        # Isolate state+longest: total body remains far below 64000.
        base={'model':r.a.j.JEV_MODEL,'state':{'text':''},'questions':{'a':{'type':'choice','instructions':'x','criteria':{'pass':'yes','fail':'no'}}}}
        longest=len(r.a.encode(base['state']))+len(r.a.encode(base['questions']['a']))+1024
        for delta in (-1,0,1):
            b=copy.deepcopy(base);b['state']['text']='y'*(32000+delta-longest);receipt=r.a.admission(b,'jev');RECEIPTS.append(receipt)
            self.assertEqual(receipt['state_longest_estimate'],32000+delta);self.assertLess(receipt['estimate'],64000);self.assertEqual(receipt['admitted'],delta<=0)

    def test_actual_synthetic_failed_call_and_later_uncalled_arm(self):
        s,i,a,v=self.record()
        for arm,expected in [('jev',['inventory','jev']),('stronger',['inventory','jev','stronger'])]:
            with self.subTest(arm=arm):
                t=Transport(i,v,fail=arm);out=r.simulate(s,i,t)
                self.assertEqual(t.calls,expected);self.assertEqual(out['synthetic_dispatches'],expected)
                self.assertEqual(out['observed']['arms'][arm]['status'],'failed');self.assertTrue(out['observed']['arms'][arm]['called'])
                self.assertFalse(out['observed']['provider_service_error'])
                if arm=='jev':self.assertEqual(out['observed']['arms']['stronger']['status'],'not_started')
                report=evaluate(out['observed'],'omitted');self.assertEqual(report['arm_invocations']['stronger']['called'],int(arm=='stronger'))

    def test_favorable_verdict_cannot_erase_extraction_uncertainty(self):
        s,i,a,v=self.record();i['alternative_groups'][0]['association']='uncertain';a=r.p.assemble(s,i);v=positive_verdict(s,a)
        out=r.simulate(s,i,Transport(i,v))
        for arm in ('jev','stronger'):self.assertEqual(out['observed']['arms'][arm]['status'],'review')
        self.assertIn('association_unresolved',out['observed']['review_reasons'])
        bad=copy.deepcopy(out['observed']);bad['arms']['jev']['status']='accepted_complete'
        with self.assertRaises(ValueError):evaluate(bad)

    def test_semantic_omission_and_classification_veto_useful_acceptance(self):
        s,i,a,v=self.record()
        # Owner pipeline admits absent policy; independent truth forbids useful complete credit.
        out=r.simulate(s,i,Transport(i,v))
        for status in ('omitted','mismatched'):
            with self.subTest(status=status):
                report=evaluate(out['observed'],status)
                for arm in ('jev','stronger'):
                    self.assertEqual(report['arms'][arm]['accepted_records'],1)
                    self.assertEqual(report['arms'][arm]['correct_complete_accepted'],0)
                    self.assertEqual(report['arms'][arm]['unsafe_accepted'],1)
                    self.assertEqual(report['arms'][arm]['useful_coverage']['value'],0)
        report=evaluate(out['observed'],'matched')
        self.assertEqual(report['arms']['jev']['correct_complete_accepted'],1)
        self.assertFalse(report['cohort_adequacy']);self.assertFalse(report['production_eligible'])

    def test_page_cap_numeric_costs_and_judgment_coherence(self):
        source,inventory,assembled,verdict=self.record()
        source['pdf_pages']=40
        out=r.simulate(source,inventory,Transport(inventory,verdict))
        self.assertEqual(out['observed']['runtime_gate'],'paired_verification_completed')
        source['pdf_pages']=41
        t=Transport(inventory,verdict);denied=r.simulate(source,inventory,t)
        self.assertEqual(t.calls,[]);self.assertEqual(denied['synthetic_dispatches'],[])
        self.assertEqual(denied['observed']['runtime_gate'],'source_review')
        self.assertIn('page cap',' '.join(denied['observed']['gate_reasons']))
        source['pdf_pages']=1
        good=r.simulate(source,inventory,Transport(inventory,verdict))['observed']
        observed={'schema_version':'round7.observed.v1','documents':[good],'costs':{'extraction':{'usage_estimate_usd':0.5,'conservative_charge_usd':1,'provider_reported_usd':None}}}
        e.validate_observed(observed)
        for mode in ('negative_cost','missing_judgment','negative_dimension','coverage_false','wrong_arm','invented_judgment'):
            with self.subTest(mode=mode):
                bad=copy.deepcopy(observed);arm=bad['documents'][0]['arms']['jev']
                if mode=='negative_cost':bad['costs']['extraction']['usage_estimate_usd']=-0.1
                elif mode=='missing_judgment':arm.pop('judgment')
                elif mode=='negative_dimension':arm['judgment']['common_dimensions']['support']='fail'
                elif mode=='coverage_false':arm['source_coverage_complete']=False
                elif mode=='wrong_arm':arm['judgment']['arm']='stronger'
                else:arm['judgment']['extra']='invented'
                with self.assertRaises(ValueError):e.validate_observed(bad)

    def test_impossible_failure_order_and_completed_gate_rejected(self):
        source,inventory,assembled,verdict=self.record()
        out=r.simulate(source,inventory,Transport(inventory,verdict))
        for mode in ('completed_with_failed_arm','stronger_after_jev_failure'):
            with self.subTest(mode=mode):
                bad=copy.deepcopy(out['observed'])
                bad['arms']['jev'].update(status='failed',source_coverage_complete=False,reason='synthetic failed call')
                bad['arms']['jev'].pop('judgment',None)
                if mode=='stronger_after_jev_failure':
                    bad.update(runtime_gate='verification_failed',gate_reasons=['jev: synthetic failure'])
                with self.assertRaises(ValueError):evaluate(bad,'omitted')

    def test_forged_call_gate_hash_states_reject_and_missing_stays_unserved(self):
        s,i,a,v=self.record();out=r.simulate(s,i,Transport(i,v))
        for mode in ('uncalled_accept','hash','pre_gate','false_coverage','no_inventory'):
            with self.subTest(mode=mode):
                bad=copy.deepcopy(out['observed'])
                if mode=='uncalled_accept':bad['arms']['jev']['called']=False
                elif mode=='hash':bad['arms']['stronger']['payload_sha256']='0'*64
                elif mode=='pre_gate':bad.update(runtime_gate='assembly_review',gate_reasons=['fabricated'])
                elif mode=='false_coverage':bad['arms']['jev']['source_coverage_complete']=False
                else:bad['inventory_sha256']=None
                with self.assertRaises(ValueError):evaluate(bad)
        doc=out['observed']['document_id']
        schedule={'schema_version':'round7.schedule.v1','documents':[{'document_id':doc,'pdf_sha256':'a'*64,'pdf_pages':1,'state':'OH','stratum':'control'}]}
        report=e.evaluate(schedule,{'schema_version':'round7.truth.v1','documents':[]},{'schema_version':'round7.matching-audit.v1','reviewer':'Independent authored mapping','documents':[]},{'schema_version':'round7.observed.v1','documents':[],'costs':{}})
        self.assertEqual(report['missing_observations'],1);self.assertEqual(report['runtime_gates'],{})
        self.assertEqual(report['arm_invocations']['jev'],{'called':0,'uncalled':1})
        self.assertEqual(report['arms']['jev']['status_counts'],{'not_started':1})

if __name__=='__main__':
    def guard(event,args):
        if event.startswith('socket.') or event in ('subprocess.Popen','os.system'):raise RuntimeError('Offline network/process dispatch forbidden')
        if event=='open' and isinstance(args[0],(str,bytes)) and any(x in str(args[0]).lower() for x in ('.env','.keychain','credentials','/secrets/')):raise RuntimeError('Credential access forbidden')
    sys.addaudithook(guard)
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(IndependentRuntime)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    (R7/'verification/runtime-results.json').write_text(json.dumps({'tests':result.testsRun,'passed':result.wasSuccessful(),'failures':[(str(t),failure) for t,failure in result.failures+result.errors],'admission_receipts':RECEIPTS,'provider_calls':0,'credential_network_process_guard':'Python audit hook active during all controls','development_only':True},sort_keys=True,indent=2)+'\n')
    sys.exit(not result.wasSuccessful())
