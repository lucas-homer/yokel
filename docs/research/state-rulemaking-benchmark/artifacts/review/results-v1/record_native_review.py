"""Materialize agent-reviewed native judgments with exact retained-text evidence.
Ranges and exceptions below were selected after reading complete native captures.
This is evidence bookkeeping, not an automatic field extractor/scorer.
"""
from pathlib import Path
import json,hashlib,collections
R=Path('/private/tmp/docketclock-expanded-benchmark-2026-10-05');O=R/'review/results-v1'
def read(name):return [json.loads(l) for l in (O/name).read_text().splitlines()]
def write(name,rows):(O/name).write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
fields=read('field-scores.jsonl');docs=read('document-scores.jsonl');ops=read('operation-records.jsonl');freeze=json.loads((R/'corpus-freeze.json').read_text());units={u['fixture_id']:u for u in freeze['units']}
ranges={
'A04':{'agency':(19,20),'notice_id':None,'lifecycle':(19,20),'withdrawal_target_scope':(19,20),'target_filing_date':(19,20),'current_filing_clock':None,'new_comment_close':None},
'A05':{'agency':(1,4),'notice_id':(1,5),'lifecycle':(1,9),'target_scope':(6,9),'target_filing_date':(6,9),'prior_comment_open':(8,9),'prior_comment_close':(8,9),'current_filing_clock':(1,5),'certification_date':(21,21),'new_comment_close':(10,15)},
'A06':{'agency':(1,2),'lifecycle':(7,12),'rule_identity':(10,12),'notice_date':(7,12),'prior_comment_close':(28,32),'current_comment_close':(37,41),'receipt_condition':(37,41),'comment_scope':(48,50),'new_hearing_clock':(37,53)},
'A07':{'agency':(3,8),'lifecycle':(1,8),'form_rule_links':(14,17),'current_comment_open':(18,21),'current_comment_close':(18,33),'comment_scope':(28,33),'prior_modification_date':(8,8),'original_notice_date':(3,58),'new_hearing_clock':(18,33)},
'A08':{'agency':(8,10),'lifecycle':(3,10),'rule_identity':(3,6),'comment_duration_anchor':(27,33),'receipt_condition':(40,44),'planned_submission':(61,64),'actual_submission_date':(61,64),'prior_effective_date':(14,16),'proposed_extension':(15,20),'printed_notice_date':(3,7)},
'A09':{'agency':(1,6),'notice_id':(3,9),'subject':(9,14),'proposed_action_rule':(3,9),'hearing_status':(3,6),'comment_duration_anchor':(37,39),'issue_publication_date':(144,145),'compliance_trigger':(94,96)},
'A10':{'agency':(90,107),'notice_id':(90,99),'subject':(100,102),'proposed_action_scope':(90,99),'hearing_status':(90,93),'comment_duration_anchor':(125,129),'petition_filing_date':(103,107),'authority':(100,100),'issue_publication_date':(136,137)},
'B01':{'agency':(8,11),'citation':(8,11),'event':(48,65),'effective':(49,51),'publication':(49,51),'signature_date':(49,51),'comment_close':(24,33),'hearing':(24,33)},
'B02':{'agency':(8,11),'citation':(8,11),'event':(53,61),'effective':(54,56),'publication':(54,56),'public_review_ambiguous':(34,38),'comment_close':(34,38),'review_clock':(34,38)},
'B03':{'agency':(2,5),'citation':(4,5),'event':(4,5),'proposed_effective':(9,9),'comment_close':(19,22),'hearing':(11,14),'objection_condition':(24,31),'close_clock':(19,31),'timezone':(11,14)},
'B04':{'agency':(13,14),'citation':(17,23),'event_selected':(15,23),'proposed_effective':(24,24),'hearing':(25,29),'comment_close':(50,58),'filing':(31,33),'close_clock':(42,58),'timezone':(25,29)},
'B05':{'agency':(111,115),'citation':(102,115),'source_id':(273,283),'comment_window':(183,198),'hearing_request':(190,194),'filing':(273,283),'earliest_adoption':(273,283),'effective':(273,283)},
'B06':{'agency':(53,61),'citation':(53,61),'source_id':(202,212),'comment_duration':(111,115),'publication':(108,108),'filing':(202,212),'earliest_adoption':(202,212),'close_clock':(111,115)},
'B07':{'agency':(65,68),'citation':(65,68),'source_id':(166,176),'comment_duration':(140,145),'publication':(228,228),'filing':(166,176),'earliest_adoption':(166,176),'effective':(166,176)},
'B08':{'agency':(1,14),'citation':(1,14),'tracking':(1,14),'event':(1,14),'termination_date':(1,14),'scope_reason':(1,14),'replacement_hearing':(1,14),'comment_close':(1,14)},
'B09':{'agency':(1,14),'citation':(1,14),'tracking':(1,14),'event':(1,14),'termination_date':(1,14),'scope_reason':(1,14),'replacement_hearing':(1,14),'comment_close':(1,14)},
'B10':{'agency':(1,12),'citation':(1,12),'event':(1,12),'effective':(1,12),'publication':(12,12),'comment_close':(1,12),'hearing':(1,12),'filing':(1,12)}
}
notes={
'A04':'Letter body survives but bottom-right filing stamp is wholly absent. Current WSR/date/time cannot be borrowed from target ID/body letter date. Full-scope absence cannot pass with that critical region missing.',
'B03':'Fiscal checkbox states are lost, but no positive selected-state assertion is added. All relevant participation/lifecycle/date evidence and notice scope survive; fiscal status is outside the predeclared critical questions.',
'B04':'Standalone X is displaced above Proposed Action heading rather than attached to AMENDMENT. Narrative says proposed amendment but cannot repair the marked-option association required by the frozen field. Other participation date roles survive.',
'A07':'Both conflicting original-notice years survive; original_notice_date is not_assessable from frozen source uncertainty, not a parse error. Unit is reference-insufficient for unqualified strict gate.',
'B08':'Labels are followed by ordered values; identities and termination-date value remain uniquely recoverable in this short complete notice. Hearing unchanged qualifier retained.',
'B09':'Labels are followed by ordered values; identities and termination-date value remain uniquely recoverable. Rescheduling promise is not a dated replacement hearing.',
'B10':'Label/value order, explicit effective-date role in rule title, and publication footer preserve the date distinction. No comment/hearing/filing date is asserted.'}
for k,u in units.items():
 p=R/u['directory']/'native.txt';t=p.read_text();lines=t.splitlines(keepends=True);status='completed_nonempty' if t.strip() else 'completed_empty';scope='none' if not t.strip() else 'partial' if k in ['A04','B04'] else 'complete'
 for row in fields:
  if row['arm']!='native' or row['fixture_id']!=k:continue
  row.update(evaluation_status='complete',operation_status=status,output_artifact=str(p.relative_to(R)),output_artifact_hash=sha(p),scope_coverage=scope,reviewer_id='independent-agent-reviewer')
  fid=row['field_id'];r=ranges.get(k,{}).get(fid)
  if r:
   lo,hi=r;assert 1<=lo<=hi<=len(lines),(k,fid,r,len(lines));start=sum(map(len,lines[:lo-1]));end=sum(map(len,lines[:hi]));quote=t[start:end];row.update(output_locator={'line_start':lo,'line_end':hi,'char_start':start,'char_end':end},exact_output_quote=quote)
  if not t.strip():outcome='not_assessable';reason='native_no_embedded_text';note='Retained native extraction is empty for an image-only form; no OCR was run. No output evidence exists for any field.';row['omission_scope']='Entire retained native.txt, zero characters; all input-page evidence absent.'
  elif k=='A04' and fid in ['notice_id','current_filing_clock','new_comment_close']:
   outcome='missing';reason='filing_stamp_omitted' if fid!='new_comment_close' else 'absence_scope_incomplete';note='Native output omits the entire filing stamp. '+('The required current identifier/date/time evidence is absent.' if fid!='new_comment_close' else 'The frozen absence scope includes the full letter and stamp; cannot certify complete scope from this output.');row['omission_scope']='Entire native output lines1–25 inspected; bottom-right official stamp (current WSR25-08-088; April2,2025 08:56) absent.'
  elif k=='B04' and fid=='event_selected':outcome='partial_ambiguous';reason='selected_mark_association_lost';note='X is detached above the Proposed Action heading; amendment label/citation and explanatory narrative survive, but selected-row relationship is ambiguous.'
  elif row['answerability']=='uncertain':outcome='not_assessable';reason='reference_uncertainty';note='Both 2025 and2026 original-notice dates survive; frozen reference does not resolve them. This is excluded from determinate recovery, not a content failure.'
  elif row['answerability']=='not_stated':outcome='safe_abstention';reason='complete_scope_preserves_absence';note='Complete relevant retained notice scope reviewed; no requested value supplied or fabricated. Quote anchors the relevant preserved section; entire target scope checked, including continuation/headers.';row['omission_scope']='Requested value not stated in complete retained target scope: '+next(d['notice_scope'] for d in docs if d['fixture_id']==k and d['arm']=='native')
  else:outcome='supported';reason='value_and_decisive_role_preserved';note='Reviewer confirmed quoted evidence preserves the frozen value and its decisive role/condition within target scope; formatting/line-wrap differences do not change meaning.'
  row.update(outcome=outcome,reason_code=reason,adjudication_note=note,decisive_relation_preserved=outcome in ['supported','safe_abstention'],field_gate_pass=outcome in ['supported','safe_abstention'])
  if k=='B04' and fid!='event_selected':row['scope_coverage']='complete'
  if k=='A04' and fid not in ['notice_id','current_filing_clock','new_comment_close']:row['scope_coverage']='complete'
 fr=[r for r in fields if r['fixture_id']==k and r['arm']=='native'];critical=[r for r in fr if r['critical']];cnt=dict(collections.Counter(r['outcome'] for r in critical));groups={g:all(x['field_gate_pass'] for x in critical if x['semantic_group_id']==g) for g in {x['semantic_group_id'] for x in critical}}
 gate='insufficient_reference' if not u['reference_gate_eligible'] else 'operational_unusable' if status!='completed_nonempty' else 'pass' if all(x['field_gate_pass'] for x in critical) else 'content_fail'
 d=next(d for d in docs if d['fixture_id']==k and d['arm']=='native');d.update(evaluation_status='complete',operation_status=status,gate_outcome=gate,scope_coverage=scope,output_artifact=str(p.relative_to(R)),output_artifact_hash=sha(p),critical_field_counts=cnt,critical_group_counts={'total':len(groups),'pass':sum(groups.values()),'nonpass':len(groups)-sum(groups.values())},extra_assertion_audit_complete=True,critical_extra_assertion_ids=[],failure_categories=sorted({x['reason_code'] for x in critical if not x['field_gate_pass']}),reviewer_note=notes.get(k,'Complete retained native target output reviewed against frozen source evidence; no new critical incorrect assertion found.'))
 o=next(o for o in ops if o['fixture_id']==k and o['arm']=='native');o.update(evaluation_status='complete',operation_status=status,output_artifact=str(p.relative_to(R)),output_artifact_hash=sha(p),reason_code='native_no_embedded_text' if status=='completed_empty' else 'native_text_available',operation_evidence={'frozen_native_artifact':str(p.relative_to(R)),'bytes':p.stat().st_size,'method':'retained embedded text extraction; no OCR'},wrapper_wall_ms=None,returned_usage=None)
write('field-scores.jsonl',fields);write('document-scores.jsonl',docs);write('operation-records.jsonl',ops)
progress={'scheduled_documents':80,'scheduled_fields':696,'completed_documents':sum(d['evaluation_status']=='complete' for d in docs),'completed_fields':sum(r['evaluation_status']=='complete' for r in fields),'completed_by_arm':dict(collections.Counter(d['arm'] for d in docs if d['evaluation_status']=='complete')),'native_document_gates':dict(collections.Counter(d['gate_outcome'] for d in docs if d['arm']=='native')),'frozen_manifest_sha256':sha(R/'corpus-freeze.json'),'note':'Native completed. Cloud rows pending final capture and review.'}
(O/'progress.json').write_text(json.dumps(progress,indent=2)+'\n');print(json.dumps(progress,indent=2))
