#!/usr/bin/env python3
"""Independent frozen integrity/cost audit; no semantic claim matching, providers or credentials."""
import copy,hashlib,importlib.util,json,sys
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
OUT=Path(__file__).resolve().parent;R=OUT.parents[1];OLD=R.parent/'round8';RUN=R/'execution/run';DOC='doc-92211b8c7ba0'
EXPECTED_E='415b294f83b3c093bd623da4cd4369a3c84cf385e6402ad190794e5681b30fb6'
def guard(event,args):
 if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.posix_spawn'):raise RuntimeError('audit networking/processes disabled')
 if event=='open' and isinstance(args[0],(str,bytes)):
  name=str(args[0]).lower()
  if '/.env' in name or '/library/keychains/' in name or '/.aws/' in name or Path(name).name in ('credentials','credentials.json'):raise RuntimeError('audit credential reads disabled')
sys.addaudithook(guard)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def canonical(v):return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
def save(name,v):
 p=OUT/name;p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n');return sha(p)
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
checks=[];frozen={}
def check(name,ok,evidence=None):
 if not ok:raise AssertionError(name)
 checks.append(dict(check=name,passed=True,evidence=evidence))
def freeze(base,letter,want=None):
 p=base/'execution'/('freeze-'+letter+'.json');v=read(p);seen=set()
 if want:check('freeze '+str(base.name)+' '+letter+' hash',sha(p)==want)
 frozen[str(p)]=sha(p)
 for row in v['files']:
  f=(base/row['path']).resolve();check('frozen '+str(base.name)+'/'+row['path'],not Path(row['path']).is_absolute() and f.is_relative_to(base.resolve()) and row['path'] not in seen and f.is_file() and f.stat().st_size==row['bytes'] and sha(f)==row['sha256']);seen.add(row['path']);frozen[str(f)]=row['sha256']
 return dict(sha256=sha(p),files=len(seen),created_utc=v['created_utc'])
def main():
 binding=read(R/'execution/service-account/binding.json')
 freezes={k:freeze(R,k,binding.get('freeze_'+k+'_sha256') if k!='E' else EXPECTED_E) for k in ('A','S','E')}
 freezes['old_B']=freeze(OLD,'B','60b1e0f8c6321cee6407cfa04ad02af92a7546b059dd5235868746115cc5b792')
 freezes['old_E']=freeze(OLD,'E','ef9891fca1a9aa6e0eeeafcdfee22d46b7d6dab8c79ff39099c3e00ef4f2c996')
 check('freeze counts',[freezes[k]['files'] for k in ('A','S','E','old_B','old_E')]==[29,4,20,9,20])
 old_baseline=read(R/'execution/prior-round8-baseline.json')['files']
 for n,h in old_baseline.items():check('original R8 baseline '+n,sha(R.parent/n)==h)
 review=read(R/'review/FINAL-REVIEW.json');impl=read(R/'runtime/implementation.json');check('reviewed implementation exact',impl==review['candidate_code_pins'])
 for n,h in impl['code'].items():check('implementation '+n,sha(n)==h)
 authorization=read(R/'execution/live-authorization.json');live=read(R/'execution/service-account/live-intent.json');live_result=read(R/'execution/service-account/live-result.json')
 for key,rel in [('implementation_sha256','runtime/implementation.json'),('manifest_sha256','sources/source-inputs.READY.json'),('authorization_sha256','execution/live-authorization.json'),('dependencies_sha256','execution/service-account/dependencies.json')]:check('service '+key,sha(R/rel)==binding[key]==live[key])
 check('service adapter/binding',live['adapter_sha256']==sha(R/'execution/service-account/adapter.py') and live['binding_sha256']==sha(R/'execution/service-account/binding.json'))
 check('authorization limits',authorization==dict(schema_version='round8-cap-probe.live-authorization.v1',implementation_sha256=sha(R/'runtime/implementation.json'),manifest_sha256=sha(R/'sources/source-inputs.READY.json'),source_labels_frozen_before_outputs=True,source_labels_freeze_sha256=freezes['old_B']['sha256'],nominal_budget_usd=2.0,prior_budget_debit_usd=.100166,prior_debit_sha256=sha(R/'runtime/prior-debit.json'),max_new_operations=3,calls_per_stage=1,inventory_completion=12288))
 for key in ('A','S'):check('service freeze '+key,live['freeze_counts'][key]==freezes[key]['files'] and binding['freeze_'+key+'_sha256']==freezes[key]['sha256'])
 check('service original B binding',binding['freeze_B_sha256']==live['source_labels_freeze_sha256']==freezes['old_B']['sha256'])
 deps=read(R/'execution/service-account/dependencies.json')
 for n,h in deps['files'].items():check('dependency '+n,sha(n)==h)
 job=read(R/'execution/service-account/native-job.json')
 for n,h in job['files'].items():check('native pin '+n,sha(n)==h)
 check('native dependency inclusion',all(job['files'].get(n)==h for n,h in deps['files'].items()))
 check('fixed isolated native job',job['argv'][1:4]==['-I','-S','-B'] and job['argv'][4:]==[str(R/'execution/service-account/adapter.py'),'--live-initial'] and job['timeout_seconds']==1800)
 check('dependency count',len(deps['files'])==live['dependency_files']==1681)
 check('completed adapter',live_result['state']=='completed' and not (R/'execution/service-account/live-stop.json').exists() and live['automatic_retry'] is False and live['output_path']==str(RUN))
 runtime=load('cap_postrun_runtime',R/'runtime/run_pipeline.py');runtime.verify_implementation(R/'runtime/implementation.json');runtime.verify_prior_debit()
 source_rows=runtime.load_sources(R/'sources/source-inputs.READY.json',R/'sources');check('single exact valid source',len(source_rows)==1 and not source_rows[0]['source_errors'])
 source=read(RUN/'documents'/DOC/'source.json');check('same descriptor as original',source==source_rows[0]['source'] and sha(RUN/'documents'/DOC/'source.json')==sha(OLD/'execution/run/documents'/DOC/'source.json'))
 schedule=read(R/'execution/schedule.json');old_schedule=read(OLD/'execution/schedule.json');check('schedule is original one-WI projection',schedule=={**old_schedule,'documents':[d for d in old_schedule['documents'] if d['document_id']==DOC]})
 obs_paths=list(RUN.glob('observed-*.json'));check('one observation',len(obs_paths)==1);obs_path=obs_paths[0];observed=read(obs_path);runtime.validate_observation(observed);check('observation version unchanged',observed['schema_version']=='round8.observed.v1')
 completed=read(RUN/'completed.json');snap_paths=list(RUN.glob('snapshot-*.json'));check('one snapshot',len(snap_paths)==1);snapshot=read(snap_paths[0]);check('snapshot completed and observation linked',snapshot['state']=='completed' and snapshot['observed_sha256']==sha(obs_path))
 check('completed observations identical',completed['documents']==observed['documents'] and completed['totals']==snapshot['totals'])
 ops=list((RUN/'operations').iterdir());check('one operation only',len(ops)==1 and ops[0].is_dir());op=ops[0];meta=read(op/'identity.json');intent=read(op/'intent.json');status=read(op/'status.json');request=read(op/'request.json');response=read(op/'response.body');result=read(op/'result.json');assembled=read(RUN/'documents'/DOC/'assembled.json');pins=read(RUN/'pins.json')
 check('one inventory no verifiers',meta['kind']=='inventory' and meta['operation_id']==DOC+'-inventory' and len(list(RUN.rglob('intent.json')))==1 and len(list(RUN.rglob('result.json')))==1)
 check('durable request/identity binding',all(intent[k]==v for k,v in meta.items()) and intent['automatic_retry'] is False and meta['request_sha256']==sha(op/'request.json') and meta['pins_sha256']==sha(RUN/'pins.json') and op.name=='inventory-'+hashlib.sha256(canonical(meta)).hexdigest()[:24])
 check('pins authorized',pins['implementation']==impl and pins['authorization_sha256']==sha(R/'execution/live-authorization.json') and pins['manifest_sha256']==binding['manifest_sha256'] and pins['prior_budget_debit_usd']==.100166 and pins['prior_debit_sha256']==sha(R/'runtime/prior-debit.json') and pins['source_labels_freeze_sha256']==freezes['old_B']['sha256'])
 check('HTTP200 complete response',status['http_status']==200 and status['response_sha256']==sha(op/'response.body') and response['choices'][0]['finish_reason']=='stop' and response['choices'][0]['native_finish_reason']=='completed' and response['usage']['completion_tokens']==8263 and not (op/'stop.json').exists())
 check('strict result reproducible',runtime.a.parse_or((op/'response.body').read_bytes())==result)
 check('frozen assembly reproducible',runtime.p.assemble(source,result['structured'])==assembled)
 check('inventory content/hash',assembled['inventory']==result['structured'] and hashlib.sha256(canonical(assembled['inventory'])).hexdigest()==assembled['inventory_sha256']=='6aefa75fb280bc77e03394b726feef404f908e72f37286c6786baa4243e308f7')
 check('exact final body',runtime.requests(source)['inventory']['body']==request)
 oldop=next((OLD/'execution/run/operations').iterdir());oldrequest=read(oldop/'request.json');check('only max_tokens changed',request==dict(oldrequest,max_tokens=12288))
 check('source-only user body',json.loads(request['messages'][1]['content'])=={'source':source})
 doc=observed['documents'][0];errors=['t-access-request: dependency ids require a relation','t-access-request: relative/conditional timing requires dependency association or explicit uncertainty']
 check('assembly review precisely represented',len(observed['documents'])==1 and doc['document_id']==DOC and doc['runtime_gate']=='assembly_review' and doc['gate_reasons']==assembled['validation']['errors']==errors and assembled['validation']['valid'] is False and assembled['record'] is None and doc['inventory_sha256']==assembled['inventory_sha256'] and doc['record_sha256'] is None and doc['payload_sha256'] is None and doc['failure'] is None and doc['provider_service_error'] is False)
 check('no calls/judgments for either verifier',all(not a['called'] and a['status']=='not_started' and a['payload_sha256'] is None and not a['source_coverage_complete'] and 'judgment' not in a for a in doc['arms'].values()))
 absent=['common-payload.json','jev-request.json','stronger-request.json','stronger-validation.json'];check('no record/payload/verifier artifacts',not any((RUN/'documents'/DOC/x).exists() for x in absent))
 check('freeze timing',datetime.fromisoformat(freezes['old_B']['created_utc'])<datetime.fromisoformat(freezes['S']['created_utc'])<datetime.fromisoformat(live['started_utc'])<=datetime.fromisoformat(intent['created_utc'])<datetime.fromisoformat(freezes['E']['created_utc']))
 usage=response['usage'];reported=Decimal(str(usage['cost']));estimate=Decimal(usage['prompt_tokens'])*Decimal(str(impl['prices']['prompt']))+Decimal(usage['completion_tokens'])*Decimal(str(impl['prices']['completion']));reserve=Decimal(str(intent['reserved_nominal_usd']));charge=max(reserve,reported);totals=completed['totals']
 check('new costs',reported==Decimal('.0900085') and estimate==Decimal('.088534') and abs(charge-Decimal('.161608'))<Decimal('1e-15') and result['observed_cost_usd']==float(reported))
 prior_usage=read(oldop/'response.body')['usage'];prior_reported=Decimal(str(prior_usage['cost']));prior_debit=Decimal(str(runtime.PRIOR_DEBIT));prior_estimate=Decimal(prior_usage['prompt_tokens'])*Decimal(str(impl['prices']['prompt']))+Decimal(prior_usage['completion_tokens'])*Decimal(str(impl['prices']['completion']))
 check('prior costs',prior_reported==Decimal('.0688185') and prior_debit==Decimal('.100166') and prior_estimate==Decimal('.067344'))
 check('combined costs',prior_reported+reported==Decimal('.158827') and abs(prior_debit+charge-Decimal('.261774'))<Decimal('1e-15'))
 check('ledger costs and counts',abs(Decimal(str(totals['budget_charge_usd']))-(prior_debit+charge))<Decimal('1e-15') and abs(Decimal(str(totals['new_budget_charge_usd']))-charge)<Decimal('1e-15') and Decimal(str(totals['observed_accounted_usd']))==reported and totals['operations']==totals['inventory_cases']==1 and totals['jev_cases']==totals['stronger_cases']==totals['ocr_pages']==0)
 costs={'extraction':dict(usage_estimate_usd=float(estimate),conservative_charge_usd=.161608,provider_reported_usd=float(reported)),**{a:dict(usage_estimate_usd=0,conservative_charge_usd=0,provider_reported_usd=0) for a in ('jev','stronger')}}
 cost_audit={'schema_version':'round8-cap-probe.cost_audit.v1','incremental_probe':costs,'prior_attempt':{'provider_reported_usd':float(prior_reported),'conservative_charge_usd':float(prior_debit),'usage_estimate_usd':float(prior_estimate)},'combined_same_notice_attempts':{'provider_reported_usd':float(prior_reported+reported),'conservative_charge_usd':.261774,'usage_estimate_usd':float(prior_estimate+estimate)},'native_response_usage':usage,'response_sha256':sha(op/'response.body'),'prior_response_sha256':sha(oldop/'response.body'),'intent_sha256':sha(op/'intent.json'),'prior_intent_sha256':sha(oldop/'intent.json'),'pinned_prices':impl['prices'],'float_note':'Runtime binary-float reservations .16160800000000003 and combined .26177400000000006 are shown at exact configured decimal precision.','invoice_verified':False,'verifier_zero_basis':'Exactly one inventory intent/result and no verifier operation exists in frozen complete run.','evaluation_cost_scope':'Incremental probe only; combined experiment costs reported separately, never added to the probe observation.'}
 save('cost-audit.json',cost_audit)
 derived=copy.deepcopy(observed);derived['costs']=costs;save('observed-with-costs.json',derived);check('observation only costs added',{k:v for k,v in derived.items() if k!='costs'}==observed)
 save('observation-derivative.json',{'schema_version':'round8.cost_only_observation_derivative.v1','source_path':str(obs_path),'source_sha256':sha(obs_path),'derived_sha256':sha(OUT/'observed-with-costs.json'),'source_freeze_E_sha256':EXPECTED_E,'changes':['Added incremental probe costs only. All original document observations/states/hashes remain unchanged.'],'cost_audit_sha256':sha(OUT/'cost-audit.json')})
 original_truth=read(OLD/'protocol/source-labels/truth.json');truth={**copy.deepcopy(original_truth),'documents':[copy.deepcopy(d) for d in original_truth['documents'] if d['document_id']==DOC]}
 check('one WI truth 31 units',truth['schema_version']=='round8.truth.v1' and len(truth['documents'])==1 and len(truth['documents'][0]['units'])==31 and truth['documents'][0]['pdf_sha256']==schedule['documents'][0]['pdf_sha256'])
 save('truth-WI-projection.json',truth);save('truth-projection-provenance.json',{'schema_version':'round8-cap-probe.truth_projection.v1','original_truth_path':str(OLD/'protocol/source-labels/truth.json'),'original_truth_sha256':sha(OLD/'protocol/source-labels/truth.json'),'original_freeze_B_sha256':freezes['old_B']['sha256'],'schedule_path':str(R/'execution/schedule.json'),'schedule_sha256':sha(R/'execution/schedule.json'),'projection_sha256':sha(OUT/'truth-WI-projection.json'),'document_id':DOC,'source_units':31,'operation':'Retain original top-level fields/schema_version; filter documents by exact scheduled ID. Every retained document field and source unit unchanged.','new_labels_created':False,'reference':'Original independent AI image reference, not human-adjudicated gold.'})
 save('artifact-audit.json',{'inventory_sha256':assembled['inventory_sha256'],'record':None,'payload':None,'validation_errors':errors,'operation_counts':{'inventory':1,'jev':0,'stronger':0},'absent_artifacts':absent,'semantic_matching':'Owned by separate image reviewer; this audit does not score inventory claims.'})
 for n,h in frozen.items():check('frozen unchanged '+n,sha(n)==h)
 outputs={n:sha(OUT/n) for n in ('cost-audit.json','observed-with-costs.json','observation-derivative.json','truth-WI-projection.json','truth-projection-provenance.json','artifact-audit.json')}
 summary={'schema_version':'round8-cap-probe.postrun_audit.v1','created_utc':datetime.now(timezone.utc).isoformat(),'passed':True,'freezes':freezes,'checks':checks,'old_R8_baseline_files_verified':len(old_baseline),'code_files_verified':len(impl['code']),'dependency_files_verified':len(deps['files']),'operation_counts':{'inventory':1,'jev':0,'stronger':0},'inventory_sha256':assembled['inventory_sha256'],'valid_provider_results':1,'assembled_records':0,'runtime_gate':'assembly_review','source_units':31,'provider_calls_by_audit':0,'credentials_read':False,'frozen_files_modified':False,'semantic_matching':'Separate image-child audit pending/consumed only by evaluate.py.','outputs':outputs}
 save('audit.json',summary);print(json.dumps({k:v for k,v in summary.items() if k not in ('checks','outputs','freezes')}))
if __name__=='__main__':main()
