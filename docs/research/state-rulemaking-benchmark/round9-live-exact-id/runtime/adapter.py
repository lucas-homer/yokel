#!/usr/bin/env python3
"""Fixed one-shot exact-ID adapter. Only primary-signed --live-initial can dispatch."""
import datetime, hashlib, importlib.util, json, math, os, ssl, sys, urllib.error, urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROUND=HERE.parent
BENCH=ROUND.parent
FROZEN=BENCH/'round9-exact-id-completeness/runtime'
PYTHON=Path('/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12')
SITE=PYTHON.parent.parent/'lib/python3.12/site-packages'
BASELINE_SHA='9df0a6b5f9bda5d031ef87426f4a03e929f268f2e3f3dceb8d7fea20ef1223ac'
PRIOR_NANO=696390718
RESERVE_NANO=161920000
CEILING_NANO=2000000000
RUN=ROUND/'execution/run'
class Denied(Exception): pass
def require(ok):
    if not ok: raise Denied()
def encode(value): return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(raw): return hashlib.sha256(raw).hexdigest()
def digest(path): return sha(Path(path).read_bytes())
def strict(raw):
    def pairs(rows):
        out={}
        for k,v in rows:
            require(k not in out); out[k]=v
        return out
    def number(v):
        n=float(v); require(math.isfinite(n)); return n
    return json.loads(raw,object_pairs_hook=pairs,parse_float=number,parse_constant=lambda _:(_ for _ in ()).throw(Denied()))
def read(path): return strict(Path(path).read_bytes())
def cost_nano(value):
    require(type(value) in (int,float) and math.isfinite(value) and value>=0)
    # Conservative upward integer conversion, avoiding float ledger accumulation.
    from decimal import Decimal, ROUND_CEILING
    return int((Decimal(str(value))*1000000000).to_integral_value(rounding=ROUND_CEILING))
def rate_nano(usage):
    require(isinstance(usage,dict) and all(type(usage.get(k)) is int and usage[k]>=0 for k in ('prompt_tokens','completion_tokens')))
    return usage['prompt_tokens']*2000+usage['completion_tokens']*10000
def recoverable_charge(raw):
    charge=RESERVE_NANO
    try:
        usage=strict(raw).get('usage',{})
        try: charge=max(charge,rate_nano(usage))
        except BaseException: pass
        try: charge=max(charge,cost_nano(usage.get('cost')))
        except BaseException: pass
    except BaseException: pass
    return charge
def put(path,data,keys=()):
    raw=data if isinstance(data,bytes) else encode(data)
    require(not any(k and k.encode() in raw for k in keys))
    with Path(path).open('xb') as f: f.write(raw); f.flush(); os.fsync(f.fileno())
    fd=os.open(Path(path).parent,os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def verify_prior():
    baseline=ROUND/'prior-baseline.json'; require(digest(baseline)==BASELINE_SHA)
    rows=read(baseline)['files']; require(len(rows)==5055); seen=set()
    for row in rows:
        path=(BENCH/row['path']).resolve()
        require(not Path(row['path']).is_absolute() and path.is_relative_to(BENCH.resolve()) and str(path) not in seen)
        seen.add(str(path)); require(digest(path)==row['sha256'] and path.stat().st_size==row['bytes'])
    prior=read(BENCH/'round8-stronger-cap-probe/runtime/prior-debit.json')
    operations=[]
    for row in prior['operations']:
        root=Path(row['round_root'])/'execution/run/operations'
        paths=[Path(p).parent for p in row['files'] if p.endswith('/intent.json')]; require(len(paths)==1)
        require(paths[0].parent==root); operations.append(paths[0])
    latest=list((BENCH/'round8-stronger-cap-probe/execution/run/operations').iterdir())
    require(len(latest)==1 and latest[0].is_dir()); operations+=latest
    debit=0; details=[]
    for folder in operations:
        intent=read(folder/'intent.json'); native=read(folder/'response.body'); status=read(folder/'status.json')
        require(intent['request_sha256']==digest(folder/'request.json') and status['response_sha256']==digest(folder/'response.body'))
        reserve=round(intent['reserved_nominal_usd']*1000000000); reported=round(native['usage'].get('cost',0)*1000000000)
        result=read(folder/'result.json') if (folder/'result.json').exists() else None
        accounted=round(result['observed_cost_usd']*1000000000) if result else 0
        charge=max(reserve,reported,accounted); debit+=charge
        details.append(dict(operation_id=intent['operation_id'],conservative_nanousd=charge,reported_nanousd=reported))
    # Frozen prior ledger amounts are rounded to exact nanodollar precision.
    require(debit==PRIOR_NANO)
    require(read(BENCH/'round8-stronger-cap-probe/execution/run/completed.json')['totals']['budget_charge_usd']==.696390718)
    return dict(prior_nanousd=PRIOR_NANO,operations=details,invoice_verified=False)

def preflight():
    prior=verify_prior()
    pins=read(HERE/'input-pins.json')
    for path,want in pins['files'].items(): require(digest(path)==want)
    # Isolated startup skips .pth/sitecustomize; add only reviewed package/runtime roots.
    if str(SITE) not in sys.path: sys.path.insert(0,str(SITE))
    if str(FROZEN) not in sys.path: sys.path.insert(0,str(FROZEN))
    import request, response
    require(Path(request.__file__).resolve()==FROZEN/'request.py' and Path(response.__file__).resolve()==FROZEN/'response.py')
    planned=request.wi(); body=planned['body']; raw=encode(body)
    require(sha(raw)==pins['request_sha256'] and len(raw)==38432 and planned['estimate']==39456 and planned['guard']==40000)
    require(body['max_tokens']==8192 and RESERVE_NANO+PRIOR_NANO<=CEILING_NANO)
    return planned, request, response, prior

def authorization_fields():
    pins=read(HERE/'input-pins.json')
    return dict(schema_version='round9-live-exact-id.authorization.v1',scope_sha256=digest(ROUND/'scope.json'),input_pins_sha256=digest(HERE/'input-pins.json'),prior_baseline_sha256=BASELINE_SHA,request_sha256=pins['request_sha256'],prior_nanousd=PRIOR_NANO,reservation_nanousd=RESERVE_NANO,ceiling_nanousd=CEILING_NANO,max_new_operations=1,stronger_calls=1,inventory_calls=0,jev_calls=0,output_cap=8192,input_guard=40000,automatic_retry=False,production_eligible=False,action_ready=False)

def verify_live_bindings():
    require(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode and Path(sys.executable).resolve()==PYTHON.resolve())
    binding=read(HERE/'binding.json'); deps=read(HERE/'dependencies.json')
    require(binding==dict(schema_version='round9-live-exact-id.binding.v1',dependencies_sha256=digest(HERE/'dependencies.json'),authorization_sha256=digest(ROUND/'live-authorization.json'),scope_sha256=digest(ROUND/'scope.json'),input_pins_sha256=digest(HERE/'input-pins.json')))
    require(deps['schema_version']=='round9-live-exact-id.dependencies.v1' and isinstance(deps['files'],dict) and deps['files'])
    needed={str(PYTHON.resolve()),str(HERE/'adapter.py'),str(HERE/'input-pins.json'),str(ROUND/'scope.json'),str(ROUND/'live-authorization.json'),str(ROUND/'prior-baseline.json')}
    require(needed.issubset(deps['files']))
    for path,want in deps['files'].items():
        p=Path(path); require(p.is_absolute() and p.resolve()==p and p.is_file() and digest(p)==want)
    require(read(ROUND/'live-authorization.json')==authorization_fields())

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): raise Denied()
def post_once(body,key):
    req=urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',data=encode(body),method='POST',headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
    opener=urllib.request.build_opener(NoRedirect(),urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    try:
        with opener.open(req,timeout=180) as r: return r.status,r.read(2000001)
    except urllib.error.HTTPError as e: return e.code,e.read(2000001)

def parse_native(raw,request,response):
    native=strict(raw); require(isinstance(native,dict) and not native.get('error'))
    require(native.get('model') in ('openai/gpt-6.1-sol','openai/gpt-6.1-sol-20260929') and native.get('provider') in (None,'OpenAI'))
    choices=native.get('choices'); require(isinstance(choices,list) and len(choices)==1)
    choice=choices[0]; require(choice.get('finish_reason')=='stop' and not choice.get('error'))
    msg=choice.get('message',{}); require(not msg.get('refusal') and not msg.get('tool_calls') and isinstance(msg.get('content'),str))
    usage=native.get('usage'); require(isinstance(usage,dict) and all(type(usage.get(k)) is int and usage[k]>=0 for k in ('prompt_tokens','completion_tokens')))
    charge=max(RESERVE_NANO,cost_nano(usage.get('cost')),rate_nano(usage))
    checked=response.validate_response(msg['content'],request.ASSEMBLED['source'],request.ASSEMBLED)
    # Model completeness is reported as its own assertion. No automatic manual-audit inference.
    value=strict(msg['content']); label=value.get('completeness',{}).get('label') if isinstance(value,dict) and isinstance(value.get('completeness',{}),dict) else None
    return dict(schema_version='round9-live-exact-id.result.v1',structural_validation=checked,model_completeness_label=label,independent_audit_agreement='unverified',semantic_status='unverified',usage=usage,reported_cost_usd=usage['cost'],usage_rate_estimated_usd=usage['prompt_tokens']*.000002+usage['completion_tokens']*.000010,new_budget_charge_nanousd=charge,budget_charge_nanousd=PRIOR_NANO+charge,provider_identity_verified=native.get('provider')=='OpenAI',production_eligible=False,action_ready=False)

def execute_once(run,planned,request,response,key,transport):
    run=Path(run)
    # mkdir(exist_ok=False) is the cross-process claim. No resume path can dispatch again.
    run.mkdir(parents=True,exist_ok=False)
    keys=(key,)
    require(isinstance(key,str) and key.strip() and not key.startswith('op://'))
    put(run/'request.json',encode(planned['body']),keys)
    intent=dict(schema_version='round9-live-exact-id.intent.v1',operation_id='doc-92211b8c7ba0-stronger-exact-id',kind='stronger',request_sha256=sha(encode(planned['body'])),prior_nanousd=PRIOR_NANO,reserved_nanousd=RESERVE_NANO,ceiling_nanousd=CEILING_NANO,input_guard=40000,output_cap=8192,automatic_retry=False,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    put(run/'intent.json',intent,keys)
    try:
        status,raw=transport(planned['body'],key)
        require(type(status) is int and isinstance(raw,bytes) and len(raw)<=2000000)
        put(run/'response.body',raw,keys)
        put(run/'status.json',dict(http_status=status,response_sha256=sha(raw)),keys)
        require(status==200)
        result=parse_native(raw,request,response); put(run/'result.json',result,keys)
        require(result['budget_charge_nanousd']<=CEILING_NANO)
        put(run/'completed.json',dict(state='completed',structural_valid=result['structural_validation']['structural_valid'],model_completeness_label=result['model_completeness_label'],independent_audit_agreement='unverified',semantic_status='unverified',production_eligible=False,action_ready=False),keys)
        return result
    except BaseException:
        # No exception strings, headers or traceback may contain provider/credential data.
        charge=recoverable_charge((run/'response.body').read_bytes()) if (run/'response.body').exists() else RESERVE_NANO
        put(run/'stop.json',dict(new_budget_charge_nanousd=charge,budget_charge_nanousd=PRIOR_NANO+charge,invoice_verified=False,state='failed_or_uncertain',provider_calls_may_have_occurred=True,response_retained=(run/'response.body').exists(),automatic_retry=False,exception_text_retained=False),keys)
        raise Denied() from None

def live_initial():
    verify_live_bindings(); planned,request,response,prior=preflight()
    require(not RUN.exists() and 'OP_SERVICE_ACCOUNT_TOKEN' not in os.environ)
    key=os.environ.get('OPENROUTER_API_KEY'); require(isinstance(key,str) and key.strip() and not key.startswith('op://'))
    return execute_once(RUN,planned,request,response,key,post_once)
def main():
    try:
        require(len(sys.argv)==2 and sys.argv[1] in ('--check','--live-initial'))
        if sys.argv[1]=='--check':
            planned,_,_,prior=preflight(); print(json.dumps(dict(state='passed',provider_calls=0,credentials_read=False,body_bytes=planned['body_bytes'],estimate=planned['estimate'],guard=40000,prior=prior,reservation_nanousd=RESERVE_NANO,aggregate_max_nanousd=PRIOR_NANO+RESERVE_NANO),sort_keys=True))
        else: live_initial(); print('Exact-ID job completed; independent semantic audit required.')
        return 0
    except BaseException:
        print('Exact-ID adapter stopped; inspect nonsecret receipts. No automatic retry.',file=sys.stderr); return 1
if __name__=='__main__': sys.exit(main())
