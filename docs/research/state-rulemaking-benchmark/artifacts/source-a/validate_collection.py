from pathlib import Path
import json,hashlib,collections
from pypdf import PdfReader
P=Path(__file__).resolve().parent
required=['fixture_id','state','bucket','layout_features','event_type','source_url','discovery_url','retrieved_at','source_title','selection_reason','original_sha256','input_sha256','original_page_count','input_page_count','original_physical_pages','package_limitations','reference_fields']
fields=['field_id','question','expected_value','answerability','critical','original_page','input_page','region','source_quote','basis']
rows=[];hashes=[];total=0
for path in sorted(P.glob('A[0-9][0-9]/fixture.json')):
 f=json.loads(path.read_text());d=path.parent;assert all(k in f for k in required)
 for key,file in [('original_sha256','original.pdf'),('input_sha256','input.pdf')]:assert hashlib.sha256((d/file).read_bytes()).hexdigest()==f[key]
 original=PdfReader(d/'original.pdf');inp=PdfReader(d/'input.pdf')
 assert len(original.pages)==f['original_page_count'] and len(inp.pages)==f['input_page_count']<=4
 pages=f['original_physical_pages'];assert len(pages)==len(inp.pages) and pages==list(range(pages[0],pages[-1]+1))
 for i,n in enumerate(pages):
  o=original.pages[n-1];p=inp.pages[i]
  assert list(o.mediabox)==list(p.mediabox)
  assert o.get_contents().get_data()==p.get_contents().get_data()
  assert (d/f'page-{i+1}.png').stat().st_size>1000
 assert 6<=len(f['reference_fields'])<=10
 assert len({x['field_id'] for x in f['reference_fields']})==len(f['reference_fields'])
 assert sum(x['critical'] for x in f['reference_fields'])>=4
 for x in f['reference_fields']:
  assert all(k in x for k in fields)
  assert x['answerability'] in ['present','explicit_negative','not_stated','uncertain']
  assert x['basis'] in ['source_text','visual_mark','full_scope_absence']
  assert x['original_page']==pages[x['input_page']-1]
  if x['basis']=='source_text':
   native=(d/f"native-page-{x['input_page']}.txt").read_text()
   if native: assert x['source_quote'] in native, (f['fixture_id'],x['field_id'])
  if x['basis']=='full_scope_absence':assert x['answerability']=='not_stated' and x['expected_value'] is None
  for extra in x.get('additional_evidence',[]):assert extra['source_quote'] in (d/f"native-page-{extra['input_page']}.txt").read_text()
 hashes.append(f['input_sha256']);total+=len(inp.pages)
 rows.append({'fixture_id':f['fixture_id'],'pages':len(inp.pages),'original_physical_pages':pages,'reference_fields':len(f['reference_fields']),'critical_fields':sum(x['critical'] for x in f['reference_fields']),'page_content_streams_unchanged':True,'schema_hash_quote_checks_passed':True})
assert len(rows)==10 and len(set(hashes))==10 and total==15
result={'passed':True,'fixtures':rows,'total_input_pages':total,'distinct_input_hashes':len(set(hashes)),
'limit':'Source-only structure/byte/page-content checks and native quote integrity. Image transcriptions/mark selection and semantic references require independent reviewer adjudication; no vendor parsing or scoring performed.'}
(P/'collection-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
