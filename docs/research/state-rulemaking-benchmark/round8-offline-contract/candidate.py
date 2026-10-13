"""Offline prompt candidate and paired sizing; no transport, credentials, repair or live entry."""
import copy,hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
PRIOR_DEBIT=.261774

def verify_inputs():
    pins=json.loads((ROOT/'input-pins.json').read_bytes())
    assert pins['schema_version']=='round8-offline-contract.inputs.v1'
    for name,want in pins['files'].items():
        path=Path(name);assert path.is_absolute() and path.resolve().is_relative_to(BASE.resolve()) and hashlib.sha256(path.read_bytes()).hexdigest()==want, name
    return len(pins['files'])
verify_inputs()
spec=importlib.util.spec_from_file_location('offline_frozen_r7',BASE/'round7/runtime/run_pipeline.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
p,a=r.p,r.a

def inventory_body(source):
    # Same cap-probe baseline request, one exact appended instruction block only.
    body=r.requests(source)['inventory']['body'];body['max_tokens']=12288
    body['messages'][0]['content']+=(ROOT/'prompt-delta.txt').read_text()
    return body

def admission(body,stage,stronger_guard=35000):
    if stronger_guard not in (35000,40000):raise ValueError('only unchanged/proposed stronger guards')
    if stage not in ('jev','stronger','inventory'):raise ValueError('unknown stage')
    baseline=a.admission(body,stage)
    if stage=='inventory':
        admitted=baseline['estimate']<=35000 and body.get('max_tokens')==12288
        return {**baseline,'admitted':admitted,'reason':None if admitted else 'inventory input/cap violation','reservation_usd':baseline['estimate']*a.PRICES['prompt']+12288*a.PRICES['completion'] if admitted else None}
    if stage!='stronger' or stronger_guard==35000:return baseline
    admitted=baseline['estimate']<=40000 and body.get('max_tokens')==4096
    return {**baseline,'cap':40000,'admitted':admitted,'reason':None if admitted else 'proposed stronger input/cap violation','reservation_usd':baseline['estimate']*a.PRICES['prompt']+4096*a.PRICES['completion'] if admitted else None}

def paired_bodies(source,inventory):
    assembled=p.assemble(source,inventory)
    if not assembled['validation']['valid']:raise ValueError('strict assembly rejection; no repair')
    plans=r.requests(source,assembled)
    assert plans['jev']['body']['state']==a.loads(plans['stronger']['body']['messages'][1]['content'])['payload']
    return assembled,{stage:plans[stage]['body'] for stage in ('jev','stronger')}

def paired_gate(bodies,stronger_guard=35000,synthetic_dispatch=None):
    # Both exact final-body admissions finish before any optional synthetic callback.
    checks={stage:admission(bodies[stage],stage,stronger_guard) for stage in ('jev','stronger')}
    if not all(row['admitted'] for row in checks.values()):return {'admission':checks,'synthetic_dispatches':[]}
    stages=[]
    if synthetic_dispatch is not None:
        for stage in ('jev','stronger'):synthetic_dispatch(stage,copy.deepcopy(bodies[stage]));stages.append(stage)
    return {'admission':checks,'synthetic_dispatches':stages}

def observed():
    run=BASE/'round8-cap-probe/execution/run';doc=run/'documents/doc-92211b8c7ba0';op=run/'operations/inventory-8f69eccb0e19f2d6e43cc72d'
    source=a.loads((doc/'source.json').read_bytes());parsed=a.parse_or((op/'response.body').read_bytes())
    assert parsed==a.loads((op/'result.json').read_bytes())
    return source,parsed['structured']

def budget(stronger_guard):
    if stronger_guard not in (35000,40000):raise ValueError('guard')
    new=35000*a.PRICES['prompt']+12288*a.PRICES['completion']+stronger_guard*a.PRICES['prompt']+4096*a.PRICES['completion']+64000*a.PRICES['jev']
    return {'prior_conservative_debit_usd':PRIOR_DEBIT,'new_nominal_reservation_usd':new,'aggregate_nominal_usd':PRIOR_DEBIT+new,'shared_budget_usd':2,'refund_or_reset':False}

def budget_admitted(new_charges,reserve):
    if any(type(value) not in (int,float) or not __import__('math').isfinite(value) or value<0 for value in (new_charges,reserve)):raise ValueError('invalid budget amount')
    return PRIOR_DEBIT+new_charges+reserve<=2
