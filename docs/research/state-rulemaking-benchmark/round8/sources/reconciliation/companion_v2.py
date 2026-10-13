#!/usr/bin/env python3
"""Bounded source-only reconciliation; imports unchanged frozen mechanical helpers."""
import argparse,contextlib,datetime,hashlib,importlib.util,json,os,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent; SOURCES=ROOT.parent; ROUND=SOURCES.parent
spec=importlib.util.spec_from_file_location('frozen_collector',SOURCES/'collect-native.py');frozen=importlib.util.module_from_spec(spec);spec.loader.exec_module(frozen)
ORIGINAL_GATE=frozen.gate; ORIGINAL_GET=frozen.get
CORRECTED={ 'Q03':[2,5,6], 'Q05':[2,4,6], 'Q14':[1,2,3] }
def get(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):Path(p).write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def lines(p):return [json.loads(x) for x in Path(p).read_text().splitlines()]
def append(p,x):
 with Path(p).open('a') as f:f.write(json.dumps({'timestamp_utc':now(),**x},ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
def key(q,c):return (q,c['display_order'],c['url'])
def identity(q,c):return {'query_id':q,'display_order':c['display_order'],'url':c['url'],'candidate_order':c['candidate_order']}
def original_events():return lines(SOURCES/'search-access-ledger.jsonl')
def access_events():return lines(ROOT/'access-ledger.jsonl')
def configuration():return get(ROOT/'plan-amendment.json')
def bounds():
 out={x['query_id']:x['corrected_bounded_candidates'] for x in configuration()['queries']}
 for x in access_events():
  if x['event']=='query_registered':assert x['query_id'] not in out;out[x['query_id']]=x['bounded_candidates']
 return out

def observations():
 obs={};orig=original_events();registrations={x['query_id']:x for x in orig if x['event']=='query_registered'}
 for line,x in enumerate(orig,1):
  if x['event'] not in ['candidate_retained','candidate_excluded']:continue
  c=registrations[x['query_id']]['bounded_candidates'][x['candidate_order']-1];k=key(x['query_id'],c)
  item={'physical_event':{'path':'search-access-ledger.jsonl','line':line,'timestamp_utc':x['timestamp_utc']},'original_status':x['event'],'url':c['url'],'reasons':x.get('reasons',[])}
  if x['event']=='candidate_retained':item.update({a:x[a] for a in ['document_id','state','stratum','pdf_pages']});item['artifact_folder']='documents/'+x['document_id'];item['eligible']=True
  else:item['eligible']=False
  obs[k]=item
 for line,x in enumerate(access_events(),1):
  if x['event'] not in ['candidate_retained','candidate_excluded']:continue
  k=(x['query_id'],x['display_order'],x['url']);assert k not in obs,'Do not overwrite any historical observation.'
  item={'physical_event':{'path':'reconciliation/access-ledger.jsonl','line':line,'timestamp_utc':x['timestamp_utc']},'original_status':x['event'],'url':x['url'],'reasons':x.get('reasons',[]),'eligible':x['event']=='candidate_retained'}
  if item['eligible']:item.update({a:x[a] for a in ['document_id','state','stratum','pdf_pages']});item['artifact_folder']='reconciliation/documents/'+x['document_id']
  obs[k]=item
 return obs

def common_quota(items,state):
 return sorted(set(frozen.quota(items,state,'general_comment',1)) & set(frozen.quota(items,state,'conditional_control',1)))

def replay(obs=None,bounded=None):
 obs=observations() if obs is None else obs;bounded=bounds() if bounded is None else bounded
 selected=[];decisions=[];pending=None;plan=get(SOURCES/'selection-plan.json')['queries'];blocked=set(get(SOURCES/'dedup-inventory.json')['blocked_url_keys'])
 for q in plan:
  qid=q['query_id']
  if qid not in bounded:break
  for c in bounded[qid]:
   k=key(qid,c);o=obs.get(k);reasons=[];status='excluded';item=None
   if frozen.success(selected):status='skipped_success_stop';reasons=['success stop before candidate']
   elif o and o['eligible']:
    reasons=frozen.quota(selected,o['state'],o['stratum'],o['pdf_pages'])
    if not reasons:status='retained';item={**identity(qid,c),**o};selected.append(item)
   elif o:
    reasons=o['reasons'];assert reasons,'Every exclusion must retain its source/access/quota basis.'
    # Earlier exclusions all have independent caps/scope/URL/redirect bases or
    # the unchanged state-spread basis. Do not revive unreviewed source bodies.
    if o['physical_event']['path']=='search-access-ledger.jsonl' and reasons and all('would exceed retained aggregate page cap'==r for r in reasons):
     pending=identity(qid,c);break
   elif frozen.urlkey(c['url']) in blocked:reasons=['prior seen source URL; frozen inventory key; no acquisition']
   else:
    reasons=common_quota(selected,q['state'])
    if not reasons:pending=identity(qid,c);break
   decisions.append({**identity(qid,c),'logical_status':status,'logical_reasons':reasons,'physical_observation':o,'artifact_folder':item['artifact_folder'] if item else None})
  if pending:break
 corrected_keys={key(q, c) for q,cs in bounded.items() for c in cs}
 outside=[{'query_id':k[0],'display_order':k[1],'url':k[2],**o} for k,o in obs.items() if k not in corrected_keys]
 return {'schema_version':'round8.logical-source-view.v1','cohort_classification':'protocol-deviation corrected','physical_access_order_restored':False,'selected':selected,'decisions':decisions,'pending_candidate':pending,'out_of_corrected_bound_observations':outside,'target_achieved':frozen.success(selected)}

def verify_baseline():
 b=get(ROOT/'original-baseline.json')
 for x in b['source_files']:assert sha(SOURCES/x['path'])==x['sha256'],x['path']
 for x in b['freeze_A_files']:assert sha(ROUND/x['path'])==x['sha256'],x['path']
 return b

def gate(operation='catchup'):
 release=get(ROOT/'amendment-release-v2.json') # Missing receipt holds before any native subprocess.
 assert release['authorized_reconciliation'] is True and release['primary_approval_message'] and release['timestamp_utc']
 assert release['companion_preparation_sha256']==sha(ROOT/'preparation-v2.READY.json')
 for x in get(ROOT/'preparation-v2.READY.json')['static_files']:assert sha(ROOT/x['path'])==x['sha256'],x['path']
 b=verify_baseline();assert release['original_ledger_sha256']==b['original_ledger_sha256'] and release['plan_amendment_sha256']==sha(ROOT/'plan-amendment.json')
 saved=frozen.ROOT
 try:frozen.ROOT=SOURCES;ORIGINAL_GATE()
 finally:frozen.ROOT=saved
 if operation=='future':
  assert release['authorized_future_queries'] is True
  checkpoint=get(ROOT/'logical-replay.READY.json');assert sha(ROOT/'logical-replay.json')==checkpoint['logical_replay_sha256']
  for x in checkpoint['catchup_artifact_files']:assert sha(ROOT/x['path'])==x['sha256'],x['path']
  prefix=[x for x in replay()['decisions'] if int(x['query_id'][1:])<=14];assert prefix==get(ROOT/'logical-replay.json')['decisions'],'Frozen corrected prefix changed.'
 return get(SOURCES/'collection-protocol.json')

def candidate(q,n):
 cs=bounds()[q];assert type(n) is int and 1<=n<=len(cs);return cs[n-1]
def current(q,n):
 c=candidate(q,n);view=replay();assert not view['target_achieved'],'Success stop reached.'
 assert view['pending_candidate']==identity(q,c),'Only the earliest unresolved logical candidate may be acquired/reviewed/retained.'
 return c

def virtual_query_events(q):
 physical=[x for x in access_events() if x.get('query_id')==q]
 if int(q[1:])<=14:out=[{'event':'query_registered','query_id':q,'bounded_candidates':bounds()[q]}]
 else:out=[x for x in physical if x['event'] not in ['candidate_retained','candidate_excluded']]
 for x in replay()['decisions']:
  if x['query_id']==q:out.append({'event':'candidate_retained' if x['logical_status']=='retained' else 'candidate_excluded','query_id':q,'candidate_order':x['candidate_order']})
 return out

def redirected_get(p):
 p=Path(p)
 if p.parent==ROOT and p.name in ['selection-plan.json','collection-protocol.json','dedup-inventory.json','native-toolchain.json']:return ORIGINAL_GET(SOURCES/p.name)
 return ORIGINAL_GET(p)

def transport_event(x):
 if x.get('candidate_order') is not None:x={**x,**identity(x['query_id'],candidate(x['query_id'],x['candidate_order']))}
 append(ROOT/'access-ledger.jsonl',x)

def selected_for_helpers():return replay()['selected']
def install_adapter():
 frozen.ROOT=ROOT;frozen.get=redirected_get;frozen.selected=selected_for_helpers;frozen.events=access_events;frozen.query_events=virtual_query_events;frozen.current=current;frozen.event=transport_event
 frozen.gate=lambda:gate('catchup')

def aliases():
 d=ROOT/'documents';d.mkdir(exist_ok=True)
 for item in replay()['selected']:
  folder=SOURCES/item['artifact_folder'];alias=d/item['document_id']
  if folder.parent!=d:
   if alias.is_symlink():assert alias.resolve()==folder.resolve()
   else:assert not alias.exists();alias.symlink_to(folder, target_is_directory=True)

def record_logical_decisions():
 view=replay();previous=lines(ROOT/'correction-ledger.jsonl');old={ (x['query_id'],x['display_order'],x['url']):x for x in previous if x['event']=='logical_decision'}
 for d in view['decisions']:
  k=(d['query_id'],d['display_order'],d['url'])
  if k in old:assert {a:v for a,v in old[k].items() if a not in ['timestamp_utc','event']}==d,'Do not rewrite a logical decision.'
  else:append(ROOT/'correction-ledger.jsonl',{'event':'logical_decision',**d})
 return view

def acquire(q,n):
 assert q=='Q05' or 15<=int(q[1:])<=24,'Only missing bounded Massachusetts or new frozen-query candidates permit acquisition.'
 gate('catchup' if q=='Q05' else 'future');install_adapter();current(q,n);aliases();frozen.acquire(q,n);record_logical_decisions()
def review_pages(q,n):gate('catchup' if q=='Q05' else 'future');install_adapter();frozen.review_pages(q,n)
def retain(q,n,note):gate('catchup' if q=='Q05' else 'future');install_adapter();aliases();frozen.retain(q,n,note);record_logical_decisions()
def exclude(q,n,reason):gate('catchup' if q=='Q05' else 'future');install_adapter();frozen.exclude(q,n,reason);record_logical_decisions()

def checkpoint():
 gate();view=record_logical_decisions();assert view['pending_candidate'] is None and not any(int(x['query_id'][1:])>14 for x in view['decisions'])
 assert len(view['decisions'])==sum(len(cs) for q,cs in bounds().items() if int(q[1:])<=14)
 assert not (ROOT/'logical-replay.READY.json').exists();put(ROOT/'logical-replay.json',view)
 put(ROOT/'logical-replay.READY.json',{'schema_version':'round8.logical-replay-ready.v1','logical_replay_sha256':sha(ROOT/'logical-replay.json'),'correction_ledger_prefix_sha256':sha(ROOT/'correction-ledger.jsonl'),'access_ledger_prefix_sha256':sha(ROOT/'access-ledger.jsonl'),'amendment_release_sha256':sha(ROOT/'amendment-release-v2.json'),'cohort_classification':'protocol-deviation corrected','physical_access_order_restored':False,'catchup_artifact_files':[{'path':str(p.relative_to(ROOT)),'sha256':sha(p)} for folder in [ROOT/'candidates',ROOT/'documents'] if folder.exists() for p in sorted(folder.rglob('*')) if p.is_file() and not p.is_symlink()]})
 return view

def request(q):
 assert 15<=int(q[1:])<=24;gate('future');install_adapter();return frozen.request(q)
def direct_basis(row):
 u=row['url'];t=row['title']
 if re.search(r'\.pdf(?:$|[?#])|/rules/pdf/|/doc/[^?]+/download(?:[?#]|$)|/documents/dsweb/(?:View|Get)/Document-\d+',u,re.I):return 'Direct PDF extension or reviewed explicit publisher document endpoint'
 if re.search(r'\.pdf\b',t,re.I) and re.search(r'/hearings/hearingsSearch/results/|/hearingSummaryReport/',u,re.I):return 'PDF-titled individual hearing/report document route'
 return None

def register(q,p):
 assert 15<=int(q[1:])<=24;gate('future');install_adapter();record,dest=frozen.preserve_search_response(q,p)
 try:
  for row in record['results']:
   review=row['source_route_review'];assert review['reviewed_from_saved_metadata'] is True and review['basis']
   assert review['classification'] in ['direct_document','not_direct_document']
   assert row.get('direct_pdf_candidate')==(review['classification']=='direct_document')
   if direct_basis(row):assert row['direct_pdf_candidate'] is True,'Known direct routes cannot be silently omitted.'
   if row['direct_pdf_candidate']:assert row.get('pdf_candidate_basis'),'Explicit metadata evidence required, including outside known endpoint patterns.'
  frozen.register(q,p);record_logical_decisions()
 except (AssertionError,KeyError,TypeError) as e:
  transport_event({'event':'query_response_held','query_id':q,'search_record_sha256':sha(dest),'reason':'Per-row source-route review required: '+str(e),'rerun_allowed':False})
  raise AssertionError('Retained raw response held for source-only route review; no rerun: '+str(e)) from e

def main():
 p=argparse.ArgumentParser();p.add_argument('command',choices=['view','acquire','review-pages','retain','exclude','checkpoint','query-request','register-search','resolve-search']);p.add_argument('args',nargs='*');a=p.parse_args();v=a.args
 if a.command=='view':print(json.dumps(replay(),indent=2))
 elif a.command=='acquire':acquire(v[0],int(v[1]))
 elif a.command=='review-pages':review_pages(v[0],int(v[1]))
 elif a.command=='retain':retain(v[0],int(v[1]),v[2])
 elif a.command=='exclude':exclude(v[0],int(v[1]),v[2])
 elif a.command=='checkpoint':print(json.dumps(checkpoint()))
 elif a.command=='query-request':print(json.dumps(request(v[0])))
 elif a.command=='register-search':register(*v)
 elif a.command=='resolve-search':
  assert 15<=int(v[0][1:])<=24;gate('future');install_adapter();frozen.resolve_search(*v);record_logical_decisions()
if __name__=='__main__':main()
