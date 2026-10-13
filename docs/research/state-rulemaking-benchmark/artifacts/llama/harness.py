"""Offline frozen-corpus planning and immutable result recording. No vendor/network calls.
prepare INPUT_LIST --freeze-manifest PATH: validate 20 local PDFs, create execution-plan.json.
record FIXTURE_ID TIER: read vendor-call envelope JSON from stdin, save once.
status: inspect completion and completion-order operational failure streak.
Input list is an object with units [{fixture_id,input_path,input_sha256,input_page_count}].
Its metadata must be adapted from the parent's frozen manifest, never reference answers.
"""
import argparse,datetime,hashlib,json,sys
from pathlib import Path
P=Path(__file__).resolve().parent
TIERS=('agentic','agentic_plus')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save_new(p,v):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(v,f,indent=2);f.write('\n')
def status():
 plan=json.loads((P/'execution-plan.json').read_text()) if (P/'execution-plan.json').exists() else {'calls':[]}
 runs=[]
 for f in (P/'runs').glob('*/*/capture.json') if (P/'runs').exists() else []:runs.append(json.loads(f.read_text()))
 runs.sort(key=lambda x:x['ended_at']); streak=0;stop=False
 for r in runs:
  streak=0 if r['outcome']=='completed' else streak+1
  if streak>=3:stop=True
 return {'planned':len(plan['calls']),'recorded':len(runs),'completed':sum(r['outcome']=='completed' for r in runs),'consecutive_operational_failures':streak,'stop_provider_latched':stop,'pending':len(plan['calls'])-len(runs)}
def main():
 a=argparse.ArgumentParser();sub=a.add_subparsers(dest='cmd',required=True)
 q=sub.add_parser('prepare');q.add_argument('input_list');q.add_argument('--freeze-manifest',required=True)
 q=sub.add_parser('record');q.add_argument('fixture_id');q.add_argument('tier',choices=TIERS)
 sub.add_parser('status');x=a.parse_args()
 if x.cmd=='prepare':
  freeze=Path(x.freeze_manifest).resolve();assert freeze.is_file(),'Parent freeze manifest required'
  units=json.loads(Path(x.input_list).read_text())['units'];assert len(units)==20
  assert {u['fixture_id'] for u in units}=={f'{g}{i:02}' for g in 'AB' for i in range(1,11)}
  total=0;calls=[]
  for u in units:
   f=Path(u['input_path']).resolve();assert f.is_file() and f.read_bytes().startswith(b'%PDF-')
   assert sha(f)==u['input_sha256'];assert u['input_sha256']!='ac95c240653690261eb7a6fef83bd80a04310cf49c15c37256569bbc70315955'
   pages=u['input_page_count'];assert isinstance(pages,int) and 1<=pages<=4;total+=pages
   for tier in TIERS:calls.append({'fixture_id':u['fixture_id'],'input_path':str(f),'input_sha256':u['input_sha256'],'input_byte_length':f.stat().st_size,'input_page_count':pages,'tier':tier,'version':'latest','markdown':True,'file_id':None,'status':'pending'})
  assert total<=80
  save_new(P/'execution-plan.json',{'freeze_manifest_sha256':sha(freeze),'freeze_manifest_path':str(freeze),'prepared_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pages_per_tier':total,'max_concurrent':2,'calls':calls})
 elif x.cmd=='record':
  assert x.fixture_id in {f'{g}{i:02}' for g in 'AB' for i in range(1,11)}
  r=json.load(sys.stdin)
  assert r['fixture_id']==x.fixture_id and r['tier']==x.tier
  assert r['outcome'] in ('completed','operational_failure','timeout_backend_unknown')
  for field in ('request','response','started_at','ended_at','elapsed_ms','input_sha256','input_page_count','file_id'):assert field in r
  assert r['request']=={'fileId':r['file_id'],'markdown':True,'tier':x.tier,'version':'latest'}
  serialized=json.dumps(r)
  assert '/api/upload/' not in serialized and 'X-Amz-' not in serialized and 'expires_at=' not in serialized,'Do not retain signed upload tokens'
  target=P/'runs'/x.fixture_id/x.tier;save_new(target/'capture.json',r)
  if r['outcome']=='completed':
   blocks=r['response'].get('content',[]);texts=[b['text'] for b in blocks if b.get('type')=='text']
   assert texts,'No returned text'
   # Preserve each text block exactly; no assumption that all blocks are markdown.
   for i,text in enumerate(texts):
    with (target/f'text-{i:02}.txt').open('x') as f:f.write(text)
  print(json.dumps(status(),indent=2))
 else:print(json.dumps(status(),indent=2))
if __name__=='__main__':main()
