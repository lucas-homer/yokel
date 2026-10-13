"""Fixed two-stage signed adapter; durable stage intent latches each possible dispatch."""
import datetime, importlib.util, os, ssl, sys, urllib.error, urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:sys.path.insert(0,str(HERE))
import common as c
import contract as k
PYTHON=Path('/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12')
PRIOR=858310718; RESERVE=161920000; CEILING=2000000000; RUN=c.ROUND/'execution/run'
ASSEMBLY=c.BENCH/'round8-stronger-cap-probe/execution/run/documents/doc-92211b8c7ba0/assembled.json'
def cost_nano(value):
    c.require(type(value) in (int,float) and c.math.isfinite(value) and value>=0)
    from decimal import Decimal,ROUND_CEILING
    return int((Decimal(str(value))*1000000000).to_integral_value(rounding=ROUND_CEILING))
def rate_nano(usage):
    c.require(isinstance(usage,dict) and all(type(usage.get(x)) is int and usage[x]>=0 for x in ('prompt_tokens','completion_tokens')))
    return usage['prompt_tokens']*2000+usage['completion_tokens']*10000
def recoverable(raw):
    debit=RESERVE
    try:
        usage=c.strict(raw).get('usage',{})
        try:debit=max(debit,rate_nano(usage))
        except BaseException:pass
        try:debit=max(debit,cost_nano(usage.get('cost')))
        except BaseException:pass
    except BaseException:pass
    return debit

def put(path,data,keys=()):
    raw=data if isinstance(data,bytes) else c.encode(data)
    c.require(not any(key and key.encode() in raw for key in keys))
    with Path(path).open('xb') as f:f.write(raw); f.flush(); os.fsync(f.fileno())
    fd=os.open(Path(path).parent,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)
def claim(path):
    Path(path).mkdir(parents=True,exist_ok=False)
    fd=os.open(Path(path).parent,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)
def verify_baseline():
    p=c.ROUND/'prior-baseline.json'; c.require(c.file_hash(p)==c.BASELINE_SHA); rows=c.read(p)['files']; c.require(len(rows)==5114); seen=set()
    for row in rows:
        path=(c.BENCH/row['path']).resolve(); c.require(not Path(row['path']).is_absolute() and path.is_relative_to(c.BENCH.resolve()) and str(path) not in seen); seen.add(str(path))
        c.require(c.file_hash(path)==row['sha256'] and path.stat().st_size==row['bytes'])
    # Independently retain predecessor's frozen debit calculation, plus the ninth-round call.
    path=c.BENCH/'round9-live-exact-id/runtime/adapter.py'; spec=importlib.util.spec_from_file_location('r10_prior_adapter',path); prior=importlib.util.module_from_spec(spec); spec.loader.exec_module(prior)
    previous=prior.verify_prior()['prior_nanousd']; run=c.BENCH/'round9-live-exact-id/execution/run'; intent=c.read(run/'intent.json'); status=c.read(run/'status.json'); raw=(run/'response.body').read_bytes(); result=c.read(run/'result.json')
    c.require(intent['request_sha256']==c.file_hash(run/'request.json') and status['response_sha256']==c.sha(raw) and intent['reserved_nanousd']==RESERVE)
    charge=max(intent['reserved_nanousd'],recoverable(raw),result['new_budget_charge_nanousd']); c.require(previous+charge==PRIOR)
    return {'prior_nanousd':PRIOR,'round9_charge_nanousd':charge,'invoice_verified':False,'baseline_files':len(rows)}

def preflight():
    c.verify_release(); prior=verify_baseline()
    for path,want in c.read(HERE/'dependency-pins.json')['files'].items():c.require(c.file_hash(path)==want)
    assembled=c.read(ASSEMBLY); text=assembled['source']['source_text']; record=assembled['record']; pins=c.read(c.PROTO/'input-pins.json')
    c.require(k.source_hash(text)==pins['source_text_sha256'] and c.digest(record)==pins['record_canonical_sha256'])
    projected,values=k.operative(record)
    c.require(projected==c.read(c.PROTO/'stage-b.operative-record.json') and values==c.read(c.PROTO/'stage-b.operative-projection.json') and sorted(values)==c.read(c.PROTO/'operative-pointers.json') and len(values)==310 and len(k.identities(record))==70)
    planned=k.build_a(text); c.require(planned['body']==c.read(c.PROTO/'stage-a.offline-request.json') and planned['request_sha256']==pins['stage_a_request_canonical_sha256'] and planned['fits'])
    c.require(PRIOR+2*RESERVE<=CEILING); return text,record,planned,prior

def authorization_fields():
    return {'schema_version':'round10.source-first.authorization.v1','scope_sha256':c.file_hash(c.ROUND/'scope.json'),'protocol_ready_sha256':c.READY_SHA,'implementation_release_sha256':c.file_hash(c.ROUND/'implementation-release.json'),'prior_baseline_sha256':c.BASELINE_SHA,'input_pins_sha256':c.file_hash(HERE/'input-pins.json'),'stage_a_request_sha256':c.read(c.PROTO/'input-pins.json')['stage_a_request_canonical_sha256'],'stage_b_request_binding':'validated-frozen-stage-a-only; exact-source-and-record; actual-full-request-guard','prior_nanousd':PRIOR,'reservation_per_call_nanousd':RESERVE,'reservation_nanousd':2*RESERVE,'ceiling_nanousd':CEILING,'max_new_operations':2,'inventory_calls':1,'mapping_calls':1,'jev_calls':0,'input_guard':40000,'output_cap':8192,'automatic_retry':False,'repair_clipping_or_fallback':False,'production_eligible':False,'action_ready':False}

def verify_live_bindings():
    c.require(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode and Path(sys.executable).resolve()==PYTHON.resolve())
    deps=c.read(HERE/'dependencies.json'); binding=c.read(HERE/'binding.json')
    c.require(binding=={'schema_version':'round10.source-first.binding.v1','dependencies_sha256':c.file_hash(HERE/'dependencies.json'),'authorization_sha256':c.file_hash(c.ROUND/'live-authorization.json'),'scope_sha256':c.file_hash(c.ROUND/'scope.json'),'input_pins_sha256':c.file_hash(HERE/'input-pins.json')})
    c.require(deps['schema_version']=='round10.source-first.dependencies.v1' and isinstance(deps['files'],dict))
    needed={str(PYTHON.resolve()),str(c.ROUND/'scope.json'),str(c.ROUND/'live-authorization.json'),str(c.ROUND/'prior-baseline.json')}|{str(HERE/n) for n in ('adapter.py','common.py','contract.py','input-pins.json','READY.json')}
    c.require(needed<=set(deps['files']))
    for p,h in deps['files'].items():
        path=Path(p); c.require(path.is_absolute() and path.resolve()==path and path.is_file() and c.file_hash(path)==h)
    c.require(c.read(c.ROUND/'live-authorization.json')==authorization_fields())

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise c.Denied()
def post_once(body,key):
    req=urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',data=c.encode(body),method='POST',headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
    opener=urllib.request.build_opener(NoRedirect(),urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    try:
        with opener.open(req,timeout=180) as r:return r.status,r.read(2000001)
    except urllib.error.HTTPError as e:return e.code,e.read(2000001)

def native(raw):
    value=c.strict(raw); c.require(isinstance(value,dict) and not value.get('error'))
    c.require(value.get('model') in ('openai/gpt-6.1-sol','openai/gpt-6.1-sol-20260929') and value.get('provider') in (None,'OpenAI'))
    choices=value.get('choices'); c.require(isinstance(choices,list) and len(choices)==1 and isinstance(choices[0],dict)); choice=choices[0]
    c.require(choice.get('finish_reason')=='stop' and not choice.get('error')); message=choice.get('message'); c.require(isinstance(message,dict) and not message.get('refusal') and not message.get('tool_calls') and isinstance(message.get('content'),str))
    usage=value.get('usage'); charge=max(RESERVE,rate_nano(usage),cost_nano(usage.get('cost')))
    return message['content'].encode(),{'model':value['model'],'provider':value.get('provider'),'provider_identity_verified':value.get('provider')=='OpenAI','finish_reason':choice['finish_reason'],'usage':usage,'reported_cost_usd':usage['cost'],'usage_rate_estimated_nanousd':rate_nano(usage),'budget_charge_nanousd':charge,'invoice_verified':False}

def stage(folder,name,planned,text,record,inventory,key,transport,current):
    claim(folder); keys=(key,); raw=None
    dispatched=False
    try:
        c.require(planned['fits'] and current+RESERVE<=CEILING)
        put(folder/'request.json',c.encode(planned['body']),keys)
        put(folder/'intent.json',{'schema_version':'round10.stage-intent.v1','stage':name,'request_sha256':planned['request_sha256'],'source_text_sha256':k.source_hash(text),'record_sha256':c.digest(record) if name=='stage-b' else None,'inventory_sha256':c.digest(inventory) if name=='stage-b' else None,'prior_stage_debit_nanousd':current,'reserved_nanousd':RESERVE,'ceiling_nanousd':CEILING,'guarded_bytes':planned['guarded_bytes'],'output_cap':8192,'protocol_ready_sha256':c.READY_SHA,'runtime_input_pins_sha256':c.file_hash(HERE/'input-pins.json'),'automatic_retry':False,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},keys)
        dispatched=True
        status,raw=transport(planned['body'],key); c.require(type(status) is int and isinstance(raw,bytes) and len(raw)<=2000000)
        put(folder/'response.body',raw,keys); put(folder/'status.json',{'http_status':status,'response_sha256':c.sha(raw)},keys); c.require(status==200)
        content,metadata=native(raw); put(folder/'content.body',content,keys); value=c.strict(content)
        checked=k.validate_a(text,value) if name=='stage-a' else k.validate_b(text,record,inventory,value)
        put(folder/'validated.json',c.encode(value),keys)
        result={'schema_version':'round10.stage-result.v1','stage':name,'request_sha256':planned['request_sha256'],'response_sha256':c.sha(raw),'content_sha256':c.sha(content),'canonical_value_sha256':c.digest(value),'source_text_sha256':k.source_hash(text),'record_sha256':c.digest(record) if name=='stage-b' else None,'inventory_sha256':c.digest(value) if name=='stage-a' else c.digest(inventory),'protocol_ready_sha256':c.READY_SHA,'runtime_input_pins_sha256':c.file_hash(HERE/'input-pins.json'),'validation':checked,**metadata,'cumulative_budget_charge_nanousd':current+metadata['budget_charge_nanousd'],'semantic_status':'unverified','production_eligible':False,'action_ready':False}
        put(folder/'result.json',result,keys); c.require(result['cumulative_budget_charge_nanousd']<=CEILING)
        put(folder/'completed.json',{'state':'validated_frozen','result_sha256':c.file_hash(folder/'result.json'),'validated_sha256':c.file_hash(folder/'validated.json'),'response_sha256':c.sha(raw)},keys)
        return value,result
    except BaseException:
        charge=recoverable(raw) if isinstance(raw,bytes) else RESERVE
        put(folder/'stop.json',{'state':'failed_or_uncertain','budget_charge_nanousd':charge,'cumulative_budget_charge_nanousd':current+charge,'response_retained':(folder/'response.body').exists(),'provider_calls_may_have_occurred':dispatched,'automatic_retry':False,'exception_text_retained':False,'invoice_verified':False},keys)
        raise c.Denied() from None

def freeze_a(run,planned,text):
    folder=run/'stage-a'; intent=c.read(folder/'intent.json'); status=c.read(folder/'status.json'); result=c.read(folder/'result.json'); done=c.read(folder/'completed.json')
    c.require(c.file_hash(folder/'request.json')==planned['request_sha256']==intent['request_sha256']==result['request_sha256'])
    c.require(status['http_status']==200 and status['response_sha256']==c.file_hash(folder/'response.body')==result['response_sha256']==done['response_sha256'])
    content,meta=native((folder/'response.body').read_bytes()); value=c.strict(content)
    c.require(content==(folder/'content.body').read_bytes() and c.sha(content)==result['content_sha256'] and c.encode(value)==(folder/'validated.json').read_bytes() and c.digest(value)==result['canonical_value_sha256']==result['inventory_sha256']==done['validated_sha256'])
    c.require(c.file_hash(folder/'result.json')==done['result_sha256'] and result['validation']==k.validate_a(text,value) and meta['budget_charge_nanousd']==result['budget_charge_nanousd'])
    witness=c.read(run/'stage-a-freeze.json')
    expected={'files':{n:c.file_hash(folder/n) for n in ('request.json','intent.json','response.body','status.json','content.body','validated.json','result.json','completed.json')},'source_text_sha256':k.source_hash(text),'inventory_sha256':c.digest(value)}
    c.require(witness==expected); return value,result

def ledger(run):
    operations=[]
    for name in ('stage-a','stage-b'):
        folder=run/name
        if folder.exists():
            # Partial/absent intent still conservatively reserves the claimed stage.
            charge=RESERVE; raw=(folder/'response.body').read_bytes() if (folder/'response.body').exists() else None
            if raw is not None:charge=max(charge,recoverable(raw))
            for receipt in ('result.json','stop.json'):
                if (folder/receipt).exists():
                    try:charge=max(charge,c.read(folder/receipt)['budget_charge_nanousd'])
                    except BaseException:pass
            operations.append({'stage':name,'budget_charge_nanousd':charge,'reserved_nanousd':RESERVE,'state':'validated_frozen' if (folder/'completed.json').exists() else 'failed_or_uncertain'})
    return {'prior_nanousd':PRIOR,'operations':operations,'new_budget_charge_nanousd':sum(x['budget_charge_nanousd'] for x in operations),'cumulative_budget_charge_nanousd':PRIOR+sum(x['budget_charge_nanousd'] for x in operations),'ceiling_nanousd':CEILING,'invoice_verified':False}

def execute_once(run,text,record,planned,key,transport):
    run=Path(run); claim(run); keys=(key,)
    try:
        c.require(isinstance(key,str) and key.strip() and not key.startswith('op://') and planned==k.build_a(text) and planned['fits'] and record['source_text_sha256']==k.source_hash(text))
        _,aresult=stage(run/'stage-a','stage-a',planned,text,record,None,key,transport,PRIOR)
        folder=run/'stage-a'; inventory=c.read(folder/'validated.json')
        put(run/'stage-a-freeze.json',{'files':{n:c.file_hash(folder/n) for n in ('request.json','intent.json','response.body','status.json','content.body','validated.json','result.json','completed.json')},'source_text_sha256':k.source_hash(text),'inventory_sha256':c.digest(inventory)},keys)
        inventory,aresult=freeze_a(run,planned,text)
        next_plan=k.build_b(text,record,inventory); current=ledger(run)['cumulative_budget_charge_nanousd']
        put(run/'stage-b-preflight.json',{'request_sha256':next_plan['request_sha256'],'body_bytes':next_plan['body_bytes'],'guarded_bytes':next_plan['guarded_bytes'],'fits':next_plan['fits'],'current_debit_nanousd':current,'admission_with_reservation_nanousd':current+RESERVE,'within_ceiling':current+RESERVE<=CEILING,'inventory_sha256':c.digest(inventory),'source_text_sha256':k.source_hash(text),'record_sha256':c.digest(record),'stage_a_freeze_sha256':c.file_hash(run/'stage-a-freeze.json')},keys)
        c.require(next_plan['fits'] and current+RESERVE<=CEILING)
        # Recheck durable A immediately before B intent/POST; no mutable response-dependent fallback.
        again,_=freeze_a(run,planned,text); c.require(c.encode(again)==c.encode(inventory) and next_plan==k.build_b(text,record,again) and ledger(run)['cumulative_budget_charge_nanousd']==current)
        _,bresult=stage(run/'stage-b','stage-b',next_plan,text,record,inventory,key,transport,current)
        debit=ledger(run); put(run/'ledger.json',debit,keys); c.require(debit['cumulative_budget_charge_nanousd']<=CEILING)
        put(run/'completed.json',{'state':'two_stages_completed','mapping_status':bresult['validation']['mapping_status'],'source_inventory_completeness':'unverified','whole_record_fidelity':'unverified','semantic_status':'unverified','production_eligible':False,'action_ready':False,'ledger_sha256':c.file_hash(run/'ledger.json')},keys)
        return bresult
    except BaseException:
        debit=ledger(run)
        if not (run/'ledger.json').exists():put(run/'ledger.json',debit,keys)
        put(run/'stop.json',{'state':'stopped_no_retry','ledger':debit,'stage_b_dispatched':(run/'stage-b/intent.json').exists(),'stage_a_frozen':(run/'stage-a-freeze.json').exists(),'automatic_retry':False,'exception_text_retained':False,'semantic_status':'unverified','production_eligible':False,'action_ready':False},keys)
        raise c.Denied() from None

def live_initial():
    verify_live_bindings(); text,record,planned,_=preflight(); c.require(not RUN.exists() and 'OP_SERVICE_ACCOUNT_TOKEN' not in os.environ)
    key=os.environ.get('OPENROUTER_API_KEY'); c.require(isinstance(key,str) and key.strip() and not key.startswith('op://')); return execute_once(RUN,text,record,planned,key,post_once)
def main():
    try:
        c.require(len(sys.argv)==2 and sys.argv[1] in ('--check','--live-initial'))
        if sys.argv[1]=='--check':
            text,record,planned,prior=preflight(); print(c.encode({'state':'passed','stage_a_body_bytes':planned['body_bytes'],'stage_a_guarded_bytes':planned['guarded_bytes'],'stage_b_guarded_bytes':None,'prior':prior,'aggregate_max_nanousd':PRIOR+2*RESERVE,'provider_calls':0,'credentials_read':False}).decode())
        else:live_initial(); print('Source-first experiment completed; independent source/mapping audit required.')
        return 0
    except BaseException: print('Source-first adapter stopped; inspect nonsecret receipts. No retry.',file=sys.stderr); return 1
if __name__=='__main__':sys.exit(main())
