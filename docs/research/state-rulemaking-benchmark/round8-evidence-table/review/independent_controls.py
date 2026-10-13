"""Independent evidence-table review: injected transports, no network or credentials."""
import contextlib,copy,hashlib,importlib.util,io,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
R=Path(__file__).resolve().parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def guard(event,args):
 if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.posix_spawn'):raise RuntimeError('review disables network/processes')
 if event=='open' and isinstance(args[0],(str,bytes)):
  name=str(args[0]).lower()
  if '/.env' in name or '/library/keychains/' in name or '/.aws/' in name or Path(name).name in ('credentials','credentials.json'):raise RuntimeError('review disables credentials')
sys.addaudithook(guard)
r=load('independent_table_runtime',R/'runtime/run_pipeline.py');c=r.codec
manifest=R/'sources/source-inputs.READY.json'
def docs():return r.load_sources(manifest,manifest.parent)
def setup(root):
 freeze=root/'implementation.json';r.put(freeze,r.code_pins());auth=root/'auth.json';r.put(auth,dict(schema_version='round8-evidence-table.live-authorization.v1',implementation_sha256=r.sha(freeze.read_bytes()),manifest_sha256=r.sha(manifest.read_bytes()),source_labels_frozen_before_outputs=True,source_labels_freeze_sha256='a'*64,nominal_budget_usd=2,**r.auth_scope()));return freeze,auth
def run(root,transport,max_new=2):
 freeze,auth=setup(root);return r.run(manifest,manifest.parent,freeze,root/'run',live=True,authorization=auth,source_labels_freeze_sha256='a'*64,max_new=max_new,keys={'openrouter':'review-dummy-or','jev':'review-dummy-j'},transport=transport)
def observed(root):return r.j.loads(next((root/'run').glob('observed-*.json')).read_bytes())['documents'][0]
def transport_for(calls,fail=None,kind=None,overrun=None,root=None):
 def transport(provider,body,key):
  stage='jev' if provider=='jev' else 'stronger';calls.append(stage)
  if root is not None:
   folder=root/'run/documents/doc-92211b8c7ba0'
   for arm in ('jev','stronger'):
    assert (folder/(arm+'-request.json')).exists() and r.j.loads((folder/(arm+'-admission.json')).read_bytes())['admitted']
  if stage==fail:
   if kind=='transport_uncertain':raise TimeoutError('synthetic')
   if kind=='http_error':return 503,b'{"synthetic":"error"}'
   if kind=='invalid_response':return 200,b'not-json'
  if stage=='jev':return 200,r.j.encode(dict(model=r.a.j.JEV_MODEL,answers={n:dict(type='choice',choice='pass',confidence=.8,probabilities={v:.8 if v=='pass' else .1 for v in q['criteria']}) for n,q in body['questions'].items()},usage=dict(input_tokens=50000000 if overrun=='jev' else 100,output_tokens=5)))
  return 200,r.j.encode(dict(model=r.a.MODEL,provider='OpenAI',choices=[dict(finish_reason='stop',message=dict(content='{}'))],usage=dict(prompt_tokens=100,completion_tokens=100,cost=2.01 if overrun=='stronger' else .0012)))
 return transport
class Independent(unittest.TestCase):
 def test_exact_expansion_and_request_mechanics(self):
  d=docs()[0];plans,receipt,originals=r.requests(d['source'],d['assembled']);wire=receipt['wire'];payload=d['common']['payload'];self.assertEqual(c.restore(wire,d['common']['payload_sha256']),payload)
  restored={stage:copy.deepcopy(plan['body']) for stage,plan in plans.items()};restored['jev']['state']=c.restore(restored['jev']['state'],d['common']['payload_sha256']);suffix=r.INSTRUCTIONS.read_text()
  for q in restored['jev']['questions'].values():self.assertTrue(q['instructions'].endswith(suffix));q['instructions']=q['instructions'][:-len(suffix)]
  wrapper=r.j.loads(restored['stronger']['messages'][1]['content']);wrapper['payload']=c.restore(wrapper['payload'],d['common']['payload_sha256']);restored['stronger']['messages'][1]['content']=r.j.encode(wrapper).decode();restored['stronger']['messages'][0]['content']=restored['stronger']['messages'][0]['content'][:-len(suffix)]
  self.assertEqual(restored,originals);self.assertEqual(set(plans),{'jev','stronger'});self.assertTrue(d['assembled']['validation']['valid']);self.assertTrue(d['assembled']['validation']['review_reasons']);self.assertFalse(d['assembled']['action_ready']);self.assertTrue(r.p.schema_errors(wire['payload']['record'],r.p.RECORD_SCHEMA));self.assertFalse(r.p.schema_errors(c.restore(wire,d['common']['payload_sha256'])['record'],r.p.RECORD_SCHEMA))
 def test_valid_reference_reassociation_drop_and_order_rejected(self):
  payload=docs()[0]['common']['payload'];wire=c.encode(payload);expected=c.digest(payload)
  variants=[]
  x=copy.deepcopy(wire);x['payload']['record']['events'][0]['evidence'][0]=(x['payload']['record']['events'][0]['evidence'][0]+1)%len(x['evidence_table']);variants.append(x)
  x=copy.deepcopy(wire);x['payload']['record']['routes'].pop();variants.append(x)
  x=copy.deepcopy(wire);x['payload']['record']['routes'].reverse();variants.append(x)
  x=copy.deepcopy(wire);x['payload']['record']['uncertainties']=[];variants.append(x)
  x=copy.deepcopy(wire);x['payload']['record']['coverage'].pop('rationale');variants.append(x)
  for n,x in enumerate(variants):
   with self.subTest(case=n),self.assertRaises(c.InvalidWire):c.restore(x,expected)
 def test_unicode_distinct_spans_repeated_evidence_and_array_order(self):
  text='🦊é\n🦊é\n';ev=[dict(start=0,end=2,quote='🦊é'),dict(start=3,end=5,quote='🦊é')];payload={'source_text':text,'source_text_sha256':hashlib.sha256(text.encode()).hexdigest(),'record':{'claims':[{'id':'a','evidence':[ev[0],ev[1],ev[0]]},{'id':'b','evidence':[ev[1]]}]}}
  wire=c.encode(payload);self.assertEqual(len(wire['evidence_table']),2);self.assertEqual(wire['payload']['record']['claims'][0]['evidence'],[0,1,0]);self.assertEqual(c.restore(wire,c.digest(payload)),payload)
  wire['payload']['record']['claims'][0]['evidence']=[1,0,0]
  with self.assertRaises(c.InvalidWire):c.restore(wire,c.digest(payload))
 def test_wire_hash_version_quote_and_noncanonical_table_rejected(self):
  payload=docs()[0]['common']['payload'];wire=c.encode(payload);expected=c.digest(payload)
  variants=[]
  x=copy.deepcopy(wire);x['schema_version']='round7.verification_payload.v1';variants.append(x)
  x=copy.deepcopy(wire);x['evidence_table'][0]['quote']+='x';variants.append(x)
  x=copy.deepcopy(wire);x['evidence_table'].append(copy.deepcopy(x['evidence_table'][0]));variants.append(x)
  x=copy.deepcopy(wire);x['payload']['record']['events'][0]['evidence'][0]=True;variants.append(x)
  for x in variants:
   with self.assertRaises(c.InvalidWire):c.restore(x,expected)
  with self.assertRaises(c.InvalidWire):c.restore(wire,'0'*64)
  # JSON object key order is immaterial under the original canonicalization.
  x=dict(reversed(list(wire.items())));self.assertEqual(c.restore(x,expected),payload)
 def test_stronger_exact_final_body_boundaries(self):
  d=docs()[0];base=r.requests(d['source'],d['assembled'])[0]['stronger']['admission']['estimate'];instructions=r.INSTRUCTIONS.read_text()
  for target in (39999,40000,40001):
   with self.subTest(target=target),tempfile.TemporaryDirectory() as tmp:
    path=Path(tmp)/'instructions';path.write_text(instructions+'x'*(target-base))
    with patch.object(r,'INSTRUCTIONS',path):item=r.requests(d['source'],d['assembled'])[0]['stronger']
    self.assertEqual(item['admission']['estimate'],target);self.assertEqual(item['admission']['admitted'],target<=40000);self.assertEqual(item['admission']['body_sha256'],r.sha(r.j.encode(item['body'])));self.assertEqual(item['body']['max_tokens'],4096)
 def test_jev_exact_state_and_total_boundaries(self):
  original=docs()[0]['plans']['jev']['body'];baseline=r.a.admission(original,'jev')['state_longest_estimate']
  for target in (31999,32000,32001):
   body=copy.deepcopy(original);longest=max(body['questions'],key=lambda k:len(r.j.encode(body['questions'][k])));body['questions'][longest]['instructions']+='x'*(target-baseline);ad=r.a.admission(body,'jev');self.assertEqual(ad['state_longest_estimate'],target);self.assertEqual(ad['admitted'],target<=32000)
  for target in (63999,64000,64001):
   body={'model':r.a.j.JEV_MODEL,'state':{},'questions':{str(i):{'type':'choice','instructions':'x'*12000,'criteria':{'yes':'y','no':'n'}} for i in range(5)}};body['questions']['0']['instructions']+='x'*(target-r.a.estimate_input(body));ad=r.a.admission(body,'jev');self.assertEqual(ad['estimate'],target);self.assertLess(ad['state_longest_estimate'],32000);self.assertEqual(ad['admitted'],target<=64000)
 def test_full_pair_staged_before_dispatch_and_uncertainty_blocks_accept(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);calls=[];result=run(root,transport_for(calls,root=root));self.assertEqual(calls,['jev','stronger']);self.assertEqual(result['totals']['inventory_cases'],0);doc=observed(root);self.assertEqual(doc['runtime_gate'],'paired_verification_completed');self.assertEqual(doc['arms']['jev']['judgment']['common_dimensions'],{x:'pass' for x in r.normalized.CRITERIA});self.assertEqual(doc['arms']['jev']['status'],'review');self.assertFalse(doc['arms']['jev']['judgment']['complete_record_shadow_accepted']);self.assertEqual(doc['review_reasons'],docs()[0]['assembled']['validation']['review_reasons'])
 def test_asymmetric_denial_prevents_both_calls(self):
  original=r.requests
  for denied in ('jev','stronger'):
   def mutated(*args):
    plans,receipt,originals=original(*args);plans[denied]['admission'].update(admitted=False,reason='independent admission denial');return plans,receipt,originals
   with self.subTest(arm=denied),tempfile.TemporaryDirectory() as tmp,patch.object(r,'requests',side_effect=mutated):
    root=Path(tmp);calls=[];run(root,transport_for(calls));self.assertFalse(calls);doc=observed(root);self.assertEqual(doc['runtime_gate'],'request_size_review');self.assertTrue(all(not a['called'] for a in doc['arms'].values()));self.assertEqual(len(list((root/'run/documents/doc-92211b8c7ba0').glob('*-request.json'))),2)
 def test_failure_states_latch_without_retry(self):
  for stage in ('jev','stronger'):
   for kind in ('http_error','transport_uncertain','invalid_response'):
    with self.subTest(stage=stage,kind=kind),tempfile.TemporaryDirectory() as tmp:
     root=Path(tmp);calls=[];transport=transport_for(calls,fail=stage,kind=kind);result=run(root,transport);self.assertEqual(result['state'],'stopped_provider_operation');doc=observed(root);self.assertEqual(doc['failure']['kind'],kind);self.assertEqual(doc['failure']['stage'],stage);self.assertEqual(doc['provider_service_error'],kind=='http_error');self.assertEqual(doc['arms'][stage]['status'],'failed');self.assertNotIn('judgment',doc['arms'][stage]);before=list(calls)
     with self.assertRaises(r.Stop):run(root,transport)
     self.assertEqual(calls,before)
 def test_postresponse_overrun_preserves_paid_judgment_and_stops(self):
  for stage in ('jev','stronger'):
   with self.subTest(stage=stage),tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);calls=[];transport=transport_for(calls,overrun=stage);result=run(root,transport);self.assertEqual(result['state'],'stopped_budget');self.assertEqual(calls,['jev'] if stage=='jev' else ['jev','stronger']);doc=observed(root);self.assertEqual(doc['runtime_gate'],'postresponse_budget_stop');self.assertIn('judgment',doc['arms'][stage]);self.assertGreater(result['totals']['budget_charge_usd'],2)
    with self.assertRaises(r.Stop):run(root,transport)
    self.assertEqual(len(calls),1 if stage=='jev' else 2)
 def test_forbidden_inventory_and_per_stage_caps(self):
  with tempfile.TemporaryDirectory() as tmp:
   calls=[];ledger=r.Ledger(tmp,{},keys={'jev':'dummy-j','openrouter':'dummy-o'},transport=lambda *args:(calls.append(args) or (200,b'{}')))
   with self.assertRaises(r.Stop):ledger.operation('x','inventory',{},lambda raw:{},identity={},reserve=.01)
   self.assertFalse(calls)
   for stage in ('jev','stronger'):
    ledger.operation(stage,stage,{},lambda raw:{'observed_cost_usd':0},identity={},reserve=.01)
    with self.assertRaises(r.Pause):ledger.operation(stage+'2',stage,{},lambda raw:{},identity={},reserve=.01)
   self.assertEqual(len(calls),2);self.assertEqual(ledger.totals()['inventory_cases'],0)
 def test_three_prior_debits_tamper_and_fixed_maximum(self):
  prior=r.verify_prior_debit();self.assertEqual(len(prior['operations']),3);self.assertAlmostEqual(sum(x['conservative_debit_usd'] for x in prior['operations']),.428936);self.assertAlmostEqual(r.MAX_RESERVATION,.123648);self.assertAlmostEqual(r.MAX_RESERVATION+r.PRIOR_DEBIT,.552584)
  variants=[]
  x=copy.deepcopy(prior);x['operations'].pop();variants.append(x)
  x=copy.deepcopy(prior);x['operations'][2]=copy.deepcopy(x['operations'][1]);variants.append(x)
  x=copy.deepcopy(prior);x['operations'][2]['conservative_debit_usd']=.090426;variants.append(x)
  x=copy.deepcopy(prior);x['operations'][2]['files'].pop(next(k for k in x['operations'][2]['files'] if k.endswith('result.json')));variants.append(x)
  for x in variants:
   with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);(root/'prior-debit.json').write_text(json.dumps(x))
    with patch.object(r,'ROOT',root),self.assertRaises(r.Stop):r.verify_prior_debit()
 def test_authorization_scope_changes_stop_before_output(self):
  for field,value in [('inventory_calls',1),('max_new_operations',3),('original_payload_sha256','0'*64),('wire_version','wrong'),('prior_budget_debit_usd',.261774),('jev_state_longest_guard',32001)]:
   with self.subTest(field=field),tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);freeze,auth=setup(root);v=r.j.loads(auth.read_bytes());v[field]=value;auth.write_bytes(r.j.encode(v));calls=[]
    with self.assertRaises(r.Stop):r.run(manifest,manifest.parent,freeze,root/'run',live=True,authorization=auth,source_labels_freeze_sha256='a'*64,keys={},transport=lambda *args:calls.append(args))
    self.assertFalse(calls);self.assertFalse((root/'run').exists())
 def test_precall_budget_and_max_new_zero_preserve_original(self):
  with tempfile.TemporaryDirectory() as tmp:
   calls=[];ledger=r.Ledger(tmp,{},keys={'jev':'dummy'},transport=lambda *args:calls.append(args))
   with self.assertRaises(r.Pause):ledger.operation('j','jev',{},lambda raw:{},identity={},reserve=1.6)
   self.assertFalse(calls);self.assertEqual(ledger.totals()['budget_charge_usd'],.428936)
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);calls=[];result=run(root,transport_for(calls),max_new=0);self.assertFalse(calls);self.assertEqual(result['state'],'paused_at_operation_boundary');doc=observed(root);self.assertEqual(doc['record_sha256'],r.j.loads((R/'runtime/input-pin.json').read_bytes())['record_sha256']);self.assertEqual(doc['failure']['kind'],'operator_pause')
if __name__=='__main__':
 paths=list((R/'runtime').glob('*'))+list((R/'execution/service-account').glob('*.py'));paths=[p for p in paths if p.is_file()];before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
 owner=load('owner_table_checks',R/'runtime/offline_checks.py');adapter=load('owner_table_adapter_checks',R/'execution/service-account/test_adapter.py');suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(Independent),unittest.defaultTestLoader.loadTestsFromModule(owner),unittest.defaultTestLoader.loadTestsFromModule(adapter)]);log=io.StringIO()
 with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
 after={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths};report={'tests':result.testsRun,'passed':result.wasSuccessful(),'failures':len(result.failures),'errors':len(result.errors),'reviewed_code':before,'code_unchanged_during_tests':before==after,'provider_calls':0,'credentials_read':False,'guard':'network/process/credential-path audit hook; synthetic transports and temporary outputs only'}
 (R/'review/independent-test-output.txt').write_text(log.getvalue());(R/'review/independent-test-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='reviewed_code'}))
