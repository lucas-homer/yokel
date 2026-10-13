"""Exact-span bookkeeping for manual source-image/annotation-Markdown reviews."""
from pathlib import Path
import json,hashlib,collections
O=Path(__file__).resolve().parent;B=O.parents[2];R=B/'artifacts';P=O.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):return [json.loads(s) for s in p.read_text().splitlines()]
def save(n,x):(O/n).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in x))
freeze=json.loads((R/'corpus-freeze.json').read_text());units={u['fixture_id']:u for u in freeze['units']};arm='openrouter_mistral_ocr';fields=[];docs=[];extras=[];ops=[];attempts=[]
for typ,dest in [('field',fields),('document',docs)]:
 for r in rows(R/f'review/results-v1/{typ}-scores.jsonl'):
  if r['arm']!='native':continue
  r.update(arm=arm,evaluation_version='round2-diagnostic-openrouter-review-v1',evaluation_status='pending',operation_status=None,output_artifact=None,output_artifact_hash=None,scope_coverage='not_assessable',execution_interface='openrouter_file_parser',cohort='diagnostic')
  if typ=='field':r.update(outcome=None,reason_code=None,output_locator=None,exact_output_quote=None,omission_scope=None,decisive_relation_preserved=False,field_gate_pass=False,adjudication_note='Awaiting canonical output/manual review.',absence_evidence_checked=None,reviewer_id='review-b-agent')
  else:r.update(gate_outcome=None,critical_field_counts={},critical_group_counts={},extra_assertion_audit_complete=False,critical_extra_assertion_ids=[],failure_categories=[],reviewer_note='Awaiting canonical output/manual review.')
  dest.append(r)
judgments=json.loads((O/'judgments.json').read_text());assert len({j['fixture_id'] for j in judgments})==len(judgments)
for j in judgments:
 k=j['fixture_id'];u=units[k];cp=P/'runs'/k/'capture.json';c=json.loads(cp.read_text());p=cp.parent/'output.md';t=p.read_text();ls=t.splitlines(keepends=True)
 assert c['phase']=='completed' and c['parse_output_usable'] and t.strip();assert c['input_sha256']==u['input_sha256'] and c['input_pages']==u['input_page_count'];assert c['output_sha256']==sha(p);assert c['response_sha256']==sha(cp.parent/'response.json')
 sm=json.loads((cp.parent/'serialization-map.json').read_text());ann=json.loads((cp.parent/'annotations.json').read_text())
 def ptr(v,path):
  for token in path.strip('/').split('/'):
   token=token.replace('~1','/').replace('~0','~');v=v[int(token)] if isinstance(v,list) else v[token]
  return v
 parts=[]
 for part in sm['parts']:
  value=ptr(ann,part['annotation_pointer']);assert t[part['start_character']:part['end_character']]==value;parts.append(value)
 assert sm['separator'].join(parts)==t and sm['downstream_completion_scored'] is False and sm['images_scored'] is False
 assert sorted(j['source_pages_viewed'])==list(range(1,u['input_page_count']+1));assert j['notice_wide_extra_assertion_audit_complete']
 ref=json.loads((R/u['reference_path']).read_text());refmap={f['field_id']:f for f in ref['reference_fields']};assert set(j['ranges'])==set(refmap)
 def quote(span):
  a,b=span;assert 1<=a<=b<=len(ls);start=sum(map(len,ls[:a-1]));end=sum(map(len,ls[:b]));return t[start:end],dict(line_start=a,line_end=b,char_start=start,char_end=end)
 for r in [x for x in fields if x['fixture_id']==k]:
  fid=r['field_id'];f=refmap[fid];span=j['ranges'][fid];q,loc=quote(span) if span else (None,None);out='not_assessable' if f['answerability']=='uncertain' else 'safe_abstention' if f['answerability']=='not_stated' else 'supported';reason='reference_uncertainty' if out=='not_assessable' else 'complete_scope_preserves_absence' if out=='safe_abstention' else 'value_and_decisive_role_preserved';scope='complete';note='Complete source-page images and target annotation Markdown inspected; decisive value/role/scope preserved. Chat completion and image/JSON sidecars do not rescue missing Markdown evidence.';omission=None
  if out=='safe_abstention':omission='Requested value absent from preserved complete scope: '+f['absence_scope_if_applicable']
  if out=='not_assessable':note='Frozen critical source conflict remains unresolved; reproducing contradictory source values is not a parser error.'
  e=j.get('exceptions',{}).get(fid)
  if e:out=e['outcome'];reason=e['reason_code'];scope=e.get('scope_coverage','partial');note=e['note'];omission=e.get('omission_scope')
  r.update(evaluation_status='complete',operation_status='completed_nonempty',outcome=out,reason_code=reason,scope_coverage=scope,output_artifact=str(p.relative_to(B)),output_artifact_hash=sha(p),output_locator=loc,exact_output_quote=q,omission_scope=omission,decisive_relation_preserved=out in ['supported','safe_abstention'],field_gate_pass=(out=='supported' and r['answerability'] in ['present','explicit_negative']) or (out=='safe_abstention' and r['answerability']=='not_stated' and scope=='complete'),adjudication_note=note,absence_evidence_checked=out=='safe_abstention' if r['answerability']=='not_stated' else None,source_input_artifact='artifacts/'+u['directory']+'/input.pdf',source_image_artifacts=[dict(path='artifacts/'+u['directory']+f'/page-{n}.png',sha256=sha(R/u['directory']/f'page-{n}.png')) for n in j['source_pages_viewed']])
 criticalids=[]
 for e in j.get('extra_assertions',[]):
  q,loc=quote(e['range']);aid=k+'-'+e['id'];row=dict(assertion_id=aid,fixture_id=k,arm=arm,cohort='diagnostic',assertion_text=q,output_artifact=str(p.relative_to(B)),output_artifact_hash=sha(p),output_locator=loc,source_scope=e['source_scope'],error_type=e['error_type'],critical=e['critical'],reason=e['reason'],affected_field_ids=e.get('affected_field_ids',[]));extras.append(row)
  if e['critical']:criticalids.append(aid)
 crit=[r for r in fields if r['fixture_id']==k and r['critical']];groups={g:all(r['field_gate_pass'] for r in crit if r['semantic_group_id']==g) for g in {r['semantic_group_id'] for r in crit}};d=next(x for x in docs if x['fixture_id']==k)
 d.update(evaluation_status='complete',operation_status='completed_nonempty',output_artifact=str(p.relative_to(B)),output_artifact_hash=sha(p),gate_outcome='insufficient_reference' if not d['reference_gate_eligible'] else 'pass' if all(r['field_gate_pass'] for r in crit) and not criticalids else 'content_fail',scope_coverage='partial' if any(r['scope_coverage']=='partial' for r in crit) else 'complete',critical_field_counts=dict(collections.Counter(r['outcome'] for r in crit)),critical_group_counts={'total':len(groups),'pass':sum(groups.values()),'nonpass':len(groups)-sum(groups.values())},extra_assertion_audit_complete=True,critical_extra_assertion_ids=criticalids,failure_categories=sorted({r['reason_code'] for r in crit if not r['field_gate_pass']}|({'critical_extra_assertion'} if criticalids else set())),reviewer_note=j['reviewer_note'])
for k,u in units.items():
 cp=P/'runs'/k/'capture.json'
 if not cp.exists():continue
 c=json.loads(cp.read_text());ops.append(dict(fixture_id=k,arm=arm,cohort='diagnostic',capture_artifact=str(cp.relative_to(B)),capture_sha256=sha(cp),canonical_capture=c,content_representation_scored='output.md serialized annotation text only',version_limitation='mistral-ocr engine alias; downstream model/provider do not identify OCR backend version',serialization_map_sha256=sha(cp.parent/'serialization-map.json') if (cp.parent/'serialization-map.json').exists() else None,parse_wrapper_separated=True))
 if c.get('phase')=='completed' and not c.get('parse_output_usable'):
  for r in [x for x in fields if x['fixture_id']==k]:r.update(evaluation_status='complete',operation_status='provider_error',outcome='not_assessable',reason_code='canonical_parse_unusable',scope_coverage='none',omission_scope='No usable canonical parser annotation text.',adjudication_note='Operational failure; not scored as missing or safe abstention.')
  d=next(x for x in docs if x['fixture_id']==k);d.update(evaluation_status='complete',operation_status='provider_error',gate_outcome='operational_unusable',scope_coverage='none',failure_categories=['canonical_parse_unusable'])
for cp in sorted((P/'rejected-attempts').glob('*/capture.json')):attempts.append(dict(capture_artifact=str(cp.relative_to(B)),capture_sha256=sha(cp),capture=json.loads(cp.read_text()),canonical=False,reason='Historical explicit rejection retained; authorized successful recovery is separate canonical attempt.'))
for n,x in [('field-scores.jsonl',fields),('document-scores.jsonl',docs),('extra-assertions.jsonl',extras),('operation-records.jsonl',ops),('rejected-attempt-records.jsonl',attempts)]:save(n,x)
for r in fields+extras:
 q=r.get('exact_output_quote',r.get('assertion_text'))
 if q is not None:
  text=(B/r['output_artifact']).read_text();loc=r['output_locator'];assert text[loc['char_start']:loc['char_end']]==q
for path,m in freeze['files'].items():assert sha(R/path)==m['sha256'],path
v=dict(passed=True,scheduled_documents=len(docs),completed_documents=sum(d['evaluation_status']=='complete' for d in docs),scheduled_fields=len(fields),completed_fields=sum(r['evaluation_status']=='complete' for r in fields),critical_extra_assertions=sum(e['critical'] for e in extras),frozen_files_unchanged=len(freeze['files']),exact_quotes_valid=True,annotation_serialization_verified_for_reviewed_outputs=True,canonical_operations=len(ops),rejected_attempts_preserved=len(attempts));(O/'validation.json').write_text(json.dumps(v,indent=2)+'\n');(O/'findings.json').write_text(json.dumps(dict(validation=v,gate_counts=dict(collections.Counter(d['gate_outcome'] for d in docs if d['evaluation_status']=='complete')),field_counts=dict(collections.Counter(r['outcome'] for r in fields if r['evaluation_status']=='complete')),documents=[d for d in docs if d['evaluation_status']=='complete']),ensure_ascii=False,indent=2)+'\n');print(json.dumps(v))
