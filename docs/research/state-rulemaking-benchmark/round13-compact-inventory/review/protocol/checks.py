"""Independent R13 protocol review. Read-only owners; sizing regenerated only in scratch."""
import copy,hashlib,importlib.util,json,math,shutil,subprocess,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROUND=HERE.parent.parent;P=ROUND/'protocol';REPO=ROUND.parents[3]
rows=[];pins={};skipped=[]
def read(p):
    p=Path(p);assert 'reference' not in p.parts and 'candidate-audit' not in p.parts
    b=p.read_bytes();pins[str(p)]={'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)};return b
def load(p):return json.loads(read(p))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canon(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def check(name,ok):rows.append({'name':name,'pass':bool(ok)})
ready=load(P/'READY.json');scope=load(ROUND/'scope.json')
for name,pin in ready['files'].items():b=read(P/name);check('protocol_pin:'+name,hashlib.sha256(b).hexdigest()==pin['sha256'] and len(b)==pin['bytes'])
for name,pin in ready['consulted_inputs'].items():
    if 'reference' in Path(name).parts or 'candidate-audit' in Path(name).parts:skipped.append(name);continue
    path=REPO/name
    # Pin-only check, not reading consulted semantic/design prose for this review.
    check('consulted_pin:'+name,sha(path)==pin['sha256'] and path.stat().st_size==pin['bytes'])
source=read(Path(scope['source_path'])).decode();check('exact_R12_source_binding',hashlib.sha256(source.encode()).hexdigest()==scope['source_sha256']=='7cf8d7a924724d7fc80c80e5b4337c2114585668feef5edb14f49a75aec4d437')
check('one_call_budget_scope',scope['max_new_calls']==1 and scope['prior_nanousd']==1505990718 and scope['reservation_nanousd']==200000000 and scope['ceiling_nanousd']==2000000000 and 1505990718+200000000==1705990718<2000000000)
check('unchanged_caps_no_retry',scope['max_output_tokens']==8192 and scope['guarded_request_bytes_max']==40000 and scope['retry'] is scope['repair'] is scope['fallback'] is False)
check('initial_checklist_preserved',sha(ROUND/'review/CHECKLIST.md')=='280d4d3fb86f3470596562f5116845dce39d72e6920793df1ebee9138105c889')
spec=importlib.util.spec_from_file_location('compact_reviewed',P/'compact.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
plan=m.build(source);table=m.span_table(source);schema=m.schema(source,table)
check('fixed_host_table_exact',table==load(P/'span-table.json') and len(table['rows'])==37)
check('whole_source_reconstructed_from_supplied_row_text',''.join(row[3] for row in table['rows']).encode()==source.encode())
check('host_ID_order_offsets_and_literal_slices',all(row[0]==f's{i+1}' and row[3]==source[row[1]:row[2]] and row[1]==(0 if i==0 else table['rows'][i-1][2]) for i,row in enumerate(table['rows'])) and table['rows'][-1][2]==len(source))
check('exact_source_instantiated_schema',schema==load(P/'schema.json'))
check('exact_offline_request_bytes_hash',canon(plan['body'])==read(P/'offline-request.json') and plan['request_sha256']==sha(P/'offline-request.json'))
check('guard_15692_full_serialized',plan['body_bytes']==len(canon(plan['body']))==14668 and plan['guarded_bytes']==15692)
user=json.loads(plan['body']['messages'][1]['content'])
check('source_only_four_field_input',set(user)=={'source_text','source_text_sha256','span_table','span_table_sha256'} and user['source_text']==source and user['span_table']==table and user['span_table_sha256']==m.digest(table))
check('GPT_OpenAI_nominal_caps',plan['body']['model']=='openai/gpt-6.1-sol' and plan['body']['reasoning']=={'effort':'low'} and plan['body']['max_tokens']==8192 and plan['body']['provider']=={'allow_fallbacks':False,'max_price':{'completion':10,'prompt':2},'only':['openai'],'order':['openai'],'require_parameters':True})
def schema_walk(s):
    allowed={'type','properties','required','additionalProperties','minimum','maximum','minLength','maxLength','items','minItems','maxItems','enum'}
    check('closed_schema_supported_keywords',not set(s)-allowed)
    if s.get('type')=='object':
        check('schema_all_fields_required_no_defaults',s['additionalProperties'] is False and set(s['required'])==set(s['properties']))
        for v in s['properties'].values():schema_walk(v)
    if 'items' in s:schema_walk(s['items'])
schema_walk(schema)
# Independent adverse controls use only invented tiny sources, never prior model prefixes.
s='🫧é\r\nrepeat\nrepeat\n\nlast e\u0301';t=m.span_table(s)
v=dict(v='r13.1',h=m.source_hash(s),t=m.digest(t),z='END',u=[dict(i=160,k=4,s='Endpoint literal.',m=0,c='',d=[],b=[],e=['s2','s3'],q=0,r=''),dict(i=2,k=5,s='Actor uses endpoint for a single purpose.',m=2,c='if eligible',d=[160],b=[],e=['s1'],q=0,r=''),dict(i=8,k=7,s='Synthetic relation of members.',m=0,c='',d=[],b=[160,2],e=['s5'],q=0,r='')])
check('gapped_ID160_and_explicit_defaults_roundtrip',canon(m.contract(m.expand(v,s,t),s,t))==canon(v))
expanded=m.expand(v,s,t);check('repeat_occurrence_unicode_exact',[(e['quote'],e['occurrence']) for e in expanded['units'][0]['evidence']]==[('repeat\n',1),('repeat\n',2)])
check('no_certainty_from_empty_default',expanded['units'][0]['applicability']=='' and expanded['units'][0]['required_unit_ids']==[] and expanded['source_inventory_completeness']=='unverified' and expanded['production_eligible'] is False and expanded['action_ready'] is False)
for sep in ['\n','\r','\r\n','\v','\f','\x1c','\x1d','\x1e','\x85','\u2028','\u2029']:
    sample='😀e\u0301'+sep+sep+'é'+sep+'tail';st=m.span_table(sample)
    check('exact_separator_'+repr(sep),m.reconstruct(sample,st)==sample and ''.join(r[3] for r in st['rows'])==sample and st==m.span_table(sample))
def reject(name,change):
    bad=copy.deepcopy(v);change(bad)
    try:m.validate(bad,s,t)
    except (ValueError,TypeError,KeyError):check(name,True)
    else:check(name,False)
for key in m.UNIT_KEYS:reject('missing_field_'+key,lambda b,k=key:b['u'][0].pop(k))
for key in ['i','k','m','q']:
    for value in [True,0.0,'1',None,-1,999]:reject('integer_'+key+'_'+repr(value),lambda b,k=key,x=value:b['u'][0].__setitem__(k,x))
for name,change in [
 ('unknown_evidence',lambda b:b['u'][0].update(e=['s999'])),('empty_evidence',lambda b:b['u'][0].update(e=[])),('duplicate_evidence',lambda b:b['u'][0].update(e=['s1','s1'])),('unknown_dependency',lambda b:b['u'][0].update(d=[99])),('self_dependency',lambda b:b['u'][0].update(d=[160])),('dependency_cycle',lambda b:b['u'][0].update(d=[2])),('duplicate_dependency',lambda b:b['u'][1].update(d=[160,160])),('boolean_dependency',lambda b:b['u'][1].update(d=[True])),('unknown_member',lambda b:b['u'][2].update(b=[160,99])),('self_member',lambda b:b['u'][2].update(b=[160,8])),('duplicate_member',lambda b:b['u'][2].update(b=[160,160])),('too_few_members',lambda b:b['u'][2].update(b=[160])),('members_nonrelationship',lambda b:b['u'][0].update(b=[2,8])),('role_no_endpoint',lambda b:b['u'][1].update(d=[])),('role_wrong_first_type',lambda b:b['u'][1].update(d=[8,160])),('duplicate_unit',lambda b:b['u'][1].update(i=160)),('unknown_force_certain',lambda b:b['u'][0].update(m=5)),('q0_reason',lambda b:b['u'][0].update(r='reason')),('q1_no_reason',lambda b:b['u'][0].update(q=1)),('whitespace_condition',lambda b:b['u'][0].update(c=' ')),('long_assertion',lambda b:b['u'][0].update(s='s'*281)),('long_condition',lambda b:b['u'][0].update(c='c'*181)),('long_reason',lambda b:b['u'][0].update(q=1,r='r'*181)),('stale_source',lambda b:b.update(h='0'*64)),('stale_table',lambda b:b.update(t='0'*64)),('no_END',lambda b:b.update(z='')),('extra_envelope',lambda b:b.update(extra=1))]:reject(name,change)
uncertain=copy.deepcopy(v);uncertain['u'][0].update(m=5,q=2,r='Unresolved external source reference.')
check('explicit_unknown_force_reference_preserved',m.expand(uncertain,s,t)['units'][0]['uncertainty']=='reference_unresolved')
cyclic=copy.deepcopy(v);cyclic['u'].append(dict(i=9,k=7,s='Separate member relation.',m=0,c='',d=[],b=[8,2],e=['s1'],q=0,r=''));cyclic['u'][2]['b']=[9,160]
check('member_cycles_not_prerequisite_cycles',m.validate(cyclic,s,t)==cyclic)
for n,want in [(159,True),(160,False),(161,False)]:
    cap=copy.deepcopy(v);cap['u']=[dict(i=i,k=8,s='Synthetic.',m=0,c='',d=[],b=[],e=['s1'],q=0,r='') for i in range(1,n+1)]
    try:m.validate(cap,s,t);accepted=True
    except ValueError:accepted=False
    check('capacity_'+str(n),accepted==want)
for key,value in [('quote','different'),('start',0),('end',0),('occurrence',True),('start',float(expanded['units'][0]['evidence'][0]['start']))]:
    bad=copy.deepcopy(expanded);bad['units'][0]['evidence'][0][key]=value
    try:m.contract(bad,s,t)
    except (ValueError,TypeError,KeyError):check('inverse_altered_'+key+'_'+repr(value),True)
    else:check('inverse_altered_'+key+'_'+repr(value),False)
for key,value in [('production_eligible',0),('action_ready',True),('source_inventory_completeness','complete')]:
    bad=copy.deepcopy(expanded);bad[key]=value
    try:m.contract(bad,s,t)
    except ValueError:check('inverse_flags_'+key,True)
    else:check('inverse_flags_'+key,False)
for raw in ['{"v":1,"v":2}','{"u":[{"i":1,"i":2}]}','NaN','Infinity','1e999','{} trailing',canon(v).decode()[:-1]]:
    try:m.strict_load(raw)
    except (ValueError,TypeError):check('strict_reject_'+raw[:30],True)
    else:check('strict_reject_'+raw[:30],False)
for finish in ['length','tool_calls','content_filter',None]:
    try:m.validate_response(canon(v).decode(),finish,s,t)
    except ValueError:check('nonstop_reject_'+str(finish),True)
    else:check('nonstop_reject_'+str(finish),False)
for mutate in [lambda x:x['rows'][0].__setitem__(1,True),lambda x:x['rows'][0].__setitem__(3,'changed'),lambda x:x['rows'].reverse(),lambda x:x.update(v='other')]:
    bad=copy.deepcopy(t);mutate(bad)
    try:m.validate(v,s,bad)
    except ValueError:check('table_mutation_rejected',True)
    else:check('table_mutation_rejected',False)
# No reference to owner ROOT is changed. Run writing sizing script in a temporary clone.
owner_test=subprocess.run([sys.executable,'-B',str(P/'test_compact.py')],capture_output=True,text=True)
check('owner_13_tests_pass',owner_test.returncode==0 and 'Ran 13 tests' in owner_test.stderr and 'OK' in owner_test.stderr)
with tempfile.TemporaryDirectory() as temp:
    base=Path(temp);scratch=base/'round13-compact-inventory/protocol';scratch.mkdir(parents=True)
    for name in ready['files']:shutil.copyfile(P/name,scratch/name)
    sourcecopy=base/'round12-automated-scope/source/26-19-016.txt';sourcecopy.parent.mkdir(parents=True);sourcecopy.write_bytes(source.encode())
    run=subprocess.run([sys.executable,'-B',str(scratch/'offline_checks.py')],capture_output=True,text=True)
    check('scratch_offline_sizing_reproduction',run.returncode==0)
    for name in ['span-table.json','schema.json','offline-request.json','offline-results.json','representative32.json','representative64.json','stressed96.json','stressed128.json']:check('exact_regenerated_'+name,sha(scratch/name)==sha(P/name))
results=load(P/'offline-results.json');sizes=[]
for profile in results['profiles']:
    obj=load(P/(profile['name']+'.json'));raw=canon(obj)
    check('fixture_roundtrip_'+profile['name'],canon(m.contract(m.expand(obj,source,table),source,table))==raw)
    check('fixture_byte_hash_'+profile['name'],len(raw)==profile['full_output_bytes'] and hashlib.sha256(raw).hexdigest()==profile['compact_sha256'])
    for ratio in [2,3,4]:check('independent_ratio_'+profile['name']+'_'+str(ratio),math.ceil(len(raw)/ratio)+256==profile['estimates_bytes_per_token'][str(ratio)]['estimated_tokens_including_reasoning_allowance'])
    sizes.append({'name':profile['name'],'bytes':len(raw),'tokens_at_2_plus256':math.ceil(len(raw)/2)+256,'tokens_at_3_plus256':math.ceil(len(raw)/3)+256})
by={p['name']:p for p in sizes}
check('primary_3byte_policy_rep64_pass',by['representative64']['tokens_at_3_plus256']/8192<=.70)
check('primary_3byte_policy_stress96_pass',by['stressed96']['tokens_at_3_plus256']/8192<=.85)
check('2byte_stress96_fails_headroom',by['stressed96']['tokens_at_2_plus256']/8192>.85)
check('3byte_stress128_exceeds_cap',by['stressed128']['tokens_at_3_plus256']>8192)
check('all_read_inputs_unchanged',all(sha(p)==pin['sha256'] for p,pin in pins.items()))
check('all_protocol_artifacts_unchanged',all(sha(P/name)==pin['sha256'] for name,pin in ready['files'].items()))
result={'schema_version':'round13.protocol-independent-review.checks.v1','checks_passed':sum(x['pass'] for x in rows),'checks_total':len(rows),'checks':rows,'input_pins':pins,'consulted_reference_paths_not_read_or_hash_verified':skipped,'owner_test_methods_passed':13,'scratch_sizing_regeneration_exact':True,'source_spans':37,'request_body_bytes':14668,'request_guarded_bytes':15692,'sizing':sizes,'recommended_disposition':'APPROVED_FOR_RUNTIME_IMPLEMENTATION','primary_policy_freeze_required':'Before paid release, explicitly freeze 3 bytes/token +256 engineering estimate, representative64 <=70%, stressed96 <=85%; preserve adverse2byte96 and3byte128 results. No guaranteed fit or semantic cap.','evaluation_gold_or_reference_contents_read':False,'R12_truncated_prefix_read_in_this_review':False,'provider_calls':0,'credentials_read':False,'signer_executor_invoked':False,'provider_compatibility':'unverified','production_eligible':False,'action_ready':False}
print(json.dumps(result,indent=2))
if result['checks_passed']!=result['checks_total']:sys.exit(1)
