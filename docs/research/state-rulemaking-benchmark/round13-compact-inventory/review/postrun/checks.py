"""Actual R13 receipt audit only; no live request, signer, executor or semantic assessment."""
import ast,base64,datetime,hashlib,json,subprocess,sys,tempfile,types
from decimal import Decimal
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROUND=HERE.parent.parent;RT=ROUND/'runtime';RUN=ROUND/'execution/run';BENCH=ROUND.parent;REPO=ROUND.parents[3]
rows=[];pins={}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):
    p=Path(p);assert not any(x in p.parts for x in ('reference','evaluation','candidate-audit'));b=p.read_bytes();pins[str(p)]={'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)};return b
def load(p):return json.loads(read(p))
def canon(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def check(n,ok):rows.append({'name':n,'pass':bool(ok)})
def package(folder):
    m=load(folder/'READY.json')
    for name,p in m['files'].items():check('pin:'+str(folder.relative_to(ROUND))+'/'+name,sha(folder/name)==p['sha256'] and (folder/name).stat().st_size==p['bytes'])
    return m
runtime=package(RT);package(ROUND/'review/runtime');package(ROUND/'protocol');package(ROUND/'review/protocol')
check('approved_runtime_READY_unchanged',sha(RT/'READY.json')=='929e14bcb80314ed323458cc07414865edf0a6ef68bc5a3a472ced9753e0df80')
execution=load(ROUND/'execution/READY.json')
for name,p in execution['files'].items():check('execution_pin:'+name,sha(RUN/name)==p['sha256'] and (RUN/name).stat().st_size==p['bytes'])
check('execution_freeze_exact11_files',len(execution['files'])==11 and set(execution['files'])=={str(p.relative_to(RUN)) for p in RUN.rglob('*') if p.is_file()})
proposal=load(RT/'UNSIGNED-JOB-PROPOSAL.json');deps=load(RT/'dependencies.json');binding=load(RT/'binding.json');auth=load(ROUND/'live-authorization.json');release=load(ROUND/'release-receipt.json');primary=load(ROUND/'primary-release-verification.json');core=load(BENCH/'runner-stability-review/deployment/core.json')
job='round13-compact-inventory-initial';stem=Path(core['registry_dir'])/job;rawmanifest=read(stem.with_suffix('.json'));signature=read(stem.with_suffix('.sig'));claim=read(Path(core['journal_dir'])/job).decode().strip();manifesthash=hashlib.sha256(rawmanifest).hexdigest()
check('published_manifest_exact_canonical_proposal',rawmanifest==canon(proposal) and json.loads(rawmanifest)==proposal and proposal['job_id']==job)
check('manifest_native_claim_and_receipts_match',manifesthash==claim==release['manifest_sha256']==primary['manifest_canonical_sha256'])
check('primary_release_receipt_native_check_success',release['state']=='released' and release['release_exit_code']==0 and release['native_check_passed'] is True and release['provider_calls']==0 and release['credential_access'] is False)
check('primary_proposal_runtime_review_pins',sha(RT/'UNSIGNED-JOB-PROPOSAL.json')==primary['proposal_sha256'] and sha(RT/'READY.json')==primary['runtime_ready_sha256'] and sha(ROUND/'review/runtime/READY.json')==primary['review_ready_sha256'])
check('native_executor_hash_unchanged',sha('/Users/home/.local/libexec/yokel/research-credentials-stable-v1')==primary['executor_sha256']=='821f91b67f4c0c2d2a7f333e1381fab9aec1f9d8a9b8be8c34a0ee135494547e')
public=base64.b64decode(core['public_key_base64']);check('public_P256_key_shape',len(public)==65 and public[0]==4)
with tempfile.TemporaryDirectory() as temp:
    p=Path(temp);(p/'public.der').write_bytes(bytes.fromhex('3059301306072a8648ce3d020106082a8648ce3d030107034200')+public);(p/'message').write_bytes(b'yokel.research-job.v1\0'+rawmanifest);(p/'signature').write_bytes(signature)
    verified=subprocess.run(['/usr/bin/openssl','dgst','-sha256','-keyform','DER','-verify',str(p/'public.der'),'-signature',str(p/'signature'),str(p/'message')],capture_output=True,text=True)
    check('independent_public_signature_verification',verified.returncode==0 and 'Verified OK' in verified.stdout)
# Only hashes are consumed for baseline/dependency artifacts, including prior references.
check('all8704_released_file_hashes_current_canonical',len(proposal['job']['files'])==8704 and all(Path(p).is_absolute() and Path(p).resolve()==Path(p) and sha(p)==h for p,h in proposal['job']['files'].items()))
check('manifest_native_size_limit',len(rawmanifest)<=4*1024*1024 and len(proposal['job']['files'])<=10000)
check('dependencies_subset_final_proposal',all(proposal['job']['files'].get(p)==h for p,h in deps['files'].items()))
check('binding_exact_current_files',binding=={'schema_version':'round13.compact.binding.v1','dependencies_sha256':sha(RT/'dependencies.json'),'authorization_sha256':sha(ROUND/'live-authorization.json'),'scope_sha256':sha(ROUND/'scope.json'),'input_pins_sha256':sha(RT/'input-pins.json')})
check('actual_runtime_review_exact_pin',proposal['review']=={'path':str(ROUND/'review/runtime/REVIEW.md'),'sha256':sha(ROUND/'review/runtime/REVIEW.md')} and proposal['job']['files'][proposal['review']['path']]==proposal['review']['sha256'])
releasecode=REPO/'tools/research-credentials-stable/release.py';check('unchanged_pure_release_validator',sha(releasecode)=='ca845ca805dbbb5fd428a06d63c735b4a326aa09100dcaeb0e913859069032a2');tree=ast.parse(releasecode.read_bytes());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'need','encode','digest','in_roots','validate'}]
epoch=datetime.datetime.fromisoformat(primary['verified_utc'].replace('Z','+00:00')).timestamp();ns={'Path':Path,'hashlib':hashlib,'json':json,'time':types.SimpleNamespace(time=lambda:epoch)};exec(compile(ast.Module(body=nodes,type_ignores=[]),'<pure-release-validator>','exec'),ns);ns['validate'](core,proposal);check('actual_manifest_valid_at_release_verification',True)
sys.path.insert(0,str(RT));import adapter as a
c=a.c;k=a.k
a.verify_live_bindings();check('actual_live_bindings_exact_authorization',auth==a.authorization_fields())
source,plan,prior=a.preflight();check('prior_recomputed_1505990718',prior['prior_nanousd']==1505990718 and prior['baseline_rows']==6981)
base=load(ROUND/'prior-baseline.json');targets=load(RT/'baseline-target-witness.json');bad=[];aliases=0
for row in base['files']:
    p=BENCH/row['path'];target=p.resolve();aliases+=p.is_symlink()
    if not target.is_relative_to(BENCH.resolve()) or str(target)!=targets[row['path']] or sha(target)!=row['sha256']:bad.append(row['path'])
check('all6981_baseline_rows_46_aliases_unchanged',len(base['files'])==6981 and aliases==46 and not bad)
request=load(RUN/'request.json');table=load(RUN/'span-table.json');intent=load(RUN/'intent.json');status=load(RUN/'status.json');raw=read(RUN/'response.body');response=c.strict(raw);result=load(RUN/'result.json');ledger=load(RUN/'ledger.json');done=load(RUN/'completed.json')
content,metadata=a.native(raw);compact_bytes=read(RUN/'validated.json');expanded_bytes=read(RUN/'expanded.json');checked=k.validate_response(content.decode('utf-8'),metadata['finish_reason'],source,table);compact=checked['compact'];expanded=checked['expanded'];inverse=k.protocol().contract(expanded,source,table)
check('request_exact_frozen_protocol_bytes',request==plan['body'] and read(RUN/'request.json')==c.encode(plan['body'])==read(ROUND/'protocol/offline-request.json') and sha(RUN/'request.json')==plan['request_sha256']==intent['request_sha256'])
check('request_exact_15692guard_8192cap_route_price',len(c.encode(request))==14668 and intent['guarded_bytes']==plan['guarded_bytes']==15692<=40000 and request['max_tokens']==intent['output_cap']==8192 and request['provider']=={'allow_fallbacks':False,'max_price':{'completion':10,'prompt':2},'only':['openai'],'order':['openai'],'require_parameters':True})
user=c.strict(request['messages'][1]['content']);check('full_source_only_exact37spans',set(user)=={'source_text','source_text_sha256','span_table','span_table_sha256'} and user['source_text']==source and table==user['span_table']==plan['table'] and len(table['rows'])==37 and ''.join(r[3] for r in table['rows'])==source and k.protocol().reconstruct(source,table)==source)
check('intent_source_table_protocol_budget_pins',intent['source_sha256']==k.protocol().source_hash(source) and intent['span_table_sha256']==c.digest(table) and intent['protocol_ready_sha256']==c.READY_SHA and intent['input_pins_sha256']==sha(RT/'input-pins.json') and intent['prior_nanousd']==1505990718 and intent['reserved_nanousd']==200000000 and intent['ceiling_nanousd']==2000000000 and intent['automatic_retry'] is False)
choice=response['choices'][0];usage=response['usage'];check('native_HTTP200_OpenAI_stop',status=={'http_status':200,'response_sha256':c.sha(raw)} and metadata['model']=='openai/gpt-6.1-sol' and metadata['provider']=='OpenAI' and choice['finish_reason']=='stop' and choice['native_finish_reason']=='completed')
check('full_raw_content_compact_expanded_exact',content==read(RUN/'content.body')==compact_bytes==c.encode(compact) and expanded_bytes==c.encode(expanded))
check('exact_inverse_object_canonical_hash',inverse==compact and c.encode(inverse)==compact_bytes and c.digest(inverse)==c.digest(compact))
check('91_units_5728completion_87reasoning',len(compact['u'])==91 and usage['completion_tokens']==5728 and usage['completion_tokens_details']['reasoning_tokens']==87 and usage['prompt_tokens']==3601 and usage['total_tokens']==9329)
check('actual_output_byte_sizes',len(raw)==24410 and len(content)==17827 and len(content.decode())==17827 and len(expanded_bytes)==55377 and len(table['rows'])==37)
expected_result={'schema_version':'round13.inventory-result.v1','request_sha256':plan['request_sha256'],'source_sha256':k.protocol().source_hash(source),'span_table_sha256':c.digest(table),'response_sha256':c.sha(raw),'content_sha256':c.sha(content),'compact_sha256':c.digest(compact),'expanded_sha256':c.digest(expanded),'unit_count':91,'roundtrip_exact':True,'whole_line_evidence_is_entailment':False,**metadata,'cumulative_budget_charge_nanousd':a.PRIOR+metadata['budget_charge_nanousd'],**k.FLAGS}
check('complete_result_receipt_recomputed',result==expected_result)
check('completion_hashes_exhaustive10_preceding_receipts',done['state']=='validated_frozen' and len(done['files'])==10 and set(done['files'])==set(execution['files'])-{'completed.json'} and all(sha(RUN/n)==h for n,h in done['files'].items()))
check('neutral_ledger_exact_and_completion_pin',ledger==a.ledger(RUN) and ledger['state']=='charge_recorded' and ledger['attempts_claimed']==1 and done['files']['ledger.json']==sha(RUN/'ledger.json'))
check('one_run_no_stop_or_retry_artifacts',not (RUN/'stop.json').exists() and not any(p.is_dir() for p in RUN.iterdir()) and {p.name for p in (ROUND/'execution').iterdir()}=={'READY.json','run'})
check('all_unverified_semantic_flags_preserved',result['semantic_status']==done['semantic_status']==result['source_inventory_completeness']==expanded['source_inventory_completeness']=='unverified' and result['whole_line_evidence_is_entailment'] is False and all(x['production_eligible'] is False and x['action_ready'] is False for x in (expanded,result,done,execution)))
check('within_authorized_expiry_and_scope_one_call',response['created']<proposal['expires_unix'] and datetime.datetime.fromisoformat(intent['started_utc']).timestamp()<proposal['expires_unix'] and auth['max_new_operations']==auth['inventory_calls']==1 and auth['direct_calls']==auth['scope_calls']==auth['mapping_calls']==0)
cost=Decimal(str(usage['cost']));detail=usage['cost_details'];promptcost=Decimal(str(detail['upstream_inference_prompt_cost']));completioncost=Decimal(str(detail['upstream_inference_completions_cost']));cachewrites=usage['prompt_tokens_details']['cache_write_tokens'];rate=a.rate_nano(usage);delta=cost-Decimal(rate)/1000000000
check('reported_cost_components_exact',cost==Decimal('.066281')==Decimal(str(detail['upstream_inference_cost']))==promptcost+completioncost and completioncost==Decimal(5728)*10/1000000)
check('cache_write_premium_arithmetic_only',cachewrites==3598 and usage['prompt_tokens_details']['cached_tokens']==0 and promptcost==(Decimal(cachewrites)*Decimal('2.5')+Decimal(usage['prompt_tokens']-cachewrites)*2)/1000000 and delta==Decimal('.001799'))
check('conservative_charge_and_cumulative_exact',rate==64482000 and result['reported_cost_nanousd']==66281000 and ledger['budget_charge_nanousd']==result['budget_charge_nanousd']==max(200000000,66281000,rate)==200000000 and ledger['cumulative_budget_charge_nanousd']==result['cumulative_budget_charge_nanousd']==1705990718<2000000000)
check('execution_READY_observations_match',execution['native_runner_exit_code']==0 and execution['provider_calls']==1 and execution['structural_outcome']=='validated_frozen' and execution['unit_count']==91 and execution['completion_tokens']==5728 and Decimal(execution['reported_cost_usd'])==cost and execution['conservative_new_charge_nanousd']==200000000 and execution['cumulative_charge_nanousd']==1705990718 and execution['no_retry'])
check('all_inspected_inputs_unchanged',all(sha(p)==v['sha256'] for p,v in pins.items()))
report={'schema_version':'round13.postrun-independent-review.checks.v1','checks_passed':sum(r['pass'] for r in rows),'checks_total':len(rows),'checks':rows,'input_pins':pins,'released_manifest_sha256':manifesthash,'public_signature_verified':verified.returncode==0,'release_files_verified':8704,'baseline_rows_verified':6981,'baseline_alias_targets_verified':46,'runtime_owner_files_verified':len(runtime['files']),'outcome':'VALIDATED_FROZEN_SINGLE_CALL','unit_count':91,'raw_response_bytes':len(raw),'content_characters':len(content.decode()),'compact_content_bytes':len(content),'expanded_bytes':len(expanded_bytes),'prompt_tokens':usage['prompt_tokens'],'completion_tokens':usage['completion_tokens'],'reasoning_tokens':usage['completion_tokens_details']['reasoning_tokens'],'completion_cap_fraction':5728/8192,'completion_cap_remaining':8192-5728,'reported_cost_usd':str(cost),'frozen_rate_estimate_nanodollars':rate,'reported_minus_rate_usd':str(delta),'reported_prompt_cost_usd':str(promptcost),'cache_write_tokens':cachewrites,'conservative_new_nanodollars':200000000,'conservative_cumulative_nanodollars':1705990718,'remaining_ceiling_nanodollars':294009282,'invoice_verified':False,'provider_acceptance_observed_for_exact_request':True,'semantic_status':'unverified','source_inventory_completeness':'unverified','baseline_reference_handling':'Hash-only integrity verification; no reference/evaluation semantics consumed.','additional_provider_calls':0,'credentials_read':False,'signer_executor_invoked':False,'production_eligible':False,'action_ready':False}
print(json.dumps(report,indent=2))
if report['checks_passed']!=report['checks_total']:sys.exit(1)
