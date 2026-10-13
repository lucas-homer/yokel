#!/usr/bin/env python3
"""Bounded validator boundary probes; synthetic evidence is explicitly synthetic.

Only writes beneath this review directory. Does not replay or mutate lane code.
Run with an optional path to the shared validate.py. Results distinguish actual
structural gaps from semantic checks intentionally delegated to source review.
"""
import copy
import hashlib
import importlib.util
import json
import pathlib
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = pathlib.Path(__file__).resolve().parent
VALIDATOR = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path('/Users/home/.codex/worktrees/e8f4/yokel/docs/research/state-rulemaking-spike/validate.py')
spec = importlib.util.spec_from_file_location('shared_validator', VALIDATOR)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)

TEXT = ('SYNTHETIC REVIEW FIXTURE, NOT A PUBLIC SOURCE.\n'
        'Filing date: 2026-10-05.\n'
        'Comments due October 9, 2026 at 5:00 p.m.\n'
        'Comments accepted for 25 days; hearing requests within 20 days.\n'
        'Only section 2 of notice 26-01-001 is withdrawn.\n')
base_artifact = dict(artifact_id='synthetic-text', path='evidence.txt',
    sha256=hashlib.sha256(TEXT.encode()).hexdigest(),
    source_url='https://example.invalid/synthetic-review',
    retrieved_at='2026-10-05T18:00:00Z', media_type='text/plain',
    representation='native_text', source_lineage='Synthetic test fixture created by reviewer.',
    collector='review-adversarial', is_inherited=False)
base_observation = dict(schema_version='state-spike-v1', observation_id='synthetic-filing',
    jurisdiction='US-WA', source_record_id='26-01-002',
    subject={'kind':'notice', 'id':'synthetic:wa:26-01-002'},
    predicate='filing_date', value={'kind':'date','date':'2026-10-05'},
    evidence=[{'artifact_id':'synthetic-text','locator':'line 2',
               'quote':'Filing date: 2026-10-05.', 'support':'text_exact'}],
    method={'kind':'deterministic','name':'synthetic-test','version':'1'},
    review_state='candidate', warnings=[])

cases = []
def case(name, category, change, desired='reject'):
    manifest, observations = [copy.deepcopy(base_artifact)], [copy.deepcopy(base_observation)]
    change(manifest, observations)
    cases.append((name, category, manifest, observations, desired))

case('valid_baseline', 'control', lambda m,o:None, 'accept')
case('missing_quote', 'control', lambda m,o:o[0]['evidence'][0].update(quote='not retained'))
case('hash_tampering', 'control', lambda m,o:m[0].update(sha256='0'*64))
case('invalid_date', 'control', lambda m,o:o[0]['value'].update(date='2026-02-30'))
case('duplicate_id', 'control', lambda m,o:o.append(copy.deepcopy(o[0])))
case('path_escape', 'control', lambda m,o:m[0].update(path='../outside.txt'))
case('provenance_fields_wrong_types', 'contract_gap', lambda m,o:m[0].update(source_url=17,retrieved_at={'unknown':True},media_type=[],collector=None))
case('fresh_artifact_has_no_retrieval_time', 'contract_gap', lambda m,o:m[0].update(retrieved_at=None))
case('unresolved_zone_but_claimed_instant', 'contract_gap', lambda m,o:o[0].update(predicate='comment_close',value={'kind':'local_datetime','date':'2026-10-09','time':'17:00','timezone_text':None,'iana_zone':None,'utc_instant':'2026-10-10T00:00:00Z'}))
case('zone_and_instant_contradict', 'consistency_gap', lambda m,o:o[0].update(predicate='comment_close',value={'kind':'local_datetime','date':'2026-10-09','time':'17:00','timezone_text':'UTC','iana_zone':'UTC','utc_instant':'2026-10-08T00:00:00Z'}))
case('infinite_relative_duration', 'contract_gap', lambda m,o:o[0].update(predicate='comment_duration',value={'kind':'relative','duration':float('inf'),'unit':'days','anchor':None,'day_basis':None,'computed_close':None}))
case('wrong_date_role_with_exact_quote', 'semantic_review_required', lambda m,o:o[0].update(predicate='comment_close'))
case('wrong_locator_with_exact_quote', 'semantic_review_required', lambda m,o:o[0]['evidence'][0].update(locator='line 999'))
def swap_duration(m,o):
    o[0].update(predicate='comment_duration',value={'kind':'relative','duration':20,'unit':'days','anchor':None,'day_basis':None,'computed_close':None})
    o[0]['evidence'][0].update(quote='Comments accepted for 25 days; hearing requests within 20 days.')
case('twenty_vs_twentyfive_swap', 'semantic_review_required', swap_duration)
def enlarge_withdrawal(m,o):
    o[0].update(predicate='withdraws',value={'target_source_record_id':'26-01-001','scope':'entire proceeding'})
    o[0]['evidence'][0].update(quote='Only section 2 of notice 26-01-001 is withdrawn.')
case('partial_withdrawal_becomes_full', 'semantic_review_required', enlarge_withdrawal)
def visual_without_note(m,o):
    m[0].update(path='synthetic.pdf',representation='pdf',media_type='application/pdf',sha256=hashlib.sha256(b'%PDF-1.4\n%synthetic fixture only\n').hexdigest())
    o[0]['evidence'][0].update(support='visual_review',locator='page 1 checkbox',quote='[checked]')
    o[0]['method']['kind']='manual_visual'
case('visual_claim_without_saved_review_note', 'contract_gap', visual_without_note)
case('nonobject_observation_crashes', 'robustness_gap', lambda m,o:o.append(None))
case('nonobject_manifest_crashes', 'robustness_gap', lambda m,o:m.append(None))

results=[]
for name, category, manifest, observations, desired in cases:
    with tempfile.TemporaryDirectory(prefix='fixture-', dir=ROOT) as tmp:
        lane=pathlib.Path(tmp)
        (lane/'evidence.txt').write_text(TEXT)
        (lane/'synthetic.pdf').write_bytes(b'%PDF-1.4\n%synthetic fixture only\n')
        (lane/'manifest.json').write_text(json.dumps(manifest))
        (lane/'observations.json').write_text(json.dumps(observations))
        try:
            result=validator.validate_lane(lane)
            outcome='accept' if result['passed'] else 'reject'
            details=result['failures']
        except Exception as exc:
            outcome='crash'
            details={'exception':type(exc).__name__, 'message':str(exc)}
        results.append(dict(case=name,category=category,desired=desired,outcome=outcome,details=details))
report={'validator_path':str(VALIDATOR),'validator_sha256':hashlib.sha256(VALIDATOR.read_bytes()).hexdigest(),
        'warning':'Synthetic probes. Acceptance of semantic mutations is expected unless separately source-reviewed.',
        'cases':results}
(ROOT/'adversarial-results.json').write_text(json.dumps(report,indent=2)+'\n')
for result in results:
    print(f"{result['outcome']:6} {result['category']:26} {result['case']}")
