#!/usr/bin/env python3
"""Manual heldout evidence decisions; materialization only, no parser or extraction calls."""
import pathlib,json,hashlib,collections
P=pathlib.Path(__file__).resolve().parent;Q=P.parents[1];B=Q.parent;E=Q/'heldout-execution/docling'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
def dump(n,x):(P/n).write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def ledger(n,x):(P/n).write_text(''.join(json.dumps(r,ensure_ascii=False,allow_nan=False)+'\n' for r in x))
F=Q/'heldout-execution/freeze.json';assert sha(F)=='9947fb211688ba7010e6e0491fadf88296bd2607cfae877e43b9b9782dc176c7';freeze=read(F)
# Reviewer-selected line ranges follow frozen reference order. Zero/zero = entire output.
M={
'docling':{
'H01':[(3,3),(25,27),(1,3),(5,9),(29,31),(63,67),(29,37),(0,0),(0,0)],
'H02':[(7,7),(9,11),(15,15),(5,15),(19,19),(21,21),(55,61),(0,0),(0,0)],
'H03':[(3,9),(1,1),(5,9),(47,49),(57,64),(27,43),(27,29),(0,0),(0,0)],
'H04':[(9,13),(65,65),(11,25),(11,13),(1,3),(15,15),(17,17),(0,0),(0,0)],
'H05':[(21,23),(105,107),(17,19),(25,27),(31,33),(51,59),(0,0),(0,0)],
'H06':[(11,17),(15,15),(11,19),(49,55),(19,71),(73,79),(5,75),(23,25),(101,103),(11,111)],
'H07':[(8,14),(3,6),(26,28),(1,40),(124,130),(132,138),(140,143),(60,60),(1,143),(1,143)],
'H08':[(1,3),(44,47),(3,8),(1,8),(10,12),(14,14),(14,14),(34,38),(0,0),(0,0)]},
'native':{
'H01':[(3,7),(28,29),(1,7),(9,13),(30,31),(57,67),(30,34),(0,0),(0,0)],
'H02':[(7,7),(8,9),(11,11),(5,11),(17,17),(18,18),(42,46),(0,0),(0,0)],
'H03':[(2,9),(1,1),(3,9),(46,49),(58,62),(29,32),(29,32),(0,0),(0,0)],
'H04':[(7,12),(92,95),(8,12),(8,12),(1,2),(14,20),(22,27),(0,0),(0,0)],
'H05':[(15,17),(110,115),(12,13),(13,16),(22,24),(30,35),(0,0),(0,0)],
'H06':[(33,41),(38,39),(35,50),(95,110),(47,140),(142,159),(7,149),(56,56),(199,202),(33,218)],
'H07':[(8,12),(4,6),(19,21),(1,35),(122,124),(126,129),(131,133),(58,58),(1,133),(1,133)],
'H08':[(1,7),(93,99),(9,19),(1,19),(28,29),(31,35),(31,35),(78,83),(0,0),(0,0)]}}
NOTES={
'H01':'Second hearing noon kept separate from date-only written-comment cutoff. Original December-January period and intended removal of sections 4/6 remain historical/change-scope facts.',
'H02':'Routine-technical proposal, explicit no hearing, September13 date-only comment deadline, and August6 payment approval kept separate. Only complete two-page form in scope, not excluded rule package.',
'H03':'Current October20 hearing10-10:30 versus comment cutoff4:30 distinct; August19 analysis publication and September8 prior hearing not current dates. Both outputs lose source rule-text underlining/strikeout; deleted 30-day contract-approval requirement is reproduced without deletion state. This substantive contract deadline is outside the bounded notice-participation assertion gate and is recorded as a markup limitation, not a new comment deadline.',
'H04':'Publication May14, hearing July15 at1pm, 60-day comment-period notice, comments prior to hearing and five working days accommodation condition preserved without computed cutoff or timezone.',
'H05':'April filing stamp date/time, May comment close5pm and hearing9-11am preserved. Four rule citations retain proposed context. Scope is first two pages only, not excluded substantive rule text.',
'H06':'General register box says20 calendar days while target says20 working days; both preserved, frozen unresolved. June3 request/comment clock,25-person threshold, withdrawal/cancellation and June17 hearing conditionality retained. Five working days after hearing only if held. Both lose strikeout/underline for2023→2026 NEC edition in proposed text, yielding2023 2026; no resolution inferred. Neighbor marriage/family notice kept separate.',
'H07':'Target58107 repeal distinguished from neighboring58106 new rule. August31 comment date, September8 anticipated MAY explicitly NOT effective date, June30 authorization and August1 publication stay distinct. No target hearing/close clock supplied.',
'H08':'July16 written-comment cutoff8am, July22-23 hearing8:30-5:30, possible July24 extension and before1pm July22 eligibility condition distinguished. June12 notice/preparation date and July15 accommodation deadline retain roles. Source standard-development and staff/public X selections checked. Docling omits fiscal footnote on page3; whole-notice absence scopes do not pass. Native preserves this footnote.'}
EX={('docling','H03','prior_hearing'):('partial_ambiguous','role_association_displaced','September8 date survives as a bullet after Waivers, separated from prior-hearing introduction by Fiscal Impact, Jobs Impact and Waivers headings. Reviewer cannot reconstruct role from source to upgrade it.'),('docling','H08','hearing'):('incorrect','transcription_error','Output reads July2223,2026, merging source July22-23 day range. No source-image/native/JSON rescue; this is a changed hearing-date rendition.'),('docling','H08','timezone'):('missing','absence_scope_incomplete','Full four-page frozen absence scope loses the substantive fiscal footnote on page3; no timezone invented, but complete absence-scope preservation is not established.'),('docling','H08','effective'):('missing','absence_scope_incomplete','Full four-page frozen absence scope loses the page3 fiscal implementation-condition footnote. No fixed effective date invented; full-scope absence gate is not awarded.')}
fields=[];docs=[];ops=[];extras=[];checks=[]
for rel,info in freeze['files'].items():assert sha(Q/rel)==info['sha256'],rel
for u in freeze['units']:
 fid=u['fixture_id'];refpath=Q/u['reference_path'];ref=read(refpath);assert sha(refpath)==u['reference_sha256'];assert sha(Q/'heldout'/fid/'input.pdf')==u['input_sha256'];cap=read(E/fid/'capture.json');assert cap['operational_success'] and cap['converted_page_count']==u['input_page_count']
 native=E/fid/'native.txt';original=E/'native'/f'{fid}.txt';assert native.read_bytes()==original.read_bytes();assert sha(native)==cap['native_baseline']['sha256']
 checks.append({'fixture_id':fid,'pages_viewed':list(range(1,u['input_page_count']+1)),'source_images':[{'artifact':str(p.relative_to(B)),'sha256':sha(p)} for p in sorted((Q/'heldout'/fid).glob('page-*.png'))],'entire_native_and_markdown_reviewed':True,'critical_extra_assertion_sweep_complete':True,'note':NOTES[fid]})
 for arm in ['native','docling']:
  output=E/fid/('native.txt' if arm=='native' else 'output.md');txt=output.read_text();lines=txt.splitlines(keepends=True);assert len(M[arm][fid])==len(ref['reference_fields']);outsha=sha(output)
  if arm=='docling':assert outsha==next(z['sha256'] for z in cap['outputs'] if z['path'].endswith('output.md'))
  c={'fixture_id':fid,'arm':arm,'evaluation_status':'complete','input_sha256':u['input_sha256'],'reference_version_hash':u['reference_sha256'],'operation_status':'completed_nonempty','output_artifact':str(output.relative_to(B)),'output_artifact_hash':outsha};unitrows=[]
  for f,(lo,hi) in zip(ref['reference_fields'],M[arm][fid]):
   if lo==hi==0:lo,hi=1,len(lines)
   assert 1<=lo<=hi<=len(lines),(arm,fid,lo,hi,len(lines))
   start=sum(map(len,lines[:lo-1]));end=sum(map(len,lines[:hi]));quote=txt[start:end]
   outcome='safe_abstention' if f['answerability']=='not_stated' else 'supported';reason='full_scope_no_stated_value' if outcome=='safe_abstention' else 'value_and_decisive_relation_preserved';note='Exact output preserves frozen value, role, conditions and precision. '+NOTES[fid]
   if outcome=='safe_abstention':note='Complete relevant retained source/output scope inspected; no value stated or added. '+NOTES[fid]
   if f['answerability']=='uncertain':outcome,reason,note='not_assessable','source_reference_uncertain','Both20-calendar/20-working-day source renditions survive; frozen critical reference conflict is unresolved. No parser error or successful abstention assigned.'
   if (arm,fid,f['field_id']) in EX:outcome,reason,note=EX[(arm,fid,f['field_id'])]
   good=(f['answerability'] in ['present','explicit_negative'] and outcome=='supported') or (f['answerability']=='not_stated' and outcome=='safe_abstention')
   row={**c,'field_id':f['field_id'],'semantic_group_id':f['semantic_group_id'],'critical':f['critical'],'answerability':f['answerability'],'outcome':outcome,'reason_code':reason,'scope_coverage':'complete' if outcome in ['supported','safe_abstention','not_assessable'] else 'partial','source_locator':{k:f.get(k) for k in ['input_page','original_page','region']},'output_locator':{'line_start':lo,'line_end':hi,'char_start':start,'char_end':end},'exact_output_quote':quote,'omission_scope':f"Entire retained output ({len(txt)} characters), source region {f['region']}. {note}" if outcome in ['missing','partial_ambiguous'] else None,'decisive_relation_preserved':good,'field_gate_pass':good,'reviewer_id':'docling-heldout-content-reviewer','adjudication_note':note,'absence_evidence_checked':outcome=='safe_abstention' if f['answerability']=='not_stated' else None};fields.append(row);unitrows.append(row)
  extraids=[]
  if arm=='docling' and fid=='H08':
   row=next(z for z in unitrows if z['field_id']=='hearing');eid='docling-H08-merged-hearing-range';extraids=[eid];extras.append({**c,'assertion_id':eid,'assertion_text':row['exact_output_quote'],'output_locator':row['output_locator'],'source_scope':{'input_page':1,'region':'Oral hearing','source_quote':'July22-23,2026'},'error_type':'transcription_error','critical':True,'affected_field_ids':['hearing'],'reason':EX[(arm,fid,'hearing')][2],'deduplication_note':'Same underlying range error as failed hearing field, counted once.'})
  critical=[z for z in unitrows if z['critical']];groups={z['semantic_group_id'] for z in critical};passed={g for g in groups if all(z['field_gate_pass'] for z in critical if z['semantic_group_id']==g)};gate='insufficient_reference' if not ref['reference_gate_eligible'] else 'pass' if all(z['field_gate_pass'] for z in critical) and not extraids else 'content_fail'
  docs.append({**c,'gate_outcome':gate,'reference_gate_eligible':ref['reference_gate_eligible'],'scope_coverage':'partial' if arm=='docling' and fid in ['H03','H08'] else 'complete','notice_scope':ref['notice_scope_boundaries'],'critical_field_counts':dict(collections.Counter(z['outcome'] for z in critical)),'critical_group_counts':{'total':len(groups),'pass':len(passed),'nonpass':len(groups-passed)},'extra_assertion_audit_complete':True,'critical_extra_assertion_ids':extraids,'failure_categories':sorted({z['reason_code'] for z in critical if not z['field_gate_pass']}),'reviewer_note':NOTES[fid]})
  ops.append({**c,'wrapper_wall_ms':cap['wrapper_wall_ms'] if arm=='docling' else None,'native_tool':'pdftotext26.05.0 -layout' if arm=='native' else None,'input_page_count':u['input_page_count'],'converted_page_count':cap['converted_page_count'] if arm=='docling' else None,'capture_artifact':str((E/fid/'capture.json').relative_to(B)),'returned_usage':None,'local_only':True,'note':'Native timing not provided; exact fresh baseline bytes verified against extraction copy.' if arm=='native' else 'Local Docling operational success; confidence/JSON not used for content rescue.'})
assert len(fields)==148 and len(docs)==len(ops)==16
assert len({(z['fixture_id'],z['arm'],z['field_id']) for z in fields})==148
for n,z in [('field-scores.jsonl',fields),('document-scores.jsonl',docs),('operation-records.jsonl',ops),('extra-assertions.jsonl',extras)]:ledger(n,z)
dump('source-page-checks.json',checks)
def metric(arm):
 fs=[z for z in fields if z['arm']==arm];ds=[z for z in docs if z['arm']==arm];pos=[z for z in fs if z['critical'] and z['answerability'] in ['present','explicit_negative']];neg=[z for z in fs if z['critical'] and z['answerability']=='not_stated']
 return {'documents':len(ds),'field_rows':len(fs),'reference_eligible_documents':sum(z['reference_gate_eligible'] for z in ds),'document_gates':dict(collections.Counter(z['gate_outcome'] for z in ds)),'field_outcomes':dict(collections.Counter(z['outcome'] for z in fs)),'critical_field_outcomes':dict(collections.Counter(z['outcome'] for z in fs if z['critical'])),'critical_positive_evidence_yield':{'supported':sum(z['outcome']=='supported' for z in pos),'scheduled_determinate_positive':len(pos)},'critical_positive_successful_output_content_score':{'supported':sum(z['outcome']=='supported' for z in pos),'successful_output_determinate_positive':len(pos)},'critical_negative_scope_preservation':{'safe_abstention':sum(z['outcome']=='safe_abstention' for z in neg),'successful_output_negative_references':len(neg)},'critical_uncertain_fields':sum(z['critical'] and z['answerability']=='uncertain' for z in fs),'critical_extra_assertions':sum(z['arm']==arm and z['critical'] for z in extras)}
paired=collections.Counter()
for u in freeze['units']:
 ds={z['arm']:z['gate_outcome'] for z in docs if z['fixture_id']==u['fixture_id']};a,b=ds['native'],ds['docling'];paired['reference_insufficient' if 'insufficient_reference' in [a,b] else 'both_pass' if a==b=='pass' else 'native_only_pass' if a=='pass' else 'docling_only_pass' if b=='pass' else 'both_content_fail']+=1
m={'estimand':'Manual preservation of frozen heldout evidence; no tuning, national accuracy claim, or extraction precision.','native':metric('native'),'docling':metric('docling'),'paired_document_gates':dict(paired),'failures':[{k:z[k] for k in ['fixture_id','arm','gate_outcome','failure_categories']} for z in docs if z['gate_outcome']!='pass']};dump('metrics.json',m)
for z in fields+extras:
 t=(B/z['output_artifact']).read_text();loc=z['output_locator'];assert t[loc['char_start']:loc['char_end']]==z.get('exact_output_quote',z.get('assertion_text'));assert sha(B/z['output_artifact'])==z['output_artifact_hash']
for rel,info in freeze['files'].items():assert sha(Q/rel)==info['sha256'],rel
dump('validation.json',{'status':'passed','freeze_sha256':sha(F),'frozen_files_verified_unchanged':len(freeze['files']),'source_pages_visually_checked':sum(u['input_page_count'] for u in freeze['units']),'reference_hashes_verified':8,'input_hashes_verified':8,'field_rows':148,'document_rows':16,'operation_rows':16,'unique_field_keys_verified':148,'output_hashes_and_exact_quote_offsets_verified':True,'native_fresh_copy_byte_identity_verified':8,'critical_extra_assertion_rows':len(extras),'manual_scoring':True,'blinded_review':False,'no_provider_calls_or_tuning':True,'artifact_paths_relative_to':'benchmark directory','ledger_hashes':{p.name:sha(p) for p in P.glob('*.jsonl')}})
print(json.dumps(m,indent=2))
