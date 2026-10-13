"""Mechanical page retention and native extraction; no labels, models or network."""
from pathlib import Path
import json,hashlib,subprocess,shutil,re,sys
from pypdf import PdfReader,PdfWriter
O=Path(__file__).resolve().parent
BIN=Path('/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/poppler/bin')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
# Complete notice/form boundaries only; scope remains conservative for partial filing packets.
selections=[
('la-ada',[1,2,3],'general_proposed_notice','unknown',False,'LA-Register-DENR-notice-of-intent','Publisher supplied three-page register excerpt; target Open Meetings via Electronic Means begins right column of page1; preceding notice tail and other material remain. Multiple scopes, no segmentation assertion.'),
('ar-marketing',[9],'general_proposed_notice','full_notice',False,'AR-DHS-standalone-notice-in-legislative-packet','Entire one-page NOTICE OF RULEMAKING through director signature. Surrounding packet contains supporting filings and rule text; none are represented as part of the standalone notice.'),
('sc-register',[15,16],'general_proposed_notice','full_notice',False,'SC-Register-proposed-regulation','First proposed regulation in register: Document5447 starts physical15/printed8; concludes physical16/printed9; next notice begins physical17. All physical page content retained.'),
('nh-agr',[1,2,3,4],'general_proposed_notice','full_notice',False,'NH-OLS-rulemaking-notice-form','Entire standalone four-page Rulemaking Notice Form Agr2500 including fiscal impact continuation.'),
('vt-rulemaking',list(range(1,7)),'publisher_scans','slice',True,'VT-APA-final-proposed-filing','Complete six-page Final Proposed coversheet; later adopting page, analyses and rule text remain in original. Scope slice because complete filing package is larger.'),
('tn-packet',list(range(1,11)),'publisher_scans','unknown',True,'TN-GOC-rulemaking-hearing-rules-filing','Complete first agency record: staff abstract, supporting statements, filed rules and certification through physical10; next agency starts11. Mixed record components; no single-notice scope assertion.'),
('vt-emergency',list(range(1,6)),'publisher_scans','slice',True,'VT-APA-emergency-filing','Complete five-page Emergency Rule coversheet; later adopting page, analyses and rule text remain in original. Scope slice for larger filing package.'),
('tn-withdrawal',list(range(1,13)),'publisher_scans','unknown',True,'TN-GOC-rulemaking-hearing-rules-filing','First agency record is Tennessee Businesses Against Trafficking, not the withdrawal mentioned in search title. Includes complete record through physical12; next agency starts13. Multiple record components, scope unknown.'),
('id-negotiated',[90],'conditional_or_relative_language_notice','full_notice',False,'ID-Administrative-Bulletin-negotiated-notice','Complete single-page Docket62-0101-2301 notice; printed and physical90. Negotiated meetings depend on responses; no adjacent notice on retained page.'),
('hi-election',list(range(1,7)),'conditional_or_relative_language_notice','full_notice',False,'HI-Elections-proposed-rules-hearing','Entire six-page publisher notice including testimony and post-hearing relative timing; no rule attachment truncation.'),
('nj-adoption',[1],'negative_lifecycle_notice','unknown',False,'NJ-DHS-administrative-change-notice','Entire one-page publisher PDF. Standard of Need administrative change appears in right column below preceding adoption text that spans both columns. Neighbor retained; scope unknown and no target segmentation assertion.'),
]
# Final Oklahoma selection is supplied only after ordered register inspection.
extra=O/'ok-selection.json'
if extra.exists():selections.append(tuple(json.loads(extra.read_text())))
records=[];metadata=[]
old={x['original_sha256'] for x in json.loads((O/'dedup-inventory.json').read_text())['notices']}
for key,pages,stratum,scope,scan,family,boundary in selections:
 c=O/'candidates'/key;src=c/'original.pdf';m=json.loads((c/'metadata.json').read_text());reader=PdfReader(src)
 assert sha(src) not in old
 assert max(pages)<=len(reader.pages),(key,len(reader.pages),pages)
 ident='doc-'+sha(src)[:12];d=O/'documents'/ident;d.mkdir(parents=True,exist_ok=True)
 if pages==list(range(1,len(reader.pages)+1)):shutil.copyfile(src,d/'input.pdf');derivation='Unmodified publisher original'
 else:
  writer=PdfWriter()
  for page in pages:writer.add_page(reader.pages[page-1])
  with (d/'input.pdf').open('wb') as f:writer.write(f)
  derivation='pypdf page copy, no cropping, masking, rasterization, OCR, text repair or reordering'
 commands=[]
 for tool,args in [('pdftotext',['-layout',str(d/'input.pdf'),str(d/'native.txt')]),('pdftoppm',['-r','110','-png',str(d/'input.pdf'),str(d/'page')])]:
  cmd=[str(BIN/tool),*args]
  if tool=='pdftoppm' and len(list(d.glob('page-*.png')))==len(pages):
   commands.append({'command':cmd,'exit':0,'reused_same_page_render':True});continue
  r=subprocess.run(cmd,capture_output=True);(d/(tool+'.stderr')).write_bytes(r.stderr);commands.append({'command':cmd,'exit':r.returncode});assert r.returncode==0
 raw=(d/'native.txt').read_bytes();text=raw.decode('utf-8');assert text.count('\f')==len(pages),(key,'page map')
 pngs=sorted(d.glob('page-*.png'));assert len(pngs)==len(pages)
 records.append(dict(document_id=ident,channel='native',text_path=str((d/'native.txt').relative_to(O)),text_sha256=sha(d/'native.txt'),pdf_path=str((d/'input.pdf').relative_to(O)),pdf_sha256=sha(d/'input.pdf'),pdf_pages=len(pages),scope=scope,native_page_map_known=True))
 metadata.append(dict(document_id=ident,candidate_id=key,state=m['state'],source_url=m['source_url'],retrieval=m,original_path=str(src.relative_to(O)),original_sha256=sha(src),original_page_count=len(reader.pages),physical_original_pages=pages,input_pages=len(pages),scope=scope,notice_boundaries=boundary,selection_stratum=stratum,original_publisher_scan=scan,scan_classification='genuine scanned original with embedded OCR' if scan else 'born-digital; not counted as scan',scan_evidence='Full-page scan images in original PDF diagnostics; rendered body has scanning noise; native OCR contains spacing/recognition degradation.' if scan else None,template_family=family,old_original_overlap=False,old_family_overlap=False,derivation=derivation,commands=commands,native_codepoints=len(text),images=[{'path':str(p.relative_to(O)),'sha256':sha(p)} for p in pngs]))
(O/'source-inputs.json').write_text(json.dumps({'schema_version':'round4.sources.v1','documents':records},indent=2)+'\n')
(O/'source-metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
print(json.dumps({'documents':len(records),'states':sorted({x['state'] for x in metadata}),'scans':sum(x['original_publisher_scan'] for x in metadata),'input_pages':sum(x['pdf_pages'] for x in records)}))
