"""Independent stopped-runtime controls. Invoke with exact READY SHA and output label."""
import copy,hashlib,importlib.util,io,json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent;ROUND=HERE.parents[1];RUNTIME=ROUND/'runtime';BENCH=ROUND.parent
sys.path.insert(0,str(HERE))
import review_support as r
if len(sys.argv)!=3:raise SystemExit('requires exact stopped READY SHA and new report label')
expected,label=sys.argv[1:]
if not label.replace('-','').isalnum():raise SystemExit('invalid report label')
ready=RUNTIME/'READY.json'
if not ready.exists() or r.sha(ready.read_bytes())!=expected:raise SystemExit('stopped runtime READY mismatch; no runtime imported')
manifest=r.strict(ready.read_bytes())
for name,want in manifest['artifacts'].items():
 if r.sha((RUNTIME/name).read_bytes())!=want:raise SystemExit('stopped runtime artifact mismatch; no runtime imported')
initial={str(p):r.sha(p.read_bytes()) for p in RUNTIME.iterdir() if p.is_file()}
barrier=ROUND/'review/BARRIER-READY.json';barrier_initial=r.sha(barrier.read_bytes())
sys.dont_write_bytecode=True;tempfile.tempdir=str(HERE);r.install_guard(HERE)
checks=[]
def ck(name,ok,detail=None):checks.append({'name':name,'passed':bool(ok),'detail':detail})
def deny(name,fn):
 try:fn()
 except (ValueError,TypeError,KeyError,IndexError,OverflowError,RecursionError):ck(name,True)
 else:ck(name,False)
def load(name,p):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
sys.path.insert(0,str(RUNTIME));a=load('reviewed_r10_adapter',RUNTIME/'adapter.py');c=a.c;k=a.k
text,record,planned,prior=a.preflight()
ck('preflight prior integer',prior['prior_nanousd']==r.PRIOR)
ck('frozen source-only request',planned['body']==c.read(c.PROTO/'stage-a.offline-request.json') and planned['guarded_bytes']==8674)
ck('authorization exact',c.read(ROUND/'live-authorization.json')==a.authorization_fields())
ck('projection independently exact',k.projection(record)==r.projection(record))
ck('all fields independently exact',k.fields(record)==r.fields(record) and len(r.fields(record))==310)
ck('all identity contexts exact',k.identities(record)==r.identities(record)==r.identities(k.projection(record)) and len(r.identities(record))==70)

def inventory(source=text,n=1,heavy=False):
 return {'schema_version':'round10.source-inventory.v1','source_text_sha256':r.sha(source.encode()),'units':[{'id':f'u{i+1:03}','kind':'fact','assertion':'x'*(360 if heavy else 30),'modality':'informational','applicability':'unconditional','uncertainty':'none','uncertainty_reason':'','required_unit_ids':[],'evidence':[{'quote':source[:min(80,len(source))],'occurrence':1}]} for i in range(n)]}
def mapping(inv,rec=record):
 p=next(p for p,v in r.fields(rec).items() if v not in (None,'',[],{}))
 return {'schema_version':'round10.source-mapping.v1','source_text_sha256':inv['source_text_sha256'],'record_sha256':r.sha(r.encode(rec)),'inventory_sha256':r.sha(r.encode(inv)),'mappings':{u['id']:{'disposition':'matched','operative_pointers':[p],'reason':'Explicit synthetic annotation, not semantic evidence.'} for u in inv['units']}}
# Source-only builder accepts no other task data, reads only three public protocol files.
seen=[];real_read=c.read
with patch.object(c,'read',lambda p:(seen.append(Path(p).name),real_read(p))[1]):built=k.build_a(text)
ck('A helper read allowlist',set(seen)<={'request-settings.json','stage-a.schema.json'})
ck('A input closed',set(c.strict(built['body']['messages'][1]['content']))=={'source_text','source_text_sha256'})
for raw in ('{"a":1,"a":2}','{"a":{"b":1,"b":2}}','{"a":[{"b":1,"b":2}]}','{}{}','{} trailing','{"a":NaN}','{"a":Infinity}','{"a":-Infinity}','{"a":1e999}'):
 deny('strict rejects '+raw,lambda raw=raw:c.strict(raw))
for name in ('stage-a.schema.json','stage-b.schema.template.json'):
 s=c.read(c.PROTO/name);expanded=c.expand(s,s['$defs']);ck('expanded no refs '+name,b'"$ref"' not in r.encode(expanded))
 for kind in ('external','missing','siblings','cycle','unknown','unused','wrongname'):
  bad=copy.deepcopy(s)
  if kind=='external':bad['properties']['schema_version']={'$ref':'https://example.invalid/x'}
  elif kind=='missing':bad['properties']['schema_version']={'$ref':'#/$defs/z'}
  elif kind=='siblings':bad['properties']['schema_version']={'$ref':'#/$defs/'+next(iter(bad['$defs'])),'type':'string'}
  elif kind=='cycle':name0=next(iter(bad['$defs']));bad['$defs'][name0]={'$ref':'#/$defs/'+name0}
  elif kind=='unknown':bad['allOf']=[]
  elif kind=='unused':bad['$defs']['e']={'unrecognized':True}
  else:bad['$defs']['z']={'type':'string'}
  deny('resolver rejects '+name+' '+kind,lambda bad=bad:c.expand(bad,bad['$defs']))
# Independent codec inversion, including all three permitted selectors and ID gaps/order.
for source,qs in [('aaaa',[('aa',1),('aa',2),('aa',3)]),('😀e\u0301😀e\u0301',[('e\u0301',2),('😀',2)]),('x\r\nx\r\n',[('x\r\n',2)])]:
 inv=inventory(source);inv['units'][0]['id']='u064';inv['units'][0]['evidence']=[{'quote':q,'occurrence':occ} for q,occ in qs]
 wire=k.wire_encode(source,inv)
 ck('independent wire '+repr(source),wire==r.span_encode(inv,source))
 ck('independent decode '+repr(source),r.span_restore(wire,source,inv)==k.wire_decode(source,wire,inv)==inv)
inv=inventory('aaaa');inv['units'][0]['evidence']=[{'quote':'aa','occurrence':2}];wire=k.wire_encode('aaaa',inv)
for row in ([True,3,2],[1,True,2],[1,3,True],[1.,3,2],[-1,3,2],[1,1,2],[3,1,2],[1,5,2],[1,3,1],[1,3,0],[1,3,4],[1,3],[1,3,2,0]):
 bad=copy.deepcopy(wire);bad['units'][0][8]=[row];deny('bad span '+repr(row),lambda bad=bad:k.wire_decode('aaaa',bad,inv))
for field,value in [('columns',list(reversed(wire['columns']))),('evidence_columns',['occurrence','start','end']),('schema_version','wrong'),('source_text_sha256','0'*64),('units',[])]:
 bad=copy.deepcopy(wire);bad[field]=value;deny('bad wire '+field,lambda bad=bad:k.wire_decode('aaaa',bad,inv))
bad=copy.deepcopy(wire);bad['extra']=1;deny('bad envelope extra',lambda:k.wire_decode('aaaa',bad,inv))
# Explicit private fixtures; no production label lookup and no semantic-discovery claim.
cases=r.strict((HERE/'synthetic_cases.json').read_bytes())['cases'];same_sources={}
for case in cases:
 src=case['source_text'];rec=case['record'];inv=case['inventory'];value=case['mapping_response'];name=case['case_id'];out=k.validate_b(src,rec,inv,value)
 ck('annotated outcome '+name,out['mapping_status']==case['expected_mapping_status'])
 ck('semantic nonpromotion '+name,out['semantic_status']=='unverified' and out['source_inventory_completeness']=='unverified' and not out['production_eligible'] and not out['action_ready'])
 A=k.build_a(src);B=k.build_b(src,rec,inv);user=c.strict(B['body']['messages'][1]['content'])
 ck('B exact approved envelope '+name,set(user)=={'source_text','source_text_sha256','record_sha256','operative_record','operative_record_sha256','inventory_wire','inventory_sha256'})
 ck('private canary absent '+name,case['private_canary'].encode() not in r.encode(A) and case['private_canary'].encode() not in r.encode(B))
 ck('same-source A invariance '+name,src not in same_sources or A==same_sources[src]);same_sources[src]=A
 ck('B same source/record/inventory '+name,user['source_text']==src and user['record_sha256']==r.sha(r.encode(rec)) and user['operative_record']==r.projection(rec) and r.span_restore(user['inventory_wire'],src,inv)==inv)
# Exact mappings, operative pointer exclusion, claimed dependency closure and transitive unknown.
inv=inventory(n=4);inv['units'][1]['required_unit_ids']=['u001'];inv['units'][2]['required_unit_ids']=['u002'];value=mapping(inv)
for ptr in ('/events','/events/0','/events/0/id','/events/0/evidence','/coverage/rationale','/document_id','/events/00/phase','/events/-1/phase','/events/999/phase','/events/0/~2phase','/events/0/description/0'):
 bad=copy.deepcopy(value);bad['mappings']['u001']['operative_pointers']=[ptr];deny('nonoperative pointer '+ptr,lambda bad=bad:k.validate_b(text,record,inv,bad))
for kind in ('missing','extra','substitution','duplicate_pointer','source','record','inventory'):
 bad=copy.deepcopy(value)
 if kind=='missing':del bad['mappings']['u001']
 elif kind=='extra':bad['mappings']['u064']=bad['mappings']['u001']
 elif kind=='substitution':bad['mappings']['u064']=bad['mappings'].pop('u001')
 elif kind=='duplicate_pointer':bad['mappings']['u001']['operative_pointers']*=2
 else:bad[{'source':'source_text_sha256','record':'record_sha256','inventory':'inventory_sha256'}[kind]]='0'*64
 deny('mapping rejects '+kind,lambda bad=bad:k.validate_b(text,record,inv,bad))
for disposition in ('missing','mismatched','unknown'):
 bad=copy.deepcopy(value);bad['mappings']['u001']['disposition']=disposition
 if disposition=='missing':bad['mappings']['u001']['operative_pointers']=[]
 deny('matched dependency rejects '+disposition,lambda bad=bad:k.validate_b(text,record,inv,bad))
value['mappings']['u001']['disposition']='unknown'
for i in ('u002','u003','u004'):value['mappings'][i]['disposition']='mismatched'
out=k.validate_b(text,record,inv,value);ck('transitive unknown retains known defects',out['mapping_status']=='unverified' and out['effective_dispositions']['u003']=='unknown' and set(out['known_defects'])=={'u002','u003','u004'})
# Lifecycle uses synthetic messages only and counts actual fake POSTs.
key='SYNTHETIC_REVIEW_SECRET_bfa816'
def scenario(name,mutate=None,expected_calls=2,expected_charges=None,success=True,inv=None,fail_write=None,tamper=None):
 inv=inventory() if inv is None else inv;value=mapping(inv);calls=[];stages={};realput=a.put;realbuild=k.build_b
 with tempfile.TemporaryDirectory(prefix='r10-review-') as tmp:
  run=Path(tmp)/'run'
  def transport(body,secret):
   n=len(calls)+1;calls.append(body);folder=run/('stage-a' if n==1 else 'stage-b')
   ck(name+' intent before POST '+str(n),(folder/'intent.json').exists() and r.sha((folder/'request.json').read_bytes())==c.read(folder/'intent.json')['request_sha256'])
   ck(name+' secret only to transport '+str(n),secret==key)
   if n==2:ck(name+' A frozen before B',(run/'stage-a-freeze.json').exists() and (run/'stage-a/completed.json').exists())
   obj=r.native(inv if n==1 else value);status=200
   if mutate:status,obj=mutate(n,obj)
   raw=obj if isinstance(obj,bytes) else r.encode(obj);stages[n]=raw
   return status,raw
  def put(path,*args):
   if fail_write and str(Path(path).relative_to(run))==fail_write:
    if Path(path).name=='intent.json':Path(path).write_bytes(b'{')
    raise OSError(key)
   return realput(path,*args)
  done_tamper=False
  def build(src,rec,iv):
   nonlocal done_tamper
   result=realbuild(src,rec,iv)
   if tamper and not done_tamper:
    done_tamper=True;p=run/tamper;p.write_bytes(b'{"tampered":true}')
   return result
  try:
   with patch.object(a,'put',put),patch.object(k,'build_b',build):result=a.execute_once(run,text,record,planned,key,transport)
  except BaseException as exc:result=None
  ck(name+' dispatch count',len(calls)==expected_calls,{'observed':len(calls),'expected':expected_calls})
  ck(name+' success state',(run/'completed.json').exists()==success)
  if expected_charges is not None:
   try:ledger=c.read(run/'ledger.json');actual=ledger['new_budget_charge_nanousd']
   except BaseException:actual=None
   ck(name+' conservative ledger',actual==sum(expected_charges),{'observed':actual,'expected':sum(expected_charges)})
  ck(name+' no leaked sentinel',all(key.encode() not in p.read_bytes() for p in run.rglob('*') if p.is_file()))
  try:a.execute_once(run,text,record,planned,key,transport)
  except FileExistsError:pass
  else:ck(name+' replay rejected',False)
  ck(name+' replay no redispatch',len(calls)==expected_calls)
scenario('positive',expected_charges=[r.RESERVE,r.RESERVE])
for fail_stage in (1,2):
 for kind in ('http','length','refusal','tools','model','provider','choicecount','badusage','badcost','inner','duplicate','transport','echo','oversize'):
  def mutate(n,obj,fs=fail_stage,kind=kind):
   if n!=fs:return 200,obj
   obj['usage']['cost']=.5
   if kind=='http':return 429,obj
   if kind=='length':obj['choices'][0]['finish_reason']='length'
   elif kind=='refusal':obj['choices'][0]['message']['refusal']='refusal'
   elif kind=='tools':obj['choices'][0]['message']['tool_calls']=[{}]
   elif kind=='model':obj['model']='wrong'
   elif kind=='provider':obj['provider']='wrong'
   elif kind=='choicecount':obj['choices']*=2
   elif kind=='badusage':obj['usage']['prompt_tokens']=True
   elif kind=='badcost':obj['usage']={'prompt_tokens':300000,'completion_tokens':100}
   elif kind=='inner':obj['choices'][0]['message']['content']='{'
   elif kind=='duplicate':obj['choices'][0]['message']['content']='{"schema_version":"a","schema_version":"b"}'
   elif kind=='transport':raise OSError(key)
   elif kind=='echo':obj['choices'][0]['message']['content']=key
   elif kind=='oversize':obj['padding']='x'*2000001
   return 200,obj
  charge=r.RESERVE if kind=='transport' else 601000000 if kind=='badcost' else 500000000
  scenario(f'{fail_stage}-{kind}',mutate,fail_stage,[r.RESERVE]*(fail_stage-1)+[charge],False)
for stage in (1,2):
 for nano in (979769281,979769282,979769283,1141689283):
  def mutate(n,obj,stage=stage,nano=nano):
   if n==stage:obj['usage']['cost']=nano/10**9
   return 200,obj
  admitted=nano<=979769282
  scenario(f'budget-stage{stage}-{nano}',mutate,2 if stage==2 or admitted else 1,[nano,r.RESERVE] if stage==1 and admitted else [nano] if stage==1 else [r.RESERVE,nano],admitted)
for stage in ('stage-a','stage-b'):
 for name in ('response.body','status.json','content.body','validated.json','result.json','completed.json'):
  def mutate(n,obj,stage=stage):
   if n==(1 if stage=='stage-a' else 2):obj['usage']['cost']=.5
   return 200,obj
  scenario('write-'+stage+'-'+name,mutate,1 if stage=='stage-a' else 2,[500000000] if stage=='stage-a' else [r.RESERVE,500000000],False,fail_write=stage+'/'+name)
for name in ('request.json','intent.json','response.body','status.json','content.body','validated.json','result.json','completed.json'):
 scenario('A-tamper-'+name,expected_calls=1,expected_charges=None,success=False,tamper='stage-a/'+name)
scenario('partial-A-intent',expected_calls=0,expected_charges=[r.RESERVE],success=False,fail_write='stage-a/intent.json')
scenario('partial-B-intent',expected_calls=1,expected_charges=[r.RESERVE,r.RESERVE],success=False,fail_write='stage-b/intent.json')
scenario('B-overguard',expected_calls=1,expected_charges=[r.RESERVE],success=False,inv=inventory(n=64,heavy=True))
for value in (-1,True,None,float('nan'),float('inf')):deny('invalid cost '+str(value),lambda value=value:a.cost_nano(value))
ck('fractional nano ceiling',a.cost_nano(.2000000001)==200000001)
# The owner suite is rerun only after all independently authored controls.
stream=io.StringIO();owner=load('owner_runtime_suite',RUNTIME/'test_runtime.py')
result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(owner))
(HERE/(label+'-owner-tests.txt')).write_text(stream.getvalue())
ck('owner independent rerun',result.wasSuccessful(),{'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors)})
ck('stopped runtime unchanged',all(Path(p).exists() and r.sha(Path(p).read_bytes())==h for p,h in initial.items()))
ck('barrier unchanged',r.sha(barrier.read_bytes())==barrier_initial)
ck('READY unchanged',r.sha(ready.read_bytes())==expected)
report={'runtime_ready_sha256':expected,'checks':checks,'checks_passed':sum(x['passed'] for x in checks),'checks_failed':sum(not x['passed'] for x in checks),'provider_calls':0,'credentials_read':False,'runtime_files':initial,'owner_tests':result.testsRun,'semantic_discovery_tested':False}
(HERE/(label+'-checks.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('checks','runtime_files')}))
