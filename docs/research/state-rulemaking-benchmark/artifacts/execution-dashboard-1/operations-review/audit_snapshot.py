"""Offline snapshot audit; only writes execution-dashboard-1/operations-review."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,collections
from pypdf import PdfReader
ROOT=Path('/Users/home/.codex/worktrees/e8f4/yokel/docs/research/state-rulemaking-benchmark/artifacts/execution-dashboard-1'); OUT=ROOT/'operations-review';OUT.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dt(s):return datetime.fromisoformat(s.replace('Z','+00:00'))
def rel(p):return str(p.relative_to(ROOT))
def lines(p):return [json.loads(s) for s in p.read_text().splitlines() if s.strip()]
checks=[];gaps=[];jobs=[];inventory=[]
def ck(i,ok,details,paths=[]):checks.append(dict(check_id=i,status='pass' if ok else 'fail',details=details,evidence_paths=paths))
freeze=read(ROOT.parent/'corpus-freeze.json');units={x['fixture_id']:x for x in freeze['units']}; expected='900f21e8a75d50444f12a0e3814d665a4f401a0d689194465d0b00467a762946'
ck('frozen-manifest-digest',sha(ROOT.parent/'corpus-freeze.json')==expected,expected,['../corpus-freeze.json'])
stage=read(ROOT/'staging-manifest.json');amend=read(ROOT/'execution-amendment-4.json');batch=read(ROOT/'batch-plan.json');ledger=lines(ROOT/'dashboard-jobs.jsonl');events=lines(ROOT/'submission-events.jsonl');pilot=read(ROOT/'pilot-submission.json')
allowed=set(units)-{'A01','A02'}
ck('amended-scope',set(stage['ordered_fixture_ids'])==allowed==set(amend['remaining_scope']['fixtures']) and len(stage['inputs'])==18 and stage['planned_jobs']==amend['remaining_scope']['new_jobs_planned']==36 and stage['frozen_manifest_sha256']==expected and stage['input_pages_per_tier']==32,'18 inputs; 36 new jobs planned; A01/A02 excluded; staging metadata is a preparation snapshot')
for x in stage['inputs']:
 fid=x['fixture_id'];p=ROOT/'inputs'/x['filename'];u=units[fid]
 ck('staged-input-'+fid,sha(p)==u['input_sha256']==x['input_sha256'] and p.stat().st_size==u['input_bytes'] and len(PdfReader(p).pages)==u['input_page_count'],dict(sha256=sha(p),bytes=p.stat().st_size,pages=len(PdfReader(p).pages)),[rel(p)])
batchids=[]
for b in batch:
 ps=list((ROOT/'batches'/f"{b['batch']:02}").glob('*.pdf'));batchids+=b['fixtures']
 ck('batch-'+str(b['batch']),len(ps)==len(b['fixtures'])<=2 and {p.stem.replace('dc-expanded-','') for p in ps}==set(b['fixtures']) and all(sha(p)==units[p.stem.replace('dc-expanded-','')]['input_sha256'] and p.stat().st_size==units[p.stem.replace('dc-expanded-','')]['input_bytes'] and len(PdfReader(p).pages)==units[p.stem.replace('dc-expanded-','')]['input_page_count'] for p in ps),'Exact frozen byte copies; each batch at most two inputs',[rel(p) for p in ps])
ck('batch-coverage',len(batchids)==17 and set(batchids)==allowed-{'A03'},'Pilot staged separately; batches cover remaining 17 inputs')
ck('job-and-fixture-tier-uniqueness',len({x['job_id'] for x in ledger})==len(ledger)==len({(x['fixture_id'],x['tier']) for x in ledger}),'Unique visible job IDs and fixture/tier pairs')
eventmap=collections.defaultdict(list)
for x in [pilot]+events:
 for fid in x.get('fixture_ids',[x.get('fixture_id')]):eventmap[(fid,x['tier'])].append(x)
ck('submission-ledger-correspondence',set(eventmap)=={(x['fixture_id'],x['tier']) for x in ledger} and all(len(v)==1 for v in eventmap.values()),'Pilot + normalized submission events cover each retained job exactly once')
for x in ledger:
 fid=x['fixture_id'];tier=x['tier'];u=units[fid];d=ROOT/'runs'/fid/tier;cap=read(d/'capture.json');config=x.get('config');note=x.get('provenance_note',x.get('ui_configuration_note',''));end=x.get('observed_at_utc',x.get('success_observed_by_utc'));start=x['started_at_utc'];outputs=x['outputs'];outpaths=[];downloads=[]
 ck('capture-ledger-'+fid+'-'+tier,x==cap and fid in allowed and tier in ['agentic','agentic_plus'] and x['status']=='SUCCESS' and x['input_sha256']==u['input_sha256'] and x['input_bytes']==u['input_bytes'] and x['pages']==u['input_page_count'],'Capture equals job ledger; status and frozen metadata match',[rel(d/'capture.json')])
 for o in outputs:
  p=ROOT/o['path'];outpaths.append(p);dp=Path(o['download_path']);matches=p.is_file() and sha(p)==o['sha256'] and p.stat().st_size==o['bytes'];original_status='missing original download'
  if dp.is_file():original_status='matches original download' if sha(dp)==o['sha256'] and dp.stat().st_size==o['bytes'] else 'original download differs';matches=matches and original_status=='matches original download'
  else:gaps.append({'fixture_id':fid,'tier':tier,'gap':'Original download unavailable; retained bytes verify against manifest only','path':o['path']})
  ck('output-'+fid+'-'+tier+'-'+p.suffix,matches and p.parent==d,{'sha256':sha(p),'bytes':p.stat().st_size,'original_download':original_status},[rel(p)])
  if o.get('download_modified_at_utc'):
   t=o['download_modified_at_utc'];ck('download-time-'+fid+'-'+tier+'-'+p.suffix,dt(start)<=dt(t)<=dt(end),'Download timestamp lies between submission and terminal-success observation')
   downloads.append(t)
 jp=read(d/'output.json');pages=jp.get('pages',[])
 ck('output-pages-'+fid+'-'+tier,len(pages)==u['input_page_count'] and [p['page_number'] for p in pages]==list(range(1,u['input_page_count']+1)) and all(p.get('success') is True for p in pages),{'page_count':len(pages),'page_numbers':[p['page_number'] for p in pages]},[rel(d/'output.json')])
 ck('provenance-'+fid+'-'+tier,'not raw API' in note or 'not a raw API' in note,'UI configuration/status metadata explicitly transcribed; downloaded output bytes are separate evidence')
 if config:
  ck('settings-'+fid+'-'+tier,config['tier']==tier and config['version']=='latest' and config['file_id']==x['file_id'] and config['file_name']==f'dc-expanded-{fid}.pdf' and int(config['file_size_bytes'])==u['input_bytes'] and config.get('parsing_instruction') in ['', '""'],'UI-transcribed file/tier/latest/empty instruction agrees with mapping')
 else:
  ck('pilot-settings-note',x.get('version')=='latest' and pilot['no_custom_prompt'] and pilot['target_pages_disabled'] and pilot['max_pages_disabled'],'Pilot note/transcribed settings; no full per-job config object retained')
  gaps.append({'fixture_id':fid,'tier':tier,'gap':'No full per-job UI config object; pilot note/preflight evidence only'})
 ck('submission-order-'+fid+'-'+tier,dt(amend['adopted_at_utc'])<dt(start)<dt(end) and eventmap[(fid,tier)][0]['started_at_utc']==start,'Authorization precedes submission; matching event; success observed after submission')
 text=x.get('dashboard_timing_text','');m=re.search(r'Queue ([0-9.]+) (ms|s) Processing ([0-9.]+)s Total ([0-9.]+)s ([0-9.]+)s TOTAL',text)
 timing={'parser_breakdown_total_seconds':x['dashboard_duration_seconds'],'dashboard_full_total_seconds':None,'processing_seconds':None,'queue_seconds':None,'submission_to_success_observation_seconds':(dt(end)-dt(start)).total_seconds(),'raw_timing_text_present':bool(text)}
 if m:
  timing.update(queue_seconds=float(m[1])/(1000 if m[2]=='ms' else 1),processing_seconds=float(m[3]),dashboard_full_total_seconds=float(m[4]))
  ck('distinct-timing-'+fid+'-'+tier,float(m[5])==x['dashboard_duration_seconds'] and float(m[4])>=float(m[5]),'Full dashboard total kept distinct from smaller parser breakdown')
 else:gaps.append({'fixture_id':fid,'tier':tier,'gap':'Full dashboard total/queue/processing unavailable; breakdown duration must not be interpreted as full total'})
 upper=min([end]+downloads,key=dt)
 jobs.append(dict(fixture_id=fid,tier=tier,job_id=x['job_id'],file_id=x['file_id'],status=x['status'],input_sha256=x['input_sha256'],input_bytes=x['input_bytes'],pages=x['pages'],started_at_utc=start,terminal_observed_at_utc=end,completion_upper_bound_utc=upper,completion_bound_source='download timestamp' if upper!=end else 'terminal-success observation',timing=timing,metadata_provenance='UI transcription',output_provenance='downloaded artifact bytes',ui_configuration=config,usage_measured=None))
points=[]
for x in jobs:points.extend([(dt(x['started_at_utc']),1),(dt(x['completion_upper_bound_utc']),-1)])
active=peak=0
for _,delta in sorted(points,key=lambda t:(t[0],t[1])):active+=delta;peak=max(peak,active)
ck('completion-upper-bound-concurrency',peak<=2,{'maximum_possible_overlap_given_recorded_bounds':peak,'not_actual_provider_start_end_times':True})
expectedpairs={(fid,t) for fid in allowed for t in ['agentic','agentic_plus']};pending=sorted(expectedpairs-{(x['fixture_id'],x['tier']) for x in ledger})
ck('snapshot-eight-complete',len(ledger)==8 and len(pending)==28,'Eight retained complete jobs; 28 planned pairs absent in snapshot, not classified as failures')
secretfindings=[]
scoped=[ROOT/n for n in ['dashboard-jobs.jsonl','submission-events.jsonl','pilot-submission.json','execution-amendment-4.json','staging-manifest.json','batch-plan.json']]+[p for p in (ROOT/'runs').rglob('*') if p.is_file()]+[p for p in (ROOT/'inputs').glob('*.pdf')]+[p for p in (ROOT/'batches').rglob('*.pdf')]
for p in sorted(scoped):
 inventory.append({'path':rel(p),'sha256':sha(p),'bytes':p.stat().st_size})
 if p.suffix in ['.json','.jsonl','.md']:
  s=p.read_text()
  for category,pattern in {'signed URL or bearer token':r'https?://[^\s"<>]*(?:X-Amz-Signature|X-Goog-Signature|X-Amz-Credential)=|Bearer\s+[A-Za-z0-9._-]{12,}','credential field':r'"(?:api_key|authorization|access_token|uploadRef|uploadUrl)"\s*:\s*"(?!\[REDACTED)[^"\n]+"'}.items():
   if re.search(pattern,s,re.I):secretfindings.append({'path':rel(p),'category':category})
ck('scoped-secret-pattern-scan',not secretfindings,{'findings':secretfindings})
report={'schema_version':'dashboard-operations-snapshot-v1','audited_at_utc':datetime.now(timezone.utc).isoformat(),'status':'snapshot_not_final_phase','completed_jobs':len(jobs),'pending_planned_pairs':[{'fixture_id':f,'tier':t} for f,t in pending],'freeze_sha256':expected,'checks':checks,'failed_checks':[x['check_id'] for x in checks if x['status']=='fail'],'jobs':jobs,'concurrency':{'completion_upper_bound_overlap':peak,'actual_provider_concurrency':'not directly timestamped'},'provenance_gaps':gaps,'measured_billing':None,'nominal_phase_estimate_credits':1760,'estimate_is_not_measured':True,'secret_findings':secretfindings,'limitations':['Snapshot only; no final phase completeness assertion.','UI configuration/status is primary transcription, not independently queried API evidence.','Completion upper bounds use retained download timestamp transcriptions or success observations; actual completion order and provider dispatch times are unavailable.','A04/A05 Agentic success observation intervals overlap later Plus submission; earlier download timestamps tighten upper bounds and support max-two overlap.','Parser breakdown total is not full total; three jobs lack full timing. Observation elapsed includes user/interface delay.','Cache booleans differ by tier (Agentic false, Plus true for invalidate_cache/do_not_cache); screenshot-save true despite visible checkbox off is disclosed UI configuration. Do not assert exact cross-interface setting equivalence.','Dashboard exports JSON page items rather than a raw API tool envelope; output hash checks verify retained bytes and available local downloaded originals, not HTTP transport-byte provenance.','Usage export not refreshed; no measured new-phase billing or cost claimed.']}
(OUT/'snapshot-review.json').write_text(json.dumps(report,indent=2)+'\n');(OUT/'snapshot-artifact-inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
(OUT/'audit_snapshot.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps({'checks':len(checks),'failed_checks':report['failed_checks'],'completed_jobs':len(jobs),'pending_pairs':len(pending),'completion_upper_bound_overlap':peak,'timing_full':sum(j['timing']['dashboard_full_total_seconds'] is not None for j in jobs),'gap_count':len(gaps),'files_inventoried':len(inventory),'secret_paths':[x['path'] for x in secretfindings]}))
