"""Bounded independent Q21 replay regression; no operational calls."""
import copy,hashlib,importlib.util,json,sys
from pathlib import Path
V=Path(__file__).resolve().parent;R8=V.parents[1];S=R8/'sources';C=S/'reconciliation'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(name,p):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def guard(event,args):
 if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.posix_spawn'):raise RuntimeError('Q21 independent review forbids network/process')
sys.addaudithook(guard)
pins_before={str(p.relative_to(C)):sha(p) for p in C.iterdir() if p.is_file()}
v1=load('independent_v1',C/'companion.py');v2=load('independent_v2',C/'companion_v2.py')
old=(C/'companion.py').read_text();expected=old.replace("if reasons and all('would exceed retained aggregate page cap'==r for r in reasons):","if o['physical_event']['path']=='search-access-ledger.jsonl' and reasons and all('would exceed retained aggregate page cap'==r for r in reasons):").replace("'amendment-release.json'","'amendment-release-v2.json'").replace("'preparation.READY.json'","'preparation-v2.READY.json'")
assert expected==(C/'companion_v2.py').read_text(),'Unexpected companion scope expansion'
assert (C/'export_bundle.py').read_text().replace('import companion as c','import companion_v2 as c').replace("'amendment-release.json'","'amendment-release-v2.json'")==(C/'export_bundle_v2.py').read_text(),'Unexpected exporter scope expansion'
oldview=v1.replay();newview=v2.replay();assert oldview['pending_candidate']=={'query_id':'Q21','display_order':8,'url':'https://rules.sd.gov/rulesguide.pdf','candidate_order':2}
assert newview['selected']==oldview['selected'] and len(newview['selected'])==5 and sum(x['pdf_pages'] for x in newview['selected'])==17
resolved=next(x for x in newview['decisions'] if x['query_id']=='Q21' and x['display_order']==8)
assert resolved['logical_status']=='excluded' and resolved['logical_reasons']==['would exceed retained aggregate page cap']
assert resolved['physical_observation']['physical_event']['path']=='reconciliation/access-ledger.jsonl'
assert newview['pending_candidate']!=oldview['pending_candidate']
obs=copy.deepcopy(v2.observations());candidate=v2.bounds()['Q21'][1];obs[v2.key('Q21',candidate)]['physical_event']['path']='search-access-ledger.jsonl'
historical=v2.replay(obs=obs);assert historical['pending_candidate']==oldview['pending_candidate'],'Historical aggregate-only reopening lost'
assert historical['selected']==oldview['selected']
baseline=v2.verify_baseline();assert len(baseline['source_files'])==503 and len(baseline['freeze_A_files'])==69
original_ready=json.loads((C/'preparation.READY.json').read_text());assert all(sha(C/x['path'])==x['sha256'] for x in original_ready['static_files'])
try:v2.gate();raise AssertionError('V2 access unexpectedly released')
except FileNotFoundError as ex:assert Path(ex.filename).name=='amendment-release-v2.json'
assert pins_before=={str(p.relative_to(C)):sha(p) for p in C.iterdir() if p.is_file()},'Review changed operational artifacts'
report={'disposition':'BOUNDED_V2_CODE_REGRESSION_PASS_AWAITING_SEALED_READY','exact_diff_allowed':'historical path conditional plus v2 preparation/release filename binding; exporter v2 import/release only','real_Q21_exclusion_resolved':True,'selected_cohort_unchanged':5,'selected_pages_unchanged':17,'historical_aggregate_only_still_pending':True,'original_503_and_69_pins_unchanged':True,'v1_static_pins_unchanged':True,'no_operational_artifact_edits':True,'fresh_access':0,'provider_calls':0,'pins':{n:sha(C/n) for n in ['companion.py','export_bundle.py','preparation.READY.json','companion_v2.py','export_bundle_v2.py','access-ledger.jsonl','correction-ledger.jsonl','Q21-replay-hold.json']},'next_pending':newview['pending_candidate']}
(V/'v2-results.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
