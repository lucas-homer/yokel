"""One-call controls; fake whole verdicts never count as semantic observations."""
import copy,importlib.util,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('stronger_cap_runtime',ROOT/'run_pipeline.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
MANIFEST=ROOT.parent/'sources/source-inputs.READY.json'
def doc():return r.load_sources(MANIFEST,MANIFEST.parent)[0]
def setup(root):
    freeze=root/'implementation.json';r.put(freeze,r.code_pins());auth=root/'authorization.json';r.put(auth,dict(schema_version='round8-stronger-cap-probe.live-authorization.v1',implementation_sha256=r.sha(freeze.read_bytes()),manifest_sha256=r.sha(MANIFEST.read_bytes()),source_labels_frozen_before_outputs=True,source_labels_freeze_sha256='a'*64,nominal_budget_usd=2.0,**r.auth_scope()));return freeze,auth

def verdict():
    d=doc();ev=[dict(quote='Notice of Hearing',occurrence=None,context=None)]
    return dict(schema_version='round7.record_verdict.v1',document_id=d['source']['document_id'],payload_sha256=d['common']['payload_sha256'],completeness=dict(label='uncertain',reason='Authored synthetic control, no semantic finding',evidence=ev),source_identity=dict(label='uncertain',reason='Authored synthetic control',evidence=ev),assessments=[dict(item_id=item['id'],support='uncertain',association='uncertain',requirements='uncertain',reason='Synthetic structural test only',evidence=ev) for _,item in r.p.all_items(d['assembled']['record'])],missing_items=[],contradictions=[])
def transport(calls,kind='valid',cost=.0012):
    def respond(provider,body,key):
        calls.append(provider)
        if kind=='timeout':raise TimeoutError('sensitive arbitrary text')
        if kind=='http':return 503,b'{"error":"synthetic"}'
        finish='length' if kind=='length' else 'stop';content='{"assessments":[' if kind=='length' else r.j.encode(verdict()).decode()
        return 200,r.j.encode(dict(model=r.a.MODEL,provider='OpenAI',choices=[dict(finish_reason=finish,message=dict(content=content))],usage=dict(prompt_tokens=100,completion_tokens=100,cost=cost)))
    return respond

def run(root,respond,max_new=1):
    freeze,auth=setup(root);return r.run(MANIFEST,MANIFEST.parent,freeze,root/'run',live=True,authorization=auth,source_labels_freeze_sha256='a'*64,max_new=max_new,keys={'openrouter':'dummyOR'},transport=respond)

class Controls(unittest.TestCase):
    def test_only_max_tokens_request_delta_and_exact_admission(self):
        d=doc();original=r.j.loads(Path(d['unit']['retained_inputs']['wire_stronger_request']['path']).read_bytes());expected=copy.deepcopy(original);expected['max_tokens']=8192;self.assertEqual(set(d['plans']),{'stronger'});self.assertEqual(d['plans']['stronger']['body'],expected);self.assertEqual(r.a.estimate_input(original),35747);self.assertEqual(d['plans']['stronger']['admission']['estimate'],35747);self.assertAlmostEqual(d['plans']['stronger']['admission']['reservation_usd'],.153414);self.assertEqual(r.codec.restore(d['restoration']['wire'],d['common']['payload_sha256']),d['common']['payload'])
    def test_all_five_conservative_debits_and_honest_prior_reporting(self):
        value=r.verify_prior_debit();self.assertEqual(len(value['operations']),5);self.assertAlmostEqual(sum(x['conservative_debit_usd'] for x in value['operations']),.542976718);self.assertAlmostEqual(value['reporting']['recoverable_native_reported_usd'],.307989);self.assertAlmostEqual(value['reporting']['jev_usage_rate_estimated_usd'],.000502026);self.assertAlmostEqual(value['reporting']['parsed_result_accounted_usd'],.180936526);self.assertIsNone(value['operations'][4]['parsed_result_accounted_usd']);self.assertAlmostEqual(value['operations'][4]['recoverable_native_reported_usd'],.058736);self.assertAlmostEqual(value['operations'][4]['conservative_debit_usd'],.112454);self.assertAlmostEqual(r.MAX_RESERVATION,.16192);self.assertAlmostEqual(r.MAX_RESERVATION+r.PRIOR_DEBIT,.704896718)
        bad=copy.deepcopy(value);bad.pop('reporting');bad['operations'][4]['conservative_debit_usd']=.058736
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'prior-debit.json').write_bytes(r.j.encode(bad))
            with patch.object(r,'ROOT',root):
                with self.assertRaises(r.Stop):r.verify_prior_debit()
    def test_one_call_resume_and_no_borrowed_jev(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);calls=[];respond=transport(calls);result=run(root,respond);self.assertEqual(calls,['openrouter']);self.assertEqual(result['state'],'completed');self.assertEqual(result['totals']['operations'],1);self.assertEqual(result['totals']['jev_cases'],0);self.assertEqual(result['totals']['inventory_cases'],0);run(root,respond);self.assertEqual(calls,['openrouter'])
            observed=r.j.loads((root/'run/completed.json').read_bytes())['documents'][0];self.assertFalse(observed['arms']['jev']['called']);self.assertEqual(observed['arms']['jev']['status'],'not_started');self.assertNotIn('judgment',observed['arms']['jev']);self.assertEqual(observed['runtime_gate'],'stronger_verification_completed');self.assertEqual(observed['arms']['stronger']['status'],'review')
    def test_no_other_stage_or_second_attempt(self):
        for stage in ('inventory','jev','stronger'):
            with tempfile.TemporaryDirectory() as temp:
                calls=[];ledger=r.Ledger(temp,{'synthetic':'stage caps'},keys={'openrouter':'dummyOR'},transport=lambda *args:(calls.append(args) or (200,b'{}')))
                if stage!='stronger':
                    with self.assertRaises(r.Stop):ledger.operation('bad',stage,{},lambda raw:{},identity={},reserve=.001)
                    self.assertEqual(calls,[]);self.assertEqual(list((Path(temp)/'operations').iterdir()),[])
                else:
                    ledger.operation('first',stage,{},lambda raw:dict(observed_cost_usd=0),identity={},reserve=.001)
                    with self.assertRaises(r.Pause):ledger.operation('second',stage,{},lambda raw:{},identity={},reserve=.001)
                    self.assertEqual(len(calls),1)
    def test_length_http_timeout_latches_and_raw_cost_reporting(self):
        for kind in ('length','http','timeout'):
            with tempfile.TemporaryDirectory() as temp:
                root=Path(temp);calls=[];respond=transport(calls,kind,cost=.058736);result=run(root,respond);self.assertEqual(result['state'],'stopped_provider_operation');self.assertEqual(calls,['openrouter']);self.assertEqual(result['totals']['observed_accounted_usd'],0)
                if kind=='length':self.assertAlmostEqual(result['totals']['recoverable_native_reported_usd'],.058736);self.assertAlmostEqual(result['totals']['new_budget_charge_usd'],.153414);self.assertFalse(any((root/'run/operations').glob('*/result.json')))
                with self.assertRaises(r.Stop):run(root,respond)
                self.assertEqual(calls,['openrouter']);self.assertNotIn('sensitive arbitrary text',str(result));observed=r.j.loads(next((root/'run').glob('observed-*.json')).read_bytes());self.assertEqual(observed['documents'][0]['provider_service_error'],kind=='http')
    def test_invalid_response_raw_over_reserve_is_not_undercharged(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);calls=[];result=run(root,transport(calls,'length',cost=1.9));self.assertAlmostEqual(result['totals']['new_budget_charge_usd'],1.9);self.assertAlmostEqual(result['totals']['recoverable_native_reported_usd'],1.9);self.assertGreater(result['totals']['budget_charge_usd'],2);self.assertEqual(result['state'],'stopped_provider_operation');self.assertFalse(any((root/'run/operations').glob('*/result.json')))
    def test_duplicate_nonfinite_native_costs_are_unavailable_not_salvaged(self):
        for raw in (b'{"usage":{"cost":1,"cost":2}}',b'{"usage":{"cost":NaN}}'):
            with tempfile.TemporaryDirectory() as temp:
                root=Path(temp);calls=[]
                def malformed(provider,body,key):calls.append(provider);return 200,raw
                result=run(root,malformed);self.assertEqual(result['state'],'stopped_provider_operation');self.assertEqual(calls,['openrouter']);self.assertAlmostEqual(result['totals']['new_budget_charge_usd'],.153414);self.assertEqual(result['totals']['recoverable_native_reported_operations'],0);self.assertEqual(result['totals']['observed_accounted_usd'],0);self.assertFalse(any((root/'run/operations').glob('*/result.json')))
                op=next((root/'run/operations').iterdir());self.assertEqual((op/'response.body').read_bytes(),raw);self.assertEqual(r.ledger_raw_reported(op),0);observed=r.j.loads(next((root/'run').glob('observed-*.json')).read_bytes())['documents'][0];self.assertEqual(observed['runtime_gate'],'verification_failed');self.assertEqual(observed['failure']['kind'],'invalid_response');self.assertNotIn('judgment',observed['arms']['stronger'])
    def test_parsed_postresponse_budget_preserves_full_result(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);calls=[];result=run(root,transport(calls,cost=1.9));self.assertEqual(result['state'],'stopped_budget');self.assertEqual(calls,['openrouter']);self.assertTrue(any((root/'run/operations').glob('*/result.json')));observed=r.j.loads(next((root/'run').glob('observed-*.json')).read_bytes())['documents'][0];self.assertEqual(observed['runtime_gate'],'postresponse_budget_stop');self.assertFalse(observed['arms']['jev']['called']);self.assertEqual(observed['arms']['stronger']['status'],'review')
    def test_exact_boundaries_output_cap_and_preintent_budget(self):
        d=doc()
        for delta in (-1,0,1):
            body=copy.deepcopy(d['plans']['stronger']['body']);body['messages'][0]['content']+='x'*(40000+delta-r.a.estimate_input(body));receipt=r.admission(body,d['source']['source_text_sha256']);self.assertEqual(receipt['estimate'],40000+delta);self.assertEqual(receipt['admitted'],delta<=0)
        body=copy.deepcopy(d['plans']['stronger']['body']);body['max_tokens']=8193;self.assertFalse(r.admission(body,d['source']['source_text_sha256'])['admitted'])
        with tempfile.TemporaryDirectory() as temp:
            calls=[];ledger=r.Ledger(temp,{'synthetic':'budget'},keys={'openrouter':'dummyOR'},transport=lambda *args:calls.append(args))
            with self.assertRaises(r.Pause):ledger.operation('over','stronger',{},lambda raw:{},identity={},reserve=1.5)
            self.assertEqual(calls,[]);self.assertFalse(any((Path(temp)/'operations').glob('*/intent.json')))
    def test_whole_verdict_all_ids_globals_and_exact_evidence_unchanged(self):
        d=doc();good=verdict();self.assertEqual(len(good['assessments']),70);self.assertTrue(r.p.validate_verdict(d['source'],d['assembled'],good)['valid'])
        for kind in ('missing_id','duplicate_id','missing_global','bad_quote','payload','complete_with_missing'):
            bad=copy.deepcopy(good)
            if kind=='missing_id':bad['assessments'].pop()
            elif kind=='duplicate_id':bad['assessments'][1]['item_id']=bad['assessments'][0]['item_id']
            elif kind=='missing_global':bad.pop('completeness')
            elif kind=='bad_quote':bad['assessments'][0]['evidence'][0]['quote']='invented evidence'
            elif kind=='payload':bad['payload_sha256']='0'*64
            else:bad['completeness']['label']='complete';bad['missing_items']=[dict(kind='event',description='Synthetic omission',evidence=bad['completeness']['evidence'])]
            self.assertFalse(r.p.validate_verdict(d['source'],d['assembled'],bad)['valid'],kind)
    def test_wrong_auth_input_hash_and_fabricated_jev_denied(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);freeze,auth=setup(root);value=r.j.loads(auth.read_bytes());value['jev_calls']=1;auth.write_bytes(r.j.encode(value));calls=[]
            with self.assertRaises(r.Stop):r.run(MANIFEST,MANIFEST.parent,freeze,root/'run',live=True,authorization=auth,source_labels_freeze_sha256='a'*64,keys={'openrouter':'dummyOR'},transport=lambda *args:calls.append(args))
            self.assertEqual(calls,[]);self.assertFalse((root/'run').exists())
        d=doc();initial=r.initial(d);value={'schema_version':'round8-stronger-cap-probe.observed.v1','documents':[initial]};initial['arms']['jev']['called']=True
        with self.assertRaises(ValueError):r.validate_observation(value)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);value=r.j.loads(MANIFEST.read_bytes());unit=value['documents'][0]
            for kind in ('text','pdf'):unit[kind+'_path']=os.path.relpath((MANIFEST.parent/unit[kind+'_path']).resolve(),root)
            unit['retained_inputs']['wire_stronger_request']['sha256']='0'*64;manifest=root/'manifest.json';manifest.write_bytes(r.j.encode(value))
            with self.assertRaises(r.Stop):r.load_sources(manifest,root)
    def test_safe_no_call_pause_and_denied_input(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);calls=[];result=run(root,transport(calls),max_new=0);self.assertEqual(result['state'],'paused_at_operation_boundary');self.assertEqual(calls,[])
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);mock=copy.deepcopy(doc());mock['plans']['stronger']['admission'].update(admitted=False,reason='Synthetic oversized body');calls=[]
            with patch.object(r,'load_sources',return_value=[mock]):result=run(root,transport(calls))
            self.assertEqual(calls,[]);self.assertEqual(result['totals']['operations'],0);self.assertEqual(result['state'],'completed')
if __name__=='__main__':unittest.main(verbosity=2)
