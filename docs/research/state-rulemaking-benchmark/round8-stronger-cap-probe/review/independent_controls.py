"""Independent stronger-only review; synthetic native responses, guarded local execution."""
import contextlib,copy,hashlib,importlib.util,io,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
R=Path(__file__).resolve().parents[1]
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def guard(event,args):
 if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.posix_spawn'):raise RuntimeError('independent review forbids network/process')
 if event=='open' and isinstance(args[0],(str,bytes)):
  n=str(args[0]).lower()
  if '/.env' in n or '/library/keychains/' in n or '/.aws/' in n or Path(n).name in ('credentials','credentials.json'):raise RuntimeError('independent review forbids credential access')
sys.addaudithook(guard)
r=load('review_stronger_runtime',R/'runtime/run_pipeline.py');MANIFEST=R/'sources/source-inputs.READY.json'
def doc():return r.load_sources(MANIFEST,MANIFEST.parent)[0]
def setup(root):
 freeze=root/'implementation.json';r.put(freeze,r.code_pins());auth=root/'auth.json';r.put(auth,dict(schema_version='round8-stronger-cap-probe.live-authorization.v1',implementation_sha256=r.sha(freeze.read_bytes()),manifest_sha256=r.sha(MANIFEST.read_bytes()),source_labels_frozen_before_outputs=True,source_labels_freeze_sha256='a'*64,nominal_budget_usd=2,**r.auth_scope()));return freeze,auth
def run(root,transport,max_new=1):
 freeze,auth=setup(root);return r.run(MANIFEST,MANIFEST.parent,freeze,root/'run',live=True,authorization=auth,source_labels_freeze_sha256='a'*64,max_new=max_new,keys={'openrouter':'independent-dummy'},transport=transport)
def observation(root):return r.j.loads(next((root/'run').glob('observed-*.json')).read_bytes())
def verdict():
 d=doc();ev=[dict(quote=d['source']['source_text'],occurrence=None,context=None)];return dict(schema_version='round7.record_verdict.v1',document_id=d['source']['document_id'],payload_sha256=d['common']['payload_sha256'],completeness=dict(label='complete',reason='Synthetic all-pass acceptance control',evidence=ev),source_identity=dict(label='resolved',reason='Synthetic',evidence=ev),assessments=[dict(item_id=item['id'],support='supported',association='matched',requirements='preserved',reason='Synthetic',evidence=ev) for _,item in r.p.all_items(d['assembled']['record'])],missing_items=[],contradictions=[])
def reply(value=None,finish='stop',cost=.02):return r.j.encode(dict(model=r.a.MODEL,provider='OpenAI',choices=[dict(finish_reason=finish,message=dict(content=r.j.encode(verdict() if value is None else value).decode()))],usage=dict(prompt_tokens=100,completion_tokens=8192 if finish=='length' else 100,cost=cost)))
def respond(calls,raw=None,status=200,error=False,root=None):
 def transport(provider,body,key):
  assert provider=='openrouter';calls.append(body)
  if root:
   folder=root/'run/documents/doc-92211b8c7ba0';assert r.j.loads((folder/'stronger-admission.json').read_bytes())['admitted'];assert (folder/'stronger-request.json').read_bytes()==r.j.encode(body)
  if error:raise TimeoutError('synthetic')
  return status,reply() if raw is None else raw
 return transport
class Independent(unittest.TestCase):
 def test_exact_single_field_request_delta(self):
  d=doc();body=d['plans']['stronger']['body'];prior=R.parent/'round8-evidence-table/execution/run/documents/doc-92211b8c7ba0/stronger-request.json';old=r.j.loads(prior.read_bytes());expected=copy.deepcopy(old);expected['max_tokens']=8192;self.assertEqual(body,expected);self.assertEqual(set(d['plans']),{'stronger'});known=r.j.loads((R/'review/independent-expected.json').read_bytes());self.assertEqual(r.sha(r.j.encode(body)),known['expected_body_sha256']);self.assertEqual(d['plans']['stronger']['admission']['estimate'],35747);self.assertAlmostEqual(d['plans']['stronger']['admission']['reservation_usd'],.153414)
 def test_exact_retained_artifacts_schema_and_uncertainty(self):
  d=doc();payload=r.codec.restore(d['restoration']['wire'],d['common']['payload_sha256']);self.assertEqual(payload,d['common']['payload']);self.assertFalse(r.p.schema_errors(payload['record'],r.p.RECORD_SCHEMA));self.assertEqual(payload['source_text'],d['source']['source_text']);self.assertTrue(d['assembled']['validation']['review_reasons']);self.assertFalse(d['assembled']['action_ready']);self.assertEqual(d['restoration']['wire_sha256'],'b0f1b97bafddf763745413c7b79f447fe9dffc181bd2989a9ab60486196fffa0')
 def test_full_success_remains_review_and_jev_uncalled(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);calls=[];transport=respond(calls,root=root);result=run(root,transport);self.assertEqual(result['state'],'completed');self.assertEqual(len(calls),1);obs=observation(root);d=obs['documents'][0];self.assertEqual(obs['schema_version'],'round8-stronger-cap-probe.observed.v1');self.assertEqual(d['runtime_gate'],'stronger_verification_completed');self.assertEqual(d['arms']['stronger']['judgment']['common_dimensions'],{k:'pass' for k in r.normalized.CRITERIA});self.assertEqual(d['arms']['stronger']['status'],'review');self.assertFalse(d['arms']['stronger']['judgment']['complete_record_shadow_accepted']);self.assertFalse(d['arms']['jev']['called']);self.assertNotIn('judgment',d['arms']['jev']);self.assertEqual(result['totals']['inventory_cases'],0);self.assertEqual(result['totals']['jev_cases'],0);run(root,transport);self.assertEqual(len(calls),1)
 def test_invalid_native_cost_json_retains_reservation_and_failure(self):
  for raw in (b'{"usage":{"cost":1,"cost":2}}',b'{"usage":{"cost":NaN}}',b'{"usage":{"cost":Infinity}}',b'{"usage":null}',b'not-json'):
   with self.subTest(raw=raw),tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);calls=[];result=run(root,respond(calls,raw=raw));self.assertEqual(result['state'],'stopped_provider_operation');self.assertAlmostEqual(result['totals']['new_budget_charge_usd'],.153414);self.assertEqual(result['totals']['recoverable_native_reported_operations'],0);d=observation(root)['documents'][0];self.assertEqual(d['failure']['kind'],'invalid_response');self.assertEqual(d['arms']['stronger']['status'],'failed');self.assertNotIn('judgment',d['arms']['stronger'])
 def test_failed_length_cost_recovered_without_judgment_or_refund(self):
  for cost in (.058736,1.9):
   with self.subTest(cost=cost),tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);calls=[];transport=respond(calls,raw=reply(finish='length',cost=cost));result=run(root,transport);self.assertEqual(result['state'],'stopped_provider_operation');self.assertEqual(result['totals']['observed_accounted_usd'],0);self.assertEqual(result['totals']['recoverable_native_reported_usd'],cost);self.assertAlmostEqual(result['totals']['new_budget_charge_usd'],max(.153414,cost));self.assertEqual(result['totals']['recoverable_native_reported_operations'],1);d=observation(root)['documents'][0];self.assertEqual(d['failure']['kind'],'invalid_response');self.assertNotIn('judgment',d['arms']['stronger']);self.assertFalse(list((root/'run').glob('operations/*/result.json')))
    with self.assertRaises(r.Stop):run(root,transport)
    self.assertEqual(len(calls),1)
 def test_http_uncertain_and_invalid_whole_verdict(self):
  for kind in ('http','uncertain','invalid_verdict'):
   with self.subTest(kind=kind),tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);calls=[];transport=respond(calls,raw=b'{}' if kind=='http' else reply({}) if kind=='invalid_verdict' else None,status=503 if kind=='http' else 200,error=kind=='uncertain');result=run(root,transport);d=observation(root)['documents'][0]
    if kind=='invalid_verdict':self.assertEqual(result['state'],'completed');self.assertEqual(d['arms']['stronger']['status'],'review');self.assertFalse(d['arms']['stronger']['source_coverage_complete']);self.assertTrue(d['arms']['stronger']['judgment']['validation_errors'])
    else:
     self.assertEqual(result['state'],'stopped_provider_operation');self.assertEqual(d['failure']['kind'],'http_error' if kind=='http' else 'transport_uncertain');self.assertEqual(d['provider_service_error'],kind=='http')
     with self.assertRaises(r.Stop):run(root,transport)
    self.assertEqual(len(calls),1)
 def test_valid_postresponse_budget_stop_keeps_paid_verdict(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);calls=[];transport=respond(calls,raw=reply(cost=1.9));result=run(root,transport);self.assertEqual(result['state'],'stopped_budget');self.assertAlmostEqual(result['totals']['budget_charge_usd'],2.442976718);d=observation(root)['documents'][0];self.assertEqual(d['runtime_gate'],'postresponse_budget_stop');self.assertIn('judgment',d['arms']['stronger']);self.assertFalse(d['arms']['jev']['called'])
   with self.assertRaises(r.Stop):run(root,transport)
   self.assertEqual(len(calls),1)
 def test_one_stronger_no_other_stages_and_no_budget_reset(self):
  with tempfile.TemporaryDirectory() as tmp:
   calls=[];ledger=r.Ledger(tmp,{},keys={'openrouter':'synthetic'},transport=lambda *args:(calls.append(args) or (200,b'{}')))
   for stage in ('inventory','jev'):
    with self.assertRaises(r.Stop):ledger.operation(stage,stage,{},lambda raw:{},identity={},reserve=.01)
   with self.assertRaises(r.Pause):ledger.operation('over','stronger',{},lambda raw:{},identity={},reserve=1.5)
   self.assertFalse(calls);self.assertAlmostEqual(ledger.totals()['budget_charge_usd'],.542976718);ledger.operation('s','stronger',{},lambda raw:{'observed_cost_usd':0},identity={},reserve=.01)
   with self.assertRaises(r.Pause):ledger.operation('s2','stronger',{},lambda raw:{},identity={},reserve=.01)
   self.assertEqual(len(calls),1)
 def test_final_body_input_boundaries_and_denial(self):
  d=doc();oldpin=r.j.loads((R/'runtime/input-pin.json').read_bytes());old=r.j.loads(Path(oldpin['files']['wire_stronger_request']['path']).read_bytes());base=d['plans']['stronger']['admission']['estimate']
  for target in (39999,40000,40001):
   with self.subTest(target=target),tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);body=copy.deepcopy(old);body['messages'][0]['content']+='x'*(target-base);p=root/'prior-request.json';p.write_bytes(r.j.encode(body));pin=copy.deepcopy(oldpin);pin['files']['wire_stronger_request']={'path':str(p),'sha256':r.sha(p.read_bytes())};(root/'input-pin.json').write_bytes(r.j.encode(pin))
    with patch.object(r,'ROOT',root):plans,_,_=r.requests(d['source'],d['assembled'])
    ad=plans['stronger']['admission'];self.assertEqual(ad['estimate'],target);self.assertEqual(ad['admitted'],target<=40000);self.assertEqual(plans['stronger']['body']['max_tokens'],8192);self.assertEqual(ad['body_sha256'],r.sha(r.j.encode(plans['stronger']['body'])))
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);denied=copy.deepcopy(d);denied['plans']=plans;calls=[]
   with patch.object(r,'load_sources',return_value=[denied]):result=run(root,respond(calls))
   self.assertFalse(calls);self.assertEqual(observation(root)['documents'][0]['runtime_gate'],'request_size_review')
 def test_prior_five_artifacts_and_no_failed_response_refund(self):
  v=r.verify_prior_debit();self.assertEqual(len(v['operations']),5);self.assertAlmostEqual(sum(x['conservative_debit_usd'] for x in v['operations']),.542976718);self.assertAlmostEqual(v['reporting']['recoverable_native_reported_usd'],.307989);self.assertAlmostEqual(v['reporting']['jev_usage_rate_estimated_usd'],.000502026);self.assertAlmostEqual(r.MAX_RESERVATION,.16192);self.assertAlmostEqual(r.MAX_RESERVATION+r.PRIOR_DEBIT,.704896718)
  base=r.j.loads((R/'runtime/prior-debit.json').read_bytes());mutations=[]
  x=copy.deepcopy(base);x['operations'].pop();mutations.append(x)
  x=copy.deepcopy(base);x['operations'][4]['conservative_debit_usd']=.058736;mutations.append(x)
  x=copy.deepcopy(base);x['operations'][4]['parsed_result_present']=True;mutations.append(x)
  x=copy.deepcopy(base);x['operations'][3]['recoverable_native_reported_usd']=.000502026;mutations.append(x)
  for x in mutations:
   with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);(root/'prior-debit.json').write_bytes(r.j.encode(x))
    with patch.object(r,'ROOT',root),self.assertRaises(r.Stop):r.verify_prior_debit()
 def test_auth_scope_tamper_before_any_output(self):
  for field,value in [('stronger_completion',4096),('max_new_operations',2),('jev_calls',1),('inventory_calls',1),('prior_budget_debit_usd',.428936),('original_payload_sha256','0'*64)]:
   with self.subTest(field=field),tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);freeze,auth=setup(root);v=r.j.loads(auth.read_bytes());v[field]=value;auth.write_bytes(r.j.encode(v));calls=[]
    with self.assertRaises(r.Stop):r.run(MANIFEST,MANIFEST.parent,freeze,root/'run',live=True,authorization=auth,source_labels_freeze_sha256='a'*64,keys={},transport=lambda *args:calls.append(args))
    self.assertFalse(calls);self.assertFalse((root/'run').exists())
 def test_stronger_only_observation_rejects_borrowed_or_fake_jev(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);run(root,respond([]));obs=observation(root);self.assertIs(r.validate_observation(obs),None)
   x=copy.deepcopy(obs);x['documents'][0]['arms']['jev']=copy.deepcopy(x['documents'][0]['arms']['stronger'])
   with self.assertRaises(ValueError):r.validate_observation(x)
   x=copy.deepcopy(obs);x['documents'][0]['arms']['stronger'].pop('judgment')
   with self.assertRaises(ValueError):r.validate_observation(x)
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);calls=[];result=run(root,respond(calls),max_new=0);self.assertFalse(calls);self.assertEqual(result['state'],'paused_at_operation_boundary');self.assertEqual(observation(root)['documents'][0]['failure']['kind'],'operator_pause')
if __name__=='__main__':
 paths=[p for p in (R/'runtime').iterdir() if p.is_file()];before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths};owner=load('owner_stronger_controls',R/'runtime/offline_checks.py');suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(Independent),unittest.defaultTestLoader.loadTestsFromModule(owner)]);log=io.StringIO()
 with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
 after={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths};report={'tests':result.testsRun,'independent_tests':12,'passed':result.wasSuccessful(),'failures':len(result.failures),'errors':len(result.errors),'reviewed_code':before,'code_unchanged_during_tests':before==after,'provider_calls':0,'credentials_read':False,'guard':'network/process/credential-path audit hook; synthetic responses and temporary outputs'};(R/'review/independent-test-output.txt').write_text(log.getvalue());(R/'review/independent-test-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='reviewed_code'}))
