"""Read-only independent audit. Writes only operations-review; no provider calls.

Run `python3 audit.py prepare` now. Run `python3 audit.py complete` only after
the primary explicitly confirms run completion; final captures are then assessed.
Never print, persist or copy signed URLs, credentials or arbitrary error strings.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,re,collections
ROOT=Path(__file__).resolve().parent.parent;OUT=Path(__file__).resolve().parent
EXPECTED='900f21e8a75d50444f12a0e3814d665a4f401a0d689194465d0b00467a762946'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def utc():return datetime.now(timezone.utc).isoformat()
def save(name,obj):(OUT/name).write_text(json.dumps(obj,indent=2)+'\n')
def check(cid,status,paths,details):return dict(check_id=cid,status=status,evidence_paths=paths,details=details)
def dt(s):return datetime.fromisoformat(s.replace('Z','+00:00'))
def public_metadata(value):
 usage=[];ids=[]
 def walk(x,path=''):
  if isinstance(x,dict):
   for k,v in x.items():
    p=path+'/'+k
    if re.search(r'credit|usage|tokens|pagesProcessed|pageCount',k,re.I) and isinstance(v,(int,float)) and not isinstance(v,bool):usage.append(dict(path=p,value=v))
    if re.fullmatch(r'id|jobId|scrapeId|scrape_id|version|parserVersion|modelVersion',k,re.I) and isinstance(v,(str,int)) and not re.search(r'https?://|Bearer |X-Amz',str(v),re.I):ids.append(dict(path=p,value=v))
    if isinstance(v,(dict,list)):walk(v,p)
  elif isinstance(x,list):
   for i,v in enumerate(x):walk(v,path+'/'+str(i))
 walk(value);return dict(reported_usage=usage or None,returned_identifiers=ids or None)
def secret_categories(value):
 findings=[]
 def walk(x,path=''):
  if isinstance(x,dict):
   for k,v in x.items():
    if re.fullmatch(r'authorization|api_key|apiKey|uploadUrl|signedUrl|token|access_token',k,re.I) and isinstance(v,str) and v and not v.startswith('[REDACTED'):findings.append(dict(json_path=path+'/'+k,category='credential-or-upload-instruction value'))
    walk(v,path+'/'+k)
  elif isinstance(x,list):
   for i,v in enumerate(x):walk(v,path+'/'+str(i))
  elif isinstance(x,str):
   if re.search(r'https?://\S*(?:X-Amz-Signature=|X-Amz-Credential=|[?&]token=|[?&]signature=)|Bearer\s+[A-Za-z0-9._-]{12,}',x,re.I):findings.append(dict(json_path=path,category='signed URL or bearer token pattern'))
 walk(value);return findings
def validate_freeze():
 f=read(ROOT/'corpus-freeze.json');checks=[]
 checks.append(check('freeze-checksum','pass' if sha(ROOT/'corpus-freeze.json')==EXPECTED else 'fail',['corpus-freeze.json'],'Checksum compared to primary-provided immutable manifest digest.'))
 bad=[]
 for name,meta in f['files'].items():
  p=ROOT/name
  if not p.is_file():bad.append(dict(path=name,reason='missing frozen file'))
  elif sha(p)!=meta['sha256'] or p.stat().st_size!=meta['bytes']:bad.append(dict(path=name,reason='hash or byte length differs'))
 checks.append(check('frozen-source-reference-files','fail' if bad else 'pass',['corpus-freeze.json/files'],dict(frozen_files=len(f['files']),mismatches=bad)))
 ids=f['ordered_fixture_ids'];units={u['fixture_id']:u for u in f['units']}
 checks.append(check('frozen-input-pairing','pass' if len(units)==20 and len({u['input_sha256'] for u in units.values()})==20 else 'fail',['corpus-freeze.json/units'],dict(units=len(units),unique_input_hashes=len({u['input_sha256'] for u in units.values()}),input_page_instances=sum(u['input_page_count'] for u in units.values()))))
 return f,units,checks
def prepare():
 f,units,checks=validate_freeze();inputs=read(ROOT/'parser-inputs.json')['units'];bad=[]
 for u in inputs:
  target=units.get(u['fixture_id'])
  if target is None or any(u.get(k)!=target.get(k) for k in ['input_sha256','input_bytes','input_page_count']):bad.append(u['fixture_id'])
 checks.append(check('shared-parser-input-list','pass' if len(inputs)==20 and not bad else 'fail',['parser-inputs.json'],dict(entries=len(inputs),mismatch_fixture_ids=bad)))
 plan=read(ROOT/'llama/execution-plan.json');planbad=[]
 for arm in ['agentic','agentic_plus']:
  calls=[c for c in plan['calls'] if c['tier']==arm]
  for c in calls:
   u=units.get(c['fixture_id'])
   if not u or c['input_sha256']!=u['input_sha256'] or c['input_byte_length']!=u['input_bytes'] or c['input_page_count']!=u['input_page_count'] or c.get('version')!='latest' or c.get('markdown') is not True:planbad.append(c['fixture_id']+':'+arm)
  if len(calls)!=20 or {c['fixture_id'] for c in calls}!=set(units):planbad.append(arm+':coverage')
 good=not planbad and plan['freeze_manifest_sha256']==EXPECTED and plan.get('max_concurrent')==2
 checks.append(check('llama-planned-paired-settings','pass' if good else 'fail',['llama/execution-plan.json'],dict(planned_calls=len(plan['calls']),mismatches=planbad,requested_version='latest',pages='omitted: full bounded input',hints='not part of planned request')))
 guard=(ROOT/'firecrawl/verify_freeze.py').read_text();stale="fixtures=corpus['fixtures']" in guard and "corpus.get('passed') is True" in guard
 checks.append(check('firecrawl-preflight-schema','fail' if stale else 'not_assessable',['firecrawl/verify_freeze.py','corpus-freeze.json'], 'Observed preflight expects passing corpus.fixtures shape; immutable manifest is top-level units/files/counts. Execution lane must reconcile without altering frozen source/reference files.' if stale else 'Review actual updated script and final preflight evidence after run complete.'))
 harness=(ROOT/'firecrawl/capture_harness.mjs').read_text()
 checks.append(check('firecrawl-planned-settings','pass' if "formats:['markdown'],parsers:['pdf'],onlyMainContent:false" in harness and 'maxPages:f.input_page_count' in harness else 'not_assessable',['firecrawl/PLAN.md','firecrawl/capture_harness.mjs'],dict(formats=['markdown'],parsers=['pdf'],onlyMainContent=False,maxPages='frozen input_page_count',max_concurrent=2,stop_after_consecutive_failures=3,timeout_retry=False,actual_requests='pending run-complete audit')))
 prepared=dict(schema_version='operations-audit-v1',phase='prepared_pending_run_complete',prepared_at_utc=utc(),freeze_sha256=EXPECTED,checks=checks,provider_plans={'firecrawl':dict(parse_calls=20,input_hash_source='shared parser-inputs.json / frozen units',actual_mapping='pending'), 'llama':dict(parse_calls=40,tiers=['agentic','agentic_plus'],inputs_per_tier=20,actual_mapping='pending')},call_results=[],security_findings=[],limitations=['Final operational results intentionally not assessed before primary run-complete notice.','Preparation is a static snapshot; provider scripts may be updated while runs are ongoing.','Requested latest is not a verified released backend version pin.','JSON tool-object preservation does not establish original HTTP transport-byte preservation.'])
 save('preparation.json',prepared)
 save('expected-inputs.json',dict(freeze_sha256=EXPECTED,units=[dict(fixture_id=u['fixture_id'],input_sha256=u['input_sha256'],input_bytes=u['input_bytes'],input_page_count=u['input_page_count']) for u in f['units']],expected_arms=['firecrawl_local_parse','llama_agentic','llama_agentic_plus']))
 print(json.dumps(dict(phase=prepared['phase'],frozen_files=len(f['files']),frozen_hash_mismatches=len(next(x for x in checks if x['check_id']=='frozen-source-reference-files')['details']['mismatches']),checks={x['check_id']:x['status'] for x in checks})))
def concurrency(intervals):
 events=[]
 for c in intervals:
  if c.get('started_at') and c.get('ended_at'):
   events.extend([(dt(c['started_at']),1,c['call_id']),(dt(c['ended_at']),-1,c['call_id'])])
 events.sort(key=lambda e:(e[0],e[1]));active=0;peak=0
 for t,delta,cid in events:active+=delta;peak=max(peak,active)
 return dict(intervals=len(intervals),peak_concurrent=peak,maximum_two_observed=peak<=2)
def complete():
 # Use only after primary says complete; missing terminal records become assessable.
 f,units,checks=validate_freeze();calls=[];security=[];inventory=[]
 for lane in ['firecrawl','llama']:
  for path in sorted((ROOT/lane).rglob('*')):
   if path.is_file():inventory.append(dict(path=str(path.relative_to(ROOT)),sha256=sha(path),bytes=path.stat().st_size))
   if path.is_file() and path.suffix=='.json':
    try: findings=secret_categories(read(path))
    except (ValueError,UnicodeDecodeError):continue
    if findings:security.append(dict(path=str(path.relative_to(ROOT)),findings=findings))
 # Final lane schemas may evolve: inventory/schema keys enable safe adaptation.
 schemas=[]
 for path in sorted((ROOT/'firecrawl').glob('*/parse-capture.json'))+sorted((ROOT/'llama').glob('runs/*/*/capture.json')):
  obj=read(path);schemas.append(dict(path=str(path.relative_to(ROOT)),top_level_keys=list(obj),input_sha256_matches=obj.get('input_sha256')==units.get(obj.get('fixture_id',path.parent.name),{}).get('input_sha256')))
 save('final-artifact-inventory.json',inventory)
 save('final-schema-inventory.json',schemas)
 save('final-audit-preflight.json',dict(schema_version='operations-audit-v1',phase='run_complete_evidence_inventory',prepared_at_utc=utc(),freeze_sha256=EXPECTED,checks=checks,security_findings=security,limitations=['This complete command inventories final schemas and freezes evidence hashes; complete provider-specific receipt/timing/concurrency checks before final conclusion.']))
 print(json.dumps(dict(phase='run_complete_evidence_inventory',provider_files=len(inventory),capture_envelopes=len(schemas),security_paths=[x['path'] for x in security])))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['prepare','complete']);a=p.parse_args()
 prepare() if a.phase=='prepare' else complete()
