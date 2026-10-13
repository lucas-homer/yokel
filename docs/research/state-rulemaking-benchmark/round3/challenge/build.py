"""Build reviewer-labeled developmental cases; never calls a verifier or changes sources."""
from pathlib import Path
import json, hashlib, collections
O=Path(__file__).resolve().parent; B=O.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
runtime=[];labels=[];dependencies={}
def retained(rel,spans):
 p=B/rel;ls=p.read_text().splitlines(keepends=True);parts=[];loc=[]
 dependencies[rel]=sha(p)
 for a,z in spans:
  end=len(ls) if z is None else z; start=sum(map(len,ls[:a-1]));stop=sum(map(len,ls[:end]));s=p.read_text()[start:stop]
  parts.append(s);loc.append(dict(path=rel,sha256=sha(p),line_start=a,line_end=end,start=start,end=stop,quote=s))
 return '\n\n'.join(parts),loc
def add(id,fixture,rel,spans,field,value,claim,target,role,conditions,verdict,origin,category,rationale,fidelity,pages,natural=None,limitation=False):
 text,loc=retained(rel,spans);evidence=[];offset=0
 for l in loc:
  q=l['quote'];evidence.append(dict(quote=q,start=offset,end=offset+len(q)));offset+=len(q)+2
 runtime.append(dict(case_id=id,source_text=text,candidate=dict(field=field,value=value,claim=claim,target=target,role=role,conditions=conditions),evidence=evidence))
 refrel=(f'round2/protocol/heldout-review/{fixture}/adjudicated-reference.json' if fixture.startswith('H') else f'artifacts/review/adjudicated/{fixture}.json')
 images=[]
 for page in pages:
  path=(f'round2/heldout/{fixture}/page-{page}.png' if fixture.startswith('H') else f'artifacts/source-{fixture[0].lower()}/{fixture}/page-{page}.png');images.append(dict(path=path,sha256=sha(B/path),input_page=page,reviewed=True));dependencies[path]=sha(B/path)
 dependencies[refrel]=sha(B/refrel)
 if natural:dependencies[natural]=sha(B/natural)
 labels.append(dict(case_id=id,fixture_id=fixture,developmental=True,category=category,candidate_origin=origin,expected_verdict=dict(zip(['support','role','condition','conflict'],verdict)),expected_source_fidelity=fidelity,rationale=rationale,limitation_case=limitation,include_in_detectable_error_denominator=not limitation and (verdict[0]!='supported' or verdict[3]=='present'),expected_runtime_disposition='text_supported_only' if verdict[0]=='supported' and verdict[3]=='absent' else 'review',source_provenance=loc,source_images_reviewed=images,reference_artifact=dict(path=refrel,sha256=sha(B/refrel)),retained_error_record=natural,label_method='Reviewer judgments from retained output and source images; no verifier responses used.',reviewer_independence='Independent of forthcoming verifier execution and candidate extractor; reviewer collected held-out sources and reviewed OpenRouter round2 outputs, so not independent of collection or earlier scoring.'))
OK=['supported','matched','preserved','absent'];BAD=['contradicted','matched','preserved','absent']
h='round2/heldout-execution/openrouter/runs/';a='round2/openrouter/runs/'
email='DNRAdministrativeRulesComments@wisconsin.gov';wrong='DNRAministrativeRulesComments@wisconsin.gov';target='FWP-22-24 (CR 25-088)'
err='round2/llama-cost-effective/review-heldout/extra-assertions.jsonl'
add('C001','H01',h+'H01/output.md',[(36,54)],'submission_email',email,f'Written comments may be emailed to {email}.',target,'written_comment_submission_email',[],OK,'correct_control','submission_route','Exact submission destination and comment role match image and retained text.','correct',[2])
add('C002','H01',h+'H01/output.md',[(36,54)],'submission_email',wrong,f'Written comments may be emailed to {wrong}.',target,'written_comment_submission_email',[],BAD,'projection_of_retained_parser_error','submission_route','Candidate copies the actual Llama missing-d email; independently retained OpenRouter evidence spells Administrative correctly. Candidate observation is reviewer-authored, not an observed extractor output.','incorrect',[2],err)
add('C003','H01','round2/heldout-execution/llama-cost-effective/execution/runs/H01/cost_effective/output.md',[(55,55)],'submission_email',wrong,f'Written comments may be emailed to {wrong}.',target,'written_comment_submission_email',[],OK,'projection_of_retained_parser_error','same_parser_blindspot','Both runtime source and candidate share the actual missing-d email. Text support is correct; original-PDF fidelity is incorrect. A semantic verifier has no independent evidence to recover the missing letter. Exclude from detectable-error recall; report accepted original-source error separately. No delivery/bounce claim.','incorrect',[2],err,True)
add('C004','H08',h+'H08/output.md',[(15,23)],'hearing_date_range',['2026-07-22','2026-07-23'],'The announced hearing dates are July22–23,2026,8:30a.m.–5:30p.m.; a possible July24 extension is separate.','Alaska Board of Game 2026200173','announced_hearing_dates',['July24 is only a possible extension'],OK,'correct_control','date_range','Two-day announced range is preserved separately from conditional extension.','correct',[1])
add('C005','H08',h+'H08/output.md',[(15,23)],'hearing_date_range','July 2223, 2026','The announced hearing date is July 2223, 2026.','Alaska Board of Game 2026200173','announced_hearing_dates',[],BAD,'projection_of_retained_parser_error','date_range','Candidate transcribes actual Docling range-merge error; runtime independent retained text preserves July22–23. Deterministic calendar validation should also reject2223; no model required for that check.','incorrect',[1],'round2/docling/review-heldout/extra-assertions.jsonl')
add('C006','A03',a+'A03/output.md',[(11,20),(36,47)],'filing_date','2026-04-07','The official filing stamp states April7,2026.','Mississippi DOR Title35 PartVIII table of contents','official_filing_stamp_date',[],['insufficient','mismatched','preserved','absent'],'controlled_candidate_mutation','semantic_role','Runtime only supplies April7 as SUBMIT DATE; filing stamp text was naturally omitted. Borrowing that date cannot prove filing role, even though the image independently confirms the same date.','correct_but_runtime_unsupported',[1],'round2/openrouter/review/field-scores.jsonl')
add('C007','A03',a+'A03/output.md',[(1,None)],'filing_date',None,'The original notice contains no official filing-stamp date.','Mississippi DOR Title35 PartVIII table of contents','absence_of_official_filing_stamp_date',[],['insufficient','insufficient','preserved','absent'],'controlled_candidate_mutation','wrong_absence','Natural missing stamp is turned into an intentionally unsupported original-document absence claim. Empty parser cells establish absence in parser text only. Source image has FILED APR07 2026. No completeness oracle is injected into runtime.','incorrect',[1],'round2/openrouter/review/field-scores.jsonl')
add('C008','B02',a+'B02/output.md',[(31,45)],'comment_close','2025-03-14','The written-comment period closes March14,2025.','258 CMR9.00','written_comment_close',[],['insufficient','insufficient','preserved','absent'],'controlled_candidate_mutation','semantic_role','Combined hearing OR comment-period label cannot establish a unique comment-close role. No actual definite close error is claimed to have occurred in a parser.','unresolved_by_source',[1])
add('C009','H07',h+'H07/output.md',[(113,127)],'effective_date','2026-09-08','The repeal takes effect September8,2026.','R18-1 filing58107','actual_effective_date',[],['contradicted','mismatched','omitted_or_changed','absent'],'controlled_candidate_mutation','lost_qualification','Source explicitly says anticipated MAY date is NOT effective date. Candidate upgrades it to actual.','incorrect',[3])
add('C010','H07',h+'H07/output.md',[(113,127)],'anticipated_effective_date','2026-09-08','The agency anticipates September8,2026; this is not the effective date.','R18-1 filing58107','anticipated_effective_date',['anticipated only; not actual effective date'],OK,'correct_control','qualified_date','Correct control keeps the express NOT-effective qualification.','correct',[3])
add('C011','H06',h+'H06/output.md',[(17,23),(75,90)],'hearing','2026-06-17T09:30','The June17,2026 9:30a.m. hearing will occur regardless of the number of requests.','RD-04985 / 5-9065-41611','conditional_hearing',[],['contradicted','matched','omitted_or_changed','absent'],'controlled_candidate_mutation','lost_condition','Explicit regardless conflicts with25 valid request threshold, withdrawal/cancellation and June3 request deadline. Extension-limit conflict lies outside this bounded context and is irrelevant to this candidate.','incorrect',[1,2,3])
add('C012','H08',h+'H08/output.md',[(17,23)],'hearing_extension','2026-07-24','The hearing might extend to July24,8:30a.m.–5:30p.m.,at the same location, to accommodate those present before1p.m.July22 who lacked an opportunity to comment.','Alaska Board of Game 2026200173','conditional_hearing_extension',['might extend','same location','present before1p.m.July22 and lacked opportunity'],OK,'correct_control','conditional_extension','Correct control retains possibility, hours, location and participation eligibility condition.','correct',[1])
add('C013','A08',a+'A08/output.md',[(24,33)],'submission_date','2026-01-28','The department submitted the emergency rulemaking to OAL on January28,2026.','CDFW emergency groundfish readoption','actual_OAL_submission_date',[],['insufficient','mismatched','omitted_or_changed','absent'],'controlled_candidate_mutation','lost_qualification','Anticipates on or after is not evidence of completed submission on that date. Actual submission may or may not occur; insufficient, not a proven different date.','unresolved_by_source',[2])
add('C014','A07',a+'A07/output.md',[(3,5),(38,40)],'original_notice_date','2025-10-31','The original notice date is definitively October31,2025.','DMV Electronic Lien and Titling second modification','original_notice_date',[],['insufficient','matched','preserved','present'],'controlled_candidate_mutation','source_conflict','Original source prints2025 in opening and2026 in availability paragraph. Do not resolve by majority, chronology or assumed typo. Runtime conflict is relevant to candidate.','unresolved_source_conflict',[1,2])
add('C015','H06',h+'H06/output.md',[(3,11),(90,100)],'posthearing_extension_max',{'days':20,'basis':'working'},'The maximum extension is unambiguously20 working days.','RD-04985 / 5-9065-41611','posthearing_extension_max',['if hearing held'],['insufficient','matched','preserved','present'],'controlled_candidate_mutation','source_conflict','General box20 calendar days conflicts with target20 working days. The frozen reference explicitly leaves it unresolved; do not silently prefer one or infer legal precedence.','unresolved_source_conflict',[1,3])
add('C016','H03','round2/heldout-execution/docling/H03/output.md',[(27,49)],'prior_hearing','2026-09-08','The prior regulatory-analysis hearing was September8,2026.','ARC0619D','prior_regulatory_analysis_hearing',[],['insufficient','insufficient','preserved','absent'],'projection_from_retained_role_loss','semantic_role','Actual Docling bullet displaced below Fiscal Impact, Jobs Impact and Waivers. Date and introductory phrase survive but role association is ambiguous under the frozen round2 review; no reconstruction from the original image at runtime. Image confirms candidate fact, so source fidelity and runtime support differ.','correct_but_runtime_unsupported',[1],'round2/docling/review-heldout/field-scores.jsonl')
# Runtime prose spacing only; retained source spans remain byte-for-byte unchanged.
spacing={'July22':'July 22','July24':'July 24','July23':'July 23','April7':'April 7','March14':'March 14','September8':'September 8','June17':'June 17','January28':'January 28','October31':'October 31',',2026':', 2026',',2025':', 2025',',8:30':', 8:30','8:30a.m.':'8:30 a.m.','5:30p.m.':'5:30 p.m.','9:30a.m.':'9:30 a.m.',',at':', at','before1p.m.':'before 1 p.m.','p.m.July':'p.m. July','unambiguously20':'unambiguously 20','Title35':'Title 35','PartVIII':'Part VIII','CMR9.00':'CMR 9.00','filing58107':'filing 58107','ARC0619D':'ARC 0619D'}
for row in runtime:
 for key in ('claim','target'):
  for before,after in spacing.items(): row['candidate'][key]=row['candidate'][key].replace(before,after)
 for i,condition in enumerate(row['candidate']['conditions']):
  for before,after in spacing.items(): condition=condition.replace(before,after)
  row['candidate']['conditions'][i]=condition
# Independent pre-run review adopted by primary; preserve the original label snapshot.
for row in labels:
 row['include_in_model_only_denominator']=row['case_id']!='C007'
 row['include_in_scheduled_system_metrics']=True
 row['evaluation_ambiguous']=row['case_id']=='C016'
 row['include_in_primary_determinate_accuracy_denominator']=row['case_id'] not in ('C003','C016')
 if row['case_id']=='C002':
  row['expected_verdict']['role']='insufficient'
  row['rationale']+=' Independent pre-run review: the exact corrupted value is absent from supplied evidence, so its role is insufficient.'
 if row['case_id']=='C007':
  row['runtime_execution_note']='Null value triggers deterministic candidate_abstained before any model call; exclude from model-only denominators and retain scheduled system metrics.'
 if row['case_id']=='C016':
  row['include_in_detectable_error_denominator']=False
  row['expected_values_status']='provisional; evaluation ambiguous'
  row['accepted_alternative_verdict']={'support':'supported','role':'matched','condition':'preserved','conflict':'absent'}
  row['rationale']+=' Independent pre-run review: the association is plausibly recoverable from the dangling sentence; supported/matched is also accepted. Excluded from primary determinate error/gate accuracy.'

# Remaining independent pre-run audit adopted before freeze.
for row in labels:
 if row['case_id']=='C005':
  row['expected_verdict']['role']='insufficient'
  row['rationale']+=' Final pre-run audit: the malformed candidate date has no established role in supplied evidence.'
 if row['case_id']=='C015':
  row['expected_verdict']['condition']='omitted_or_changed'
  row['rationale']+=' Final pre-run audit: if-hearing-held appears in conditions but is omitted from the claim.'
 if row['case_id']=='C006':
  row['accepted_role_alternatives']=['mismatched','insufficient']
  row['rationale']+=' Final pre-run audit accepts mismatched or insufficient for the secondary role judgment.'
 if row['case_id']=='C004':
  row['material_scope']='Initial announced hearing dates only; separate extension conditions are tested by C012.'
 row['excerpt_scope']='Reviewer-scoped to the named notice; target segmentation is not evaluated.'

assert len(runtime)==16
contract=json.loads((B/'round3/verifiers/INPUT-CONTRACT.json').read_text())
for r in runtime:
 assert set(r)==set(contract['required']);assert set(r['candidate'])==set(contract['candidate_required'])
 assert len(r['source_text'])<=contract['limits']['source_text_codepoints']
 assert len(json.dumps(r,ensure_ascii=False).encode())<=contract['limits']['case_serialized_utf8_bytes']
 for e in r['evidence']:assert r['source_text'][e['start']:e['end']]==e['quote']
for l in labels:
 for k,v in l['expected_verdict'].items():assert v in contract['output_dimensions'][k]
for root,freeze_path in [(B/'artifacts',B/'artifacts/corpus-freeze.json'),(B/'round2',B/'round2/heldout-execution/freeze.json')]:
 frozen=json.loads(freeze_path.read_text())
 for path,meta in frozen['files'].items():assert sha(root/path)==meta['sha256'],path
for rel,hsh in dependencies.items():assert sha(B/rel)==hsh,rel
for name,rows in [('runtime.jsonl',runtime),('evaluation-only.jsonl',labels)]:
 (O/name).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
dump(O/'contract.json',dict(schema_version=contract['schema_version'],adapter_contract='round3/verifiers/INPUT-CONTRACT.json',adapter_contract_sha256=sha(B/'round3/verifiers/INPUT-CONTRACT.json'),runtime_file='runtime.jsonl',evaluation_file='evaluation-only.jsonl',status='developmental_reviewer_labeled_not_fresh',cases=16,labels_must_not_enter_runtime=True,candidates_are_reviewer_authored=True,natural_error_semantics='Natural parser errors are exact retained errors projected into manually authored observations; these are not naturally observed extractor errors.',source_text_semantics='Unmodified retained parser-text spans joined by two newlines; reviewer-selected context, not automated retrieval. Complete output supplied for original-document absence challenge.',label_conventions={'support':'Entailment by supplied text; explicit false certainty loses support. No image/reference rescue.','role':'Whether candidate assigns evidence to the correct semantic slot; ambiguous/displaced slot is insufficient.','condition':'Preserved includes no applicable condition; omitted_or_changed only for relevant qualification/condition.','conflict':'Relevant source disagreement, not merely candidate contradiction or unrelated conflict.'},same_parser_blindspot='C003 should be text-supported despite incorrect original-PDF email. Never count rejection as successful semantic recovery without independent evidence; report source-fidelity limitation separately.',scope_limitations=['No fresh evaluation, random sampling, statistical independence or national generalization.','Excerpts are reviewer-scoped to the named notice; target segmentation is not evaluated.','C004 material scope is initial announced hearing dates only; separate extension conditions are tested by C012.','Related cases deliberately share evidence; report paired case families, not independent trials.','Submission-email risk is newly scoped here; do not retroactively change round2 gate.','Labels independent of model execution, but challenge reviewer also collected held-out sources and reviewed earlier OpenRouter results.','No paid calls, network lookups, or original-source edits.'],review_status='Primary adopted all independent pre-run audit amendments; ready for freeze. Labels are agent judgments, not human gold.',label_history='evaluation-only.pre-review.jsonl',model_only_denominator_note='C007 is deterministic abstention; retain in scheduled system metrics.',ambiguous_case_note='C016 excluded from primary determinate error/gate accuracy; provisional labels and accepted alternative retained.'))
dump(O/'source-dependencies.json',dependencies)
counts=dict(collections.Counter(l['candidate_origin'] for l in labels));dump(O/'validation.json',dict(passed=True,cases=16,origin_counts=counts,correct_controls=sum(l['candidate_origin']=='correct_control' for l in labels),limitation_cases=1,exact_runtime_evidence_spans=True,source_spans_match_retained_artifacts=True,runtime_contains_no_labels_or_provenance=True,all_source_images_reviewed=True,source_dependencies=len(dependencies),diagnostic_frozen_files_unchanged=141,heldout_frozen_files_unchanged=127,provider_calls=0))
dump(O/'manifest.json',dict(status='developmental_inputs_ready_for_primary_freeze',files={n:sha(O/n) for n in ['runtime.jsonl','evaluation-only.jsonl','contract.json','source-dependencies.json','validation.json','build.py','evaluation-only.pre-review.jsonl','evaluation-only.pre-final-audit.jsonl','review-amendments.json']},cases=16))
print(json.dumps(json.loads((O/'validation.json').read_text())))
