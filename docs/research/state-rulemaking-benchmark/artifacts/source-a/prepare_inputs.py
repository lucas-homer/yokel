from pathlib import Path
import shutil,json,subprocess,pypdfium2
from pypdf import PdfReader,PdfWriter
ROOT=Path(__file__).resolve().parent
render='/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/override/pdftoppm'
for fid in ['A01','A02','A03','A04','A05','A06','A07','A08','A09','A10']:
 d=ROOT/fid;d.mkdir(exist_ok=True)
 if fid in ['A09','A10']: shutil.copyfile(ROOT/'ny-issue/original.pdf',d/'original.pdf')
 r=PdfReader(d/'original.pdf')
 pages={'A05':[11],'A09':[30],'A10':[36]}.get(fid,list(range(1,len(r.pages)+1)))
 if fid in ['A05','A09','A10']:
  w=PdfWriter()
  for n in pages: w.add_page(r.pages[n-1])
  with (d/'input.pdf').open('wb') as f:w.write(f)
 else: shutil.copyfile(d/'original.pdf',d/'input.pdf')
 i=PdfReader(d/'input.pdf');texts=[page.extract_text() or '' for page in i.pages]
 (d/'native.txt').write_text('\n\f\n'.join(texts))
 for n,t in enumerate(texts,1):(d/f'native-page-{n}.txt').write_text(t)
 (d/'page-map.json').write_text(json.dumps({'original_physical_pages':pages,'original_page_count':len(r.pages),'input_page_count':len(i.pages)},indent=2)+'\n')
 doc=pypdfium2.PdfDocument(d/'input.pdf')
 for n in range(len(doc)):
  page=doc[n];bitmap=page.render(scale=1.8);bitmap.to_pil().save(d/f'page-{n+1}.png');bitmap.close();page.close()
 doc.close()
 (d/'render-log.txt').write_text('Rendered full input using bundled PDFium at scale 1.8; Poppler initially attempted and interrupted for slow rendering.\n')
 print(fid,'pages',pages,'rendered pdfium')
