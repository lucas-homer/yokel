"""Independent offline lifecycle controls against owner-stopped runtime only."""
import copy, hashlib, importlib.util, io, json, os, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent; RUNTIME=HERE.parent/'runtime'; BENCH=HERE.parent.parent
checks=[]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_bytes())
def guard(event,args):
 if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.posix_spawn'):raise AssertionError('no network/process allowed')
 if event=='open' and isinstance(args[0],(str,bytes)):
  p=Path(args[0]).resolve();mode=args[1];flags=args[2]
  if any(x in p.parts for x in ('.ssh','.aws','Keychains')) or p.name=='.env':raise AssertionError('credential-file guard')
  writing=(isinstance(mode,str) and any(x in mode for x in 'wax+')) or (isinstance(flags,int) and flags & 3 in (1,2))
  if writing and not p.is_relative_to(HERE):raise AssertionError('review-only write guard: '+str(p))
sys.addaudithook(guard);tempfile.tempdir=str(HERE)
def check(name,ok,detail=None):
 checks.append(dict(name=name,passed=bool(ok),detail=detail))
 if not ok:raise AssertionError(name)
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
ready=read(RUNTIME/'READY.json'); initial={str(p):sha(p) for p in RUNTIME.iterdir() if p.is_file()}
check('Owner READY present',bool(ready))
a=load('independent_adapter',RUNTIME/'adapter.py')
planned,request,response,prior=a.preflight()
fixture=read(BENCH/'round9-exact-id-completeness/protocol/wi70-offline-request.fixture.json')
check('Exact frozen request equality',planned['body']==fixture)
check('Exact size guard and integer budget',len(a.encode(fixture))==38432 and planned['estimate']==39456 and planned['guard']==40000 and a.PRIOR_NANO==696390718 and a.RESERVE_NANO==161920000 and a.CEILING_NANO==2000000000)
check('Scope authorization independently matches',read(HERE.parent/'live-authorization.json')==a.authorization_fields())
wire_cases=read(BENCH/'round9-exact-id-completeness/protocol/response-fixtures.json')['cases']
content=next(c['raw_json'] for c in wire_cases if c['expected_structural_valid'])
def native(text=content):return dict(model='openai/gpt-6.1-sol',provider='OpenAI',choices=[dict(finish_reason='stop',message=dict(content=text))],usage=dict(prompt_tokens=100,completion_tokens=100,cost=.01))
key='SYNTHETIC_REVIEW_SENTINEL_5b389e'
def scenario(name,obj=None,raw=None,status=200,fail=False,expected_valid=None,expected_charge=a.RESERVE_NANO,retain=True,expect_result=True,expect_complete=True):
 raw=a.encode(native() if obj is None else obj) if raw is None else raw
 with tempfile.TemporaryDirectory() as tmp:
  run=Path(tmp)/'run';calls=[]
  def transport(body,secret):
   calls.append(1)
   check(name+' durable intent precedes POST',(run/'intent.json').is_file() and read(run/'intent.json')['request_sha256']==sha(run/'request.json'))
   check(name+' exact body and sentinel',body==fixture and secret==key)
   if fail:raise OSError(key)
   return status,raw
  try:result=a.execute_once(run,planned,request,response,key,transport)
  except a.Denied:result=None
  check(name+' one call',len(calls)==1)
  check(name+' raw retention',(run/'response.body').exists()==retain)
  if retain:check(name+' exact raw bytes',(run/'response.body').read_bytes()==raw)
  check(name+' result retained',(run/'result.json').exists()==expect_result)
  check(name+' completion state',(run/'completed.json').exists()==expect_complete)
  receipt=read(run/'result.json') if expect_complete else read(run/'stop.json')
  check(name+' conservative accounting',receipt['new_budget_charge_nanousd']==expected_charge and receipt['budget_charge_nanousd']==a.PRIOR_NANO+expected_charge)
  if expect_result:
   paid=read(run/'result.json')
   check(name+' semantic nonpromotion',paid['semantic_status']=='unverified' and paid['independent_audit_agreement']=='unverified' and paid['production_eligible'] is False and paid['action_ready'] is False)
   if expected_valid is not None:check(name+' structural result',paid['structural_validation']['structural_valid'] is expected_valid)
  try:a.execute_once(run,planned,request,response,key,transport)
  except FileExistsError:pass
  else:raise AssertionError('repeat should reject')
  check(name+' no repeat dispatch',len(calls)==1)
  check(name+' sentinel never retained',all(key.encode() not in p.read_bytes() for p in run.iterdir() if p.is_file()))
scenario('valid uncertain',expected_valid=True)
for case in wire_cases:
 try:json.loads(case['raw_json'],object_pairs_hook=lambda p:dict(p));strict_ok=True
 except ValueError:strict_ok=False
 # Duplicate inner keys pass ordinary json.loads but the independent expectation below uses fixture kind.
 try:a.strict(case['raw_json'])
 except Exception:strict_ok=False
 scenario('wire '+case['id'],obj=native(case['raw_json']),expected_valid=case['expected_structural_valid'] if strict_ok else None,expect_result=strict_ok,expect_complete=strict_ok)
obj=native();obj['usage']['cost']=3.0
scenario('HTTP schema rejection retains charged cost',obj=obj,status=400,expected_charge=3000000000,expect_result=False,expect_complete=False)
scenario('paid successful response overrun',obj=obj,expected_charge=3000000000,expect_result=True,expect_complete=False)
obj=native();obj['usage'].update(prompt_tokens=200000,completion_tokens=123,cost=.001)
scenario('estimate exceeds reported',obj=obj,expected_charge=401230000,expected_valid=True)
obj['usage'].pop('cost')
scenario('missing reported estimate recovered',obj=obj,expected_charge=401230000,expect_result=False,expect_complete=False)
obj['usage']['cost']=-1
scenario('negative reported estimate recovered',obj=obj,expected_charge=401230000,expect_result=False,expect_complete=False)
obj=native();obj['choices'][0]['message']['content']='{'
obj['usage']['cost']=.5
scenario('malformed inner cost retained',obj=obj,expected_charge=500000000,expect_result=False,expect_complete=False)
scenario('transport uncertainty',fail=True,retain=False,expect_result=False,expect_complete=False)
scenario('credential echo',raw=key.encode(),retain=False,expect_result=False,expect_complete=False)
scenario('oversize',raw=b'x'*2000001,retain=False,expect_result=False,expect_complete=False)
for name,raw in [('duplicate cost',b'{"usage":{"cost":9,"cost":1}}'),('nested duplicate',b'{"usage":{"cost":9,"prompt_tokens":2,"prompt_tokens":1}}'),('nonfinite cost',b'{"usage":{"cost":NaN}}'),('overflow cost',b'{"usage":{"cost":1e999}}'),('trailing JSON',b'{"usage":{"cost":9}} {}'),('nonobject native',b'[]')]:
 scenario(name,raw=raw,expect_result=False,expect_complete=False)
for label in ('wrong model','wrong provider','truncation','refusal','tools','choice count','bad usage'):
 obj=native();obj['usage']['cost']=.4
 if label=='wrong model':obj['model']='wrong'
 elif label=='wrong provider':obj['provider']='wrong'
 elif label=='truncation':obj['choices'][0]['finish_reason']='length'
 elif label=='refusal':obj['choices'][0]['message']['refusal']='refused'
 elif label=='tools':obj['choices'][0]['message']['tool_calls']=[{}]
 elif label=='choice count':obj['choices']*=2
 elif label=='bad usage':obj['usage']['prompt_tokens']=True
 scenario(label,obj=obj,expected_charge=400000000,expect_result=False,expect_complete=False)
# Unknown provider metadata is not falsely verified; the fixed request still pins routing.
obj=native();obj.pop('provider');parsed=a.parse_native(a.encode(obj),request,response)
check('Missing provider identity remains unverified',parsed['provider_identity_verified'] is False)
check('One-nanodollar upward rounding',a.cost_nano(.0000000001)==1)
for value in (-1,True,None,float('nan'),float('inf')):
 try:a.cost_nano(value)
 except Exception:check('Invalid cost rejects '+str(value),True)
 else:check('Invalid cost rejects '+str(value),False)
# Tamper only in memory; never rewrite pinned files.
original_read=a.read
for name,path in [('request pin',RUNTIME/'input-pins.json'),('historical baseline',HERE.parent/'prior-baseline.json')]:
 original_digest=a.digest
 def wrong_digest(p,target=path):return '0'*64 if Path(p)==target else original_digest(p)
 if name=='historical baseline':
  with patch.object(a,'digest',wrong_digest):
   try:a.preflight()
   except Exception:check(name+' drift blocks',True)
   else:check(name+' drift blocks',False)
 else:
  def wrong_read(p):
   value=original_read(p)
   if Path(p)==path:value['request_sha256']='0'*64
   return value
  with patch.object(a,'read',wrong_read):
   try:a.preflight()
   except Exception:check(name+' drift blocks',True)
   else:check(name+' drift blocks',False)
for extra in (543,544,545):
 changed=copy.deepcopy(request.BASELINE);changed['messages'][0]['content']+='x'*extra
 with patch.object(request,'BASELINE',changed):
  try:built=request.wi();ok=True
  except Exception:ok=False
  check('Guard boundary '+str(39456+extra),ok==(extra<=544))
# A denied release never reads credentials or reaches the POST transport.
class ForbiddenEnv(dict):
 def get(self,*args):raise AssertionError('credential lookup before admission')
with patch.object(a,'verify_live_bindings',side_effect=a.Denied()),patch.object(a.os,'environ',ForbiddenEnv()),patch.object(a,'post_once',side_effect=AssertionError('network')):
 try:a.live_initial()
 except a.Denied:check('Rejected admission before credential lookup or POST',True)
# Exercise live admission using synthetic late-binding JSON in memory; no production release files written.
deps={'schema_version':'round9-live-exact-id.dependencies.v1','files':read(RUNTIME/'dependency-pins.json')['files'].copy()}
for p in (a.PYTHON.resolve(),RUNTIME/'adapter.py',RUNTIME/'input-pins.json',HERE.parent/'scope.json',HERE.parent/'live-authorization.json',HERE.parent/'prior-baseline.json'):
 deps['files'][str(p)]=sha(p)
binding=dict(schema_version='round9-live-exact-id.binding.v1',dependencies_sha256=a.sha(a.encode(deps)),authorization_sha256=sha(HERE.parent/'live-authorization.json'),scope_sha256=sha(HERE.parent/'scope.json'),input_pins_sha256=sha(RUNTIME/'input-pins.json'))
real_digest=a.digest;real_read=a.read
for mutation in ('none','missing adapter','drift dependency','drift binding','scope authorization','guard authorization','budget authorization'):
 d=copy.deepcopy(deps);b=copy.deepcopy(binding);auth=real_read(HERE.parent/'live-authorization.json')
 if mutation=='missing adapter':d['files'].pop(str(RUNTIME/'adapter.py'))
 if mutation=='drift dependency':d['files'][str(RUNTIME/'adapter.py')]='0'*64
 b['dependencies_sha256']=a.sha(a.encode(d))
 if mutation=='drift binding':b['dependencies_sha256']='0'*64
 if mutation=='scope authorization':auth['scope_sha256']='0'*64
 if mutation=='guard authorization':auth['input_guard']=40001
 if mutation=='budget authorization':auth['ceiling_nanousd']=2000000001
 def fake_read(path):
  path=Path(path)
  if path==RUNTIME/'dependencies.json':return copy.deepcopy(d)
  if path==RUNTIME/'binding.json':return copy.deepcopy(b)
  if path==HERE.parent/'live-authorization.json':return copy.deepcopy(auth)
  return real_read(path)
 def fake_digest(path):
  if Path(path)==RUNTIME/'dependencies.json':return a.sha(a.encode(d))
  return real_digest(path)
 with patch.object(a,'read',fake_read),patch.object(a,'digest',fake_digest):
  try:a.verify_live_bindings();admitted=True
  except a.Denied:admitted=False
  check('Synthetic late-binding admission '+mutation,admitted==(mutation=='none'))
# Independently verify closure against original bytes, including bundled Python executable.
bad=[name for name,want in deps['files'].items() if sha(Path(name))!=want]
check('Dependency closure matches original bytes',not bad,{'files':len(deps['files']),'mismatches':bad})

# Independent rerun of owner unit suite, with all temporary files under review.
owner=load('owner_tests_independent',RUNTIME/'test_adapter.py');stream=io.StringIO()
result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(owner))
(HERE/'owner-tests-independent.txt').write_text(stream.getvalue())
check('Owner independent rerun passes',result.wasSuccessful(),{'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors)})
changed=[p for p,want in initial.items() if sha(Path(p))!=want]
check('Stopped runtime unchanged by review',not changed,changed)
report=dict(state='passed',checks=checks,checks_passed=len(checks),provider_calls=0,credentials_read=False,owner_tests=result.testsRun,runtime_ready_sha256=sha(RUNTIME/'READY.json'),runtime_files=initial,limitations=['Synthetic transports only; provider schema compatibility unverified.','Signed late-binding proposal remains primary-owned and must match review pins.','No invoice verification or model-semantic accuracy claim.'])
(HERE/'independent-checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('checks','runtime_files','limitations')}))
