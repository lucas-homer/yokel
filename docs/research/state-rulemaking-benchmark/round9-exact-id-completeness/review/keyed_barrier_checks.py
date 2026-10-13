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
schema=copy.deepcopy(p.VERDICT_SCHEMA)
schema['properties']['schema_version']['enum']=['round9.exact-id.record_verdict.v1']
value=copy.deepcopy(schema['properties']['assessments']['items']);del value['properties']['item_id'];value['required'].remove('item_id')
schema['properties']['assessments']={'type':'object','properties':{i:copy.deepcopy(value) for i in sorted(ids)},'required':sorted(ids),'additionalProperties':False}
schema['properties']['contradictions']['items']['properties']['item_ids']['items']['enum']=sorted(ids)
schema['properties']['document_id']['enum']=[source['document_id']];schema['properties']['payload_sha256']['enum']=[schedule['payload_sha256']]
compact=read(PROTO/'wi70-response.schema.json')
def expand(v,chain=()):
 if isinstance(v,dict):
  if '$ref' in v:
   ref=v['$ref'];assert set(v)=={'$ref'} and ref in ('#/$defs/a','#/$defs/e') and ref not in chain and len(chain)<8
   return expand(compact['$defs'][ref.rsplit('/',1)[1]],chain+(ref,))
  return {k:expand(x,chain) for k,x in v.items() if k!='$defs'}
 if isinstance(v,list):return [expand(x,chain) for x in v]
 return v
expanded=expand(compact)
check('compact expansion equals independent keyed schema',expanded==schema)
size=read(PROTO/'wire-size-check.json');check('expanded schema pinned digest',hashv(expanded)==size['baseline_expanded_schema_canonical_sha256'])
def strict(raw):
 def pairs(rows):
  out={}
  for k,v in rows:
   if k in out:raise ValueError('duplicate key: '+k)
   out[k]=v
  return out
 return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)))
for case in read(PROTO/'response-fixtures.json')['cases']:
 try:
  wire=strict(case['raw_json']);errors=p.schema_errors(wire,expanded)
  if not errors:
   legacy=copy.deepcopy(wire);legacy['schema_version']='round7.record_verdict.v1';legacy['assessments']=[dict(item_id=i,**wire['assessments'][i]) for i in sorted(ids)]
   errors=p.validate_verdict(source,assembled,legacy)['errors']
   check('lossless values '+case['id'],all({k:v for k,v in row.items() if k!='item_id'}==wire['assessments'][row['item_id']] for row in legacy['assessments']))
 except ValueError as e:errors=[str(e)]
 check('response '+case['id'],(not errors)==case['expected_structural_valid'],errors)
check('exactly 13 active raw response cases',len(read(PROTO/'response-fixtures.json')['cases'])==13)
request=read(PROTO/'wi70-offline-request.fixture.json');oldrequest=read(BENCH/'round8-stronger-cap-probe/execution/run/documents/doc-92211b8c7ba0/stronger-request.json');expected_request=copy.deepcopy(oldrequest);expected_request['response_format']['json_schema']['schema']=compact;expected_request['messages'][0]['content']+='\n'+size['added_neutral_instruction']
check('request only declared changes',request==expected_request)
request_bytes=json.dumps(request,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
check('full request unchanged guard',len(request_bytes)==38432 and len(request_bytes)+1024==size['guarded_bytes']==39456 and size['headroom_bytes']==544 and hashv(request)==size['request_canonical_sha256'])
check('compact schema exact size',len(json.dumps(compact,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())==7506)

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
# Validate audit envelopes and every semantic-field/hash binding independently.
fixtures=read(PROTO/'development-fixtures.json')['fixtures'];by_variant={(f['fixture_id'],v['id']):(f,v) for f in fixtures for v in f['variants']}
audits=read(PROTO/'development-audit-inputs.json')['audits'];maps={x['audit_id']:x for x in read(PROTO/'development-audit-mapping.json')['mappings']};review=read(PROTO/'offline-audit-review.json');review_by={x['audit_id']:x for x in review['entries']}
check('review envelope schema',not p.schema_errors(review,read(PROTO/'offline-audit-review.schema.json')))
check('audit ids unique',len(audits)==len({x['audit_id'] for x in audits})==len(review_by)==10)
def resolve(record,pointer):
 val=record
 for part in pointer.split('/')[1:]:
  part=part.replace('~1','/').replace('~0','~');val=val[int(part)] if isinstance(val,list) else val[part]
 return val

def fields(record):
 result={}
 def visit(item,path):
  for key,val in item.items():
   if key in ('id','evidence'):continue
   if key in ('timing','components'):
    for i,x in enumerate(val):visit(x,path+'/'+key+'/'+str(i))
   else:result[path+'/'+key]=val
 for cat in p.CATEGORIES:
  for i,item in enumerate(record[cat]):visit(item,'/'+cat+'/'+str(i))
 return result
outcomes={};unit_count=claim_count=0
for audit in audits:
 name=audit['audit_id'];family,variant=by_variant[tuple(name.split('/'))];record=variant['record'];text=variant.get('source_text_override',family['source_text']);ref=audit['source_reference'];mapping=maps[name];endorsement=review_by[name];name_prefix=name+' audit '
 check(name_prefix+'schema',not p.schema_errors(audit,read(PROTO/'semantic-audit-input.schema.json')))
 check(name_prefix+'hash bindings',hashv(audit)==mapping['audit_sha256']==endorsement['audit_sha256'] and hashv(record)==audit['record_sha256']==endorsement['record_sha256'] and hashv(ref)==audit['source_reference_sha256']==endorsement['source_reference_sha256'] and hashlib.sha256(text.encode()).hexdigest()==audit['source_text_sha256']==ref['source_text_sha256']==endorsement['source_text_sha256'] and audit['document_id']==ref['document_id']==record['document_id'])
 evidence(ref,text);check(name_prefix+'full source scope',ref['scope']['reviewed_start']==0 and ref['scope']['reviewed_end']==len(text) and ref['scope']['status']=='complete' and not ref['scope']['exclusions'] and not ref['scope']['unresolved_questions'])
 units={x['source_unit_id']:x for x in ref['units']};rows={x['source_unit_id']:x for x in audit['source_dispositions']};claims={x['claim_id']:x for x in audit['candidate_claim_checks']};field_values=fields(record);ptrs={x['record_pointer']:x for x in claims.values()}
 check(name_prefix+'exact sets',len(units)==len(ref['units'])==len(rows)==len(audit['source_dispositions']) and set(units)==set(rows) and len(claims)==len(audit['candidate_claim_checks'])==len(ptrs)==len(field_values) and set(ptrs)==set(field_values))
 check(name_prefix+'all field hashes and unit refs',all(x['value_sha256']==hashv(field_values[q]) and set(x['source_unit_ids'])<=set(units) for q,x in ptrs.items()))
 for unit_id,unit in units.items():
  row=rows[unit_id];deps=unit['required_source_unit_ids'];check(name_prefix+'mapping '+unit_id,all(q in ptrs for q in row['semantic_record_pointers']) and len(set(row['semantic_record_pointers']))==len(row['semantic_record_pointers']) and set(row['candidate_claim_ids'])=={ptrs[q]['claim_id'] for q in row['semantic_record_pointers']} and set(deps)<=set(units) and unit_id not in deps)
  if row['disposition']=='matched':check(name_prefix+'matched '+unit_id,bool(row['candidate_claim_ids']) and all(claims[c]['disposition']=='supported' and unit_id in claims[c]['source_unit_ids'] for c in row['candidate_claim_ids']) and all(rows[d]['disposition']=='matched' for d in deps))
  if row['disposition']=='omitted':check(name_prefix+'omitted '+unit_id,not row['semantic_record_pointers'] and not row['candidate_claim_ids'])
 def closure(k,seen):
  assert k not in seen
  for dep in units[k]['required_source_unit_ids']:closure(dep,seen|{k})
 for unit_id in units:closure(unit_id,set())
 unknown=any(x['disposition']=='unknown' for x in rows.values()) or any(x['disposition']=='unknown' for x in claims.values()) or bool(p.review_reasons(record))
 bad=any(x['disposition'] in ('mismatched','omitted') for x in rows.values()) or any(x['disposition']=='unsupported' for x in claims.values())
 conditional='unverified' if unknown else 'not_complete' if bad else 'complete_supported';outcomes[name]=conditional
 check(name_prefix+'conditional outcome',conditional==mapping['conditional_result_after_valid_review_approval'])
 check(name_prefix+'approval not fabricated',endorsement['decision']=='pending' and endorsement['primary_reviewer'] is None and endorsement['independent_reviewer'] is None and mapping['current_expected_result']=='unverified')
 unit_count+=len(units);claim_count+=len(claims)
check('44 source dispositions and214 semantic fields',unit_count==44 and claim_count==214)
check('prior still unchanged',all(sha(Path(n))==h for n,h in prior.items()))
report=dict(state='structural_authoring_checks_passed_semantic_barrier_review_separate',checks=checks,fixture_details=fixture_details,conditional_audit_outcomes=outcomes,provider_calls=0,credential_reads=False,protocol_READY_sha256=sha(PROTO/'READY.json'))
(HERE/'keyed-barrier-checks.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n');print(json.dumps({'checks':len(checks),'passed':True,'protocol_READY_sha256':sha(PROTO/'READY.json')}))
