"""Bounded offline review reproductions; no implementation edits or transport clients."""
import copy, importlib.util, json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
c=load('review_controls',R/'runtime/offline_checks.py');r=c.r
e=load('review_evaluator',R/'protocol/evaluate.py')
s,inv,verdict=c.fixture()
def transport(stage,body):return inv if stage=='inventory' else verdict if stage=='stronger' else {k:'fail' for k in r.CRITERIA}
run=r.simulate(s,inv,transport)
observed={'schema_version':'round7.observed.v1','documents':[run['observed']]}
results={}
def check(name,mutate):
    candidate=copy.deepcopy(observed);mutate(candidate['documents'][0])
    try:e.validate_observed(candidate);results[name]={'rejected':False}
    except ValueError as err:results[name]={'rejected':True,'reason':str(err)}
check('negative_judgment_promoted_to_accepted',lambda d:d['arms']['jev'].update(status='accepted_complete'))
check('accepted_judgment_removed',lambda d:d['arms']['stronger'].pop('judgment'))
check('completed_pair_has_failed_arm',lambda d:d['arms']['jev'].update(status='failed',source_coverage_complete=False))
check('first_arm_failed_but_later_called',lambda d:(d.update(runtime_gate='verification_failed',gate_reasons=['jev failure']),d['arms']['jev'].update(status='failed',source_coverage_complete=False)))
def size_inventory_only(d):
    d.update(runtime_gate='request_size_review',gate_reasons=['inventory size'],record_sha256=None,payload_sha256=None)
    d['arms']={a:dict(status='not_started',called=False,payload_sha256=None,source_coverage_complete=False,reason='size') for a in r.CRITERIA if a in ('jev','stronger')}
    d['arms']={a:dict(status='not_started',called=False,payload_sha256=None,source_coverage_complete=False,reason='size') for a in ('jev','stronger')}
check('size_gate_has_inventory_but_no_record',size_inventory_only)
for number in (0,0.0,1):
    candidate=copy.deepcopy(observed);candidate['costs']={'extraction':{'usage_estimate_usd':number}}
    try:e.validate_observed(candidate);results['cost_'+repr(number)]={'rejected':False}
    except ValueError as err:results['cost_'+repr(number)]={'rejected':True,'reason':str(err)}
s41=copy.deepcopy(s);s41['pdf_pages']=41
page_run=r.simulate(s41,inv,transport)
results['41_pdf_pages']={'gate':page_run['observed']['runtime_gate'],'dispatches':page_run['synthetic_dispatches']}
base=r.requests(s,r.p.assemble(s,inv))['jev']['body']
b=copy.deepcopy(base);b['state']['review_padding']='x'*40000
results['jev_state_only_overlimit']=r.a.admission(b,'jev')
b=copy.deepcopy(base)
for question in b['questions'].values():question['instructions']+='x'*12000
results['jev_total_only_overlimit']=r.a.admission(b,'jev')
for failed in ('jev','stronger'):
    def fail_transport(stage,body):
        if stage==failed:raise RuntimeError('synthetic failure')
        return inv if stage=='inventory' else verdict if stage=='stronger' else {k:'pass' for k in r.CRITERIA}
    result=r.simulate(s,inv,fail_transport)
    e.validate_observed({'schema_version':'round7.observed.v1','documents':[result['observed']]})
    results[failed+'_failure_preservation']={'gate':result['observed']['runtime_gate'],'arms':{k:{f:v[f] for f in ('status','called','source_coverage_complete')} for k,v in result['observed']['arms'].items()}}
print(json.dumps(results,indent=2))
