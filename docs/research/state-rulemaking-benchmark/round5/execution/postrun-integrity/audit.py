#!/usr/bin/env python3
"""Independent metadata/opaque-hash execution audit; no provider/runtime/proposer imports."""
import ast
import collections
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import statistics

B=Path(__file__).resolve().parents[2]
R=B/'execution/run'
O=Path(__file__).resolve().parent
checks=[]

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()

def unique(pairs):
    d={}
    for k,v in pairs:
        if k in d:raise ValueError('duplicate metadata key')
        d[k]=v
    return d

def load(p):return json.loads(Path(p).read_bytes(),object_pairs_hook=unique,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite JSON')))
def enc(o):return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(b):return hashlib.sha256(b).hexdigest()
def ck(name,ok,detail=None):checks.append({'check':name,'pass':bool(ok),'detail':detail})
def stamp(s):return dt.datetime.fromisoformat(s)
def confined(rel):
    p=(B/rel).resolve()
    if Path(rel).is_absolute() or not p.is_relative_to(B):raise ValueError('frozen path escapes round5')
    return p

def constants(path,names):
    found={}
    for node in ast.parse(Path(path).read_text()).body:
        if isinstance(node,ast.Assign):
            for target in node.targets:
                if isinstance(target,ast.Name) and target.id in names:found[target.id]=ast.literal_eval(node.value)
    if set(found)!=set(names):raise ValueError('missing static policy constants')
    return found

if not (R/'completed.json').exists():raise SystemExit('No completed receipt; final audit withheld.')
before={str(p.relative_to(R)):sha(p) for p in R.rglob('*') if p.is_file()}
pins=load(R/'pins.json');impl=load(B/'runtime/implementation-pins.READY.json')
manifest=load(B/'sources/source-inputs.json');auth=load(B/'execution/live-authorization.json')
pre=load(B/'execution/pre-output-binding.json');exception=load(B/'execution/freeze-A-ledger-exception.json')
freezes={k:load(B/'execution'/('freeze-'+k+'.json')) for k in ('A','S','B','E')}
freeze_hashes={k:sha(B/'execution'/('freeze-'+k+'.json')) for k in freezes}
ck('primary-E-receipt-hash',freeze_hashes['E']=='166ec1fcaa15189366982bfa66d8fe98707cc41ee21b04896334b7103dcee669')
freeze_inventory=[];freeze_counts={};exceptions=[]
for label,freeze in freezes.items():
    matches=0;seen=set()
    for e in freeze['files']:
        p=confined(e['path']);actual=sha(p);size=p.stat().st_size
        ck(label+'-unique-'+e['path'],e['path'] not in seen);seen.add(e['path'])
        same=actual==e['sha256'] and size==e['bytes']
        allowed=label=='A' and e['path']=='sources/search-access-ledger.jsonl' and exception['path']==e['path'] and exception['freeze_A_sha256']==freeze_hashes['A'] and e['bytes']==exception['original_bytes']==0 and e['sha256']==exception['original_sha256']==digest(b'') and actual==exception['current_sha256'] and size==exception['current_bytes']
        if allowed:
            ck('A-exception-current-pinned-by-S',any(x['path']==e['path'] and x['sha256']==actual and x['bytes']==size for x in freezes['S']['files']))
            exceptions.append({'path':e['path'],'original_bytes':0,'current_bytes':size,'current_sha256':actual,'exception_receipt_sha256':sha(B/'execution/freeze-A-ledger-exception.json')})
        ck(label+'-bytes-or-explicit-exception-'+e['path'],same or allowed)
        matches+=same
        freeze_inventory.append({'freeze':label,'path':e['path'],'sha256':actual,'bytes':size,'original_freeze_match':same,'authorized_append_exception':allowed})
    freeze_counts[label]={'files':len(freeze['files']),'exact_matches':matches}
ck('exactly-one-A-exception',len(exceptions)==1 and freeze_counts['A']['exact_matches']==181)
ck('implementation-pins-equality',pins['implementation']==impl)
for p,h in impl['code'].items():
    path=Path(p).resolve()
    if not path.is_relative_to(B):raise ValueError('code path outside round5')
    ck('code-pin-'+path.name,sha(path)==h)
ck('native-only-implementation',impl['provider']=='jev' and impl['runtime_channels']==['native'])
ck('manifest-source-pin',pins['manifest_sha256']==sha(B/'sources/source-inputs.json')==auth['manifest_sha256'])
ck('same-scheduled-records',pins['documents']==manifest['documents'])
required_auth={'schema_version','implementation_sha256','manifest_sha256','source_labels_frozen_before_outputs','source_labels_freeze_sha256','nominal_budget_usd'}
ck('exact-authorization-keys',set(auth)==required_auth and auth['schema_version']=='round5.live-authorization.v1')
ck('authorization-run-pin',sha(B/'execution/live-authorization.json')==pins['authorization_sha256']==pre['authorization_sha256'])
ck('implementation-authorization',auth['implementation_sha256']==sha(B/'runtime/implementation-pins.READY.json'))
ck('external-label-freeze-binding',auth['source_labels_freeze_sha256']==pins['source_labels_freeze_sha256']==pre['freeze_B_sha256']==freeze_hashes['B'] and auth['source_labels_frozen_before_outputs'] is True)
ck('pre-output-A-S-binding',pre['freeze_A_sha256']==freeze_hashes['A'] and pre['freeze_S_sha256']==freeze_hashes['S'])
ck('pre-output-absent-run-attestation',pre['run_directory_absent'] is True)
ck('pre-output-A-exception-disclosed',pre['freeze_A']['changed']==['sources/search-access-ledger.jsonl'] and pre['freeze_A']['unchanged'] is False)
ck('freeze-chronology',stamp(freezes['A']['created_utc'])<stamp(freezes['S']['created_utc'])<stamp(freezes['B']['created_utc'])<=stamp(pre['created_utc'])<stamp(freezes['E']['created_utc']))
ck('nominal-cap-binding',auth['nominal_budget_usd']==pins['budget']==.1)
units={u['document_id']:u for u in manifest['documents']};ck('eight-documents',len(units)==8)
ck('twenty-two-pages',sum(u['pdf_pages'] for u in units.values())==22)
for ident,u in units.items():
    for kind in ('pdf','text'):
        path=(B/'sources'/u[kind+'_path']).resolve()
        if not path.is_relative_to((B/'sources').resolve()):raise ValueError('source escapes root')
        ck('source-hash-'+ident+'-'+kind,sha(path)==u[kind+'_sha256'])

base=constants(B/'runtime/jev_frozen.py',{'RUBRICS','POLICY','RATES','JEV_MODEL'})
policy=constants(B/'runtime/run_pipeline.py',{'OLD_PREFIX','NOTICE_PREFIX'})
full_policy=policy['NOTICE_PREFIX']+base['POLICY'][len(policy['OLD_PREFIX']):]
ck('policy-base-prefix',base['POLICY'].startswith(policy['OLD_PREFIX']))
ck('policy-rubric-pin',digest(enc({'policy':full_policy,'rubrics':base['RUBRICS']}))==impl['policy_sha256'])
favorable={'support':'supported','role':'matched','condition':'preserved','conflict':'absent'}
operation_rows=[];parsed_by_id={};starts=[];latencies=[];reserved=estimated=charged=0.0;inputs=outputs=0;stop_count=0
for folder in sorted((R/'operations').iterdir()):
    if not folder.is_dir():continue
    ck('operation-complete-files-'+folder.name,all((folder/n).exists() for n in ('identity.json','request.json','intent.json','response.body','status.json','result.json')))
    identity=load(folder/'identity.json');intent=load(folder/'intent.json');request=load(folder/'request.json');raw=load(folder/'response.body');status=load(folder/'status.json');result=load(folder/'result.json')
    op=intent['operation_id'];document=intent['identity']['document_id'];starts.append(stamp(intent['created_utc']))
    stop_count+=(folder/'stop.json').exists()
    ck('jev-only-operation-'+op,intent['kind']=='jev' and intent['pages']==0 and document in units)
    ck('identity-intent-'+op,all(intent[k]==v for k,v in identity.items()))
    ck('folder-identity-'+op,folder.name=='jev-'+digest(enc(identity))[:24])
    ck('single-attempt-policy-'+op,intent['automatic_retry'] is False)
    ck('request-identity-'+op,sha(folder/'request.json')==intent['request_sha256']==identity['request_sha256'])
    ck('pin-identity-'+op,intent['pins_sha256']==sha(R/'pins.json'))
    ck('provider-model-'+op,request['model']==raw['model']==base['JEV_MODEL']=='jev-1.13.0')
    ck('request-top-whitelist-'+op,set(request)=={'model','state','questions'})
    ck('state-whitelist-'+op,set(request['state'])=={'source_text','candidate','evidence'})
    ck('full-original-native-text-hash-'+op,digest(request['state']['source_text'].encode())==units[document]['text_sha256'])
    expected_questions={k:{'type':'choice','instructions':full_policy+' Decide '+k+' for `candidate` against `source_text` and `evidence`.','criteria':v} for k,v in base['RUBRICS'].items()}
    ck('four-frozen-rubrics-'+op,request['questions']==expected_questions)
    ck('response-hash-'+op,sha(folder/'response.body')==status['response_sha256'])
    ck('successful-HTTP-'+op,status['http_status']==200)
    latency=status['elapsed_seconds'];ck('finite-latency-'+op,type(latency) in (int,float) and math.isfinite(latency) and latency>=0);latencies.append(latency)
    ck('label-before-operation-'+op,stamp(freezes['B']['created_utc'])<=stamp(pre['created_utc'])<stamp(intent['created_utc']))
    usage=raw['usage'];ck('usage-int-nonnegative-'+op,all(type(usage[k]) is int and usage[k]>=0 for k in ('input_tokens','output_tokens')))
    ck('raw-usage-retained-'+op,result['usage']==usage)
    inputs+=usage['input_tokens'];outputs+=usage['output_tokens']
    cost=usage['input_tokens']*base['RATES']['jev'][0];reserve=(len((folder/'request.json').read_bytes())+1024)*base['RATES']['jev'][0]
    ck('usage-rate-cost-'+op,abs(result['observed_cost_usd']-cost)<1e-12 and result['usage_cost_observed_usd'] is None)
    ck('reservation-formula-'+op,abs(intent['reserved_nominal_usd']-reserve)<1e-12)
    ck('answers-four-keys-'+op,set(raw['answers'])==set(base['RUBRICS']))
    labels={}
    for k,rubric in base['RUBRICS'].items():
        answer=raw['answers'][k];probs=answer['probabilities'];confidence=answer['confidence'];choice=answer['choice']
        valid=answer['type']=='choice' and choice in rubric and set(probs)==set(rubric) and all(type(v) in (int,float) and math.isfinite(v) and 0<=v<=1 for v in probs.values()) and abs(sum(probs.values())-1)<=.02 and type(confidence) in (int,float) and math.isfinite(confidence) and 0<=confidence<=1
        ck('Choice-contract-'+op+'-'+k,valid)
        highest=max(probs.values());tied=sum(abs(v-highest)<.000001 for v in probs.values())>1
        label='insufficient' if tied else choice;labels[k]=label
        ck('Choice-highest-'+op+'-'+k,probs[choice]>=highest-.000001)
        expected={'label':label,'raw_label':choice,'probabilities':probs,'confidence':confidence,'reason':'tied_distribution' if tied else 'model_choice'}
        ck('exact-dimension-retention-'+op+'-'+k,result['dimensions'][k]==expected)
    accepted=not result['deterministic']['blocking_issues'] and all(labels[k]==v for k,v in favorable.items())
    ck('raw-categorical-conjunction-'+op,result['disposition']==('accept_shadow' if accepted else 'review') and result['shadow_status']==('text_supported' if accepted else 'review'))
    ck('unverified-provider-result-'+op,result['source_fidelity']=='unverified' and result['notice_completeness']=='unverified' and result['production_eligible'] is False and result['operation_status']=='completed')
    ck('unique-operation-ID-'+op,op not in parsed_by_id);parsed_by_id[op]=result
    reserved+=reserve;estimated+=cost;charged+=max(reserve,cost)
    operation_rows.append({'operation_id':op,'document_id':document,'input_tokens':usage['input_tokens'],'output_tokens':usage['output_tokens'],'usage_rate_estimated_usd':cost,'reserved_nominal_usd':reserve,'elapsed_seconds':latency,'raw_favorable':accepted})
ck('exactly-nine-successful-operations',len(operation_rows)==9 and stop_count==0)
ck('no-recorded-OCR-operation',not list((R/'operations').glob('ocr-*')))
ck('no-uncertain-or-temporary-files',not list(R.rglob('*.tmp')))
ck('Jev-case-cap',len(operation_rows)<=80)
ck('budget-cap',charged<=pins['budget'])
ck('E-after-last-operation-start',not starts or max(starts)<stamp(freezes['E']['created_utc']))

completion=load(R/'completed.json');document_rows=[];terminal_status=collections.Counter();blocks=collections.Counter();seen_completed=[]
for ident,u in units.items():
    folder=R/'documents'/ident
    record=load(folder/'native/pipeline-record.json');rows=load(folder/'native/results.json');terminal=load(folder/'shadow-observations.json')
    ck('native-record-source-'+ident,record['document_id']==ident and record['channel']=='native' and record['text_sha256']==u['text_sha256'] and record['source_scope']==u['scope'])
    ck('untruncated-context-'+ident,record['full_source_context_map']['truncated'] is False)
    ck('case-counts-'+ident,len(record['candidates'])==len(rows)==len(terminal['observations']))
    ck('terminal-research-only-'+ident,terminal['production_eligible'] is False and terminal['action_ready'] is False and terminal['source_fidelity']=='not_verified' and terminal['document_completeness']=='requires_independent_source_audit' and terminal['fallback_decision']=='native_only_no_ocr')
    items={x['case']['case_id']:x for x in record['candidates']}
    ck('unique-candidates-'+ident,len(items)==len(record['candidates']))
    for row in rows:
        case_id=row['case_id'];item=items[case_id]
        ck('case-result-file-'+case_id,load(folder/'native'/(case_id+'.json'))==row)
        ck('candidate-raw-trace-'+case_id,row['raw_literal']==item['raw_literal'] and row['candidate_value']==item['case']['candidate']['value'] and row['pipeline_issues']==item['issues'])
        if row['operation_status']=='completed':
            ck('completed-case-ledger-'+case_id,case_id in parsed_by_id)
            opfolder=next(p for p in (R/'operations').iterdir() if p.is_dir() and load(p/'intent.json')['operation_id']==case_id)
            identity=load(opfolder/'identity.json')
            ck('case-identity-hash-'+case_id,identity['identity']['case_sha256']==digest(enc(item['case'])) and identity['identity']['channel']=='native')
            ck('case-state-request-hash-'+case_id,digest(enc({k:item['case'][k] for k in ('source_text','candidate','evidence')}))==digest(enc(load(opfolder/'request.json')['state'])))
            ck('provider-dimensions-copied-'+case_id,row['dimensions']==parsed_by_id[case_id]['dimensions'] and row['usage']==parsed_by_id[case_id]['usage'])
        else:
            ck('blocked-not-attempted-'+case_id,row['operation_status']=='not_attempted' and bool(row['deterministic']['blocking_issues']) and case_id not in parsed_by_id)
            blocks.update(row['deterministic']['blocking_issues'])
    for field in ('comment_deadline','submission_email'):
        field_rows=[x for x in rows if x['field']==field]
        winners={enc(x['candidate_value']) for x in field_rows if parsed_by_id.get(x['case_id'],{}).get('shadow_status')=='text_supported'}
        resolved=False
        if len(winners)==1:
            winner=next(iter(winners))
            resolved=all(parsed_by_id.get(x['case_id'],{}).get('shadow_status')=='text_supported' if enc(x['candidate_value'])==winner else parsed_by_id.get(x['case_id'],{}).get('dimensions',{}).get('role',{}).get('label')=='mismatched' for x in field_rows)
        for row in field_rows:
            expected_supported=resolved and parsed_by_id.get(row['case_id'],{}).get('shadow_status')=='text_supported'
            ck('competition-resolution-'+row['case_id'],row['field_competition_resolved']==resolved and row['shadow_status']==('text_supported' if expected_supported else 'review'))
    for row,obs in zip(rows,terminal['observations']):
        acceptable=row['shadow_status']=='text_supported' and u['scope']=='full_notice'
        expected={**row,'shadow_status':'text_supported' if acceptable else 'review','disposition':'accept_shadow' if acceptable else 'review','action_readiness':'requires_source_verification' if acceptable else 'not_ready','stage':'terminal_shadow_observation','channel_disagreement':False,'unresolved_channel_evidence':False,'production_eligible':False,'source_fidelity':'unverified','notice_completeness':'unverified'}
        ck('exact-terminal-projection-'+row['case_id'],obs==expected);terminal_status[obs['shadow_status']]+=1
    seen_completed.append(terminal)
    document_rows.append({'document_id':ident,'state':'completed','candidates':len(rows),'completed_Jev_cases':sum(x['operation_status']=='completed' for x in rows),'deterministically_blocked':sum(x['operation_status']=='not_attempted' for x in rows),'terminal_supported':sum(x['shadow_status']=='text_supported' for x in terminal['observations']),'terminal_review':sum(x['shadow_status']=='review' for x in terminal['observations'])})
ck('all-scheduled-completed-receipt',completion['documents']==seen_completed and completion['production_eligible'] is False)
ck('twenty-two-total-candidates',sum(x['candidates'] for x in document_rows)==22)
ck('nine-cases-accounted',sum(x['completed_Jev_cases'] for x in document_rows)==len(parsed_by_id))
totals=completion['totals']
ck('receipt-operation-counts',totals['operations']==totals['jev_cases']==9 and totals['ocr_pages']==0)
for k,value in [('nominal_reserved_usd',reserved),('observed_accounted_usd',estimated),('budget_charge_usd',charged)]:ck('receipt-'+k,abs(totals[k]-value)<1e-12)
for e in freeze_inventory:ck('unchanged-during-audit-'+e['freeze']+'-'+e['path'],sha(B/e['path'])==e['sha256'])
after={str(p.relative_to(R)):sha(p) for p in R.rglob('*') if p.is_file()}
ck('run-unchanged-during-audit',before==after)
failed=[x for x in checks if not x['pass']]
result={'status':'completed_integrity_audit' if not failed else 'integrity_checks_failed','checks_passed':len(checks)-len(failed),'checks_total':len(checks),'failed_checks':failed,
 'scheduled_documents':len(units),'PDF_pages':22,'candidates':22,'Jev_operations':len(operation_rows),'OCR_operations':0,'stop_records':stop_count,
 'documents':document_rows,'terminal_status_counts':dict(terminal_status),'deterministic_block_reasons':dict(blocks),'operations':operation_rows,
 'costs':{'usage_input_tokens':inputs,'usage_output_tokens':outputs,'Jev_usage_rate_estimated_usd':estimated,'provider_reported_invoice_usd':None,'nominal_reserved_usd':reserved,'conservative_budget_charge_usd':charged,'cap_usd':.1,'actual_invoice_verified':False},
 'latency_seconds':{'sum':sum(latencies),'mean':statistics.mean(latencies),'min':min(latencies),'max':max(latencies)},
 'freeze_counts':freeze_counts,'freeze_A_authorized_exceptions':exceptions,'freeze_receipt_hashes':freeze_hashes,
 'label_binding':{'external_receipt_hash':freeze_hashes['B'],'labels_frozen_utc':freezes['B']['created_utc'],'pre_output_binding_utc':pre['created_utc'],'first_operation_utc':min(starts).isoformat(),'run_absent_at_binding_primary_attestation':True},
 'boundaries':{'provider_calls_by_audit':0,'runtime_or_proposer_imported':False,'native_source_text_decoded':False,'source_or_image_content_inspected':False,'label_contents_inspected':False,'labels_hashed_as_opaque_bytes_only':True,'accuracy_measured':False},
 'execution_artifacts_unchanged':before==after,'execution_artifact_count':len(before),
 'limitations':['Ledger shows nine single-attempt successful operations; external provider-internal transport history cannot be independently reconstructed.',
 'Primary reports an earlier 1Password timeout before run creation with no calls; retained successful ledger does not independently prove that negative event.',
 'Jev cost is usage × pinned rate, not provider-reported charge or verified invoice.',
 'Freeze chronology and hash binding plus primary absent-run attestation establish the retained evidence; not an independent OS isolation/timestamp authority.',
 'Research-only terminal indicators do not certify source fidelity/completeness or substantive field accuracy.']}
(O/'audit.json').write_text(json.dumps(result,indent=2)+'\n');(O/'checks.json').write_text(json.dumps(checks,indent=2)+'\n')
(O/'frozen-hash-inventory.json').write_text(json.dumps(freeze_inventory,indent=2)+'\n');(O/'execution-hashes.json').write_text(json.dumps(before,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('status','checks_passed','checks_total','failed_checks','scheduled_documents','candidates','Jev_operations','terminal_status_counts','costs','latency_seconds','freeze_counts','label_binding')},indent=2))
