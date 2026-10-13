import copy,importlib.util,json,tempfile,unittest
from unittest.mock import patch
from pathlib import Path
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('cap_probe_runtime',ROOT/'run_pipeline.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
SOURCE=r.j.loads((ROOT.parents[1]/'round8/execution/run/documents/doc-92211b8c7ba0/source.json').read_bytes())

def development_inventory():
    ev=[dict(quote='Department of Natural Resources',occurrence=None,context=None)]
    # Use full source for an unambiguous synthetic structural control; no semantic acceptance claim.
    ev=[dict(quote=SOURCE['source_text'],occurrence=None,context=None)]
    inv=dict(schema_version='round7.source_inventory.v1',document_id=SOURCE['document_id'],source_text_sha256=SOURCE['source_text_sha256'],coverage=dict(status='uncertain',rationale='Hand authored development only',evidence=ev),events=[],routes=[],requirements=[],identities=[],uncertainties=[],alternative_groups=[])
    assembled=r.p.assemble(SOURCE,inv);v=dict(schema_version='round7.record_verdict.v1',document_id=SOURCE['document_id'],payload_sha256=r.p.verification_payload(SOURCE,assembled)['payload_sha256'],completeness=dict(label='uncertain',reason='Synthetic',evidence=ev),source_identity=dict(label='uncertain',reason='Synthetic',evidence=ev),assessments=[],missing_items=[],contradictions=[])
    return inv,v

def reply(value,cost=.0012):return r.j.encode(dict(model=r.a.MODEL,provider='OpenAI',choices=[dict(finish_reason='stop',message=dict(content=json.dumps(value)))],usage=dict(prompt_tokens=100,completion_tokens=100,cost=cost)))
def setup(root):
    freeze=root/'implementation.json';r.put(freeze,r.code_pins());manifest=ROOT.parent/'sources/source-inputs.READY.json';auth=root/'auth.json';r.put(auth,dict(schema_version='round8-contract-probe.live-authorization.v1',implementation_sha256=r.sha(freeze.read_bytes()),manifest_sha256=r.sha(manifest.read_bytes()),source_labels_frozen_before_outputs=True,source_labels_freeze_sha256='a'*64,nominal_budget_usd=2,**r.auth_scope()))
    return manifest,freeze,auth

def run(root,transport,max_new=3):
    manifest,freeze,auth=setup(root)
    return r.run(manifest,manifest.parent,freeze,root/'run',live=True,authorization=auth,source_labels_freeze_sha256='a'*64,max_new=max_new,keys={'openrouter':'dummy-OR','jev':'dummy-jeV'},transport=transport)

def transport_for(inv,v,calls,cost=.0012,fail=None):
    def transport(provider,body,key):
        stage='jev' if provider=='jev' else 'inventory' if body['response_format']['json_schema']['name'].endswith('inventory') else 'stronger';calls.append(stage)
        if stage==fail:raise TimeoutError('sensitive arbitrary text')
        if stage=='jev':return 200,r.j.encode(dict(model=r.a.j.JEV_MODEL,answers={n:dict(type='choice',choice='uncertain',confidence=.8,probabilities={c:.8 if c=='uncertain' else .1 for c in q['criteria']}) for n,q in body['questions'].items()},usage=dict(input_tokens=100,output_tokens=5)))
        return 200,reply(inv if stage=='inventory' else v,cost)
    return transport

class Controls(unittest.TestCase):
    def test_exact_reviewed_prompt_delta_and_unchanged_schema(self):
        old=r.j.loads((ROOT.parents[1]/'round8/execution/run/operations/inventory-82b41c219e64bc9c63a0ed61/request.json').read_bytes());item=r.requests(SOURCE)['inventory'];new=item['body']
        expected=copy.deepcopy(old);expected['max_tokens']=12288;expected['messages'][0]['content']+=r.PROMPT.read_text()
        self.assertEqual(new,expected);self.assertEqual(r.a.LIMITS['inventory_completion'],6144)
        self.assertAlmostEqual(item['admission']['reservation_usd'],item['admission']['estimate']*.000002+12288*.000010)
    def test_full3_calls_and_completed_resume_with_prior_debit(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);inv,v=development_inventory();calls=[];transport=transport_for(inv,v,calls)
            result=run(root,transport);self.assertEqual(result['state'],'completed');self.assertEqual(calls,['inventory','jev','stronger']);self.assertAlmostEqual(result['totals']['prior_budget_debit_usd'],.261774);self.assertAlmostEqual(result['totals']['budget_charge_usd'],.261774+result['totals']['new_budget_charge_usd'])
            run(root,transport);self.assertEqual(len(calls),3)
    def test_exact_source_and_hard_limits(self):
        rows=r.load_sources(ROOT.parent/'sources/source-inputs.READY.json',ROOT.parent/'sources');self.assertEqual(rows[0]['source'],SOURCE);self.assertEqual(r.LIMITS['inventory_calls'],1)
        for stage in ('inventory','jev','stronger'):
            with tempfile.TemporaryDirectory() as temp:
                calls=[];ledger=r.Ledger(temp,{'development':'stage-cap'},max_new=3,budget=2,keys={'openrouter':'dummy-OR','jev':'dummy-jeV'},transport=lambda *args:(calls.append(args) or (200,b'{}')))
                ledger.operation('first',stage,{},lambda raw:dict(observed_cost_usd=0),identity={},reserve=.001)
                with self.assertRaises(r.Pause):ledger.operation('second',stage,{},lambda raw:{},identity={},reserve=.001)
                self.assertEqual(len(calls),1)
        with tempfile.TemporaryDirectory() as temp:
            calls=[];ledger=r.Ledger(temp,{'development':'debit'},max_new=3,budget=2,keys={'openrouter':'dummy-OR'},transport=lambda *args:calls.append(args))
            with self.assertRaises(r.Pause):ledger.operation('too-big','inventory',{},lambda raw:{},identity={},reserve=1.9)
            self.assertEqual(calls,[])
    def test_uncertain_and_postresponse_overrun_latch(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);inv,v=development_inventory();calls=[];transport=transport_for(inv,v,calls,fail='inventory');result=run(root,transport)
            self.assertEqual(result['state'],'stopped_provider_operation');self.assertEqual(calls,['inventory'])
            with self.assertRaises(r.Stop):run(root,transport)
            self.assertEqual(calls,['inventory'])
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);inv,v=development_inventory();calls=[];result=run(root,transport_for(inv,v,calls,cost=1.95))
            self.assertEqual(result['state'],'stopped_budget');self.assertEqual(calls,['inventory']);self.assertGreater(result['totals']['budget_charge_usd'],2)
            doc=r.j.loads(next((root/'run').glob('observed-*.json')).read_bytes())['documents'][0];self.assertIsNotNone(doc['inventory_sha256']);self.assertEqual(doc['runtime_gate'],'postresponse_budget_stop')
    def test_authorization_scope_rejected_before_dispatch(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);manifest,freeze,auth=setup(root);value=r.j.loads(auth.read_bytes());value['inventory_completion']=6144;auth.write_bytes(r.j.encode(value));calls=[]
            with self.assertRaises(r.Stop):r.run(manifest,manifest.parent,freeze,root/'run',live=True,authorization=auth,source_labels_freeze_sha256='a'*64,max_new=3,keys={'openrouter':'dummy','jev':'dummy'},transport=lambda *args:calls.append(args))
            self.assertEqual(calls,[]);self.assertFalse((root/'run/operations').exists())
    def test_alternate_source_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);value=r.j.loads((ROOT.parent/'sources/source-inputs.READY.json').read_bytes());value['documents'][0]['document_id']='doc-aaaaaaaaaaaa';path=root/'manifest.json';path.write_bytes(r.j.encode(value))
            with self.assertRaises(r.Stop):r.load_sources(path,root)
    def test_prior_debit_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);value=r.j.loads((ROOT/'prior-debit.json').read_bytes());value['prior_budget_debit_usd']=0;(root/'prior-debit.json').write_bytes(r.j.encode(value))
            with patch.object(r,'ROOT',root):
                with self.assertRaises(r.Stop):r.verify_prior_debit()
    def test_paid_original_rejects_without_repair_or_verifiers(self):
        paid=r.j.loads((ROOT.parents[1]/'round8-cap-probe/execution/run/operations/inventory-8f69eccb0e19f2d6e43cc72d/result.json').read_bytes())['structured'];before=r.j.encode(paid)
        with tempfile.TemporaryDirectory() as temp:
            calls=[];_,v=development_inventory();result=run(Path(temp),transport_for(paid,v,calls));self.assertEqual(calls,['inventory']);self.assertEqual(result['state'],'completed');self.assertEqual(r.j.encode(paid),before)
            observed=r.j.loads((Path(temp)/'run/completed.json').read_bytes())['documents'][0];self.assertEqual(observed['runtime_gate'],'assembly_review');self.assertIsNone(observed['record_sha256']);self.assertTrue(all(not a['called'] for a in observed['arms'].values()))
    def test_new_bodies_equal_reviewed_offline_candidate_and_guard_delta(self):
        c=r.load('frozen_offline_contract',ROOT.parents[1]/'round8-offline-contract/candidate.py');self.assertEqual(r.requests(SOURCE)['inventory']['body'],c.inventory_body(SOURCE))
        paid=r.j.loads((ROOT.parents[1]/'round8-cap-probe/execution/run/operations/inventory-8f69eccb0e19f2d6e43cc72d/result.json').read_bytes())['structured'];diagnostic=copy.deepcopy(paid);next(t for e in diagnostic['events'] for t in e['timing'] if t['id']=='t-access-request')['dependency_relation']='uncertain';assembled,bodies=c.paired_bodies(SOURCE,diagnostic);plans=r.requests(SOURCE,assembled)
        for stage in ('jev','stronger'):
            self.assertEqual(plans[stage]['body'],bodies[stage]);receipt=c.admission(bodies[stage],stage,40000)
            for field in ('estimate','cap','admitted','reservation_usd','body_sha256','state_longest_estimate'):self.assertEqual(plans[stage]['admission'][field],receipt[field])
        self.assertEqual(plans['stronger']['admission']['estimate'],38347);self.assertTrue(plans['stronger']['admission']['admitted']);self.assertFalse(c.admission(bodies['stronger'],'stronger',35000)['admitted']);self.assertEqual(r.a.LIMITS['OR_input_estimate'],35000)
        for delta in (-1,0,1):
            # Use actual final bodies and a copied plan generator to isolate exact admission boundary; no frozen module mutation.
            body=copy.deepcopy(bodies['stronger']);body['messages'][0]['content']+='x'*(40000+delta-r.a.estimate_input(body));base={'body':body,'admission':r.a.admission(body,'stronger')}
            inv=r.normalized.requests(SOURCE)['inventory']
            with patch.object(r.normalized,'requests',return_value={'inventory':inv,'stronger':base}):receipt=r.requests(SOURCE)['stronger']['admission']
            self.assertEqual(receipt['estimate'],40000+delta);self.assertEqual(receipt['admitted'],delta<=0)
    def test_both_prior_debits_and_metadata_tamper(self):
        value=r.verify_prior_debit();self.assertAlmostEqual(value['operations'][0]['conservative_debit_usd'],.100166);self.assertAlmostEqual(value['operations'][1]['conservative_debit_usd'],.161608);self.assertAlmostEqual(r.MAX_RESERVATION,.316528);self.assertAlmostEqual(r.MAX_RESERVATION+r.PRIOR_DEBIT,.578302)
        for mutate in ('refund','omit_cap_result','debit','freeze_hash'):
            with tempfile.TemporaryDirectory() as temp:
                root=Path(temp);bad=copy.deepcopy(value)
                if mutate=='refund':bad['operations'][1]['conservative_debit_usd']=.0900085
                elif mutate=='omit_cap_result':bad['operations'][1]['files'].pop(next(x for x in bad['operations'][1]['files'] if x.endswith('result.json')))
                elif mutate=='debit':bad['prior_budget_debit_usd']=.1901745
                else:bad['operations'][1]['files'][next(x for x in bad['operations'][1]['files'] if x.endswith('freeze-E.json'))]='0'*64
                (root/'prior-debit.json').write_bytes(r.j.encode(bad))
                with patch.object(r,'ROOT',root):
                    with self.assertRaises(r.Stop):r.verify_prior_debit()
    def test_asymmetric_paired_denial_in_durable_runner(self):
        original=r.normalized.requests
        for denied in ('jev','stronger'):
            def altered(source,assembled=None):
                plans=original(source,assembled)
                if assembled is not None:
                    body=plans[denied]['body']
                    if denied=='stronger':body['messages'][0]['content']+='x'*(40001-r.a.estimate_input(body))
                    else:
                        k=max(body['questions'],key=lambda k:len(r.j.encode(body['questions'][k])));measure=r.a.admission(body,'jev')['state_longest_estimate'];body['questions'][k]['instructions']+='x'*(32001-measure)
                    plans[denied]['admission']=r.a.admission(body,denied)
                return plans
            with tempfile.TemporaryDirectory() as temp,patch.object(r.normalized,'requests',side_effect=altered):
                root=Path(temp);inv,v=development_inventory();calls=[];run(root,transport_for(inv,v,calls));self.assertEqual(calls,['inventory']);doc=r.j.loads((root/'run/completed.json').read_bytes())['documents'][0];self.assertEqual(doc['runtime_gate'],'request_size_review');self.assertTrue(all(not arm['called'] for arm in doc['arms'].values()))
                folder=root/'run/documents'/SOURCE['document_id'];bad=r.j.loads((folder/(denied+'-admission.json')).read_bytes());other=r.j.loads((folder/(('stronger' if denied=='jev' else 'jev')+'-admission.json')).read_bytes());self.assertFalse(bad['admitted']);self.assertTrue(other['admitted'])
    def test_both_verifier_bodies_admit_before_either_call(self):
        inv,v=development_inventory()
        for i in range(9):inv['events'].append(dict(id='x'+str(i),phase='other',description='x'*4000,timing=[],evidence=inv['coverage']['evidence']))
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);calls=[];result=run(root,transport_for(inv,v,calls));self.assertEqual(calls,['inventory']);self.assertEqual(result['state'],'completed')
            doc=r.j.loads((root/'run/completed.json').read_bytes())['documents'][0];self.assertEqual(doc['runtime_gate'],'request_size_review');self.assertIsNotNone(doc['record_sha256']);self.assertTrue(all(not arm['called'] for arm in doc['arms'].values()))
if __name__=='__main__':unittest.main(verbosity=2)
