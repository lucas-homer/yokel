#!/usr/bin/env python3
"""Final export of the authoritative corrected cohort; source-only, no models."""
import json,math,re,subprocess
from collections import Counter
from pathlib import Path
import companion as c

def manifest_for(view):
 rows=[]
 for item in view['selected']:
  folder=c.SOURCES/item['artifact_folder'];p=c.get(folder/'provenance.json');relative=item['artifact_folder']
  rows.append({'document_id':item['document_id'],'channel':'native','text_path':relative+'/native.txt','text_sha256':p['native_sha256'],'pdf_path':relative+'/input.pdf','pdf_sha256':p['original_sha256'],'pdf_pages':item['pdf_pages'],'scope':'full_notice','native_page_map_known':True})
 assert [x['document_id'] for x in rows]==[x['document_id'] for x in view['selected']]
 return {'schema_version':'round8.sources.v1','documents':rows}

def export():
 c.gate('future');view=c.record_logical_decisions();assert not (c.ROOT/'source-collection.READY.json').exists()
 assert view['pending_candidate'] is None
 if not view['target_achieved']:assert set(c.bounds())=={f'Q{i:02d}' for i in range(1,25)},'Stop only at target or resolved Q24.'
 from pypdf import PdfReader
 from PIL import Image
 runtime=manifest_for(view);images=[];metadata=[];inv=c.get(c.SOURCES/'dedup-inventory.json');caps=c.get(c.SOURCES/'collection-protocol.json')['native_caps']
 for item,row in zip(view['selected'],runtime['documents']):
  folder=c.SOURCES/item['artifact_folder'];prov=c.get(folder/'provenance.json');raw=(folder/'native.txt').read_bytes();text=raw.decode('utf-8');pdf=PdfReader(folder/'input.pdf',strict=True)
  assert c.sha(folder/'original.pdf')==c.sha(folder/'input.pdf')==row['pdf_sha256']
  assert c.sha(folder/'native.txt')==row['text_sha256'] and len(pdf.pages)==row['pdf_pages']
  assert not c.frozen.native_reasons(text,len(pdf.pages),(folder/'input.pdf').stat().st_size,caps)
  assert subprocess.run([str(c.frozen.POP/'pdftotext'),'-layout','-enc','UTF-8',str(folder/'input.pdf'),'-'],capture_output=True,check=True).stdout==raw
  assert prov['body_coverage_verified'] is True and prov['prior_notice_identity_duplicate'] is False and prov['material_native_damage'] is False
  assert row['pdf_sha256'] not in inv['blocked_original_hashes'] and row['text_sha256'] not in inv['blocked_native_hashes'] and c.frozen.textkey(text) not in inv['blocked_normalized_text_hashes']
  pngs=sorted(folder.glob('page-*.png'),key=lambda p:int(re.search(r'page-(\d+)',p.name).group(1)));coverage=prov['body_coverage_evidence'];assert len(pngs)==len(coverage)==len(pdf.pages)
  pages=[]
  for n,(png,page,evidence) in enumerate(zip(pngs,pdf.pages,coverage),1):
   with Image.open(png) as im:size=im.size;im.verify()
   w,h=float(page.mediabox.width),float(page.mediabox.height)
   if page.rotation in [90,270]:w,h=h,w
   assert all(abs(a-b)<=1 for a,b in zip(size,[math.ceil(w/72*150),math.ceil(h/72*150)]))
   assert evidence['page']==n and evidence['image_sha256']==c.sha(png) and evidence['native_matches_visual_body'] is True and evidence['evidence']
   assert not evidence['substantive_body_present'] or evidence['native_body_present'] is True
   pages.append({'page':n,'image_path':str(png.relative_to(c.SOURCES)),'image_sha256':c.sha(png)})
  images.append({'document_id':row['document_id'],'pdf_pages':row['pdf_pages'],'pages':pages})
  metadata.append({'document_id':row['document_id'],'artifact_folder':item['artifact_folder'],'source_provenance_sha256':c.sha(folder/'provenance.json'),'state':item['state'],'stratum':item['stratum'],'native_codepoints':len(text),'input_equals_original':True,'exact_native_replayed':True,'all_pages_body_and150dpi_checked':True})
 counts={'notices':len(view['selected']),'pages':sum(x['pdf_pages'] for x in view['selected']),'states':dict(Counter(x['state'] for x in view['selected'])),'strata':dict(Counter(x['stratum'] for x in view['selected']))}
 assert counts['pages']<=40 and max(counts['states'].values(),default=0)<=2
 c.put(c.ROOT/'logical-selection.FINAL.json',view)
 for name,data in [('source-inputs.READY.json',runtime),('blinded-image-inventory.READY.json',{'schema_version':'round8.blinded-images.v1','documents':images}),('source-metadata.READY.json',{'schema_version':'round8.source-metadata.v1','documents':metadata})]:
  if name!='source-inputs.READY.json' or runtime['documents']:c.put(c.ROOT/name,data)
 audit={'schema_version':'round8.corrected-collection-audit.v1','counts':counts,'target_achieved':view['target_achieved'],'cohort_classification':'protocol-deviation corrected','physical_access_order_restored':False,'deviation':'Original Q05 candidates were omitted until after Q14; Q03 display13 was physically acquired outside corrected bounds. Preserve original source observations and replay corrected chronology before model outputs.','logical_selection_path':'reconciliation/logical-selection.FINAL.json','logical_selection_sha256':c.sha(c.ROOT/'logical-selection.FINAL.json'),'original_ledger_sha256':c.sha(c.SOURCES/'search-access-ledger.jsonl'),'correction_ledger_sha256':c.sha(c.ROOT/'correction-ledger.jsonl'),'access_ledger_sha256':c.sha(c.ROOT/'access-ledger.jsonl'),'plan_amendment_sha256':c.sha(c.ROOT/'plan-amendment.json'),'amendment_release_sha256':c.sha(c.ROOT/'amendment-release.json'),'application_parser_model_provider_OCR_labels_calls':0,'query_reruns':0}
 c.put(c.ROOT/'collection-audit.READY.json',audit);c.verify_baseline()
 files=[{'path':str(p.relative_to(c.SOURCES)),'sha256':c.sha(p),'bytes':p.stat().st_size} for p in sorted(c.SOURCES.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p not in [c.ROOT/'source-files.READY.json',c.ROOT/'source-collection.READY.json']]
 c.put(c.ROOT/'source-files.READY.json',{'files':files,'source_root':str(c.SOURCES),'excluded_paths':['reconciliation/source-files.READY.json','reconciliation/source-collection.READY.json','__pycache__']})
 names=['blinded-image-inventory.READY.json','source-metadata.READY.json','collection-audit.READY.json','logical-selection.FINAL.json','source-files.READY.json']+(['source-inputs.READY.json'] if runtime['documents'] else [])
 ready={'schema_version':'round8.source-collection-ready.v1','status':'PROTOCOL_DEVIATION_CORRECTED_READY' if view['target_achieved'] else 'PROTOCOL_DEVIATION_CORRECTED_BOUNDED_SHORTFALL','target_achieved':view['target_achieved'],'counts':counts,'cohort_classification':'protocol-deviation corrected','physical_access_order_restored':False,'source_root':str(c.SOURCES),'artifacts':{n:c.sha(c.ROOT/n) for n in names},'collection_edits_complete':True}
 c.put(c.ROOT/'source-collection.READY.json',ready);return ready
if __name__=='__main__':print(json.dumps(export(),indent=2))
