"""Offline REST active-phase audit; no credentials or network calls."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re,collections
ROOT=Path('/Users/home/.codex/worktrees/e8f4/yokel/docs/research/state-rulemaking-benchmark/artifacts/execution-api-1');OUT=ROOT/'operations-review';OUT.mkdir(exist_ok=True);P=ROOT.parent
EXPECTED='900f21e8a75d50444f12a0e3814d665a4f401a0d689194465d0b00467a762946'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def dt(s):return datetime.fromisoformat(s.replace('Z','+00:00'))
def rel(p):return str(p.relative_to(ROOT))
checks=[];gaps=[];jobs=[];inv=[]
def ck(i,ok,d,paths=[]):checks.append(dict(check_id=i,status='pass' if ok else 'fail',details=d,evidence_paths=paths))
audit_start=datetime.now(timezone.utc); statebytes=(ROOT/'state.json').read_bytes();state=json.loads(statebytes);amend=read(ROOT/'primary-execution-amendment-5.json');gate=read(ROOT/'primary-pilot-gate.json');freeze=read(P/'corpus-freeze.json');units={u['fixture_id']:u for u in freeze['units']};runner=P.parent/'run_llama_api.py';code=runner.read_text();plan=state['plan']
ck('freeze-digest',sha(P/'corpus-freeze.json')==EXPECTED==plan['freeze_sha256'],EXPECTED)
bad=[]
for n,m in freeze['files'].items():
 p=P/n
 if not p.is_file() or sha(p)!=m['sha256'] or p.stat().st_size!=m['bytes']:bad.append(n)
ck('141-frozen-artifacts',not bad,{'count':len(freeze['files']),'mismatches':bad})
ck('runner-sha-before-pilot',sha(runner)==amend['runner_sha256'],{'script_sha256':sha(runner),'amendment_adopted_at':amend['adopted_at_utc']})
ck('runner-tls-and-barrier',not any(x in code for x in ['_create_unverified_context','CERT_NONE','check_hostname = False']) and 'build_opener(NoRedirect())' in code and 'if not active and not reconcile_only and not self.state["stopped"]:' in code,'Code has default verified HTTPS and NoRedirect; pair barrier retained. Runtime CA repair is primary-reported, not independently reexecuted.')
excluded={tuple(x) for x in plan['completed_excluded']};pairs={(j['fixture_id'],j['tier']) for j in plan['jobs']};allpairs={(f,t) for f in units for t in ['agentic','agentic_plus']}
ck('remaining-plan-no-duplicates',len(plan['jobs'])==len(pairs)==28 and len(excluded)==12 and pairs.isdisjoint(excluded) and pairs|excluded==allpairs and plan['max_active']==2 and plan['stop_consecutive_failures']==3 and plan['version']=='latest','28 remaining pairs, excluding prior 12 completed; maximum two and stop three')
ck('resume-plan-hash',sha(P/'execution-dashboard-1/resume-state.json')==plan['resume_sha256'],'Frozen resume plan digest matches')
for j in plan['jobs']:
 u=units[j['fixture_id']];p=P/j['input_path'];ck('input-'+j['fixture_id']+'-'+j['tier'],j['input_sha256']==u['input_sha256']==sha(p) and j['input_bytes']==u['input_bytes']==p.stat().st_size and j['pages']==u['input_page_count'],'Exact frozen input hash/bytes/page metadata',[str(p.relative_to(P))])
http={}
# Only paired receipts complete as of initial audit timestamp; ongoing orphan response writes excluded.
for p in sorted((ROOT/'http').glob('*.json')):
 if p.name.endswith('.response.json'):continue
 x=read(p)
 if dt(x['received_at_utc'])>audit_start:continue
 http[rel(p)]=x;rp=ROOT/x['raw_response_path'] if x.get('raw_response_path') else None
 ok=not rp or (rp.is_file() and read(rp)==x['response'])
 ck('http-body-'+p.stem,ok and (x['raw_response_bytes_unmodified']==x['response_object_unmodified']) and bool(x['redaction_exception'])==(not x['response_object_unmodified']),'Retained response JSON equals receipt object; preservation/sanitization flags agree',[rel(p)]+([rel(rp)] if rp else []))
 delta=(dt(x['received_at_utc'])-dt(x['actual_dispatch_at_utc'])).total_seconds()*1000
 ck('http-timing-'+p.stem,0<=delta and abs(delta-x['http_wall_ms'])<=5,{'actual_dispatch_at_utc':x['actual_dispatch_at_utc'],'received_at_utc':x['received_at_utc'],'http_wall_ms':x['http_wall_ms']})
posts=[(p,x) for p,x in http.items() if x['method']=='POST' and x['path']=='/api/v2/parse'];postids=[x['response'].get('id') for p,x in posts];ck('post-job-uniqueness',len(postids)==len(set(postids)) and all(postids),'One retained accepted POST per unique parse job ID')
submitted=[j for j in state['jobs'] if j.get('job_id')];ck('state-job-intent-uniqueness',len({j['job_id'] for j in submitted})==len(submitted) and len({j['intent_token'] for j in state['jobs']})==28,'Unique job IDs; 28 durable intents')
files=state['files'];ck('file-identities',len({v['file_id'] for v in files.values()})==len(files),'File IDs distinct across fixtures; sharing across tiers is expected')
for fid,v in files.items():ck('remote-input-proof-'+fid,v['phase']=='verified' and v['download_sha256']==units[fid]['input_sha256'],'State retains downloaded remote input hash proof; remote bytes are not persisted')
complete=[];active=[]
for j in state['jobs']:
 fid=j['fixture_id'];tier=j['tier'];ident=fid+'-'+tier
 if not j.get('request'):continue
 q=j['request'];expected=dict(plan['config_template']);expected.update(file_id=j['file_id'],tier=tier,user_metadata={'benchmark_run':'execution-api-1','intent_token':j['intent_token'],'input_sha256':j['input_sha256'],'tier':tier})
 ck('request-config-'+ident,q==expected and 'target_pages' not in q and 'max_pages' not in q and 'parsing_instruction' not in q,'Exact plan config, latest, no limits/prompts. Request is durable state object; receipt does not retain wire request body.')
 matches=[(p,x) for p,x in posts if x['response'].get('id')==j.get('job_id')]
 if j.get('job_id') is None and j['phase'] in ['submit_inflight','submit_uncertain']:
  checks.append(dict(check_id='accepted-receipt-'+ident,status='pending',details='Submission in flight or acceptance uncertain at atomic state cut; no missing-receipt failure inferred',evidence_paths=[]))
 else:
  ck('accepted-receipt-'+ident,len(matches)==1 and matches[0][1]['response']['user_metadata']==q['user_metadata'] and matches[0][1]['response']['tier']==tier and dt(matches[0][1]['actual_dispatch_at_utc'])>=dt(amend['adopted_at_utc']),'POST response IDs, intent/hash/tier metadata and prospective authorization agree')
 if j['phase'] not in ['completed','failed']:
  active.append({'fixture_id':fid,'tier':tier,'phase':j['phase'],'job_id':j.get('job_id')});continue
 cap=read(ROOT/j['capture']);result=read(ROOT/f'runs/{fid}/{tier}/output.json');raw=read(ROOT/cap['terminal_api_capture']);pageitems=result.get('markdown',{}).get('pages',[]);numbers=[p['page_number'] for p in pageitems];u=units[fid]
 ck('terminal-capture-'+ident,cap['job_id']==result['job']['id']==j['job_id'] and cap['file_id']==j['file_id']==files[fid]['file_id'] and cap['config']==q and cap['input_sha256']==u['input_sha256'] and cap['input_bytes']==u['input_bytes'] and cap['pages']==u['input_page_count'] and cap['status']==result['job']['status']=='COMPLETED' and cap['operational_success'] and not cap['operation_anomalies'] and raw['response']==result,'Terminal raw/sanitized response, state, capture and input mappings agree',[j['capture'],cap['terminal_api_capture']])
 ck('page-evidence-'+ident,len(pageitems)==u['input_page_count'] and len(set(numbers))==len(numbers) and set(numbers) in [set(range(u['input_page_count'])),set(range(1,u['input_page_count']+1))] and all(p.get('success') is True for p in pageitems),'Expanded Markdown page count/ordinals/success cover input')
 for o in cap['outputs']:
  p=ROOT/o['path'];ck('output-hash-'+ident+'-'+p.suffix,sha(p)==o['sha256'] and p.stat().st_size==o['bytes'],'Output hash and byte count agree',[rel(p)])
 md=ROOT/f'runs/{fid}/{tier}/output.md';ck('exact-markdown-'+ident,md.read_bytes()==result['markdown_full'].encode('utf-8') and result['markdown_full']==raw['response']['markdown_full'],'Whole provider string preserved byte-for-byte, not reassembled from pages')
 ck('usage-'+ident,cap['returned_usage']==result['job'].get('usage')==raw['response']['job'].get('usage'),'Returned usage retained unchanged; absence remains unavailable')
 if result['job'].get('file_id') is None:gaps.append({'fixture_id':fid,'tier':tier,'gap':'Terminal result lacks direct file_id; mapping relies on durable request, file proof and POST intent/hash echo'})
 if result['job'].get('version') is None:gaps.append({'fixture_id':fid,'tier':tier,'gap':'Backend resolved version unavailable; latest requested only'})
 trans=(cap.get('job_metadata') or {}).get('state_transitions',{});start=j['submit_started_at_utc'];end=cap['observed_at_utc'];ck('terminal-order-'+ident,dt(start)<dt(end)<=dt(j['observed_at_utc']) and (not trans.get('completed_at') or dt(start)<=dt(trans['completed_at'])<=dt(end)),'Submission before backend completion before terminal observation/state completion')
 complete.append(j);jobs.append(dict(fixture_id=fid,tier=tier,job_id=j['job_id'],file_id=j['file_id'],started_at_utc=start,terminal_observed_at_utc=end,state_completed_observed_at_utc=j['observed_at_utc'],reported_usage=cap['returned_usage'],backend_state_transitions=trans,returned_latency=(cap.get('job_metadata') or {}).get('latency'),http_body_unmodified=raw['raw_response_bytes_unmodified'],http_object_unmodified=raw['response_object_unmodified'],redaction_exception=raw['redaction_exception']))
# Bound accepted/in-flight provider intervals by POST dispatch to terminal observation, or audit start if active.
points=[]
for j in submitted:
 match=[x for _,x in posts if x['response'].get('id')==j['job_id']]
 if not match:continue
 begin=match[0]['actual_dispatch_at_utc'];end=j.get('observed_at_utc') if j['phase'] in ['completed','failed'] else audit_start.isoformat();points.extend([(dt(begin),1),(dt(end),-1)])
peak=cur=0
for t,d in sorted(points,key=lambda x:(x[0],x[1])):cur+=d;peak=max(peak,cur)
ck('snapshot-concurrency',peak<=2 and len(active)<=2,{'post-dispatch-to-terminal-observation_upper_bound':peak,'active_in_state_snapshot':len(active)})
ordered=sorted(submitted,key=lambda j:dt(j['submit_started_at_utc']));barrier=True
for i,j in enumerate(ordered):
 if i<2:continue
 earlier=ordered[:i];running=[x for x in earlier if x['phase'] not in ['completed','failed'] or dt(x['observed_at_utc'])>dt(j['submit_started_at_utc'])]
 if len(running)>1:barrier=False
ck('observed-dispatch-slot-bound',barrier,'No dispatch observed while two prior jobs lack terminal observations; pilot/invocation boundaries retained')
order=[tuple(x) for x in state['completion_order']];lookup={(j['fixture_id'],j['tier']):j for j in complete};streak=0;trigger=None
for pair in order:
 j=lookup[pair];streak=0 if j['phase']=='completed' else streak+1
 if streak>=3 and trigger is None:trigger=j
ck('snapshot-stop-ledger',len(order)==len(lookup) and set(order)==set(lookup) and streak==state['consecutive_failures'] and state['stopped']==bool(trigger),'No failures so far; threshold not exercised. Scheduler code and offline checks are separate evidence.')
# Preserve prior dashboards and baseline reviews; do not refresh or modify them.
db=P/'execution-dashboard-1/operations-review';dbreport=read(db/'snapshot-review.json');dbinv=read(db/'snapshot-artifact-inventory.json');changes=[x['path'] for x in dbinv if sha(P/'execution-dashboard-1'/x['path'])!=x['sha256']];ck('prior-dashboard-eight-preserved',len(dbreport['checks'])==110 and not dbreport['failed_checks'] and not changes,{'prior_checks':110,'changed_snapshot_paths':changes})
secrets=[]
for p in sorted([x for x in ROOT.rglob('*') if x.is_file() and OUT not in x.parents]):
 if p.name=='state.json':inv.append({'path':rel(p),'sha256':hashlib.sha256(statebytes).hexdigest(),'bytes':len(statebytes),'snapshot':'initial atomic state read'});continue
 if p.parent==ROOT/'http' and p.name not in {Path(n).name for n in http}|{Path(x['raw_response_path']).name for x in http.values() if x.get('raw_response_path')}:continue
 inv.append({'path':rel(p),'sha256':sha(p),'bytes':p.stat().st_size})
 if p.suffix in ['.json','.jsonl','.md']:
  s=p.read_text()
  if re.search(r'https?://[^\s"<>]*(?:X-Amz-Signature|X-Goog-Signature|X-Amz-Credential)=|Bearer\s+[A-Za-z0-9._-]{12,}|"(?:api_key|access_token)"\s*:\s*"(?!\[REDACTED)[^"\n]+"',s,re.I):secrets.append({'path':rel(p),'category':'credential or signed URL pattern'})
if re.search(r'https?://[^\s"<>]*(?:X-Amz-Signature|X-Goog-Signature|X-Amz-Credential)=|Bearer\s+[A-Za-z0-9._-]{12,}|"(?:api_key|access_token)"\s*:\s*"(?!\[REDACTED)[^"\n]+"',statebytes.decode(),re.I):secrets.append({'path':'state.json','category':'credential or signed URL pattern'})
ck('snapshot-secret-pattern-scan',not secrets,{'findings':secrets})
usage=[j['reported_usage'].get('credits') for j in jobs if isinstance(j['reported_usage'],dict) and isinstance(j['reported_usage'].get('credits'),(int,float))]
pilot=next(j for j in jobs if (j['fixture_id'],j['tier'])==('A06','agentic_plus'))
ck('pilot-gate-before-expansion',gate['passed'] and gate['job_id']==pilot['job_id'] and gate['actual_reported_credits']==pilot['reported_usage']['credits']==90 and all(dt(j['started_at_utc'])>=dt(gate['checked_at_utc']) for j in jobs if j['job_id']!=pilot['job_id']),'Pilot completed with 90 returned credits; passing gate precedes expansion submissions',['primary-pilot-gate.json'])
# Final full-run reconciliation and retained baseline integrity.
ck('final-rest-completeness',len(complete)==28 and not active and all(j['phase']=='completed' for j in state['jobs']) and len(posts)==28 and len(usage)==28 and not state['stopped'] and state['consecutive_failures']==0,'28 complete captures/unique POSTs/returned usage; zero failures, pending or active')
ck('rest-returned-usage-vs-estimate',sum(usage)==1555==amend['nominal_remaining_credits'],'All 28 returned job usage credits sum1555; matches nominal estimate, not a currency invoice')
groups=[ordered[:1]]+[ordered[i:i+2] for i in range(1,len(ordered),2)];prior=[];groupdetails=[];pairok=True
for group in groups:
 first=min(dt(j['submit_started_at_utc']) for j in group)
 prev=max([dt(j['observed_at_utc']) for j in prior],default=dt(amend['adopted_at_utc']))
 pairok=pairok and prev<=first
 groupdetails.append({'pairs':[[j['fixture_id'],j['tier']] for j in group],'first_submit_at_utc':first.isoformat(),'prior_terminal_observation_upper_bound':prev.isoformat(),'barrier_pass':prev<=first});prior+=group
ck('final-pair-barrier',pairok,'Pilot alone; each subsequent pair begins after all prior jobs terminal observations')
ck('completion-ledger-order',order==[(j['fixture_id'],j['tier']) for j in sorted(complete,key=lambda j:dt(j['observed_at_utc']))],'Completion-consumption order agrees with durable terminal observation times; backend completion order is separate')
ret=read(P/'retention-manifest.json');changed=[]
for x in ret['files']:
 p=P/x['path']
 if not p.is_file() or sha(p)!=x['sha256'] or p.stat().st_size!=x['bytes']:changed.append(x['path'])
ck('original-629-retained',len(ret['files'])==629 and not changed,{'baseline_files':len(ret['files']),'changed_paths':changed})
hdir=ROOT/'historical-usage-refresh';hist=read(hdir/'usage.json');hs=[];hfiles=[]
for h in hist['jobs']:
 receipt=read(hdir/h['http_receipt']);response=receipt['response'];rp=hdir/receipt['raw_response_path'];hfiles.extend([hdir/h['http_receipt'],rp]);ok=receipt['method']=='GET' and receipt['http_status']==200 and response['job']['id']==h['job_id'] and response['job']['usage']==h['usage'] and response['job_metadata']==h['job_metadata'] and read(rp)==response
 ck('historical-get-'+h['fixture_id']+'-'+h['tier'],ok,'GET-only raw job usage/metadata identity matches retained refresh')
 hs.append({'fixture_id':h['fixture_id'],'tier':h['tier'],'job_id':h['job_id'],'credits':h['usage'].get('credits'),'job_metadata':h['job_metadata'],'receipt_path':str((hdir/h['http_receipt']).relative_to(ROOT))})
ck('all-40-job-identities',len(hs)==12 and len({(h['fixture_id'],h['tier']) for h in hs})==12 and {(h['fixture_id'],h['tier']) for h in hs}==excluded and len({h['job_id'] for h in hs}|{j['job_id'] for j in jobs})==40,'Historical12 +REST28 are unique jobs and complementary fixture/tier pairs; no completed-job reparse')
legacy=[h for h in hs if h['fixture_id'] in ['A01','A02']];export=read(P/'llama-recovery-2026-10-05/usage-export.json');by=collections.defaultdict(float)
for e in export:by[e['event_aggregation_key']]+=e.get('credits',0)
ck('legacy-four-110-export-match',sum(h['credits'] for h in legacy)==110 and all(by[h['job_id']]==h['credits'] for h in legacy),'Refreshed historical four-job usage agrees with prior export job IDs and110subtotal')
ck('full-40-returned-credits',len(hs)==12 and all(isinstance(h['credits'],(int,float)) for h in hs) and sum(h['credits'] for h in hs)==315 and sum(usage)+sum(h['credits'] for h in hs)==1870,'Returned usage available for all40jobs: REST1555 +historical315 =1870credits')
oldlegacy=read(P/'llama-recovery-2026-10-05/recovery-manifest.json')['jobs'];old_dashboard=[json.loads(line) for line in (P/'execution-dashboard-1/dashboard-jobs.jsonl').read_text().splitlines() if line.strip()];priorlookup={(j['fixture_id'],j['tier']):j for j in oldlegacy+old_dashboard}
ck('historical-original-job-mappings',len(priorlookup)==12 and all(priorlookup[(h['fixture_id'],h['tier'])]['job_id']==h['job_id'] and priorlookup[(h['fixture_id'],h['tier'])]['input_sha256']==units[h['fixture_id']]['input_sha256'] for h in hs),'Refresh job IDs match four retained recovered jobs and eight unchanged dashboard captures with frozen input hashes')
ck('historical-refreshed-page-metadata',all(h['job_metadata'].get('pdf-pages')==units[h['fixture_id']]['input_page_count'] for h in hs),'Refreshed historical metadata reports the frozen input page count for every job')
ck('all40-per-job-returned-credit-match',all(h['credits']==units[h['fixture_id']]['input_page_count']*(10 if h['tier']=='agentic' else 45) for h in hs) and all(j['reported_usage']['credits']==units[j['fixture_id']]['input_page_count']*(10 if j['tier']=='agentic' else 45) for j in jobs),'Actual returned usage independently matches per-page nominal credit rates for all40 jobs; no dollar-cost inference')
full_usage={'historical_jobs':12,'rest_jobs':28,'jobs_with_returned_credits':40,'historical_credits':sum(h['credits'] for h in hs),'rest_credits':sum(usage),'full40_reported_credits':sum(usage)+sum(h['credits'] for h in hs),'legacy_four_credits':sum(h['credits'] for h in legacy),'by_tier':{t:sum(h['credits'] for h in hs if h['tier']==t)+sum(j['reported_usage']['credits'] for j in jobs if j['tier']==t) for t in ['agentic','agentic_plus']},'currency_invoice_cost':None}
report={'schema_version':'rest-operations-final-v1','snapshot_started_at_utc':audit_start.isoformat(),'audited_at_utc':datetime.now(timezone.utc).isoformat(),'state_snapshot_sha256':hashlib.sha256(statebytes).hexdigest(),'phase_final':True,'planned_jobs':28,'completed_snapshot_jobs':len(complete),'active_snapshot_jobs':active,'pending_snapshot_jobs':sum(j['phase']=='pending' for j in state['jobs']),'checks':checks,'failed_checks':[c['check_id'] for c in checks if c['status']=='fail'],'jobs':jobs,'pair_barrier_groups':groupdetails,'historical_jobs':hs,'full40_usage':full_usage,'retained_http_receipts_as_of_snapshot':len(http),'accepted_post_receipts_as_of_snapshot':len(posts),'known_completed_credit_subtotal':sum(usage),'jobs_with_returned_credits':len(usage),'total_phase_billing_measured':False,'gaps':gaps,'secret_findings':secrets,'limitations':['Final phase completeness is assessed from retained state/receipts, not a fresh provider query.','HTTP receipts retain response bodies with explicit preservation/sanitization flags; no request headers or complete wire request bodies retained.','Remote input bytes are verified by runner and hash proof retained in state; raw downloaded remote input bytes are not independently available.','Sanitized expanded result may redact transient URLs; Markdown is independently exact against retained provider string.','Returned job file_id/resolved version may be absent; do not infer direct availability or release pin.','Provider backend timing, actual HTTP dispatch latency, and wrapper observation elapsed remain distinct.','Completed usage credits are provider-returned subtotal, not final account bill or currency cost.','No credential access, provider/browser calls, jobs or retries by this audit; prior review baselines preserved.']}
(OUT/'final-review.json').write_text(json.dumps(report,indent=2)+'\n');(OUT/'final-artifact-inventory.json').write_text(json.dumps(inv,indent=2)+'\n');(OUT/'audit_final.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps({'checks':len(checks),'failed_checks':report['failed_checks'],'snapshot_at':report['snapshot_started_at_utc'],'completed':len(complete),'active':len(active),'pending':report['pending_snapshot_jobs'],'known_credit_subtotal':sum(usage),'http_receipts':len(http),'concurrency_upper_bound':peak,'secret_paths':[s['path'] for s in secrets]}))
