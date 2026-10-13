"""Versioned stronger-only operational states. No fabricated prior/current Jev invocation."""
import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parent
path=ROOT.parents[1]/'round8/protocol/evaluate.py'
spec=importlib.util.spec_from_file_location('frozen_r8_state_shapes',path);base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
VERSION='round8-stronger-cap-probe.observed.v1'
GATES=('not_started','request_size_review','stronger_verification_completed','verification_failed','operation_pause','postresponse_budget_stop')
def require(ok,message):
    if not ok:raise ValueError('stronger-only observed: '+message)
def validate_observed(value):
    schema=base.observed_schema();schema['properties']['schema_version']['enum']=[VERSION];document=schema['properties']['documents']['items'];document['properties']['runtime_gate']['enum']=list(GATES);document['properties']['failure']['properties']['stage']['enum']=['stronger']
    errors=base.P.schema_errors(value,schema);require(not errors,'shape: '+'; '.join(errors));require(len(value['documents'])==1,'one exact document')
    d=value['documents'][0];gate=d['runtime_gate'];failure=d['failure'];j=d['arms']['jev'];s=d['arms']['stronger'];record=d['record_sha256'];payload=d['payload_sha256']
    require(j['status']=='not_started' and not j['called'] and j['payload_sha256'] is None and not j['source_coverage_complete'] and 'judgment' not in j,'Jev must remain uncalled with no borrowed judgment')
    require((record is None)==(payload is None) and (record is None or d['inventory_sha256'] is not None),'retained artifact stage mismatch')
    require(d['provider_service_error']==bool(failure and failure['kind']=='http_error'),'HTTP service flag semantics')
    if failure:
        require(failure['stage']=='stronger','only stronger failure stage')
        if failure['kind']=='http_error':require(failure['intent_recorded'] and failure['http_status'] is not None and failure['http_status']!=200,'HTTP failure facts')
        else:require(failure['http_status'] is None,'non-HTTP cause with HTTP status')
        require(not failure['intent_recorded'] or failure['operation_id'] is not None,'attempt lacks identity')
    if gate=='not_started':require(record is None and d['inventory_sha256'] is None and not s['called'] and failure is None and d['gate_reasons'],'unstarted facts')
    elif gate=='request_size_review':require(record is not None and not s['called'] and failure is None and d['gate_reasons'],'admission denied facts')
    elif gate=='stronger_verification_completed':require(record is not None and s['called'] and s['status'] in ('accepted_complete','review') and failure is None and not d['gate_reasons'],'completed facts')
    elif gate=='verification_failed':require(record is not None and s['called'] and s['status']=='failed' and failure and failure['intent_recorded'] and failure['kind'] in ('http_error','transport_uncertain','invalid_response','local_error') and d['gate_reasons'],'failed operation facts')
    elif gate=='operation_pause':require(record is not None and not s['called'] and failure and not failure['intent_recorded'] and failure['kind'] in ('budget_stop','operator_pause','local_error') and d['gate_reasons'],'safe pause facts')
    elif gate=='postresponse_budget_stop':require(record is not None and s['called'] and s['status'] in ('accepted_complete','review') and failure and failure['intent_recorded'] and failure['kind']=='budget_stop' and d['gate_reasons'],'completed paid-result budget-stop facts')
    require(s['called']==(s['status']!='not_started'),'called/status mismatch')
    if s['called']:require(record is not None and s['payload_sha256']==payload,'payload binding')
    else:require(s['payload_sha256'] is None and not s['source_coverage_complete'],'uncalled fabricated coverage')
    if s['status'] in ('accepted_complete','review'):
        require('judgment' in s,'missing judgment');v=s['judgment'];require(v.get('arm')=='stronger' and v['deterministic_review_reasons']==d['review_reasons'],'judgment metadata')
        accepted=not v['validation_errors'] and not d['review_reasons'] and all(x=='pass' for x in v['common_dimensions'].values());require(v['complete_record_shadow_accepted']==accepted and v['status']==s['status'] and (s['status']=='accepted_complete')==accepted,'unchanged semantic acceptance gate');require(s['source_coverage_complete']==(not v['validation_errors']),'complete assessment coverage')
    else:require('judgment' not in s and not s['source_coverage_complete'],'failed/uncalled fabricated judgment')
    return value
