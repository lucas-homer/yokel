"""Read-only independent mechanical execution/cost audit. No runtime or provider imports."""
import hashlib,json,math
from decimal import Decimal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent;RUN=ROOT/'execution/run'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
def save(name,value):
    path=OUT/name;path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as file:file.write(canonical(value))
checks=[]
def check(name,ok):
    checks.append({'check':name,'passed':bool(ok)})
    if not ok:raise ValueError(name)
def verify_freezes():
    hashes={};counts={}
    for name in ('freeze-A.json','freeze-S.json','freeze-B.json','freeze-E.json'):
        path=ROOT/'execution'/name;data=read(path);hashes[name]=digest(path);counts[name]=len(data['files'])
        for row in data['files']:
            p=(ROOT/row['path']).resolve();check(name+':'+row['path'],p.is_relative_to(ROOT) and p.stat().st_size==row['bytes'] and digest(p)==row['sha256'])
    return hashes,counts
before,counts=verify_freezes()
schedule=read(ROOT/'execution/schedule.json');completed=read(RUN/'completed.json');pins=read(RUN/'pins.json');pin_hash=digest(RUN/'pins.json');impl=read(ROOT/'runtime/implementation.json')
check('implementation pins equal original',pins['implementation']==impl)
check('original budget/auth/reference pins',pins['budget']==2.0 and pins['authorization_sha256']==digest(ROOT/'execution/live-authorization.json') and pins['source_labels_freeze_sha256']==before['freeze-B.json'])
check('all scheduled terminal IDs',len(schedule['documents'])==4 and {d['document_id'] for d in schedule['documents']}=={d['document_id'] for d in completed['documents']})
ops={};operation_rows=[];reported=Decimal(0);estimated=Decimal(0);reserved=Decimal(0);charge=Decimal(0);input_tokens=output_tokens=0
for folder in sorted((RUN/'operations').iterdir()):
    i=read(folder/'intent.json');meta=read(folder/'identity.json');request=read(folder/'request.json');raw=read(folder/'response.body');status=read(folder/'status.json');result=read(folder/'result.json')
    check(folder.name+': durable intent binding',set(i)==set(meta)|{'created_utc','automatic_retry'} and all(i[k]==v for k,v in meta.items()) and i['automatic_retry'] is False and i['pins_sha256']==pin_hash and i['request_sha256']==digest(folder/'request.json') and folder.name==i['kind']+'-'+hashlib.sha256(canonical(meta)).hexdigest()[:24])
    check(folder.name+': only inventory no OCR',i['kind']=='inventory' and i['pages']==0 and not (folder/'stop.json').exists())
    check(folder.name+': request routing/caps',request['model']=='openai/gpt-6.1-sol' and request['max_tokens']==6144 and request['reasoning']=={'effort':'low'} and request['provider']=={'only':['openai'],'order':['openai'],'allow_fallbacks':False,'require_parameters':True,'max_price':{'prompt':2,'completion':10}})
    estimate=len(canonical(request))+1024;calculated=Decimal(estimate)*Decimal('.000002')+Decimal(6144)*Decimal('.000010')
    check(folder.name+': reservation recomputed',estimate<=35000 and math.isclose(i['reserved_nominal_usd'],float(calculated),rel_tol=0,abs_tol=1e-12))
    check(folder.name+': raw response HTTP/model/provider',status['http_status']==200 and status['response_sha256']==digest(folder/'response.body') and raw['model']=='openai/gpt-6.1-sol' and raw['provider']=='OpenAI' and len(raw['choices'])==1 and raw['choices'][0]['finish_reason']=='stop')
    structured=json.loads(raw['choices'][0]['message']['content']);usage=raw['usage'];check(folder.name+': exact parser response and usage',structured==result['structured'] and usage==result['usage'] and result['model']==raw['model'] and result['provider']==raw['provider'])
    rate=Decimal(usage['prompt_tokens'])*Decimal('.000002')+Decimal(usage['completion_tokens'])*Decimal('.000010');cost=Decimal(str(usage['cost']));reservation=Decimal(str(i['reserved_nominal_usd']))
    check(folder.name+': usage cost reported and estimated separately',cost>=0 and math.isclose(result['reported_cost_usd'],float(cost),abs_tol=1e-12) and math.isclose(result['observed_cost_usd'],float(cost),abs_tol=1e-12) and math.isclose(result['usage_rate_estimated_usd'],float(rate),abs_tol=1e-12))
    reported+=cost;estimated+=rate;reserved+=reservation;charge+=max(reservation,cost);input_tokens+=usage['prompt_tokens'];output_tokens+=usage['completion_tokens']
    doc=i['identity']['document_id'];check('one operation per extracted document:'+doc,doc not in ops);ops[doc]={'structured':structured,'folder':folder}
    operation_rows.append({'document_id':doc,'operation_id':i['operation_id'],'request_sha256':i['request_sha256'],'response_sha256':status['response_sha256'],'result_sha256':digest(folder/'result.json'),'prompt_tokens':usage['prompt_tokens'],'completion_tokens':usage['completion_tokens'],'usage_rate_estimated_usd':float(rate),'provider_response_reported_usd':float(cost),'nominal_reserved_usd':float(reservation),'conservative_charge_usd':float(max(reservation,cost)),'elapsed_seconds':status['elapsed_seconds'],'finish_reason':'stop','provider':'OpenAI','model':'openai/gpt-6.1-sol','invoice_verified':False})
check('three successful inventory POSTs only',len(ops)==3 and completed['totals']['operations']==3 and completed['totals']['inventory_cases']==3 and completed['totals']['jev_cases']==completed['totals']['stronger_cases']==completed['totals']['ocr_pages']==0)
for key,value in [('observed_accounted_usd',reported),('nominal_reserved_usd',reserved),('budget_charge_usd',charge)]:check('ledger cost total:'+key,math.isclose(completed['totals'][key],float(value),abs_tol=1e-12))
observed=[];artifacts=[];gate_counts={};ids={d['document_id'] for d in schedule['documents']}
for scheduled in schedule['documents']:
    doc=scheduled['document_id'];folder=RUN/'documents'/doc;terminal=read(folder/'terminal.json');check('exact complete terminal:'+doc,terminal==next(d for d in completed['documents'] if d['document_id']==doc) and terminal['action_ready'] is False and terminal['production_eligible'] is False and terminal['arms']=={})
    state=terminal['state'];gate_counts[state]=gate_counts.get(state,0)+1;inv_sha=None;record_sha=None;inventory_path=None;assembled_path=None
    if state=='assembly_review':
        assembled=read(folder/'assembled.json');inventory=ops[doc]['structured'];check('assembly retains exact inventory:'+doc,assembled['inventory']==inventory and assembled['validation']['valid'] is False and assembled['record'] is None and assembled['validation']['errors']==terminal['errors'])
        save('inventories/'+doc+'.json',inventory);inventory_path=OUT/'inventories'/ (doc+'.json');inv_sha=digest(inventory_path);check('canonical inventory hash matches assembly:'+doc,inv_sha==assembled['inventory_sha256']);assembled_path=folder/'assembled.json'
    elif state=='request_size_review':
        check('size gate did not dispatch:'+doc,doc not in ops and not (folder/'assembled.json').exists())
        plan=read(folder/'inventory-plan.json');user=json.loads(plan['user']);check('exact duplicate schema before size gate:'+doc,user['response_schema']==plan['response_schema']);user.pop('response_schema')
        body={'model':'openai/gpt-6.1-sol','stream':False,'max_tokens':6144,'reasoning':{'effort':'low'},'provider':{'only':['openai'],'order':['openai'],'allow_fallbacks':False,'require_parameters':True,'max_price':{'prompt':2,'completion':10}},'messages':[{'role':'system','content':plan['system']},{'role':'user','content':canonical(user).decode()}],'response_format':{'type':'json_schema','json_schema':{'name':'round6_inventory','strict':True,'schema':plan['response_schema']}}}
        check('original full request exceeds fixed size cap:'+doc,len(canonical(body))+1024>35000)
    else:raise ValueError('unexpected terminal')
    check('no verifier dispatch artifacts:'+doc,not any((folder/name).exists() for name in ('common-payload.json','Jev-request.json','stronger-request.json','stronger-validation.json')))
    reason='pre_verifier_'+state+': '+'; '.join(terminal['errors'])
    observed.append({'document_id':doc,'inventory_sha256':inv_sha,'record_sha256':record_sha,'payload_sha256':None,'runtime_gate':state,'provider_service_error':False,'verifiers_dispatched':False,'arms':{arm:{'status':'review','payload_sha256':None,'source_coverage_complete':False,'failure_reason':reason} for arm in ('jev','stronger')}})
    artifacts.append({'document_id':doc,'inventory_path':str(inventory_path) if inventory_path else None,'inventory_sha256':inv_sha,'record_path':None,'record_sha256':None,'record_absence':'assembly invalid; normalized record null' if assembled_path else 'inventory size gate; extraction not dispatched','assembled_path':str(assembled_path) if assembled_path else None,'assembled_sha256':digest(assembled_path) if assembled_path else None,'terminal_path':str(folder/'terminal.json'),'terminal_sha256':digest(folder/'terminal.json')})
costs={'extraction':{'usage_estimate_usd':float(estimated),'conservative_charge_usd':float(charge),'provider_reported_usd':float(reported)},'jev':{'usage_estimate_usd':0,'conservative_charge_usd':0,'provider_reported_usd':0},'stronger':{'usage_estimate_usd':0,'conservative_charge_usd':0,'provider_reported_usd':0}}
save('observed.json',{'schema_version':'round6.observed.v1','documents':observed,'costs':costs})
save('matching-artifacts.json',{'schema_version':'round6.matching-artifacts.v1','documents':artifacts,'inventory_serialization':'Exact parsed inventory object, canonical UTF8 JSON sorted keys/no spaces/no newline; hash agrees frozen assembly. No invented normalized record for invalid assembly.'})
validation=read(ROOT/'execution/service-account/primary-validation-v2.json');live=read(ROOT/'execution/service-account/live-result.json')
check('v2 primary identity/smoke/live success evidence',validation['identity']=='passed' and validation['two_key_injection_smoke']=='passed' and validation['keychain_interaction']=='disabled_by_runner' and live['state']=='completed')
after,after_counts=verify_freezes();check('all freeze receipts unchanged before/after',before==after and counts==after_counts)
report={'schema_version':'round6.postrun-integrity-cost.v1','passed':True,'checks':len(checks),'freezes':before,'freeze_counts':counts,'scheduled_documents':4,'PDF_pages':14,'collection_target_achieved':False,'inventory_calls':3,'Jev_calls':0,'stronger_calls':0,'gates':gate_counts,'service_errors':0,'prompt_tokens':input_tokens,'completion_tokens':output_tokens,'nominal_reserved_usd':float(reserved),'conservative_charge_usd':float(charge),'provider_response_reported_usd':float(reported),'usage_rate_estimated_usd':float(estimated),'invoice_verified':False,'operation_rows':operation_rows,'v2_evidence':{'primary_validation_sha256':digest(ROOT/'execution/service-account/primary-validation-v2.json'),'live_result_sha256':digest(ROOT/'execution/service-account/live-result.json'),'identity':'passed','two_key_smoke':'passed','live_execution':'completed','keychain_interaction':'disabled_by_runner','desktop_lock_state':'not independently established','scope':'logged-in Mini Codex agent context; no logout/reboot claim'},'audit_provider_calls':0,'credentials_read':False,'reference_contents_semantically_read':False,'production_eligible':False,'cost_note':'Reported usage.cost differs from simple pinned rate estimate because response includes cache-write/read accounting. Reported cost is not independently billed/invoice verified. Zero verifier stage cost established by no intents, not assumed missing usage.'}
save('audit.json',report);save('checks.json',checks);print(json.dumps({k:report[k] for k in ('checks','freeze_counts','inventory_calls','gates','provider_response_reported_usd','usage_rate_estimated_usd','nominal_reserved_usd','prompt_tokens','completion_tokens')}))
