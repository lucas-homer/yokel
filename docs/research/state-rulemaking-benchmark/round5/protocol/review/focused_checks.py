import copy,contextlib,hashlib,importlib.util,io,json,sys,tempfile,unittest
from pathlib import Path
B=Path('/Users/home/.codex/worktrees/e8f4/yokel/docs/research/state-rulemaking-benchmark'); R=B/'round5'
sys.path.insert(0,str(R/'runtime'))
import offline_checks as t
r=t.r;j=r.j;p=r.module_at(t.PIPELINE);soft,_=r.routing_policy(p)
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
log=io.StringIO()
with contextlib.redirect_stdout(log):
 result=unittest.TextTestRunner(stream=log).run(unittest.defaultTestLoader.loadTestsFromTestCase(t.Tests))
assert result.wasSuccessful()
checks=[]
def actual(name,text,expected,labels=None,scope='full_notice'):
 with tempfile.TemporaryDirectory() as td,contextlib.redirect_stdout(log):
  def fake(payload):
   c=payload['state']['candidate']; dims=(labels or {}).get(c['value'],{})
   assert payload['state']['source_text']==text
   assert all(text[e['start']:e['end']]==e['quote'] for e in payload['state']['evidence'])
   return 200,t.response(payload,dims)
  outcome,terminal,calls,_=t.execute(td,text,scope=scope,fake=fake)
  accepted=sorted((x['field'],x['candidate_value']) for x in terminal['observations'] if x['shadow_status']=='text_supported')
  assert accepted==sorted(expected),(name,accepted,expected)
  for row in terminal['observations']:
   assert row['stage']=='terminal_shadow_observation'
   yes=row['shadow_status']=='text_supported'
   assert row['disposition']==('accept_shadow' if yes else 'review')
   assert row['action_readiness']==('requires_source_verification' if yes else 'not_ready')
  assert terminal['action_ready'] is False and terminal['production_eligible'] is False
  checks.append({'name':name,'passed':True,'fake_POSTs':len(calls),'accepted':accepted})
D=('comment_deadline','2026-10-31');E=('submission_email','comments@example.gov')
actual('unicode_incidental_if_and_date_email','😀 If accessibility help is needed, call staff.\n\nWritten comments close October 31, 2026.\n\nSend written comments to comments@example.gov.',[D,E])
actual('same_DATE_real_contingency','If a hearing is requested, written comments close October 31, 2026.\n\nSend written comments to comments@example.gov.',[E])
actual('unconditional_clock_date','Written comments must be received by October 31, 2026 at 5 p.m. Pacific Time.',[D])
actual('email_competitor_positive_wrong_role','Submit written comments to comments@example.gov.\n\nFor accessibility help contact access@example.gov.',[E],{'access@example.gov':{'role':'mismatched'}})
actual('email_competitor_unknown','Submit written comments to comments@example.gov.\n\nFor accessibility help contact access@example.gov.',[],{'access@example.gov':{'role':'insufficient'}})
actual('two_confirmed_dates_hard_block','Written comments close October 31, 2026.\n\nWritten comments close November 2, 2026.',[])
actual('split_paragraph_year_never_borrowed','Written comments close October 31\n\n2026.',[])
actual('invalid_calendar_date','Written comments close February 29, 2026.',[])
actual('relative_DATE_independent_EMAIL','Written comments close within 30 days after publication.\n\nSend written comments to comments@example.gov.',[E])
actual('unknown_notice_scope','Written comments close October 31, 2026.',[],scope='unknown')
actual('semantic_only_remote_qualification_rejected','Written comments close October 31, 2026.\n\nThe deadline applies only in the event that a hearing occurs.',[],{'2026-10-31':{'support':'contradicted','condition':'omitted_or_changed'}})
# Local gates independently reject altered literal, evidence, unknown issue, and weakened claim.
item=p.propose('Written comments close October 31, 2026.','doc-0123456789ab')['candidates'][0]
for name in ('claim','literal','unknown','evidence'):
 bad=copy.deepcopy(item)
 if name=='claim':bad['case']['candidate']['claim']='Written comments close October 31, 2026 if a hearing occurs.'
 elif name=='literal':bad['value_span']['quote']='October 30, 2026'
 elif name=='unknown':bad['issues'].append('unreviewed_clearance')
 else:bad['case']['evidence'][0]['quote']='altered'
 payload,gate=r.local_gate(bad,soft);assert payload is None
 checks.append({'name':'mutation_'+name,'passed':True,'blocking_issues':gate['blocking_issues']})
# Positive classification is required for a DATE alternative, not just lack of support.
for role,expected in [('mismatched','text_supported'),('insufficient','review')]:
 rows=[{'field':'comment_deadline','candidate_value':'2026-10-31','shadow_status':'text_supported','operation_status':'completed','dimensions':{'role':{'label':'matched'}}},{'field':'comment_deadline','candidate_value':'2026-11-02','shadow_status':'review','operation_status':'completed','dimensions':{'role':{'label':role}}}]
 assert r.resolve_email_multiplicity(rows)[0]['shadow_status']==expected
 checks.append({'name':'DATE_alternative_'+role,'passed':True})
# Run immutable historical evaluator synthetic suite and verify R5 terminal compatibility.
sys.path.insert(0,str(B/'round4/evaluation'));evtest=load('evtest',B/'round4/evaluation/test_evaluate.py')
with contextlib.redirect_stdout(log):eresult=unittest.TextTestRunner(stream=log).run(unittest.defaultTestLoader.loadTestsFromTestCase(evtest.EvaluatorTests))
assert eresult.wasSuccessful()
# Feed real Round5 terminal rows to unchanged R4 evaluator with synthetic audit labels.
with tempfile.TemporaryDirectory() as td,contextlib.redirect_stdout(log):
 _,terminal,_,_=t.execute(td,'Written comments close October 31, 2026.\n\nSubmit written comments to A+b@Example.gov.')
 m,l=evtest.setup();audits=[]
 for row in terminal['observations']:
  typ='DATE' if row['field']=='comment_deadline' else 'EMAIL'
  audits.append(evtest.audit(typ,case=row['case_id']))
 scored=evtest.evaluate(m,l,{evtest.ID:terminal},{'schema_version':'round4.evaluation.audits.v1','audits':audits})
 assert scored['correct_shadow_acceptance_coverage']['pooled']['value']==1
 assert scored['unsafe_acceptance_fraction']['value']==0
 assert scored['scheduled_documents']==1
 checks.append({'name':'actual_R5_terminal_into_unchanged_R4_evaluator','passed':True,'synthetic_correct_accepts':2})
# Hash invariants after tests.
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
verify={}
a=json.loads((R/'pipeline/freeze.json').read_text());b=json.loads((R/'runtime/implementation-pins.READY.json').read_text());s=json.loads((R/'sources/prep-manifest.json').read_text());e=json.loads((R/'protocol/REUSED-EVALUATOR-PINS.json').read_text())
for label,pairs in [('pipeline',[(R/'pipeline'/k,v) for k,v in a['files_sha256'].items()]),('runtime',[(Path(k),v) for k,v in b['code'].items()]),('source_prep',[(R/'sources'/k,v) for k,v in s['files'].items()]),('evaluator',[(B/k,v) for k,v in e['files'].items()])]:
 assert all(sha(path)==v for path,v in pairs),label
 verify[label]={'files':len(pairs),'match':True}
assert sha(R/'pipeline/freeze.json')=='aa35c6c288fe46e9780b5c7762aebbd7b934d990aca3c95e41cbf8ff798e01a8'
assert sha(R/'runtime/implementation-pins.READY.json')=='1c6c04badde7600672b74f88ada498ddbf4279929fbe6b38c0b38bd297e4845d'
r.verify_implementation(R/'runtime/implementation-pins.READY.json')
report={'status':'checks_passed','runtime_suite':{'tests':result.testsRun,'success':True},'historical_evaluator_suite':{'tests':eresult.testsRun,'success':True},'independent_checks':checks,'pin_verification':verify,'actual_provider_calls':0,'fresh_source_access':False,'limits':'Semantic-only phrasing relies on model judgment and post-run source audit; fake transport does not establish accuracy.'}
Path('/tmp/round5-focused-review-results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'checks':len(checks),'runtime_suite':result.testsRun,'evaluator_suite':eresult.testsRun,'pins':verify,'all_passed':True}))
