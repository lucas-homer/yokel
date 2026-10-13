from pathlib import Path
from pypdf import PdfReader,PdfWriter
import json,hashlib,subprocess,shutil
from datetime import datetime,timezone
R=Path(__file__).parent
inventory=json.loads((R/'retrieval-inventory.json').read_text())
old=next(x for x in inventory if x['fixture_id']=='H03');(R/'inaccessible-attempts.json').write_text(json.dumps([old],indent=2)+'\n')
old.update(state='IA',source_url='https://www.legis.iowa.gov/docs/aco/arc/0619D.pdf',discovery_url='https://rules.iowa.gov/Notice/Details/0619D',retrieved_at=datetime.now(timezone.utc).isoformat(),retrieval_exit=0,retrieval_error='',replacement_reason='Tennessee official PDF returned HTTP403; no access-control bypass attempted.')
mapping={'H01':[1,2],'H02':[1,2],'H03':[1,2,3],'H04':[62,63],'H05':[1,2],'H06':[5,6,7,8],'H07':[9,10,11],'H08':[1,2,3,4]}
for rec in inventory:
 k=rec['fixture_id'];d=R/k;p=PdfReader(d/'original.pdf');pages=mapping[k]
 if len(pages)==len(p.pages):shutil.copyfile(d/'original.pdf',d/'input.pdf')
 else:
  w=PdfWriter()
  for n in pages:w.add_page(p.pages[n-1])
  with (d/'input.pdf').open('wb') as f:w.write(f)
 t=[]
 for i,n in enumerate(pages):
  s=p.pages[n-1].extract_text();(d/f'native-page-{i+1}.txt').write_text(s);t.append(f'=== INPUT PAGE {i+1}; ORIGINAL PHYSICAL PAGE {n} ===\n{s}')
 (d/'native.txt').write_text('\n\n'.join(t))
 subprocess.run(['pdftoppm','-scale-to','1600','-png',str(d/'input.pdf'),str(d/'page')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
 for variant in d.glob('page-*.png'):
  normalized=d/f'page-{int(variant.stem.split("-")[-1])}.png'
  if variant!=normalized:variant.rename(normalized)
 rec.update(original_page_count=len(p.pages),original_sha256=hashlib.sha256((d/'original.pdf').read_bytes()).hexdigest(),original_bytes=(d/'original.pdf').stat().st_size,input_page_count=len(pages),input_sha256=hashlib.sha256((d/'input.pdf').read_bytes()).hexdigest(),input_bytes=(d/'input.pdf').stat().st_size,original_physical_pages=pages,input_is_publisher_original=len(pages)==len(p.pages))
 print(k,pages,rec['input_sha256'])
(R/'source-inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
