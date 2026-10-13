#!/usr/bin/env python3
"""Release-gated bounded source transport. Never searches, models, OCRs or labels."""
import argparse,datetime,hashlib,json,math,os,re,shutil,subprocess,unicodedata
from pathlib import Path
from urllib.parse import urlparse,urlsplit,urlunsplit
ROOT=Path(__file__).resolve().parent
POP=Path('/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/poppler/bin')
def normalized_text(t):return ' '.join(unicodedata.normalize('NFKC',t).casefold().split())
def textkey(t):return hashlib.sha256(normalized_text(t).encode()).hexdigest()
def urlkey(u):
 p=urlsplit(u);return urlunsplit(('',p.netloc.lower(),p.path,p.query,''))
def get(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):Path(p).write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def events():return [json.loads(x) for x in (ROOT/'search-access-ledger.jsonl').read_text().splitlines()]
def event(x):
 with (ROOT/'search-access-ledger.jsonl').open('a') as f:
  f.write(json.dumps({'timestamp_utc':now(),**x},ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
def gate():
 ready=get(ROOT/'preparation.READY.json'); release=get(ROOT/'freeze-release.json')
 assert release['authorized_collection'] is True and release['primary_release_message'] and release['timestamp_utc']
 assert release['preparation_ready_sha256']==sha(ROOT/'preparation.READY.json')
 assert release['implementation_and_policy_freezes']
 for x in release['implementation_and_policy_freezes']:assert sha(x['path'])==x['sha256']
 for x in ready['static_files']:assert sha(ROOT/x['path'])==x['sha256'],x['path']
 toolchain=get(ROOT/'native-toolchain.json')
 for t in ['pdftotext','pdftoppm']:
  assert toolchain['version'] in subprocess.run([str(POP/t),'-v'],capture_output=True,check=True).stderr.decode()
 return get(ROOT/'collection-protocol.json')
def selected():return [x for x in events() if x['event']=='candidate_retained']
def success(items):
 return len(items)==8 and len({x['state'] for x in items})>=6 and sum(x['stratum']=='general_comment' for x in items)==6 and sum(x['pdf_pages'] for x in items)<=40

def quota(items,state,stratum,pages):
 reasons=[]
 if len(items)>=8:reasons.append('eight-notice cap')
 if sum(x['state']==state for x in items)>=2:reasons.append('two-per-state cap')
 if len({x['state'] for x in items})<6 and any(x['state']==state for x in items):reasons.append('one-per-state until six states spread rule')
 if sum(x['pdf_pages'] for x in items)+pages>40:reasons.append('aggregate page cap')
 isgeneral=stratum=='general_comment'
 if sum((x['stratum']=='general_comment')==isgeneral for x in items)>=(6 if isgeneral else 2):reasons.append('source-stratum quota full')
 if len({x['state'] for x in items}|{state})+(8-len(items)-1)<6:reasons.append('six-state feasibility guard')
 return reasons

def native_reasons(text,pages,size,cap):
 reasons=[]
 if not text.strip():reasons.append('native text absent')
 if '\ufffd' in text:reasons.append('native replacement-character damage')
 if len(text)>cap['max_codepoints']:reasons.append('native codepoint cap')
 if text.count('\f')!=pages:reasons.append('native page-map mismatch')
 if size>cap['max_pdf_bytes']:reasons.append('original PDF byte cap')
 if pages>40:reasons.append('complete original over aggregate page cap')
 return reasons

def query(q):return next(x for x in get(ROOT/'selection-plan.json')['queries'] if x['query_id']==q)
def query_events(q):return [x for x in events() if x.get('query_id')==q]
def current(q,n):
 assert not success(selected()),'success stop already reached'
 records=query_events(q); registered=next(x for x in records if x['event']=='query_registered')
 candidates=registered['bounded_candidates']; assert 1<=n<=len(candidates)
 for k in range(1,n):assert any(x.get('candidate_order')==k and x['event'] in ['candidate_retained','candidate_excluded'] for x in records)
 assert not any(x.get('candidate_order')==n and x['event'] in ['candidate_retained','candidate_excluded'] for x in records)
 return candidates[n-1]

def previous_queries_complete(q):
 for i in range(1,int(q[1:])):
  records=query_events(f'Q{i:02d}');registered=[x for x in records if x['event']=='query_registered']
  assert len(registered)==1,'Previous query pending retained-response resolution; no advance or rerun.'
  for c in registered[0]['bounded_candidates']:assert any(x.get('candidate_order')==c['candidate_order'] and x['event'] in ['candidate_retained','candidate_excluded'] for x in records)

def request(q):
 gate();assert not success(selected());plan=query(q)
 assert not query_events(q),'Query invocation already consumed; retain/resolve its response, never rerun.'
 previous_queries_complete(q)
 event({'event':'query_invocation_intent','query_id':q,'submitted_query':plan['query'],'search_invocations_allowed':1,'retry_allowed':False})
 return plan

def pending_invocation(q):
 assert not success(selected());plan=query(q);records=query_events(q)
 assert sum(x['event']=='query_invocation_intent' for x in records)==1,'Persist query-request intent before the single external search.'
 assert not any(x['event']=='query_registered' for x in records),'Query already resolved; no rerun or second registration.'
 previous_queries_complete(q)
 return plan

def preserve_search_response(q,record_path):
 plan=pending_invocation(q);record=get(record_path)
 assert record['submitted_query']==plan['query'],'Actual submitted query must exactly match frozen literal string.'
 assert isinstance(record['raw_tool_result'],str) and record['raw_tool_result'] and record['executed_at_utc']
 dest=ROOT/'search-results'/f'{q}.json';dest.parent.mkdir(exist_ok=True)
 if dest.exists():
  saved=next(x for x in query_events(q) if x['event']=='query_response_retained')
  assert sha(dest)==saved['search_record_sha256'] and dest.read_bytes()==Path(record_path).read_bytes(),'Retained response immutable; primary review must resolve the exact retained bytes.'
 else:
  shutil.copyfile(record_path,dest)
  with dest.open('rb') as f:os.fsync(f.fileno())
  event({'event':'query_response_retained','query_id':q,'search_record_path':str(dest.relative_to(ROOT)),'search_record_sha256':sha(dest)})
 return record,dest

def finalize_registration(q,record,dest,results,disposition,review=None):
 assert isinstance(results,list) and [r['display_order'] for r in results]==list(range(1,len(results)+1))
 plan=query(q);candidates=[];seen=set()
 for row in results:
  u=row['url'];host=urlparse(u).hostname or '';domain=plan['official_domain']
  if row.get('direct_pdf_candidate') and (host==domain or host.endswith('.'+domain)) and u not in seen:
   assert row.get('pdf_candidate_basis'),'Direct PDF/document route basis required; never expand HTML links.'
   seen.add(u);candidates.append({'candidate_order':len(candidates)+1,'display_order':row['display_order'],'title':row['title'],'url':u})
   if len(candidates)==3:break
 receipt={'event':'query_registered','query_id':q,'submitted_query':plan['query'],'search_record_path':str(dest.relative_to(ROOT)),'search_record_sha256':sha(dest),'returned_result_count':len(results),'bounded_candidates':candidates,'search_disposition':disposition}
 if review:receipt.update(primary_review_receipt_path=str(review.relative_to(ROOT)),primary_review_receipt_sha256=sha(review))
 event(receipt)

def register(q,record_path):
 gate();record,dest=preserve_search_response(q,record_path)
 try:
  assert record.get('response_status','success')=='success','Failed/unknown response retained and HELD for primary review; never rerun.'
  raw=record['raw_tool_result'];results=record['results']
  assert record['returned_result_count']==len(results),'Preserve metadata for every returned result, not only candidates.'
  headers=re.findall(r'(?m)^([^\n]*?) \((https?://[^\n]+)\)\n[^\n]*cite',raw)
  empty=raw.strip().casefold() in ['no search results found.','no search results found','no results found.','no results found']
  assert headers or empty,'Unrecognized or failed response retained and HELD; primary review required, never rerun.'
  assert [(x['title'],x['url']) for x in results]==headers,'Raw displayed headers must equal ALL structured result rows, including first/empty-title headers.'
  assert not empty or (not results and record['returned_result_count']==0),'Recognized empty response requires exact zero metadata.'
  finalize_registration(q,record,dest,results,'recognized_zero_results' if empty else 'recognized_ordered_results')
 except (AssertionError,KeyError,TypeError) as e:
  event({'event':'query_response_held','query_id':q,'search_record_sha256':sha(dest),'reason':str(e),'rerun_allowed':False})
  raise AssertionError(str(e)) from e

def resolve_search(q,review_path):
 gate();pending_invocation(q);dest=ROOT/'search-results'/f'{q}.json';record=get(dest)
 saved=next(x for x in query_events(q) if x['event']=='query_response_retained');assert sha(dest)==saved['search_record_sha256'],'Retained raw response changed; hold.'
 review_path=Path(review_path).resolve();assert review_path.is_relative_to(ROOT),'Primary resolution receipt must be retained under owned sources.'
 review=get(review_path)
 assert review['authorized_resolution'] is True and review['primary_review_message'] and review['timestamp_utc'] and review['raw_response_interpretation']
 assert review['query_id']==q and review['retained_search_record_sha256']==sha(dest),'Primary review must bind exact retained response bytes.'
 decision=review['decision']
 if decision=='failed_or_unavailable_no_candidates':
  assert record['results']==[] and record['returned_result_count']==0,'Do not discard returned rows as a failed query.'
  results=[]
 elif decision=='reviewed_ordered_results':
  results=review['reviewed_results'];assert review['reviewed_result_count']==len(results)
 else:raise AssertionError('Unsupported primary resolution; keep response held, never rerun.')
 finalize_registration(q,record,dest,results,'primary_resolved_'+decision,review_path)

def acquire(q,n):
 protocol=gate();c=current(q,n);d=ROOT/'candidates'/f'{q}-{n:02d}';d.mkdir(parents=True,exist_ok=False)
 rec={'query_id':q,'candidate_order':n,'state':query(q)['state'],'url':c['url'],'attempts':[]}
 if urlkey(c['url']) in get(ROOT/'dedup-inventory.json')['blocked_url_keys']:
  rec.update(mechanical_eligible=False,exclusion_reasons=['prior seen source URL; bounded slot consumed without reacquisition']);put(d/'acquisition.json',rec)
  event({'event':'candidate_excluded','query_id':q,'candidate_order':n,'url':c['url'],'reasons':rec['exclusion_reasons']});print(json.dumps(rec));return
 # Collector must be the sole retrieval mechanism. Any prior access consumes the retry budget;
 # if one occurs, log it and exclude/resolve manually rather than invoking this acquisition anew.
 for attempt in [1,2]:
  p=subprocess.run(['curl','--fail','--location','--max-redirs','5','--max-time','60','--silent','--show-error','--dump-header',str(d/f'headers-{attempt}.txt'),'--output',str(d/f'attempt-{attempt}.body'),'--write-out','%{http_code}\n%{url_effective}\n%{content_type}\n',c['url']],capture_output=True)
  (d/f'curl-{attempt}.metadata').write_bytes(p.stdout);(d/f'curl-{attempt}.stderr').write_bytes(p.stderr)
  rec['attempts'].append({'attempt':attempt,'timestamp_utc':now(),'returncode':p.returncode,'metadata':p.stdout.decode(errors='replace')})
  if p.returncode==0:
   shutil.copyfile(d/f'attempt-{attempt}.body',d/'original.pdf');break
 reasons=[]
 if p.returncode:reasons.append('access failure after one ordinary retry')
 else:
  original=d/'original.pdf';rec.update(original_sha256=sha(original),original_bytes=original.stat().st_size)
  response=p.stdout.decode(errors='replace').splitlines();rec['response_metadata']=response
  finalhost=urlparse(response[1]).hostname or '';domain=query(q)['official_domain']
  if not (finalhost==domain or finalhost.endswith('.'+domain)):reasons.append('redirect outside official query domain; no publisher substitution')
  mime=response[2].lower().split(';')[0].strip();rec['pdf_magic']=original.read_bytes().startswith(b'%PDF-');rec['response_mime']=mime
  if mime not in ['application/pdf','application/octet-stream'] or not rec['pdf_magic']:reasons.append('unsupported MIME or absent PDF magic; not verified official PDF response')
  if rec['original_bytes']>protocol['native_caps']['max_pdf_bytes']:reasons.append('original PDF byte cap')
  if rec['original_sha256'] in get(ROOT/'dedup-inventory.json')['blocked_original_hashes']:reasons.append('prior original exact hash')
  if any(x['document_id']=='doc-'+rec['original_sha256'][:12] for x in selected()):reasons.append('current-round original exact hash')
  if not reasons:
   try:
    from pypdf import PdfReader
    rec['pdf_pages']=len(PdfReader(original,strict=True).pages);assert rec['pdf_pages']>=1
    for t,args in [('pdfinfo',['-box']),('pdffonts',[]),('pdfimages',['-list'])]:
     p=subprocess.run([str(POP/t),*args,str(original)],capture_output=True);(d/(t+'.txt')).write_bytes(p.stdout);(d/(t+'.stderr')).write_bytes(p.stderr)
     if p.returncode:reasons.append(t+' diagnostics failure')
    p=subprocess.run([str(POP/'pdftotext'),'-layout','-enc','UTF-8',str(original),str(d/'native.txt')],capture_output=True);(d/'pdftotext.stderr').write_bytes(p.stderr)
    text=(d/'native.txt').read_bytes().decode('utf-8');rec.update(native_sha256=sha(d/'native.txt'),native_codepoints=len(text),native_bytes=(d/'native.txt').stat().st_size,formfeed_count=text.count('\f'))
    if p.returncode:reasons.append('native extraction failed')
    inv=get(ROOT/'dedup-inventory.json');rec['normalized_text_sha256']=textkey(text)
    if rec['native_sha256'] in inv['blocked_native_hashes']:reasons.append('prior exact native text')
    if rec['normalized_text_sha256'] in inv['blocked_normalized_text_hashes']:reasons.append('prior normalized native text')
    for item in selected():
     previous=(ROOT/'documents'/item['document_id']/'native.txt').read_text(encoding='utf-8')
     if textkey(previous)==textkey(text):reasons.append('current-round normalized native text')
    reasons+=native_reasons(text,rec['pdf_pages'],rec['original_bytes'],protocol['native_caps'])
    if sum(x['pdf_pages'] for x in selected())+rec['pdf_pages']>40:reasons.append('would exceed retained aggregate page cap')
   except Exception as e:reasons.append('unreadable/native extraction failure: '+type(e).__name__)
 rec.update(mechanical_eligible=not reasons,exclusion_reasons=reasons);put(d/'acquisition.json',rec)
 event({'event':'candidate_acquired','query_id':q,'candidate_order':n,'acquisition_path':str((d/'acquisition.json').relative_to(ROOT)),'mechanical_eligible':not reasons})
 if reasons:event({'event':'candidate_excluded','query_id':q,'candidate_order':n,'url':c['url'],'reasons':reasons})
 print(json.dumps(rec))

def review_pages(q,n):
 gate();current(q,n);d=ROOT/'candidates'/f'{q}-{n:02d}';acq=get(d/'acquisition.json');assert acq['mechanical_eligible']
 assert not list(d.glob('page-*.png')),'Review pages already rendered; inspect existing unchanged images.'
 p=subprocess.run([str(POP/'pdftoppm'),'-r','150','-png',str(d/'original.pdf'),str(d/'page')],capture_output=True);(d/'pdftoppm.stderr').write_bytes(p.stderr);assert p.returncode==0
 imgs=sorted(d.glob('page-*.png'),key=lambda p:int(re.search(r'page-(\d+)',p.name).group(1)));assert len(imgs)==acq['pdf_pages']
 print(json.dumps([{'page':i,'image_path':str(p.relative_to(ROOT)),'image_sha256':sha(p)} for i,p in enumerate(imgs,1)]))

def retain(q,n,note_path):
 protocol=gate();c=current(q,n);d=ROOT/'candidates'/f'{q}-{n:02d}';acq=get(d/'acquisition.json');note=get(note_path)
 allowed={'complete_notice','boundary_evidence','notice_identity','dedup_evidence','prior_notice_identity_duplicate','material_native_damage','source_stratum','stratum_basis','template_family','source_anomalies','body_coverage_verified','body_coverage_evidence'}
 assert set(note)==allowed and note['complete_notice'] is True and note['prior_notice_identity_duplicate'] is False and note['material_native_damage'] is False
 assert note['boundary_evidence'] and note['notice_identity'] and note['dedup_evidence']
 assert note['source_stratum'] in ['general_comment','conditional_control']
 assert acq['mechanical_eligible'] and note['body_coverage_verified'] is True
 coverage=note['body_coverage_evidence'];assert [x['page'] for x in coverage]==list(range(1,acq['pdf_pages']+1))
 imgs=sorted(d.glob('page-*.png'),key=lambda p:int(re.search(r'page-(\d+)',p.name).group(1)));assert len(imgs)==acq['pdf_pages'],'Render and visually inspect every original page before retention.'
 for x,img in zip(coverage,imgs):
  assert set(x)=={'page','substantive_body_present','native_body_present','native_matches_visual_body','evidence','image_sha256'}
  assert type(x['substantive_body_present']) is bool and type(x['native_body_present']) is bool and x['native_matches_visual_body'] is True and x['evidence'] and x['image_sha256']==sha(img)
  assert not x['substantive_body_present'] or x['native_body_present'] is True,'Captions alone do not establish native body coverage.'
 native=(d/'native.txt').read_bytes().decode('utf-8')
 reasons=native_reasons(native,acq['pdf_pages'],acq['original_bytes'],protocol['native_caps'])+quota(selected(),acq['state'],note['source_stratum'],acq['pdf_pages'])
 if reasons:
  event({'event':'candidate_excluded','query_id':q,'candidate_order':n,'url':c['url'],'reasons':reasons,'source_notes':note});return
 assert acq['original_sha256']==sha(d/'original.pdf') and acq['native_sha256']==sha(d/'native.txt')
 shutil.copyfile(d/'original.pdf',d/'input.pdf'); assert sha(d/'input.pdf')==acq['original_sha256']
 # Original review-page renders remain unchanged and hash-bound by per-page coverage notes.
 imgs=sorted(d.glob('page-*.png'),key=lambda p:int(re.search(r'page-(\d+)',p.name).group(1)));assert len(imgs)==acq['pdf_pages']
 doc='doc-'+acq['original_sha256'][:12];dest=ROOT/'documents'/doc;assert not dest.exists()
 prov={**acq,**note,'document_id':doc,'render_dpi':150,'input_equals_original':True,'planned_query_stratum':query(q)['planned_stratum'],'tools':{t:subprocess.run([str(POP/t),'-v'],capture_output=True).stderr.decode().splitlines()[0] for t in ['pdfinfo','pdffonts','pdfimages','pdftotext','pdftoppm']}}
 put(d/'provenance.json',prov);shutil.move(str(d),str(dest))
 event({'event':'candidate_retained','query_id':q,'candidate_order':n,'url':c['url'],'document_id':doc,'state':acq['state'],'stratum':note['source_stratum'],'pdf_pages':acq['pdf_pages'],'source_provenance':str((dest/'provenance.json').relative_to(ROOT))})
 print(json.dumps({'retained':doc,'success_stop':success(selected())}))

def exclude(q,n,reason):
 gate();c=current(q,n);assert reason
 event({'event':'candidate_excluded','query_id':q,'candidate_order':n,'url':c['url'],'reasons':[reason]})

def selftest():
 cap={'max_codepoints':30000,'max_pdf_bytes':25000000}
 assert native_reasons('x'*30000+'\f',1,100,cap)==['native codepoint cap']
 assert native_reasons('x'*29999+'\f',1,100,cap)==[]
 assert 'native text absent' in native_reasons('\f',1,100,cap)
 assert 'native page-map mismatch' in native_reasons('x',1,100,cap)
 items=[{'state':s,'stratum':'general_comment' if i<5 else 'conditional_control','pdf_pages':2} for i,s in enumerate(['A','A','B','C','C','D','E'])]
 assert 'six-state feasibility guard' in quota(items,'E','general_comment',1)
 assert not quota(items,'F','general_comment',1)
 assert 'source-stratum quota full' in quota(items,'F','conditional_control',1)
 assert not success(items)
 assert success(items+[{'state':'F','stratum':'general_comment','pdf_pages':1}])
 assert all(q['query'].endswith('filetype:pdf') for q in get(ROOT/'selection-plan.json')['queries'])
 assert len({q['state'] for q in get(ROOT/'selection-plan.json')['queries']})==24
 print('PASS: native cap boundary, empty/page-map checks, quotas, state feasibility, success stop and exact plan strings. No network calls.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('command',choices=['self-test','query-request','register-search','resolve-search','acquire','review-pages','retain','exclude']);p.add_argument('args',nargs='*');a=p.parse_args()
 if a.command=='self-test':selftest()
 elif a.command=='query-request':print(json.dumps(request(a.args[0])))
 elif a.command=='register-search':register(*a.args)
 elif a.command=='resolve-search':resolve_search(*a.args)
 elif a.command=='acquire':acquire(a.args[0],int(a.args[1]))
 elif a.command=='review-pages':review_pages(a.args[0],int(a.args[1]))
 elif a.command=='retain':retain(a.args[0],int(a.args[1]),a.args[2])
 elif a.command=='exclude':exclude(a.args[0],int(a.args[1]),a.args[2])
