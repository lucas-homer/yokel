import copy,importlib.util,unittest
from pathlib import Path
R=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('r7_runtime',R/'run_pipeline.py'); r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
p=r.p

def fixture():
    s=p.make_source('Notice ABC. Comments close Monday July 13, 2026.','control')
    spec=importlib.util.spec_from_file_location('r7_fixtures',R.parent/'pipeline/development_fixtures.py')
    # Fixture module takes pipeline through a scoped binding, never an accidental R6 cache.
    import sys
    prior=sys.modules.get('pipeline');sys.modules['pipeline']=p
    try:f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
    finally:
        if prior is None:sys.modules.pop('pipeline',None)
        else:sys.modules['pipeline']=prior
    inv=f.empty_inventory(s);inv['coverage']['status']='claimed_complete'
    inv['events']=[f.event('comment','written_comment',s['source_text'],[f.timing('close','Monday July 13, 2026','2026-07-13')])]
    out=p.assemble(s,inv)
    return s,inv,f.verdict(s,out)

class Controls(unittest.TestCase):
    def test_actual_serialized_admission_and_zero_dispatch_gate(self):
        s,inv,v=fixture();requests=r.requests(s,p.assemble(s,inv));self.assertTrue(all(x['admission']['admitted'] for x in requests.values()))
        self.assertEqual(requests['jev']['body']['state'],r.a.loads(requests['stronger']['body']['messages'][1]['content'])['payload'])
        calls=[]
        result=r.simulate(s,inv,lambda stage,body:(calls.append(stage) or (inv if stage=='inventory' else v if stage=='stronger' else {k:'pass' for k in r.CRITERIA})))
        self.assertEqual(calls,['inventory','jev','stronger']);self.assertTrue(all(x['status']=='accepted_complete' for x in result['observed']['arms'].values()))
        big=p.make_source('漢'*20000,'large');calls=[]
        result=r.simulate(big,None,lambda *args:calls.append(args))
        self.assertEqual(result['observed']['runtime_gate'],'request_size_review');self.assertEqual(calls,[])
        self.assertTrue(all(not x['called'] for x in result['observed']['arms'].values()))

    def test_request_caps_independent_boundaries_and_reservation(self):
        s,inv,v=fixture();bodies=r.requests(s,p.assemble(s,inv))
        for stage in ('inventory','stronger'):
            for delta in (-1,0,1):
                body=copy.deepcopy(bodies[stage]['body']);target=r.a.LIMITS['OR_input_estimate']+delta
                body['messages'][0]['content']+='x'*(target-r.a.estimate_input(body))
                receipt=r.a.admission(body,stage)
                self.assertEqual(receipt['estimate'],target);self.assertEqual(receipt['admitted'],delta<=0)
            bad=copy.deepcopy(bodies[stage]['body']);bad['max_tokens']+=1
            self.assertFalse(r.a.admission(bad,stage)['admitted'])
        # Each probe remains short while the full five-question request independently reaches total cap.
        total={'model':r.a.j.JEV_MODEL,'state':{},'questions':{str(i):{'type':'choice','instructions':'x'*10000,'criteria':{'pass':'p','fail':'f'}} for i in range(5)}}
        for delta in (-1,0,1):
            body=copy.deepcopy(total);target=r.a.LIMITS['Jev_input_estimate']+delta
            body['questions']['0']['instructions']+='x'*(target-r.a.estimate_input(body))
            receipt=r.a.admission(body,'jev');self.assertEqual(receipt['estimate'],target);self.assertLess(receipt['state_longest_estimate'],32000);self.assertEqual(receipt['admitted'],delta<=0)
        for delta in (-1,0,1):
            body={'model':r.a.j.JEV_MODEL,'state':{},'questions':{'q':{'type':'choice','instructions':'','criteria':{'pass':'p','fail':'f'}}}}
            current=len(r.a.encode(body['state']))+len(r.a.encode(body['questions']['q']))+1024
            body['questions']['q']['instructions']='x'*(32000+delta-current)
            receipt=r.a.admission(body,'jev');self.assertEqual(receipt['state_longest_estimate'],32000+delta);self.assertEqual(receipt['admitted'],delta<=0)
        self.assertEqual(r.a.LIMITS['budget_usd'],2);self.assertEqual(r.a.LIMITS['inventory_completion'],6144);self.assertLess(r.a.MAX_RESERVATION,2)

    def test_verifier_gate_failures_and_uncertainty_guards(self):
        s,inv,v=fixture()
        for dimension in r.CRITERIA:
            labels={k:'pass' for k in r.CRITERIA};labels[dimension]='fail'
            result=r.simulate(s,inv,lambda stage,body:inv if stage=='inventory' else v if stage=='stronger' else labels)
            self.assertEqual(result['observed']['arms']['jev']['status'],'review')
            self.assertTrue(result['observed']['arms']['jev']['source_coverage_complete'])
        uncertain=copy.deepcopy(inv);uncertain['coverage']['status']='uncertain'
        # Stronger verdict must match the changed canonical payload.
        out=p.assemble(s,uncertain);v['payload_sha256']=p.verification_payload(s,out)['payload_sha256']
        result=r.simulate(s,uncertain,lambda stage,body:uncertain if stage=='inventory' else v if stage=='stronger' else {k:'pass' for k in r.CRITERIA})
        self.assertTrue(all(a['status']=='review' for a in result['observed']['arms'].values()))
        for fail_stage in ('inventory','jev','stronger'):
            def transport(stage,body):
                if stage==fail_stage:raise RuntimeError('synthetic exception text must not be retained')
                return inv if stage=='inventory' else v if stage=='stronger' else {k:'pass' for k in r.CRITERIA}
            result=r.simulate(s,inv,transport)
            self.assertNotIn('synthetic exception text',str(result));self.assertFalse(result['observed']['provider_service_error'])
            if fail_stage=='inventory':self.assertTrue(all(not a['called'] for a in result['observed']['arms'].values()))
            else:self.assertEqual(result['observed']['arms'][fail_stage]['status'],'failed')
            if fail_stage=='jev':self.assertFalse(result['observed']['arms']['stronger']['called'])
        large=p.make_source('Notice. '+'x'*8000,'verifier-large')
        import sys
        spec=importlib.util.spec_from_file_location('r7_fixture_large',R.parent/'pipeline/development_fixtures.py');prior=sys.modules.get('pipeline');sys.modules['pipeline']=p
        try:f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
        finally:
            if prior is None:sys.modules.pop('pipeline',None)
            else:sys.modules['pipeline']=prior
        big=f.empty_inventory(large);big['events']=[f.event('event'+str(i),'other','Notice.') for i in range(8)]
        for event in big['events']:event['description']='x'*4000
        calls=[];result=r.simulate(large,big,lambda stage,body:(calls.append(stage) or big))
        self.assertEqual(result['observed']['runtime_gate'],'request_size_review');self.assertEqual(calls,['inventory']);self.assertIsNotNone(result['observed']['record_sha256']);self.assertIsNotNone(result['observed']['payload_sha256'])

    def test_page_cap_rejects_before_dispatch(self):
        s,inv,v=fixture();s['pdf_pages']=41;calls=[]
        result=r.simulate(s,inv,lambda *args:calls.append(args))
        self.assertEqual(calls,[]);self.assertEqual(result['observed']['runtime_gate'],'source_review')

if __name__=='__main__':unittest.main(verbosity=2)
