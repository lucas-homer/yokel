import importlib.util,json,os,sys,tempfile
from pathlib import Path
p=Path(__file__).with_name('run_ocr.py');spec=importlib.util.spec_from_file_location('ocr',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Response:
 status=200
 def __init__(self,payload):self.payload=payload
 def __enter__(self):return self
 def __exit__(self,*a):pass
 def read(self):return json.dumps(self.payload).encode()
class Opener:
 def __init__(self,payload):self.payload=payload;self.calls=0
 def open(self,req,timeout):
  self.calls+=1
  if isinstance(self.payload,Exception):raise self.payload
  return Response(self.payload)
checks=[]
for label,payload,expected in [('annotations',{'id':'fake','choices':[{'message':{'content':'DO NOT SCORE THIS','annotations':[{'type':'file','file':{'hash':'h','content':[{'type':'text','text':'first'},{'type':'image_url','image_url':{'url':'data:image/png;base64,AA=='}},{'type':'text','text':'second'}]}}]}}]},'completed'),('missing',{'choices':[{'message':{'content':'DO NOT SCORE'}}]},'needs_review'),('timeout',TimeoutError(),'uncertain')]:
 with tempfile.TemporaryDirectory() as tmp:
  m.ROOT=Path(tmp);(m.ROOT/'pilot-authorization.json').write_text(json.dumps({'model':'google/gemma-3-27b-it','engine':'mistral-ocr','corpus_freeze_sha256':m.sha((m.ART/'corpus-freeze.json').read_bytes()),'runner_sha256':m.sha(p.read_bytes()),'allowed_fixtures':['A01'],'max_pages':1,'stop_at_reported_usd':1}));op=Opener(payload);m.urllib.request.build_opener=lambda *a:op;os.environ['OPENROUTER_API_KEY']='offline-test-token';sys.argv=['test','--execute','--max-new','1'];m.main();st=json.loads((m.ROOT/'state.json').read_text());assert st['jobs']['A01']['phase']==expected;assert op.calls==1
  if label=='annotations':
   assert (m.ROOT/'runs/A01/output.md').read_text()=='first\n\nsecond';mp=json.loads((m.ROOT/'runs/A01/serialization-map.json').read_text());assert mp['parts'][1]['start_character']==7
  if expected!='completed':
   try:m.main()
   except AssertionError:pass
   else:raise AssertionError('Uncertain request retried')
   assert op.calls==1
  checks.append({'case':label,'passed':True})
Path(__file__).with_name('offline-checks.json').write_text(json.dumps({'network_calls':0,'checks':checks},indent=2)+'\n')
print('3 offline cases passed; no network calls')
