"""Independent offline audit of terminal lanes; no provider calls or lane writes."""
import json,re,hashlib,collections,statistics
from pathlib import Path
import audit
R=audit.ROOT; O=audit.OUT
checks=[];issues=[];inventory=[];secrets=[]
def ck(name,ok,details,paths=()):
 checks.append(dict(check_id=name,status='pass' if ok else 'fail',details=details,evidence_paths=list(paths)))
 if not ok:issues.append(name)
def read(p):return json.loads(p.read_text())
def rel(p):return str(p.relative_to(R))
def elapsed(x):return round((audit.dt(x['ended_at'])-audit.dt(x['started_at'])).total_seconds()*1000)
def markdown(x):
 strings=[]
 def walk(y):
  if isinstance(y,dict):
   if isinstance(y.get('markdown'),str):strings.append(y['markdown'])
   for k,v in y.items():
    if k!='markdown':walk(v)
  elif isinstance(y,list):
   for v in y:walk(v)
 walk(x);return list(set(strings))
def stopreview(rows,success,sequence):
 rows=sorted(rows,key=lambda x:x[sequence]);streak=0;trigger=None
 for x in rows:
  streak=0 if success(x) else streak+1
  if streak>=3 and trigger is None:trigger=x
 return dict(completion_ids=[x.get('fixture_id','')+(':'+x['tier'] if 'tier' in x else '') for x in rows],trigger=None if not trigger else {'fixture_id':trigger['fixture_id'],'ended_at':trigger['ended_at'],'sequence':trigger[sequence]},no_dispatch_after_trigger=trigger is None or all(audit.dt(x['started_at'])<=audit.dt(trigger['ended_at']) for x in rows))
f,units,freezechecks=audit.validate_freeze();checks.extend(freezechecks)
ll=R/'llama'; ledger=read(ll/'call-ledger.json'); plan=read(ll/'execution-plan.json');caps=[]
ck('llama-ledger-coverage',len(ledger)==40 and {(x['fixture_id'],x['tier']) for x in ledger}=={(i,t) for i in units for t in ['agentic','agentic_plus']},'40 unique frozen fixture/tier pairs',['llama/call-ledger.json'])
ck('llama-ledger-inputs',all(x['input_sha256']==units[x['fixture_id']]['input_sha256'] and x['pages']==units[x['fixture_id']]['input_page_count'] for x in ledger),'All ledger inputs match freeze')
for p in sorted(ll.glob('runs/*/*/capture.json')):
 x=read(p);fid=x['fixture_id'];u=units[fid];up=read(ll/'uploads'/f'{fid}-attempt.json');ur=read(ll/'uploads'/f'{fid}-response.json')
 ok=x==read(p.parent/'tool-envelope.json') and x['request']=={'fileId':x['file_id'],'markdown':True,'tier':x['tier'],'version':'latest'} and x['file_id']==ur['file_id']==up['file_id'] and x['input_sha256']==up['local_input_sha256']==u['input_sha256'] and x['input_byte_length']==up['input_byte_length']==u['input_bytes'] and x['input_page_count']==u['input_page_count']
 for i,b in enumerate(x['response'].get('content',[])):
  if b.get('type')=='text':ok=ok and (p.parent/f'response-text-{i:02}.txt').read_bytes()==b['text'].encode()
 ck('llama-capture-'+fid+'-'+x['tier'],ok and abs(elapsed(x)-x['elapsed_ms'])<=1,'Input/upload IDs, exact request/envelope/text and elapsed time match',[rel(p)])
 caps.append(x)
hashes=read(ll/'artifact-hashes.json');ck('llama-retained-hash-ledger',all((ll/x['path']).exists() and audit.sha(ll/x['path'])==x['sha256'] and (ll/x['path']).stat().st_size==x['bytes'] for x in hashes),{'entries':len(hashes)})
stop=stopreview(caps,lambda x:x['outcome']=='completed','completion_order');conc=audit.concurrency([dict(x,call_id=x['fixture_id']+x['tier']) for x in caps]);
ck('llama-concurrency-stop',conc['maximum_two_observed'] and stop['no_dispatch_after_trigger'] and len(caps)==4 and sum(x['outcome']=='not_attempted_provider_stopped' for x in ledger)==36,dict(concurrency=conc,stop=stop))
ck('llama-completion-order', [x['completion_order'] for x in sorted(caps,key=lambda x:audit.dt(x['ended_at']))]==list(range(1,len(caps)+1)),'Sequence agrees with retained end timestamps')
llreport=dict(final=True,attempted=len(caps),timeouts=sum(x['outcome']=='timeout_backend_unknown' for x in caps),outputs=sum(x['outcome']=='completed' for x in caps),unattempted=40-len(caps),uploaded_units=2,concurrency=conc,stop=stop,returned_usage=[audit.public_metadata(x['response'])['reported_usage'] for x in caps],actual_cost=None,backend_completion='unknown after tool timeouts',successful_latency_ms=None,failure_elapsed_ms=[x['elapsed_ms'] for x in caps])
fc=R/'firecrawl';phases=[];allpipes=[];allparses=[];credits=0;calls=0;uploads=0;setup=0;successful=[];raterejected=[];immutable=[]
for lane in ['', 'recovery-1','initial-remaining','rate-limit-recovery']:
 d=fc/lane;p=d/'results.json';result=read(p);rows=[]
 pre=read(d/'preflight.json');ck('firecrawl-preflight-'+(lane or 'original'),pre['freeze_sha256']==audit.EXPECTED and len(pre['fixtures'])==(6 if lane in ['initial-remaining','rate-limit-recovery'] else 20) and all(x['input_sha256']==units[x['fixture_id']]['input_sha256'] and x['input_bytes']==units[x['fixture_id']]['input_bytes'] for x in pre['fixtures']),{'fixtures':len(pre['fixtures']),'schema_mismatch_resolved':True},[rel(d/'preflight.json')])
 for supplied in result['outcomes']:
  fid=supplied['fixture_id'];fd=d/fid;u=units[fid];x=read(fd/'outcome.json');rows.append(x);allpipes.append(dict(x,call_id=(lane or 'original')+':'+fid));req=read(fd/'phase-one-request.json');setup+=1
  ck('firecrawl-outcome-'+(lane or 'original')+'-'+fid,x==supplied and req['input_sha256']==u['input_sha256'] and req['input_page_count']==u['input_page_count'] and abs(elapsed(x)-x['elapsed_ms'])<=1,'Result ledger, setup input metadata, and total pipeline elapsed match',[rel(fd/'outcome.json')])
  upfile=fd/'upload-receipt.json'
  if upfile.exists():
   up=read(upfile);uploads+=1;ck('firecrawl-upload-'+lane+'-'+fid,up['success'] and up['input_sha256']==u['input_sha256'] and up['uploaded_pdf_bytes']==u['input_bytes'] and up['http_status'] in [200,201,204],{'uploaded_bytes':up['uploaded_pdf_bytes'],'local_wall_ms':up['local_wall_ms'],'http_elapsed_ms':up['elapsed_seconds']*1000},[rel(upfile)])
  elif not lane:ck('firecrawl-original-no-submission-'+fid,not (fd/'parse-request.redacted.json').exists() and not (fd/'parse-response.json').exists(),'No HTTP upload receipt or final request/response retained; original failure stage is upload')
  cp=fd/'parse-capture.json'
  responsefile=fd/'parse-response.json' if cp.exists() else fd/'phase-one-response.redacted.json';resp=read(responsefile);resp=resp.get('response',resp)
  errtext=' '.join(b.get('text','') for b in resp.get('content',[]) if b.get('type')=='text')
  if 'Rate limit exceeded' in errtext:raterejected.append(dict(fixture_id=fid,phase=lane,stage=x['failure_stage'],explicit_rate_rejection=True,accepted_job_id_returned=bool(audit.public_metadata(resp)['returned_identifiers'])))
  if cp.exists():
   c=read(cp);calls+=1;allparses.append(dict(c,call_id=lane+':'+fid));q=read(fd/'parse-request.redacted.json');settings={'formats':['markdown'],'parsers':['pdf'],'onlyMainContent':False,'pdfOptions':{'maxPages':u['input_page_count']}}
   ok=c['input_sha256']==q['input_sha256']==u['input_sha256'] and q['input_bytes']==u['input_bytes'] and c['settings']==settings and q['request']==dict(settings,uploadRef='[REDACTED_UPLOAD_REFERENCE]') and abs(elapsed(c)-c['wall_ms'])<=1 and x['parse_wall_ms']==c['wall_ms']
   ck('firecrawl-parse-'+lane+'-'+fid,ok,'Frozen input, redacted request, capture settings and timed interval match',[rel(cp)])
   immutable.append({'path':rel(responsefile),'response_unmodified_claim':c['response_unmodified'],'redaction_exception_declared':c['redaction_exception'] is not None})
   if x['success']:
    s=markdown(resp.get('structuredContent') or resp);raw=(fd/'markdown.md').read_bytes();exact=x['exact_markdown_capture'];
    ck('firecrawl-exact-text-'+lane+'-'+fid,len(s)==1 and raw==s[0].encode() and audit.sha(fd/'markdown.md')==exact['sha256'] and len(raw)==exact['byte_length'] and raw.endswith(b'\n')==exact['terminal_newline'],'Derived markdown exactly matches retained response string/hash/length/newline',[rel(fd/'markdown.md'),rel(responsefile)])
    usage=audit.public_metadata(resp)['reported_usage'] or [];v=[i['value'] for i in usage if i['path'].endswith('/creditsUsed')];credits+=sum(v);successful.append(dict(fixture_id=fid,phase=lane,parse_interval_including_queue_ms=c['wall_ms'],pipeline_ms=x['elapsed_ms'],credits_reported=sum(v) if v else None))
 stop=stopreview(rows,lambda x:x['success'],'completion_sequence');co=[x['fixture_id'] for x in sorted(rows,key=lambda x:x['completion_sequence'])];streak=0;streakok=True
 for x in sorted(rows,key=lambda x:x['completion_sequence']):
  streak=0 if x['success'] else streak+1;streakok=streakok and x['consecutive_failures_after_completion']==streak
 ck('firecrawl-stop-'+(lane or 'original'),stop['no_dispatch_after_trigger'] and streakok and co==result['completion_order'] and result['stopped']==(stop['trigger'] is not None),stop,[rel(p)])
 phases.append(dict(directory=rel(d),pipelines=len(rows),successes=sum(x['success'] for x in rows),failures=sum(not x['success'] for x in rows),concurrency=audit.concurrency([dict(x,call_id=x['fixture_id']) for x in rows]),stop=stop))
fcconc=audit.concurrency(allpipes);parseconc=audit.concurrency(allparses);ck('firecrawl-completed-global-concurrency',fcconc['maximum_two_observed'] and parseconc['maximum_two_observed'],dict(pipelines=fcconc,final_parse_intervals=parseconc))
ck('firecrawl-six-explicit-rejections',{x['fixture_id'] for x in raterejected}=={'A05','A06','B01','B02','B03','B04'} and not any(x['accepted_job_id_returned'] for x in raterejected),raterejected)
can=read(fc/'canonical-results-before-rate-recovery.json');ck('firecrawl-historical-canonical-coverage',len(can['units'])==20 and {x['fixture_id'] for x in can['units']}==set(units) and all(x['input_sha256']==units[x['fixture_id']]['input_sha256'] for x in can['units']) and sum(x['status']=='captured' for x in can['units'])==8,'Historical snapshot after recovery-1: 8 captures, 6 rejections, 6 unattempted. Completed initial-remaining adds 6 verified captures.')
# Snapshot all terminal provider artifacts.
paths=list(ll.rglob('*'))+list(fc.glob('*'))
for lane in ['recovery-1','initial-remaining','rate-limit-recovery']:paths+=list((fc/lane).rglob('*'))
for p in sorted(set(paths)):
 if not p.is_file():continue
 inventory.append(dict(path=rel(p),sha256=audit.sha(p),bytes=p.stat().st_size))
 if p.suffix not in ['.json','.txt','.md','.py','.mjs']:continue
 try:s=p.read_text()
 except UnicodeDecodeError:continue
 found=[]
 if p.suffix=='.json':
  try:found=audit.secret_categories(json.loads(s))
  except ValueError:pass
 patterns={'signed URL credential pattern':r'https?://[^\s"<>]*(?:X-Goog-Signature|X-Amz-Signature|expires_at|X-Amz-Credential)=','unsanitized upload form credential':r'"(?:x-goog-signature|policy|uploadRef)"\s*:\s*"(?!\[REDACTED)[A-Za-z0-9+/=_-]{40,}"'}
 for category,pattern in patterns.items():
  if re.search(pattern,s,re.I):found.append(dict(json_path=None,category=category))
 if found:secrets.append(dict(path=rel(p),findings=found))
ck('completed-evidence-secret-scan',not secrets,{'scanned_files':len(inventory),'findings':secrets})
canonical=read(fc/'canonical-results.json'); mapped=[]
for row in canonical['units']:
 fid=row['fixture_id'];cp=R/row['canonical_response_path'];mp=R/row['markdown_path'];op=R/row['recovery_outcome_path'];up=R/row['upload_receipt_path'];cap=R/row['parse_capture_path'];first=R/row['first_provider_attempt_path'];outcome=read(op);firstoutcome=read(first);u=units[fid]
 ok=row['status']=='captured' and outcome['success'] and row['input_sha256']==u['input_sha256'] and row['input_page_count']==u['input_page_count'] and mp.parent==cp.parent==op.parent==up.parent==cap.parent and row['exact_markdown']==outcome['exact_markdown_capture'] and audit.sha(mp)==row['exact_markdown']['sha256'] and row['first_provider_attempt_success']==firstoutcome['success'] and row['rate_limit_recovered']==('rate-limit-recovery' in str(op))
 ck('canonical-mapping-'+fid,ok,'Canonical response, markdown, outcome, capture, upload and initial attempt resolve to verified fixture artifacts',[rel(cp),rel(mp),rel(first)])
 mapped.append(fid)
ck('canonical-final-completeness',len(mapped)==20 and set(mapped)==set(units),'20 distinct verified frozen fixtures, all with exact returned markdown')
summary=canonical['summary'];recovered={x['fixture_id'] for x in canonical['units'] if x['rate_limit_recovered']};expectedrecover={'A05','A06','B01','B02','B03','B04'}
ck('canonical-final-counts',summary['total_setup_requests_including_local_failures']==setup==30 and summary['total_successful_http_uploads']==uploads==24 and summary['total_final_parse_requests']==calls==24 and summary['markdown_captures']==len(successful)==20 and summary['known_reported_credits_sum']==credits==34 and summary['first_provider_attempt_successes']==14 and summary['first_provider_attempt_failures']==6 and summary['rate_limit_recovered_captures']==6,dict(setup_requests=setup,uploads=uploads,final_requests=calls,captures=len(successful),reported_credit_subtotal=credits))
rr=read(fc/'rate-limit-recovery/results.json');elig=read(fc/'rate-limit-recovery/recovery-eligibility.json');note3=read(R/'execution-note-3.json');firstphase=read(fc/'recovery-1/results.json');amend=read(R/'execution-amendment-1.json');note2=read(R/'execution-note-2.json')
ck('single-authorized-rate-recoveries',recovered==expectedrecover=={x['fixture_id'] for x in rr['outcomes']}=={x['fixture_id'] for x in elig['units']} and len(rr['outcomes'])==6 and all(audit.dt(x['started_at'])>audit.dt(note3['at_utc']) for x in rr['outcomes']) and all(not read(R/x['first_provider_attempt_path'])['success'] for x in canonical['units'] if x['rate_limit_recovered']),{'recovered_fixture_ids':sorted(recovered),'one_pipeline_each':True,'after_note3':True})
ck('authorized-local-transport-recovery',all(audit.dt(x['started_at'])>audit.dt(amend['at_utc']) for x in firstphase['outcomes']) and {x['fixture_id'] for x in read(fc/'results.json')['outcomes']}=={'A01','A02','A03','A04'},'Four original local failures retained; recovery-1 follows prospective authorization')
ck('authorized-paced-continuation',all(audit.dt(x['started_at'])>audit.dt(note2['at_utc']) for x in read(fc/'initial-remaining/results.json')['outcomes']),'Never-submitted B05-B10 began after documented continuation authorization')
previous=read(O/'completed-phases-artifact-inventory.json');changes=[];rawcount=0
for item in previous:
 p=R/item['path']
 if p.name in ['outcome.json','parse-response.json','parse-capture.json','markdown.md','capture.json','tool-envelope.json','upload-receipt.json'] or p.name.startswith('response-text-'):
  rawcount+=1
  if not p.exists() or audit.sha(p)!=item['sha256']:changes.append(item['path'])
ck('prior-raw-artifacts-retained',not changes,{'prior_raw_artifacts_checked':rawcount,'changed_paths':changes})
notes=[]
for n in ['execution-amendment-1.json','execution-note-2.json','execution-note-3.json']:
 p=R/n;notes.append(dict(path=n,sha256=audit.sha(p),decision=read(p)['decision']))
report=dict(schema_version='operations-audit-v1',phase='final_independent_operations_review',reviewed_at_utc=audit.utc(),freeze_sha256=audit.EXPECTED,checks=checks,issue_check_ids=issues,llama=llreport,firecrawl=dict(final=True,completed_phases=phases,setup_requests=setup,successful_http_uploads=uploads,final_parse_requests=calls,successful_captures=len(successful),reported_credits_on_successes=credits,total_usage_known=False,actual_cost=None,success_details=successful,explicit_rate_rejections=raterejected,response_provenance=immutable,concurrency=fcconc,final_parse_concurrency=parseconc),execution_authorizations=notes,security_findings=secrets,limitations=['No independent HTTP wire bytes exist; JSON response object preservation is recorded, and exact markdown equivalence is independently checked against retained objects.','Firecrawl response_unmodified is a capture claim; no separate original tool envelope is retained for independent original-object comparison.','Signed upload instructions and uploadRefs were intentionally not retained; file hashes/bytes and receipts support mappings but direct replay of transient URLs is unavailable.','Paced harness timestamps precede pacing waits, so parse/phase-one intervals include queue delay; actual endpoint dispatch spacing and pure vendor latency cannot be reconstructed from these timestamps. Code inspection shows a shared 7000ms dispatch gate in paced continuation.','Original Firecrawl no-upload/no-final-submission assertion is supported by local failure artifacts and absence of corresponding receipts; absence alone cannot independently prove a network negative.','Recovery-1 launched B04 17ms after B02 ended at the third consecutive failure; timestamp-based stop compliance fails. Scheduler may have consumed B03 and launched B04 before consuming already-completed B02; no completion-consumption timestamps establish this boundary. Original finding is retained for primary interpretation.','Llama timeouts leave backend completion and billing unknown. No parse-quality conclusion follows from zero returned outputs.','Latest is requested rather than a verified backend release pin; published price assumptions are not actual bills.'])
audit.save('final-artifact-inventory.json',inventory);audit.save('final-review.json',report)
print(json.dumps({'checks':len(checks),'failed_checks':issues,'security_paths':[x['path'] for x in secrets],'llama':{'timeouts':llreport['timeouts'],'unattempted':llreport['unattempted']},'firecrawl':{'captures':len(successful),'reported_credits':credits,'setup_requests':setup,'final_requests':calls},'final_firecrawl_completeness':'verified with retained stop-boundary finding'}))
