import hashlib,importlib.util,json,sys,tempfile,types
from pathlib import Path
HERE=Path(__file__).resolve().parent
adapter=HERE.parent/'runtime/adapter.py'
spec=importlib.util.spec_from_file_location('candidate',adapter);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def guard(event,args):
 if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.posix_spawn'):raise AssertionError('offline only')
sys.addaudithook(guard)
planned={'body':json.loads((HERE.parent.parent/'round9-exact-id-completeness/protocol/wi70-offline-request.fixture.json').read_bytes())}
native={'error':{'message':'synthetic schema rejection'},'usage':{'cost':3.0}}
raw=json.dumps(native).encode()
with tempfile.TemporaryDirectory(dir=HERE) as tmp:
 run=Path(tmp)/'run';calls=[]
 def transport(body,key):calls.append(1);return 400,raw
 try:m.execute_once(run,planned,None,None,'SYNTHETIC_SENTINEL_KEY',transport)
 except m.Denied:pass
 artifacts={p.name:json.loads(p.read_bytes()) for p in run.iterdir() if p.suffix=='.json'}
 report={'adapter_sha256':hashlib.sha256(adapter.read_bytes()).hexdigest(),'state':'reproduced_on_in_progress_candidate','transport_calls':len(calls),'provider_calls':0,'response_retained_exact':(run/'response.body').read_bytes()==raw,'raw_reported_cost_usd':3,'expected_conservative_total_nanousd':3696390718,'artifacts':artifacts,'finding':'Failed HTTP response contains finite usage.cost above reservation, but retained receipts omit recovered cost and cumulative debit; no cost ledger summary is written.'}
 # Avoid duplicating the provider request in this diagnostic.
 report['artifacts'].pop('request.json',None)
 (HERE/'early-failure-probe.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k!='artifacts'}))
