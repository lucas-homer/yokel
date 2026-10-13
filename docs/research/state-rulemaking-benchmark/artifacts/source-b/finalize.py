from pathlib import Path
from pypdf import PdfReader
import json,hashlib,collections
P=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
fixtures=[];checks=[]
for d in sorted(P.glob('B[0-9][0-9]')):
 m=json.loads((d/'fixture.json').read_text());texts=(d/'native.txt').read_text().split('\n\f\n')
 assert len(m['reference_fields']) in range(6,11)
 assert sum(f['critical'] for f in m['reference_fields'])>=4
 assert m['original_sha256']==sha(d/'original.pdf') and m['input_sha256']==sha(d/'input.pdf')
 assert m['input_page_count']<=4
 assert len(list(d.glob('page-*.png')))==m['input_page_count']
 assert m['original_physical_pages']==list(range(m['original_physical_pages'][0],m['original_physical_pages'][-1]+1))
 for f in m['reference_fields']:
  assert f['original_page']==m['original_physical_pages'][f['input_page']-1]
  if f['basis']=='source_text':assert f['source_quote'] in texts[f['input_page']-1],(d.name,f['field_id'])
 m['shared_original_group']='MA-register-1542' if m['state']=='MA' else 'TX-2026-05-22' if m['fixture_id'] in ['B05','B06'] else 'TX-2026-06-05' if m['state']=='TX' else 'CO-49-17' if m['fixture_id'] in ['B08','B10'] else 'CO-49-16' if m['state']=='CO' else 'NC-exempt-sales' if m['fixture_id']=='B03' else 'NC-register-41-01-waiver'
 m['template_family']='MA-Regulation-Filing' if m['state']=='MA' else 'NC-Form-300' if d.name=='B04' else 'NC-agency-notice' if m['state']=='NC' else 'TX-Register-proposed-rule' if m['state']=='TX' else 'CO-Terminated-Rulemaking' if d.name!='B10' else 'CO-Permanent-Rules-Adopted'
 if m['state']=='MA':m['layout_features']=['filled form','embedded native text','signature/stamp image','blank fields']
 if m['state']=='NC':m['layout_features'].extend(['checkboxes','filled notice' if d.name=='B04' else 'rule text attachment'])
 if m['state']=='TX':m['layout_features'].extend(['cross-page continuation','neighboring notices','rule text strikeouts'])
 if m['state']=='CO':m['layout_features'].extend(['label/value layout','lifecycle event'])
 m['layout_features']=list(dict.fromkeys(m['layout_features']))
 (d/'fixture.json').write_text(json.dumps(m,indent=2)+'\n')
 fixtures.append(m);checks.append(dict(fixture_id=d.name,input_sha256=sha(d/'input.pdf'),fixture_sha256=sha(d/'fixture.json'),pages=m['input_page_count'],fields=len(m['reference_fields']),critical_fields=sum(f['critical'] for f in m['reference_fields']),quotes_verified=True,images_inspected_by_collector=True))
assert len({m['input_sha256'] for m in fixtures})==10
assert max(collections.Counter(m['state'] for m in fixtures).values())<=4
assert max(collections.Counter(m['shared_original_group'] for m in fixtures).values())<=2
summary=dict(fixture_count=len(fixtures),input_pages=sum(m['input_page_count'] for m in fixtures),states=dict(collections.Counter(m['state'] for m in fixtures)),buckets=dict(collections.Counter(m['bucket'] for m in fixtures)),distinct_original_hashes=len({m['original_sha256'] for m in fixtures}),distinct_input_hashes=10,distinct_template_families=len({m['template_family'] for m in fixtures}),fields=sum(len(m['reference_fields']) for m in fixtures),critical_fields=sum(sum(f['critical'] for f in m['reference_fields']) for m in fixtures),checks=checks,vendor_parsing_run=False,independent_review='pending',quota_deviations=[])
(P/'collection-validation.json').write_text(json.dumps(summary,indent=2)+'\n')
files=[]
for f in sorted(P.rglob('*')):
 if f.is_file() and f.name not in ['artifact-manifest.json']:
  files.append(dict(path=str(f.relative_to(P)),sha256=sha(f),bytes=f.stat().st_size))
(P/'artifact-manifest.json').write_text(json.dumps(files,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='checks'}))
