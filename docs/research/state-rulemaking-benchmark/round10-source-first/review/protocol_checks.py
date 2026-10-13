"""Independent read-only protocol checks. No provider/imported runtime dependencies."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROUND=HERE.parent
BENCH=ROUND.parent
P=ROUND/'protocol'
def read(p):
 def pairs(rows):
  d={}
  for k,v in rows:
   assert k not in d
   d[k]=v
  return d
 return json.loads(p.read_bytes(),object_pairs_hook=pairs,parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
def enc(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(v):return hashlib.sha256(v).hexdigest()
checks=[]
def check(name,ok):checks.append({'name':name,'passed':bool(ok)})
r=read(P/'READY.json')
for f,h in r['files'].items():check('protocol_pin:'+f,sha((P/f).read_bytes())==h)
b=read(ROUND/'prior-baseline.json')
check('prior_baseline_pin',sha((ROUND/'prior-baseline.json').read_bytes())=='b69bb44ca0fe9364fbae7380287a3d13fe07698997532fb5f5cbac394ab1450f')
check('prior_5114_unchanged',len(b['files'])==5114 and all((BENCH/f['path']).stat().st_size==f['bytes'] and sha((BENCH/f['path']).read_bytes())==f['sha256'] for f in b['files']))
pins=read(P/'input-pins.json')
for f,h in pins['files'].items():check('input_pin:'+f,sha((BENCH/f).read_bytes())==h)
a=read(BENCH/'round8-stronger-cap-probe/execution/run/documents/doc-92211b8c7ba0/assembled.json');record=a['record'];source=a['source']['source_text']
check('source_hash',sha(source.encode())==pins['source_text_sha256'])
check('record_hash',sha(enc(record))==pins['record_canonical_sha256'])
fields={};ids={}
def walk(obj,path):
 if 'id' in obj:ids[obj['id']]=path
 for k,v in obj.items():
  if k in ('id','evidence'):continue
  if k in ('timing','components'):
   for i,item in enumerate(v):walk(item,path+'/'+k+'/'+str(i))
  else:fields[path+'/'+k]=v
for k in ('events','routes','requirements','identities','uncertainties','alternative_groups'):
 for i,obj in enumerate(record[k]):walk(obj,'/'+k+'/'+str(i))
projection=read(P/'stage-b.operative-projection.json')
check('all_310_operative_fields_exact',len(fields)==310 and fields==projection)
q=read(P/'stage-a.offline-request.json');settings=read(P/'request-settings.json')
check('A_settings',all(q[k]==v for k,v in settings.items()))
check('A_two_messages',len(q['messages'])==2)
check('A_system_exact',q['messages'][0]=={'role':'system','content':(P/'stage-a.system.txt').read_text()})
check('A_source_only',read(P/'stage-a.offline-request.json')['messages'][1]['role']=='user' and json.loads(q['messages'][1]['content'])=={'source_text':source,'source_text_sha256':sha(source.encode())})
check('A_schema_exact',q['response_format']['json_schema']['schema']==read(P/'stage-a.schema.json'))
check('A_request_pin',sha(enc(q))==pins['stage_a_request_canonical_sha256'])
check('A_guard_8674',len(enc(q))+1024==8674 and len(enc(q))+1024<=40000)
check('reservation_arithmetic',858310718+2*161920000==1182150718<2000000000)
fixtures=read(BENCH/'round9-exact-id-completeness/protocol/development-fixtures.json')['fixtures']
variant=next(v for f in fixtures for v in f['variants'] if v['id']=='source_only_extra_negative')
reg=read(P/'offline-regressions.json')
check('source_override_policy_correct',all('variant.source_text_override' in c['source_override_policy'] for c in reg['cases']))
# Current closed B input includes no ID-to-object index. Show concrete dangling graph data.
check('B_relationship_identity_preserved',any(k.endswith('/id') for k in projection))
print(json.dumps({'protocol_ready_sha256':sha((P/'READY.json').read_bytes()),'checks':checks,'passed':sum(x['passed'] for x in checks),'failed':sum(not x['passed'] for x in checks),'relationship_example':{'group_pointer':'/alternative_groups/1/route_ids','values':projection['/alternative_groups/1/route_ids'],'missing_identity_index':{k:ids[k] for k in projection['/alternative_groups/1/route_ids']}},'source_override_actual_field':'source_text_override','source_override_actual_length':len(variant['source_text_override']),'provider_calls':0},indent=2))
