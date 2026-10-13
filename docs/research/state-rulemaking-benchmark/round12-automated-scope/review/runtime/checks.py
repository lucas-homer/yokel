"""Independent R12 offline runtime review; synthetic execution only, no credentials/signing/network."""
import ast, copy, hashlib, importlib.util, json, socket, subprocess, sys, tempfile, time
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent;ROUND=HERE.parent.parent;RT=ROUND/'runtime';BENCH=ROUND.parent;REPO=ROUND.parents[3]
PYTHON=Path('/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12')
rows=[];pins={}
def enc(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
    p=Path(p);assert not p.is_relative_to(ROUND/'reference') and not p.is_relative_to(ROUND/'candidate-audit');pins[str(p)]={'sha256':sha(p),'bytes':p.stat().st_size};return json.loads(p.read_bytes())
def check(name,ok):rows.append({'name':name,'pass':bool(ok)})
def package(folder):
    m=load(folder/'READY.json')
    for n,p in m['files'].items():check('package:'+str(folder.relative_to(ROUND))+'/'+n,sha(folder/n)==p['sha256'] and (folder/n).stat().st_size==p['bytes'])
    return m
ready=package(RT);package(ROUND/'protocol');package(ROUND/'review/protocol-revised');package(ROUND/'review/protocol')
check('reviewed_protocol',ready['protocol_ready_sha256']=='be674e8d2dc1240bc445acccdd4e70f52319584017e52ccb7649938cc679a7a9')
check('codec_byte_identical',sha(RT/'scope_codec.py')==sha(ROUND/'protocol/scope_codec.py'))
base=load(ROUND/'prior-baseline.json');targets=load(RT/'baseline-target-witness.json');dep=load(RT/'dependency-pins.json')['files'];old=load(BENCH/'round10-source-first/runtime/dependency-pins.json')['files'];transition=load(RT/'dependency-runtime-transition.json');codepins=load(RT/'code-pins.json')['files'];inputpins=load(RT/'input-pins.json')
check('R10_transition_inventory_pin',sha(BENCH/'round10-source-first/runtime/dependency-pins.json')==transition['R10_inventory_sha256'])
check('baseline_manifest_hard_pin',sha(ROUND/'prior-baseline.json')=='37fce781c7477b80a38dfcd323e2b44851837cfbd0e14bcface0846a91c3a205')
check('baseline_6829_unique_exact_witness',len(base['files'])==6829 and len({r['path'] for r in base['files']})==6829 and set(targets)=={r['path'] for r in base['files']})
bad=[];aliases=[]
for r in base['files']:
    path=BENCH/r['path'];resolved=path.resolve()
    if path.is_symlink():aliases.append({'path':r['path'],'relative_target':str(path.readlink()),'canonical_target':str(resolved),'sha256':r['sha256']})
    if Path(r['path']).is_absolute() or not resolved.is_relative_to(BENCH.resolve()) or str(resolved)!=targets[r['path']] or sha(resolved)!=r['sha256'] or dep.get(str(resolved))!=r['sha256']:bad.append(r['path'])
check('all_baseline_contents_targets_in_dependency_closure',not bad)
check('46_relative_PDF_aliases',len(aliases)==46 and all(x['path'].endswith('.pdf') and not Path(x['relative_target']).is_absolute() for x in aliases))
closure_bad=[];forbidden=[]
for p,h in dep.items():
    path=Path(p)
    if path.is_relative_to(ROUND/'reference') or path.is_relative_to(ROUND/'candidate-audit'):forbidden.append(p);continue
    if not path.is_absolute() or path.resolve()!=path or not path.is_file() or sha(path)!=h:closure_bad.append(p)
check('all_8586_dependency_pins_current_canonical',len(dep)==8586 and not closure_bad)
check('no_reference_or_candidate_audit_content_in_closure',not forbidden)
check('all_input_pins_in_base_closure_and_code_hashes_current',all(dep.get(p)==h==sha(p) for p,h in inputpins['files'].items()) and all(sha(p)==h for p,h in codepins.items()))
actual_changes={};missing=[];lost=[];nonpython_changes=[]
pyroot=PYTHON.parent.parent
for p,h in old.items():
    path=Path(p);current=sha(path) if path.is_file() else None
    if current!=h:actual_changes[p]={'R10_sha256':h,'R12_sha256':current}
    if current is None:missing.append(p)
    elif dep.get(str(path.resolve()))!=current:lost.append(p)
    if current!=h and not path.is_relative_to(pyroot):nonpython_changes.append(p)
check('transition_exact_553_changes',actual_changes=={p:{k:v[k] for k in ('R10_sha256','R12_sha256')} for p,v in transition['changed_files'].items()} and len(actual_changes)==553)
check('75_removed_bytecode_only',len(missing)==75 and all(p.endswith('.pyc') and '/__pycache__/' in p for p in missing))
check('all_existing_R10_paths_retained_current_hashes',not lost)
check('no_prior_core_executor_or_benchmark_content_changes',not nonpython_changes)
stdlib=pyroot/'lib/python3.12';stdlib_files={str(p.resolve()):sha(p) for p in stdlib.rglob('*') if p.is_file() and 'site-packages' not in p.relative_to(stdlib).parts}
check('full_current_stdlib_pinned',all(dep.get(p)==h for p,h in stdlib_files.items()))
# Load the inspected adapter and supplied annotation helper, never any live entry point.
sys.path.insert(0,str(RT));import adapter as a
c=a.c;k=a.k
spec=importlib.util.spec_from_file_location('owner_tests',RT/'test_runtime.py');owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
fixture=owner.Tests('test_17_strict_JSON');fixture.text,fixture.record,fixture.plans,prior=a.preflight()
check('independent_preflight_prior_debit',prior['prior_nanousd']==1182150718 and prior['baseline_files']==6829)
check('fixed_guards_unchanged',fixture.plans['D']['guarded_bytes']==28441 and fixture.plans['A']['guarded_bytes']==10205)
# Native whole-field inventory derived independently from the actual field layout.
rec=fixture.record;expected={};ids={}
def enumerate_item(item,ptr):
    ids[item['id']]=ptr
    for key,value in item.items():
        if key in ('id','evidence','coverage'):continue
        path=ptr+'/'+key
        if key in ('timing','components'):
            for i,child in enumerate(value):enumerate_item(child,path+'/'+str(i))
        else:expected[path]=value
for cat in ('events','routes','requirements','identities','uncertainties','alternative_groups'):
    for i,item in enumerate(rec[cat]):enumerate_item(item,f'/{cat}/{i}')
check('276_whole_fields_independent',len(expected)==276 and expected==load(RT/'operative-values.json') and sorted(expected)==load(RT/'operative-pointers.json'))
check('58_ID_container_bindings_independent',len(ids)==58 and ids==load(RT/'identity-witness.json'))
check('full_projection_exact',k.projection(rec)==load(RT/'operative-record.json') and k.projection(rec)['record_notes']==rec['record_notes'])
# Tamper each source-first receipt independently immediately before its freeze is rechecked.
for stage in ('A','C'):
    for receipt in a.RECEIPTS+('freeze',):
        original=a.freeze_write
        def tamper(run,name,*args,stage=stage,receipt=receipt):
            original(run,name,*args)
            if name==stage:
                target=run/f'stage-{name.lower()}-freeze.json' if receipt=='freeze' else run/f'stage-{name.lower()}'/receipt
                target.write_bytes(b'{}')
        with patch.object(a,'freeze_write',side_effect=tamper):run,calls,result=fixture.run_case()
        check(f'freeze_receipt_tamper_stops_{stage}_{receipt}',result is None and [n for n,_ in calls]==(['D','A'] if stage=='A' else ['D','A','C']) and not (run/'stage-b').exists())
# Failure accounting remains stage-local, including observations on unsuccessful HTTP calls.
for name in a.ORDER:
    def modify(n,obj,run,name=name):
        if n==name:obj['usage']['cost']=.2500000001;return 429,obj
        return 200,obj
    run,calls,result=fixture.run_case(modify=modify);ledger=c.read(run/'ledger.json');actual=next(x for x in ledger['operations'] if x['stage']==name)
    check('failed_http_cost_ceil_'+name,actual['budget_charge_nanousd']==250000001 and ledger['cumulative_budget_charge_nanousd']==a.PRIOR+sum(x['budget_charge_nanousd'] for x in ledger['operations']) and len(calls)<=4)
for amount,expectednano in [(0,0),(.0000000001,1),(.1619200001,161920001),(.25,250000000)]:check('cost_round_up_'+str(amount),a.cost_nano(amount)==expectednano)
# Stale valid C hash cannot bind B; model-supplied scope/mappings never establish semantics.
inv=fixture.inventory();scope=fixture.scope(inv);mapped=fixture.mapping(inv,scope);newscope=copy.deepcopy(scope);newscope['scopes']['u001']['reason']+=' changed'
try:k.validate_b(fixture.text,rec,inv,newscope,mapped)
except (ValueError,KeyError,TypeError):check('stale_complete_C_hash_denied',True)
else:check('stale_complete_C_hash_denied',False)
valid=k.validate_b(fixture.text,rec,inv,scope,mapped)
check('supplied_match_does_not_certify_semantics',all(valid[x]=='unverified' for x in ('semantic_status','source_inventory_completeness','whole_record_fidelity')) and not valid['production_eligible'] and not valid['action_ready'])
userC=c.strict(k.build_c(fixture.text,inv)['body']['messages'][1]['content']);userB=c.strict(k.build_b(fixture.text,rec,inv,scope)['body']['messages'][1]['content']);userD=c.strict(k.build_d(fixture.text,rec)['body']['messages'][1]['content'])
check('D_B_same_full_candidate_source',userD['operative_record']==userB['operative_record']==k.projection(rec) and userD['source_text']==userB['source_text']==fixture.text)
check('C_source_inventory_only_same_A_wire',set(userC)=={'source_text','source_text_sha256','inventory_wire','inventory_sha256'} and userC['inventory_wire']==userB['inventory_wire'])
check('full_C_wire_roundtrip_before_B',k.sc.decode(userB['scope_wire'],fixture.text,c.digest(inv),['u001'],scope)==scope and userB['scope_sha256']==c.digest(scope))
# Capture late-binding output in memory and validate only unchanged pure release functions.
release=REPO/'tools/research-credentials-stable/release.py';check('unchanged_release_validator_pin',sha(release)=='ca845ca805dbbb5fd428a06d63c735b4a326aa09100dcaeb0e913859069032a2')
tree=ast.parse(release.read_bytes());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'need','encode','digest','in_roots','validate'}];check('pure_validation_functions_only',len(nodes)==5)
ns={'Path':Path,'json':json,'hashlib':hashlib,'time':time};exec(compile(ast.Module(body=nodes,type_ignores=[]),'<pure-release-validators>','exec'),ns)
spec=importlib.util.spec_from_file_location('review_prep',RT/'prepare_bindings.py');prep=importlib.util.module_from_spec(spec);spec.loader.exec_module(prep)
core=load(BENCH/'runner-stability-review/deployment/core.json');captured={}
def capture(p,v):captured[str(p)]=copy.deepcopy(v)
def mockdigest(p):
    if str(p) in captured:return hashlib.sha256(enc(captured[str(p)])).hexdigest()
    if Path(p)==ROUND/'live-authorization.json':return hashlib.sha256(enc(a.authorization_fields())).hexdigest()
    return sha(p)
with patch.object(prep,'put',side_effect=capture),patch.object(prep,'digest',side_effect=mockdigest),patch.dict(ns,{'digest':mockdigest}):
    prepared=prep.prepare('synthetic-independent-review',int(time.time())+3600,HERE/'checks.py');proposal=captured[str(RT/'UNSIGNED-JOB-PROPOSAL.json')];ns['validate'](core,proposal)
    check('synthetic_proposal_passes_unchanged_validator',True)
    for label,mutate in [('over10000',lambda x:x['job']['files'].update({f'/not-used/{i}':'0'*64 for i in range(10001)})),('argv',lambda x:x['job']['argv'].__setitem__(1,'-E')),('budget',lambda x:x['budget'].update(reservation_nanousd=2000000000)),('reviewhash',lambda x:x['review'].update(sha256='0'*64)),('wrongpin',lambda x:x['job']['files'].__setitem__(str(PYTHON),'0'*64))]:
        bad=copy.deepcopy(proposal);mutate(bad)
        try:ns['validate'](core,bad)
        except ValueError:check('native_rejects_'+label,True)
        else:check('native_rejects_'+label,False)
check('late_binding_no_actual_files_created',not any((RT/n).exists() for n in ('dependencies.json','binding.json','UNSIGNED-JOB-PROPOSAL.json')) and not (ROUND/'live-authorization.json').exists())
check('late_binding_max4_fixed_budget',proposal['budget']=={'prior_nanousd':1182150718,'reservation_nanousd':647680000,'ceiling_nanousd':2000000000} and a.authorization_fields()['max_new_operations']==4 and proposal['provider_variables']==['OPENROUTER_API_KEY'])
check('all_runtime_code_pins_added_to_late_closure',all(proposal['job']['files'].get(p)==h for p,h in codepins.items()))
check('complete_late_closure_fits_native_limits',set(dep)<=set(proposal['job']['files']) and len(proposal['job']['files'])<=10000 and len(enc(proposal))<=4*1024*1024)
check('actual_review_pinned_in_synthetic_closure',proposal['review']['sha256']==sha(HERE/'checks.py')==proposal['job']['files'][str(HERE/'checks.py')])
# Owner reproduction uses synthetic temporary directories, no --record mutation.
run=subprocess.run([str(PYTHON),'-I','-S','-B',str(RT/'verify_offline.py')],capture_output=True,text=True,env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'})
check('read_only_owner_suite_33_pass',run.returncode==0 and json.loads(run.stdout)=={'passed':True,'test_methods':33,'dependency_files':8586,'provider_calls':0,'credentials_read':False})
fixture.doCleanups()
check('reviewed_manifests_unchanged',all(sha(p)==v['sha256'] for p,v in pins.items()))
check('all_runtime_artifacts_still_frozen',all(sha(RT/n)==p['sha256'] for n,p in ready['files'].items()))
result={'schema_version':'round12.runtime-independent-review.checks.v1','checks_passed':sum(x['pass'] for x in rows),'checks_total':len(rows),'checks':rows,'input_manifest_pins':pins,'full_dependency_files_verified':len(dep),'baseline_files_verified':len(base['files']),'baseline_relative_pdf_aliases_verified':len(aliases),'baseline_alias_details':aliases,'current_stdlib_files_verified':len(stdlib_files),'R10_runtime_transition_entries_verified':len(actual_changes),'removed_unused_bytecode_entries':len(missing),'current_existing_R10_paths_preserved':len(old)-len(missing),'native_synthetic_proposal_dependency_files':len(proposal['job']['files']),'native_synthetic_proposal_bytes':len(enc(proposal)),'owner_readonly_reproduction':json.loads(run.stdout) if run.returncode==0 else {'exit_code':run.returncode,'stderr':run.stderr},'paid_calls':0,'credentials_read':False,'signer_executor_invoked':False,'reference_or_candidate_audit_contents_read':False,'semantic_validation':'Host structure and supplied annotations only; not discovery or semantic equivalence.'}
print(json.dumps(result,indent=2))
if result['checks_passed']!=result['checks_total']:sys.exit(1)
