#!/usr/bin/env python3
"""Materialize manually adjudicated Docling Markdown evidence; no provider calls.
Ranges follow frozen reference order, and are reviewer-selected, not text matching.
"""
import json, hashlib, pathlib, collections
HERE=pathlib.Path(__file__).resolve().parent
B=HERE.parents[2]; R=B/'artifacts'; D=HERE.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def rows(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def dump(name,x): (HERE/name).write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def ledger(name,x): (HERE/name).write_text(''.join(json.dumps(r,ensure_ascii=False,allow_nan=False)+'\n' for r in x))
# Exactly one range per frozen field, in frozen order; ranges include decisive labels.
RANGES={
'A01':[(9,13),(27,35),(65,95),(43,51),(19,23),(115,133),(83,85),(99,123),(53,53),(43,53)],
'A02':[(9,13),(27,33),(65,75),(35,41),(35,39),(17,19),(87,95),(77,81),(43,43),(35,43)],
'A03':[(9,11),(31,39),(59,103),(41,45),(19,21),(109,133),(89,91),(99,103),(47,47),(41,47)],
'A04':[(7,7),(25,31),(7,7),(7,7),(7,7),(25,31),(1,31)],
'A05':[(7,9),(1,3),(7,11),(9,11),(11,11),(11,11),(11,11),(3,7),(23,23),(1,27)],
'A06':[(1,5),(7,15),(13,13),(7,11),(19,19),(27,35),(27,33),(35,35),(1,39)],
'A07':[(1,3),(1,5),(9,10),(12,12),(12,16),(16,16),(3,3),(3,27),(1,29)],
'A08':[(9,11),(1,11),(1,3),(19,19),(25,37),(39,39),(1,81),(11,11),(11,11),(1,7)],
'A09':[(5,5),(7,13),(9,19),(13,15),(7,13),(29,35),(1,3),(60,62)],
'A10':[(65,75),(59,65),(61,71),(65,77),(59,65),(81,89),(75,77),(67,69),(1,3)],
'B01':[(25,27),(17,19),(43,47),(101,103),(93,99),(83,91),(1,115),(1,115)],
'B02':[(25,27),(17,19),(79,81),(103,105),(93,101),(53,57),(1,123),(1,123)],
'B03':[(1,3),(3,3),(3,3),(7,7),(19,21),(9,15),(23,23),(1,59),(1,59)],
'B04':[(15,15),(17,23),(17,29),(31,31),(32,40),(84,86),(1,1),(1,114),(1,114)],
'B05':[(43,51),(45,51),(155,165),(79,79),(79,79),(153,157),(155,165),(41,165)],
'B06':[(61,67),(63,67),(131,141),(88,88),(90,90),(129,141),(139,141),(59,151)],
'B07':[(35,37),(35,37),(77,81),(63,63),(53,53),(77,81),(79,81),(35,87)],
'B08':[(5,7),(9,11),(13,15),(25,27),(17,19),(21,23),(1,27),(1,27)],
'B09':[(5,7),(9,11),(13,15),(25,27),(17,19),(21,23),(1,27),(1,27)],
'B10':[(1,5),(1,5),(7,9),(1,5),(7,9),(1,9),(1,9),(1,9)]}
EXCEPTIONS={
('A01','filing_stamp'):('missing','omitted_filing_stamp','Colored FILED stamp date is absent; submit date does not substitute for a filing stamp. Image placeholders are not scoreable evidence.'),
('A01','selected_effective'):('partial_ambiguous','lost_selection_mark','Final effective option text survives but the source X is lost and both 30-day choices are rendered unchecked; generic labels cannot establish the selected final-column choice.'),
('A02','filing_stamp'):('missing','omitted_filing_stamp','Proposed-column APR 14 2026 stamp is absent; the submit date cannot rescue this distinct role.'),
('A02','selected_lifecycle'):('partial_ambiguous','lost_selection_mark','Proposed Action heading and amendment label survive, but source X on amendment is lost; all action options rendered unchecked. Body explanation cannot reconstruct selection.'),
('A02','proposed_effective'):('partial_ambiguous','contradictory_selection_rendition','Literal X survives attached to the proposed 30-day effective choice, while Markdown explicitly renders that option unchecked. This contradictory state does not pass the visual-selection gate.'),
('A03','rule_identity'):('incorrect','transcription_error','Frozen title reads Subpart 1 to S; output title and repealed/amended list replace S with 5. Separate body statement that new subpart 5 was created is faithful and is not an additional error.'),
('A03','selected_lifecycle'):('partial_ambiguous','contradictory_selection_rendition','Literal X remains attached to Adopted with no changes in text, but its Markdown checkbox is unchecked. Contradictory selected-state rendition prevents a gate pass.'),
('A03','filing_stamp'):('missing','omitted_filing_stamp','Final-column APR 07 2026 stamp is omitted behind image placeholders. Submit date retains another role and cannot substitute.'),
('A07','original_notice_date'):('not_assessable','source_reference_uncertain','Both source years, October 31 2025 and October 31 2026, survive; unchanged frozen reference leaves this critical conflict unresolved. No correction or error inferred.'),
('B08','scope_reason'):('partial_ambiguous','truncated_scope_reason','Hearing unchanged and notice re-filed survive, but to correct an administrative error is omitted. Full predeclared reason is not preserved.'),
('B08','replacement_hearing'):('missing','absence_scope_incomplete','Termination reason is truncated before its final clause. Under frozen full-notice absence scope, no safe absence gate is awarded despite no invented replacement clock.'),
('B08','comment_close'):('missing','absence_scope_incomplete','Full-notice absence scope is incomplete because the termination reason is truncated. No comment close is invented, but absence is not fully evidenced.')}
NOTES={
'A01':'Interleaved form columns reviewed against source; final lifecycle X stays attached, final effective X is lost; colored stamp omitted. Generic 20/25-day boilerplate not converted into new deadlines.',
'A02':'Hearing checked and full date/time preserved. Proposed amendment X lost; proposed-effective literal X conflicts with unchecked checkbox. Colored proposed stamp omitted. No invented final action.',
'A03':'Literal title S versus body subpart 5 checked visually. Title/list normalization counted once. Lifecycle X contradicts unchecked state; May 8 selected Other correct; colored stamp omitted.',
'A04':'Full withdrawal letter and filing-stamp identity/date/time preserved, without timezone or new participation deadline.',
'A05':'Historical February/March comment window stays historical; July filing and August certification kept distinct. No new comment close.',
'A06':'Both continuation-notice pages preserve old August close, new September receipt deadline and indicated-change scope. No additional hearing date.',
'A07':'Both original-notice years retained; reference insufficient, not parser error. Markup descriptions preserved; no resolved year or new hearing invented.',
'A08':'All four pages inspected; source itself prints January 29 2025 and awkward body wording. Five working days pre-notice versus five calendar days after OAL submission preserved; anticipated on-or-after date is not actual submission.',
'A09':'Target 00023-P stays separate from neighboring 00024-P. Sixty-day comment anchor versus adoption-triggered compliance preserved; bracketed prior rule text not a new deadline.',
'A10':'Target 00027-P stays separate from 00026-P and preceding petition. $500m through 2029 is authority horizon, September 1 petition date, sixty days comment duration.',
'B01':'Both pages preserve effective/publication/signature roles and blank public-review date. Page numeral 55 remains isolated, not an asserted review date. Attestation image omission does not remove any predeclared decisive date or absence region.',
'B02':'Three pages preserve emergency amendment and undifferentiated hearing-or-comment March 14 date; no specific close or review clock inferred. Attestation image omitted, date elsewhere role-preserved.',
'B03':'Two pages reviewed; October hearing, November comment close, January proposed effective date and conditional next-day 5pm objection are separate. Rule-text underlining lost but proposal stage remains explicit; no absolute objection date.',
'B04':'Two-page form preserves selected hearing and AMENDMENT under Proposed Action. June filing, May formal-proposal, November proposed effective and August comment/hearing roles remain distinct. Unfilled automatic-legislative-review label is not a selected assertion; no time/zone inferred for comment close.',
'B05':'Three-page target boundaries distinguish prior licensing notices and following real-estate notice. Comment window, fourteen-calendar-day hearing-request condition and earliest adoption remain separate. Proposed figure bracket markup is not a participation claim.',
'B06':'Two-page target boundaries and cross-page comment paragraph intact. Thirty-day comment duration and June earliest adoption retained separately; committee term dates are not comment clocks.',
'B07':'Two-page target distinguished from neighboring repeal. Thirty-day target comments, filing, publication and earliest adoption retained. Bracketed deleted provisions retain deletion context; no fixed effective date inferred.',
'B08':'Complete source image checked. Reason truncated after re-filed; no invented dates. Full frozen absence scope not passed.',
'B09':'Complete termination reason and publication footer retained; rescheduling promise does not supply replacement hearing date or comment close.',
'B10':'Single-page adoption preserved despite flattened labels; exact effective date and publication footer retained; no hearing, comment-close or filing date added.'}
freeze=read(R/'corpus-freeze.json');units=freeze['units'];fields=[];docs=[];ops=[];extras=[];source_checks=[];native_reuse=[]
old=R/'review/results-completed-v1'
# Freeze and output identity checks are prerequisites to writing any scores.
for rel,info in freeze['files'].items():assert sha(R/rel)==info['sha256'],rel
for u in units:
 fid=u['fixture_id'];refpath=R/u['reference_path'];ref=read(refpath);md=D/fid/'output.md';capture=read(D/fid/'capture.json');txt=md.read_text();lines=txt.splitlines(keepends=True)
 assert sha(refpath)==u['reference_sha256']; assert sha(R/u['directory']/'input.pdf')==u['input_sha256']
 assert len(RANGES[fid])==len(ref['reference_fields']); assert capture['operational_success'] and capture['converted_page_count']==u['input_page_count']
 assert sha(md)==next(x['sha256'] for x in capture['outputs'] if x['path'].endswith('output.md'))
 native=R/u['directory']/'native.txt';copy=D/fid/'native.txt';assert native.read_bytes()==copy.read_bytes()
 native_reuse.append({'fixture_id':fid,'original_artifact':str(native.relative_to(B)),'retained_copy':str(copy.relative_to(B)),'sha256':sha(native),'bytes':native.stat().st_size,'byte_identical':True})
 pages=list((R/u['directory']).glob('page-*.png'));assert len(pages)==u['input_page_count']
 source_checks.append({'fixture_id':fid,'source_pages_viewed':list(range(1,u['input_page_count']+1)),'source_images':[{'artifact':str(p.relative_to(B)),'sha256':sha(p)} for p in sorted(pages)],'entire_markdown_reviewed':True,'supplementary_json_used_to_rescue_score':False,'critical_extra_assertion_sweep_complete':True,'note':NOTES[fid]})
 common={'fixture_id':fid,'arm':'docling','evaluation_status':'complete','input_sha256':u['input_sha256'],'reference_version_hash':u['reference_sha256'],'operation_status':'completed_nonempty','output_artifact':str(md.relative_to(B)),'output_artifact_hash':sha(md)}
 scope='partial' if fid in ['A01','A02','A03','B08'] else 'complete'
 unitrows=[]
 for f,(lo,hi) in zip(ref['reference_fields'],RANGES[fid]):
  assert 1<=lo<=hi<=len(lines),(fid,lo,hi,len(lines))
  start=sum(map(len,lines[:lo-1]));end=sum(map(len,lines[:hi]));quote=txt[start:end];assert quote
  outcome='safe_abstention' if f['answerability']=='not_stated' else 'supported'
  reason='full_scope_no_stated_value' if outcome=='safe_abstention' else 'value_and_decisive_relation_preserved'
  note='Exact retained Markdown preserves the frozen value, role and required condition/precision. '+NOTES[fid]
  if outcome=='safe_abstention':note='All relevant retained notice pages/sections reviewed; no value for this field is stated or added. '+NOTES[fid]
  if (fid,f['field_id']) in EXCEPTIONS:outcome,reason,note=EXCEPTIONS[(fid,f['field_id'])]
  omission=None
  if outcome in ['missing','partial_ambiguous']:omission=f"Entire Markdown ({len(txt)} characters), source region: {f['region']}. {note}"
  fs='complete' if outcome in ['supported','safe_abstention'] else 'partial'
  if f['answerability']=='uncertain':fs='complete'
  r={**common,'field_id':f['field_id'],'semantic_group_id':f['semantic_group_id'],'critical':f['critical'],'answerability':f['answerability'],'outcome':outcome,'reason_code':reason,'scope_coverage':fs,'source_locator':{k:f.get(k) for k in ['input_page','original_page','region']},'output_locator':{'line_start':lo,'line_end':hi,'char_start':start,'char_end':end},'exact_output_quote':quote,'omission_scope':omission,'decisive_relation_preserved':outcome in ['supported','safe_abstention'],'field_gate_pass':(f['answerability'] in ['present','explicit_negative'] and outcome=='supported') or (f['answerability']=='not_stated' and outcome=='safe_abstention'),'reviewer_id':'docling-content-reviewer','adjudication_note':note,'absence_evidence_checked':outcome=='safe_abstention' if f['answerability']=='not_stated' else None}
  fields.append(r);unitrows.append(r)
 crit=[r for r in unitrows if r['critical']];groups={r['semantic_group_id'] for r in crit};passing={g for g in groups if all(r['field_gate_pass'] for r in crit if r['semantic_group_id']==g)}
 extraids=[]
 if fid=='A03':
  r=next(r for r in unitrows if r['field_id']=='rule_identity');eid='docling-A03-title-S-to-5';extraids=[eid]
  extras.append({**common,'assertion_id':eid,'assertion_text':r['exact_output_quote'],'output_locator':r['output_locator'],'source_scope':{'input_page':1,'region':'Name or number title and list of rules amended; distinct body statement is correct','source_quote':'Title 35, Part VIII, Subpart 1 to S - Table of Contents'},'error_type':'transcription_error','critical':True,'affected_field_ids':['rule_identity'],'reason':EXCEPTIONS[(fid,'rule_identity')][2],'deduplication_note':'One underlying title normalization, repeated in title/list; not an additional independent field failure.'})
 gate='insufficient_reference' if not ref['reference_gate_eligible'] else ('pass' if all(r['field_gate_pass'] for r in crit) and not extraids else 'content_fail')
 docs.append({**common,'gate_outcome':gate,'reference_gate_eligible':ref['reference_gate_eligible'],'scope_coverage':scope,'notice_scope':ref['reference_fields'][0]['notice_scope_boundaries'],'critical_field_counts':dict(collections.Counter(r['outcome'] for r in crit)),'critical_group_counts':{'total':len(groups),'pass':len(passing),'nonpass':len(groups-passing)},'extra_assertion_audit_complete':True,'critical_extra_assertion_ids':extraids,'failure_categories':sorted({r['reason_code'] for r in crit if not r['field_gate_pass']}),'reviewer_note':NOTES[fid]})
 ops.append({**common,'wrapper_wall_ms':capture['wrapper_wall_ms'],'returned_usage':None,'provider_cost':None,'local_only':True,'converted_page_count':capture['converted_page_count'],'input_page_count':u['input_page_count'],'capture_artifact':str((D/fid/'capture.json').relative_to(B))})
assert len(fields)==174 and len(docs)==20 and len(ops)==20
ledger('field-scores.jsonl',fields);ledger('document-scores.jsonl',docs);ledger('operation-records.jsonl',ops);ledger('extra-assertions.jsonl',extras)
# Retain original native record bytes, with original artifact-root semantics.
for name,expected in [('field-scores.jsonl',174),('document-scores.jsonl',20),('operation-records.jsonl',20)]:
 source=old/name;selected=[line for line in source.read_text().splitlines(keepends=True) if json.loads(line)['arm']=='native'];assert len(selected)==expected
 for line in selected:
  r=json.loads(line);assert sha(R/r['output_artifact'])==r['output_artifact_hash']
 (HERE/('native-'+name)).write_text(''.join(selected))
selected=[line for line in (old/'extra-assertions.jsonl').read_text().splitlines(keepends=True) if json.loads(line)['arm']=='native'];(HERE/'native-extra-assertions.jsonl').write_text(''.join(selected))
dump('native-reuse.json',{'policy':'Native score rows reused byte-for-byte only after all 20 original/native retained outputs compare byte-identically. Original score artifact root is artifacts; Docling score root is benchmark directory. No new native extraction or score reinterpretation.','source_results_directory':str(old.relative_to(B)),'source_ledger_hashes':{p.name:sha(p) for p in old.glob('*.jsonl')},'units':native_reuse})
dump('source-page-checks.json',source_checks)
def metrics(fs,ds):
 pos=[r for r in fs if r['critical'] and r['answerability'] in ['present','explicit_negative']];neg=[r for r in fs if r['critical'] and r['answerability']=='not_stated'];usable={r['fixture_id'] for r in ds if r['operation_status']=='completed_nonempty'}
 return {'documents':len(ds),'field_rows':len(fs),'document_gates':dict(collections.Counter(r['gate_outcome'] for r in ds)),'reference_eligible_documents':sum(r['reference_gate_eligible'] for r in ds),'field_outcomes':dict(collections.Counter(r['outcome'] for r in fs)),'critical_field_outcomes':dict(collections.Counter(r['outcome'] for r in fs if r['critical'])),'critical_positive_evidence_yield':{'supported':sum(r['outcome']=='supported' for r in pos),'scheduled_determinate_positive':len(pos)},'critical_positive_successful_output_content_score':{'supported':sum(r['outcome']=='supported' for r in pos if r['fixture_id'] in usable),'successful_output_determinate_positive':sum(r['fixture_id'] in usable for r in pos)},'critical_negative_scope_preservation':{'safe_abstention':sum(r['outcome']=='safe_abstention' for r in neg if r['fixture_id'] in usable),'successful_output_negative_references':sum(r['fixture_id'] in usable for r in neg)},'critical_uncertain_fields':sum(r['critical'] and r['answerability']=='uncertain' for r in fs)}
nf=rows(HERE/'native-field-scores.jsonl');nd=rows(HERE/'native-document-scores.jsonl')
paired=collections.Counter();ng={r['fixture_id']:r['gate_outcome'] for r in nd}
for r in docs:
 a=ng[r['fixture_id']];c=r['gate_outcome']; key='reference_insufficient' if 'insufficient_reference' in [a,c] else 'one_or_both_operationally_unusable' if 'operational_unusable' in [a,c] else 'both_pass' if a==c=='pass' else 'native_only_pass' if a=='pass' else 'docling_only_pass' if c=='pass' else 'both_content_fail';paired[key]+=1
m={'estimand':freeze.get('estimand','Reviewer-assessed preservation of predeclared evidence on purposive diagnostic20; not national or extraction accuracy.'),'docling':metrics(fields,docs),'native_reused':metrics(nf,nd),'paired_document_gates':dict(paired),'docling_critical_extra_assertions':len(extras),'docling_documents_with_critical_extra_assertions':len({r['fixture_id'] for r in extras}),'docling_failures':{r['fixture_id']:r['failure_categories'] for r in docs if r['gate_outcome']!='pass'}}
dump('metrics.json',m)
# Full serialized-record integrity check, not an alternative semantic reviewer.
for r in rows(HERE/'field-scores.jsonl')+rows(HERE/'extra-assertions.jsonl'):
 p=B/r['output_artifact'];assert sha(p)==r['output_artifact_hash'];t=p.read_text();loc=r['output_locator'];quote=r.get('exact_output_quote',r.get('assertion_text'));assert t[loc['char_start']:loc['char_end']]==quote
for rel,info in freeze['files'].items():assert sha(R/rel)==info['sha256'],rel
dump('validation.json',{'status':'passed','docling_field_rows':len(fields),'docling_document_rows':len(docs),'docling_operation_rows':len(ops),'docling_extra_rows':len(extras),'native_field_rows_reused':len(nf),'native_document_rows_reused':len(nd),'native_outputs_byte_identical':20,'frozen_files_hash_verified_unchanged':len(freeze['files']),'source_pages_visually_checked':sum(u['input_page_count'] for u in units),'all_output_hashes_and_exact_quote_offsets_valid':True,'reference_hashes_verified':20,'corpus_freeze_sha256':sha(R/'corpus-freeze.json'),'scoring_contract_sha256':sha(R/'review/scoring-contract.json'),'ledger_hashes':{p.name:sha(p) for p in HERE.glob('*.jsonl')},'manual_scoring':True,'blinded_review':False,'no_supplementary_output_rescue':True,'no_provider_calls':True})
print(json.dumps(m,indent=2))
