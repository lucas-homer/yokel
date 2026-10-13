"""One-source cap-probe staged append-only per-operation ledger. No provider retry logic."""
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import time
import types

def encode(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def loads(raw):
    def unique(pairs):
        out={}
        for k,v in pairs:
            if k in out:raise Stop('duplicate JSON key')
            out[k]=v
        return out
    return json.loads(raw,object_pairs_hook=unique,parse_constant=lambda x:(_ for _ in ()).throw(Stop('nonfinite JSON')))
j=types.SimpleNamespace(encode=encode,loads=loads)

class Pause(RuntimeError):
    pass

class Stop(RuntimeError):
    pass


def sha(b):
    return hashlib.sha256(b).hexdigest()


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def put(path, data):
    """Immutable artifact, fsync file then directory. Byte-identical resume only."""
    data = data if isinstance(data,bytes) else j.encode(data)
    path=Path(path)
    if path.exists():
        if path.read_bytes()!=data:
            raise Stop('immutable artifact differs')
        return
    tmp=path.with_name(path.name+'.tmp')
    # Interrupted artifact writes are local and can safely restart before any POST intent.
    if tmp.exists():
        tmp.unlink()
    with open(tmp,'xb') as f:
        f.write(data);f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)
    fd=os.open(path.parent,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)


def sanitize_input(data,keys):
    raw=data if isinstance(data,bytes) else j.encode(data)
    if any(k and k.encode() in raw for k in keys):
        raise Stop('credential present in artifact; retention blocked')
    return raw


class Ledger:
    def __init__(self,root,pins,*,max_new=3,budget=2.0,transport=None,keys=None,clock=time.time,sleeper=time.sleep):
        if type(budget) not in (int,float) or budget!=2.0 or type(max_new) is not int or not 0<=max_new<=3:
            raise Stop('invalid runtime caps')
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
        self.keys=keys or {};self.transport=transport;self.max_new=max_new;self.new=0
        self.clock=clock;self.sleeper=sleeper;self.budget=budget;self.prior_debit=.100166
        put(self.root/'pins.json',sanitize_input(pins,self.keys.values()))
        self.pin_hash=sha((self.root/'pins.json').read_bytes())
        (self.root/'operations').mkdir(exist_ok=True)
        self.precheck()

    def intents(self):
        return [j.loads(p.read_bytes()) for p in (self.root/'operations').glob('*/intent.json')]

    def precheck(self):
        for folder in (self.root/'operations').iterdir():
            if not folder.is_dir():continue
            if (folder/'intent.json').exists():
                intent=j.loads((folder/'intent.json').read_bytes())
                if intent.get('kind') not in ('inventory','jev','stronger') or intent.get('pages')!=0:raise Stop('unsupported stage/OCR operation in ledger')
                if not (folder/'identity.json').exists() or not (folder/'request.json').exists():raise Stop('intent lacks bound identity/request')
                meta=j.loads((folder/'identity.json').read_bytes())
                required={'operation_id','kind','identity','pins_sha256','request_sha256','reserved_nominal_usd','pages'}
                if set(meta)!=required or set(intent)!=required|{'created_utc','automatic_retry'}:raise Stop('retained operation binding shape drift')
                if any(intent[k]!=meta[k] for k in required) or intent['automatic_retry'] is not False:raise Stop('retained intent identity/reservation drift')
                if meta['pins_sha256']!=self.pin_hash or meta['request_sha256']!=sha((folder/'request.json').read_bytes()):raise Stop('retained request/pins drift')
                if folder.name!=meta['kind']+'-'+sha(j.encode(meta))[:24]:raise Stop('retained operation binding digest drift')
                value=meta['reserved_nominal_usd']
                if type(value) not in (int,float) or not math.isfinite(value) or value<0:raise Stop('invalid bound reservation')
            if (folder/'stop.json').exists():raise Stop('prior failed operation latched; reconcile outside runner')
            if (folder/'intent.json').exists() and not (folder/'response.body').exists():
                raise Stop('uncertain prior POST; no automatic retries')
            if (folder/'result.json').exists() and not (folder/'intent.json').exists():
                raise Stop('operation result missing durable intent')
            if (folder/'response.body').exists() and not (folder/'status.json').exists():
                raise Stop('response lacks durable HTTP status; no automatic retry')

    def totals(self):
        ints=self.intents();nominal=sum(x['reserved_nominal_usd'] for x in ints)
        observed=[];charged=0.0
        for folder in (self.root/'operations').iterdir():
            if not (folder/'intent.json').exists():continue
            intent=j.loads((folder/'intent.json').read_bytes());cost=None
            if (folder/'result.json').exists():
                cost=j.loads((folder/'result.json').read_bytes()).get('observed_cost_usd')
                if cost is not None:
                    if type(cost) not in (int,float) or not math.isfinite(cost) or cost<0:raise Stop('invalid retained cost')
                    observed.append(cost)
            charged+=max(intent['reserved_nominal_usd'],cost if cost is not None else 0)
        return {'operations':len(ints),'jev_cases':sum(x['kind']=='jev' for x in ints),
                'inventory_cases':sum(x['kind']=='inventory' for x in ints),'stronger_cases':sum(x['kind']=='stronger' for x in ints),
                'ocr_pages':0,
                'nominal_reserved_usd':nominal,'observed_accounted_usd':sum(observed),
                'new_budget_charge_usd':charged,'prior_budget_debit_usd':self.prior_debit,'budget_charge_usd':self.prior_debit+charged}

    def operation(self,operation_id,kind,payload,parse,*,identity,reserve,pages=0):
        if kind not in ('inventory','jev','stronger') or type(reserve) not in (int,float) or not math.isfinite(reserve) or reserve<0 or type(pages) is not int or pages!=0:
            raise Stop('invalid operation reservation')
        self.precheck()
        provider='jev' if kind=='jev' else 'openrouter'
        body=sanitize_input(payload,self.keys.values())
        meta={'operation_id':operation_id,'kind':kind,'identity':identity,'pins_sha256':self.pin_hash,'request_sha256':sha(body),'reserved_nominal_usd':reserve,'pages':pages}
        folder=self.root/'operations'/(kind+'-'+sha(j.encode(meta))[:24])
        for prior in (self.root/'operations').glob('*/identity.json'):
            retained=j.loads(prior.read_bytes())
            if retained['operation_id']==operation_id and retained!=meta:raise Stop('operation ID reused with changed identity/request')
        folder.mkdir(exist_ok=True)
        put(folder/'identity.json',sanitize_input(meta,self.keys.values()));put(folder/'request.json',body)
        if (folder/'result.json').exists():
            result=j.loads((folder/'result.json').read_bytes())
            status=j.loads((folder/'status.json').read_bytes())
            if sha((folder/'response.body').read_bytes())!=status['response_sha256']:
                raise Stop('retained response drift')
            # Reparse native provider bytes so changed or corrupted result records cannot silently resume.
            rebuilt=parse((folder/'response.body').read_bytes())
            if rebuilt!=result:raise Stop('retained parsed result drift')
            return result
        if (folder/'intent.json').exists():
            # Received-but-unparsed response is replayable locally; never resubmit.
            if not (folder/'response.body').exists():raise Stop('uncertain operation; no retry')
            status=j.loads((folder/'status.json').read_bytes())
            raw=(folder/'response.body').read_bytes()
            if status['http_status']!=200 or sha(raw)!=status['response_sha256']:
                raise Stop('failed or corrupted retained response')
        else:
            totals=self.totals()
            if self.new>=self.max_new:raise Pause('max-new provider operations reached')
            if kind=='jev' and totals['jev_cases']>=1:raise Pause('1 batched Jev-call cap reached')
            if kind=='inventory' and totals['inventory_cases']>=1:raise Pause('1 source-inventory cap reached')
            if kind=='stronger' and totals['stronger_cases']>=1:raise Pause('1 stronger-verifier cap reached')
            if totals['budget_charge_usd']+reserve>self.budget:
                raise Pause('nominal/reported budget cap reached')
            key=self.keys.get(provider)
            if not isinstance(key,str) or not key.strip():raise Stop('missing provider credential')
            intent={**meta,'pages':pages,'reserved_nominal_usd':reserve,'created_utc':now(),'automatic_retry':False}
            if self.transport is None:raise Stop('missing explicit provider transport')
            put(folder/'intent.json',intent)
            print(json.dumps({'operation':operation_id,'kind':kind,'state':'single_POST_started'}),flush=True)
            start=self.clock()
            try:status_code,raw=self.transport(provider,payload,key)
            except Exception:
                put(folder/'stop.json',{'state':'uncertain_POST','retry_allowed':False})
                raise Stop('uncertain POST; stop without retry') from None
            self.new+=1
            if not isinstance(raw,bytes) or len(raw)>2_000_000:
                put(folder/'stop.json',{'state':'oversize_or_invalid_response','retry_allowed':False})
                raise Stop('unsafe response')
            try:raw=sanitize_input(raw,self.keys.values())
            except Stop:
                put(folder/'stop.json',{'state':'credential_echo_response','retry_allowed':False});raise
            put(folder/'response.body',raw)
            put(folder/'status.json',{'http_status':status_code,'elapsed_seconds':self.clock()-start,'response_sha256':sha(raw)})
            if status_code!=200:
                put(folder/'stop.json',{'state':'provider_HTTP_error','retry_allowed':False})
                raise Stop('provider HTTP error; exact response retained')
        try:result=parse(raw)
        except Exception:
            put(folder/'stop.json',{'state':'invalid_response_or_usage','retry_allowed':False})
            raise Stop('invalid provider response/usage; exact bytes retained') from None
        put(folder/'result.json',sanitize_input(result,self.keys.values()))
        print(json.dumps({'operation':operation_id,'state':'completed','totals':self.totals()}),flush=True)
        if self.totals()['budget_charge_usd']>self.budget:
            put(folder/'stop.json',{'state':'observed_budget_exceeded','retry_allowed':False})
            # The provider work completed successfully. Return its paid result; runner stops the next stage.
            self.reported_budget_exceeded=True
        return result
