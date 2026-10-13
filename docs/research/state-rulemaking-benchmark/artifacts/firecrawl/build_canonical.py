"""Read-only verification of captures; write an all-unit operational manifest."""
from pathlib import Path
import hashlib,json,re,datetime
root=Path(__file__).resolve().parent; corpus=root.parent; recovery=root/'recovery-1'
freeze=json.loads((corpus/'corpus-freeze.json').read_text())
assert hashlib.sha256((corpus/'corpus-freeze.json').read_bytes()).hexdigest()=='900f21e8a75d50444f12a0e3814d665a4f401a0d689194465d0b00467a762946'
for name,record in freeze['files'].items():
 assert hashlib.sha256((corpus/name).read_bytes()).hexdigest()==record['sha256'],name
initial=json.loads((root/'results.json').read_text()); result=json.loads((recovery/'results.json').read_text())
runs=[('recovery-1',result)]
for lane in ['initial-remaining','rate-limit-recovery']:
 path=root/lane/'results.json'
 if path.exists():runs.append((lane,json.loads(path.read_text())))
outcomes={};firsts={}
for lane,record in runs:
 for o in record['outcomes']:
  firsts.setdefault(o['fixture_id'],(lane,o));outcomes[o['fixture_id']]=(lane,o)
units=[]; credits=0; events=[]
for runlane,run in runs:
 for attempt in run['outcomes']:
  capture=root/runlane/attempt['fixture_id']/'parse-capture.json'
  if capture.exists():
   cap=json.loads(capture.read_text());events.extend([(cap['started_at'],1),(cap['ended_at'],-1)])
for f in freeze['units']:
 fid=f['fixture_id']; selected=outcomes.get(fid);lane,o=selected if selected else ('recovery-1',None); d=root/lane/fid; row={'fixture_id':fid,'input_sha256':f['input_sha256'],'input_page_count':f['input_page_count'],'initial_local_failure_path':f'firecrawl/{fid}/outcome.json' if (root/fid/'outcome.json').exists() else None,'recovery_outcome_path':f'firecrawl/{lane}/{fid}/outcome.json' if o else None,'status':'not_submitted_after_stop' if not o else 'captured' if o['success'] else 'operational_failure','failure_stage':o.get('failure_stage') if o else None,'failure_classification':None,'canonical_response_path':None,'markdown_path':None,'credits_reported':None,'parse_wall_ms':o.get('parse_wall_ms') if o else None}
 if o:
  row['timing_semantics']={'elapsed_ms':'Entire local pipeline wrapper wall time','parse_wall_ms':'Parse wrapper wall time; includes metadata capture and, in paced runs, request queue delay; not isolated API latency','actual_api_dispatch_timestamp_available':False}
  firstlane,first=firsts[fid];row['first_provider_attempt_path']=f'firecrawl/{firstlane}/{fid}/outcome.json';row['first_provider_attempt_success']=first['success'];row['rate_limit_recovered']=lane=='rate-limit-recovery' and o['success']
  responsefile=d/'parse-response.json' if (d/'parse-response.json').exists() else d/'phase-one-response.redacted.json'
  row['canonical_response_path']=str(responsefile.relative_to(corpus))
  response=json.loads(responsefile.read_text()); response=response.get('response',response)
  texts=[c.get('text','') for c in response.get('content',[]) if c.get('type')=='text']
  if not o['success']:
   row['failure_classification']='provider_rate_limit' if any('Rate limit exceeded' in s for s in texts) else 'other_retained_operational_failure'
   row['provider_error_code']=(response.get('structuredContent') or {}).get('error_code')
  if (d/'parse-capture.json').exists():
   cap=json.loads((d/'parse-capture.json').read_text())
   row['parse_capture_path']=str((d/'parse-capture.json').relative_to(corpus))
   row['final_response_unmodified']=cap['response_unmodified']
  if o['success']:
   p=response.get('structuredContent')
   if p is None:
    for s in texts:
     try:p=json.loads(s);break
     except json.JSONDecodeError:pass
   strings=[]
   def walk(x):
    if isinstance(x,dict):
     if isinstance(x.get('markdown'),str):strings.append(x['markdown'])
     for k,v in x.items():
      if k!='markdown':walk(v)
    elif isinstance(x,list):
     for v in x:walk(v)
   walk((p or {}).get('data',p)); assert len(set(strings))==1,fid
   raw=(d/'markdown.md').read_bytes(); assert raw==strings[0].encode(),fid
   assert hashlib.sha256(raw).hexdigest()==o['exact_markdown_capture']['sha256']
   row['markdown_path']=str((d/'markdown.md').relative_to(corpus)); row['exact_markdown']=o['exact_markdown_capture']
   values=[u['value'] for u in o['reported']['usage'] or [] if u['path'].endswith('/creditsUsed')]
   assert len(values)<=1
   if values:row['credits_reported']=values[0];credits+=values[0]
  if (d/'upload-receipt.json').exists():
   upload=json.loads((d/'upload-receipt.json').read_text()); assert upload['success'] and upload['input_sha256']==f['input_sha256'];row['upload_receipt_path']=str((d/'upload-receipt.json').relative_to(corpus))
 units.append(row)
active=maximum=0
for stamp,delta in sorted(events,key=lambda e:(e[0],e[1])):
 active+=delta;maximum=max(maximum,active);assert active>=0
assert active==0 and maximum<=2
scan=[]
for path in root.rglob('*.json'):
 text=path.read_text()
 assert not re.search(r'https://[^\s"<>]*(?:X-Goog-Signature|X-Amz-Signature)=',text,re.I),str(path)
 assert not re.search(r'"(?:x-goog-signature|policy)"\s*:\s*"(?!\[REDACTED)[A-Za-z0-9+/=]{40,}"',text,re.I),str(path)
 scan.append(str(path.relative_to(root)))
summary={'corpus_units':20,'initial_local_failures':4,'initial_phase_one_requests':4,'initial_http_uploads':0,'initial_final_parse_requests':0,'first_provider_attempt_units':len(firsts),'first_provider_attempt_successes':sum(o['success'] for lane,o in firsts.values()),'first_provider_attempt_failures':sum(not o['success'] for lane,o in firsts.values()),'rate_limit_recovery_units':sum(lane=='rate-limit-recovery' for lane,o in outcomes.values()),'rate_limit_recovered_captures':sum(u.get('rate_limit_recovered',False) for u in units),'total_setup_requests_including_local_failures':4+sum(len(r['outcomes']) for lane,r in runs),'total_successful_http_uploads':sum((root/lane/o['fixture_id']/'upload-receipt.json').exists() for lane,r in runs for o in r['outcomes']),'total_final_parse_requests':sum((root/lane/o['fixture_id']/'parse-request.redacted.json').exists() for lane,r in runs for o in r['outcomes']),'markdown_captures':sum(u['status']=='captured' for u in units),'remaining_provider_failures':sum(u['status']=='operational_failure' for u in units),'not_submitted_after_stop':sum(u['status']=='not_submitted_after_stop' for u in units),'known_reported_credits_sum':credits,'credits_total_known':False,'unknown_usage_note':'Setup responses and failed calls did not report credits; do not infer zero.','max_observed_concurrent_final_parse_calls':maximum,'timing_limitation':'Recorded request/capture timestamps precede pacing waits. Wall times include wrapper overhead and pacing queue delay; isolated API latency unavailable. No job was rerun for timing.','all_frozen_files_unchanged':True,'all_successful_markdown_exact':True,'credential_scan_json_files':len(scan),'runs':[{'directory':'firecrawl/'+lane,'results_path':'firecrawl/'+lane+'/results.json','stopped':r['stopped'],'completion_order':r['completion_order']} for lane,r in runs]}
manifest={'version':1,'freeze_sha256':result['freeze_sha256'],'initial_run_results':'firecrawl/results.json','recovery_run_results':'firecrawl/recovery-1/results.json','execution_amendment':'execution-amendment-1.json','execution_note':'execution-note-2.json','summary':summary,'units':units}
(root/'canonical-results.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(summary))
