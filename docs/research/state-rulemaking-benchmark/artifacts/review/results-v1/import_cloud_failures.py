"""Record final captured operational failures; never assign content success by text matching."""
from pathlib import Path
import json,hashlib,collections
R=Path('/private/tmp/docketclock-expanded-benchmark-2026-10-05');O=R/'review/results-v1';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(n):return [json.loads(l) for l in (O/n).read_text().splitlines()]
def write(n,v):(O/n).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in v))
fields=read('field-scores.jsonl');docs=read('document-scores.jsonl');ops=read('operation-records.jsonl')
failures={'timeout_backend_unknown','failed_before_job','provider_error','completed_empty','malformed_output','not_attempted_provider_stop'}
recorded=[]
for p in sorted((R/'llama/runs').glob('*/*/capture.json')):
 c=json.loads(p.read_text());status=c['outcome'];k=c['fixture_id'];arm={'agentic':'llama_agentic','agentic_plus':'llama_agentic_plus'}[c['tier']]
 if status not in failures:continue
 d=next(d for d in docs if d['fixture_id']==k and d['arm']==arm)
 if d['evaluation_status']=='complete':continue
 assert c['input_sha256']==d['input_sha256']
 # Capture status and full raw response are final operation evidence, not parse content.
 rel=str(p.relative_to(R));explanation='No usable parse output was returned. '+('MCP timeout leaves backend completion and billing unknown; no retry is inferred.' if status=='timeout_backend_unknown' else 'Preserve the captured operation classification; do not score as content error or safe abstention.')
 for r in fields:
  if r['fixture_id']!=k or r['arm']!=arm:continue
  r.update(evaluation_status='complete',operation_status=status,outcome='not_assessable',reason_code=status,scope_coverage='not_assessable',output_artifact=rel,output_artifact_hash=sha(p),output_locator=None,exact_output_quote=None,omission_scope='No parse-content artifact exists for this operation; final capture: '+rel,decisive_relation_preserved=False,field_gate_pass=False,adjudication_note=explanation)
 critical=[r for r in fields if r['fixture_id']==k and r['arm']==arm and r['critical']];groups={r['semantic_group_id'] for r in critical}
 d.update(evaluation_status='complete',operation_status=status,gate_outcome='insufficient_reference' if not d['reference_gate_eligible'] else 'not_attempted_provider_stop' if status=='not_attempted_provider_stop' else 'operational_unusable',scope_coverage='not_assessable',output_artifact=rel,output_artifact_hash=sha(p),critical_field_counts={'not_assessable':len(critical)},critical_group_counts={'total':len(groups),'pass':0,'nonpass':len(groups)},extra_assertion_audit_complete=False,critical_extra_assertion_ids=[],failure_categories=[status],reviewer_note=explanation+' Extra-assertion audit not applicable: no content result.')
 op=next(r for r in ops if r['fixture_id']==k and r['arm']==arm);op.update(evaluation_status='complete',operation_status=status,output_artifact=rel,output_artifact_hash=sha(p),reason_code=status,operation_evidence={'capture_path':rel,'capture_sha256':sha(p),'response':c.get('response'),'completion_order':c.get('completion_order'),'requested_tier':c['tier'],'resolved_version':c.get('reported_version'),'job_id':c.get('reported_job_id')},wrapper_wall_ms=c.get('elapsed_ms'),returned_usage=c.get('reported_usage'))
 recorded.append((k,arm,status))
# Final lane ledger explicitly distinguishes unattempted units after provider stop.
ledger=R/'llama/call-ledger.json'
for index,c in enumerate(json.loads(ledger.read_text())):
 if c['outcome']!='not_attempted_provider_stopped':continue
 k=c['fixture_id'];arm={'agentic':'llama_agentic','agentic_plus':'llama_agentic_plus'}[c['tier']];status='not_attempted_provider_stop';d=next(d for d in docs if d['fixture_id']==k and d['arm']==arm)
 if d['evaluation_status']=='complete':continue
 assert c['input_sha256']==d['input_sha256']
 rel=str(ledger.relative_to(R));note='Final provider ledger confirms no call after shared timeout stop threshold; unavailable content is not a parser content failure.'
 for row in fields:
  if row['fixture_id']!=k or row['arm']!=arm:continue
  row.update(evaluation_status='complete',operation_status=status,outcome='not_assessable',reason_code=status,scope_coverage='not_assessable',output_artifact=rel,output_artifact_hash=sha(ledger),output_locator=None,exact_output_quote=None,omission_scope='No parse call or output; final ledger entry '+str(index),decisive_relation_preserved=False,field_gate_pass=False,adjudication_note=note)
 critical=[row for row in fields if row['fixture_id']==k and row['arm']==arm and row['critical']];groups={row['semantic_group_id'] for row in critical}
 d.update(evaluation_status='complete',operation_status=status,gate_outcome='insufficient_reference' if not d['reference_gate_eligible'] else status,scope_coverage='not_assessable',output_artifact=rel,output_artifact_hash=sha(ledger),critical_field_counts={'not_assessable':len(critical)},critical_group_counts={'total':len(groups),'pass':0,'nonpass':len(groups)},extra_assertion_audit_complete=False,critical_extra_assertion_ids=[],failure_categories=[status],reviewer_note=note)
 op=next(row for row in ops if row['fixture_id']==k and row['arm']==arm);op.update(evaluation_status='complete',operation_status=status,output_artifact=rel,output_artifact_hash=sha(ledger),reason_code=status,operation_evidence={'ledger_path':rel,'ledger_sha256':sha(ledger),'ledger_index':index,'entry':c,'operations_manifest':'llama/operations.json'},wrapper_wall_ms=None,returned_usage=None)
 recorded.append((k,arm,status))
for name,rows in [('field-scores.jsonl',fields),('document-scores.jsonl',docs),('operation-records.jsonl',ops)]:write(name,rows)
progress={'scheduled_documents':80,'scheduled_fields':696,'completed_documents':sum(d['evaluation_status']=='complete' for d in docs),'completed_fields':sum(r['evaluation_status']=='complete' for r in fields),'completed_by_arm':dict(collections.Counter(d['arm'] for d in docs if d['evaluation_status']=='complete')),'frozen_manifest_sha256':sha(R/'corpus-freeze.json'),'note':'Native completed; final cloud failures recorded; cloud content captures await manual review.'};(O/'progress.json').write_text(json.dumps(progress,indent=2)+'\n');print(json.dumps({'recorded':recorded,'progress':progress},indent=2))
