"""Read-only production review; synthetic provider responses, temporary outputs only."""
import contextlib,copy,hashlib,importlib.util,io,json,sys,tempfile,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def guard(event,args):
 if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.posix_spawn'):raise RuntimeError('review disables networking/processes')
 if event=='open' and isinstance(args[0],(str,bytes)):
  p=str(args[0]).lower()
  if '/.env' in p or '/library/keychains/' in p or '/.aws/' in p or Path(p).name in ('credentials','credentials.json'):raise RuntimeError('review disables credential reads')
sys.addaudithook(guard)
o=load('owner_controls',R/'runtime/offline_checks.py');r=o.r
class Independent(unittest.TestCase):
 def test_old_and_new_all_request_bodies(self):
  inv,v=o.development_inventory();assembled=r.p.assemble(o.SOURCE,inv)
  old=r.normalized.requests(o.SOURCE,assembled);new=r.requests(o.SOURCE,assembled)
  self.assertEqual(set(old),set(new))
  for stage in old:
   expected=copy.deepcopy(old[stage]['body'])
   if stage=='inventory':
    expected['max_tokens']=12288;expected['messages'][0]['content']+=r.PROMPT.read_text()
   self.assertEqual(expected,new[stage]['body'])
  retained=r.j.loads((R.parent/'round8/execution/run/operations/inventory-82b41c219e64bc9c63a0ed61/request.json').read_bytes());retained['max_tokens']=12288;retained['messages'][0]['content']+=r.PROMPT.read_text()
  self.assertEqual(retained,r.requests(o.SOURCE)['inventory']['body'])
 def test_failure_latches_at_each_stage(self):
  for stage in ('inventory','jev','stronger'):
   with self.subTest(stage=stage),tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);calls=[];inv,v=o.development_inventory();transport=o.transport_for(inv,v,calls,fail=stage)
    result=o.run(root,transport);self.assertEqual(result['state'],'stopped_provider_operation');self.assertEqual(calls, ['inventory','jev','stronger'][:['inventory','jev','stronger'].index(stage)+1])
    before=list(calls)
    with self.assertRaises(r.Stop):o.run(root,transport)
    self.assertEqual(calls,before)
 def test_truncated_inventory_retains_no_partial_structure(self):
  with tempfile.TemporaryDirectory() as tmp:
   calls=[]
   def transport(*args):
    calls.append(args);return 200,r.j.encode(dict(model=r.a.MODEL,provider='OpenAI',choices=[dict(finish_reason='length',message=dict(content='{"schema_version":'))],usage=dict(prompt_tokens=10,completion_tokens=12288,cost=.12)))
   root=Path(tmp);result=o.run(root,transport);self.assertEqual(result['state'],'stopped_provider_operation');self.assertEqual(len(calls),1)
   doc=r.j.loads(next((root/'run').glob('observed-*.json')).read_bytes())['documents'][0]
   self.assertIsNone(doc['inventory_sha256']);self.assertIsNone(doc['record_sha256']);self.assertFalse(list((root/'run').glob('operations/*/result.json')))
   with self.assertRaises(r.Stop):o.run(root,transport)
   self.assertEqual(len(calls),1)
 def test_both_size_denials_before_verifiers(self):
  # Force one final admission false at a time; unchanged request builder computes both full bodies first.
  original=r.requests
  try:
   for denied in ('jev','stronger'):
    with self.subTest(arm=denied),tempfile.TemporaryDirectory() as tmp:
     def requests(source,assembled=None):
      plans=original(source,assembled)
      if assembled is not None:plans[denied]['admission'].update(admitted=False,reason='independent one-arm denial')
      return plans
     r.requests=requests;inv,v=o.development_inventory();calls=[];root=Path(tmp);o.run(root,o.transport_for(inv,v,calls));self.assertEqual(calls,['inventory'])
     folder=root/'run/documents'/o.SOURCE['document_id'];self.assertTrue((folder/'jev-request.json').exists());self.assertTrue((folder/'stronger-request.json').exists())
  finally:r.requests=original
 def test_source_mutations_fail_without_call(self):
  manifest=R/'sources/source-inputs.READY.json';value=r.j.loads(manifest.read_bytes())
  for key,replacement in [('scope','slice'),('document_id','doc-aaaaaaaaaaaa'),('text_sha256','a'*64),('pdf_pages',3)]:
   with self.subTest(field=key),tempfile.TemporaryDirectory() as tmp:
    clone=copy.deepcopy(value);clone['documents'][0][key]=replacement
    # Keep original absolute source resolution relative to the temporary manifest.
    import os
    for kind in ('text','pdf'):clone['documents'][0][kind+'_path']=os.path.relpath((manifest.parent/value['documents'][0][kind+'_path']).resolve(),tmp)
    p=Path(tmp)/'manifest.json';p.write_text(json.dumps(clone))
    with self.assertRaises(r.Stop):r.load_sources(p,p.parent)
 def test_prepare_actual_manifest_shape(self):
  m=load('prepare_review',R/'execution/service-account/prepare_manifest.py')
  with tempfile.TemporaryDirectory() as tmp:
   base=Path(tmp);new=base/'round8-contract-probe';old=base/'round8';here=new/'execution/service-account';here.mkdir(parents=True);(new/'runtime').mkdir();(new/'sources').mkdir();(old/'execution').mkdir(parents=True)
   def put(path,v):path.write_text(json.dumps(v))
   (here/'adapter.py').write_text('# synthetic fixture\n');put(new/'runtime/implementation.json',{'code':{}});put(new/'execution/live-authorization.json',{})
   fixture=copy.deepcopy(r.j.loads((R/'sources/source-inputs.READY.json').read_bytes()))
   for kind in ('text','pdf'):
    p=new/'sources'/('fixture.'+kind);p.write_bytes(b'synthetic');fixture['documents'][0][kind+'_path']=p.name
   put(new/'sources/source-inputs.READY.json',fixture)
   (base/'round8-cap-probe/execution').mkdir(parents=True)
   put(base/'round8-cap-probe/execution/freeze-E.json',{'files':[]})
   for root,names in ((new,('A','S')),(old,('B','E'))):
    for n in names:put(root/'execution'/('freeze-'+n+'.json'),{'files':[]})
   exe=base/'python';exe.write_bytes(b'synthetic');lib=base/'lib';lib.mkdir();std=lib/'python3.12';std.mkdir();site=std/'site-packages';site.mkdir()
   m.ROOT=new;m.HERE=here;m.PYTHON=exe;m.LIB=lib;m.STD=std;m.SITE=site
   result=m.prepare();self.assertFalse(result['credentials_read']);job=json.loads((here/'native-job.json').read_bytes())
   self.assertEqual(job['argv'],[str(exe),'-I','-S','-B',str(here/'adapter.py'),'--live-initial']);self.assertEqual(job['timeout_seconds'],1800)
   for kind in ('text','pdf'):self.assertIn(str((new/'sources'/('fixture.'+kind)).resolve()),job['files'])

 def test_both_prior_charges_bound_and_tamper_rejected(self):
  from unittest.mock import patch
  debit=r.verify_prior_debit();self.assertAlmostEqual(sum(x['conservative_debit_usd'] for x in debit['operations']),.261774)
  variants=[]
  x=copy.deepcopy(debit);x['operations']=x['operations'][:1];variants.append(x)
  x=copy.deepcopy(debit);x['operations'][1]=copy.deepcopy(x['operations'][0]);variants.append(x)
  x=copy.deepcopy(debit);x['operations'][1]['conservative_debit_usd']=.0900085;variants.append(x)
  x=copy.deepcopy(debit);x['operations'][0]['reported_cost_usd']=0;variants.append(x)
  x=copy.deepcopy(debit);x['operations'][1]['files'][str(R.parent/'round8-cap-probe/execution/freeze-E.json')]='0'*64;variants.append(x)
  for n,value in enumerate(variants):
   with self.subTest(case=n),tempfile.TemporaryDirectory() as temp:
    root=Path(temp);(root/'prior-debit.json').write_text(json.dumps(value))
    with patch.object(r,'ROOT',root):
     with self.assertRaises(r.Stop):r.verify_prior_debit()
 def test_debit_at_precall_and_postresponse_boundary(self):
  with tempfile.TemporaryDirectory() as temp:
   calls=[];ledger=r.Ledger(temp,{'synthetic':'cumulative'},keys={'openrouter':'test-OR'},transport=lambda *args:calls.append(args))
   self.assertEqual(ledger.totals()['budget_charge_usd'],.261774)
   with self.assertRaises(r.Pause):ledger.operation('inventory','inventory',{},lambda raw:{},identity={},reserve=1.75)
   self.assertFalse(calls);self.assertEqual(ledger.totals()['operations'],0)
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);inv,v=o.development_inventory();calls=[];result=o.run(root,o.transport_for(inv,v,calls,cost=1.8))
   self.assertEqual(result['state'],'stopped_budget');self.assertEqual(calls,['inventory']);self.assertAlmostEqual(result['totals']['budget_charge_usd'],2.061774)
   obs=r.j.loads(next((root/'run').glob('observed-*.json')).read_bytes());self.assertIsNotNone(obs['documents'][0]['inventory_sha256']);self.assertEqual(obs['documents'][0]['runtime_gate'],'postresponse_budget_stop')
   with self.assertRaises(r.Stop):o.run(root,o.transport_for(inv,v,calls))
   self.assertEqual(calls,['inventory'])
 def test_response_failures_no_retry_or_partial_acceptance(self):
  for kind in ('http_error','invalid_response'):
   with self.subTest(kind=kind),tempfile.TemporaryDirectory() as temp:
    root=Path(temp);calls=[]
    def transport(*args):calls.append(args);return (503,b'{"error":"synthetic"}') if kind=='http_error' else (200,b'not-json')
    result=o.run(root,transport);self.assertEqual(result['state'],'stopped_provider_operation');self.assertEqual(len(calls),1)
    obs=r.j.loads(next((root/'run').glob('observed-*.json')).read_bytes())['documents'][0];self.assertEqual(obs['failure']['kind'],kind);self.assertEqual(obs['provider_service_error'],kind=='http_error');self.assertIsNone(obs['inventory_sha256'])
    with self.assertRaises(r.Stop):o.run(root,transport)
    self.assertEqual(len(calls),1)
 def test_stronger_40000_boundary_on_final_request(self):
  from unittest.mock import patch
  inv,v=o.development_inventory();assembled=r.p.assemble(o.SOURCE,inv);original=r.normalized.requests
  for target in (39999,40000,40001):
   def padded(source,record=None):
    plans=original(source,record)
    if record is not None:
     body=plans['stronger']['body'];body['messages'][0]['content']+='x'*(target-r.a.estimate_input(body))
    return plans
   with self.subTest(target=target),patch.object(r.normalized,'requests',padded):
    item=r.requests(o.SOURCE,assembled)['stronger'];self.assertEqual(item['admission']['estimate'],target);self.assertEqual(item['admission']['cap'],40000);self.assertEqual(item['admission']['admitted'],target<=40000);self.assertEqual(item['body']['max_tokens'],4096);self.assertEqual(item['admission']['body_sha256'],r.sha(r.j.encode(item['body'])))
 def test_new_scope_fields_rejected_before_intent(self):
  for name,value in [('stronger_input_guard',35000),('jev_state_longest_guard',32001),('prior_budget_debit_usd',.100166),('prompt_delta_sha256','0'*64),('calls_per_stage',2)]:
   with self.subTest(field=name),tempfile.TemporaryDirectory() as temp:
    root=Path(temp);manifest,freeze,auth=o.setup(root);authorization=r.j.loads(auth.read_bytes());authorization[name]=value;auth.write_text(json.dumps(authorization));calls=[]
    with self.assertRaises(r.Stop):r.run(manifest,manifest.parent,freeze,root/'run',live=True,authorization=auth,source_labels_freeze_sha256='a'*64,keys={'openrouter':'synthetic','jev':'synthetic'},transport=lambda *args:calls.append(args))
    self.assertFalse(calls);self.assertFalse((root/'run').exists())

if __name__=='__main__':
 paths=list((R/'runtime').glob('*.py'))+list((R/'execution/service-account').glob('*.py'))
 before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
 log=io.StringIO();suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(o),unittest.defaultTestLoader.loadTestsFromTestCase(Independent),unittest.defaultTestLoader.loadTestsFromModule(load('owner_adapter_controls',R/'execution/service-account/test_adapter.py'))])
 with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
 after={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
 (R/'review/independent-test-output.txt').write_text(log.getvalue())
 report={'tests':result.testsRun,'passed':result.wasSuccessful(),'failures':len(result.failures),'errors':len(result.errors),'reviewed_code':before,'code_unchanged_during_tests':before==after,'provider_calls':0,'credentials_read':False,'guard':'network, subprocess and credential-path audit hook; synthetic transports only'}
 (R/'review/independent-test-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='reviewed_code'}))
