"""Materialize manually inspected Firecrawl captures; ranges selected by reviewer, not heuristic scoring."""
from pathlib import Path
import json,hashlib,collections
R=Path('/private/tmp/docketclock-expanded-benchmark-2026-10-05');O=R/'review/results-v1';arm='firecrawl_local_parse';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(n):return [json.loads(l) for l in (O/n).read_text().splitlines()]
def write(n,v):(O/n).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in v))
fields=read('field-scores.jsonl');docs=read('document-scores.jsonl');ops=read('operation-records.jsonl');extras=[x for x in read('extra-assertions.jsonl') if x['assertion_id']!='A03-firecrawl-subpart-5']
ranges={
'A01':{'agency':(5,5),'rule_identity':(8,8),'selected_lifecycle':(66,78),'hearing_selection':(22,26),'submit_date':(8,8),'filing_stamp':(98,102),'prior_proposal_filed':(66,68),'selected_effective':(66,84),'generic_comment_duration':(28,28),'conditional_oral_request':(28,28)},
'A02':{'agency':(5,5),'rule_identity':(8,8),'selected_lifecycle':(40,50),'hearing_selection':(14,20),'hearing_clock':(16,18),'submit_date':(8,8),'filing_stamp':(74,78),'proposed_effective':(52,56),'generic_comment_duration':(22,22),'oral_request_condition':(22,22)},
'A03':{'agency':(5,5),'rule_identity':(8,14),'selected_lifecycle':(62,74),'hearing_selection':(16,20),'submit_date':(8,8),'filing_stamp':(92,96),'prior_proposal_filed':(62,64),'selected_effective':(62,80),'generic_comment_duration':(22,22),'conditional_oral_request':(22,22)},
'A04':{'agency':(12,12),'notice_id':None,'lifecycle':(12,12),'withdrawal_target_scope':(12,12),'target_filing_date':(12,12),'current_filing_clock':None,'new_comment_close':None},
'A07':{'agency':(3,3),'lifecycle':(1,5),'form_rule_links':(9,10),'current_comment_open':(11,11),'current_comment_close':(11,25),'comment_scope':(25,25),'prior_modification_date':(3,3),'original_notice_date':(3,37),'new_hearing_clock':(1,39)},
'A08':{'agency':(10,11),'lifecycle':(1,11),'rule_identity':(1,4),'comment_duration_anchor':(30,36),'receipt_condition':(42,45),'planned_submission':(74,77),'actual_submission_date':(74,77),'prior_effective_date':(15,17),'proposed_extension':(16,20),'printed_notice_date':(1,6)},
'A09':{'agency':(5,5),'notice_id':None,'subject':(18,18),'proposed_action_rule':(13,13),'hearing_status':(7,7),'comment_duration_anchor':(46,47),'issue_publication_date':(1,3),'compliance_trigger':(113,114)},
'A10':{'agency':(126,128),'notice_id':(109,111),'subject':(122,122),'proposed_action_scope':(115,118),'hearing_status':(109,111),'comment_duration_anchor':(149,150),'petition_filing_date':(126,128),'authority':(120,120),'issue_publication_date':(1,3)}
}
ranges.update({
'B05':{'agency':(119,132),'citation':(123,132),'source_id':(292,299),'comment_window':(203,216),'hearing_request':(210,216),'filing':(292,299),'earliest_adoption':(292,299),'effective':(289,299)},
'B06':{'agency':(55,63),'citation':(59,63),'source_id':(229,241),'comment_duration':(119,122),'publication':None,'filing':(229,241),'earliest_adoption':(229,241),'close_clock':(119,122)},
'B07':{'agency':(69,72),'citation':(69,72),'source_id':(170,177),'comment_duration':(137,140),'publication':None,'filing':(170,177),'earliest_adoption':(170,177),'effective':(167,177)},
'B08':{f:(1,5) for f in ['agency','citation','tracking','event','termination_date','scope_reason','replacement_hearing','comment_close']},
'B09':{f:(1,5) for f in ['agency','citation','tracking','event','termination_date','scope_reason','replacement_hearing','comment_close']},
'B10':{f:(1,5) for f in ['agency','citation','event','effective','publication','comment_close','hearing','filing']}
})

ranges.update({
'A05':{'agency':(4,8),'notice_id':(2,3),'lifecycle':(4,11),'target_scope':(8,11),'target_filing_date':(8,11),'prior_comment_open':(8,11),'prior_comment_close':(8,11),'current_filing_clock':(2,7),'certification_date':(22,22),'new_comment_close':(8,22)},
'A06':{'agency':(1,4),'lifecycle':(6,14),'rule_identity':(12,12),'notice_date':(6,12),'prior_comment_close':(19,19),'current_comment_close':(22,28),'receipt_condition':(24,24),'comment_scope':(28,28),'new_hearing_clock':(1,31)},
'B01':{'agency':(9,12),'citation':(9,12),'event':(25,30),'effective':(75,77),'publication':(71,73),'signature_date':(66,69),'comment_close':(38,45),'hearing':(38,45)},
'B02':{'agency':(9,13),'citation':(9,13),'event':(49,49),'effective':(59,59),'publication':(55,57),'public_review_ambiguous':(33,33),'comment_close':(33,33),'review_clock':(33,33)}
})

ranges.update({
'B03':{'agency':(1,4),'citation':(3,4),'event':(3,4),'proposed_effective':(8,8),'comment_close':(24,24),'hearing':(10,16),'objection_condition':(26,33),'close_clock':(21,33),'timezone':(10,16)},
'B04':{'agency':(16,16),'citation':(19,25),'event_selected':(19,25),'proposed_effective':(26,26),'hearing':(27,31),'comment_close':(39,40),'filing':None,'close_clock':(38,40),'timezone':(27,31)}
})

for k,rs in ranges.items():
 p=R/('firecrawl/rate-limit-recovery' if k in ['A05','A06','B01','B02','B03','B04'] else 'firecrawl/initial-remaining' if k in ['B05','B06','B07','B08','B09','B10'] else 'firecrawl/recovery-1')/k/'markdown.md';t=p.read_text();ls=t.splitlines(keepends=True);oc=p.parent/'outcome.json';c=json.loads(oc.read_text());raw=json.loads((p.parent/'parse-response.json').read_text());assert raw['structuredContent']['data']['markdown']==t;assert c['exact_markdown_capture']['sha256']==sha(p)
 d=next(d for d in docs if d['fixture_id']==k and d['arm']==arm)
 assert set(rs)=={r['field_id'] for r in fields if r['fixture_id']==k and r['arm']==arm}
 for r in fields:
  if r['fixture_id']!=k or r['arm']!=arm:continue
  fid=r['field_id'];span=rs[fid];loc=None;q=None
  if span:
   a,b=span;start=sum(map(len,ls[:a-1]));end=sum(map(len,ls[:b]));loc={'line_start':a,'line_end':b,'char_start':start,'char_end':end};q=t[start:end]
  outcome='supported';reason='value_and_decisive_role_preserved';note='Full returned target scope inspected against frozen source. Quote preserves required value and role; no inferred dates or timezone.';omission=None;scope='complete'
  if k in ['A01','A02','A03'] and fid=='hearing_selection':outcome='partial_ambiguous';reason='selected_mark_association_lost';note='Both oral-proceeding option labels survive but their checkbox marks do not; literal labels alone do not preserve selected state.';scope='partial'
  elif k=='A02' and fid=='proposed_effective':outcome='missing';reason='selected_effective_option_omitted';note='The selected proposed 30-days-after-filing choice is omitted; only Other remains under proposed effective date.';omission='Entire returned markdown inspected; proposed effective section lines52–56 lacks 30-day choice.';scope='partial'
  elif k=='A03' and fid=='rule_identity':note='Title preserves frozen Subpart1 to S. Reinspection shows source explanatory body says5, matching output; this is not an added false assertion. See score-correction-history.json.'
  elif k=='A04' and fid in ['notice_id','current_filing_clock','new_comment_close']:outcome='missing';reason='absence_scope_incomplete' if fid=='new_comment_close' else 'filing_stamp_omitted';note='Bottom-right official filing stamp omitted. Current WSR and filing clock cannot be substituted with withdrawn target ID or letter date; full letter-plus-stamp absence scope incomplete.';omission='Entire output lines1–14 inspected; official stamp WSR25-08-088 / April2,2025 08:56 absent.';scope='partial'
  elif k=='A09' and fid=='notice_id':outcome='missing';reason='notice_identifier_omitted';note='Target notice ID SGC-39-26-00023-P is absent; neighboring SGC-39-26-00024-P remains attached to separate Coupling notice and cannot be borrowed.';omission='Entire output lines1–177 inspected, especially target heading lines5–13; target identifier absent.';scope='partial'
  elif k in ['B06','B07','B10'] and fid=='publication':outcome='missing';reason='publication_footer_omitted';note='Returned text omits source publication footer. No date from filing, earliest adoption, or effective field may substitute.';omission='Entire returned markdown inspected; publication footer and its frozen date are absent.';scope='partial'
  elif k=='B10' and fid in ['comment_close','hearing','filing']:outcome='missing';reason='absence_scope_incomplete';note='Requested value is absent, but frozen absence scope is the entire retained notice header and the publication footer is omitted. Complete-scope safe absence is not certified.';omission='Entire output lines1–5 inspected; footer omitted from the retained notice scope.';scope='partial'
  elif k=='B04' and fid in ['filing','close_clock','timezone']:outcome='missing';reason='filing_stamp_omitted' if fid=='filing' else 'absence_scope_incomplete';note='The June8,2026 OAH filing stamp is absent. Frozen negative questions require complete two-page Form300 scope, so absence cannot pass with this source region omitted.';omission='Entire returned markdown lines1–42 inspected; OAH filing stamp omitted. May20 formal proposal date is a different role.';scope='partial'
  elif r['answerability']=='uncertain':outcome='not_assessable';reason='reference_uncertainty';note='Both conflicting original-notice years retained. Frozen source cannot resolve them; excluded from determinate recovery.'
  elif r['answerability']=='not_stated':outcome='safe_abstention';reason='complete_scope_preserves_absence';note='Complete relevant target scope reviewed; requested value absent without fabrication. Quoted section anchors evidence; full notice checked.';omission='Requested value absent from complete retained scope: '+d['notice_scope']
  r.update(evaluation_status='complete',operation_status='completed_nonempty',output_artifact=str(p.relative_to(R)),output_artifact_hash=sha(p),outcome=outcome,reason_code=reason,scope_coverage=scope,output_locator=loc,exact_output_quote=q,omission_scope=omission,decisive_relation_preserved=outcome in ['supported','safe_abstention'],field_gate_pass=outcome in ['supported','safe_abstention'],adjudication_note=note)
 extraids=[]

 critical=[r for r in fields if r['fixture_id']==k and r['arm']==arm and r['critical']];groups={g:all(x['field_gate_pass'] for x in critical if x['semantic_group_id']==g) for g in {x['semantic_group_id'] for x in critical}};gate='insufficient_reference' if not d['reference_gate_eligible'] else 'pass' if all(x['field_gate_pass'] for x in critical) and not extraids else 'content_fail'
 d.update(evaluation_status='complete',operation_status='completed_nonempty',gate_outcome=gate,scope_coverage='partial' if any(x['scope_coverage']=='partial' for x in critical) else 'complete',output_artifact=str(p.relative_to(R)),output_artifact_hash=sha(p),critical_field_counts=dict(collections.Counter(x['outcome'] for x in critical)),critical_group_counts={'total':len(groups),'pass':sum(groups.values()),'nonpass':len(groups)-sum(groups.values())},extra_assertion_audit_complete=True,critical_extra_assertion_ids=extraids,failure_categories=sorted({x['reason_code'] for x in critical if not x['field_gate_pass']}),reviewer_note='Complete returned target scope and neighboring boundaries inspected for critical extra assertions. Unmarked alternative form labels alone are not positive false assertions. Raw evidence preservation reviewed; no downstream normalizer evaluated.')
 op=next(x for x in ops if x['fixture_id']==k and x['arm']==arm);op.update(evaluation_status='complete',operation_status='completed_nonempty',output_artifact=str(p.relative_to(R)),output_artifact_hash=sha(p),reason_code='parse_text_available_after_transport_amendment',operation_evidence={'final_outcome_path':str(oc.relative_to(R)),'final_outcome_sha256':sha(oc),'execution_amendment':'execution-amendment-1.json','initial_transport_attempt_excluded_from_vendor_failure':k in ['A01','A02','A03','A04'],'overall_setup_and_parse_ms':c['elapsed_ms'],'completion_sequence':c['completion_sequence']},wrapper_wall_ms=c['parse_wall_ms'],returned_usage=c['reported'])
 op['operation_evidence']['timing_scope']='Recorded parse-wrapper elapsed time; paced runs include local pacing/queue wait because start precedes wait. Excludes separate upload/setup; not provider service latency.'
 if k in ['A05','A06','B01','B02','B03','B04']:
  initial=R/'firecrawl/recovery-1'/k/'outcome.json';ic=json.loads(initial.read_text());response=initial.parent/('parse-response.json' if ic['failure_stage']=='parse' else 'phase-one-response.redacted.json');assert not ic['success']
  op['reason_code']='parse_text_available_after_explicit_rate_rejection';op['operation_evidence'].update({'execution_note':'execution-note-2.json','rate_limit_recovered':True,'first_provider_attempt_path':str(initial.relative_to(R)),'first_provider_attempt_sha256':sha(initial),'first_provider_attempt_status':'provider_error','first_provider_attempt_reason':'provider_rate_limit','first_response_path':str(response.relative_to(R)),'first_response_sha256':sha(response),'first_failure_stage':ic['failure_stage'],'first_parse_wall_ms':ic.get('parse_wall_ms'),'first_overall_wall_ms':ic.get('elapsed_ms'),'first_usage':ic.get('reported')})
 else:op['operation_evidence']['rate_limit_recovered']=False

for n,v in [('field-scores.jsonl',fields),('document-scores.jsonl',docs),('operation-records.jsonl',ops),('extra-assertions.jsonl',extras)]:write(n,v)
print('Reviewed',list(ranges))
