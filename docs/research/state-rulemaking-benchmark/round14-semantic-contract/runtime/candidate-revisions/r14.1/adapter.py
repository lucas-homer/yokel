"""Single source-only attempt, exact protocol calls, durable claim and no resume."""
import datetime,importlib.util,os,ssl,sys,urllib.error,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:sys.path.insert(0,str(HERE))
import common as c
import contract as k
PYTHON=Path('/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12')
PRIOR=1705990718;RESERVE=200000000;CEILING=2000000000;HISTORICAL_RESERVE=161920000;BASELINE_ROWS=7063;RUN=c.ROUND/'execution/run'
def cost_nano(value):
    c.require(type(value) in (int,float) and c.math.isfinite(value) and value>=0)
    from decimal import Decimal,ROUND_CEILING
    return int((Decimal(str(value))*1000000000).to_integral_value(rounding=ROUND_CEILING))
def rate_nano(usage):
    c.require(isinstance(usage,dict) and all(type(usage.get(x)) is int and usage[x]>=0 for x in ('prompt_tokens','completion_tokens')))
    return usage['prompt_tokens']*2000+usage['completion_tokens']*10000
def recoverable(raw,reservation=RESERVE):
    debit=reservation
    try:
        usage=c.strict(raw).get('usage',{})
        try:debit=max(debit,rate_nano(usage))
        except BaseException:pass
        try:debit=max(debit,cost_nano(usage.get('cost')))
        except BaseException:pass
    except BaseException:pass
    return debit

def put(path,data,keys=()):
    raw=data if isinstance(data,bytes) else c.encode(data);c.require(not any(key and key.encode() in raw for key in keys))
    with Path(path).open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    fd=os.open(Path(path).parent,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)
def claim(path):
    Path(path).mkdir(parents=True,exist_ok=False);fd=os.open(Path(path).parent,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)
def verify_baseline():
    p=c.ROUND/'prior-baseline.json';c.require(c.file_hash(p)==c.BASELINE_SHA);rows=c.read(p)['files'];targets=c.read(HERE/'baseline-target-witness.json');c.require(len(rows)==BASELINE_ROWS and set(targets)=={x['path'] for x in rows});seen=set()
    for row in rows:
        path=(c.BENCH/row['path']).resolve();c.require(not Path(row['path']).is_absolute() and path.is_relative_to(c.BENCH.resolve()) and row['path'] not in seen and str(path)==targets[row['path']]);seen.add(row['path']);c.verify_pin(path,row)
    path=c.BENCH/'round9-live-exact-id/runtime/adapter.py';spec=importlib.util.spec_from_file_location('r14_historical_calculator',path);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    previous=old.verify_prior()['prior_nanousd'];root=c.BENCH/'round9-live-exact-id/execution/run';intent=c.read(root/'intent.json');status=c.read(root/'status.json');raw=(root/'response.body').read_bytes();result=c.read(root/'result.json')
    c.require(intent['request_sha256']==c.file_hash(root/'request.json') and status['response_sha256']==c.sha(raw) and intent['reserved_nanousd']==HISTORICAL_RESERVE)
    debit=previous+max(HISTORICAL_RESERVE,recoverable(raw,HISTORICAL_RESERVE),result['new_budget_charge_nanousd']);c.require(debit==858310718)
    details=[]
    for round_name,names in [('round10-source-first',('stage-a','stage-b')),('round12-automated-scope',('stage-d','stage-a'))]:
        run=c.BENCH/round_name/'execution/run';ledger=c.read(run/'ledger.json');start=debit;charges=[]
        for name in names:
            folder=run/name;intent=c.read(folder/'intent.json');status=c.read(folder/'status.json');raw=(folder/'response.body').read_bytes()
            c.require(intent['request_sha256']==c.file_hash(folder/'request.json') and status['http_status']==200 and status['response_sha256']==c.sha(raw) and intent['reserved_nanousd']==HISTORICAL_RESERVE and intent['prior_stage_debit_nanousd']==debit)
            receipt=c.read(folder/('result.json' if round_name=='round10-source-first' else 'stop.json'));charge=max(HISTORICAL_RESERVE,recoverable(raw,HISTORICAL_RESERVE),receipt['budget_charge_nanousd'])
            c.require(receipt['cumulative_budget_charge_nanousd']==debit+charge)
            if round_name=='round10-source-first':
                done=c.read(folder/'completed.json');content,meta=native(raw,HISTORICAL_RESERVE);value=c.strict(content)
                c.require(content==(folder/'content.body').read_bytes() and c.encode(value)==(folder/'validated.json').read_bytes() and done['result_sha256']==c.file_hash(folder/'result.json') and done['validated_sha256']==c.file_hash(folder/'validated.json') and done['response_sha256']==receipt['response_sha256']==c.sha(raw) and charge==meta['budget_charge_nanousd'])
                state='validated_frozen';stage=name
            else:
                c.require(receipt['state']=='failed_or_uncertain' and not (folder/'completed.json').exists());state='failed_or_uncertain';stage='D' if name=='stage-d' else 'A'
            debit+=charge;charges.append({'stage':stage,'budget_charge_nanousd':charge,'reserved_nanousd':HISTORICAL_RESERVE,'state':state})
        c.require(ledger['operations']==charges and ledger['prior_nanousd']==start and ledger['new_budget_charge_nanousd']==sum(x['budget_charge_nanousd'] for x in charges) and ledger['cumulative_budget_charge_nanousd']==debit)
        if round_name=='round12-automated-scope':c.require(not (run/'stage-c').exists() and not (run/'stage-b').exists() and ledger['planned_outcomes']=={'D':'failed_or_uncertain','A':'failed_or_uncertain','C':'not_attempted','B':'not_attempted'})
        details.append({'round':round_name,'operations':charges})
    c.require(debit==1505990718)
    # R13 is a completed single-call debit; verify its immutable receipts.
    run=c.BENCH/'round13-compact-inventory/execution/run';intent=c.read(run/'intent.json');status=c.read(run/'status.json');raw=(run/'response.body').read_bytes();result=c.read(run/'result.json');book=c.read(run/'ledger.json');done=c.read(run/'completed.json')
    c.require(not (run/'stop.json').exists() and done['state']=='validated_frozen' and book['state']=='charge_recorded')
    for name,want in done['files'].items():
        path=(run/name).resolve();c.require(path.is_relative_to(run.resolve()));c.verify_pin(path,want)
    c.require(intent['prior_nanousd']==debit and intent['reserved_nanousd']==RESERVE and intent['request_sha256']==c.file_hash(run/'request.json') and status=={'http_status':200,'response_sha256':c.sha(raw)})
    content,meta=native(raw);charge=max(RESERVE,recoverable(raw),result['budget_charge_nanousd']);c.require(content==(run/'content.body').read_bytes() and result['response_sha256']==c.sha(raw) and result['content_sha256']==c.sha(content) and result['budget_charge_nanousd']==meta['budget_charge_nanousd'])
    c.require(book['prior_nanousd']==debit and book['reserved_nanousd']==RESERVE and book['budget_charge_nanousd']==charge and book['cumulative_budget_charge_nanousd']==result['cumulative_budget_charge_nanousd']==debit+charge)
    debit+=charge;details.append({'round':'round13-compact-inventory','budget_charge_nanousd':charge,'state':'validated_frozen'})
    c.require(debit==PRIOR);return {'prior_nanousd':debit,'baseline_rows':len(rows),'historical_rounds':details,'invoice_verified':False}
def read_source():
    ready_path=c.ROUND/'source/READY.json';c.require(c.file_hash(ready_path)==c.SOURCE_READY_SHA);ready=c.read(ready_path)
    c.require(ready['status']=='READY' and ready['extraction']['model_source']=='parsed-body.txt' and ready['checks']['selection_record_precedes_fetch'] is True and ready['checks']['gold_or_candidate_or_provider_outputs_added'] is False)
    for name,want in ready['artifacts'].items():
        path=(c.ROUND/'source'/name).resolve();c.require(path.is_relative_to((c.ROUND/'source').resolve()));c.verify_pin(path,want)
    path=c.SOURCE_PATH;c.require(path.is_absolute() and path.resolve()==path);raw=path.read_bytes();source=raw.decode('utf-8');pins=c.read(HERE/'input-pins.json');c.require(c.sha(raw)==ready['artifacts']['parsed-body.txt']['sha256']==pins['source_sha256'] and source.encode('utf-8')==raw);return source
def offline_integrity(source):
    c.verify_protocol()
    for path,want in c.read(HERE/'code-pins.json')['files'].items():c.verify_pin(path,want)
    c.require(read_source()==source)
def integrity(source):
    c.verify_release();offline_integrity(source)
def prepare_offline():
    c.verify_protocol();prior=verify_baseline()
    for path,want in c.read(HERE/'dependency-pins.json')['files'].items():c.verify_pin(path,want)
    source=read_source();plan=k.build(source);pins=c.read(HERE/'input-pins.json');c.require(plan['request_sha256']==pins['request_sha256'] and plan['body']==c.read(HERE/'source-request.json') and plan['table']==c.read(HERE/'source-span-table.json') and plan['body']['response_format']['json_schema']['schema']==c.read(HERE/'source-schema.json'))
    c.require(c.read(c.PROTO/'request-settings.json')=={'model':'openai/gpt-6.1-sol','stream':False,'max_tokens':8192,'reasoning':{'effort':'low'},'provider':{'allow_fallbacks':False,'max_price':{'completion':10,'prompt':2},'only':['openai'],'order':['openai'],'require_parameters':True}} and PRIOR+RESERVE<=CEILING)
    return source,plan,prior
def preflight():
    c.verify_release();source,plan,prior=prepare_offline();integrity(source);return source,plan,prior

def authorization_fields():
    return {'schema_version':'round14.compact.authorization.v1','scope_sha256':c.file_hash(c.ROUND/'scope.json'),'protocol_ready_sha256':c.READY_SHA,'implementation_release_sha256':c.file_hash(c.ROUND/'implementation-release.json'),'prior_baseline_sha256':c.BASELINE_SHA,'sizing_decision_sha256':c.file_hash(c.ROUND/'sizing-decision.json'),'input_pins_sha256':c.file_hash(HERE/'input-pins.json'),'request_sha256':c.read(HERE/'input-pins.json')['request_sha256'],'source_ready_sha256':c.SOURCE_READY_SHA,'source_sha256':c.read(HERE/'input-pins.json')['source_sha256'],'span_table_sha256':c.read(HERE/'input-pins.json')['span_table_sha256'],'prior_nanousd':PRIOR,'reservation_per_call_nanousd':RESERVE,'reservation_nanousd':RESERVE,'ceiling_nanousd':CEILING,'max_new_operations':1,'inventory_calls':1,'direct_calls':0,'scope_calls':0,'mapping_calls':0,'jev_calls':0,'input_guard':40000,'output_cap':8192,'automatic_retry':False,'repair_clipping_or_fallback':False,'candidate_or_reference_input':False,'outcome_exposed_engineering_case':False,'fresh_prospective_source':True,'production_eligible':False,'action_ready':False}
def verify_live_bindings():
    c.require(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode and Path(sys.executable).resolve()==PYTHON.resolve());deps=c.read(HERE/'dependencies.json');binding=c.read(HERE/'binding.json')
    c.require(binding=={'schema_version':'round14.compact.binding.v1','dependencies_sha256':c.file_hash(HERE/'dependencies.json'),'authorization_sha256':c.file_hash(c.ROUND/'live-authorization.json'),'scope_sha256':c.file_hash(c.ROUND/'scope.json'),'input_pins_sha256':c.file_hash(HERE/'input-pins.json')})
    needed=set(c.read(HERE/'dependency-pins.json')['files'])|set(c.read(HERE/'input-pins.json')['files'])|set(c.read(HERE/'code-pins.json')['files'])|{str(PYTHON),str(c.ROUND/'live-authorization.json'),str(HERE/'READY.json'),str(HERE/'code-pins.json'),str(HERE/'input-pins.json')};c.require(deps['schema_version']=='round14.compact.dependencies.v1' and needed<=set(deps['files']) and 0<len(deps['files'])<=10000)
    for p,h in deps['files'].items():
        path=Path(p);c.require(path.is_absolute() and path.resolve()==path and path.is_file());c.verify_pin(path,h)
    c.require(c.read(c.ROUND/'live-authorization.json')==authorization_fields())
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise c.Denied()
def post_once(body,key):
    req=urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',data=c.encode(body),method='POST',headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
    opener=urllib.request.build_opener(NoRedirect(),urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    try:
        with opener.open(req,timeout=180) as r:return r.status,r.read(2000001)
    except urllib.error.HTTPError as e:return e.code,e.read(2000001)
def native(raw,reservation=RESERVE):
    value=c.strict(raw);c.require(isinstance(value,dict) and not value.get('error'));c.require(value.get('model') in ('openai/gpt-6.1-sol','openai/gpt-6.1-sol-20260929') and value.get('provider') in (None,'OpenAI'))
    choices=value.get('choices');c.require(isinstance(choices,list) and len(choices)==1 and isinstance(choices[0],dict));choice=choices[0];c.require(choice.get('finish_reason')=='stop' and not choice.get('error'));message=choice.get('message');c.require(isinstance(message,dict) and not message.get('refusal') and not message.get('tool_calls') and isinstance(message.get('content'),str))
    usage=value.get('usage');reported=cost_nano(usage.get('cost')) if isinstance(usage,dict) else None;c.require(reported is not None);rate=rate_nano(usage)
    return message['content'].encode(),{'model':value['model'],'provider':value.get('provider'),'provider_identity_verified':value.get('provider')=='OpenAI','finish_reason':choice['finish_reason'],'usage':usage,'reported_cost_usd':usage['cost'],'reported_cost_nanousd':reported,'usage_rate_estimated_nanousd':rate,'rate_estimate_includes_cache_write_premium':False,'budget_charge_nanousd':max(reservation,reported,rate),'invoice_verified':False}
def ledger(run):
    charge=RESERVE;raw=(run/'response.body').read_bytes() if (run/'response.body').exists() else None
    if raw is not None:charge=max(charge,recoverable(raw))
    for n in ('result.json','stop.json'):
        if (run/n).exists():
            try:charge=max(charge,c.read(run/n)['budget_charge_nanousd'])
            except BaseException:pass
    return {'prior_nanousd':PRIOR,'reserved_nanousd':RESERVE,'budget_charge_nanousd':charge,'cumulative_budget_charge_nanousd':PRIOR+charge,'ceiling_nanousd':CEILING,'attempts_claimed':1,'state':'charge_recorded','outcome_attestation':'separate completed.json or stop.json receipt','provider_calls_may_have_occurred':(run/'intent.json').exists(),'invoice_verified':False}
def execute_once(run,source,plan,key,transport,integrity_check=integrity):
    run=Path(run);claim(run);raw=None;dispatched=False;keys=(key,)
    try:
        c.require(isinstance(key,str) and key.strip() and not key.startswith('op://') and plan==k.build(source) and plan['guarded_bytes']<=40000 and PRIOR+RESERVE<=CEILING);integrity_check(source)
        put(run/'request.json',c.encode(plan['body']),keys);put(run/'span-table.json',c.encode(plan['table']),keys);integrity_check(source);c.require(c.file_hash(run/'request.json')==plan['request_sha256'] and c.read(run/'span-table.json')==plan['table'])
        put(run/'intent.json',{'schema_version':'round14.inventory-intent.v1','request_sha256':plan['request_sha256'],'source_ready_sha256':c.SOURCE_READY_SHA,'source_sha256':k.protocol().source_hash(source),'span_table_sha256':c.digest(plan['table']),'protocol_ready_sha256':c.READY_SHA,'input_pins_sha256':c.file_hash(HERE/'input-pins.json'),'prior_nanousd':PRIOR,'reserved_nanousd':RESERVE,'ceiling_nanousd':CEILING,'guarded_bytes':plan['guarded_bytes'],'output_cap':8192,'automatic_retry':False,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},keys)
        dispatched=True;status,raw=transport(plan['body'],key);c.require(type(status) is int and isinstance(raw,bytes) and len(raw)<=2000000 and key.encode() not in raw)
        put(run/'response.body',raw,keys);put(run/'status.json',{'http_status':status,'response_sha256':c.sha(raw)},keys)
        # Preserve exact provider content separately even when finish/structure fails;
        # this is not prefix salvage and never enters validation as a repaired output.
        envelope=c.strict(raw)
        choices=envelope.get('choices') if isinstance(envelope,dict) else None
        if isinstance(choices,list) and len(choices)==1 and isinstance(choices[0],dict) and isinstance(choices[0].get('message'),dict) and isinstance(choices[0]['message'].get('content'),str):put(run/'content.body',choices[0]['message']['content'].encode(),keys)
        c.require(status==200);content,meta=native(raw);c.require(content==(run/'content.body').read_bytes());checked=k.validate_response(content.decode('utf-8'),meta['finish_reason'],source,plan['table'])
        put(run/'validated.json',c.encode(checked['compact']),keys);put(run/'expanded.json',c.encode(checked['expanded']),keys)
        # Re-read receipts and exercise the exact inverse before marking completion.
        c.require(c.file_hash(run/'request.json')==plan['request_sha256'] and c.read(run/'span-table.json')==plan['table'] and c.file_hash(run/'response.body')==c.sha(raw) and c.read(run/'status.json')=={'http_status':200,'response_sha256':c.sha(raw)})
        again=k.validate_response((run/'content.body').read_bytes().decode('utf-8'),meta['finish_reason'],source,c.read(run/'span-table.json'));c.require(again==checked and c.encode(again['compact'])==(run/'validated.json').read_bytes() and c.encode(again['expanded'])==(run/'expanded.json').read_bytes());integrity_check(source)
        result={'schema_version':'round14.inventory-result.v1','request_sha256':plan['request_sha256'],'source_ready_sha256':c.SOURCE_READY_SHA,'source_sha256':k.protocol().source_hash(source),'span_table_sha256':c.digest(plan['table']),'response_sha256':c.sha(raw),'content_sha256':c.sha(content),'compact_sha256':c.digest(checked['compact']),'expanded_sha256':c.digest(checked['expanded']),'unit_count':len(checked['compact']['u']),'roundtrip_exact':True,'whole_line_evidence_is_entailment':False,**meta,'cumulative_budget_charge_nanousd':PRIOR+meta['budget_charge_nanousd'],**k.FLAGS}
        put(run/'result.json',result,keys);put(run/'ledger.json',ledger(run),keys);c.require(result['cumulative_budget_charge_nanousd']<=CEILING)
        put(run/'completed.json',{'state':'validated_frozen','files':{n:c.file_hash(run/n) for n in ('request.json','span-table.json','intent.json','response.body','status.json','content.body','validated.json','expanded.json','result.json','ledger.json')},**k.FLAGS},keys);return result
    except BaseException:
        charge=recoverable(raw) if isinstance(raw,bytes) else RESERVE
        put(run/'stop.json',{'state':'failed_or_uncertain','budget_charge_nanousd':charge,'cumulative_budget_charge_nanousd':PRIOR+charge,'provider_calls_may_have_occurred':dispatched,'response_retained':(run/'response.body').exists(),'automatic_retry':False,'exception_text_retained':False,'invoice_verified':False,**k.FLAGS},keys)
        if not (run/'ledger.json').exists():put(run/'ledger.json',ledger(run),keys)
        raise c.Denied() from None
def live_initial():
    verify_live_bindings();source,plan,_=preflight();c.require(not RUN.exists() and 'OP_SERVICE_ACCOUNT_TOKEN' not in os.environ);key=os.environ.get('OPENROUTER_API_KEY');c.require(isinstance(key,str) and key.strip() and not key.startswith('op://'));return execute_once(RUN,source,plan,key,post_once)
def main():
    try:
        c.require(len(sys.argv)==2 and sys.argv[1] in ('--candidate-check','--check','--live-initial'))
        if sys.argv[1] in ('--candidate-check','--check'):
            source,plan,prior=prepare_offline() if sys.argv[1]=='--candidate-check' else preflight();offline_integrity(source);print(c.encode({'state':'candidate_checked' if sys.argv[1]=='--candidate-check' else 'passed','release_preflight_passed':sys.argv[1]=='--check','body_bytes':plan['body_bytes'],'guarded_bytes':plan['guarded_bytes'],'request_sha256':plan['request_sha256'],'source_ready_sha256':c.SOURCE_READY_SHA,'source_sha256':k.protocol().source_hash(source),'span_count':len(plan['table']['rows']),'prior':prior,'aggregate_max_nanousd':PRIOR+RESERVE,'provider_calls':0,'credentials_read':False}).decode())
        else:live_initial();print('Compact inventory attempt completed; independent semantic review required.')
        return 0
    except BaseException:print('Compact inventory adapter stopped; inspect nonsecret receipts. No retry.',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
