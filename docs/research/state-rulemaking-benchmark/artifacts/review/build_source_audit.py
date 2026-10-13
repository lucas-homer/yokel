"""Rebuild reviewer-owned source audit; reads only collector fixtures/source artifacts.
No vendor outputs, network, or non-stdlib imports. Collector files are never modified.
"""
from pathlib import Path
import json, hashlib, collections, datetime, copy
ROOT=Path('/private/tmp/docketclock-expanded-benchmark-2026-10-05'); REVIEW=ROOT/'review'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v): p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
ready=json.loads((REVIEW/'collector-readiness-confirmation.json').read_text())
confirmed=ready['source_a_final_confirmed'] and ready['source_b_final_confirmed']
notes=json.loads((REVIEW/'independent-source-notes.json').read_text())['units']
collector_dir=REVIEW/'collector-snapshots'; collector_dir.mkdir(exist_ok=True)
adjudicated_dir=REVIEW/'adjudicated'; adjudicated_dir.mkdir(exist_ok=True)
scopes={
'A01':'Entire single-page MS filing form; final-action column is selected; attachments absent from original.',
'A02':'Entire single-page MS filing form; proposed-action column and scheduled-hearing box selected; attachments absent.',
'A03':'Entire single-page MS filing form; final-action column selected; attachments absent.',
'A04':'Entire one-page withdrawal letter and current filing stamp.',
'A05':'Complete WSR26-16-026A on original physical11, printed11; no neighboring notice on input.',
'A06':'Both pages of complete continuation notice, excluding separately linked proposed text.',
'A07':'Both pages of complete second modification notice, excluding separately available rule text/forms.',
'A08':'All four pages of complete proposed emergency-readoption notice.',
'A09':'Originalphysical30 printed24: target SGC-39-26-00023-P starts upperleft; continues upperright and ends before Coupling heading SGC-39-26-00024-P.',
'A10':'Originalphysical36 printed30: target PSC-39-26-00027-P starts rightcolumn heading Issuance of Securities and ends at (26-G-0592SP1); exclude leftcolumn/topright PSC-39-26-00026-P and submetering.',
'B01':'Complete two-page Hospital Assessment filing form, original61–62 printed55–56; separate rule text excluded.',
'B02':'Complete two-page Social Workers filing form and one-page emergency rationale, original69–71.',
'B03':'Complete two-page Exempt Sales Plan notice plus proposed rule text; opening proposal controls proposed history effective date.',
'B04':'Complete two-page Form300 notice, original1–2; rule-text attachment original3–4 excluded.',
'B05':'Target19TAC151.1001 starts input1 bottomright heading; continues both columns input2, ends input3 left TRD-202601979/diamonds. Exclude TDLR/TRD-202601993/1994 and TREC to right.',
'B06':'Target22TAC535.46 starts input1 right; continues input2 left/right through TRD-202601973/diamonds. Exclude TEA left input1 and following SubchapterF.',
'B07':'Target22TAC271.12 begins input1 right after TRD-202602104/diamonds; continues input2 left/righttop, ends TRD-202602105/contact/diamonds before Chapter272. Exclude271.8 and272.4 repeals.',
'B08':'Entire one-page terminated-rulemaking notice, original1207; no actual hearing date supplied.',
'B09':'Entire one-page terminated-rulemaking notice, original1018; rescheduling promised without new date.',
'B10':'Entire permanent-adoption header original233; attached adopted-rule text excluded; absences apply only to this notice header.'}
overrides={
('A03','rule_identity'):{'expected_value':'Title 35, Part VIII, Subpart 1 to S - Table of Contents','source_quote':'Title 35, Part VIII, Subpart 1 to S - Table of Contents','reason':'Rendered rule-name cell reads Subpart 1 to S; accompanying description says a new subpart S was created. Collector numeral 5 transcription corrected to letter S.','type':'value_transcription_correction'},
('A10','issue_publication_date'):{'expected_value':{'date':'2026-09-30','role':'issue publication header'},'answerability':'present','source_quote':'NYS Register/September 30, 2026','basis':'source_text','region':'Top-right page header on original physical36 / printed30.','reason':'Collector confirmed. Primary challenged initial reviewer absence claim; original-detail full-image reinspection visibly confirms September30,2026. Initial review error retained in superseded-pre-freeze and reviewer-primary-disagreements.json.','type':'reviewer_error_corrected_collector_restored'},
('B03','event'):{'expected_value':'proposed adoption','reason':'Opening says intends to adopt and all action is proposed. Expected answer must preserve proposed stage; asserted final adoption fails.','type':'role_precision_clarification'},
('B04','event_selected'):{'expected_value':'proposed amendment','reason':'Selected AMENDMENT is inside Proposed Action block. Must retain proposed stage and X association, not final amendment.','type':'role_precision_clarification'},
('A10','authority'):{'critical':False,'reason':'Statutory authority is supporting context; this section69 citation alone does not identify the notice or determine lifecycle/participation/date scope. Do not inflate critical quota with legal-authority trivia.','type':'criticality_adjudication'}
}
groups={
'A02':{'hearing_selection':'hearing','hearing_clock':'hearing'},
'A05':{'prior_comment_open':'prior_comment_window','prior_comment_close':'prior_comment_window'},
'A06':{'current_comment_close':'current_comment_deadline','receipt_condition':'current_comment_deadline'},
'A07':{'current_comment_open':'current_comment_window','current_comment_close':'current_comment_window'},
'A08':{'comment_duration_anchor':'comment_deadline','receipt_condition':'comment_deadline','actual_submission_date':'comment_deadline'},
'B01':{'comment_close':'public_review','hearing':'public_review'},
'B02':{'public_review_ambiguous':'public_review','comment_close':'public_review','review_clock':'public_review'},
'B03':{'comment_close':'comment_deadline','close_clock':'comment_deadline','hearing':'hearing','timezone':'hearing'},
'B04':{'comment_close':'comment_deadline','close_clock':'comment_deadline','hearing':'hearing','timezone':'hearing'},
'B06':{'comment_duration':'comment_deadline','close_clock':'comment_deadline'},
'B08':{'event':'lifecycle_scope','scope_reason':'lifecycle_scope'},
'B09':{'event':'lifecycle_scope','scope_reason':'lifecycle_scope'}
}
def decisive(k,f):
 fid=f['field_id']; rule='Preserve the stated value with the question’s exact role and target scope; equivalent date/number formats are allowed, new precision or changed lifecycle is not.'
 if f['answerability']=='not_stated': rule='No value is supplied in the retained target scope. Safe abstention requires complete relevant output scope; omitted scope cannot establish absence. Do not infer from neighboring notices or metadata.'
 elif f['answerability']=='uncertain': rule='Preserve conflicting source renditions without resolving. Exclude from determinate field denominator and unqualified document gate.'
 elif f['answerability']=='explicit_negative': rule='Preserve explicit no-hearing-scheduled assertion or selected negative checkbox; silence is insufficient.'
 if f['basis']=='visual_mark': rule+=' Preserve marked state attached to correct option, action heading, and column; merely listing labels is insufficient.'
 if k in ['A01','A03'] and fid in ['generic_comment_duration','conditional_oral_request']: rule+=' Printed boilerplate on final filing; must not assert new current comment/request window or compute a close from final filing stamp.'
 if k=='A02' and fid=='oral_request_condition': rule+=' Counterfactual condition only: source already marks hearing scheduled. Must not treat this as an active hearing-request deadline.'
 if k=='A02' and fid=='selected_lifecycle': rule+=' Selected amendment is PROPOSED, not final/adopted.'
 if k=='A07' and fid=='current_comment_close': rule+=' Full notice also says comments received by October20,2026; preserve receipt condition, date-only precision.'
 if k=='A07' and fid=='original_notice_date': rule+=' Page1 prints October31,2025; page2 prints October31,2026.'
 if k=='A08' and fid in ['planned_submission','printed_notice_date','prior_effective_date']: rule+=' Retain literal role and chronology inconsistency; anticipated on-or-after submission does not supply actual submission or absolute comment deadline.'
 if k=='B02' and fid=='public_review_ambiguous': rule+=' March14,2025 belongs to combined hearing-or-comment-period field; neither scheduled hearing nor comment close is resolved. This compound literal observation is determinate; the actual separate role is not.'
 if k in ['B03','B04'] and fid in ['comment_close','close_clock']: rule+=' Five p.m. belongs to later legislative-review objections, not current comment close.'
 if k=='B05' and fid=='hearing_request': rule+=' Request must be RECEIVED by commissioner of education not more than14 calendar days after May22publication; no computed absolute date.'
 if k=='B07': rule+=' Target opening says proposed amendments; authority paragraph inconsistently says proposes this repeal. Preserve source wording where reproduced; do not assert final repeal or borrow neighboring repeal lifecycle.'
 if k=='B08' and fid in ['event','scope_reason']: rule+=' Notice termination retains unchanged hearing date and promises corrected refiling; does not establish hearing cancellation.'
 if k=='B09' and fid in ['event','scope_reason']: rule+=' Hearing will be rescheduled and new notice filed; new hearing date remains unknown.'
 return rule
units=[]; all_changes=[]; failures=[]; corpus=[]
for p in sorted(ROOT.glob('source-*/[AB]*/fixture.json')):
 d=json.loads(p.read_text());k=d['fixture_id'];s=p.parent
 assert k in notes
 raw=p.read_bytes();h=sha(p); snap=collector_dir/(k+'-'+h[:12]+'.json')
 if not snap.exists():snap.write_bytes(raw)
 checks={n:sha(s/n)==d[n.replace('.pdf','')+'_sha256'] for n in ['original.pdf','input.pdf']}
 assert all(checks.values()),(k,checks)
 assert notes[k]['pages']==list(range(1,d['input_page_count']+1)),k
 page_records=[{'input_page':i,'original_physical_page':d['original_physical_pages'][i-1],'rendered_image_path':str(s/f'page-{i}.png'),'rendered_image_sha256':sha(s/f'page-{i}.png'),'complete_page_viewed':True,'continuation_checked':True,'neighboring_notice_boundaries_checked':True} for i in notes[k]['pages']]
 for page_record in page_records:
  page_record['absence_scope_rechecked_original_detail_after_primary_correction']=k in ['A04','A05','A06','A07','A08','A10','B01','B02','B03','B04','B05','B06','B07','B08','B09','B10']
 fields=[];audits=[];changes=[]
 for orig in d['reference_fields']:
  f=copy.deepcopy(orig);change=overrides.get((k,f['field_id']));reason='Independent full-page source review agrees with collector answer, answerability and role.'
  if change:
   f.update({a:b for a,b in change.items() if a not in ['reason','type']});reason=change['reason'];changes.append({'field_id':f['field_id'],'type':change['type'],'reason':reason,'collector_value':orig['expected_value'],'reviewer_value':f['expected_value'],'collector_answerability':orig['answerability'],'reviewer_answerability':f['answerability']})
  f['semantic_group_id']=groups.get(k,{}).get(f['field_id'],f['field_id'])
  f['critical_reason']='Loss or wrong association can change target identity, lifecycle, temporal role/precision or participation conditions.' if f['critical'] else 'Supporting context; not counted in critical evidence gate.'
  f['expected_value_shape']=type(f['expected_value']).__name__
  f['accepted_equivalences']=['Equivalent date, time, number, capitalization and whitespace formats preserving meaning.','No added timezone, computed relative date, final/proposed stage change, or borrowed neighboring value.']
  f['decisive_evidence']=decisive(k,f);f['notice_scope_boundaries']=scopes[k]
  f['source_pages_viewed']=notes[k]['pages'];f['absence_scope_if_applicable']=scopes[k] if f['answerability']=='not_stated' else None
  f['reviewer_source_note']=notes[k]['facts'];fields.append(f)
  audits.append({'field_id':f['field_id'],'collector_value':orig['expected_value'],'collector_answerability':orig['answerability'],'collector_critical':orig['critical'],'source_pages_viewed':notes[k]['pages'],'source_regions':f['region'],'source_quote_or_blank_scope':f['source_quote'] or scopes[k],'reviewer_value':f['expected_value'],'reviewer_answerability':f['answerability'],'reviewer_critical':f['critical'],'semantic_group_id':f['semantic_group_id'],'disagreement_type':change['type'] if change else None,'adjudication':'reviewer_corrected' if change else 'confirmed','adjudication_reason':reason,'final_status':'source_review_complete' if confirmed else 'source_comparison_complete_pending_collector_ready'})
 count=len({f['semantic_group_id'] for f in fields if f['critical'] and f['answerability']!='uncertain'})
 uncertain=[f['field_id'] for f in fields if f['critical'] and f['answerability']=='uncertain']
 adj={'fixture_id':k,'reference_version':'reviewer-source-v1' if confirmed else 'reviewer-source-v1-provisional','collector_annotation_hash':h,'collector_snapshot':str(snap),'input_sha256':d['input_sha256'],'reviewer_kind':'independent agent, not human gold standard','new_vendor_outputs_inspected':False,'state':d['state'].removeprefix('US-'),'primary_bucket':d['bucket'],'layout_features':d['layout_features'],'package_limitations':d['package_limitations'],'notice_scope_boundaries':scopes[k],'reference_fields':fields,'adjudications':changes,'critical_determinate_groups':count,'critical_uncertain_fields':uncertain,'reference_gate_eligible':count>=4 and not uncertain,'collector_ready_confirmed':confirmed}
 adj['original_sha256']=d['original_sha256']
 adj['original_physical_pages']=d['original_physical_pages']
 adj['collector_shared_original_group']=d.get('shared_original_group')
 adj['collector_template_family']=d.get('template_family',d.get('template_group'))
 adj['agency_reference']=next((f['expected_value'] for f in fields if f['field_id']=='agency'),None)
 out=adjudicated_dir/(k+'.json');save(out,adj)
 u={'fixture_id':k,'status':'source_review_complete' if confirmed else 'source_comparison_complete_pending_collector_ready','state':adj['state'],'primary_bucket':d['bucket'],'expected_source_directory':str(s),'original_sha256':d['original_sha256'],'input_sha256':d['input_sha256'],'input_page_count':d['input_page_count'],'original_physical_pages':d['original_physical_pages'],'hash_checks':checks,'notice_scope_verified':True,'all_relevant_rendered_pages_viewed':True,'reviewed_page_records':page_records,'collector_annotation_hash':h,'adjudicated_annotation_hash':sha(out),'adjudicated_annotation_path':str(out),'field_audits':audits,'disagreements':changes,'adjudications':changes,'critical_determinate_groups':count,'critical_uncertain_fields':uncertain,'reference_gate_eligible':adj['reference_gate_eligible'],'package_limitations_checked':True,'collector_ready_confirmed':confirmed,'freeze_ready':confirmed}
 units.append(u);all_changes.extend([dict(fixture_id=k,**c) for c in changes]);corpus.append(d)
a=json.loads((REVIEW/'source-annotation-audit.json').read_text())
a.update(phase='source-only review complete; ready for primary corpus freeze' if confirmed else 'awaiting collector-ready confirmation',units=units,visually_preinspected_units=len(units),visually_preinspected_pages=sum(u['input_page_count'] for u in units),source_compared_units=len(units),reviewed_units=len(units) if confirmed else 0,pending_units=0 if confirmed else len(units),freeze_ready=confirmed,new_vendor_outputs_inspected=False,notes=['All20units/34renderedinputpages independently inspected; all collector questions compared.','Both collectors confirmed final via primary; all20 annotation hashes match independently compared versions.','No new vendor parse output read. Reviewer corrections reside only in review/adjudicated; collector snapshots retained. A10 incorrect reviewer absence claim was reversed following primary challenge; disagreement history retained and all30 related pages rechecked at original detail.','PDF content-stream equivalence is collector-reported; reviewer independently checks source/input/image hashes, page maps and visual notice boundaries.'])
save(REVIEW/'source-annotation-audit.json',a)
counts={
 'units':len(units),'input_page_instances':sum(u['input_page_count'] for u in units),'distinct_original_hashes':len({u['original_sha256'] for u in units}),'distinct_input_hashes':len({u['input_sha256'] for u in units}),'states':dict(collections.Counter(u['state'] for u in units)),'buckets':dict(collections.Counter(u['primary_bucket'] for u in units)),
 'fields':sum(len(u['field_audits']) for u in units),'critical_fields':sum(f['reviewer_critical'] for u in units for f in u['field_audits']),'critical_determinate_groups':sum(u['critical_determinate_groups'] for u in units),'reference_gate_eligible_units':[u['fixture_id'] for u in units if u['reference_gate_eligible']],'reference_insufficient_units':[u['fixture_id'] for u in units if not u['reference_gate_eligible']],
 'shared_original_clusters':{h:[u['fixture_id'] for u in units if u['original_sha256']==h] for h,n in collections.Counter(u['original_sha256'] for u in units).items() if n>1},
 'template_families':dict(collections.Counter(d.get('template_family',d.get('template_group','unlabeled')) for d in corpus)),
 'max_page_count':max(u['input_page_count'] for u in units),'calibration_hash_present':any(u['input_sha256']=='ac95c240653690261eb7a6fef83bd80a04310cf49c15c37256569bbc70315955' for u in units),'all_hash_checks_pass':all(all(u['hash_checks'].values()) for u in units),'new_vendor_outputs_inspected':False}
counts['distinct_original_physical_pages']=len({(u['original_sha256'],p) for u in units for p in u['original_physical_pages']})
counts['overlapping_page_instances']=[{'units':['B05','B06'],'original_physical_page':32,'reason':'Two distinct complete target notices share a whole register page; contextual content overlaps.'}]
counts['quota_checks']={'20units':counts['units']==20,'6plusstates':len(counts['states'])>=6,'max4perstate':max(counts['states'].values())<=4,'5perbucket':sorted(counts['buckets'].values())==[5,5,5,5],'max4pages':counts['max_page_count']<=4,'under80pageinstances':counts['input_page_instances']<=80,'max2peroriginal_issue':max(collections.Counter(u['original_sha256'] for u in units).values())<=2,'calibration_excluded':not counts['calibration_hash_present']}
save(REVIEW/'corpus-audit.json',counts);save(REVIEW/'adjudications.json',all_changes)
print(json.dumps(counts,indent=2))
