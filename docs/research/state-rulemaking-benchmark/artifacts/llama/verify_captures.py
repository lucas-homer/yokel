"""Offline verification and operations summary; does not contact providers."""
from pathlib import Path
import hashlib,json,statistics,re
P=Path(__file__).resolve().parent

def main():
 plan=json.loads((P/'execution-plan.json').read_text());captures=[];files=[]
 for f in sorted(P.glob('runs/*/*/capture.json')):
  r=json.loads(f.read_text());assert r==json.loads((f.parent/'tool-envelope.json').read_text())
  matching=[x for x in plan['calls'] if (x['fixture_id'],x['tier'])==(r['fixture_id'],r['tier'])];assert len(matching)==1
  m=matching[0];assert r['input_sha256']==m['input_sha256'] and r['input_page_count']==m['input_page_count']
  assert r['request']=={'fileId':r['file_id'],'markdown':True,'tier':r['tier'],'version':'latest'}
  up=json.loads((P/'uploads'/f"{r['fixture_id']}-response.json").read_text());assert up['file_id']==r['file_id']
  if r['outcome']=='completed':
   texts=[x['text'] for x in r['response']['content'] if x['type']=='text']
   for i,t in enumerate(texts):assert (f.parent/f'text-{i:02}.txt').read_text()==t
  for i,b in enumerate(r['response'].get('content',[])):
   if b.get('type')=='text':assert (f.parent/f'response-text-{i:02}.txt').read_text()==b['text']
  captures.append(r)
 captures.sort(key=lambda x:x['completion_order']);assert [r['completion_order'] for r in captures]==list(range(1,len(captures)+1))
 streak=0;trigger=None
 for r in captures:
  streak=0 if r['outcome']=='completed' else streak+1
  if streak>=3 and trigger is None:trigger=r
 events=[]
 for r in captures:events.extend([(r['started_at'],1),(r['ended_at'],-1)])
 active=maximum=0
 for _,delta in sorted(events,key=lambda x:(x[0],x[1])):active+=delta;maximum=max(maximum,active)
 assert maximum<=2
 if trigger:
  assert all(r['started_at']<=trigger['ended_at'] for r in captures),'New parse launched after stop threshold'
 ledger=[]
 for m in plan['calls']:
  match=next((r for r in captures if (r['fixture_id'],r['tier'])==(m['fixture_id'],m['tier'])),None)
  ledger.append({'fixture_id':m['fixture_id'],'tier':m['tier'],'input_sha256':m['input_sha256'],'pages':m['input_page_count'],'outcome':match['outcome'] if match else 'not_attempted_provider_stopped' if trigger else 'pending','capture':f"runs/{m['fixture_id']}/{m['tier']}/capture.json" if match else None})
 summary={'expected_units':20,'pages_per_tier':34,'expected_parse_calls':40,'attempted_parse_calls':len(captures),'completed_parse_calls':sum(r['outcome']=='completed' for r in captures),'timeout_calls':sum(r['outcome']=='timeout_backend_unknown' for r in captures),'unattempted_parse_calls':40-len(captures),'uploaded_units':len(list((P/'uploads').glob('*-response.json'))),'max_observed_concurrency':maximum,'stop_trigger':None if not trigger else {'fixture_id':trigger['fixture_id'],'tier':trigger['tier'],'ended_at':trigger['ended_at'],'completion_order':trigger['completion_order']},'usage':'unknown unless explicitly present in raw responses','backend_completion':'unknown for timeouts; no blind retries','validation':'passed immutable envelope equality, input metadata pairing, uploaded file IDs, exact successful text, completion ordering and concurrency/stop limits','successful_latency_ms':{},'failure_elapsed_ms':[{'fixture_id':r['fixture_id'],'tier':r['tier'],'elapsed_ms':r['elapsed_ms']} for r in captures if r['outcome']!='completed']}
 for tier in ['agentic','agentic_plus']:
  vals=[r['elapsed_ms'] for r in captures if r['tier']==tier and r['outcome']=='completed'];summary['successful_latency_ms'][tier]={'count':len(vals),'median':statistics.median(vals) if vals else None,'min':min(vals) if vals else None,'max':max(vals) if vals else None}
 for f in P.rglob('*'):
  if f.is_file() and f.suffix in ['.json','.txt','.md']:
   s=f.read_text();assert not re.search(r'https://[^\s"<>]*(?:expires_at=|X-Amz-Signature=)',s),'Signed URL found'
   if f.name not in ['artifact-hashes.json','operations.json','call-ledger.json']:files.append({'path':str(f.relative_to(P)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size})
 for name,data in [('operations.json',summary),('call-ledger.json',ledger),('artifact-hashes.json',files)]: (P/name).write_text(json.dumps(data,indent=2)+'\n')
 print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
