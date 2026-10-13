#!/usr/bin/env python3
"""Read-only frozen R8 integrity/cost audit and deterministic scoring; writes only this directory."""
import copy,hashlib,importlib.util,json,sys
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path
OUT=Path(__file__).resolve().parent;R=OUT.parents[1];RUN=R/'execution/run'
EXPECTED_E='ef9891fca1a9aa6e0eeeafcdfee22d46b7d6dab8c79ff39099c3e00ef4f2c996'
def guard(event,args):
    if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.posix_spawn'):raise RuntimeError('audit network/process blocked')
    if event=='open' and isinstance(args[0],(str,bytes)):
        name=str(args[0]).lower()
        if '/.env' in name or '/library/keychains/' in name or '/.aws/' in name or Path(name).name in ('credentials','credentials.json'):raise RuntimeError('audit credential access blocked')
sys.addaudithook(guard)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def canonical(v):return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
def save(name,value):
    path=OUT/name;path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');return sha(path)
checks=[]
def check(name,ok,evidence=None):
    if not ok:raise AssertionError(name)
    checks.append(dict(check=name,passed=True,evidence=evidence))
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
check('supplied E hash',sha(R/'execution/freeze-E.json')==EXPECTED_E)
freezes={}
frozen_before={}
for letter in 'ASBE':
    path=R/'execution'/('freeze-'+letter+'.json');freeze=read(path);seen=set()
    for row in freeze['files']:
        file=(R/row['path']).resolve();check('freeze path '+letter+':'+row['path'],not Path(row['path']).is_absolute() and file.is_relative_to(R.resolve()) and row['path'] not in seen);seen.add(row['path'])
        check('freeze bytes '+letter+':'+row['path'],file.is_file() and file.stat().st_size==row['bytes'] and sha(file)==row['sha256'])
        frozen_before[str(file)]=row['sha256']
    freezes[letter]=dict(sha256=sha(path),files=len(seen),created_utc=freeze['created_utc'])
check('freeze counts A/S/B/E',[freezes[k]['files'] for k in 'ASBE']==[69,927,9,20])
schedule=read(R/'execution/schedule.json');truth=read(R/'protocol/source-labels/truth.json');observed_paths=list(RUN.glob('observed-*.json'));check('single observed artifact',len(observed_paths)==1)
observed_path=observed_paths[0];observed=read(observed_path);snapshot_paths=list(RUN.glob('snapshot-*.json'));check('single run snapshot',len(snapshot_paths)==1);snapshot=read(snapshot_paths[0]);pins=read(RUN/'pins.json')
scheduled=schedule['documents'];ids=[d['document_id'] for d in scheduled];truth_by={d['document_id']:d for d in truth['documents']}
check('five notices/five states/seventeen pages',len(ids)==5 and len({d['state'] for d in scheduled})==5 and sum(d['pdf_pages'] for d in scheduled)==17)
check('schedule truth observed exact cohort',set(ids)==set(truth_by)=={d['document_id'] for d in observed['documents']})
check('178 frozen source units',sum(len(d['units']) for d in truth['documents'])==178)
check('truth PDF identities',all(truth_by[d['document_id']]['pdf_sha256']==d['pdf_sha256'] for d in scheduled))
impl=read(R/'runtime/implementation.json')
for name,want in impl['code'].items():check('implementation pin '+name,sha(name)==want)
authorization=read(R/'execution/live-authorization.json');binding=read(R/'execution/service-account/binding.json');live_intent=read(R/'execution/service-account/live-intent.json');live_result=read(R/'execution/service-account/live-result.json');live_stop=read(R/'execution/service-account/live-stop.json')
for name,relative in [('implementation_sha256','runtime/implementation.json'),('manifest_sha256','sources/source-inputs.READY.json'),('authorization_sha256','execution/live-authorization.json'),('dependencies_sha256','execution/service-account/dependencies.json')]:
    check('service binding '+name,binding[name]==sha(R/relative) and live_intent[name]==binding[name])
for letter in 'ASB':check('service freeze binding '+letter,binding['freeze_'+letter+'_sha256']==freezes[letter]['sha256'])
check('live label authorization',authorization['source_labels_freeze_sha256']==freezes['B']['sha256']==live_intent['source_labels_freeze_sha256'] and authorization['source_labels_frozen_before_outputs'] is True)
check('live authorization budget/code/source',authorization['nominal_budget_usd']==2 and authorization['implementation_sha256']==binding['implementation_sha256'] and authorization['manifest_sha256']==binding['manifest_sha256'])
check('adapter and binding hashes',live_intent['adapter_sha256']==sha(R/'execution/service-account/adapter.py') and live_intent['binding_sha256']==sha(R/'execution/service-account/binding.json'))
dependencies=read(R/'execution/service-account/dependencies.json')
for name,want in dependencies['files'].items():check('service dependency '+name,sha(name)==want)
check('dependency count',len(dependencies['files'])==live_intent['dependency_files']==2590)
check('adapter stopped no automatic retry',live_result['state']=='stopped_provider_operation' and live_stop['automatic_retry'] is False and live_intent['automatic_retry'] is False)
ops=list((RUN/'operations').iterdir());check('exactly one operation directory',len(ops)==1 and ops[0].is_dir());op=ops[0];meta=read(op/'identity.json');intent=read(op/'intent.json');status=read(op/'status.json');stop=read(op/'stop.json');request=read(op/'request.json');response=read(op/'response.body')
check('only first inventory intent',meta['kind']=='inventory' and meta['identity']['document_id']==ids[0] and len(list(RUN.rglob('intent.json')))==1)
check('durable operation binding',all(intent[k]==v for k,v in meta.items()) and intent['automatic_retry'] is False and meta['request_sha256']==sha(op/'request.json') and meta['pins_sha256']==sha(RUN/'pins.json') and op.name=='inventory-'+hashlib.sha256(canonical(meta)).hexdigest()[:24])
check('raw HTTP200 response binding',status['http_status']==200 and status['response_sha256']==sha(op/'response.body'))
check('invalid response latch no retry',stop==dict(retry_allowed=False,state='invalid_response_or_usage'))
choice=response['choices'][0];usage=response['usage']
check('length-limited completion',len(response['choices'])==1 and choice['finish_reason']=='length' and choice['native_finish_reason']=='max_output_tokens' and usage['completion_tokens']==request['max_tokens']==6144)
check('pinned actual provider/model',response['provider']=='OpenAI' and response['model'] in (impl['models']['inventory'],impl['OR_canonical_slug']))
check('freeze timing consistent',datetime.fromisoformat(freezes['S']['created_utc'])<datetime.fromisoformat(freezes['B']['created_utc'])<datetime.fromisoformat(live_intent['started_utc'])<=datetime.fromisoformat(intent['created_utc'])<datetime.fromisoformat(freezes['E']['created_utc']))
manifest=read(R/'sources/source-inputs.READY.json');check('pinned source schedule',set(ids)=={d['document_id'] for d in manifest['documents']} and pins['documents']==manifest['documents'])
check('run pins identity',pins['implementation']==impl and pins['manifest_sha256']==authorization['manifest_sha256'] and pins['authorization_sha256']==sha(R/'execution/live-authorization.json'))
source=read(RUN/'documents'/ids[0]/'source.json');user=json.loads(request['messages'][1]['content']);check('inventory source-only input',set(user)=={'source'} and user['source']==source and source['source_text_sha256']==meta['identity']['source_text_sha256'] and hashlib.sha256(source['source_text'].encode()).hexdigest()==source['source_text_sha256'])
runtime=load('r8_postrun_frozen_runtime',R/'runtime/run_pipeline.py')
check('frozen final request reproducible',runtime.normalized.requests(source)['inventory']['body']==request)
check('frozen strict parser rejects completion',choice['finish_reason']!='stop')
try:runtime.a.parse_or((op/'response.body').read_bytes())
except runtime.a.Stop as exc:parser_rejection=str(exc)
else:raise AssertionError('frozen parser accepted incomplete response')
check('frozen observed validator',runtime.validate_observation(observed) is None)
check('receipt resolves to ledger',runtime.audit_failure_receipts(observed,RUN))
absence=[]
for document in observed['documents']:
    ident=document['document_id'];folder=RUN/'documents'/ident
    artifacts={name:(folder/name).exists() for name in ('assembled.json','common-payload.json','stronger-validation.json','jev-request.json','stronger-request.json')}
    check('absent inventory/record '+ident,all(document[k] is None for k in ('inventory_sha256','record_sha256','payload_sha256')) and not any(artifacts.values()))
    check('uncalled arms '+ident,all(a['status']=='not_started' and a['called'] is False and a['source_coverage_complete'] is False and a['payload_sha256'] is None and 'judgment' not in a for a in document['arms'].values()))
    absence.append(dict(document_id=ident,runtime_gate=document['runtime_gate'],source_units=len(truth_by[ident]['units']),directory_exists=folder.exists(),forbidden_artifacts=artifacts,inventory_assessment=None,record_assessment=None))
check('no validated operation results or completed run',not list(RUN.rglob('result.json')) and not (RUN/'completed.json').exists())
check('true gates and no service outage assertion',Counter(d['runtime_gate'] for d in observed['documents'])=={'inventory_failed':1,'not_started':4} and not any(d['provider_service_error'] for d in observed['documents']) and observed['documents'][0]['failure']['kind']=='invalid_response')
check('snapshot binds observations',snapshot['observed_sha256']==sha(observed_path) and snapshot['state']=='stopped_provider_operation')
reported=Decimal(str(usage['cost']));estimate=Decimal(usage['prompt_tokens'])*Decimal(str(impl['prices']['prompt']))+Decimal(usage['completion_tokens'])*Decimal(str(impl['prices']['completion']));reservation=Decimal(str(intent['reserved_nominal_usd']));charge=max(reservation,reported)
check('reported response cost',reported==Decimal('0.0688185'))
check('snapshot conservative accounting',Decimal(str(snapshot['totals']['budget_charge_usd']))==charge==Decimal('0.100166') and snapshot['totals']['observed_accounted_usd']==0 and snapshot['totals']['operations']==1 and snapshot['totals']['jev_cases']==snapshot['totals']['stronger_cases']==0)
costs={'extraction':dict(usage_estimate_usd=float(estimate),conservative_charge_usd=float(charge),provider_reported_usd=float(reported)),**{arm:dict(usage_estimate_usd=0,conservative_charge_usd=0,provider_reported_usd=0) for arm in ('jev','stronger')}}
cost_audit=dict(schema_version='round8.postrun_cost_audit.v1',operation_id=meta['operation_id'],stage='extraction',provider_response_sha256=sha(op/'response.body'),request_sha256=sha(op/'request.json'),usage=usage,http_status=200,finish_reason=choice['finish_reason'],parser_rejection=parser_rejection,response_provider=response['provider'],response_model=response['model'],pinned_rates=impl['prices'],usage_rate_estimate_usd=str(estimate),provider_response_reported_usd=str(reported),nominal_reservation_usd=str(reservation),conservative_charge_usd=str(charge),frozen_ledger_observed_accounted_usd=snapshot['totals']['observed_accounted_usd'],ledger_note='No parsed result was persisted, so the frozen ledger observed_accounted_usd omits the charge available in raw response usage; this does not mean free execution. Conservative charge already covers it.',verifier_zero_basis='No verifier intents or operations exist in the complete frozen run inventory.',invoice_verified=False,costs=costs)
save('cost-audit.json',cost_audit);save('artifact-absence.json',dict(schema_version='round8.artifact_absence_audit.v1',observed_sha256=sha(observed_path),operation_result_files=[],documents=absence,partial_response_scored=False))
matching=dict(schema_version='round8.matching-audit.v1',reviewer='Independent postrun artifact-absence audit; no valid inventory/record exists; partial response text not scored',documents=[dict(document_id=ident,inventory=None,record=None) for ident in ids])
save('matching-audit.json',matching)
derived=copy.deepcopy(observed);derived['costs']=costs;save('observed-with-costs.json',derived)
check('cost-only derivative preserves all observations',{k:v for k,v in derived.items() if k!='costs'}==observed)
provenance=dict(schema_version='round8.cost_only_observation_derivative.v1',source_path=str(observed_path.relative_to(R)),source_sha256=sha(observed_path),derived_path='execution/postrun-audit/observed-with-costs.json',derived_sha256=sha(OUT/'observed-with-costs.json'),changes=['Added top-level costs from independently checked raw response usage, immutable reservation and proven absence of verifier intents.'],states_judgments_hashes_preserved=True,source_freeze_E_sha256=EXPECTED_E,cost_audit_sha256=sha(OUT/'cost-audit.json'),scoring_partial_raw_text=False)
save('observation-derivative.json',provenance)
scorer=load('r8_frozen_postrun_scorer',R/'protocol/evaluate.py');report=scorer.evaluate(schedule,truth,matching,derived);report['input_file_sha256']={k:sha(path) for k,path in dict(schedule=R/'execution/schedule.json',truth=R/'protocol/source-labels/truth.json',audit=OUT/'matching-audit.json',observed=OUT/'observed-with-costs.json').items()};save('evaluation-report.json',report)
check('all 178 units retained for both artifact denominators',all(sum(v['denominator'] for v in report['quality'][artifact]['source_coverage_by_category'].values())==178 for artifact in ('inventory','record')))
check('no acceptance/verifier quality and null success cost',all(v['accepted_records']==v['correct_complete_accepted']==v['unsafe_accepted']==0 and v['useful_coverage']['denominator']==5 and v['review_or_unserved_fraction']['value']==1 and v['unsafe_acceptance_fraction']['value'] is None for v in report['arms'].values()) and all(all(x is None for x in report['costs'][arm]['scenario_cost_per_correct_complete_record'].values()) for arm in ('jev','stronger')))
check('actual cohort inadequate',report['scheduled_notices']==5 and report['cohort_adequacy'] is False and report['source_truth_complete'] is True)
save('source-unit-dispositions.json',dict(schema_version='round8.unserved_source_unit_audit.v1',total_units=178,documents=[dict(document_id=ident,units=[dict(source_unit_id=u['id'],category=u['category'],inventory='unserved_artifact_absent',record='unserved_artifact_absent') for u in truth_by[ident]['units']]) for ident in ids]))
for path,want in frozen_before.items():check('freeze remains unchanged '+path,sha(path)==want)
summary=dict(schema_version='round8.postrun_audit.v1',passed=True,freezes=freezes,checks=checks,dependency_files_checked=len(dependencies['files']),scheduled_documents=5,states=5,PDF_pages=17,source_units=178,cohort_status='protocol-deviation corrected development cohort; planned8notices/6states unmet',operation_counts=dict(inventory=1,jev=0,stronger=0),valid_inventories=0,records=0,provider_http_errors=0,invalid_response_stops=1,remaining_not_started=4,costs=costs,scope_note='No valid artifact exists for semantic claim matching; all178source units are unserved, not selectively dropped or credited from partial response.',reference='Independent AI image reference, not human gold; freeze timestamps and hash bindings consistent with pre-output labeling, not an independent proof of every labeler access.',new_provider_calls=0,credentials_read=False,network_process_guard=True,frozen_files_modified=False,outputs={name:sha(OUT/name) for name in ('cost-audit.json','artifact-absence.json','matching-audit.json','observed-with-costs.json','observation-derivative.json','evaluation-report.json','source-unit-dispositions.json')})
save('audit.json',summary)
print(json.dumps(dict(passed=True,checks=len(checks),freezes={k:v['files'] for k,v in freezes.items()},source_units=178,costs=costs,accepted_per_arm=0)))
