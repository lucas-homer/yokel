#!/usr/bin/env python3
"""Verify and freeze source-only collection. No pipeline, model, OCR or labels calls."""
import json,hashlib,subprocess,datetime,re,math,shutil
from pathlib import Path
from collections import Counter
from pypdf import PdfReader
from PIL import Image
ROOT=Path(__file__).resolve().parent
ROUND=ROOT.parent
POP=Path('/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/poppler/bin')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def get(p):return json.loads(p.read_text())
def files(d):return [{'path':str(p.relative_to(ROOT)),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(d.rglob('*')) if p.is_file()]
assert not (ROOT/'source-collection.READY.json').exists()
base=get(ROOT/'source-inputs.json'); extra=get(ROOT/'continuation-retained.json'); docs=base['documents']+extra
assert len(docs)==8 and len({d['document_id'] for d in docs})==8
manifest={'schema_version':'round4.sources.v1','documents':docs}
keys={'document_id','channel','text_path','text_sha256','pdf_path','pdf_sha256','pdf_pages','scope','native_page_map_known'}
prior=get(ROOT/'dedup-inventory.json'); inventory_text=(ROOT/'dedup-inventory.json').read_text()
freeze=get(ROUND/'execution/freeze-A.json')
for rec in freeze['files']:
 if rec['path']=='sources/search-access-ledger.jsonl':continue # Frozen empty ledger is explicitly appendable.
 p=ROUND/rec['path'];assert sha(p)==rec['sha256'],str(p)
prep=get(ROOT/'prep-manifest.json')
for name,expected in prep['files'].items():
 if name!='search-access-ledger.jsonl':assert sha(ROOT/name)==expected,name
assert sha(ROOT/'prep-manifest.json')=='42346fbed3f2f7b4e926075af22a1f16deb9016c03a4b091614cef3463f2656c'
receipt=get(ROOT/'freeze-receipt.json')
assert sha(ROUND/'execution/freeze-A.json')==receipt['freeze_sha256']
assert sha(ROUND/'runtime/implementation-pins.READY.json')==receipt['runtime_pin_sha256']
assert sha(ROUND/'pipeline/source-input.schema.json')==prep['source_input_contract_sha256']
versions={t:subprocess.run([str(POP/t),'-v'],capture_output=True,check=True).stderr.decode().splitlines()[0] for t in ['pdfinfo','pdffonts','pdfimages','pdftotext','pdftoppm']}
assert all('26.05.0' in x for x in versions.values())
metadata=[]
for d in docs:
 assert set(d)==keys and d['channel']=='native' and d['scope']=='full_notice' and d['native_page_map_known'] is True
 folder=ROOT/'documents'/d['document_id']; prov=get(folder/'provenance.json'); text=(ROOT/d['text_path']).read_bytes(); native=text.decode('utf-8')
 original=folder/'original.pdf'; inp=ROOT/d['pdf_path']; pdf=PdfReader(inp)
 assert sha(original)==sha(inp)==d['pdf_sha256'] and sha(ROOT/d['text_path'])==d['text_sha256']
 assert d['pdf_sha256'] not in inventory_text
 assert native.strip() and '\ufffd' not in native and len(native)<=30000 and native.count('\f')==len(pdf.pages)==d['pdf_pages']
 assert original.stat().st_size<=25000000
 replay=subprocess.run([str(POP/'pdftotext'),'-layout','-enc','UTF-8',str(inp),'-'],capture_output=True,check=True)
 assert replay.stdout==text, d['document_id']+' native differs from exact pinned command'
 images=sorted(folder.glob('page-*.png'),key=lambda p:int(re.search(r'page-(\d+)',p.name).group(1)))
 assert len(images)==len(pdf.pages)
 renders=[]
 for i,(im,page) in enumerate(zip(images,pdf.pages),1):
  with Image.open(im) as pic:
   dims=pic.size;pic.verify()
  w,h=float(page.mediabox.width),float(page.mediabox.height)
  if page.rotation in [90,270]:w,h=h,w
  expected=(math.ceil(w/72*150),math.ceil(h/72*150))
  assert all(abs(a-b)<=1 for a,b in zip(dims,expected)), (im,dims,expected)
  renders.append({'page':i,'path':str(im.relative_to(ROOT)),'sha256':sha(im),'pixels':list(dims),'expected_pixels_at_150_dpi':list(expected)})
 metadata.append({'document_id':d['document_id'],'state':prov['state'],'source_stratum':prov['stratum'],'query_id':prov['query_id'],'query_stratum':'general_comment','publisher_url':prov['retrieval_url'],'notice_identity':prov.get('notice_identity',prov.get('boundary_evidence')),'boundary_evidence':prov['boundary_evidence'],'prior_notice_identity_duplicate':False,'dedup_evidence':prov.get('dedup_evidence',prov.get('deduplication_basis',prov.get('deduplication'))),'source_uncertainty':prov.get('source_uncertainty'),'native_codepoints':len(native),'native_bytes':len(text),'formfeed_count':native.count('\f'),'pdf_pages':len(pdf.pages),'native_exact_command_reverified':True,'original_equals_input':True,'native_eligible':True,'render_dpi':150,'rendered_pages':renders,'provenance_path':str((folder/'provenance.json').relative_to(ROOT)),'artifact_files':files(folder)})
counts=Counter(m['state'] for m in metadata); strata=Counter(m['source_stratum'] for m in metadata)
assert len(counts)>=6 and max(counts.values())<=2 and sum(d['pdf_pages'] for d in docs)<=40
assert strata=={'general_comment':6,'conditional_control':2}
# Only now finalize the unfrozen runtime manifest; preserve the corrected base history.
shutil.copyfile(ROOT/'source-inputs.json',ROOT/'source-inputs.pre-finalization.json')
put(ROOT/'source-inputs.json',manifest)
put(ROOT/'source-inputs.READY.json',manifest)
put(ROOT/'source-metadata.READY.json',{'schema_version':'round5.source-metadata.v1','status':'READY','tools':versions,'documents':metadata})
old=[json.loads(x) for x in (ROOT/'search-access-ledger.jsonl').read_text().splitlines()]
new=[json.loads(x) for x in (ROOT/'continuation-events.jsonl').read_text().splitlines()]
queryplan=get(ROOT/'search-plan.json')['queries'];queries=[];candidates=[]
for q in queryplan:
 qid=q['query_id']; executed=int(qid[1:])<=12
 raw=ROOT/(qid+'-search.raw.json')
 if not raw.exists():raw=ROOT/(qid+('-search.txt' if qid=='Q01' else '-search.json'))
 queryrec={**q,'executed':executed,'status':'resolved' if executed else 'skipped_success_stop','actual_query_status':'exact_frozen_query' if 4<=int(qid[1:])<=12 else ('reported_filter_omission_unresolved_Q03_conflict' if executed else 'not_submitted')}
 if executed:
  queryrec.update(raw_result_path=str(raw.relative_to(ROOT)),raw_result_sha256=sha(raw),timezone='UTC',timestamp_evidence='in raw result or original ledger; Q02 exact seconds unavailable',metadata_complete=qid!='Q02')
 queries.append(queryrec)
 if not executed:continue
 for n in range(1,4):
  legacy=[x for x in old if x.get('event')=='candidate_disposition' and x.get('query_id')==qid and x.get('candidate_order',x.get('result_rank'))==n]
  contemporary=[x for x in new if x.get('query_id')==qid and x.get('candidate_order')==n and x.get('event') in ['candidate_excluded','candidate_retained']]
  events=legacy+contemporary;assert events,(qid,n)
  selected=events[-1]
  rec={'query_id':qid,'candidate_order':n,'state':q['state'],'url':selected.get('candidate_url',selected.get('retrieval_url')),'decision':'retain' if selected.get('event')=='candidate_retained' or selected.get('decision')=='retain' else 'exclude','reason':selected.get('reason',selected.get('decision_reason','complete eligible original with source boundaries and provenance')),'evidence_records':events}
  if qid=='Q03' and n==1:rec.update(decision='exclude',reason='Pre-freeze correction: 32481 native codepoints exceeds frozen 30000 limit; earlier retained evidence preserved.',correction_path='native-size-correction.json')
  matches=[m for m in metadata if m['publisher_url']==rec['url']]
  if matches:rec['retained_document_id']=matches[0]['document_id']
  candidates.append(rec)
assert len(candidates)==36 and sum(c['decision']=='retain' for c in candidates)==8
# Convert full raw tool returns into structured displayed result metadata without new searches.
returns={}
for qid in ['Q01',*[f'Q{i:02d}' for i in range(5,13)]]:
 p=ROOT/(qid+'-search.txt' if qid=='Q01' else qid+'-search.raw.json')
 raw=p.read_text() if qid=='Q01' else get(p)['raw_tool_result']
 rows=[]
 for rank,match in enumerate(re.finditer(r'([^\n]+) \((https?://[^\n]+)\)\n',raw),1):
  rows.append({'display_order':rank,'title':match.group(1),'url':match.group(2)})
 returns[qid]=rows
 for c in candidates:
  if c['query_id']==qid:
   match=next((x for x in rows if x['url']==c['url']),None)
   c['displayed_result']=match
put(ROOT/'search-results-index.READY.json',{'result_order_rule':'Displayed order, not numeric tool citation IDs. Q02 original result_rank values 12–14 were citation/result identifiers; candidate order 1–3 is preserved and full Q02 result metadata is unavailable. Q03/Q04 structured returns are preserved in original files.','raw_return_index':returns})
deviations=[
 'Primary reported Q01–Q03 submitted query strings omitted trailing filetype:pdf. Original ledger/prep describe planned strings. Q03 child transcript was reported visibly to include filetype:pdf: conflicting evidence remains unresolved. No rerun or substitution; exact first-three adherence for those histories is not certified.',
 'Q02 retained metadata is partial (7 observed of 17 returned results); exact execution seconds unavailable. Numeric result_rank 12–14 in original ledger are not reliably displayed rank; candidate_order 1–3 records are preserved.',
 'Collector initially retained Kentucky doc-cdc84f3180fe with 32481 native codepoints. Frozen 30000 limit applied before source freeze; complete artifacts and earlier manifest retained as excluded evidence. Primary clarification superseded four-slot math with corrected three eligible/12-page base and five remaining slots, at least four new states, three general plus two controls. Q03 third candidate was not revisited.',
 'Michigan source is an official Supreme Court proposed rule order rather than an executive agency notice; protocol did not exclude judicial rulemaking.',
 'Both controls were encountered in planned general queries: New Mexico event-relative hearing-close cutoff and Connecticut expressly conditional comment extension. Categories determined from original source before outputs; no evaluation labels or output filtering.',
 'New Mexico PRC notice has inconsistent docket caption/footer (23-00119-UT versus 23-00188-UT); preserved without repair. Connecticut form prints Page 2 of 2 on both pages. Ohio inorganic notice includes literal LINK placeholders; all unchanged.',
 'Original prep records remain PREPARED/AWAITING historical snapshots. New READY files certify final collection only; original search ledger and continuation history preserved.',
 'Q11 three access failures each had one ordinary retry; no bytes/HTTP headers available from web fetch failure. Excluded as access failures, not search-snippet source evidence.'
]
audit={'schema_version':'round5.source-collection-audit.v1','status':'READY_WITH_DISCLOSED_DEVIATIONS','completed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'target_achieved':True,'stop_point':'Q12 candidate 3; stopped immediately after eighth eligible retention','retained_count':8,'input_pages':22,'state_counts':dict(counts),'strata_counts':dict(strata),'queries_executed':12,'queries_skipped_after_success':12,'bounded_candidates_resolved':36,'candidate_dispositions':candidates,'query_execution':queries,'deviations':deviations,'selection_basis':'Frozen sequential candidate queue; original source type, scope, native eligibility, state/stratum/page budgets and prior dedup only. No output-informed selection.','bias_notes':['Native-only corpus excludes scans and over-30000 native inputs.','Complete individual publisher distribution excludes multi-notice registers and mixed packets.','Frozen search rank and sequential quotas limit coverage; no random sample or population representativeness claim.','Control coverage is conditional/relative only; no negative-lifecycle notice retained before success stop.','Repeated Ohio publisher template retained for distinct proceedings; New Mexico same publisher different issuers.'], 'prior_round_dedup':{'notice_inventory_count':40,'distinct_original_hashes':36,'retained_hash_matches':0,'retained_notice_identity_matches':0,'identity_evidence':'Manual issuer/title/rule/docket/source/date comparisons recorded per retained provenance and consolidated metadata. Source uncertainties retained.'},'native_verification':{'exact_pinned_extraction_replay_equal':8,'all_valid_nonempty_UTF8':True,'replacement_characters':0,'all_within_30000_codepoints':True,'all_formfeed_counts_equal_pdf_pages':True,'all_originals_identical_to_inputs':True,'all_22_png_pages_verified_at_150_dpi':True},'forbidden_calls':{'pipeline':0,'model':0,'provider':0,'OCR':0,'proposer':0,'labels':0},'immutable_verification':{'freeze_inventory_files':len(freeze['files']),'immutable_freeze_files_reverified':len(freeze['files'])-1,'appendable_ledger_exception':'sources/search-access-ledger.jsonl was empty at freeze; collection events preserved' ,'freeze_A_sha256':sha(ROUND/'execution/freeze-A.json'),'implementation_pins_sha256':sha(ROUND/'runtime/implementation-pins.READY.json'),'prep_manifest_sha256':sha(ROOT/'prep-manifest.json'),'schema_sha256':sha(ROUND/'pipeline/source-input.schema.json'),'prep_artifact_hashes_preserved_except_appendable_ledger':True},'tools':versions}
put(ROOT/'collection-audit.READY.json',audit)
md='# Round 5 source collection audit\n\nEight eligible complete original notices from Kentucky, Ohio, Michigan, New Mexico, Connecticut, and South Dakota; 22 input pages; six general notices and two conditional/relative controls. Stopped at Q12 candidate 3. Q13–Q24 were not submitted.\n\nAll exact original/input hashes match, all native inputs replay identically under pinned pdftotext 26.05.0 with -layout -enc UTF-8, all are valid nonempty UTF-8 within 30000 codepoints, and all 22 rendered pages match 150 DPI dimensions. Prior inventory comparisons found no original or underlying-notice duplication. No pipeline, model, provider, OCR, proposer or labels calls.\n\n## Disclosed deviations and limits\n\n'+''.join('- '+x+'\n' for x in deviations)+'\nSee collection-audit.READY.json for all 36 bounded candidate dispositions, source-metadata.READY.json for retained provenance and artifact/page hashes, and source-inputs.READY.json for the exact runtime schema. Historical counts in earlier artifacts are superseded by native-size-correction.json and this READY audit.\n'
(ROOT/'collection-audit.READY.md').write_text(md)
# READY itself is excluded from the hashed file inventory to avoid a circular hash.
bundle=files(ROOT)
put(ROOT/'source-files.READY.json',{'schema_version':'round5.source-files.v1','excluded_paths':['source-files.READY.json','source-collection.READY.json'],'files':bundle})
ready={'schema_version':'round5.source-collection-ready.v1','status':'READY_WITH_DISCLOSED_DEVIATIONS','target_achieved':True,'retained_count':8,'input_pages':22,'state_counts':dict(counts),'strata_counts':dict(strata),'stop_point':'Q12 candidate 3','source_inputs_path':'source-inputs.READY.json','source_inputs_sha256':sha(ROOT/'source-inputs.READY.json'),'runtime_source_inputs_path':'source-inputs.json','runtime_source_inputs_sha256':sha(ROOT/'source-inputs.json'),'audit_path':'collection-audit.READY.json','audit_sha256':sha(ROOT/'collection-audit.READY.json'),'metadata_path':'source-metadata.READY.json','metadata_sha256':sha(ROOT/'source-metadata.READY.json'),'file_inventory_path':'source-files.READY.json','file_inventory_sha256':sha(ROOT/'source-files.READY.json'),'authorization_freeze_sha256':receipt['freeze_sha256'],'implementation_pins_sha256':receipt['runtime_pin_sha256'],'prep_manifest_sha256':sha(ROOT/'prep-manifest.json'),'source_input_contract_sha256':prep['source_input_contract_sha256'],'collection_edits_complete':True,'runtime_execution_not_performed':True}
put(ROOT/'source-collection.READY.json',ready)
print(json.dumps(ready,indent=2));print('READY sha256',sha(ROOT/'source-collection.READY.json'))
