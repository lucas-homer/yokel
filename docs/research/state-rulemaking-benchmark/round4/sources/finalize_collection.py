from pathlib import Path
import json,hashlib,re,datetime,subprocess,collections
from pypdf import PdfReader
O=Path(__file__).resolve().parent;R=O.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def dump(n,x):(O/n).write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def event(**x):
 x['timestamp']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 with (O/'search-access-ledger.jsonl').open('a') as f:f.write(json.dumps(x)+'\n')
meta=json.loads((O/'source-metadata.json').read_text());runtime=json.loads((O/'source-inputs.json').read_text());selected={x['candidate_id']:x for x in meta}
reasons={'tn-drug':'HTTP403 in web retrieval and ordinary curl retrieval; no access-control bypass.','tn-insurance':'TLS connection failure; no PDF retrieved.','nh-adopted':'HTTP403; no bypass.','ok-occ':'HTTP404; no PDF retrieved.','hi-comment':'Public testimony submission, not an agency rulemaking notice.','sc-be':'Utility application and hearing affidavit, not a rulemaking notice.','nj-proposal':'General stratum already filled by earlier eligible candidates; retained unused, not replaced based on parser outcomes.','de-proposed':'General stratum already filled by earlier eligible candidates; retained unused.','ok-negative':'Later-ranked register; earlier Q041 register provided eligible lifecycle notice, so this candidate is not selected.'}
for c in sorted((O/'candidates').iterdir()):
 if not (c/'metadata.json').exists():continue
 m=json.loads((c/'metadata.json').read_text());sel=selected.get(c.name)
 event(event='notice_accepted' if sel else 'eligibility_decision',candidate_id=c.name,query_id=m['query_id'],candidate_url=m['source_url'],state=m['state'],decision='accepted' if sel else 'not_selected',reason=sel['notice_boundaries'] if sel else reasons.get(c.name,'Not selected; retained for audit.'),document_id=sel['document_id'] if sel else None)
# Returned search-result order is retained; uninspected results are not falsely called ineligible.
results=[]
for p in sorted(O.glob('Q*-search.txt')):
 headers=re.findall(r'^(.{1,250}) \((https?://[^\n]+)\)$',p.read_text(),re.M)
 for rank,(title,url) in enumerate(headers,1):
  found=[m['candidate_id'] for m in meta if m['source_url']==url]
  results.append(dict(query_id=p.stem.split('-')[0],returned_result_rank=rank,title=title,url=url,selected_candidate_ids=found,disposition='selected_direct_result' if found else 'see_candidate_and_discovery_ledger_or_not_inspected'))
dump('discovery-result-inventory.json',results)
links={'tn-drug':'https://www.tn.gov/workforce/events/2026/11/10/dfwp-public-rulemaking-hearing.html','nh-agr':'https://gc.nh.gov/rules/register/default.aspx','id-negotiated':'https://oah.idaho.gov/rulemaking-docket-no-62-0101-2301/','nj-adoption':'https://www.nj.gov/humanservices/notices/rules-and-fees/rule-adoptions/'}
dump('discovery-links.json',{'publisher_links':links,'other_access_checks':[{'url':'https://adem.alabama.gov/sites/default/files/2026-05/05-26div1and6.html','result':'HTML notice; linked PDFs are rule text/summary, not notice PDF; no synthetic conversion.'},{'url':'https://www.opers.ok.gov/proposed-rules-and-rule-impact-statements-2027/','result':'web cache miss; not selected'},{'url':'https://public.occ.ok.gov/WebLink/Docview.aspx?id=20989989','result':'JS viewer only in web tool; no original PDF available through observed link; no inferred endpoint used'}]})
versions={}
bin=Path('/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/poppler/bin')
for n in ['pdftotext','pdftoppm','pdfinfo','pdfimages','pdffonts']:
 r=subprocess.run([str(bin/n),'-v'],capture_output=True,text=True);versions[n]={'path':str(bin/n),'version_output':r.stderr+r.stdout,'exit':r.returncode}
import pypdf
versions['pypdf']=pypdf.__version__;dump('tool-versions.json',versions)
for rec in runtime['documents']:
 assert set(rec)=={'document_id','channel','text_path','text_sha256','pdf_path','pdf_sha256','pdf_pages','scope','native_page_map_known'}
 assert sha(O/rec['pdf_path'])==rec['pdf_sha256'];assert sha(O/rec['text_path'])==rec['text_sha256']
 assert len(PdfReader(O/rec['pdf_path']).pages)==rec['pdf_pages']
 assert (O/rec['text_path']).read_text().count('\f')==rec['pdf_pages']
for m in meta:
 assert sha(O/m['original_path'])==m['original_sha256']
 assert len(m['images'])==m['input_pages']
 for im in m['images']:assert sha(O/im['path'])==im['sha256']
old={x['original_sha256'] for x in json.loads((O/'dedup-inventory.json').read_text())['notices']}
assert not old.intersection(x['original_sha256'] for x in meta)
assert len({x['original_sha256'] for x in meta})==12
for f in json.loads((R/'execution/freeze-A.json').read_text())['files']:
 if f['path'].startswith('sources/'):assert sha(R/f['path'])==f['sha256']
counts=collections.Counter(x['selection_stratum'] for x in meta);pages=sum(x['input_pages'] for x in meta);assert pages<=60
caveats=['Purposive bounded web-search sample; not random or nationally representative.','Four real scans are concentrated in two states and related filing families: two Vermont APA filings and two Tennessee GOC packets. They are distinct originals and distinct filings, but not four independent layout families.','Scans have embedded publisher OCR; this collection does not establish performance on image-only PDFs with no text layer.','Vermont cover forms are complete but larger rulemaking packages remain in original PDFs; runtime scope slice. Tennessee first-agency records retain complete supporting components and runtime scope unknown.','Louisiana, New Jersey and Oklahoma retain neighboring notices and runtime scope unknown; no target segmentation certification.','General-stratum quota was filled before later New Jersey and Delaware candidates; unused originals retained. No native-length exclusions or parser-success replacement occurred.','All48 planned searches were executed before queued-candidate downloads/inspection finished. This departs from a literal immediate-stop reading of the48-query ceiling; no unlisted queries or additional query rounds were used. Primary should review this collection-order deviation before freeze.','Search result order is recorded as returned; not every result was opened. First notice/form within each selected packet was used except the explicitly linked Idaho notice and the complete Arkansas notice within its supporting packet. Page selection is reviewer boundary work and is not a test of automatic register segmentation.','Native extraction, original PDF diagnostics and rendering ran locally; no OCR/parser-provider or model calls.']
dump('collection-audit.json',{'status':'ready_for_primary_freeze_with_disclosed_selection_caveats','documents':12,'states':sorted({m['state'] for m in meta}),'state_count':len({m['state'] for m in meta}),'publisher_scans':4,'synthetic_scans':0,'input_pages':pages,'distinct_original_pdfs':12,'old_original_overlap':0,'strata':dict(counts),'scope_counts':dict(collections.Counter(x['scope'] for x in meta)),'prepared_queries':48,'executed_queries':48,'downloaded_candidate_attempts':len(list((O/'candidates').glob('*/metadata.json'))),'runtime_labels_present':False,'all_input_page_images_retained':True,'native_page_maps_verified':True,'frozen_preparation_files_unchanged':True,'native_length_exclusions':0,'provider_calls':0,'pipeline_calls':0,'quota_shortfalls':[],'caveats':caveats,'boundary_visual_review':['boundary-review-1.png','boundary-review-2.png','boundary-review-3.png'],'scan_visual_review':['candidates/vt-rulemaking/preview.png','candidates/vt-emergency/preview.png','candidates/tn-packet/preview.png','candidates/tn-withdrawal/preview.png']})
files={str(p.relative_to(O)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(O.rglob('*')) if p.is_file() and '__pycache__' not in str(p) and p.name not in ('READY.json','retention-manifest.json')}
dump('retention-manifest.json',{'files':files,'note':'Contains full originals, unused candidates, source-only metadata, all page images, native outputs and collection logs. Runtime reads source-inputs.json and only its listed PDF/text bytes.'})
dump('READY.json',{'status':'READY_WITH_COLLECTION_CAVEATS','runtime_manifest':'source-inputs.json','runtime_manifest_sha256':sha(O/'source-inputs.json'),'source_metadata':'source-metadata.json','source_metadata_sha256':sha(O/'source-metadata.json'),'retention_manifest':'retention-manifest.json','retention_manifest_sha256':sha(O/'retention-manifest.json'),'audit':'collection-audit.json','audit_sha256':sha(O/'collection-audit.json'),'documents':12,'states':10,'publisher_scans':4,'input_pages':52,'provider_calls':0,'pipeline_calls':0,'edits_complete':True})
print((O/'READY.json').read_text())
