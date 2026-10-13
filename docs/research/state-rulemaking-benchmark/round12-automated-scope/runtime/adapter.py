"""Fixed D/A/C/B adapter: exclusive durable claims, immutable freezes, no resume."""
import datetime, importlib.util, os, ssl, sys, urllib.error, urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:sys.path.insert(0,str(HERE))
import common as c
import contract as k
PYTHON=Path('/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12')
PRIOR=1182150718; RESERVE=161920000; CEILING=2000000000; RUN=c.ROUND/'execution/run'
ORDER=('D','A','C','B'); RECEIPTS=('request.json','intent.json','response.body','status.json','content.body','validated.json','result.json','completed.json')
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
    with Path(path).open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    fd=os.open(Path(path).parent,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)
def claim(path):
    Path(path).mkdir(parents=True,exist_ok=False)
    fd=os.open(Path(path).parent,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)
def verify_baseline():
    p=c.ROUND/'prior-baseline.json';c.require(c.file_hash(p)==c.BASELINE_SHA);rows=c.read(p)['files'];c.require(len(rows)==6829);seen=set();targets=c.read(HERE/'baseline-target-witness.json')
    c.require(set(targets)=={row['path'] for row in rows})
    for row in rows:
        path=(c.BENCH/row['path']).resolve();c.require(not Path(row['path']).is_absolute() and path.is_relative_to(c.BENCH.resolve()) and row['path'] not in seen and str(path)==targets[row['path']]);seen.add(row['path']);c.verify_pin(path,row)
    # The unchanged historical calculator preserves predecessor rounding.
    path=c.BENCH/'round9-live-exact-id/runtime/adapter.py';spec=importlib.util.spec_from_file_location('r12_prior_adapter',path);prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
    previous=prior.verify_prior()['prior_nanousd'];root=c.BENCH/'round9-live-exact-id/execution/run'
    intent=c.read(root/'intent.json');status=c.read(root/'status.json');raw=(root/'response.body').read_bytes();result=c.read(root/'result.json')
    c.require(intent['request_sha256']==c.file_hash(root/'request.json') and status['response_sha256']==c.sha(raw) and intent['reserved_nanousd']==RESERVE)
    debit=previous+max(RESERVE,recoverable(raw),result['new_budget_charge_nanousd']);c.require(debit==858310718)
    r10=c.BENCH/'round10-source-first/execution/run';old=c.read(r10/'ledger.json');charges=[]
    for name in ('stage-a','stage-b'):
        folder=r10/name;intent=c.read(folder/'intent.json');status=c.read(folder/'status.json');raw=(folder/'response.body').read_bytes();result=c.read(folder/'result.json');done=c.read(folder/'completed.json')
        c.require(intent['request_sha256']==c.file_hash(folder/'request.json')==result['request_sha256'] and intent['reserved_nanousd']==RESERVE)
        c.require(status['http_status']==200 and status['response_sha256']==c.sha(raw)==result['response_sha256']==done['response_sha256'])
        content,meta=native(raw);value=c.strict(content)
        c.require(content==(folder/'content.body').read_bytes() and c.encode(value)==(folder/'validated.json').read_bytes() and c.sha(content)==result['content_sha256'])
        c.require(c.file_hash(folder/'result.json')==done['result_sha256'] and c.file_hash(folder/'validated.json')==done['validated_sha256'])
        c.require(intent['prior_stage_debit_nanousd']==debit and result['cumulative_budget_charge_nanousd']==debit+meta['budget_charge_nanousd'])
        charge=max(RESERVE,recoverable(raw),result['budget_charge_nanousd']);charges.append({'stage':name,'budget_charge_nanousd':charge,'reserved_nanousd':RESERVE,'state':'validated_frozen'});debit+=charge
    c.require(old['operations']==charges and old['prior_nanousd']==858310718 and old['new_budget_charge_nanousd']==sum(x['budget_charge_nanousd'] for x in charges) and old['cumulative_budget_charge_nanousd']==debit==PRIOR)
    return {'prior_nanousd':PRIOR,'round10_operations':charges,'baseline_files':len(rows),'invoice_verified':False}
def read_inputs():
    text=(c.ROUND/'source/26-19-016.txt').read_bytes().decode('utf-8');record=c.read(c.ROUND/'candidate/candidate.json');pins=c.read(HERE/'input-pins.json')
    c.require(k.source_hash(text)==pins['source_text_sha256'] and c.digest(record)==pins['record_canonical_sha256'] and record['source_text_sha256']==k.source_hash(text))
    projected,values=k.operative(record)
    c.require(projected==c.read(HERE/'operative-record.json') and values==c.read(HERE/'operative-values.json') and k.identities(record)==c.read(HERE/'identity-witness.json') and sorted(values)==c.read(HERE/'operative-pointers.json'))
    return text,record
def integrity(text,record):
    c.verify_release()
    for path,want in c.read(HERE/'code-pins.json')['files'].items():c.verify_pin(path,want)
    nowtext,nowrecord=read_inputs();c.require(nowtext==text and c.encode(nowrecord)==c.encode(record))
def preflight():
    c.verify_release();prior=verify_baseline()
    for path,want in c.read(HERE/'dependency-pins.json')['files'].items():c.verify_pin(path,want)
    text,record=read_inputs();integrity(text,record);plans={'D':k.build_d(text,record),'A':k.build_a(text)};pins=c.read(HERE/'input-pins.json')
    for name,plan in plans.items():c.require(plan['request_sha256']==pins['fixed_request_sha256'][name] and plan['body']==c.read(HERE/f'stage-{name.lower()}.offline-request.json'))
    c.require(PRIOR+4*RESERVE<=CEILING);return text,record,plans,prior

def authorization_fields():
    return {'schema_version':'round12.automated-scope.authorization.v1','scope_sha256':c.file_hash(c.ROUND/'scope.json'),'protocol_ready_sha256':c.READY_SHA,'implementation_release_sha256':c.file_hash(c.ROUND/'implementation-release.json'),'prior_baseline_sha256':c.BASELINE_SHA,'input_pins_sha256':c.file_hash(HERE/'input-pins.json'),'fixed_request_sha256':c.read(HERE/'input-pins.json')['fixed_request_sha256'],'dynamic_request_binding':'C:exact-source-and-frozen-A; B:same-source-candidate-A-and-lossless-frozen-C; actual-full-request-guard','prior_nanousd':PRIOR,'reservation_per_call_nanousd':RESERVE,'reservation_nanousd':4*RESERVE,'ceiling_nanousd':CEILING,'max_new_operations':4,'direct_calls':1,'inventory_calls':1,'scope_calls':1,'mapping_calls':1,'jev_calls':0,'input_guard':40000,'output_cap':8192,'automatic_retry':False,'repair_clipping_or_fallback':False,'human_scope_input':False,'reference_input':False,'production_eligible':False,'action_ready':False}
def verify_live_bindings():
    c.require(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode and Path(sys.executable).resolve()==PYTHON.resolve())
    deps=c.read(HERE/'dependencies.json');binding=c.read(HERE/'binding.json')
    c.require(binding=={'schema_version':'round12.automated-scope.binding.v1','dependencies_sha256':c.file_hash(HERE/'dependencies.json'),'authorization_sha256':c.file_hash(c.ROUND/'live-authorization.json'),'scope_sha256':c.file_hash(c.ROUND/'scope.json'),'input_pins_sha256':c.file_hash(HERE/'input-pins.json')})
    c.require(deps['schema_version']=='round12.automated-scope.dependencies.v1' and isinstance(deps['files'],dict) and 0<len(deps['files'])<=10000)
    needed=set(c.read(HERE/'dependency-pins.json')['files'])|set(c.read(HERE/'input-pins.json')['files'])|set(c.read(HERE/'code-pins.json')['files'])|{str(PYTHON.resolve()),str(c.ROUND/'scope.json'),str(c.ROUND/'live-authorization.json'),str(c.ROUND/'prior-baseline.json')}|{str(HERE/n) for n in ('adapter.py','common.py','contract.py','scope_codec.py','code-pins.json','input-pins.json','READY.json')}
    c.require(needed<=set(deps['files']))
    for p,h in deps['files'].items():
        path=Path(p);c.require(path.is_absolute() and path.resolve()==path and path.is_file() and not path.is_relative_to(c.ROUND/'reference'));c.verify_pin(path,h)
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
    value=c.strict(raw);c.require(isinstance(value,dict) and not value.get('error'))
    c.require(value.get('model') in ('openai/gpt-6.1-sol','openai/gpt-6.1-sol-20260929') and value.get('provider') in (None,'OpenAI'))
    choices=value.get('choices');c.require(isinstance(choices,list) and len(choices)==1 and isinstance(choices[0],dict));choice=choices[0]
    c.require(choice.get('finish_reason')=='stop' and not choice.get('error'));message=choice.get('message');c.require(isinstance(message,dict) and not message.get('refusal') and not message.get('tool_calls') and isinstance(message.get('content'),str))
    usage=value.get('usage');charge=max(RESERVE,rate_nano(usage),cost_nano(usage.get('cost')))
    return message['content'].encode(),{'model':value['model'],'provider':value.get('provider'),'provider_identity_verified':value.get('provider')=='OpenAI','finish_reason':choice['finish_reason'],'usage':usage,'reported_cost_usd':usage['cost'],'usage_rate_estimated_nanousd':rate_nano(usage),'budget_charge_nanousd':charge,'invoice_verified':False}
def bindings(name,text,record,inventory,scope):
    return {'stage':name,'source_text_sha256':k.source_hash(text),'record_sha256':c.digest(record) if name in ('D','B') else None,'operative_record_sha256':c.digest(k.operative(record)[0]) if name in ('D','B') else None,'inventory_sha256':c.digest(inventory) if name in ('C','B') else None,'scope_sha256':c.digest(scope) if name=='B' else None,'protocol_ready_sha256':c.READY_SHA,'runtime_input_pins_sha256':c.file_hash(HERE/'input-pins.json')}
def stage(folder,name,planned,text,record,inventory,scope,key,transport,current):
    c.require(planned['fits'] and current+RESERVE<=CEILING);claim(folder);keys=(key,);raw=None;dispatched=False;safe=True
    try:
        put(folder/'request.json',c.encode(planned['body']),keys)
        intent={'schema_version':'round12.stage-intent.v1',**bindings(name,text,record,inventory,scope),'request_sha256':planned['request_sha256'],'prior_stage_debit_nanousd':current,'reserved_nanousd':RESERVE,'ceiling_nanousd':CEILING,'guarded_bytes':planned['guarded_bytes'],'output_cap':8192,'automatic_retry':False,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
        put(folder/'intent.json',intent,keys);dispatched=True
        status,raw=transport(planned['body'],key)
        safe=type(status) is int and isinstance(raw,bytes) and len(raw)<=2000000 and key.encode() not in raw;c.require(safe)
        put(folder/'response.body',raw,keys);put(folder/'status.json',{'http_status':status,'response_sha256':c.sha(raw)},keys);c.require(status==200)
        content,metadata=native(raw);put(folder/'content.body',content,keys);value=c.strict(content);checked=k.validate(name,text,record,inventory,scope,value)
        put(folder/'validated.json',c.encode(value),keys)
        result={'schema_version':'round12.stage-result.v1',**bindings(name,text,record,inventory,scope),'request_sha256':planned['request_sha256'],'response_sha256':c.sha(raw),'content_sha256':c.sha(content),'canonical_value_sha256':c.digest(value),'validation':checked,**metadata,'cumulative_budget_charge_nanousd':current+metadata['budget_charge_nanousd'],**k.FLAGS}
        put(folder/'result.json',result,keys);c.require(result['cumulative_budget_charge_nanousd']<=CEILING)
        put(folder/'completed.json',{'state':'validated_frozen','result_sha256':c.file_hash(folder/'result.json'),'validated_sha256':c.file_hash(folder/'validated.json'),'response_sha256':c.sha(raw)},keys)
        return value,result
    except BaseException:
        charge=recoverable(raw) if isinstance(raw,bytes) else RESERVE
        # Only durable safe D failure receipts can admit the separate A arm.
        receipt_safe=safe and (not isinstance(raw,bytes) or ((folder/'status.json').exists() and (folder/'response.body').exists() and c.file_hash(folder/'response.body')==c.sha(raw)))
        put(folder/'stop.json',{'state':'failed_or_uncertain','budget_charge_nanousd':charge,'cumulative_budget_charge_nanousd':current+charge,'response_retained':(folder/'response.body').exists(),'provider_calls_may_have_occurred':dispatched,'safe_separate_arm_continuation':receipt_safe,'automatic_retry':False,'exception_text_retained':False,'invoice_verified':False},keys)
        raise c.Denied() from None

def freeze_write(run,name,text,record,inventory,scope,key):
    folder=run/f'stage-{name.lower()}';put(run/f'stage-{name.lower()}-freeze.json',{'files':{n:c.file_hash(folder/n) for n in RECEIPTS},'bindings':bindings(name,text,record,inventory,scope)},(key,))
def freeze_read(run,name,planned,text,record,inventory=None,scope=None):
    folder=run/f'stage-{name.lower()}';witness=c.read(run/f'stage-{name.lower()}-freeze.json');c.require(witness=={'files':{n:c.file_hash(folder/n) for n in RECEIPTS},'bindings':bindings(name,text,record,inventory,scope)})
    intent=c.read(folder/'intent.json');status=c.read(folder/'status.json');result=c.read(folder/'result.json');done=c.read(folder/'completed.json')
    for field,value in bindings(name,text,record,inventory,scope).items():c.require(intent[field]==result[field]==value)
    c.require(c.file_hash(folder/'request.json')==planned['request_sha256']==intent['request_sha256']==result['request_sha256'] and intent['reserved_nanousd']==RESERVE and intent['guarded_bytes']==planned['guarded_bytes'])
    c.require(status['http_status']==200 and status['response_sha256']==c.file_hash(folder/'response.body')==result['response_sha256']==done['response_sha256'])
    content,meta=native((folder/'response.body').read_bytes());value=c.strict(content)
    c.require(content==(folder/'content.body').read_bytes() and c.sha(content)==result['content_sha256'] and c.encode(value)==(folder/'validated.json').read_bytes() and c.digest(value)==result['canonical_value_sha256']==done['validated_sha256'])
    c.require(c.file_hash(folder/'result.json')==done['result_sha256'] and result['validation']==k.validate(name,text,record,inventory,scope,value) and all(result[x]==v for x,v in meta.items()))
    return value,result

def ledger(run):
    operations=[];outcomes={}
    for name in ORDER:
        folder=run/f'stage-{name.lower()}';outcomes[name]='not_attempted'
        admission=run/f'stage-{name.lower()}-preflight.json'
        if not folder.exists() and admission.exists():
            check=c.read(admission);outcomes[name]='not_admitted_guard' if not check['fits'] else 'not_admitted_budget' if not check['within_ceiling'] else 'not_dispatched'
        if folder.exists():
            charge=RESERVE;raw=(folder/'response.body').read_bytes() if (folder/'response.body').exists() else None
            if raw is not None:charge=max(charge,recoverable(raw))
            for receipt in ('result.json','stop.json'):
                if (folder/receipt).exists():
                    try:charge=max(charge,c.read(folder/receipt)['budget_charge_nanousd'])
                    except BaseException:pass
            state='validated_frozen' if (folder/'completed.json').exists() else 'failed_or_uncertain';outcomes[name]=state
            operations.append({'stage':name,'budget_charge_nanousd':charge,'reserved_nanousd':RESERVE,'state':state})
    new=sum(x['budget_charge_nanousd'] for x in operations)
    return {'prior_nanousd':PRIOR,'operations':operations,'planned_outcomes':outcomes,'new_budget_charge_nanousd':new,'cumulative_budget_charge_nanousd':PRIOR+new,'ceiling_nanousd':CEILING,'invoice_verified':False}
def pre_admission(run,name,plan,text,record,inventory,scope,key):
    current=ledger(run)['cumulative_budget_charge_nanousd'];put(run/f'stage-{name.lower()}-preflight.json',{'request_sha256':plan['request_sha256'],'body_bytes':plan['body_bytes'],'guarded_bytes':plan['guarded_bytes'],'fits':plan['fits'],'current_debit_nanousd':current,'admission_with_reservation_nanousd':current+RESERVE,'within_ceiling':current+RESERVE<=CEILING,**bindings(name,text,record,inventory,scope)},(key,));return current

def execute_once(run,text,record,plans,key,transport,integrity_check=integrity):
    run=Path(run);claim(run);keys=(key,);inventory=scope=None;direct=None
    try:
        c.require(isinstance(key,str) and key.strip() and not key.startswith('op://') and plans=={'D':k.build_d(text,record),'A':k.build_a(text)});integrity_check(text,record)
        put(run/'inputs-freeze.json',{'source_text_sha256':k.source_hash(text),'record_sha256':c.digest(record),'input_pins_sha256':c.file_hash(HERE/'input-pins.json')},keys)
        for name in ORDER:
            integrity_check(text,record);c.require(c.read(run/'inputs-freeze.json')=={'source_text_sha256':k.source_hash(text),'record_sha256':c.digest(record),'input_pins_sha256':c.file_hash(HERE/'input-pins.json')})
            if name in ('C','B'):
                inventory,_=freeze_read(run,'A',plans['A'],text,record);k.wire_decode(text,k.wire_encode(text,inventory),inventory)
            if name=='C':plan=k.build_c(text,inventory)
            elif name=='B':
                cplan=k.build_c(text,inventory);scope,_=freeze_read(run,'C',cplan,text,record,inventory);k.scope_wire(text,inventory,scope);plan=k.build_b(text,record,inventory,scope)
            else:plan=plans[name]
            current=pre_admission(run,name,plan,text,record,inventory,scope,key)
            if not plan['fits']:
                if name=='D':continue
                raise c.Denied()
            c.require(current+RESERVE<=CEILING)
            # Complete roundtrips and freeze-chain rechecks immediately before dependent intent.
            integrity_check(text,record)
            if name in ('C','B'):
                again,_=freeze_read(run,'A',plans['A'],text,record);c.require(c.encode(again)==c.encode(inventory));k.wire_decode(text,k.wire_encode(text,again),inventory)
                if name=='B':
                    again_c,_=freeze_read(run,'C',k.build_c(text,again),text,record,again);c.require(c.encode(again_c)==c.encode(scope));k.scope_wire(text,again,again_c);c.require(plan==k.build_b(text,record,again,again_c))
                else:c.require(plan==k.build_c(text,again))
            c.require(ledger(run)['cumulative_budget_charge_nanousd']==current)
            try:value,result=stage(run/f'stage-{name.lower()}',name,plan,text,record,inventory,scope,key,transport,current)
            except c.Denied:
                if name!='D':raise
                stopped=c.read(run/'stage-d/stop.json');c.require(stopped['safe_separate_arm_continuation']);integrity_check(text,record);c.require(ledger(run)['cumulative_budget_charge_nanousd']+RESERVE<=CEILING);continue
            freeze_write(run,name,text,record,inventory,scope,key);value,result=freeze_read(run,name,plan,text,record,inventory,scope)
            if name=='D':direct=result['validation']
            elif name=='A':inventory=value
            elif name=='C':scope=value
        debit=ledger(run);put(run/'ledger.json',debit,keys);c.require(debit['cumulative_budget_charge_nanousd']<=CEILING)
        put(run/'completed.json',{'state':'source_first_completed','direct_status':direct['mapping_status'] if direct else 'failed_or_not_admitted','mapping_status':result['validation']['mapping_status'],'planned_outcomes':debit['planned_outcomes'],'ledger_sha256':c.file_hash(run/'ledger.json'),**k.FLAGS},keys);return result
    except BaseException:
        debit=ledger(run)
        if not (run/'ledger.json').exists():put(run/'ledger.json',debit,keys)
        put(run/'stop.json',{'state':'stopped_no_retry','ledger':debit,'automatic_retry':False,'exception_text_retained':False,**k.FLAGS},keys);raise c.Denied() from None

def live_initial():
    verify_live_bindings();text,record,plans,_=preflight();c.require(not RUN.exists() and 'OP_SERVICE_ACCOUNT_TOKEN' not in os.environ)
    key=os.environ.get('OPENROUTER_API_KEY');c.require(isinstance(key,str) and key.strip() and not key.startswith('op://'));return execute_once(RUN,text,record,plans,key,post_once)
def main():
    try:
        c.require(len(sys.argv)==2 and sys.argv[1] in ('--check','--live-initial'))
        if sys.argv[1]=='--check':
            text,record,plans,prior=preflight();print(c.encode({'state':'passed','fixed_requests':{name:{x:plan[x] for x in ('body_bytes','guarded_bytes','request_sha256','fits')} for name,plan in plans.items()},'dynamic_C_B_guarded_bytes':None,'prior':prior,'aggregate_max_nanousd':PRIOR+4*RESERVE,'operative_pointers':len(k.fields(record)),'candidate_ids':len(k.identities(record)),'provider_calls':0,'credentials_read':False}).decode())
        else:live_initial();print('Automated scope experiment completed; independent semantic review required.')
        return 0
    except BaseException:print('Automated scope adapter stopped; inspect nonsecret receipts. No retry.',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
