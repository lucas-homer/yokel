#!/usr/bin/env python3
"""Prepared final source-only verifier/exporter; only run after primary release."""
import json,math,re,subprocess
from collections import Counter
from pathlib import Path
from pypdf import PdfReader
from PIL import Image
import importlib.util
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('collector',ROOT/'collect-native.py');collector=importlib.util.module_from_spec(spec);spec.loader.exec_module(collector)
collector.gate()
assert not (ROOT/'source-collection.READY.json').exists()
events=collector.events();items=collector.selected()
if not collector.success(items):
 for i in range(1,25):
  q=f'Q{i:02d}';records=[x for x in events if x.get('query_id')==q]
  registered=next(x for x in records if x['event']=='query_registered')
  for c in registered['bounded_candidates']:assert any(x.get('candidate_order')==c['candidate_order'] and x['event'] in ['candidate_retained','candidate_excluded'] for x in records)
# A zero-source shortfall has an audit/image inventory, but no invalid empty runtime manifest.
runtime=[];images=[];source_meta=[]
for item in items:
 doc=item['document_id'];folder=ROOT/'documents'/doc;prov=collector.get(folder/'provenance.json');native=(folder/'native.txt').read_bytes();text=native.decode('utf-8');pdf=PdfReader(folder/'input.pdf')
 assert collector.sha(folder/'original.pdf')==collector.sha(folder/'input.pdf')==prov['original_sha256']
 assert collector.sha(folder/'native.txt')==prov['native_sha256']
 assert len(pdf.pages)==item['pdf_pages'] and not collector.native_reasons(text,len(pdf.pages),(folder/'original.pdf').stat().st_size,collector.get(ROOT/'collection-protocol.json')['native_caps'])
 assert subprocess.run([str(collector.POP/'pdftotext'),'-layout','-enc','UTF-8',str(folder/'input.pdf'),'-'],capture_output=True,check=True).stdout==native
 assert prov['prior_notice_identity_duplicate'] is False and prov['original_sha256'] not in collector.get(ROOT/'dedup-inventory.json')['blocked_original_hashes']
 runtime.append({'document_id':doc,'channel':'native','text_path':f'documents/{doc}/native.txt','text_sha256':prov['native_sha256'],'pdf_path':f'documents/{doc}/input.pdf','pdf_sha256':prov['original_sha256'],'pdf_pages':len(pdf.pages),'scope':'full_notice','native_page_map_known':True})
 pngs=sorted(folder.glob('page-*.png'),key=lambda p:int(re.search(r'page-(\d+)',p.name).group(1)));assert len(pngs)==len(pdf.pages)
 pages=[]
 for n,(png,page) in enumerate(zip(pngs,pdf.pages),1):
  with Image.open(png) as image:size=image.size;image.verify()
  w,h=float(page.mediabox.width),float(page.mediabox.height)
  if page.rotation in [90,270]:w,h=h,w
  expected=[math.ceil(w/72*150),math.ceil(h/72*150)];assert all(abs(a-b)<=1 for a,b in zip(size,expected))
  pages.append({'page':n,'image_path':str(png.relative_to(ROOT)),'image_sha256':collector.sha(png)})
 images.append({'document_id':doc,'pdf_pages':len(pdf.pages),'pages':pages})
 source_meta.append({'document_id':doc,'native_codepoints':len(text),'provenance_path':str((folder/'provenance.json').relative_to(ROOT)),'provenance_sha256':collector.sha(folder/'provenance.json'),'source_state':item['state'],'source_stratum':item['stratum'],'all_pages_verified_150dpi':True,'input_equals_original':True,'exact_native_replayed':True})
state_counts=Counter(x['state'] for x in items);strata=Counter(x['stratum'] for x in items)
assert max(state_counts.values())<=2 and sum(x['pdf_pages'] for x in items)<=40
for name,value in ([('source-inputs.READY.json',{'schema_version':'round4.sources.v1','documents':runtime})] if items else [])+[('blinded-image-inventory.READY.json',{'schema_version':'round6.blinded-images.v1','documents':images}),('source-metadata.READY.json',{'schema_version':'round6.source-metadata.v1','documents':source_meta})]:collector.put(ROOT/name,value)
queries=[]
for q in collector.get(ROOT/'selection-plan.json')['queries']:
 records=[x for x in events if x.get('query_id')==q['query_id']]
 query={**q,'status':'executed' if any(x['event']=='query_registered' for x in records) else 'skipped_success_stop'}
 if query['status']=='executed':
  registered=next(x for x in records if x['event']=='query_registered')
  query['unprocessed_bounded_candidates']=[c['candidate_order'] for c in registered['bounded_candidates'] if not any(x.get('candidate_order')==c['candidate_order'] and x['event'] in ['candidate_retained','candidate_excluded'] for x in records)]
  if query['unprocessed_bounded_candidates']:assert collector.success(items)
 queries.append(query)
audit={'schema_version':'round6.collection-audit.v1','target_achieved':collector.success(items),'counts':{'notices':len(items),'pages':sum(x['pdf_pages'] for x in items),'states':dict(state_counts),'strata':dict(strata)},'queries':queries,'ledger_path':'search-access-ledger.jsonl','ledger_sha256':collector.sha(ROOT/'search-access-ledger.jsonl'),'selection_basis':'Original source scope, native/PDF/page caps, dedup, fixed sequential quotas only. No outputs/labels/substantive-field-presence filtering except source control strata.','deviations':'Collector must append any actual search/access/scope/selection deviations to ledger before invoking final freeze; do not reconstruct or erase history.','runtime_provider_model_OCR_label_calls':0,'prior_rounds_changed':False}
collector.put(ROOT/'collection-audit.READY.json',audit)
file_records=[{'path':str(p.relative_to(ROOT)),'sha256':collector.sha(p),'bytes':p.stat().st_size} for p in sorted(ROOT.rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
collector.put(ROOT/'source-files.READY.json',{'files':file_records,'excluded_paths':['source-files.READY.json','source-collection.READY.json','__pycache__']})
ready={'schema_version':'round6.source-collection-ready.v1','status':'READY' if collector.success(items) else 'BOUNDED_COLLECTION_COMPLETE_WITH_SHORTFALL','target_achieved':collector.success(items),'counts':audit['counts'],'preparation_sha256':collector.sha(ROOT/'preparation.READY.json'),'release_receipt_sha256':collector.sha(ROOT/'freeze-release.json'),'artifacts':{name:collector.sha(ROOT/name) for name in (['source-inputs.READY.json'] if items else [])+['blinded-image-inventory.READY.json','source-metadata.READY.json','collection-audit.READY.json','source-files.READY.json']},'collection_edits_complete':True}
collector.put(ROOT/'source-collection.READY.json',ready);print(json.dumps(ready,indent=2))
