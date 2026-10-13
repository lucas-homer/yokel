from pathlib import Path
import json,hashlib
R=Path('/private/tmp/docketclock-expanded-benchmark-2026-10-05');O=R/'review/results-v1';f=json.loads((R/'corpus-freeze.json').read_text());arms=['native','firecrawl_local_parse','llama_agentic','llama_agentic_plus'];fields=[];docs=[];ops=[]
for u in f['units']:
 ref=json.loads((R/u['reference_path']).read_text())
 for arm in arms:
  shared={'fixture_id':u['fixture_id'],'arm':arm,'evaluation_status':'pending','input_sha256':u['input_sha256'],'reference_version_hash':u['reference_sha256'],'operation_status':None,'output_artifact':None,'output_artifact_hash':None}
  docs.append(dict(shared,gate_outcome=None,reference_gate_eligible=u['reference_gate_eligible'],scope_coverage=None,notice_scope=ref['notice_scope_boundaries'],critical_field_counts={},critical_group_counts={},extra_assertion_audit_complete=False,critical_extra_assertion_ids=[],failure_categories=[],reviewer_note=None))
  ops.append(dict(shared,reason_code=None,operation_evidence=None,wrapper_wall_ms=None,returned_usage=None))
  for rf in ref['reference_fields']:
   fields.append(dict(shared,field_id=rf['field_id'],semantic_group_id=rf['semantic_group_id'],critical=rf['critical'],answerability=rf['answerability'],outcome=None,reason_code=None,scope_coverage=None,source_locator={'input_page':rf['input_page'],'original_page':rf['original_page'],'region':rf['region']},output_locator=None,exact_output_quote=None,omission_scope=None,decisive_relation_preserved=None,field_gate_pass=None,reviewer_id='independent-agent-reviewer',adjudication_note=None))
for name,rows in [('field-scores.jsonl',fields),('document-scores.jsonl',docs),('operation-records.jsonl',ops)]:
 p=O/name;assert not p.exists();p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
(O/'extra-assertions.jsonl').write_text('');(O/'progress.json').write_text(json.dumps({'scheduled_documents':len(docs),'scheduled_fields':len(fields),'completed_documents':0,'completed_fields':0,'frozen_manifest_sha256':hashlib.sha256((R/'corpus-freeze.json').read_bytes()).hexdigest(),'note':'Scaffolding only; no performance results yet.'},indent=2)+'\n')
print('Initialized',len(docs),'document-arm and',len(fields),'field-arm rows.')
