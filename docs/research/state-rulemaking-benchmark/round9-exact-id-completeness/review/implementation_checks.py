"""Independent offline adversarial review. Execute only after owner stops at READY."""
import copy,hashlib,importlib.util,json,math,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent;RUNTIME=ROOT/'runtime';PROTO=ROOT/'protocol'
sys.dont_write_bytecode=True

def guard(event,args):
    if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.posix_spawn'):raise RuntimeError('offline only')
    if event=='open' and isinstance(args[0],(str,bytes)):
        p=Path(str(args[0]));mode=args[1];flags=args[2]
        if any(x in str(p).lower() for x in ('/library/keychains/','/.aws/','/.env','.pem')):raise RuntimeError('no credential access')
        if ((isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags&3)) and not p.resolve().is_relative_to(HERE):raise RuntimeError('review writes only')
sys.addaudithook(guard)
assert (RUNTIME/'READY.json').exists(),'Owner stopped READY required before runtime import'
sys.path.insert(0,str(RUNTIME));sys.path.insert(0,str(HERE))
import common as c,request,response,semantic,adversarial_data as data
checks=[]
def check(name,ok,detail=None):checks.append({'name':name,'passed':bool(ok),'detail':detail})
def reject(name,fn):
    try:out=fn()
    except (ValueError,TypeError,KeyError,RecursionError) as e:check(name,True,type(e).__name__);return
    check(name,False,str(out)[:300])
def result(name,fn,expected,key):
    try:
        out=fn();check(name,out.get(key)==expected,out)
        if 'production_eligible' in out:check(name+' never production',out['production_eligible'] is False and out['action_ready'] is False)
        return out
    except Exception as e:check(name,False,{'uncaught':type(e).__name__,'message':str(e)[:300]})
def read(path):return json.loads(path.read_bytes())
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
start_pins={str(p):sha(p) for p in RUNTIME.glob('*') if p.is_file()}
check('protocol pins',all(sha(PROTO/n)==h for n,h in read(PROTO/'READY.json')['artifacts'].items()))
check('approval binding',sha(ROOT/'approved-development-audits.json')=='5682a7a621cd36b54b7736001799395dc9dd21d0c73010cb773f9e6a567c8f99')
body=request.wi();check('exact full fixture',body['body']==read(PROTO/'wi70-offline-request.fixture.json'))
check('canonical request size and estimate',body['body_bytes']==38432 and body['estimate']==39456 and body['schema_bytes']==7506, {k:body[k] for k in ['body_bytes','estimate','schema_bytes']})
check('provider absent/unverified',body['provider_calls']==0 and body['provider_compatibility']=='unverified')
old=request.BASELINE['messages'][0]['content']
try:
    request.BASELINE['messages'][0]['content']=old+'x'*544
    check('full request exact 40000 accepted',request.wi()['estimate']==40000)
    request.BASELINE['messages'][0]['content']=old+'x'*545
    reject('full request 40001 rejected',request.wi)
    request.BASELINE['messages'][0]['content']=old+'é'*273
    reject('full request multibyte counts bytes',request.wi)
finally:request.BASELINE['messages'][0]['content']=old
check('request user exact unchanged',body['body']['messages'][1]==request.BASELINE['messages'][1])
check('request neutral system only',body['body']['messages'][0]['content']==old+'\n'+request.SIZES['added_neutral_instruction'])
for canary in ['candidate_claim_checks','source_dispositions','expected_semantic_status','adversarial-test-only','primary_reviewer','independent_reviewer']:
    check('request private data absent '+canary,canary not in c.encode(body['body']).decode())
for raw in ['{"x":1,"x":2}','{"x":{"y":1,"y":2}}','{"x":[{"y":1,"\\u0079":2}]}','{"x":NaN}','{"x":Infinity}','{"x":-Infinity}','{"x":1e999}','{"x":-1e999}','{}{}']:
    reject('strict raw rejection '+raw,lambda raw=raw:c.strict(raw))
fixtures=read(PROTO/'response-fixtures.json')['cases'];source=request.ASSEMBLED['source'];assembled=request.ASSEMBLED
for f in fixtures:result('response fixture '+f['id'],lambda f=f:response.validate_response(f['raw_json'],source,assembled),f['expected_structural_valid'],'structural_valid')
wire=json.loads(fixtures[0]['raw_json']);nested_id=next(x['item_id'] for x in body['schedule']['items'] if x['kind'] in ('timing','components'))
for name,mutate in [
    ('missing nested ID',lambda v:v['assessments'].pop(nested_id)),
    ('wrong evidence',lambda v:v['completeness']['evidence'][0].update(quote='NOT PRESENT 983719')),
    ('wrong document',lambda v:v.update(document_id='other-document')),
    ('unknown assessment ID',lambda v:v['assessments'].update(unknown=copy.deepcopy(next(iter(v['assessments'].values()))))),
    ('embedded item ID',lambda v:next(iter(v['assessments'].values())).update(item_id='bad'))]:
    v=copy.deepcopy(wire);mutate(v);result(name,lambda v=v:response.validate_response(c.encode(v),source,assembled),False,'structural_valid')
for malformed in [None,[],{'record':None}]:result('malformed assembled '+str(malformed),lambda malformed=malformed:response.validate_response('{}',source,malformed),False,'structural_valid')
for raw in ['['*1100+'0'+']'*1100, '{"x":1e999}', '{"x":"\\ud800"}']:
    result('malformed raw response '+raw[:35],lambda raw=raw:response.validate_response(raw,source,assembled),False,'structural_valid')
schema=response.schema_for(body['schedule']);expanded=response.expand(schema)
check('expanded pinned schema',c.digest(expanded)=='7e1d307af2f397b8fea7b9388239091537b91c638cdcf69c74508b31e23d28f4')
for name,ref in [('unknown','#/$defs/z'),('external','https://example.invalid/schema'),('cycle','#')]:
    v=copy.deepcopy(schema);v['properties']['assessments']['properties'][nested_id]={'$ref':ref};reject('schema ref '+name,lambda v=v:response.expand(v))
v=copy.deepcopy(schema);v['properties']['assessments']['properties'][nested_id]['title']='sibling';reject('schema ref sibling',lambda:response.expand(v))
v=copy.deepcopy(schema);del v['$defs']['e'];reject('schema missing definition',lambda:response.expand(v))
v=copy.deepcopy(schema);v['$defs']['a']={'$ref':'#/$defs/a'};reject('schema changed/cyclic definition',lambda:response.expand(v))
v=copy.deepcopy(schema);v['unevaluatedProperties']=False;reject('schema unsupported keyword',lambda:response.expand(v))
v=copy.deepcopy(schema);branch={'$ref':'#/$defs/e'}
for _ in range(10):branch={'type':'object','properties':{'deep':branch}}
v['properties']['deep']=branch;reject('schema deep reference',lambda:response.expand(v))
for name,mutate in [('empty',lambda r:r['events'][0].update(id='')),('whitespace',lambda r:r['events'][0].update(id=' ')),('reserved',lambda r:r['events'][0].update(id='coverage')),('collision',lambda r:r['events'][0].update(id=r['identities'][0]['id']))]:
    record=copy.deepcopy(assembled['record']);mutate(record);reject('schedule '+name,lambda record=record:response.schedule(record,'0'*64))
record=copy.deepcopy(assembled['record'])
for category in response.CATEGORIES:record[category]=[]
reject('empty schedule',lambda:response.schedule(record,'0'*64))
record['identities']=[{'id':'id'+str(i)} for i in range(1001)];reject('1001 IDs rejected',lambda:response.schedule(record,'0'*64))
for family in read(PROTO/'development-fixtures.json')['fixtures']:
    for variant in family['variants']:
        name=family['fixture_id']+'/'+variant['id'];cx=data.context(name)
        expected={'semantic_positive':'complete_supported','full_group_positive':'complete_supported','optional_positive':'complete_supported','unknown_endpoint_blocks_group':'unverified','unclear_negative':'unverified'}.get(variant['id'],'not_complete')
        result('endorsed audit '+name,lambda cx=cx:semantic.aggregate(cx['source'],cx['record'],cx['audit'],cx['review']),expected,'semantic_status')
for name,cx,expected in data.audit_cases():
    out=result('audit mutation '+name,lambda cx=cx:semantic.aggregate(cx['source'],cx['record'],cx['audit'],cx['review']),expected,'semantic_status')
    if cx['review'] and any(e.get('primary_reviewer')=='adversarial-test-only-primary' for e in cx['review']['entries']):
        check('mutation reaches below bindings '+name,out is not None and not {'binding_mismatch','audit_unapproved'}&set(out.get('diagnostic_codes',[])),out.get('diagnostic_codes') if out else None)
    expected_code={'source_dependency_missing':'dependency_invalid','source_dependency_self':'dependency_invalid','source_dependency_cycle':'dependency_invalid','null_field_cannot_discharge_source_obligation':'mapping_inconsistent','unknown_precedes_known_defect':'semantic_unknown','unsupported_compound_addition':'semantic_defect'}.get(name)
    if expected_code:check('specific semantic guard '+name,out is not None and expected_code in out.get('diagnostic_codes',[]),out.get('diagnostic_codes') if out else None)
for name,mutate in [
    ('same reviewers',lambda e:e.update(independent_reviewer=e['primary_reviewer'])),
    ('author as reviewer',lambda e:e.update(primary_reviewer=data.context()['audit']['provenance']['author'])),
    ('empty note',lambda e:e.update(review_note='  ')),
    ('stale record',lambda e:e.update(record_sha256='0'*64))]:
    cx=data.seal(data.context());mutate(cx['review']['entries'][0]);result(name,lambda cx=cx:semantic.aggregate(cx['source'],cx['record'],cx['audit'],cx['review']),'unverified','semantic_status')
for record in [None,[],{}, {'coverage':[]}, {'coverage':None}, {'coverage':'invalid'}]:result('malformed semantic record '+str(record),lambda record=record:semantic.aggregate('',record),'unverified','semantic_status')
for raw in ['{"a":1,"a":2}','['*1100+'0'+']'*1100]:result('raw semantic input '+raw[:35],lambda raw=raw:semantic.aggregate_json('"source"',raw),'unverified','semantic_status')
cx=data.context();cx['audit']['audit_id']='independent-renamed-positive';data.seal(cx)
result('renamed audit no fixture lookup',lambda:semantic.aggregate(cx['source'],cx['record'],cx['audit'],cx['review']),'complete_supported','semantic_status')
cx=data.context();cx['audit']['candidate_claim_checks'][0]['record_pointer']='/coverage/rationale';data.seal(cx)
result('coverage never operative',lambda:semantic.aggregate(cx['source'],cx['record'],cx['audit'],cx['review']),'unverified','semantic_status')
cx=data.context();cx['audit']['candidate_claim_checks'][0]['record_pointer']='/events/0/evidence';data.seal(cx)
result('evidence never operative',lambda:semantic.aggregate(cx['source'],cx['record'],cx['audit'],cx['review']),'unverified','semantic_status')
prior=read(HERE/'prior-baseline.json')['files'];bad=[p for p,h in prior.items() if not Path(p).exists() or sha(Path(p))!=h]
check('4995 prior artifacts unchanged',len(prior)==4995 and not bad,bad)
check('runtime unchanged during independent test',all(sha(Path(p))==h for p,h in start_pins.items()))
report={'scope':'independent offline implementation review; no provider calls','runtime_sha256':start_pins,'checks':checks,'passed':sum(x['passed'] for x in checks),'failed':sum(not x['passed'] for x in checks)}
(HERE/'implementation-checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'passed':report['passed'],'failed':report['failed'],'failures':[x for x in checks if not x['passed']]},indent=2))
