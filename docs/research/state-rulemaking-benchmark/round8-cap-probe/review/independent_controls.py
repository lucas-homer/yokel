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
   if stage=='inventory':expected['max_tokens']=12288
   self.assertEqual(expected,new[stage]['body'])
  retained=r.j.loads((R.parent/'round8/execution/run/operations/inventory-82b41c219e64bc9c63a0ed61/request.json').read_bytes());retained['max_tokens']=12288
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
   base=Path(tmp);new=base/'round8-cap-probe';old=base/'round8';here=new/'execution/service-account';here.mkdir(parents=True);(new/'runtime').mkdir();(new/'sources').mkdir();(old/'execution').mkdir(parents=True)
   def put(path,v):path.write_text(json.dumps(v))
   (here/'adapter.py').write_text('# synthetic fixture\n');put(new/'runtime/implementation.json',{'code':{}});put(new/'execution/live-authorization.json',{})
   fixture=copy.deepcopy(r.j.loads((R/'sources/source-inputs.READY.json').read_bytes()))
   for kind in ('text','pdf'):
    p=new/'sources'/('fixture.'+kind);p.write_bytes(b'synthetic');fixture['documents'][0][kind+'_path']=p.name
   put(new/'sources/source-inputs.READY.json',fixture)
   for root,names in ((new,('A','S')),(old,('B','E'))):
    for n in names:put(root/'execution'/('freeze-'+n+'.json'),{'files':[]})
   exe=base/'python';exe.write_bytes(b'synthetic');lib=base/'lib';lib.mkdir();std=lib/'python3.12';std.mkdir();site=std/'site-packages';site.mkdir()
   m.ROOT=new;m.HERE=here;m.PYTHON=exe;m.LIB=lib;m.STD=std;m.SITE=site
   result=m.prepare();self.assertFalse(result['credentials_read']);job=json.loads((here/'native-job.json').read_bytes())
   self.assertEqual(job['argv'],[str(exe),'-I','-S','-B',str(here/'adapter.py'),'--live-initial']);self.assertEqual(job['timeout_seconds'],1800)
   for kind in ('text','pdf'):self.assertIn(str((new/'sources'/('fixture.'+kind)).resolve()),job['files'])
if __name__=='__main__':
 paths=list((R/'runtime').glob('*.py'))+list((R/'execution/service-account').glob('*.py'))
 before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
 log=io.StringIO();suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(o),unittest.defaultTestLoader.loadTestsFromTestCase(Independent),unittest.defaultTestLoader.loadTestsFromModule(load('owner_adapter_controls',R/'execution/service-account/test_adapter.py'))])
 with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
 after={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
 (R/'review/independent-test-output.txt').write_text(log.getvalue())
 report={'tests':result.testsRun,'passed':result.wasSuccessful(),'failures':len(result.failures),'errors':len(result.errors),'reviewed_code':before,'code_unchanged_during_tests':before==after,'provider_calls':0,'credentials_read':False,'guard':'network, subprocess and credential-path audit hook; synthetic transports only'}
 (R/'review/independent-test-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='reviewed_code'}))
