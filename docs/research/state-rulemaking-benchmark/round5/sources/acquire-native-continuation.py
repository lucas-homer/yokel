#!/usr/bin/env python3
"""Bounded original-PDF/native acquisition only; no parser, OCR, model, or labels."""
import sys,json,hashlib,subprocess,datetime,re,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent
POP=Path('/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/poppler/bin')
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def event(x):
 x['recorded_at_utc']=now()
 with (ROOT/'continuation-events.jsonl').open('a') as f:f.write(json.dumps(x,ensure_ascii=False)+'\n')
def run(tool,args,out):
 p=subprocess.run([str(POP/tool),*map(str,args)],capture_output=True)
 (out).write_bytes(p.stdout); out.with_suffix(out.suffix+'.stderr').write_bytes(p.stderr)
 if p.returncode:raise RuntimeError(tool+' failed '+str(p.returncode))
def acquire(q,n,state,stratum,url):
 d=ROOT/'candidates'/f'{q}-{n:02d}';d.mkdir(parents=True,exist_ok=False)
 rec={'query_id':q,'candidate_order':n,'state':state,'stratum':stratum,'discovery_url':url,'retrieval_url':url,'attempts':[]}
 for attempt in range(1,3):
  p=subprocess.run(['curl','--fail','--location','--max-redirs','5','--max-time','60','--silent','--show-error','--dump-header',str(d/f'headers-{attempt}.txt'),'--output',str(d/'original.pdf'),'--write-out','%{http_code}\n%{url_effective}\n%{content_type}\n',url],capture_output=True)
  (d/f'curl-{attempt}.stderr').write_bytes(p.stderr);(d/f'curl-{attempt}.metadata').write_bytes(p.stdout)
  rec['attempts'].append({'attempt':attempt,'timestamp_utc':now(),'returncode':p.returncode,'metadata':p.stdout.decode(errors='replace')})
  if p.returncode==0:break
 if p.returncode:
  rec.update(eligible_native=False,exclusion='access failure after at most one ordinary retry');put(d/'acquisition.json',rec);event({'event':'candidate_excluded',**rec});print(json.dumps(rec));return
 original=d/'original.pdf';rec.update(original_sha256=sha(original),original_bytes=original.stat().st_size)
 if not original.read_bytes().startswith(b'%PDF-'):
  rec.update(eligible_native=False,exclusion='non-PDF publisher response');put(d/'acquisition.json',rec);event({'event':'candidate_excluded',**rec});print(json.dumps(rec));return
 from pypdf import PdfReader
 pages=len(PdfReader(original).pages);rec['pdf_pages']=pages
 run('pdfinfo',['-box',original],d/'pdfinfo.txt');run('pdffonts',[original],d/'pdffonts.txt');run('pdfimages',['-list',original],d/'pdfimages-list.txt')
 p=subprocess.run([str(POP/'pdftotext'),'-layout','-enc','UTF-8',str(original),str(d/'native.txt')],capture_output=True);(d/'pdftotext.stderr').write_bytes(p.stderr)
 reasons=[]
 try:text=(d/'native.txt').read_bytes().decode('utf-8')
 except (UnicodeDecodeError,FileNotFoundError):text='';reasons.append('damaged/non-UTF8 native text')
 rec.update(native_bytes=(d/'native.txt').stat().st_size if (d/'native.txt').exists() else 0,native_codepoints=len(text),formfeed_count=text.count('\f'))
 if p.returncode or not text.strip():reasons.append('native text absent or extraction failed')
 if '\ufffd' in text:reasons.append('damaged native text: replacement character')
 if text.count('\f')!=pages:reasons.append('page-map mismatch')
 if len(text)>30000:reasons.append('native source over frozen 30000-codepoint limit')
 if original.stat().st_size>25000000:reasons.append('PDF over frozen 25000000-byte limit')
 if rec['original_sha256'] in (ROOT/'dedup-inventory.json').read_text():reasons.append('prior original hash duplicate')
 rec.update(eligible_native=not reasons,exclusion='; '.join(reasons) if reasons else None,native_sha256=sha(d/'native.txt') if (d/'native.txt').exists() else None)
 put(d/'acquisition.json',rec);event({'event':'candidate_native_acquired',**rec});print(json.dumps(rec))
def retain(q,n,note):
 d=ROOT/'candidates'/f'{q}-{n:02d}';rec=json.loads((d/'acquisition.json').read_text());assert rec['eligible_native']
 metadata=json.loads(Path(note).read_text());assert metadata['complete_notice'] and metadata['prior_notice_identity_duplicate'] is False
 rec.update(metadata);docid='doc-'+rec['original_sha256'][:12];dest=ROOT/'documents'/docid;assert not dest.exists()
 shutil.copyfile(d/'original.pdf',d/'input.pdf');assert sha(d/'original.pdf')==sha(d/'input.pdf')
 p=subprocess.run([str(POP/'pdftoppm'),'-r','150','-png',str(d/'input.pdf'),str(d/'page')],capture_output=True);(d/'pdftoppm.stderr').write_bytes(p.stderr);assert p.returncode==0
 images=sorted(d.glob('page-*.png'));assert len(images)==rec['pdf_pages']
 rec.update(document_id=docid,scope='full_notice',native_page_map_known=True,input_sha256=sha(d/'input.pdf'),render_dpi=150,rendered_pages=len(images),tools={t:subprocess.run([str(POP/t),'-v'],capture_output=True).stderr.decode(errors='replace').splitlines()[0] for t in ['pdfinfo','pdffonts','pdfimages','pdftotext','pdftoppm']})
 put(d/'provenance.json',rec);shutil.move(str(d),str(dest))
 entry={'document_id':docid,'channel':'native','text_path':f'documents/{docid}/native.txt','text_sha256':rec['native_sha256'],'pdf_path':f'documents/{docid}/input.pdf','pdf_sha256':rec['original_sha256'],'pdf_pages':rec['pdf_pages'],'scope':'full_notice','native_page_map_known':True}
 new=ROOT/'continuation-retained.json';items=json.loads(new.read_text()) if new.exists() else [];items.append(entry);put(new,items);event({'event':'candidate_retained','document_id':docid,**rec});print(json.dumps(entry))
if __name__=='__main__':
 if sys.argv[1]=='acquire':acquire(sys.argv[2],int(sys.argv[3]),*sys.argv[4:])
 elif sys.argv[1]=='retain':retain(sys.argv[2],int(sys.argv[3]),sys.argv[4])
 elif sys.argv[1]=='exclude':event({'event':'candidate_excluded','query_id':sys.argv[2],'candidate_order':int(sys.argv[3]),'candidate_url':sys.argv[4],'reason':sys.argv[5]})
