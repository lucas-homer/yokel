"""Offline evidence audit; never dispatches runtime or provider operations."""
import sys, json, hashlib, importlib.util, collections
from pathlib import Path
from decimal import Decimal as D
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]; BENCH=ROOT.parent

def guard(event,args):
    if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.posix_spawn'):raise RuntimeError('No external operation permitted')
    if event=='open' and isinstance(args[0],(str,bytes)):
        name=str(args[0]); low=name.lower()
        if any(x in low for x in ('/library/keychains/','/.aws/','/.env','.pem')):raise RuntimeError('Credential path forbidden')
        mode=args[1];flags=args[2]
        if ((isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags & 3)) and not Path(name).resolve().is_relative_to(HERE):raise RuntimeError('Write outside audit forbidden')
sys.addaudithook(guard)
def pairs(rows):
    out={}
    for k,v in rows:
        if k in out:raise ValueError('Duplicate JSON key')
        out[k]=v
    return out

def loads(raw):return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))
def read(p):return loads(Path(p).read_bytes())
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def hval(v):return hashlib.sha256(canonical(v)).hexdigest()
checks=[]
def check(name,ok,detail=None):
    checks.append(dict(check=name,passed=bool(ok),detail=detail))
    if not ok:raise AssertionError(name+': '+str(detail))
def mapping(name,files):
    bad=[p for p,h in files.items() if not Path(p).is_file() or digest(p)!=h]
    check(name,not bad,dict(files=len(files),mismatches=bad))
def freeze(name,p,base,expected=None):
    if expected:check(name+' manifest digest',digest(p)==expected)
    rows=read(p)['files'];seen=set();bad=[]
    for row in rows:
        q=(base/row['path']).resolve()
        if not q.is_relative_to(base.resolve()) or row['path'] in seen or not q.is_file() or digest(q)!=row['sha256'] or q.stat().st_size!=row['bytes']:bad.append(row['path'])
        seen.add(row['path'])
    check(name+' file hashes and sizes',not bad,dict(files=len(rows),mismatches=bad));return rows

E=freeze('Freeze E',ROOT/'execution/freeze-E.json',ROOT,'33837085a3fde23e7323372de77c31cc694a532865c49799d4457668826aa1c6')
binding=read(ROOT/'execution/service-account/binding.json')
for letter in ('A','S'):freeze('Freeze '+letter,ROOT/f'execution/freeze-{letter}.json',ROOT,binding[f'freeze_{letter}_sha256'])
freeze('Freeze B',BENCH/'round8/execution/freeze-B.json',BENCH/'round8',binding['freeze_B_sha256'])
for relative in ('execution/prior-baseline.json','review/prior-baseline.json'):
    mapping(relative,read(ROOT/relative)['files'])
impl=read(ROOT/'runtime/implementation.json');mapping('implementation code pins',impl['code'])
deps=read(ROOT/'execution/service-account/dependencies.json');mapping('signed job dependency pins',deps['files'])
for field,rel in [('implementation','runtime/implementation.json'),('manifest','sources/source-inputs.READY.json'),('authorization','execution/live-authorization.json'),('dependencies','execution/service-account/dependencies.json')]:check(field+' binding',digest(ROOT/rel)==binding[field+'_sha256'])
pin=read(ROOT/'runtime/input-pin.json')
mapping('retained input pins',{v['path']:v['sha256'] for v in pin['files'].values()})
prior=read(ROOT/'runtime/prior-debit.json');prior_rows=[];seen_freeze=set()
for row in prior['operations']:
    mapping('prior '+Path(row['round_root']).name+' '+row['kind'],row['files'])
    old=Path(row['round_root']);f=old/'execution/freeze-E.json'
    if f not in seen_freeze:freeze('Prior '+old.name+' E',f,old,row['files'][str(f)]);seen_freeze.add(f)
    response=next(Path(x) for x in row['files'] if x.endswith('/response.body'));op=response.parent
    raw=read(response);intent=read(op/'intent.json');reported=raw['usage'].get('cost');reserve=D(str(intent['reserved_nominal_usd']));result=read(op/'result.json') if (op/'result.json').exists() else None
    accounted=result.get('observed_cost_usd') if result else None
    charge=max(reserve,D(str(reported or 0)),D(str(accounted or 0)))
    check('prior costs '+old.name+' '+row['kind'],abs(charge-D(str(row['conservative_debit_usd'])))<D('1e-15') and reported==row['recoverable_native_reported_usd'] and accounted==row['parsed_result_accounted_usd'])
    prior_rows.append(dict(round=old.name,kind=row['kind'],reserved=str(reserve),reported=reported,accounted=accounted,charge=str(charge)))
run=ROOT/'execution/run';ops=list((run/'operations').iterdir());check('one operation directory',len(ops)==1)
op=ops[0];identity=read(op/'identity.json');intent=read(op/'intent.json');status=read(op/'status.json');result=read(op/'result.json');native=read(op/'response.body');request=read(op/'request.json');complete=read(run/'completed.json');pins=read(run/'pins.json')
check('one stronger attempt no automatic retry',identity['kind']=='stronger' and intent['automatic_retry'] is False and all(intent[k]==v for k,v in identity.items()) and not list(run.rglob('*stop*.json')))
check('operation hashes',identity['pins_sha256']==digest(run/'pins.json') and identity['request_sha256']==digest(op/'request.json') and status['response_sha256']==digest(op/'response.body') and op.name=='stronger-'+hval(identity)[:24])
check('runtime pins match authorization',pins['implementation']==impl and pins['authorization_sha256']==binding['authorization_sha256'] and pins['manifest_sha256']==binding['manifest_sha256'] and pins['source_labels_freeze_sha256']==binding['freeze_B_sha256'])
oldrequest=read(pin['files']['wire_stronger_request']['path']);diff=[k for k in set(request)|set(oldrequest) if request.get(k)!=oldrequest.get(k)]
check('only max_tokens changed',diff==['max_tokens'] and oldrequest['max_tokens']==4096 and request['max_tokens']==8192,diff)
oldbytes=Path(pin['files']['wire_stronger_request']['path']).read_bytes();newbytes=(op/'request.json').read_bytes()
check('literal request delta only',oldbytes.count(b'"max_tokens":4096')==1 and oldbytes.replace(b'"max_tokens":4096',b'"max_tokens":8192')==newbytes)
doc=run/'documents/doc-92211b8c7ba0'
check('request copies identical',newbytes==(doc/'stronger-request.json').read_bytes())
for field,filename in [('assembled','assembled.json'),('common_payload','common-payload.json'),('source','source.json')]:check('unchanged '+field,digest(doc/filename)==pin['files'][field]['sha256'])
assembled=read(doc/'assembled.json');source=read(doc/'source.json');restoration=read(doc/'restoration.json');wrapper=loads(request['messages'][1]['content'])
check('record and wire pins',hval(assembled['record'])==pin['record_sha256'] and hval(wrapper['payload'])==identity['identity']['wire_payload_sha256'] and wrapper['payload']==restoration['wire'])
check('native HTTP and finish',status['http_status']==200 and len(native['choices'])==1 and native['choices'][0]['finish_reason']=='stop' and native['choices'][0]['native_finish_reason']=='completed')
structured=loads(native['choices'][0]['message']['content']);check('whole response retained unmodified',structured==result['structured'])
expected={i['id'] for cat in ('events','routes','requirements','identities','uncertainties','alternative_groups') for i in assembled['record'][cat]};expected.update(t['id'] for e in assembled['record']['events'] for t in e['timing']);expected.update(c['id'] for r in assembled['record']['routes'] for c in r['components']);returned=[x['item_id'] for x in structured['assessments']];counts=collections.Counter(returned)
coverage=dict(expected_count=len(expected),returned_count=len(returned),unique_returned_count=len(counts),missing=sorted(expected-set(returned)),extra=sorted(set(returned)-expected),duplicates=sorted(k for k,n in counts.items() if n>1))
check('precise coverage defect',coverage==dict(expected_count=70,returned_count=71,unique_returned_count=71,missing=[],extra=['coverage'],duplicates=[]),coverage)

def load(name,p):
    s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
# Only import frozen offline helpers. Never call run(), transport, credential readers, or adapter main.
r=load('audit_frozen_runtime',ROOT/'runtime/run_pipeline.py')
check('reparse native response',r.a.parse_or((op/'response.body').read_bytes())==result)
validation=r.p.validate_verdict(source,assembled,structured);check('reproduced validation',validation==read(doc/'stronger-validation.json') and validation['errors']==['verdict must assess exactly every record item id'] and validation['normalized_verdict'] is None)
check('JSON schema alone passes',r.p.schema_errors(structured,r.p.VERDICT_SCHEMA)==[])
check('lossless wire restoration',r.codec.restore(wrapper['payload'],pin['payload_sha256'])==read(doc/'common-payload.json')['payload'])
observed_paths=list(run.glob('observed-*.json'));check('one observation',len(observed_paths)==1);observed=read(observed_paths[0]);r.validate_observation(observed)
check('observation digest',observed_paths[0].stem=='observed-'+digest(observed_paths[0]))
terminal=read(doc/'terminal.json');check('terminal receipts equal',terminal==read(doc/'progress-after-stronger.json')==complete['documents'][0]==observed['documents'][0])
judgment=terminal['arms']['stronger']['judgment'];check('rejected verdict not promoted',terminal['runtime_gate']=='stronger_verification_completed' and terminal['failure'] is None and terminal['arms']['stronger']['called'] and terminal['arms']['stronger']['status']=='review' and not terminal['arms']['stronger']['source_coverage_complete'] and not judgment['complete_record_shadow_accepted'] and all(x=='uncertain' for x in judgment['common_dimensions'].values()) and judgment['validation_errors']==validation['errors'] and not judgment['production_eligible'] and not judgment['action_ready'])
check('no fresh Jev judgment',terminal['arms']['jev']['called'] is False and terminal['arms']['jev']['status']=='not_started' and 'judgment' not in terminal['arms']['jev'])
usage=native['usage'];reserve=D(str(intent['reserved_nominal_usd']));reported=D(str(usage['cost']));rate=D(usage['prompt_tokens'])*D('.000002')+D(usage['completion_tokens'])*D('.000010');prior_debit=sum(D(x['charge']) for x in prior_rows);prior_reported=sum(D(str(x['reported'] or 0)) for x in prior_rows);total=prior_debit+max(reserve,reported)
admission=read(doc/'stronger-admission.json');estimate=len(newbytes)+1024
check('reservation exact computation',estimate==35747 and D(estimate)*D('.000002')+D(8192)*D('.000010')==reserve and admission['estimate']==estimate and admission['reservation_usd']==float(reserve))
check('usage costs',reported==D('.078036') and rate==D('.074482') and D(str(result['usage_rate_estimated_usd']))==rate and usage['total_tokens']==usage['prompt_tokens']+usage['completion_tokens'])
check('conservative cumulative cost',abs(total-D('.696390718'))<D('1e-15') and abs(D(str(complete['totals']['budget_charge_usd']))-total)<D('1e-15') and complete['totals']['operations']==1 and complete['totals']['jev_cases']==0 and complete['totals']['inventory_cases']==0 and complete['totals']['stronger_cases']==1)
check('paid outputs all frozen',set(x['path'] for x in E)=={str(p.relative_to(ROOT)) for p in run.rglob('*') if p.is_file()}|{'execution/service-account/live-intent.json','execution/service-account/live-result.json'})
continuity=read(BENCH/'runner-stability-review/deployment/continuity-result.json')
reader=Path('/Users/home/.local/libexec/yokel/research-credentials-stable-v1');check('installed reader unchanged',digest(reader)==continuity['reader_sha256']=='821f91b67f4c0c2d2a7f333e1381fab9aec1f9d8a9b8be8c34a0ee135494547e')
report=dict(state='passed',scope='Offline operational audit; semantic source review separate',provider_calls=0,credential_reads=False,freeze_E_sha256=digest(ROOT/'execution/freeze-E.json'),checks=checks,coverage=coverage,response=dict(http_status=status['http_status'],finish_reason=native['choices'][0]['finish_reason'],native_finish_reason=native['choices'][0]['native_finish_reason'],provider=native['provider'],model=native['model'],usage=usage,elapsed_seconds=status['elapsed_seconds'],parsed=True,exact_contract_valid=False,accepted_verdict=False),costs=dict(prior_operations=prior_rows,prior_debit_usd=str(prior_debit),new_reserved_usd=str(reserve),new_reported_usd=str(reported),new_usage_rate_estimated_usd=str(rate),cumulative_conservative_debit_usd=str(total),cumulative_native_reported_subtotal_usd=str(prior_reported+reported),prior_Jev_estimate_usd='.000502026',invoice_verified=False),observation_caveat='stronger_verification_completed means execution completed, not a valid or accepted verdict; common_dimensions uncertain are forced invalid-response fallbacks, not model judgments')
(HERE/'RESULT.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps({'state':'passed','checks':len(checks),'coverage':coverage,'costs':report['costs']},indent=2))
