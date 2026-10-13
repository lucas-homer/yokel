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
    freeze=root/'implementation.json';r.put(freeze,r.code_pins());manifest=ROOT.parent/'sources/source-inputs.READY.json';auth=root/'auth.json';r.put(auth,dict(schema_version='round8-cap-probe.live-authorization.v1',implementation_sha256=r.sha(freeze.read_bytes()),manifest_sha256=r.sha(manifest.read_bytes()),source_labels_frozen_before_outputs=True,source_labels_freeze_sha256='a'*64,nominal_budget_usd=2,prior_budget_debit_usd=.100166,prior_debit_sha256=r.sha((ROOT/'prior-debit.json').read_bytes()),max_new_operations=3,calls_per_stage=1,inventory_completion=12288))
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
    def test_final_inventory_delta_is_only_output_cap(self):
        old=r.j.loads((ROOT.parents[1]/'round8/execution/run/operations/inventory-82b41c219e64bc9c63a0ed61/request.json').read_bytes());item=r.requests(SOURCE)['inventory'];new=item['body']
        expected=copy.deepcopy(old);expected['max_tokens']=12288
        self.assertEqual(new,expected);self.assertEqual(r.a.LIMITS['inventory_completion'],6144)
        self.assertAlmostEqual(item['admission']['reservation_usd'],item['admission']['estimate']*.000002+12288*.000010)
    def test_full3_calls_and_completed_resume_with_prior_debit(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);inv,v=development_inventory();calls=[];transport=transport_for(inv,v,calls)
            result=run(root,transport);self.assertEqual(result['state'],'completed');self.assertEqual(calls,['inventory','jev','stronger']);self.assertAlmostEqual(result['totals']['prior_budget_debit_usd'],.100166);self.assertAlmostEqual(result['totals']['budget_charge_usd'],.100166+result['totals']['new_budget_charge_usd'])
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
    def test_both_verifier_bodies_admit_before_either_call(self):
        inv,v=development_inventory()
        for i in range(9):inv['events'].append(dict(id='x'+str(i),phase='other',description='x'*4000,timing=[],evidence=inv['coverage']['evidence']))
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);calls=[];result=run(root,transport_for(inv,v,calls));self.assertEqual(calls,['inventory']);self.assertEqual(result['state'],'completed')
            doc=r.j.loads((root/'run/completed.json').read_bytes())['documents'][0];self.assertEqual(doc['runtime_gate'],'request_size_review');self.assertIsNotNone(doc['record_sha256']);self.assertTrue(all(not arm['called'] for arm in doc['arms'].values()))
if __name__=='__main__':unittest.main(verbosity=2)
