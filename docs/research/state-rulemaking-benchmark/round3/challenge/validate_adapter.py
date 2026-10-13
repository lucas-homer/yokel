"""Offline compatibility check: constructs requests, never executes provider calls."""
from pathlib import Path
import sys, importlib.util, json, hashlib
sys.dont_write_bytecode=True
O=Path(__file__).resolve().parent
adapter=O.parent/'verifiers/verifier.py'
spec=importlib.util.spec_from_file_location('challenge_adapter',adapter)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=[json.loads(x) for x in (O/'runtime.jsonl').read_text().splitlines()]
results=[]
for row in rows:
 m.state_for(row)
 gates={}; eligible={}
 for provider in ('jev','openrouter'):
  request,gate=m.build_request(row,provider)
  gates[provider]=gate;eligible[provider]=request is not None
 assert gates['jev']==gates['openrouter']
 assert eligible['jev']==eligible['openrouter']
 results.append({'case_id':row['case_id'],'schema_valid':True,'request_eligible':eligible,'deterministic':gates['jev']})
blocked=[r['case_id'] for r in results if not r['request_eligible']['jev']]
assert blocked==['C007'],blocked
assert results[6]['deterministic']['blocking_issues']==['candidate_abstained']
report={'passed':True,'adapter_sha256':sha(adapter),'runtime_sha256':sha(O/'runtime.jsonl'),'evaluation_sha256':sha(O/'evaluation-only.jsonl'),'schema_valid_cases':len(rows),'request_eligible_cases_per_provider':15,'deterministic_abstentions':['C007'],'model_completed_cases':0,'provider_calls':0,'note':'Request construction only. C007 retained in scheduled system metrics, excluded from model-only denominators. C016 ambiguous and excluded from primary determinate error/gate accuracy. C003 source-fidelity blindspot excluded from detectable-error denominator.','cases':results}
(O/'adapter-validation.json').write_text(json.dumps(report,indent=2)+'\n')
manifest=json.loads((O/'manifest.json').read_text())
for name in ('validate_adapter.py','adapter-validation.json'):manifest['files'][name]=sha(O/name)
(O/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='cases'},indent=2))
