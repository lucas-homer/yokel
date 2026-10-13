"""Offline smoke adapter/proposal validation; no real credentials or dispatch."""
import importlib.util,io,json,sys,tempfile,time,unittest,hashlib
from pathlib import Path
from unittest.mock import patch
REPO=Path(__file__).resolve().parents[5];ROOT=REPO/'docs/research/state-rulemaking-benchmark/runner-stability-review/live-smoke'
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def guard(event,args):
 if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.posix_spawn'):raise RuntimeError('offline smoke guard')
sys.addaudithook(guard)
def main():
 before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.rglob('*') if p.is_file()}
 tests=load('smoke_owner',ROOT/'job-alpha/test_smoke.py');log=io.StringIO();result=unittest.TextTestRunner(stream=log).run(unittest.defaultTestLoader.loadTestsFromModule(tests));assert result.wasSuccessful(),log.getvalue()
 prep=load('smoke_prep',ROOT/'job-alpha/prepare_jobs.py');release=load('smoke_release',REPO/'tools/research-credentials-stable/release.py');checks=[]
 def check(name,ok):checks.append({'name':name,'passed':bool(ok)});assert ok,name
 with tempfile.TemporaryDirectory(prefix='yokel-smoke-review-') as temp:
  root=Path(temp).resolve();python=root/'bin/python';python.parent.mkdir();python.write_text('synthetic interpreter');lib=root/'lib';std=lib/'python3.12';std.mkdir(parents=True);review=root/'review.md';review.write_text('synthetic review')
  for job in ('job-alpha','job-beta'):(root/job).mkdir();(root/job/'adapter.py').write_bytes((ROOT/job/'adapter.py').read_bytes())
  with patch.multiple(prep,ROOT=root,PYTHON=python,LIB=lib,STD=std):prep.prepare(scope_id='smoke-test-scope',expires_unix=int(time.time())+3600,review=review)
  core={'python_path':str(python),'adapter_roots':[str(root)],'dependency_roots':[str(root)],'timeout_max_seconds':1800,'base_policy':{'references':{'OPENROUTER_API_KEY':'synthetic-reference','TYPESAFE_API_KEY':'synthetic-reference'}}}
  raws=[]
  for job in ('job-alpha','job-beta'):
   proposal=json.loads((root/job/'UNSIGNED-ZERO-COST-PROPOSAL.json').read_bytes());release.validate(core,proposal);check(job+'-accepted-by-final-release-validator',True);check(job+'-zero-paid-reservation',proposal['budget']['reservation_nanousd']==0);check(job+'-openrouter-subset',proposal['provider_variables']==['OPENROUTER_API_KEY']);raws.append(release.encode(proposal))
  check('two-distinct-signed-input-definitions',raws[0]!=raws[1])
 check('smoke-owner-files-unchanged',before=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.rglob('*') if p.is_file()})
 print(json.dumps({'status':'passed','owner_tests_rerun':result.testsRun,'independent_checks':len(checks),'checks':checks,'provider_calls':0,'real_credentials_read':False,'native_builds':0,'real_smoke_receipts_created':False,'source_hashes':{str(p):h for p,h in before.items()}},indent=2))
if __name__=='__main__':main()
