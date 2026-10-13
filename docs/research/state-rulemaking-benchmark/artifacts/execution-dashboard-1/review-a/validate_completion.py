"""Reproducible final invariants; manual judgments remain in judgments.json."""
from pathlib import Path
import json,hashlib,collections
R=Path('/Users/home/.codex/worktrees/e8f4/yokel/docs/research/state-rulemaking-benchmark/artifacts');O=R/'execution-dashboard-1/review-a'
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda n:[json.loads(s) for s in (O/n).read_text().splitlines()]
f=read('field-scores.jsonl');d=read('document-scores.jsonl');e=read('extra-assertions.jsonl');ops=read('operation-records.jsonl')
b=json.loads((O/'completion-baseline.json').read_text());freeze=json.loads((R/'corpus-freeze.json').read_text())
assert h(R/'corpus-freeze.json')==b['freeze_sha256']=='900f21e8a75d50444f12a0e3814d665a4f401a0d689194465d0b00467a762946'
for p,m in freeze['files'].items():assert h(R/p)==m['sha256'],p
for n,old in b['dashboard_rows'].items():assert old==[x for x in read(n) if x.get('execution_lane')=='execution-dashboard-1'],n
for p,old in b['v1_files'].items():assert h(R/p)==old,p
assert len(f)==144 and len(d)==len(ops)==16
assert len({(x['fixture_id'],x['arm'],x['field_id']) for x in f})==144
assert len({(x['fixture_id'],x['arm']) for x in d})==16
assert all(x['evaluation_status']=='complete' for x in f+d)
assert all(x['extra_assertion_audit_complete'] for x in d)
quote_count=0
for x in f+e:
 assert h(R/x['output_artifact'])==x['output_artifact_hash']
 q=x.get('exact_output_quote',x.get('assertion_text'))
 if q is None:assert x['omission_scope'];continue
 t=(R/x['output_artifact']).read_text();loc=x['output_locator'];ls=t.splitlines(keepends=True)
 assert t[loc['char_start']:loc['char_end']]==q
 assert ''.join(ls[loc['line_start']-1:loc['line_end']])==q
 quote_count+=1
for x in f:
 if x['answerability']=='not_stated':assert x['outcome']=='safe_abstention' and x['scope_coverage']=='complete' and x['absence_evidence_checked']
 if x['answerability']=='uncertain':assert x['outcome']=='not_assessable' and not x['field_gate_pass']
 for p in x['source_image_artifacts']:assert h(R/p['path'])==p['sha256']
for x in d:
 fs=[z for z in f if (z['fixture_id'],z['arm'])==(x['fixture_id'],x['arm'])]
 ref=json.loads((R/f"review/adjudicated/{x['fixture_id']}.json").read_text())
 assert {z['field_id'] for z in fs}=={z['field_id'] for z in ref['reference_fields']}
 extra=[z['assertion_id'] for z in e if z['critical'] and (z['fixture_id'],z['arm'])==(x['fixture_id'],x['arm'])]
 assert extra==x['critical_extra_assertion_ids']
 expected='insufficient_reference' if not x['reference_gate_eligible'] else 'pass' if all(z['field_gate_pass'] for z in fs if z['critical']) and not extra else 'content_fail'
 assert x['gate_outcome']==expected
for x in ops:
 assert h(R/x['capture_artifact'])==x['capture_sha256']
 c=json.loads((R/x['capture_artifact']).read_text())
 assert c['status'] in ['SUCCESS','COMPLETED']
 if x['execution_lane']=='execution-api-1':
  assert (R/x['terminal_api_capture']).is_file()
  assert x['returned_usage']==c['returned_usage'] and x['job_metadata']==c['job_metadata']
  assert x['actual_config']==c['config']
metrics={}
for arm in ['llama_agentic','llama_agentic_plus']:
 crit=[x for x in f if x['arm']==arm and x['critical']];pos=[x for x in crit if x['answerability'] in ['present','explicit_negative']];neg=[x for x in crit if x['answerability']=='not_stated']
 metrics[arm]={'document_gates':dict(collections.Counter(x['gate_outcome'] for x in d if x['arm']==arm)),'supported_critical_positive':sum(x['outcome']=='supported' for x in pos),'critical_positive_denominator':len(pos),'preserved_critical_absence':sum(x['outcome']=='safe_abstention' for x in neg),'critical_absence_denominator':len(neg),'critical_uncertain':sum(x['answerability']=='uncertain' for x in crit)}
result={'passed':True,'documents_completed':16,'fields_completed':144,'notice_wide_audits_completed':16,'field_and_extra_quotes_verified':quote_count,'critical_extra_assertions':sum(x['critical'] for x in e),'frozen_files_unchanged':len(freeze['files']),'original_v1_artifacts_unchanged':len(b['v1_files']),'original_dashboard_document_field_operation_records_unchanged':True,'execution_lanes':dict(collections.Counter(x['execution_lane'] for x in d)),'metrics':metrics,'source_detail_crop':{'path':str((O/'A08-page2-condition-detail.png').relative_to(R)),'sha256':h(O/'A08-page2-condition-detail.png'),'method':'pdftoppm page2 300dpi crop x150 y1600 width2250 height660 from frozen source-a/A08/input.pdf'},'interpretation':'Reviewer-assessed Markdown evidence preservation on purposive correlated notice sample; not extractor precision. A08 Plus has all frozen critical fields preserved but fails separate critical-extra-assertion gate. Mixed execution lanes and unresolved latest alias preclude settings-equivalence claims.'}
(O/'completion-audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
