import json,hashlib,importlib.util,copy,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent; ROOT=HERE.parent; PROTO=ROOT/'protocol'; BENCH=ROOT.parent
sys.dont_write_bytecode=True

def guard(event,args):
 if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.posix_spawn'):raise RuntimeError('offline only')
 if event=='open' and isinstance(args[0],(str,bytes)):
  p=Path(str(args[0]));mode=args[1];flags=args[2]
  if any(x in str(p).lower() for x in ('/library/keychains/','/.aws/','/.env','.pem')):raise RuntimeError('no credential access')
  if ((isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags&3)) and not p.resolve().is_relative_to(HERE):raise RuntimeError('review writes only')
sys.addaudithook(guard)
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def hashv(v):return hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
spec=importlib.util.spec_from_file_location('frozen_pipeline',BENCH/'round7/pipeline/pipeline.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
checks=[]
def check(name,ok,detail=None):
 checks.append(dict(name=name,passed=bool(ok),detail=detail))
 if not ok:raise AssertionError((name,detail))
ready=read(PROTO/'READY.json');check('all proposed artifact pins',all(sha(PROTO/n)==h for n,h in ready['artifacts'].items()))
prior=read(HERE/'prior-baseline.json')['files'];bad=[n for n,h in prior.items() if sha(Path(n))!=h];check('historical baseline unchanged',not bad,{'files':len(prior),'mismatches':bad})
for row in read(PROTO/'PROVENANCE.json')['inputs']:check('provenance '+Path(row['path']).name,sha(Path(row['path']))==row['sha256'])
assembled=read(BENCH/'round8-stronger-cap-probe/execution/run/documents/doc-92211b8c7ba0/assembled.json');source=read(BENCH/'round8-stronger-cap-probe/execution/run/documents/doc-92211b8c7ba0/source.json');schedule=read(PROTO/'wi70-schedule.json');ids=[x['id'] for _,x in p.all_items(assembled['record'])]
check('70 item schedule and record binding',len(ids)==len(set(ids))==70 and schedule['sorted_ids']==sorted(ids) and schedule['record_sha256']==hashv(assembled['record']) and schedule['payload_sha256']==p.verification_payload(source,assembled)['payload_sha256'])
for item in schedule['items']:
 value=assembled['record']
 for part in item['pointer'].split('/')[1:]:value=value[int(part)] if isinstance(value,list) else value[part]
 check('schedule pointer '+item['item_id'],value['id']==item['item_id'])
schema=copy.deepcopy(p.VERDICT_SCHEMA);schema['properties']['assessments']['minItems']=70;schema['properties']['assessments']['maxItems']=70;schema['properties']['assessments']['items']['properties']['item_id']['enum']=sorted(ids);schema['properties']['contradictions']['items']['properties']['item_ids']['items']['enum']=sorted(ids);schema['properties']['document_id']['enum']=[source['document_id']];schema['properties']['payload_sha256']['enum']=[schedule['payload_sha256']]
check('schema only specified dynamic changes',schema==read(PROTO/'wi70-response.schema.json'))
for case in read(PROTO/'response-fixtures.json')['cases']:
 checked=p.validate_verdict(source,assembled,case['response']);check('response '+case['id'],checked['valid']==case['expected_structural_valid'],checked['errors'])
 if case['id']=='duplicate_balanced_negative':check('balanced duplicate evades schema alone',not p.schema_errors(case['response'],schema))
 if checked['valid']:check('positive is uncertain not complete',case['response']['completeness']['label']=='uncertain' and not case['expected_accepted'])

def evidence(value,text):
 if isinstance(value,dict):
  if {'start','end','quote'}<=set(value):assert text[value['start']:value['end']]==value['quote']
  for v in value.values():evidence(v,text)
 elif isinstance(value,list):
  for v in value:evidence(v,text)

def diff(a,b,path=''):
 if isinstance(a,dict) and isinstance(b,dict):return sum((diff(a.get(k),b.get(k),path+'/'+k) for k in a.keys()|b.keys()),[])
 if isinstance(a,list) and isinstance(b,list) and len(a)==len(b):return sum((diff(x,y,path+'/'+str(i)) for i,(x,y) in enumerate(zip(a,b))),[])
 return [] if a==b else [path]
fixture_details=[]
for family in read(PROTO/'development-fixtures.json')['fixtures']:
 variants={v['id']:v for v in family['variants']}
 for variant in variants.values():
  text=variant.get('source_text_override',family['source_text']);record=variant['record'];name=family['fixture_id']+'/'+variant['id'];errors=p.schema_errors(record,p.RECORD_SCHEMA)+p.relationship_errors(record)
  evidence(record,text);evidence(family['source_units']+variant.get('additional_source_units',[]),text)
  check(name+' record and exact evidence',not errors and hashlib.sha256(text.encode()).hexdigest()==record['source_text_sha256'],errors)
  fixture_details.append(dict(name=name,review_reasons=p.review_reasons(record),expected=variant['expected']))
 if family['fixture_id']=='rule_assertion':
  check('rule evidence held constant',diff(variants['semantic_positive']['record'],variants['evidence_only_negative']['record'])==['/events/0/description'])
  check('coverage change only',diff(variants['evidence_only_negative']['record'],variants['coverage_rationale_cannot_repair']['record'])==['/coverage/rationale'])
 if family['fixture_id']=='modality_preservation':
  for name in ['unclear_negative','mandatory_negative']:check(name+' modality only',diff(variants['optional_positive']['record'],variants[name]['record'])==['/requirements/0/modality'])
check('prior still unchanged',all(sha(Path(n))==h for n,h in prior.items()))
report=dict(state='structural_authoring_checks_passed_semantic_barrier_review_separate',checks=checks,fixture_details=fixture_details,provider_calls=0,credential_reads=False,protocol_READY_sha256=sha(PROTO/'READY.json'))
(HERE/'barrier-checks.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n');print(json.dumps({'checks':len(checks),'passed':True,'protocol_READY_sha256':sha(PROTO/'READY.json')}))
