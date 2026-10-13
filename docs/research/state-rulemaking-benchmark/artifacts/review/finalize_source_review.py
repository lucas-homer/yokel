from pathlib import Path
import json,hashlib,collections
R=Path('/private/tmp/docketclock-expanded-benchmark-2026-10-05/review'); ROOT=R.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
a=json.loads((R/'source-annotation-audit.json').read_text());c=json.loads((R/'corpus-audit.json').read_text())
assert a['freeze_ready'] and a['reviewed_units']==20 and all(c['quota_checks'].values())
checks=[];clusters=[];frozen=[]
def add(p,kind):frozen.append({'path':str(p),'kind':kind,'sha256':sha(p)})
reviewer_templates={'A04':'WA-CRO-withdrawal-letter','A05':'WA-register-withdrawal','A06':'CA-CDFW-standalone-notice','A07':'CA-DMV-modification-notice','A08':'CA-CDFW-standalone-notice'}
issues={'A04':'WA-2025-08','A05':'WA-2026-16','A09':'NY-2026-39','A10':'NY-2026-39','B01':'MA-1542','B02':'MA-1542','B04':'NC-41-01','B05':'TX-2026-05-22','B06':'TX-2026-05-22','B07':'TX-2026-06-05','B08':'CO-49-17','B09':'CO-49-16','B10':'CO-49-17'}
for u in a['units']:
 k=u['fixture_id'];s=Path(u['expected_source_directory']);d=json.loads((s/'fixture.json').read_text());p=Path(u['adjudicated_annotation_path']);j=json.loads(p.read_text())
 assert sha(s/'fixture.json')==u['collector_annotation_hash']==j['collector_annotation_hash']
 assert sha(p)==u['adjudicated_annotation_hash']
 assert sha(s/'original.pdf')==u['original_sha256'] and sha(s/'input.pdf')==u['input_sha256']
 assert Path(j['collector_snapshot']).read_bytes()==(s/'fixture.json').read_bytes()
 assert len(u['field_audits'])==len(j['reference_fields'])==len(d['reference_fields'])
 assert len(u['reviewed_page_records'])==u['input_page_count']
 assert all(f['final_status']=='source_review_complete' for f in u['field_audits'])
 assert len({f['field_id'] for f in j['reference_fields']})==len(j['reference_fields'])
 for f in j['reference_fields']:
  assert f['input_page'] in range(1,u['input_page_count']+1)
  assert f['original_page']==u['original_physical_pages'][f['input_page']-1]
  assert f['semantic_group_id'] and f['decisive_evidence'] and f['notice_scope_boundaries']
  if f['answerability']=='not_stated':assert f['absence_scope_if_applicable']
 for rec in u['reviewed_page_records']:
  q=Path(rec['rendered_image_path']);assert sha(q)==rec['rendered_image_sha256'];assert rec['complete_page_viewed'] and rec['continuation_checked'] and rec['neighboring_notice_boundaries_checked'];add(q,'visually reviewed rendered input page')
 for name in ['original.pdf','input.pdf','fixture.json']:add(s/name,'collector source artifact')
 add(p,'adjudicated reference');add(Path(j['collector_snapshot']),'unaltered collector reference snapshot')
 clusters.append({'fixture_id':k,'original_pdf_id':u['original_sha256'],'input_sha256':u['input_sha256'],'original_physical_pages':u['original_physical_pages'],'register_issue_id':issues.get(k),'collector_shared_original_group':d.get('shared_original_group'),'template_family_id':d.get('template_family') or d.get('template_group') or reviewer_templates[k],'template_basis':'collector annotation' if d.get('template_family') or d.get('template_group') else 'reviewer grouping of visually inspected forms/notices','agency':j['agency_reference']})
 checks.append({'fixture_id':k,'hashes_match':True,'all_page_images_recorded_and_unchanged':True,'all_fields_and_page_locators_consistent':True,'critical_determinate_groups':u['critical_determinate_groups'],'reference_gate_eligible':u['reference_gate_eligible']})
# Check the corrected reviewer error and substantive transcription correction explicitly.
a10=json.loads((R/'adjudicated/A10.json').read_text());f=next(f for f in a10['reference_fields'] if f['field_id']=='issue_publication_date');assert f['answerability']=='present' and f['expected_value']['date']=='2026-09-30'
a03=json.loads((R/'adjudicated/A03.json').read_text());assert '1 to S' in next(f['expected_value'] for f in a03['reference_fields'] if f['field_id']=='rule_identity')
issuecounts=collections.Counter(v['register_issue_id'] for v in clusters if v['register_issue_id']);assert max(issuecounts.values())<=2
ny=(ROOT/'source-a/A10/original.pdf').read_bytes();assert ny.find(b'%PDF')==422
assert (ROOT/'source-a/A09/input.pdf').read_bytes().startswith(b'%PDF') and (ROOT/'source-a/A10/input.pdf').read_bytes().startswith(b'%PDF')
cluster_record={'units':clusters,'distinct_original_pdfs':len({v['original_pdf_id'] for v in clusters}),'register_issue_counts':dict(issuecounts),'template_counts':dict(collections.Counter(v['template_family_id'] for v in clusters)),'page_overlap':c['overlapping_page_instances'],'ny_original_prefix_caveat':{'pdf_header_offset':422,'original_bytes_retained_unrepaired':True,'derived_input_headers_valid':True,'page_content_equivalence':'Collector validation reports unchanged mapped content streams; reviewer did not independently rerun PDF content-stream comparison.'}}
save(R/'cluster-ledger.json',cluster_record)
save(R/'source-review-validation.json',{'passed':True,'units':checks,'fields_checked':c['fields'],'page_instances':34,'distinct_original_physical_pages':33,'absence_recheck_page_instances':sum(u['input_page_count'] for u in a['units'] if any(p['absence_scope_rechecked_original_detail_after_primary_correction'] for p in u['reviewed_page_records'])),'new_vendor_outputs_inspected':False,'collector_files_modified':False,'limitation':'Automated validation checks consistency/hashes, not semantic truth. Semantic judgments come from documented visual review and retained primary correction.'})
protocol=Path(json.loads((R/'scoring-contract.json').read_text())['protocol_path'])
assert sha(protocol)==a['protocol_sha256'];add(protocol,'accepted protocol')
for q in sorted((R/'superseded-pre-freeze').glob('*')):add(q,'superseded pre-freeze reviewer history; not scoring reference')
for lane in ['source-a','source-b']:
 add(ROOT/lane/'collection-validation.json','collector validation relied upon')
for name in ['SOURCE-REVIEW.md','source-annotation-audit.json','corpus-audit.json','adjudications.json','independent-source-notes.json','reviewer-primary-disagreements.json','cluster-ledger.json','source-review-validation.json','scoring-contract.json','acceptance.json','collector-readiness-confirmation.json','build_source_audit.py','finalize_source_review.py']:
 add(R/name,'reviewer artifact')
save(R/'source-review-hash-manifest.json',{'status':'ready for primary freeze; this manifest records source-only reviewed versions','new_vendor_outputs_inspected':False,'entries':frozen})
print(json.dumps({'ready_to_freeze':True,'reviewed_units':20,'reviewed_fields':174,'pages':34,'reference_eligible_units':19,'reference_insufficient_units':['A07'],'hashes':{name:sha(R/name) for name in ['source-review-hash-manifest.json','source-annotation-audit.json','scoring-contract.json','adjudications.json','source-review-validation.json']}},indent=2))
