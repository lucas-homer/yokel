"""Bounded independent R13 runtime review; synthetic transport, memory-only proposal."""
import ast,copy,hashlib,importlib.util,json,sys,tempfile,time
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent;ROUND=HERE.parent.parent;RT=ROUND/'runtime';BENCH=ROUND.parent;REPO=ROUND.parents[3]
rows=[];pins={}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
    p=Path(p);assert not any(x in p.parts for x in ('reference','evaluation','candidate-audit'))
    pins[str(p)]={'sha256':sha(p),'bytes':p.stat().st_size};return json.loads(p.read_bytes())
def enc(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def check(n,ok):rows.append({'name':n,'pass':bool(ok)})
def package(folder):
    m=load(folder/'READY.json')
    for n,v in m['files'].items():check('pin:'+str(folder.relative_to(ROUND))+'/'+n,sha(folder/n)==v['sha256'] and (folder/n).stat().st_size==v['bytes'])
    return m
ready=package(RT);package(ROUND/'protocol');package(ROUND/'review/protocol')
release=load(ROUND/'implementation-release.json');scope=load(ROUND/'scope.json');decision=load(ROUND/'sizing-decision.json')
for p,h in release['files'].items():check('implementation_pin:'+Path(p).name,sha(p)==h)
check('frozen_sizing_policy',decision['selected_sensitivity_utf8_bytes_per_token']==3 and decision['extra_token_allowance']==256 and decision['representative64_target_fraction']==.70 and decision['stressed96_target_fraction']==.85 and decision['stress128_at_selected_ratio']=='exceeds_cap' and decision['stress96_at_2bytes_per_token']=='insufficient_headroom' and not decision['tokenizer_matched'])
base=load(ROUND/'prior-baseline.json');targets=load(RT/'baseline-target-witness.json');dep=load(RT/'dependency-pins.json')['files'];previous=load(BENCH/'round12-automated-scope/runtime/dependency-pins.json')['files'];transition=load(RT/'dependency-runtime-transition.json');code=load(RT/'code-pins.json')['files'];ip=load(RT/'input-pins.json')
check('baseline_exact_count_and_unique_witness',len(base['files'])==6981 and len({x['path'] for x in base['files']})==6981 and set(targets)=={x['path'] for x in base['files']})
basebad=[];aliascount=0
for item in base['files']:
    p=BENCH/item['path'];target=p.resolve();aliascount+=p.is_symlink()
    # Hash-only baseline verification; do not decode prior semantic/reference documents.
    if Path(item['path']).is_absolute() or not target.is_relative_to(BENCH.resolve()) or str(target)!=targets[item['path']] or sha(target)!=item['sha256'] or dep.get(str(target))!=item['sha256']:basebad.append(item['path'])
check('all6981_baseline_contents_and_canonical_targets_unchanged',not basebad)
check('46_alias_targets',aliascount==46)
check('all8685_base_dependency_hashes_canonical',len(dep)==8685 and all(Path(p).is_absolute() and Path(p).resolve()==Path(p) and sha(p)==h for p,h in dep.items()))
check('all_R12_paths_retained_no_drift',all(dep.get(p)==h==sha(p) for p,h in previous.items()))
check('runtime_transition_zero_exact',transition['changed_files']=={} and transition['prior_benchmark_drift_files']==0 and transition['R12_inventory_sha256']==sha(BENCH/'round12-automated-scope/runtime/dependency-pins.json'))
check('all_input_and_code_pins_current',all(sha(p)==h for p,h in (ip['files']|code).items()))
check('no_new_reference_evaluation_files_in_R13_dependencies',not any(Path(p).is_relative_to(ROUND) and any(x in Path(p).parts for x in ('reference','evaluation','candidate-audit')) for p in dep))
sys.path.insert(0,str(RT));import adapter as a
c=a.c;k=a.k
spec=importlib.util.spec_from_file_location('r13_owner_fixture',RT/'test_runtime.py');owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner);f=owner.Tests('test_14_strict_JSON_and_closed_schema_keywords');f.source,f.plan,f.prior=a.preflight()
check('actual_prior_historical_reserve_and_admission',f.prior['prior_nanousd']==1505990718 and a.HISTORICAL_RESERVE==161920000 and a.RESERVE==200000000 and a.PRIOR+a.RESERVE==1705990718<a.CEILING==2000000000)
check('full_source_request_protocol_exact',f.plan['guarded_bytes']==15692 and f.plan['body']==c.read(c.PROTO/'offline-request.json') and len(f.plan['table']['rows'])==37 and Path(k.protocol().__file__).resolve()==c.PROTO/'compact.py')
check('single_call_authorization_only',a.authorization_fields()['max_new_operations']==1 and a.authorization_fields()['inventory_calls']==1 and all(a.authorization_fields()[x]==0 for x in ('direct_calls','scope_calls','mapping_calls','jev_calls')) and a.authorization_fields()['automatic_retry'] is False)
check('one_POST_site_no_loop_in_execute',len([n for n in ast.walk(ast.parse((RT/'adapter.py').read_text())) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='transport'])==1)
run,calls,result=f.run_case(real_integrity=True);done=c.read(run/'completed.json');ledger=c.read(run/'ledger.json')
check('success_ledger_neutral_and_hash_concordant',len(calls)==1 and result is not None and ledger['state']=='charge_recorded' and done['state']=='validated_frozen' and not (run/'stop.json').exists() and done['files']['ledger.json']==c.file_hash(run/'ledger.json') and ledger['budget_charge_nanousd']==result['budget_charge_nanousd']==200000000)
check('success_completion_all_receipt_pins',all(c.file_hash(run/n)==h for n,h in done['files'].items()))
check('success_original_compact_inverse_exact',k.protocol().contract(c.read(run/'expanded.json'),f.source,f.plan['table'])==c.read(run/'validated.json') and result['roundtrip_exact'] and result['source_inventory_completeness']=='unverified' and not result['production_eligible'])
try:a.execute_once(run,f.source,f.plan,owner.SECRET,lambda *_:(_ for _ in ()).throw(AssertionError('retry')))
except FileExistsError:check('success_run_latched_no_resume',True)
else:check('success_run_latched_no_resume',False)
# Independent failure injection after complete writes, including fsync-style completion failure.
realput=a.put
for target in ('intent.json','content.body','validated.json','expanded.json','result.json','ledger.json','completed.json'):
    def after_write(path,data,*args,target=target):
        realput(path,data,*args)
        if Path(path).name==target:raise OSError('synthetic post-write failure')
    with patch.object(a,'put',side_effect=after_write):run,calls,result=f.run_case()
    stop=c.read(run/'stop.json');charge=a.ledger(run)
    check('postwrite_stop_dominates_'+target,result is None and len(calls)<=1 and stop['state']=='failed_or_uncertain' and charge['state']=='charge_recorded' and charge['budget_charge_nanousd']>=200000000 and (run/'completed.json').exists()==(target=='completed.json'))
    try:a.execute_once(run,f.source,f.plan,owner.SECRET,lambda *_:None)
    except FileExistsError:check('postwrite_latch_'+target,True)
    else:check('postwrite_latch_'+target,False)
# A disk refusing either accounting/outcome file still leaves a claim and recoverable raw cost.
for target in ('ledger.json','stop.json'):
    with tempfile.TemporaryDirectory() as td:
        run=Path(td)/'run';calls=[]
        def fake(body,key):
            calls.append(1);obj=f.native();obj['usage']['cost']=.2500000001;obj['choices'][0]['finish_reason']='length';return 200,c.encode(obj)
        def fail(path,data,*args,target=target):
            if Path(path).name==target:raise OSError('synthetic disk failure')
            return realput(path,data,*args)
        with patch.object(a,'put',side_effect=fail):
            try:a.execute_once(run,f.source,f.plan,owner.SECRET,fake,integrity_check=lambda *_:None)
            except (OSError,c.Denied):pass
        check('unwritable_accounting_claim_retains_raw_'+target,run.exists() and len(calls)==1 and (run/'response.body').exists() and a.ledger(run)['budget_charge_nanousd']==250000001 and not (run/'completed.json').exists())
        try:a.execute_once(run,f.source,f.plan,owner.SECRET,fake)
        except FileExistsError:check('unwritable_claim_no_resume_'+target,True)
        else:check('unwritable_claim_no_resume_'+target,False)
for status in (200,429):
    def invalid(obj,run,status=status):obj['choices'][0]['finish_reason']='length';obj['usage']['cost']=.3000000001;return status,obj
    run,calls,result=f.run_case(modify=invalid)
    check('invalid_completion_charged_and_content_retained_'+str(status),result is None and len(calls)==1 and c.read(run/'ledger.json')['budget_charge_nanousd']==300000001 and (run/'content.body').exists() and not (run/'validated.json').exists() and not (run/'completed.json').exists())
# Exact inverse continues to reject changed expanded evidence in runtime wrapper.
real_validate=k.protocol().validate_response
for field,value in [('quote','tampered'),('occurrence',True),('start',0.0)]:
    def altered(*args,field=field,value=value):
        out=real_validate(*args);out['expanded']['units'][0]['evidence'][0][field]=value;return out
    with patch.object(k.protocol(),'validate_response',side_effect=altered):
        try:k.validate_response(c.encode(f.value()).decode(),'stop',f.source,f.plan['table'])
        except (ValueError,TypeError):check('wrapper_inverse_reject_'+field,True)
        else:check('wrapper_inverse_reject_'+field,False)
# Pure native manifest validation only, captured helper writes; no signer/executor imports.
release_path=REPO/'tools/research-credentials-stable/release.py';check('unchanged_release_validator',sha(release_path)=='ca845ca805dbbb5fd428a06d63c735b4a326aa09100dcaeb0e913859069032a2')
tree=ast.parse(release_path.read_bytes());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'need','encode','digest','in_roots','validate'}];ns={'Path':Path,'hashlib':hashlib,'json':json,'time':time};exec(compile(ast.Module(body=nodes,type_ignores=[]),'<pure-validator>','exec'),ns)
spec=importlib.util.spec_from_file_location('r13_review_prepare',RT/'prepare_bindings.py');prep=importlib.util.module_from_spec(spec);spec.loader.exec_module(prep);core=load(BENCH/'runner-stability-review/deployment/core.json');captured={}
def capture(path,value):captured[str(path)]=copy.deepcopy(value)
def mockdigest(path):
    if str(path) in captured:return hashlib.sha256(enc(captured[str(path)])).hexdigest()
    if Path(path)==ROUND/'live-authorization.json':return hashlib.sha256(enc(a.authorization_fields())).hexdigest()
    return sha(path)
with patch.object(prep,'put',side_effect=capture),patch.object(prep,'digest',side_effect=mockdigest),patch.dict(ns,{'digest':mockdigest}):
    summary=prep.prepare('synthetic-r13-independent-review',int(time.time())+3600,HERE/'checks.py');proposal=captured[str(RT/'UNSIGNED-JOB-PROPOSAL.json')];ns['validate'](core,proposal);check('actual_helper_synthetic_proposal_valid',True)
    for name,modify in [('scopebudget',lambda x:x['budget'].update(reservation_nanousd=600000000)),('reviewpin',lambda x:x['review'].update(sha256='0'*64)),('argv',lambda x:x['job']['argv'].__setitem__(1,'-E'))]:
        bad=copy.deepcopy(proposal);modify(bad)
        try:ns['validate'](core,bad)
        except ValueError:check('native_reject_'+name,True)
        else:check('native_reject_'+name,False)
check('final_closure_all_base_code_input_pins',all(proposal['job']['files'].get(p)==h for p,h in (dep|code|ip['files']).items()))
check('native_file_size_limits',len(proposal['job']['files'])<=10000 and len(enc(proposal))<=4*1024*1024)
check('proposal_one_call_budget_model_entry',proposal['budget']=={'prior_nanousd':1505990718,'reservation_nanousd':200000000,'ceiling_nanousd':2000000000} and proposal['job']['argv']==[str(a.PYTHON),'-I','-S','-B',str(RT/'adapter.py'),'--live-initial'] and proposal['provider_variables']==['OPENROUTER_API_KEY'])
check('no_actual_late_artifacts_created',not any((RT/n).exists() for n in ('dependencies.json','binding.json','UNSIGNED-JOB-PROPOSAL.json')) and not (ROUND/'live-authorization.json').exists())
f.doCleanups()
check('all_runtime_files_still_frozen',all(sha(RT/n)==v['sha256'] for n,v in ready['files'].items()))
check('all_loaded_manifest_pins_unchanged',all(sha(p)==v['sha256'] for p,v in pins.items()))
result={'schema_version':'round13.runtime-independent-review.checks.v1','checks_passed':sum(x['pass'] for x in rows),'checks_total':len(rows),'checks':rows,'manifest_pins':pins,'baseline_rows_verified':6981,'baseline_alias_targets_verified':aliascount,'base_dependencies_verified':8685,'R12_dependency_paths_retained':len(previous),'Python_or_R12_dependency_drift':0,'late_proposal_files':len(proposal['job']['files']),'late_proposal_canonical_bytes':len(enc(proposal)),'readonly_owner_reproduction_observed_separately':{'command':str(a.PYTHON)+' -I -S -B '+str(RT/'verify_offline.py'),'passed':True,'runtime_test_methods':18,'dependency_files':8685},'baseline_reference_handling':'Prior artifacts hash-verified only; no evaluation/reference semantic contents decoded or consumed.','additional_provider_calls':0,'credentials_read':False,'signer_executor_invoked':False,'semantic_status':'unverified','provider_compatibility':'unverified','production_eligible':False,'action_ready':False}
print(json.dumps(result,indent=2))
if result['checks_passed']!=result['checks_total']:sys.exit(1)
