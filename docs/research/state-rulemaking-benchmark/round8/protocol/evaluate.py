#!/usr/bin/env python3
"""R8 live-state validation and explicit version adapter over frozen R7 scoring. No providers."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BENCH=ROOT.parents[1]
PINS=json.loads((ROOT/'reuse-pins.json').read_text())['files']
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def require(ok,message):
    if not ok:raise ValueError(message)
def load(name,relative):
    path=BENCH/relative
    require(digest(path)==PINS[relative],'read-only dependency hash changed: '+relative)
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
for relative,expected in PINS.items():require(digest(BENCH/relative)==expected,'read-only dependency hash changed: '+relative)
P=load('r8_pinned_r7_pipeline','round7/pipeline/pipeline.py')
BASE=load('r8_isolated_r7_scoring','round7/protocol/evaluate.py')
CATEGORIES=BASE.CATEGORIES
ARMS=BASE.ARMS
GATES=('source_review','request_size_review','assembly_review','inventory_failed','paired_verification_completed','verification_failed','operation_pause','not_started','postresponse_budget_stop')
KINDS=('http_error','transport_uncertain','invalid_response','budget_stop','operator_pause','local_error')
HASH={'type':'string','pattern':'^[a-f0-9]{64}$'}
VERSIONS={'schedule':'round8.schedule.v1','truth':'round8.truth.v1','audit':'round8.matching-audit.v1','observed':'round8.observed.v1'}

def observed_schema():
    schema=json.loads((BENCH/'round7/protocol/observed.schema.json').read_text())
    schema['properties']['schema_version']['enum']=['round8.observed.v1']
    doc=schema['properties']['documents']['items']
    doc['properties']['runtime_gate']['enum']=list(GATES)
    doc['properties']['failure']={'type':['object','null'],'properties':{
        'stage':{'type':'string','enum':['inventory','jev','stronger']},
        'kind':{'type':'string','enum':list(KINDS)},
        'intent_recorded':{'type':'boolean'},
        'operation_id':{'type':['string','null'],'minLength':1},
        'http_status':{'type':['integer','null'],'minimum':100,'maximum':599},
        'evidence_sha256':HASH},
        'required':['stage','kind','intent_recorded','operation_id','http_status','evidence_sha256'],
        'additionalProperties':False}
    doc['required'].append('failure')
    return schema

def validate_observed(observed):
    errors=P.schema_errors(observed,observed_schema());require(not errors,'observed schema: '+'; '.join(errors))
    ids=[d['document_id'] for d in observed['documents']];require(len(ids)==len(set(ids)),'duplicate observed document')
    for d in observed['documents']:
        gate=d['runtime_gate'];failure=d['failure'];j=d['arms']['jev'];s=d['arms']['stronger']
        called=[a for a,v in d['arms'].items() if v['called']]
        inv,record,payload=(d[k] for k in ('inventory_sha256','record_sha256','payload_sha256'))
        require((record is None)==(payload is None),'record/payload must exist together')
        require(record is None or inv is not None,'record requires inventory')
        require(d['provider_service_error']==bool(failure and failure['kind']=='http_error'),'service flag must mean retained HTTP error only')
        if failure:
            if failure['kind']=='http_error':require(failure['intent_recorded'] and failure['http_status'] is not None and failure['http_status']!=200,'HTTP error lacks attempted call/non-200 status')
            else:require(failure['http_status'] is None,'non-HTTP failure carries HTTP error status')
            if failure['intent_recorded']:require(failure['operation_id'] is not None,'attempted failure needs operation identity')
        local=gate in ('source_review','request_size_review','assembly_review','not_started')
        if local:
            require(not called and failure is None and d['gate_reasons'],'local gate cannot fabricate call/failure')
            if gate in ('source_review','not_started'):require(inv is None and record is None,'unstarted/source gate has artifacts')
            if gate=='assembly_review':require(inv is not None and record is None,'assembly gate artifacts')
            if gate=='request_size_review':require((inv is None)==(record is None),'admission gate artifact stage mismatch')
        if gate=='inventory_failed':
            require(not called and inv is None and record is None and d['gate_reasons'],'inventory failure artifacts/arms')
            require(failure and failure['stage']=='inventory' and failure['intent_recorded'] and failure['kind'] in ('http_error','transport_uncertain','invalid_response','local_error'),'inventory failure needs attempted inventory cause')
        if gate=='paired_verification_completed':
            require(len(called)==2 and failure is None and not d['gate_reasons'] and all(v['status'] in ('accepted_complete','review') for v in d['arms'].values()),'completed pair invocation/gate mismatch')
        if gate=='verification_failed':
            require(failure and failure['intent_recorded'] and failure['kind'] in ('http_error','transport_uncertain','invalid_response','local_error') and d['gate_reasons'],'verification failure needs attempted failure cause')
            require((failure['stage']=='jev' and j['status']=='failed' and not s['called']) or (failure['stage']=='stronger' and j['status'] in ('accepted_complete','review') and s['status']=='failed'),'failed verification violates serial dispatch')
        if gate=='postresponse_budget_stop':
            require(failure and failure['kind']=='budget_stop' and failure['intent_recorded'] and d['gate_reasons'],'postresponse stop needs completed-operation budget receipt')
            require(inv is not None,'completed inventory must be retained at budget stop')
            if failure['stage']=='inventory':require(not called,'inventory budget stop cannot dispatch verifiers')
            if failure['stage']=='jev':require(j['status'] in ('accepted_complete','review') and not s['called'],'Jev budget stop must preserve completed Jev only')
            if failure['stage']=='stronger':require(all(v['status'] in ('accepted_complete','review') for v in d['arms'].values()),'stronger budget stop must preserve both completed judgments')
        if gate=='operation_pause':
            require(failure and not failure['intent_recorded'] and failure['kind'] in ('budget_stop','operator_pause','local_error') and d['gate_reasons'],'pause needs local no-intent receipt')
            require(not s['called'] and j['status'] in ('not_started','accepted_complete','review'),'pause violates serial dispatch')
            if failure['stage']=='inventory':require(not called and inv is None,'inventory pause already progressed')
            if failure['stage']=='jev':require(not called and record is not None,'Jev pause requires assembled payload')
            if failure['stage']=='stronger':require(j['called'] and record is not None,'stronger pause requires prior Jev judgment')
        for arm,v in d['arms'].items():
            require(v['called']==(v['status']!='not_started'),'called/status mismatch')
            if not v['called']:require(v['payload_sha256'] is None and not v['source_coverage_complete'],'uncalled arm fabricated coverage/payload')
            else:require(record is not None and v['payload_sha256']==payload,'called arm payload/record mismatch')
            if v['status'] in ('accepted_complete','review'):
                require('judgment' in v,'called judgment missing');judgment=v['judgment']
                require(judgment.get('arm',arm)==arm and judgment['deterministic_review_reasons']==d['review_reasons'],'judgment arm/review reasons disagree')
                accepted=not judgment['validation_errors'] and not d['review_reasons'] and all(x=='pass' for x in judgment['common_dimensions'].values())
                require(judgment['complete_record_shadow_accepted']==accepted and judgment['status']==v['status'] and (v['status']=='accepted_complete')==accepted,'judgment/status/dimensions disagree')
                require(v['source_coverage_complete']==(not judgment['validation_errors']),'coverage differs from complete validated assessment schedule')
            else:require('judgment' not in v and not v['source_coverage_complete'],'failed/uncalled arm has judgment/coverage')
        require(not s['called'] or j['called'],'stronger cannot precede Jev')
    return observed

# Isolated module instance only. Preserve every live state/flag; replace validation, not metrics.
def _validate_projection(observed):
    value=copy.deepcopy(observed);require(value['schema_version']=='round7.observed.v1','projection version');value['schema_version']=VERSIONS['observed'];return validate_observed(value)
BASE.validate_observed=_validate_projection

def evaluate(schedule,truth,audit,observed):
    originals=dict(schedule=schedule,truth=truth,audit=audit,observed=observed)
    projected={}
    for name,value in originals.items():
        require(value.get('schema_version')==VERSIONS[name],name+' version')
        projected[name]=copy.deepcopy(value);projected[name]['schema_version']=value['schema_version'].replace('round8.','round7.',1)
    validate_observed(observed)
    report=BASE.evaluate(*(projected[k] for k in ('schedule','truth','audit','observed')))
    report['schema_version']='round8.evaluation.report.v1'
    report['operational_failures']={kind:sum(bool(d['failure'] and d['failure']['kind']==kind) for d in observed['documents']) for kind in KINDS}
    report['provider_service_errors']=sum(d['provider_service_error'] for d in observed['documents'])
    report['version_adapter']={'schema_version':'round8.r7_scoring_adapter.v1','changes':'top-level input/report version tags and R8 strict live-state validation only; original judgments, states, flags, hashes and costs preserved','original_canonical_sha256':{k:P.sha(P.canonical(v)) for k,v in originals.items()},'projection_canonical_sha256':{k:P.sha(P.canonical(v)) for k,v in projected.items()},'scoring_code_sha256':PINS['round7/protocol/evaluate.py']}
    report['limitations'].extend(['Independent AI image reference, not human-adjudicated gold.','Called includes uncertain attempted POSTs bound to durable intents; HTTP-error counts do not establish provider outage.'])
    return report

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('schedule','truth','audit','observed','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();inputs={k:json.loads(getattr(args,k).read_text()) for k in ('schedule','truth','audit','observed')}
    report=evaluate(**inputs);report['input_file_sha256']={k:digest(getattr(args,k)) for k in inputs}
    with args.output.open('x') as out:json.dump(report,out,indent=2,allow_nan=False);out.write('\n')
if __name__=='__main__':main()
