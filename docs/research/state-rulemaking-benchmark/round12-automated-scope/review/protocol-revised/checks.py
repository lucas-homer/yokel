"""Independent revised-protocol checks. Standard library only; no network/provider/runtime."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROUND=HERE.parent.parent
REPO=ROUND.parents[3]
P=ROUND/'protocol'
rows=[];inputs={}
def raw(path):
    b=path.read_bytes();inputs[str(path.relative_to(REPO))]={'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)};return b
def load(path):return json.loads(raw(path))
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def digest(x):return hashlib.sha256(canon(x)).hexdigest()
def check(name,ok):rows.append({'name':name,'pass':bool(ok)})
def pin(path,expected):
    b=raw(path);check('pin:'+str(path.relative_to(REPO)),hashlib.sha256(b).hexdigest()==expected['sha256'] and len(b)==expected['bytes'])
ready=load(P/'READY.json')
for name,p in ready['files'].items():pin(P/name,p)
for name,p in ready['consulted_inputs'].items():pin(REPO/name,p)
initial=load(P/'revisions/initial/READY.json')
for name,p in initial['files'].items():pin(P/'revisions/initial'/name,p)
old_review=load(ROUND/'review/protocol/READY.json')
for name,p in old_review['files'].items():pin(ROUND/'review/protocol'/name,p)
check('initial_review_ready_unchanged',hashlib.sha256(raw(ROUND/'review/protocol/READY.json')).hexdigest()=='024f9890d305d35962bd364e6f46b41270a5e145ef8355fb2a6350a0f4b10661')
for folder in ('source','candidate'):
    manifest=load(ROUND/folder/'READY.json')
    for name,p in manifest['artifacts'].items():pin(ROUND/folder/p.get('path',name),p)
binding=load(P/'SOURCE-BINDING.json');sr=load(P/'SOURCE-READY.json')
for name,p in sr['files'].items():pin(P/name,p)
pin(P/'READY.json',binding['generic_ready']);pin(ROUND/'source/READY.json',binding['source_archive_ready']);pin(ROUND/'source/FRAME.json',binding['source_archive_frame']);pin(P/'revisions/initial/READY.json',binding['initial_generic_ready'])
for name in ('stage-a.system.txt','stage-c.system.txt','stage-d.system.txt','stage-a.schema.template.json','stage-b.schema.template.json','stage-c.schema.template.json','stage-d.schema.template.json','inventory-wire-contract.json','policy.json','request-settings.json'):
    check('unchanged:'+name,raw(P/name)==raw(P/'revisions/initial'/name))
boundary=load(P/'boundaries.json');before=load(P/'revisions/initial/boundaries.json')
check('B_only_input_change',boundary['exact_user_fields']['B']==['scope_wire' if x=='scope' else x for x in before['exact_user_fields']['B']])
check('A_C_D_boundaries_unchanged',all(boundary['exact_user_fields'][s]==before['exact_user_fields'][s] for s in ('A','C','D')))
check('forbidden_inputs_unchanged',boundary['forbidden_all_stages']==before['forbidden_all_stages'])
check('full_C_hash_substitution_unchanged',boundary['template_substitutions']==before['template_substitutions'])
oldprompt=raw(P/'revisions/initial/stage-b.system.txt').decode();prompt=raw(P/'stage-b.system.txt').decode()
check('B_only_appended_codec_explanation',prompt.startswith(oldprompt) and 'scope_wire has rows [id,category,basis,reason,evidence]' in prompt)
contract=load(P/'scope-wire-contract.json')
check('fixed_contract_version',contract['schema_version']=='round12.scope-span-tuples.v1' and contract['restored_schema_version']=='round12.source-scope.v1')
check('no_fallback_spec','No other scope representation or fallback' in raw(P/'SPEC.md').decode() and 'No full-C/fallback alternative on overflow' in boundary['B_scope_transport'])
check('partial_overflow_explicit','actual overflow stops B without shorter reasons, deleted evidence, source/candidate changes, cap increase or alternate codec' in raw(P/'SPEC.md').decode())
# Inspected owner probe module has no I/O at import. -B suppresses pycache.
spec=importlib.util.spec_from_file_location('reviewed_scope_codec',P/'scope_codec.py');codec=importlib.util.module_from_spec(spec);spec.loader.exec_module(codec)
check('constants_equal_contract',codec.COLUMNS==contract['columns'] and codec.EVIDENCE_COLUMNS==contract['evidence_columns'] and codec.CATEGORIES==contract['category_codes'] and codec.BASES==contract['basis_codes'])
source='🫧é aaa aa e\u0301\n"end"';ih='a'*64;ids=['u064','u002','u001','u031'];sh=hashlib.sha256(source.encode()).hexdigest()
c={'schema_version':'round12.source-scope.v1','source_text_sha256':sh,'inventory_sha256':ih,'scopes':{}}
quotes=[('é',1),('aa',2),('aa',3),('e\u0301',1)]
for j,uid in enumerate(ids):
    c['scopes'][uid]={'category':contract['category_codes'][j],'basis':contract['basis_codes'][j],'reason':f'Preserve reason {j}: "quoted"\n🫧é e\u0301.','evidence':[{'quote':quotes[j][0],'occurrence':quotes[j][1]},{'quote':'"end"','occurrence':1}]}
frozen=canon(c)
def independent_wire(scope,text,ordered_ids):
    out={'schema_version':contract['schema_version'],'source_text_sha256':scope['source_text_sha256'],'inventory_sha256':scope['inventory_sha256'],'columns':contract['columns'],'evidence_columns':contract['evidence_columns'],'scopes':[]}
    for uid in ordered_ids:
        s=scope['scopes'][uid];ev=[]
        for e in s['evidence']:
            matches=[i for i in range(len(text)) if text.startswith(e['quote'],i)];start=matches[e['occurrence']-1];ev.append([start,start+len(e['quote']),e['occurrence']])
        out['scopes'].append([uid,contract['category_codes'].index(s['category']),contract['basis_codes'].index(s['basis']),s['reason'],ev])
    return out
w=independent_wire(c,source,ids)
check('independent_wire_matches_owner',w==codec.encode(c,source,ih,ids))
check('exact_full_roundtrip_all_enum_unicode_overlap',canon(codec.decode(w,source,ih,ids,c))==frozen)
check('codepoint_not_utf8_or_utf16',w['scopes'][0][4][0]==[1,2,1])
def reject(name,mutation):
    bad=copy.deepcopy(w);mutation(bad)
    try:codec.decode(bad,source,ih,ids,c)
    except (ValueError,TypeError,KeyError,IndexError):check(name,True)
    else:check(name,False)
for col in (1,2):
    for value in (True,False,-1,4,0.0,'0',None,[],{}):reject(f'enum_type_bound_{col}_{value!r}',lambda b,v=value,col=col:b['scopes'][0].__setitem__(col,v))
for cat in range(4):
    for basis in range(4):
        if cat!=basis:reject(f'contradictory_codes_{cat}_{basis}',lambda b,x=cat,y=basis:(b['scopes'][0].__setitem__(1,x),b['scopes'][0].__setitem__(2,y)))
for key,value in [('schema_version','other'),('columns',list(reversed(contract['columns']))),('evidence_columns',['start','end']),('source_text_sha256','0'*64),('inventory_sha256','0'*64),('extra',1)]:reject('envelope_'+key,lambda b,k=key,v=value:b.update({k:v}))
for label,mutation in [('missing',lambda b:b['scopes'].pop()),('extra',lambda b:b['scopes'].append(copy.deepcopy(b['scopes'][0]))),('reorder',lambda b:b['scopes'].reverse()),('duplicate',lambda b:b['scopes'][1].__setitem__(0,b['scopes'][0][0])),('unknown_ID',lambda b:b['scopes'][0].__setitem__(0,'u063')),('row_width',lambda b:b['scopes'][0].append('extra'))]:reject('schedule_'+label,mutation)
for span in ([True,2,1],[1,2,True],[1.0,2,1],[1,'2',1],[-1,2,1],[1,1,1],[2,1,1],[1,999,1],[1,2,0],[1,2,10001],[1,2,2],[1,3,1],[1,2],[1,2,1,9]):reject('span_'+repr(span),lambda b,s=span:b['scopes'][0][4].__setitem__(0,s))
for value in ('Different valid reason','', ' ', 'x'*361, None):reject('reason_'+repr(value)[:35],lambda b,v=value:b['scopes'][0].__setitem__(3,v))
reject('evidence_order',lambda b:b['scopes'][0][4].reverse());reject('evidence_drop',lambda b:b['scopes'][0][4].pop());reject('evidence_empty',lambda b:b['scopes'][0].__setitem__(4,[]));reject('evidence_more_than_three',lambda b:b['scopes'][0].__setitem__(4,b['scopes'][0][4]*2))
reject('different_but_internally_valid_category_basis',lambda b:(b['scopes'][0].__setitem__(1,2),b['scopes'][0].__setitem__(2,2)))
check('frozen_scope_unmodified',canon(c)==frozen)
# A 64-unit schedule and maximum legal reason/quote lengths still roundtrip; fitting is a separate gate.
wide_ids=[f'u{i:03}' for i in range(1,65)];wide_source='z'*321
wide={'schema_version':codec.C_VERSION,'source_text_sha256':hashlib.sha256(wide_source.encode()).hexdigest(),'inventory_sha256':ih,'scopes':{i:{'category':codec.CATEGORIES[j%4],'basis':codec.BASES[j%4],'reason':'r'*360,'evidence':[{'quote':'z'*320,'occurrence':2}]} for j,i in enumerate(wide_ids)}}
check('64_unit_bound_exact_roundtrip',canon(codec.decode(codec.encode(wide,wide_source,ih,wide_ids),wide_source,ih,wide_ids,wide))==canon(wide))
# Reproduce original reviewer sizing independently of owner size_probes and owner encoder.
text=raw(ROUND/'source/26-19-016.txt').decode();source_hash=hashlib.sha256(text.encode()).hexdigest();record=load(ROUND/'candidate/candidate.json')
def project(x):
    if isinstance(x,dict):return {k:project(v) for k,v in x.items() if k not in ('evidence','coverage')}
    if isinstance(x,list):return [project(v) for v in x]
    return x
op=project(record);settings=load(P/'request-settings.json');aw=load(P/'inventory-wire-contract.json');bschema=load(P/'stage-b.schema.template.json')
def measure(user,schedule):
    schema=copy.deepcopy(bschema)
    substitutions={'__SOURCE_SHA256__':source_hash,'__RECORD_SHA256__':digest(record),'__OPERATIVE_SHA256__':digest(op),'__INVENTORY_SHA256__':user['inventory_sha256'],'__SCOPE_SHA256__':user['scope_sha256']}
    for a,b in substitutions.items():schema=json.loads(json.dumps(schema).replace(a,b))
    schema['properties']['mappings'].update(properties={uid:{'$ref':'#/$defs/m'} for uid in schedule},required=schedule)
    body=copy.deepcopy(settings);body.update(messages=[{'role':'system','content':prompt},{'role':'user','content':canon(user).decode()}],response_format={'type':'json_schema','json_schema':{'name':'source_mapping','strict':True,'schema':schema}})
    b=canon(body);return {'body_bytes':len(b),'guarded_bytes':len(b)+1024,'fits':len(b)+1024<=40000,'request_sha256':hashlib.sha256(b).hexdigest()}
profiles=[];owner_probes=load(P/'size-probes.json')
for entry in owner_probes['profiles']:
    n=entry['units'];schedule=[f'u{i:03}' for i in range(1,n+1)];units=[];scopes={};spans=[]
    for j,uid in enumerate(schedule):
        start=(j*59)%(len(text)-entry['quote_chars']);q=text[start:start+entry['quote_chars']];occ=sum(text.startswith(q,k) for k in range(start+1));ev={'quote':q,'occurrence':occ}
        units.append(dict(id=uid,kind='instruction',assertion='a'*entry['assertion_chars'],modality='informational',applicability='a'*entry['applicability_chars'],uncertainty='none',uncertainty_reason='',required_unit_ids=[],evidence=[ev]));spans.append([[start,start+len(q),occ]])
        scopes[uid]=dict(category='required_participation',basis='participation_function',reason='r'*entry['reason_chars'],evidence=[ev])
    inv=dict(schema_version='round12.source-inventory.v1',source_text_sha256=source_hash,units=units);scope=dict(schema_version=codec.C_VERSION,source_text_sha256=source_hash,inventory_sha256=digest(inv),scopes=scopes)
    awire=dict(schema_version=aw['schema_version'],source_text_sha256=source_hash,columns=aw['columns'],evidence_columns=aw['evidence_columns'],units=[[u[k] if k!='evidence' else spans[j] for k in aw['columns']] for j,u in enumerate(units)])
    swire=independent_wire(scope,text,schedule)
    check(f'size_exact_C_roundtrip_{entry["profile"]}_{n}',canon(codec.decode(swire,text,digest(inv),schedule,scope))==canon(scope))
    user=dict(source_text=text,source_text_sha256=source_hash,record_sha256=digest(record),operative_record=op,operative_record_sha256=digest(op),inventory_wire=awire,inventory_sha256=digest(inv),scope_wire=swire,scope_sha256=digest(scope))
    result=measure(user,schedule);check(f'independent_request_size_hash_{entry["profile"]}_{n}',result==entry['revised_scope_wire'])
    check(f'full_candidate_source_and_exact_fields_{entry["profile"]}_{n}',user['source_text']==text and canon(user['operative_record'])==canon(op) and set(user)==set(boundary['exact_user_fields']['B']))
    profiles.append({'profile':entry['profile'],'units':n,**result})
owner_runs={}
for label,args in [('static',[sys.executable,'-B',str(P/'authoring_checks.py')]),('codec',[sys.executable,'-B',str(P/'test_scope_codec.py')]),('sizes',[sys.executable,'-B',str(P/'size_probes.py')])]:
    run=subprocess.run(args,capture_output=True,text=True);owner_runs[label]={'exit_code':run.returncode,'stdout':run.stdout,'stderr':run.stderr};check('owner_run_'+label,run.returncode==0)
check('static_54_reproduced',json.loads(owner_runs['static']['stdout'])==load(P/'authoring-checks.json'))
check('owner_sizes_exact_reproduced',json.loads(owner_runs['sizes']['stdout'])==owner_probes)
check('owner_8_tests','Ran 8 tests' in owner_runs['codec']['stderr'] and 'OK' in owner_runs['codec']['stderr'])
check('input_closure_unchanged',all(hashlib.sha256((REPO/n).read_bytes()).hexdigest()==v['sha256'] for n,v in inputs.items()))
output={'schema_version':'round12.protocol-revised-review.checks.v1','checks_passed':sum(x['pass'] for x in rows),'checks_total':len(rows),'checks':rows,'input_pins':inputs,'independent_size_profiles':profiles,'owner_validation':{'static':54,'codec':8,'sizing_roundtrips':15,'all_exit_codes_zero':all(x['exit_code']==0 for x in owner_runs.values())},'record_canonical_sha256':digest(record),'operative_canonical_sha256':digest(op),'source_sha256':source_hash,'operative_canonical_bytes':len(canon(op)),'scope':'Protocol implementation barrier only; no provider/runtime release; size fillers not semantic truth or guaranteed complete-case fit.','reference_contents_read':False,'provider_calls':0}
print(json.dumps(output,indent=2))
if output['checks_passed']!=output['checks_total']:sys.exit(1)
