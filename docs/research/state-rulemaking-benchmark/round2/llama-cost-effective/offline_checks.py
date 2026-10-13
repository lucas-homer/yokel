"""Meaningful offline state-machine checks; fake API only, no credential access."""
import contextlib,copy,hashlib,importlib.util,io,json,tempfile,time,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]/'artifacts'
spec=importlib.util.spec_from_file_location('runner',HERE/'run_cost_effective.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
PLAN=m.local_plan(ROOT)
class Fake:
 key='synthetic-test-key';last_capture=None
 def __init__(self,failed=(),markdown='α\nsecond\n',missing_pages=False):self.posts=[];self.active=set();self.peak=0;self.failed=set(failed);self.md=markdown;self.missing=missing_pages;self.requests=[];self.proofs=[];self.list_items=[]
 def verify_file(self,fid,h):self.proofs.append((fid,h));return {'file_id':fid,'download_sha256':h,'checked_at_utc':m.now(),'project_id':'offline-project'}
 def request(self,method,path,data=None,query=None,content_type=None):
  self.requests.append((method,path))
  if method=='POST' and path=='/api/v2/parse':
   q=json.loads(data);jid='fake-'+str(len(self.posts)+1);self.posts.append((jid,q));self.active.add(jid);self.peak=max(self.peak,len(self.active));return {'id':jid,'status':'PENDING'}
  if method=='GET' and path=='/api/v2/parse':return {'items':self.list_items}
  if method=='GET' and path.startswith('/api/v2/parse/'):
   jid=path.rsplit('/',1)[-1];q=dict(self.posts)[jid];self.active.discard(jid);u=next(j for j in PLAN['jobs'] if j['input_sha256']==q['user_metadata']['input_sha256']);pages=[] if self.missing else [{'page_number':i+1,'success':True} for i in range(u['pages'])];return {'job':{'id':jid,'status':'FAILED' if jid in self.failed else 'COMPLETED','file_id':q['file_id'],'tier':q['tier'],'usage':{'credits':u['pages']*3}},'markdown_full':self.md,'markdown':{'pages':pages},'job_metadata':{}}
  raise AssertionError('Unexpected offline API operation')
class Checks(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory(dir=HERE/'offline-scratch');self.out=Path(self.tmp.name);self.api=Fake();self.r=m.Runner(ROOT,self.out,PLAN,self.api,'offline-project');self.old_sleep=m.time.sleep;m.time.sleep=lambda _:None
 def tearDown(self):m.time.sleep=self.old_sleep;self.tmp.cleanup()
 def runr(self,n=20):
  with contextlib.redirect_stdout(io.StringIO()):self.r.run(max_jobs=n,max_run_seconds=60)
 def test_plan_exact20_34pages_102(self):self.assertEqual((len(PLAN['jobs']),sum(j['pages'] for j in PLAN['jobs']),PLAN['nominal_credits']),(20,34,102));self.assertEqual(len({j['candidate_file_id'] for j in PLAN['jobs']}),20)
 def test_same_parse_options_except_tier_and_tags(self):
  prior=json.loads((ROOT/'execution-api-1/state.json').read_text())['plan']['config_template'];q=copy.deepcopy(PLAN['config_template']);q['tier']=prior['tier'];q['user_metadata']=prior['user_metadata'];self.assertEqual(q,prior)
 def test_full20_no_more_than_two_and_exact_bytes(self):
  self.runr();self.assertEqual(len(self.api.posts),20);self.assertLessEqual(self.api.peak,2);self.assertEqual(len(self.api.proofs),20);self.assertEqual(len(self.r.state['completion_order']),20)
  for j in self.r.state['jobs']:self.assertEqual((self.out/f"runs/{j['fixture_id']}/cost_effective/output.md").read_bytes(),self.api.md.encode())
 def test_pilot_one_job_preserves_fullplan(self):self.runr(1);self.assertEqual(len(self.api.posts),1);self.assertEqual(len(self.r.state['jobs']),20);self.assertEqual(sum(j['phase']=='pending' for j in self.r.state['jobs']),19)
 def test_restart_does_not_repeat_completed(self):
  self.runr(1);self.r=m.Runner(ROOT,self.out,PLAN,self.api,'offline-project');self.runr(1);self.assertEqual(len(self.api.posts),2);self.assertEqual(len({x[0] for x in self.api.posts}),2)
 def test_restart_accepted_polls_without_resubmission(self):
  self.r.deadline=time.monotonic()+60;self.r.submit(self.r.state['jobs'][0]);self.r=m.Runner(ROOT,self.out,PLAN,self.api,'offline-project');self.runr(0);self.assertEqual(len(self.api.posts),1);self.assertEqual(self.r.state['jobs'][0]['phase'],'completed')
 def test_candidate_verification_failure_no_upload_or_submit(self):
  def mismatch(*args):raise ValueError('Remote reusable file bytes differ from freeze')
  self.api.verify_file=mismatch;self.r.deadline=time.monotonic()+60
  with self.assertRaises(ValueError):self.r.submit(self.r.state['jobs'][0])
  self.assertFalse(self.api.requests);self.assertEqual(self.r.state['jobs'][0]['phase'],'pending')
 def test_pair_barrier_no_slot_refill(self):
  self.runr(4);ops=[op for op in self.api.requests if '/parse' in op[1]];self.assertEqual([o[0] for o in ops],['POST','POST','GET','GET','POST','POST','GET','GET'])
 def test_three_failures_retains_fourth_no_fifth(self):
  self.api.failed={'fake-1','fake-2','fake-3','fake-4'};self.runr();self.assertEqual(len(self.api.posts),4);self.assertTrue(self.r.state['stopped']);self.assertEqual(sum(j['phase']=='failed' for j in self.r.state['jobs']),4);self.runr();self.assertEqual(len(self.api.posts),4)
 def test_missing_page_evidence_operational_failure(self):self.api.missing=True;self.runr(1);self.assertEqual(self.r.state['jobs'][0]['phase'],'failed')
 def test_uncertain_zero_match_no_submit(self):
  j=self.r.state['jobs'][0];j.update(phase='submit_uncertain',submit_started_at_utc=m.now());self.r.deadline=time.monotonic()+10
  with self.assertRaises(ValueError):self.r.reconcile(j)
  self.assertFalse(self.api.posts);self.assertEqual(j['phase'],'submit_uncertain')
 def test_uncertain_unique_resumes_id_without_post(self):
  j=self.r.state['jobs'][0];j.update(phase='submit_uncertain',submit_started_at_utc=m.now());self.r.deadline=time.monotonic()+10;self.api.list_items=[{'id':'existing','tier':j['tier'],'user_metadata':{'benchmark_run':m.RUN_TAG,'intent_token':j['intent_token'],'input_sha256':j['input_sha256']}}];self.r.reconcile(j);self.assertEqual(j['job_id'],'existing');self.assertFalse(self.api.posts)
 def test_multiple_matches_stays_uncertain(self):
  j=self.r.state['jobs'][0];j.update(phase='submit_uncertain',submit_started_at_utc=m.now());self.r.deadline=time.monotonic()+10;t={'id':'one','tier':j['tier'],'user_metadata':{'benchmark_run':m.RUN_TAG,'intent_token':j['intent_token'],'input_sha256':j['input_sha256']}};self.api.list_items=[t,dict(t,id='two')]
  with self.assertRaises(ValueError):self.r.reconcile(j)
  self.assertFalse(self.api.posts)
 def test_lost_post_response_persists_intent_no_retry(self):
  self.r.deadline=time.monotonic()+10;original=self.api.request
  def lose(method,path,*args,**kwargs):
   if method=='POST':raise m.TransportFailure()
   return original(method,path,*args,**kwargs)
  self.api.request=lose;j=self.r.state['jobs'][0]
  with self.assertRaises(ValueError):self.r.submit(j)
  durable=json.loads((self.out/'state.json').read_text())['jobs'][0];self.assertEqual(durable['phase'],'submit_uncertain');self.assertTrue(durable['intent_token']);self.assertTrue(durable['request']);self.assertIsNone(durable.get('job_id'))
 def test_project_or_plan_drift_refuses_resume(self):
  with self.assertRaises(ValueError):m.Runner(ROOT,self.out,PLAN,self.api,'other-project')
  changed=copy.deepcopy(PLAN);changed['jobs'][0]['input_sha256']='bad'
  with self.assertRaises(ValueError):m.Runner(ROOT,self.out,changed,self.api,'offline-project')
 def test_uncertain_upload_no_replacement(self):
  j=self.r.state['jobs'][0];self.r.state['files'][j['fixture_id']]={'phase':'upload_inflight'}
  with self.assertRaises(ValueError):self.r.file_for(j)
  self.assertFalse(self.api.requests)
 def test_signed_secret_redaction_and_tier_guard(self):
  s=m.safe_value({'download_url':'https://x.invalid?a=1','note':'synthetic-test-key https://x.invalid/a?X-Amz-Signature=abc'},self.api.key);self.assertNotIn(self.api.key,json.dumps(s));self.assertNotIn('Signature',json.dumps(s))
  with self.assertRaises(ValueError):m.config('file','agentic','token','hash')
 def test_partial_http_prefix_resume(self):
  (self.out/'http').mkdir();(self.out/'http/00007.response.json').write_text('{}');api=m.API('synthetic','offline',self.out);self.assertEqual(api.sequence,7)
if __name__=='__main__':
 (HERE/'offline-scratch').mkdir(exist_ok=True)
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(Checks);result=unittest.TextTestRunner(verbosity=1).run(suite)
 report={'passed':result.wasSuccessful(),'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'authenticated_calls':0,'credential_access':False,'fixture_count':20,'input_pages':34,'nominal_credits':102,'runner_sha256':hashlib.sha256((HERE/'run_cost_effective.py').read_bytes()).hexdigest(),'test_names':[x for x in dir(Checks) if x.startswith('test_')]};(HERE/'offline-checks.json').write_text(json.dumps(report,indent=2)+'\n');(HERE/'plan.json').write_text(json.dumps(PLAN,indent=2)+'\n')
 raise SystemExit(0 if result.wasSuccessful() else 1)
