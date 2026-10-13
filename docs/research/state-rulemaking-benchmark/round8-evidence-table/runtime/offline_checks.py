"""Guarded verifier-only controls; synthetic responses are not semantic findings."""
import copy,importlib.util,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('evidence_table_runtime',ROOT/'run_pipeline.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
MANIFEST=ROOT.parent/'sources/source-inputs.READY.json'
def doc():return r.load_sources(MANIFEST,MANIFEST.parent)[0]
def setup(root):
    freeze=root/'implementation.json';r.put(freeze,r.code_pins());auth=root/'authorization.json';r.put(auth,dict(schema_version='round8-evidence-table.live-authorization.v1',implementation_sha256=r.sha(freeze.read_bytes()),manifest_sha256=r.sha(MANIFEST.read_bytes()),source_labels_frozen_before_outputs=True,source_labels_freeze_sha256='a'*64,nominal_budget_usd=2.0,**r.auth_scope()));return freeze,auth

def verdict():
    d=doc();ev=[dict(quote=d['source']['source_text'],occurrence=None,context=None)]
    return dict(schema_version='round7.record_verdict.v1',document_id=d['source']['document_id'],payload_sha256=d['common']['payload_sha256'],completeness=dict(label='uncertain',reason='Synthetic structural control only',evidence=ev),source_identity=dict(label='uncertain',reason='Synthetic',evidence=ev),assessments=[dict(item_id=item['id'],support='uncertain',association='uncertain',requirements='uncertain',reason='Synthetic not semantic acceptance',evidence=ev) for _,item in r.p.all_items(d['assembled']['record'])],missing_items=[],contradictions=[])

def transport(calls,fail=None,http=None,jev_tokens=100):
    def respond(provider,body,key):
        stage='jev' if provider=='jev' else 'stronger';calls.append(stage)
        if stage==fail:raise TimeoutError('sensitive arbitrary text')
        if stage==http:return 503,b'{"error":"synthetic"}'
        if provider=='jev':return 200,r.j.encode(dict(model=r.a.j.JEV_MODEL,answers={k:dict(type='choice',choice='uncertain',confidence=.8,probabilities={label:.8 if label=='uncertain' else .1 for label in q['criteria']}) for k,q in body['questions'].items()},usage=dict(input_tokens=jev_tokens,output_tokens=5)))
        return 200,r.j.encode(dict(model=r.a.MODEL,provider='OpenAI',choices=[dict(finish_reason='stop',message=dict(content=r.j.encode(verdict()).decode()))],usage=dict(prompt_tokens=100,completion_tokens=100,cost=.0012)))
    return respond

def run(root,respond,max_new=2):
    freeze,auth=setup(root);return r.run(MANIFEST,MANIFEST.parent,freeze,root/'run',live=True,authorization=auth,source_labels_freeze_sha256='a'*64,max_new=max_new,keys={'jev':'dummy-jeV','openrouter':'dummy-OR'},transport=respond)

class Controls(unittest.TestCase):
    def test_exact_retained_payload_record_and_provider_shape(self):
        d=doc();plans=d['plans'];wire=d['restoration']['wire'];self.assertEqual(r.codec.restore(wire,d['common']['payload_sha256']),d['common']['payload']);self.assertEqual(len(wire['evidence_table']),42);self.assertEqual(set(plans),{'jev','stronger'})
        original={stage:r.j.loads(Path(d['unit']['retained_inputs']['original_'+stage+'_request']['path']).read_bytes()) for stage in plans};strong=copy.deepcopy(plans['stronger']['body']);strong['messages'][0]['content']=strong['messages'][0]['content'][:-len(r.INSTRUCTIONS.read_text())];wrapper=r.j.loads(strong['messages'][1]['content']);wrapper['payload']=r.codec.restore(wrapper['payload'],d['common']['payload_sha256']);strong['messages'][1]['content']=r.j.encode(wrapper).decode();self.assertEqual(strong,original['stronger'])
        jev=copy.deepcopy(plans['jev']['body']);jev['state']=r.codec.restore(jev['state'],d['common']['payload_sha256'])
        for q in jev['questions'].values():q['instructions']=q['instructions'][:-len(r.INSTRUCTIONS.read_text())]
        self.assertEqual(jev,original['jev']);self.assertEqual(set(jev),{'model','state','questions'});self.assertEqual(plans['stronger']['body']['response_format'],original['stronger']['response_format']);self.assertTrue(all(x['admission']['admitted'] for x in plans.values()))
    def test_adversarial_restoration(self):
        d=doc();wire=d['restoration']['wire'];before=r.j.encode(wire)
        for kind in ('source','quote','swap','reorder','drop_field','drop_evidence','unused_table','negative','bool','span','version'):
            bad=copy.deepcopy(wire);ev=bad['payload']['record']['events'][0]['evidence']
            if kind=='source':bad['payload']['source_text']+='x'
            elif kind=='quote':bad['evidence_table'][0]['quote']+='x'
            elif kind=='swap':ev[0]=(ev[0]+1)%len(bad['evidence_table'])
            elif kind=='reorder':ev.reverse()
            elif kind=='drop_field':bad['payload']['record']['events'][0].pop('description')
            elif kind=='drop_evidence':ev.pop()
            elif kind=='unused_table':bad['evidence_table'].append(copy.deepcopy(bad['evidence_table'][0]))
            elif kind=='negative':ev[0]=-1
            elif kind=='bool':ev[0]=True
            elif kind=='span':bad['evidence_table'][0]['end']+=1
            else:bad['schema_version']='unknown'
            with self.subTest(kind=kind):
                with self.assertRaises(r.codec.InvalidWire):r.codec.restore(bad,d['common']['payload_sha256'])
        self.assertEqual(r.j.encode(wire),before)
        with self.assertRaises(r.codec.InvalidWire):r.codec.restore(wire,'0'*64)
    def test_unicode_repeated_spans_and_empty_evidence(self):
        text='α repeated.\nα repeated.\n';payload={'source_text':text,'source_text_sha256':r.sha(text.encode()),'record':{'claims':[{'id':'x','evidence':[{'start':0,'end':11,'quote':'α repeated.'},{'start':12,'end':23,'quote':'α repeated.'},{'start':0,'end':11,'quote':'α repeated.'}]},{'id':'y','evidence':[]}],'uncertainties':[]}}
        wire=r.codec.encode(payload);self.assertEqual(len(wire['evidence_table']),2);self.assertEqual(wire['payload']['record']['claims'][0]['evidence'],[0,1,0]);self.assertEqual(r.codec.restore(wire,r.sha(r.j.encode(payload))),payload)
    def test_two_calls_zero_inventory_and_completed_resume(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);calls=[];respond=transport(calls);result=run(root,respond);self.assertEqual(calls,['jev','stronger']);self.assertEqual(result['state'],'completed');self.assertEqual(result['totals']['inventory_cases'],0);self.assertEqual(result['totals']['prior_budget_debit_usd'],.428936);self.assertAlmostEqual(result['totals']['budget_charge_usd'],.428936+result['totals']['new_budget_charge_usd']);run(root,respond);self.assertEqual(len(calls),2)
            completed=r.j.loads((root/'run/completed.json').read_bytes())['documents'][0];self.assertTrue(all(a['status']=='review' for a in completed['arms'].values()));self.assertEqual(completed['payload_sha256'],r.auth_scope()['original_payload_sha256'])
    def test_prohibited_inventory_and_stage_caps(self):
        for stage in ('inventory','jev','stronger'):
            with tempfile.TemporaryDirectory() as temp:
                calls=[];ledger=r.Ledger(temp,{'synthetic':'caps'},keys={'jev':'dummy','openrouter':'dummy'},transport=lambda *args:(calls.append(args) or (200,b'{}')))
                if stage=='inventory':
                    with self.assertRaises(r.Stop):ledger.operation('bad',stage,{},lambda raw:{},identity={},reserve=.001)
                    self.assertEqual(calls,[]);self.assertEqual(list((Path(temp)/'operations').iterdir()),[])
                else:
                    ledger.operation('first',stage,{},lambda raw:dict(observed_cost_usd=0),identity={},reserve=.001)
                    with self.assertRaises(r.Pause):ledger.operation('second',stage,{},lambda raw:{},identity={},reserve=.001)
                    self.assertEqual(len(calls),1)
    def test_failure_latch_http_and_no_credential_echo(self):
        for options in ({'fail':'jev'},{'fail':'stronger'},{'http':'stronger'}):
            with tempfile.TemporaryDirectory() as temp:
                root=Path(temp);calls=[];respond=transport(calls,**options);result=run(root,respond);self.assertEqual(result['state'],'stopped_provider_operation');self.assertEqual(calls,['jev'] if options.get('fail')=='jev' else ['jev','stronger']);count=len(calls)
                with self.assertRaises(r.Stop):run(root,respond)
                self.assertEqual(len(calls),count);self.assertNotIn('sensitive arbitrary text',str(result))
    def test_postresponse_budget_preserves_jev_and_stops(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);calls=[];result=run(root,transport(calls,jev_tokens=42000000));self.assertEqual(calls,['jev']);self.assertEqual(result['state'],'stopped_budget');self.assertGreater(result['totals']['budget_charge_usd'],2)
            observed=r.j.loads(next((root/'run').glob('observed-*.json')).read_bytes())['documents'][0];self.assertEqual(observed['runtime_gate'],'postresponse_budget_stop');self.assertTrue(observed['arms']['jev']['called']);self.assertIsNotNone(observed['record_sha256']);self.assertFalse(observed['arms']['stronger']['called'])
    def test_no_refund_prior_debits_and_budget_admission(self):
        value=r.verify_prior_debit();self.assertEqual(len(value['operations']),3);self.assertAlmostEqual(sum(x['conservative_debit_usd'] for x in value['operations']),.428936);self.assertAlmostEqual(r.MAX_RESERVATION,.123648);self.assertAlmostEqual(r.PRIOR_DEBIT+r.MAX_RESERVATION,.552584)
        bad=copy.deepcopy(value);bad['operations'][2]['conservative_debit_usd']=bad['operations'][2]['reported_cost_usd']
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'prior-debit.json').write_bytes(r.j.encode(bad))
            with patch.object(r,'ROOT',root):
                with self.assertRaises(r.Stop):r.verify_prior_debit()
        with tempfile.TemporaryDirectory() as temp:
            calls=[];ledger=r.Ledger(temp,{'synthetic':'budget'},keys={'jev':'dummy'},transport=lambda *args:calls.append(args))
            with self.assertRaises(r.Pause):ledger.operation('over','jev',{},lambda raw:{},identity={},reserve=1.6)
            self.assertEqual(calls,[]);self.assertFalse(any((Path(temp)/'operations').glob('*/intent.json')))
    def test_changed_auth_denied_before_intent(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);freeze,auth=setup(root);value=r.j.loads(auth.read_bytes());value['inventory_calls']=1;auth.write_bytes(r.j.encode(value));calls=[]
            with self.assertRaises(r.Stop):r.run(MANIFEST,MANIFEST.parent,freeze,root/'run',live=True,authorization=auth,source_labels_freeze_sha256='a'*64,keys={'jev':'dummy','openrouter':'dummy'},transport=lambda *args:calls.append(args))
            self.assertEqual(calls,[]);self.assertFalse((root/'run').exists())
    def test_final_full_body_boundaries_and_paired_denial(self):
        d=doc();source=d['source'];assembled=d['assembled'];original=r.a.admission
        # The actual request builders always generate both full bodies. Copying the input plan into a test loader isolates final-body denial without mutating originals.
        for denied in ('jev','stronger'):
            with tempfile.TemporaryDirectory() as temp:
                root=Path(temp);mockdoc=copy.deepcopy(d);body=mockdoc['plans'][denied]['body']
                if denied=='stronger':body['messages'][0]['content']+='x'*(40001-r.a.estimate_input(body));mockdoc['plans'][denied]['admission'].update(admitted=False,reason='synthetic boundary overlimit')
                else:
                    k=max(body['questions'],key=lambda k:len(r.j.encode(body['questions'][k])));measure=original(body,'jev')['state_longest_estimate'];body['questions'][k]['instructions']+='x'*(32001-measure);mockdoc['plans'][denied]['admission']=original(body,'jev')
                calls=[]
                with patch.object(r,'load_sources',return_value=[mockdoc]):result=run(root,transport(calls))
                self.assertEqual(calls,[]);self.assertEqual(result['state'],'completed');self.assertEqual(result['totals']['operations'],0)
        for delta in (-1,0,1):
            body=r.j.loads(Path(d['unit']['retained_inputs']['original_stronger_request']['path']).read_bytes());body['messages'][0]['content']+='x'*(40000+delta-d['plans']['stronger']['admission']['estimate'])
            # Same final admission formula used by requests; reservations remain tied to exact body bytes.
            with patch.object(r.a,'or_body',return_value=body):plans,_,_=r.requests(source,assembled)
            self.assertEqual(plans['stronger']['admission']['estimate'],40000+delta);self.assertEqual(plans['stronger']['admission']['admitted'],delta<=0)
            body=copy.deepcopy(d['plans']['jev']['body']);k=max(body['questions'],key=lambda k:len(r.j.encode(body['questions'][k])));measure=original(body,'jev')['state_longest_estimate'];body['questions'][k]['instructions']+='x'*(32000+delta-measure);receipt=original(body,'jev');self.assertEqual(receipt['state_longest_estimate'],32000+delta);self.assertEqual(receipt['admitted'],delta<=0)
    def test_retained_manifest_hash_change_denied_before_intent(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);freeze,auth=setup(root);value=r.j.loads(MANIFEST.read_bytes());unit=value['documents'][0]
            for kind in ('text','pdf'):unit[kind+'_path']=os.path.relpath((MANIFEST.parent/unit[kind+'_path']).resolve(),root)
            unit['retained_inputs']['common_payload']['sha256']='0'*64;manifest=root/'manifest.json';manifest.write_bytes(r.j.encode(value));calls=[]
            with self.assertRaises(r.Stop):r.run(manifest,root,freeze,root/'run',live=True,authorization=auth,source_labels_freeze_sha256='a'*64,keys={'jev':'dummy','openrouter':'dummy'},transport=lambda *args:calls.append(args))
            self.assertEqual(calls,[]);self.assertFalse((root/'run').exists())
    def test_jev_total_boundary_and_completion_mismatch(self):
        d=doc()
        for delta in (-1,0,1):
            # Synthetic empty state isolates total guard; the fixed production record must still satisfy both guards.
            body=copy.deepcopy(d['plans']['jev']['body']);body['state']={};needed=64000+delta-r.a.estimate_input(body);keys=list(body['questions']);quotient,remainder=divmod(needed,len(keys))
            for n,k in enumerate(keys):body['questions'][k]['instructions']+='x'*(quotient+(n<remainder))
            receipt=r.a.admission(body,'jev');self.assertEqual(receipt['estimate'],64000+delta);self.assertLess(receipt['state_longest_estimate'],32000);self.assertEqual(receipt['admitted'],delta<=0)
        original=r.j.loads(Path(d['unit']['retained_inputs']['original_stronger_request']['path']).read_bytes());original['max_tokens']=4097
        with patch.object(r.a,'or_body',return_value=original):plans,_,_=r.requests(d['source'],d['assembled'])
        self.assertFalse(plans['stronger']['admission']['admitted'])
    def test_operation_pause_resume_and_invalid_response_latch(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);calls=[];respond=transport(calls);result=run(root,respond,max_new=1);self.assertEqual(result['state'],'paused_at_operation_boundary');self.assertEqual(calls,['jev']);result=run(root,respond,max_new=2);self.assertEqual(result['state'],'completed');self.assertEqual(calls,['jev','stronger'])
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);calls=[]
            def invalid(provider,body,key):calls.append(provider);return 200,b'{"model":"wrong"}'
            result=run(root,invalid);self.assertEqual(result['state'],'stopped_provider_operation');self.assertEqual(calls,['jev'])
            with self.assertRaises(r.Stop):run(root,invalid)
            self.assertEqual(calls,['jev'])
if __name__=='__main__':unittest.main(verbosity=2)
