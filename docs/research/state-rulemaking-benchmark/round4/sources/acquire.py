from pathlib import Path
import sys,json,subprocess,hashlib,datetime
O=Path(__file__).resolve().parent
BIN=Path('/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/poppler/bin')
def event(**x):
 x['timestamp']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 with (O/'search-access-ledger.jsonl').open('a') as f:f.write(json.dumps(x)+'\n')
def get(key,url,q,state):
 p=O/'candidates'/key;p.mkdir(parents=True,exist_ok=True)
 args=['curl','-L','--max-time','45','-sS','-D',str(p/'headers.txt'),'-o',str(p/'original.pdf'),'-w','%{http_code}\n%{url_effective}',url]
 r=subprocess.run(args,capture_output=True,text=True);(p/'curl.stderr').write_text(r.stderr)
 m={'candidate_id':key,'source_url':url,'query_id':q,'state':state,'curl_exit':r.returncode,'http_result':r.stdout,'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 event(event='retrieval_attempt',**m)
 if r.returncode or not (p/'original.pdf').read_bytes().startswith(b'%PDF'):
  m['status']='access_failure_or_non_pdf';event(event=m['status'],**{k:v for k,v in m.items() if k!='status'})
 else:
  data=(p/'original.pdf').read_bytes();m['original_sha256']=hashlib.sha256(data).hexdigest();m['original_bytes']=len(data)
  for tool,args in [('pdfinfo',[]),('pdffonts',[]),('pdfimages',['-list']),('pdftotext',['-layout'])]:
   cmd=[str(BIN/tool),*args,str(p/'original.pdf')]+([str(p/'native-original.txt')] if tool=='pdftotext' else [])
   r=subprocess.run(cmd,capture_output=True,text=True);(p/(tool+'.stdout')).write_text(r.stdout);(p/(tool+'.stderr')).write_text(r.stderr)
   m[tool]={'command':cmd,'exit':r.returncode}
  m['status']='downloaded_pending_selection';m['native_chars']=len((p/'native-original.txt').read_text())
 (p/'metadata.json').write_text(json.dumps(m,indent=2)+'\n');print(json.dumps(m))
if __name__=='__main__':get(*sys.argv[1:])
