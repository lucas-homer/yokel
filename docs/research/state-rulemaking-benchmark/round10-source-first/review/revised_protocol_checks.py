"""Independent protocol inversion and boundary probes, not runtime implementation."""
import copy,hashlib,json,subprocess,sys
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parent;B=R.parent;P=R/'protocol'
def enc(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(v):return hashlib.sha256(v).hexdigest()
def read(p):return json.loads(p.read_bytes())
checks=[]
def ck(name,ok):checks.append({'name':name,'passed':bool(ok)})
ready=read(P/'READY.json'); readyhash=sha((P/'READY.json').read_bytes())
for f,h in ready['files'].items():ck('manifest:'+f,sha((P/f).read_bytes())==h)
base=read(R/'prior-baseline.json');ck('5114_prior_unchanged',len(base['files'])==5114 and all(sha((B/f['path']).read_bytes())==f['sha256'] and (B/f['path']).stat().st_size==f['bytes'] for f in base['files']))
pins=read(P/'input-pins.json')
for f,h in pins['files'].items():ck('input:'+f,sha((B/f).read_bytes())==h)
a=read(B/'round8-stronger-cap-probe/execution/run/documents/doc-92211b8c7ba0/assembled.json');s=a['source']['source_text'];record=a['record'];op=read(P/'stage-b.operative-record.json')
def project(x):
 if isinstance(x,dict):return {k:project(v) for k,v in x.items() if k not in ('evidence','coverage')}
 if isinstance(x,list):return [project(v) for v in x]
 return x
def ids(x,p=''):
 out={}
 if isinstance(x,dict):
  if 'id' in x:out[x['id']]=p
  for k,v in x.items():
   z=ids(v,p+'/'+k.replace('~','~0').replace('/','~1'));assert not out.keys()&z.keys();out.update(z)
 elif isinstance(x,list):
  for i,v in enumerate(x):
   z=ids(v,p+'/'+str(i));assert not out.keys()&z.keys();out.update(z)
 return out
ck('operative_record_exact',project(record)==op)
ck('all70_id_bindings',len(ids(record))==70 and ids(record)==ids(op))
fields={}
def walk(obj,p):
 for k,v in obj.items():
  if k in ('id','evidence'):continue
  if k in ('timing','components'):
   for i,item in enumerate(v):walk(item,p+'/'+k+'/'+str(i))
  else:fields[p+'/'+k]=v
for k in ('events','routes','requirements','identities','uncertainties','alternative_groups'):
 for i,obj in enumerate(record[k]):walk(obj,'/'+k+'/'+str(i))
ck('310_operative_fields_exact',len(fields)==310 and fields==read(P/'stage-b.operative-projection.json'))
ck('ids_not_operative',not any(p.endswith('/id') for p in fields))
# Opaque identity renaming and swapped endpoints must survive projection literally.
renames={v:'opaque_'+str(i) for i,v in enumerate(ids(record))}
def rename(v):
 if isinstance(v,str):return renames.get(v,v)
 if isinstance(v,list):return [rename(x) for x in v]
 if isinstance(v,dict):return {k:rename(x) for k,x in v.items()}
 return v
opaque=rename(record);ck('opaque_ids_preserved',ids(project(opaque))==ids(opaque))
swapped=copy.deepcopy(opaque);swapped['routes'][2]['id'],swapped['routes'][3]['id']=swapped['routes'][3]['id'],swapped['routes'][2]['id'];ck('swapped_endpoints_preserved',ids(project(swapped))==ids(swapped) and ids(swapped)!=ids(opaque))
c=read(P/'inventory-wire-contract.json');cols=['id','kind','assertion','modality','applicability','uncertainty','uncertainty_reason','required_unit_ids','evidence']
ck('fixed_columns',c['columns']==cols and c['evidence_columns']==['start','end','occurrence'] and c['schema_version']=='round10.inventory-span-tuples.v1')
def starts(source,q):
 assert type(q) is str and q.strip()
 out=[];i=0
 while True:
  i=source.find(q,i)
  if i<0:return out
  out.append(i);i+=1

def wire(inv,source):
 assert inv['source_text_sha256']==sha(source.encode())
 rows=[]
 for u in inv['units']:
  assert set(u)==set(cols)
  row=[]
  for k in cols:
   if k!='evidence':row.append(copy.deepcopy(u[k]));continue
   es=[]
   for e in u[k]:
    assert set(e)=={'quote','occurrence'} and type(e['occurrence']) is int
    pp=starts(source,e['quote']);n=e['occurrence'];assert 1<=n<=len(pp);i=pp[n-1]
    es.append([i,i+len(e['quote']),n])
   row.append(es)
  rows.append(row)
 return {'schema_version':c['schema_version'],'source_text_sha256':inv['source_text_sha256'],'columns':cols,'evidence_columns':['start','end','occurrence'],'units':rows}

def restore(w,source,frozen):
 assert set(w)=={'schema_version','source_text_sha256','columns','evidence_columns','units'}
 assert w['schema_version']==c['schema_version'] and w['columns']==cols and w['evidence_columns']==['start','end','occurrence'] and w['source_text_sha256']==sha(source.encode())
 units=[]
 for r in w['units']:
  assert type(r) is list and len(r)==9
  u=dict(zip(cols,copy.deepcopy(r)));evidence=[]
  for e in u['evidence']:
   assert type(e) is list and len(e)==3 and all(type(x) is int for x in e)
   i,j,n=e;assert 0<=i<j<=len(source);q=source[i:j];ss=starts(source,q);assert 1<=n<=len(ss) and ss[n-1]==i
   evidence.append({'quote':q,'occurrence':n})
  u['evidence']=evidence;units.append(u)
 out={'schema_version':'round10.source-inventory.v1','source_text_sha256':sha(source.encode()),'units':units}
 assert enc(out)==enc(frozen) and sha(enc(out))==sha(enc(frozen))
 return out

def inv(source,quotes):
 return {'schema_version':'round10.source-inventory.v1','source_text_sha256':sha(source.encode()),'units':[{'id':f'u{i+1:03}','kind':'relationship' if i else 'fact','assertion':'A source-local assertion.','modality':'unknown' if i else 'informational','applicability':'unconditional','uncertainty':'source_ambiguous' if i else 'none','uncertainty_reason':'Ambiguous.' if i else '', 'required_unit_ids':['u001'] if i else [],'evidence':[{'quote':q,'occurrence':n}]} for i,(q,n) in enumerate(quotes)]}
for source,qs in [('aaaa',[('aa',1),('aa',2),('aa',3)]),('😀e\u0301😀e\u0301',[('e\u0301',2),('😀',1)]),('x\r\nx\r\n',[('x\r\n',2)]),('q/~ \\"\nq/~ \\"',[('q/~',2)])]:
 f=inv(source,qs);ck('roundtrip:'+repr(source),restore(wire(f,source),source,f)==f)
f=inv('aaaa',[('aa',2)]);w=wire(f,'aaaa')
def bad(name,mutate,source='aaaa',frozen=f):
 z=copy.deepcopy(w);mutate(z)
 try:restore(z,source,frozen)
 except (AssertionError,ValueError,TypeError,KeyError,IndexError):ck('reject:'+name,True)
 else:ck('reject:'+name,False)
for name,row in [('bool_start',[True,3,2]),('bool_end',[1,True,2]),('bool_occurrence',[1,3,True]),('float',[1.,3,2]),('negative',[-1,3,2]),('empty',[1,1,2]),('reversed',[3,1,2]),('too_long',[1,5,2]),('wrong_occurrence',[1,3,1]),('zero_occurrence',[1,3,0]),('too_many_occurrence',[1,3,4]),('short_row',[1,3]),('long_row',[1,3,2,0])]:bad(name,lambda z,row=row:z['units'][0].__setitem__(8,[row]))
bad('extra_envelope',lambda z:z.update(extra=True));bad('wrong_columns',lambda z:z['columns'].reverse());bad('wrong_evidence_columns',lambda z:z['evidence_columns'].reverse());bad('short_unit',lambda z:z['units'][0].pop());bad('long_unit',lambda z:z['units'][0].append(None));bad('changed_assertion',lambda z:z['units'][0].__setitem__(2,'changed'));bad('dropped_empty',lambda z:z['units'][0].pop(6));bad('source_hash',lambda z:z.update(source_text_sha256='0'*64));bad('wrong_version',lambda z:z.update(schema_version='other'))
# Author's frozen runnable probes are read-only; independently verified operations above.
author=json.loads(subprocess.check_output([sys.executable,'-B',str(P/'authoring_checks.py')]))
ck('author_probe_reproduction',author['stage_b_probes']==read(P/'size-probes.json')['stage_b_probes'])
ck('author_id_count',author['id_container_bindings_verified']==70)
# Schema objects are closed and their references stay within the frozen allowlist.
def schema_check(x):
 if not isinstance(x,dict):return
 if '$ref' in x:assert set(x)=={'$ref'} and x['$ref'] in ('#/$defs/e','#/$defs/u','#/$defs/m')
 if x.get('type')=='object':assert x.get('additionalProperties') is False and set(x['required'])==set(x['properties'])
 for k,v in x.items():
  if k in ('properties','$defs'):
   for child in v.values():schema_check(child)
  elif k=='items':schema_check(v)
for fn in ('stage-a.schema.json','stage-b.schema.template.json'):
 try:schema_check(read(P/fn));ck('closed_schema:'+fn,True)
 except AssertionError:ck('closed_schema:'+fn,False)
reg=read(P/'offline-regressions.json');fixtures=read(B/'round9-exact-id-completeness/protocol/development-fixtures.json')['fixtures'];ck('10_declared_cases',len(reg['cases'])==10)
for fam in fixtures:
 for v in fam['variants']:
  source=v.get('source_text_override',fam['source_text']);ck('fixture_source_hash:'+fam['fixture_id']+'/'+v['id'],sha(source.encode())==v['record']['source_text_sha256'])
ck('source_override_policy_correct',all("variant.get('source_text_override', family['source_text'])" in row['source_override_policy'] for row in reg['cases']))
ck('ready_still_frozen',sha((P/'READY.json').read_bytes())==readyhash and all(sha((P/f).read_bytes())==h for f,h in ready['files'].items()))
print(json.dumps({'protocol_ready_sha256':readyhash,'checks':checks,'passed':sum(x['passed'] for x in checks),'failed':sum(not x['passed'] for x in checks),'author_probe_reproduction':author,'provider_calls':0,'runtime_approval':False},indent=2))
