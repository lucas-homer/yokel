import sys,json,time,hashlib,subprocess
from pathlib import Path
BIN='/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/poppler/bin/pdftotext'
source,target=map(Path,sys.argv[1:3]);version=subprocess.run([BIN,'-v'],capture_output=True,text=True,check=True).stderr;assert '26.05.0' in version
start=time.monotonic();subprocess.run([BIN,'-layout','-enc','UTF-8',str(source),str(target)],check=True,capture_output=True);elapsed=time.monotonic()-start;raw=target.read_bytes();text=raw.decode('utf-8');parts=text.split('\f');offset=0;mapping=[]
for i,part in enumerate(parts):
 if i==len(parts)-1 and not part:break
 mapping.append({'input_page':i+1,'start_character':offset,'end_character':offset+len(part)});offset+=len(part)+1
target.with_suffix('.capture.json').write_text(json.dumps({'engine':'pdftotext','version':version,'method':'-layout -enc UTF-8; no OCR; exact native output bytes','pages':mapping,'input_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(raw).hexdigest(),'conversion_seconds':elapsed,'time_includes_subprocess':True},indent=2)+'\n')
