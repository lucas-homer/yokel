"""Deterministic controls with synthetic provider replies; never resolves keys or networks."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
from pypdf import PdfWriter
import provider_adapters as a
import run_pipeline as r
from operations import Ledger,Pause,Stop,put,sha
P=Path(__file__).resolve().parent.parent/'pipeline'
sys.path.insert(0,str(P))
import pipeline as p
import development_fixtures as f
j=a.j

def or_reply(value,**changes):
    obj={'model':a.MODEL,'provider':'OpenAI','choices':[{'finish_reason':'stop','message':{'content':json.dumps(value)}}],'usage':{'prompt_tokens':100,'completion_tokens':100,'cost':.0012}}
    obj.update(changes);return j.encode(obj)

def jev_reply(questions,label='pass'):
    return j.encode({'model':j.JEV_MODEL,'answers':{k:{'type':'choice','choice':label,'confidence':.8,'probabilities':{v:(.8 if v==label else .1) for v in q['criteria']}} for k,q in questions.items()},'usage':{'input_tokens':100,'output_tokens':5}})

def fixture():
    source=p.make_source('Notice ABC. Comments due January 1, 2026. Include ABC.', 'doc-000000000001')
    inv=f.empty_inventory(source);inv['coverage']['status']='claimed_complete'
    inv['events']=[f.event('comment','written_comment','Comments due January 1, 2026.',[f.timing('close','January 1, 2026','2026-01-01')])]
    inv['requirements']=[f.requirement('reference','reference','Include ABC.',['comment'])]
    inv['identities']=[{'id':'identity','kind':'notice','literal':'ABC','relation':'canonical','event_ids':['comment'],'evidence':f.evidence('Notice ABC.')}]
    assembled=p.assemble(source,inv)
    verdict={'schema_version':'round6.record_verdict.v1','document_id':source['document_id'],'payload_sha256':p.verification_payload(source,assembled)['payload_sha256'],
      'completeness':{'label':'complete','reason':'Synthetic control','evidence':f.evidence(source['source_text'])},'source_identity':{'label':'resolved','reason':'Synthetic control','evidence':f.evidence('Notice ABC.')},
      'assessments':[{'item_id':x['id'],'support':'supported','association':'matched','requirements':'preserved','reason':'Synthetic control','evidence':f.evidence(source['source_text'])} for _,x in p.all_items(assembled['record'])], 'missing_items':[],'contradictions':[]}
    return source,inv,assembled,verdict

class Controls(unittest.TestCase):
    def test_approved_caps(self):
        self.assertEqual(a.LIMITS['Jev_calls'],8);self.assertEqual(a.LIMITS['OR_input_estimate'],35000);self.assertAlmostEqual(a.MAX_RESERVATION,1.960704)
    def test_ky_actual_admission(self):
        src,inv=f.ky_fixture();out=p.assemble(src,inv);self.assertTrue(out['validation']['valid'])
        for stage,plan in [('inventory',p.inventory_request(src)),('stronger',p.verification_request(src,out))]:
            self.assertLessEqual(a.estimate_input(a.or_request(plan,stage)),35000)
        a.jev_request(p.verification_payload(src,out)['payload'],r.question_plan(p))
        self.assertEqual(src['pdf_pages'],8);self.assertGreater(len(src['source_text']),19000)
    def test_no_clipping_or_size_bypass(self):
        with self.assertRaises(Stop):a.or_request({'system':'x','user':{'source':'x'*35000},'response_schema':{}},'inventory')
        with self.assertRaises(Stop):a.jev_request({'source':'x'*32000},r.question_plan(p))
    def test_source_first_and_identical_pair(self):
        src,inv,out,v=fixture();q=r.question_plan(p);body=a.or_request(p.inventory_request(src),'inventory')
        self.assertEqual(set(j.loads(body['messages'][1]['content'])),{'source'})
        common=p.verification_payload(src,out);jb=a.jev_request(common['payload'],q);ob=a.or_request(p.verification_request(src,out),'stronger')
        self.assertEqual(jb['state'],j.loads(ob['messages'][1]['content'])['payload']);self.assertEqual(jb['state']['source_text'],src['source_text'])
        self.assertNotIn('answers',jb['state']);self.assertNotIn('verdict',jb['state'])
    def test_schema_relocation_exact(self):
        src,_,_,_=fixture();plan=p.inventory_request(src);body=a.or_request(plan,'inventory')
        self.assertEqual(body['response_format']['json_schema']['schema'],plan['response_schema'])
        self.assertEqual(body['provider']['max_price'],{'prompt':2,'completion':10});self.assertFalse(body['provider']['allow_fallbacks'])
    def test_or_model_provider_usage_fail_closed(self):
        for changes in [{'model':'wrong'},{'provider':'other'},{'usage':{'prompt_tokens':100,'completion_tokens':20}},{'choices':[{'finish_reason':'length','message':{'content':'{}'}}]}]:
            with self.subTest(changes=changes),self.assertRaises(Stop):a.parse_or(or_reply({},**changes))
        obj=j.loads(or_reply({}));obj.pop('provider');self.assertFalse(a.parse_or(j.encode(obj))['provider_identity_verified'])
    def test_jev_incomplete_batch(self):
        q=r.question_plan(p);obj=j.loads(jev_reply(q));obj['answers'].pop('support')
        with self.assertRaises(Stop):a.parse_jev(j.encode(obj),q)
    def test_tie_abstains(self):
        q=r.question_plan(p);obj=j.loads(jev_reply(q));obj['answers']['support'].update(choice='pass',probabilities={'pass':.5,'fail':.5,'uncertain':0})
        self.assertIsNone(a.parse_jev(j.encode(obj),q)['answers']['support']['label'])
    def test_terminal_positive_and_each_negative_dimension(self):
        src,inv,out,v=fixture();self.assertTrue(p.validate_verdict(src,out,v)['valid']);labels={k:'pass' for k in r.CRITERIA}
        self.assertTrue(r.terminal_arm('jev',labels,out)['complete_record_shadow_accepted'])
        for key in labels:
            bad={**labels,key:'fail'};self.assertFalse(r.terminal_arm('jev',bad,out)['complete_record_shadow_accepted'])
        self.assertFalse(r.terminal_arm('stronger',labels,out,valid=False)['complete_record_shadow_accepted'])
        self.assertFalse(r.terminal_arm('jev',labels,out)['action_ready'])
    def test_uncertainty_vetoes_favorable_model(self):
        src,inv,_,_=fixture();inv['coverage']['status']='uncertain';out=p.assemble(src,inv)
        self.assertFalse(r.terminal_arm('jev',{k:'pass' for k in r.CRITERIA},out)['complete_record_shadow_accepted'])
    def test_omission_explanation_not_empty_success(self):
        src,inv,out,v=fixture();v['completeness']['label']='incomplete';v['missing_items']=[{'kind':'requirement','description':'missing instruction','evidence':f.evidence('Include ABC.')}]
        checked=p.validate_verdict(src,out,v);self.assertTrue(checked['valid']);self.assertEqual(r.stronger_labels(checked['normalized_verdict'])['completeness'],'fail')
    def test_changed_payload_verdict_rejected(self):
        src,_,out,v=fixture();v['payload_sha256']='0'*64;self.assertFalse(p.validate_verdict(src,out,v)['valid'])
    def test_all_loaded_dependency_pins_and_drift(self):
        pins=r.code_pins(P/'pipeline.py')
        for name in ('pipeline.py','record.schema.json','inventory.schema.json','verdict.schema.json'):
            self.assertIn(str(P/name),pins['code'])
        with tempfile.TemporaryDirectory() as tmp:
            receipt=Path(tmp)/'freeze.json';put(receipt,pins);r.verify_implementation(receipt)
            pins['code'][str(P/'record.schema.json')]='0'*64;receipt.write_bytes(j.encode(pins))
            with self.assertRaises(Stop):r.verify_implementation(receipt)
    def ledger(self,root,transport,max_new=24,budget=2):return Ledger(root,{'test':'offline'},max_new=max_new,budget=budget,keys={'jev':'dummy-jeV','openrouter':'dummy-OR'},transport=transport)
    def test_resume_no_repost(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls=[];transport=lambda *args:(calls.append(args) or (200,or_reply({})))
            l=self.ledger(tmp,transport);kw=dict(identity={'id':'one'},reserve=.1)
            value=l.operation('one','inventory',{'x':1},a.parse_or,**kw)
            self.assertEqual(self.ledger(tmp,transport).operation('one','inventory',{'x':1},a.parse_or,**kw),value);self.assertEqual(len(calls),1)
    def test_changed_identity_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            l=self.ledger(tmp,lambda *x:(200,or_reply({})));l.operation('one','inventory',{},a.parse_or,identity={},reserve=.1)
            with self.assertRaises(Stop):l.operation('one','inventory',{'changed':1},a.parse_or,identity={},reserve=.1)
    def test_intent_identity_and_reservation_tamper_rejected(self):
        for field,value in [('identity',{'changed':True}),('reserved_nominal_usd',0)]:
            with tempfile.TemporaryDirectory() as tmp:
                l=self.ledger(tmp,lambda *x:(200,or_reply({})));l.operation('one','inventory',{},a.parse_or,identity={},reserve=.1)
                file=next(Path(tmp).glob('operations/*/intent.json'));obj=j.loads(file.read_bytes());obj[field]=value;file.write_bytes(j.encode(obj))
                with self.assertRaises(Stop):self.ledger(tmp,lambda *x:None)
    def test_recomputed_reservation_change_rejected_on_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            l=self.ledger(tmp,lambda *x:(200,or_reply({})));l.operation('one','inventory',{},a.parse_or,identity={},reserve=.1)
            with self.assertRaises(Stop):l.operation('one','inventory',{},a.parse_or,identity={},reserve=0)
    def test_uncertain_post_latched(self):
        with tempfile.TemporaryDirectory() as tmp:
            def transport(*x):raise TimeoutError()
            l=self.ledger(tmp,transport)
            with self.assertRaises(Stop):l.operation('one','inventory',{},a.parse_or,identity={},reserve=.1)
            with self.assertRaises(Stop):self.ledger(tmp,transport)
    def test_error_usage_latched(self):
        with tempfile.TemporaryDirectory() as tmp:
            l=self.ledger(tmp,lambda *x:(200,b'{}'))
            with self.assertRaises(Stop):l.operation('one','inventory',{},a.parse_or,identity={},reserve=.1)
            with self.assertRaises(Stop):self.ledger(tmp,lambda *x:None)
    def test_budget_before_post(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls=[];l=self.ledger(tmp,lambda *x:calls.append(x),budget=.01)
            with self.assertRaises(Pause):l.operation('one','inventory',{},a.parse_or,identity={},reserve=.02)
            self.assertEqual(calls,[])
    def test_exact_eight_batched_jev_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            q=r.question_plan(p);calls=[];l=self.ledger(tmp,lambda *x:(calls.append(x) or (200,jev_reply(q))))
            for n in range(8):l.operation(str(n),'jev',{},lambda raw:a.parse_jev(raw,q),identity={},reserve=.001)
            with self.assertRaises(Pause):l.operation('9','jev',{},lambda raw:a.parse_jev(raw,q),identity={},reserve=.001)
            self.assertEqual(len(calls),8)
    def test_secret_echo_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            l=self.ledger(tmp,lambda *x:(200,b'dummy-OR'))
            with self.assertRaises(Stop):l.operation('one','inventory',{},a.parse_or,identity={},reserve=.1)
            self.assertFalse(list(Path(tmp).glob('operations/*/response.body')))
    def test_full_staged_resume_and_blind_requests(self):
        src,inv,out,v=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'sources').mkdir();s=root/'sources';(s/'native.txt').write_text(src['source_text']);w=PdfWriter();w.add_blank_page(width=100,height=100);w.write(s/'source.pdf')
            manifest=s/'manifest.json';unit={'document_id':src['document_id'],'channel':'native','text_path':'native.txt','text_sha256':sha((s/'native.txt').read_bytes()),'pdf_path':'source.pdf','pdf_sha256':sha((s/'source.pdf').read_bytes()),'pdf_pages':1,'scope':'full_notice','native_page_map_known':False}
            put(manifest,{'schema_version':'round4.sources.v1','documents':[unit]});freeze=root/'implementation.json';put(freeze,r.code_pins(P/'pipeline.py'));auth=root/'auth.json';put(auth,{'schema_version':'round6.live-authorization.v1','implementation_sha256':sha(freeze.read_bytes()),'manifest_sha256':sha(manifest.read_bytes()),'source_labels_frozen_before_outputs':True,'source_labels_freeze_sha256':'a'*64,'nominal_budget_usd':2.0})
            calls=[]
            def transport(provider,body,key):
                calls.append(body)
                if provider=='jev':return 200,jev_reply(body['questions'])
                return 200,or_reply(inv if len(calls)==1 else v)
            kw=dict(live=True,authorization=auth,source_labels_freeze_sha256='a'*64,max_new=24,keys={'jev':'dummy-jeV','openrouter':'dummy-OR'},transport=transport)
            result=r.run(manifest,s,freeze,root/'run',**kw);self.assertEqual(result['state'],'completed');self.assertEqual(len(calls),3)
            self.assertEqual(calls[1]['state'],j.loads(calls[2]['messages'][1]['content'])['payload'])
            r.run(manifest,s,freeze,root/'run',**kw);self.assertEqual(len(calls),3)
            terminal=j.loads(next((root/'run/documents').glob('*/terminal.json')).read_bytes());self.assertTrue(all(x['complete_record_shadow_accepted'] for x in terminal['arms'].values()))

if __name__=='__main__':unittest.main(verbosity=2)
