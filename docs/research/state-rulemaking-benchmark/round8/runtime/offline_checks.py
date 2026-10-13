import copy,importlib.util,json,tempfile,unittest
from pypdf import PdfWriter
from pathlib import Path
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('r8_run',ROOT/'run_pipeline.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

def fixture(root,documents=1,pages=1,text=None):
    sources=root/'sources';sources.mkdir();units=[];inventories={};verdicts={}
    for number in range(documents):
        ident='doc-'+format(number+1,'012x');text_value=text or 'Notice ABC. Comments close Monday July 13, 2026.'
        pdf=sources/(ident+'.pdf');writer=PdfWriter()
        for page in range(pages):writer.add_blank_page(width=100,height=100)
        writer.write(pdf);native=sources/(ident+'.txt');native.write_text(text_value)
        unit=dict(document_id=ident,channel='native',text_path=native.name,text_sha256=r.sha(native.read_bytes()),pdf_path=pdf.name,pdf_sha256=r.sha(pdf.read_bytes()),pdf_pages=pages,scope='full_notice',native_page_map_known=False);units.append(unit)
        source=r.p.make_source(text_value,ident,pdf_pages=pages)
        evidence=lambda quote:[dict(quote=quote,occurrence=None,context=None)]
        inv=dict(schema_version='round7.source_inventory.v1',document_id=ident,source_text_sha256=source['source_text_sha256'],coverage=dict(status='claimed_complete',rationale='Synthetic offline development',evidence=evidence(text_value)),events=[],routes=[],requirements=[],identities=[],uncertainties=[],alternative_groups=[])
        if text is None:
            inv['events']=[dict(id='comment',phase='written_comment',description='comment',evidence=evidence('Comments close Monday July 13, 2026.'),timing=[dict(id='close',kind='absolute_date',role='closes',dependency_relation='none',anchor_event_ids=[],condition_requirement_ids=[],raw='Monday July 13, 2026',value='2026-07-13',evidence=evidence('Monday July 13, 2026'))])]
            inv['identities']=[dict(id='notice',kind='notice',literal='ABC',relation='canonical',event_ids=['comment'],evidence=evidence('ABC'))]
        assembled=r.p.assemble(source,inv);common=r.p.verification_payload(source,assembled)
        verdict=dict(schema_version='round7.record_verdict.v1',document_id=ident,payload_sha256=common['payload_sha256'],completeness=dict(label='complete',reason='Synthetic',evidence=evidence(text_value)),source_identity=dict(label='resolved',reason='Synthetic',evidence=evidence(text_value)),assessments=[dict(item_id=i['id'],support='supported',association='matched',requirements='preserved',reason='Synthetic',evidence=evidence(text_value)) for _,i in r.p.all_items(assembled['record'])],missing_items=[],contradictions=[])
        inventories[ident]=inv;verdicts[ident]=verdict
    manifest=sources/'manifest.json';r.put(manifest,dict(schema_version='round8.sources.v1',documents=units));freeze=root/'implementation.json';r.put(freeze,r.code_pins());auth=root/'authorization.json';r.put(auth,dict(schema_version='round8.live-authorization.v1',implementation_sha256=r.sha(freeze.read_bytes()),manifest_sha256=r.sha(manifest.read_bytes()),source_labels_frozen_before_outputs=True,source_labels_freeze_sha256='a'*64,nominal_budget_usd=2.0))
    return sources,manifest,freeze,auth,inventories,verdicts

def reply(value):return r.j.encode(dict(model=r.a.MODEL,provider='OpenAI',choices=[dict(finish_reason='stop',message=dict(content=json.dumps(value)))],usage=dict(prompt_tokens=100,completion_tokens=100,cost=.0012)))
def transport_for(inventories,verdicts,calls,fail=None):
    def transport(provider,body,key):
        stage='jev' if provider=='jev' else 'inventory' if body['response_format']['json_schema']['name'].endswith('inventory') else 'stronger'
        calls.append(stage)
        if stage==fail:raise TimeoutError('sensitive exception text not retained')
        if stage=='jev':return 200,r.j.encode(dict(model=r.a.j.JEV_MODEL,answers={name:dict(type='choice',choice='pass',confidence=.8,probabilities={c:.8 if c=='pass' else .1 for c in q['criteria']}) for name,q in body['questions'].items()},usage=dict(input_tokens=100,output_tokens=5)))
        user=r.a.loads(body['messages'][1]['content']);ident=user['source']['document_id'] if stage=='inventory' else user['payload']['document_id']
        return 200,reply(inventories[ident] if stage=='inventory' else verdicts[ident])
    return transport

def execute(root,data,calls,max_new=24,fail=None):
    sources,manifest,freeze,auth,inv,v=data
    return r.run(manifest,sources,freeze,root/'run',live=True,authorization=auth,source_labels_freeze_sha256='a'*64,max_new=max_new,budget=2,keys={'openrouter':'dummy-OR','jev':'dummy-jeV'},transport=transport_for(inv,v,calls,fail))

class Controls(unittest.TestCase):
    def test_completed_durable_resume_does_not_post_again(self):
        with tempfile.TemporaryDirectory() as temp:
            calls=[]
            transport=lambda *args:(calls.append(args) or (200,b'{}'))
            ledger=r.Ledger(temp,{'fixture':'development'},max_new=24,budget=2,keys={'openrouter':'dummy-OR'},transport=transport)
            parse=lambda raw:dict(observed_cost_usd=.001)
            kw=dict(identity={'document_id':'dev'},reserve=.1)
            ledger.operation('dev-inventory','inventory',{},parse,**kw)
            r.Ledger(temp,{'fixture':'development'},max_new=24,budget=2,keys={'openrouter':'dummy-OR'},transport=transport).operation('dev-inventory','inventory',{},parse,**kw)
            self.assertEqual(len(calls),1)
    def test_uncertain_post_latches_no_resume(self):
        with tempfile.TemporaryDirectory() as temp:
            def transport(*args):raise TimeoutError('DO NOT retain arbitrary exception text')
            ledger=r.Ledger(temp,{'fixture':'development'},max_new=24,budget=2,keys={'openrouter':'dummy-OR'},transport=transport)
            with self.assertRaises(r.Stop):ledger.operation('dev-inventory','inventory',{},lambda raw:{},identity={},reserve=.1)
            with self.assertRaises(r.Stop):r.Ledger(temp,{'fixture':'development'},max_new=24,budget=2,keys={'openrouter':'dummy-OR'},transport=transport)
            self.assertNotIn('DO NOT',str([p.read_text() for p in Path(temp).rglob('*.json')]))
    def test_real_runner_mock_eight_docs_full24_and_no_repost(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);data=fixture(root,documents=8);calls=[]
            result=execute(root,data,calls);self.assertEqual(result['state'],'completed');self.assertEqual(len(calls),24)
            self.assertEqual(result['totals']['inventory_cases'],8);self.assertEqual(result['totals']['jev_cases'],8);self.assertEqual(result['totals']['stronger_cases'],8);self.assertLess(result['totals']['budget_charge_usd'],2)
            execute(root,data,calls);self.assertEqual(len(calls),24)
            for request in (root/'run/operations').glob('*/request.json'):
                value=r.j.loads(request.read_bytes())
                if 'messages' in value and value['response_format']['json_schema']['name'].endswith('inventory'):self.assertEqual(set(r.a.loads(value['messages'][1]['content'])),{'source'})
    def test_pause_after_inventory_then_resume_and_real_uncertain_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);data=fixture(root);calls=[]
            result=execute(root,data,calls,max_new=1);self.assertEqual(result['state'],'paused_at_operation_boundary');self.assertEqual(calls,['inventory'])
            observed=r.j.loads(next((root/'run').glob('observed-*.json')).read_bytes());self.assertEqual(observed['documents'][0]['failure']['stage'],'jev');self.assertFalse(observed['documents'][0]['failure']['intent_recorded'])
            execute(root,data,calls);self.assertEqual(calls,['inventory','jev','stronger'])
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);data=fixture(root,documents=2);calls=[]
            result=execute(root,data,calls,fail='jev');self.assertEqual(result['state'],'stopped_provider_operation');self.assertEqual(calls,['inventory','jev'])
            observed=r.j.loads(next((root/'run').glob('observed-*.json')).read_bytes());doc=observed['documents'][0]
            self.assertEqual(doc['failure']['kind'],'transport_uncertain');self.assertFalse(doc['provider_service_error']);self.assertTrue(doc['arms']['jev']['called']);self.assertFalse(doc['arms']['stronger']['called']);self.assertEqual(observed['documents'][1]['runtime_gate'],'not_started')
            with self.assertRaises(r.Stop):execute(root,data,calls)
            self.assertEqual(calls,['inventory','jev'])
    def test_actual_document_and_pdf_page_caps_before_any_dispatch(self):
        for docs,pages in [(9,1),(1,41)]:
            with tempfile.TemporaryDirectory() as temp:
                root=Path(temp);data=fixture(root,documents=docs,pages=pages);calls=[]
                with self.assertRaises(r.Stop):execute(root,data,calls)
                self.assertEqual(calls,[])
    def test_stage_and_budget_limits_before_intent_and_tamper_refusal(self):
        for kind in ('inventory','jev','stronger'):
            with tempfile.TemporaryDirectory() as temp:
                calls=[];transport=lambda *args:(calls.append(args) or (200,b'{}'));ledger=r.Ledger(temp,{'test':'cap'},max_new=24,budget=2,keys={'openrouter':'dummy-OR','jev':'dummy-jeV'},transport=transport)
                for i in range(8):ledger.operation(str(i),kind,{},lambda raw:dict(observed_cost_usd=0),identity={},reserve=.001)
                with self.assertRaises(r.Pause):ledger.operation('ninth',kind,{},lambda raw:{},identity={},reserve=.001)
                self.assertEqual(len(calls),8)
        with tempfile.TemporaryDirectory() as temp:
            calls=[];ledger=r.Ledger(temp,{'test':'budget'},max_new=24,budget=2,keys={'openrouter':'dummy-OR'},transport=lambda *args:calls.append(args))
            with self.assertRaises(r.Pause):ledger.operation('too-big','inventory',{},lambda raw:{},identity={},reserve=2.01)
            self.assertEqual(calls,[]);self.assertEqual(ledger.totals()['operations'],0)
        with tempfile.TemporaryDirectory() as temp:
            ledger=r.Ledger(temp,{'test':'tamper'},max_new=24,budget=2,keys={'openrouter':'dummy-OR'},transport=lambda *args:(200,b'{}'));parse=lambda raw:dict(observed_cost_usd=0)
            ledger.operation('once','inventory',{},parse,identity={},reserve=.001)
            request=next(Path(temp).glob('operations/*/request.json'));request.write_text('{"changed":true}')
            with self.assertRaises(r.Stop):r.Ledger(temp,{'test':'tamper'},max_new=24,budget=2,keys={'openrouter':'dummy-OR'})

    def test_structural_and_actual_paired_admission_gates(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);data=fixture(root,text='漢'*20000);calls=[]
            result=execute(root,data,calls);self.assertEqual(result['state'],'completed');self.assertEqual(calls,[])
            doc=r.j.loads((root/'run/completed.json').read_bytes())['documents'][0];self.assertEqual(doc['runtime_gate'],'request_size_review');self.assertIsNone(doc['inventory_sha256'])
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);data=fixture(root);calls=[];inv=data[4][next(iter(data[4]))];inv['events'][0]['timing'][0]['value']='2026-07-14'
            result=execute(root,data,calls);self.assertEqual(calls,['inventory']);doc=r.j.loads((root/'run/completed.json').read_bytes())['documents'][0];self.assertEqual(doc['runtime_gate'],'assembly_review');self.assertIsNone(doc['record_sha256'])
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);data=fixture(root);calls=[];inv=data[4][next(iter(data[4]))]
            for i in range(8):inv['events'].append(dict(id='extra'+str(i),phase='other',description='x'*4000,timing=[],evidence=inv['coverage']['evidence']))
            result=execute(root,data,calls);self.assertEqual(calls,['inventory']);doc=r.j.loads((root/'run/completed.json').read_bytes())['documents'][0];self.assertEqual(doc['runtime_gate'],'request_size_review');self.assertIsNotNone(doc['record_sha256']);self.assertIsNotNone(doc['payload_sha256'])
    def test_http_failure_and_invalid_stronger_schedule_have_distinct_states(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);data=fixture(root,documents=2);sources,manifest,freeze,auth,inv,v=data
            result=r.run(manifest,sources,freeze,root/'run',live=True,authorization=auth,source_labels_freeze_sha256='a'*64,keys={'openrouter':'dummy-OR','jev':'dummy-jeV'},transport=lambda *args:(503,b'{"error":"offline control"}'))
            self.assertEqual(result['state'],'stopped_provider_operation');doc=r.j.loads(next((root/'run').glob('observed-*.json')).read_bytes())['documents'][0]
            self.assertTrue(doc['provider_service_error']);self.assertEqual(doc['failure']['kind'],'http_error');self.assertEqual(doc['failure']['http_status'],503)
            self.assertTrue(any(r.sha(path.read_bytes())==doc['failure']['evidence_sha256'] for path in (root/'run/documents').rglob('failure-*.json')))
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);data=fixture(root);calls=[];data[5][next(iter(data[5]))]['assessments'].pop()
            result=execute(root,data,calls);self.assertEqual(result['state'],'completed');doc=r.j.loads((root/'run/completed.json').read_bytes())['documents'][0]
            self.assertEqual(doc['arms']['stronger']['status'],'review');self.assertFalse(doc['arms']['stronger']['source_coverage_complete']);self.assertFalse(doc['provider_service_error'])
    def test_completed_response_tamper_stops_and_authorization_drift_never_dispatches(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);data=fixture(root);calls=[];execute(root,data,calls)
            raw=next((root/'run/operations').glob('inventory-*/response.body'));raw.write_bytes(b'{}')
            with self.assertRaises(r.Stop):execute(root,data,calls)
            self.assertEqual(len(calls),3)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);data=fixture(root);calls=[];authorization=data[3];bad=r.j.loads(authorization.read_bytes());bad['nominal_budget_usd']=3;authorization.write_bytes(r.j.encode(bad))
            with self.assertRaises(r.Stop):execute(root,data,calls)
            self.assertEqual(calls,[])

    def test_reported_cost_overrun_preserves_completed_inventory_and_stops_next_call(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);data=fixture(root,documents=2);sources,manifest,freeze,auth,inv,v=data;calls=[];normal=transport_for(inv,v,calls)
            def transport(provider,body,key):
                status,raw=normal(provider,body,key);value=r.j.loads(raw);value['usage']['cost']=3.0
                return status,r.j.encode(value)
            result=r.run(manifest,sources,freeze,root/'run',live=True,authorization=auth,source_labels_freeze_sha256='a'*64,keys={'openrouter':'dummy-OR','jev':'dummy-jeV'},transport=transport)
            self.assertEqual(result['state'],'stopped_budget');self.assertEqual(calls,['inventory'])
            doc=r.j.loads(next((root/'run').glob('observed-*.json')).read_bytes())['documents'][0]
            self.assertIsNotNone(doc['inventory_sha256']);self.assertIsNotNone(doc['record_sha256']);self.assertEqual(doc['runtime_gate'],'postresponse_budget_stop');self.assertEqual(doc['failure']['kind'],'budget_stop');self.assertTrue(doc['failure']['intent_recorded']);self.assertFalse(doc['provider_service_error'])

    def test_receipt_hash_and_referenced_stop_tamper_reject(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);data=fixture(root);calls=[];execute(root,data,calls,fail='jev')
            observed=r.j.loads(next((root/'run').glob('observed-*.json')).read_bytes())
            self.assertTrue(r.audit_failure_receipts(observed,root/'run'))
            stop=next((root/'run/operations').glob('jev-*/stop.json'));stop.write_text('{"state":"provider_HTTP_error","retry_allowed":false}')
            with self.assertRaises(r.Stop):r.audit_failure_receipts(observed,root/'run')
    def test_unavailable_observation_boundary_blocks_first_dispatch(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);data=fixture(root);calls=[]
            with patch.object(r,'validate_observation',side_effect=ValueError('unavailable')):
                with self.assertRaises(ValueError):execute(root,data,calls)
            self.assertEqual(calls,[])

if __name__=='__main__':unittest.main(verbosity=2)
