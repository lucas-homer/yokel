"""Read-only postrun audit; no private key, credentials, signer, executor or provider calls."""
import ast,base64,datetime,hashlib,json,subprocess,sys,tempfile,types
from decimal import Decimal
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROUND=HERE.parent.parent;RT=ROUND/'runtime';RUN=ROUND/'execution/run';BENCH=ROUND.parent;REPO=ROUND.parents[3]
rows=[];inputs={}
def read(p):
    p=Path(p);assert not p.is_relative_to(ROUND/'reference') and not p.is_relative_to(ROUND/'candidate-audit')
    b=p.read_bytes();inputs[str(p)]={'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)};return b
def load(p):return json.loads(read(p))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def enc(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def check(name,ok):rows.append({'name':name,'pass':bool(ok)})
def package(folder):
    m=load(folder/'READY.json')
    for n,v in m['files'].items():check('pin:'+str(folder.relative_to(ROUND))+'/'+n,sha(folder/n)==v['sha256'] and (folder/n).stat().st_size==v['bytes'])
    return m
ready=package(RT);package(ROUND/'review/runtime');package(ROUND/'review/protocol-revised')
check('runtime_freeze_unchanged',sha(RT/'READY.json')=='572124980bb9793d34c22902f83c32e5850f96c53dd861b7084051d41712c29c')
execution=load(ROUND/'execution/READY.json')
for n,v in execution['files'].items():check('execution_pin:'+n,sha(RUN/n)==v['sha256'] and (RUN/n).stat().st_size==v['bytes'])
check('execution_freeze_exhaustive',set(execution['files'])=={str(p.relative_to(RUN)) for p in RUN.rglob('*') if p.is_file()})
proposal=load(RT/'UNSIGNED-JOB-PROPOSAL.json');deps=load(RT/'dependencies.json');binding=load(RT/'binding.json');auth=load(ROUND/'live-authorization.json');released=load(ROUND/'release-receipt.json');primary=load(ROUND/'primary-release-verification.json')
core=load(BENCH/'runner-stability-review/deployment/core.json');stem=Path(core['registry_dir'])/'round12-automated-scope-initial';manifest_bytes=read(stem.with_suffix('.json'));manifest=json.loads(manifest_bytes);signature=read(stem.with_suffix('.sig'));claim=read(Path(core['journal_dir'])/'round12-automated-scope-initial').decode().strip()
manifest_hash=hashlib.sha256(manifest_bytes).hexdigest()
check('exact_released_canonical_proposal',manifest==proposal and manifest_bytes==enc(proposal))
check('release_receipt_and_native_claim_bound',manifest_hash==released['manifest_sha256']==primary['manifest_canonical_sha256']==claim)
check('native_release_receipt_success',released['state']=='released' and released['release_exit_code']==0 and released['native_check_passed'] is True and released['provider_calls']==0 and released['credential_access'] is False)
check('primary_proposal_file_pin',sha(RT/'UNSIGNED-JOB-PROPOSAL.json')==primary['proposal_sha256'])
check('primary_runtime_review_pins',primary['runtime_ready_sha256']==sha(RT/'READY.json') and primary['review_ready_sha256']==sha(ROUND/'review/runtime/READY.json'))
check('unchanged_native_executor_bytes',sha('/Users/home/.local/libexec/yokel/research-credentials-stable-v1')==primary['executor_sha256']=='821f91b67f4c0c2d2a7f333e1381fab9aec1f9d8a9b8be8c34a0ee135494547e')
# Public-only P-256 verification, independent of the signer/executor. No private material is read.
public=base64.b64decode(core['public_key_base64']);check('public_P256_uncompressed_shape',len(public)==65 and public[0]==4)
with tempfile.TemporaryDirectory() as td:
    td=Path(td);(td/'public.der').write_bytes(bytes.fromhex('3059301306072a8648ce3d020106082a8648ce3d030107034200')+public);(td/'message').write_bytes(b'yokel.research-job.v1\0'+manifest_bytes);(td/'signature').write_bytes(signature)
    verified=subprocess.run(['/usr/bin/openssl','dgst','-sha256','-keyform','DER','-verify',str(td/'public.der'),'-signature',str(td/'signature'),str(td/'message')],capture_output=True,text=True)
    check('detached_signature_public_verification',verified.returncode==0 and 'Verified OK' in verified.stdout)
check('actual_manifest_count_size_bounds',len(proposal['job']['files'])==8606 and len(manifest_bytes)<=4*1024*1024 and len(proposal['job']['files'])<=10000)
bad=[];forbidden=[]
for p,h in proposal['job']['files'].items():
    path=Path(p)
    if path.is_relative_to(ROUND/'reference') or path.is_relative_to(ROUND/'candidate-audit'):forbidden.append(p);continue
    if not path.is_absolute() or path.resolve()!=path or sha(path)!=h:bad.append(p)
check('all_8606_actual_release_file_pins_match',not bad and not forbidden)
check('dependencies_binding_scope_authorization_pins',binding=={'schema_version':'round12.automated-scope.binding.v1','dependencies_sha256':sha(RT/'dependencies.json'),'authorization_sha256':sha(ROUND/'live-authorization.json'),'scope_sha256':sha(ROUND/'scope.json'),'input_pins_sha256':sha(RT/'input-pins.json')})
check('deps_subset_actual_proposal',all(proposal['job']['files'].get(p)==h for p,h in deps['files'].items()))
check('actual_review_artifact_pinned',proposal['review']=={'path':str(ROUND/'review/runtime/REVIEW.md'),'sha256':sha(ROUND/'review/runtime/REVIEW.md')} and proposal['job']['files'][proposal['review']['path']]==proposal['review']['sha256'])
# Reuse only read-only adapter validation functions and the pure release validator AST.
sys.path.insert(0,str(RT));import adapter as a
c=a.c;k=a.k
a.verify_live_bindings();check('actual_live_bindings_validate',True)
text,record,plans,prior=a.preflight();check('prior_debit_and_full_baseline_reproduced',prior['prior_nanousd']==1182150718 and prior['baseline_files']==6829)
check('authorization_exact_and_max4_unchanged_cap',auth==a.authorization_fields() and auth['max_new_operations']==4 and auth['input_guard']==40000 and auth['output_cap']==8192 and auth['automatic_retry'] is False)
base=load(ROUND/'prior-baseline.json');targets=load(RT/'baseline-target-witness.json');base_bad=[];aliases=0
for row in base['files']:
    p=BENCH/row['path'];aliases+=p.is_symlink();target=p.resolve()
    if str(target)!=targets[row['path']] or not target.is_relative_to(BENCH.resolve()) or sha(target)!=row['sha256']:base_bad.append(row['path'])
check('all_6829_baseline_targets_content_unchanged',len(base['files'])==6829 and not base_bad and aliases==46)
release=REPO/'tools/research-credentials-stable/release.py';check('unchanged_pure_release_validator',sha(release)=='ca845ca805dbbb5fd428a06d63c735b4a326aa09100dcaeb0e913859069032a2')
tree=ast.parse(release.read_bytes());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'need','encode','digest','in_roots','validate'}]
epoch=datetime.datetime.fromisoformat(primary['verified_utc'].replace('Z','+00:00')).timestamp();ns={'Path':Path,'hashlib':hashlib,'json':json,'time':types.SimpleNamespace(time=lambda:epoch)};exec(compile(ast.Module(body=nodes,type_ignores=[]),'<pure-validation>','exec'),ns);ns['validate'](core,proposal);check('actual_proposal_valid_at_primary_verification_time',True)
ledger=load(RUN/'ledger.json');check('ledger_recomputed_exact',ledger==a.ledger(RUN));check('only_D_A_stage_directories',{p.name for p in RUN.iterdir() if p.is_dir()}=={'stage-d','stage-a'})
check('no_dependent_intents_freezes_validated_or_completion',all(not (RUN/n).exists() for n in ['stage-c-preflight.json','stage-b-preflight.json','stage-a-freeze.json','stage-d-freeze.json','completed.json']) and all(not (RUN/f'stage-{s}'/n).exists() for s in ('d','a') for n in ('content.body','validated.json','result.json','completed.json')))
stages=[];reported=Decimal(0);rate_total=0;prompt_premium=Decimal(0)
for name in ('D','A'):
    folder=RUN/f'stage-{name.lower()}';request=load(folder/'request.json');intent=load(folder/'intent.json');status=load(folder/'status.json');stop=load(folder/'stop.json');pre=load(RUN/f'stage-{name.lower()}-preflight.json');raw=read(folder/'response.body');response=c.strict(raw);choice=response['choices'][0];msg=choice['message'];content=msg['content'];usage=response['usage'];details=usage['cost_details'];prompt=usage['prompt_tokens'];completion=usage['completion_tokens'];cost=Decimal(str(usage['cost']));reported+=cost;rate=a.rate_nano(usage);rate_total+=rate
    check(name+'_exact_frozen_request',request==plans[name]['body'] and sha(folder/'request.json')==plans[name]['request_sha256']==intent['request_sha256']==pre['request_sha256'])
    check(name+'_guard_output_price_settings',len(enc(request))+1024==pre['guarded_bytes']==intent['guarded_bytes']<=40000 and request['max_tokens']==8192 and request['provider']['max_price']=={'completion':10,'prompt':2} and request['provider']['allow_fallbacks'] is False and request['provider']['only']==['openai'])
    check(name+'_response_hash_HTTP200',status['http_status']==200 and status['response_sha256']==hashlib.sha256(raw).hexdigest())
    check(name+'_OpenAI_Sol_length_at_cap',response['provider']=='OpenAI' and response['model']=='openai/gpt-6.1-sol' and choice['finish_reason']=='length' and choice['native_finish_reason']=='max_output_tokens' and completion==8192)
    try:c.strict(content)
    except (ValueError,TypeError):parse_valid=False
    else:parse_valid=True
    check(name+'_partial_content_invalid_JSON',not parse_valid)
    try:a.native(raw)
    except (ValueError,TypeError):native_rejected=True
    else:native_rejected=False
    check(name+'_adapter_rejects_truncated_native',native_rejected)
    check(name+'_durable_no_retry_stop',stop['state']=='failed_or_uncertain' and stop['response_retained'] and stop['provider_calls_may_have_occurred'] and not stop['automatic_retry'] and stop['budget_charge_nanousd']==max(a.RESERVE,a.recoverable(raw))==161920000)
    expected_prior=1182150718 if name=='D' else 1344070718
    check(name+'_stage_budget_admission_chain',intent['prior_stage_debit_nanousd']==pre['current_debit_nanousd']==expected_prior and pre['within_ceiling'] and stop['cumulative_budget_charge_nanousd']==expected_prior+161920000)
    check(name+'_during_authorized_expiry',response['created']<proposal['expires_unix'] and datetime.datetime.fromisoformat(intent['started_utc']).timestamp()<proposal['expires_unix'])
    prompt_cost=Decimal(str(details['upstream_inference_prompt_cost']));completion_cost=Decimal(str(details['upstream_inference_completions_cost']));cache_write=usage['prompt_tokens_details']['cache_write_tokens'];cached=usage['prompt_tokens_details']['cached_tokens'];premium=prompt_cost-Decimal(prompt)*Decimal(2)/1000000;prompt_premium+=premium
    check(name+'_reported_cost_components_exact',prompt_cost+completion_cost==cost==Decimal(str(details['upstream_inference_cost'])) and completion_cost==Decimal(completion)*10/1000000)
    implied=(Decimal(cache_write)*Decimal('2.5')+Decimal(prompt-cache_write)*2)/1000000
    check(name+'_cache_write_premium_arithmetic',cached==0 and prompt_cost==implied and premium==Decimal(cache_write)*Decimal('.5')/1000000)
    stages.append({'stage':name,'http_status':status['http_status'],'provider':response['provider'],'model':response['model'],'generation_id':response['id'],'finish_reason':choice['finish_reason'],'native_finish_reason':choice['native_finish_reason'],'prompt_tokens':prompt,'completion_tokens':completion,'reasoning_tokens':usage['completion_tokens_details']['reasoning_tokens'],'content_characters':len(content),'content_utf8_bytes':len(content.encode()),'raw_response_bytes':len(raw),'content_valid_JSON':parse_valid,'reported_cost_usd':str(cost),'frozen_rate_estimate_nanodollars':rate,'conservative_charge_nanodollars':161920000,'reported_prompt_cost_usd':str(prompt_cost),'reported_completion_cost_usd':str(completion_cost),'cache_write_tokens':cache_write,'cached_tokens':cached,'implied_aggregate_prompt_USD_per_million':str(prompt_cost*1000000/Decimal(prompt)),'cache_write_premium_inference_usd':str(premium)})
check('D_safe_independent_A_continuation',load(RUN/'stage-d/stop.json')['safe_separate_arm_continuation'] is True)
check('all_four_outcomes_exact',ledger['planned_outcomes']=={'D':'failed_or_uncertain','A':'failed_or_uncertain','C':'not_attempted','B':'not_attempted'})
check('two_attempt_reservations_cumulative',len(ledger['operations'])==2 and ledger['new_budget_charge_nanousd']==323840000 and ledger['cumulative_budget_charge_nanousd']==1505990718 and ledger['cumulative_budget_charge_nanousd']<ledger['ceiling_nanousd']==2000000000)
check('reported_total_and_cache_premium',reported==Decimal('.182347') and rate_total==178648000 and prompt_premium==Decimal('.003699') and reported-Decimal(rate_total)/1000000000==prompt_premium)
stop=load(RUN/'stop.json');check('overall_stop_matches_ledger',stop['state']=='stopped_no_retry' and stop['ledger']==ledger and not stop['automatic_retry'] and not stop['production_eligible'] and not stop['action_ready'])
check('execution_READY_exact_observations',execution['provider_calls']==2 and execution['native_runner_exit_code']==1 and execution['outcome']=='D_and_A_output_truncated_C_and_B_not_attempted' and Decimal(execution['reported_cost_usd'])==reported and execution['conservative_new_charge_nanousd']==323840000 and execution['cumulative_charge_nanousd']==1505990718 and execution['no_retry'] is True)
check('all_inspected_pins_still_unchanged',all(sha(p)==v['sha256'] for p,v in inputs.items()))
result={'schema_version':'round12.postrun-independent-review.checks.v1','checks_passed':sum(x['pass'] for x in rows),'checks_total':len(rows),'checks':rows,'input_pins':inputs,'manifest_sha256':manifest_hash,'actual_release_files_verified':len(proposal['job']['files']),'baseline_files_verified':len(base['files']),'baseline_alias_targets_verified':aliases,'runtime_owner_files_verified':len(ready['files']),'public_signature_verified':verified.returncode==0,'stages':stages,'reported_total_usd':str(reported),'frozen_rate_total_nanodollars':rate_total,'reported_minus_frozen_rate_usd':str(prompt_premium),'conservative_new_nanodollars':323840000,'conservative_cumulative_nanodollars':1505990718,'remaining_ceiling_nanodollars':494009282,'outcome':'PARTIAL_TRUNCATED_D_A_C_B_NOT_ATTEMPTED','operational_gate':'correct_fail_closed','evaluation_completed':False,'semantic_status':'unverified','price_caveat':'Reported prompt components exceed the nominal 2 USD/M request cap; arithmetic exactly fits 2.5 USD/M cache-write tokens plus 2 USD/M remaining prompt tokens. This is an inference from raw usage, not verified provider pricing policy or invoice. Conservative reservations still dominate.','additional_provider_calls':0,'credentials_read':False,'signer_executor_invoked':False,'reference_contents_read':False,'production_eligible':False,'action_ready':False}
print(json.dumps(result,indent=2))
if result['checks_passed']!=result['checks_total']:sys.exit(1)
