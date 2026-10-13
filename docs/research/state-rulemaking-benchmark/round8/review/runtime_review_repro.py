"""Independent R8 early-review controls; synthetic PDFs/provider bytes only."""
import contextlib,hashlib,importlib.util,io,json,socket,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1];runtime=R/'runtime'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
paths=[p for directory in (runtime,R/'execution/service-account',R/'protocol') for p in sorted(directory.glob('*')) if p.is_file() and p.suffix in ('.py','.json','.md')]
before={str(p.relative_to(R)):digest(p) for p in paths}
spec=importlib.util.spec_from_file_location('r8_independent_review_helpers',runtime/'offline_checks.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c);r=c.r
socket.socket=lambda *a,**k:(_ for _ in ()).throw(AssertionError('network forbidden during independent review'))
results=[]
for stage in ('inventory','stronger'):
 with tempfile.TemporaryDirectory() as temporary:
  root=Path(temporary);sources,manifest,freeze,auth,inv,verdict=c.fixture(root,documents=2);calls=[];normal=c.transport_for(inv,verdict,calls)
  def transport(provider,body,key):
   status,raw=normal(provider,body,key)
   if calls[-1]==stage:
    value=r.j.loads(raw);value['usage']['cost']=3;raw=r.j.encode(value)
   return status,raw
  with contextlib.redirect_stdout(io.StringIO()):out=r.run(manifest,sources,freeze,root/'run',live=True,authorization=auth,source_labels_freeze_sha256='a'*64,keys={'openrouter':'dummy-OR','jev':'dummy-jeV'},transport=transport)
  observed=r.j.loads(next((root/'run').glob('observed-*.json')).read_bytes());doc=observed['documents'][0]
  results.append(dict(case='postresponse_cost_overrun',stage=stage,synthetic_calls=calls,gate=doc['runtime_gate'],failure=doc['failure']['kind'] if doc['failure'] else None,arms={a:v['status'] for a,v in doc['arms'].items()},inventory_hash=doc['inventory_sha256'],retained_completed_results=len(list((root/'run/operations').glob('*/result.json'))),conservative_charge=out['totals']['budget_charge_usd']))
pins=r.code_pins()['code'];references=r.j.loads((R/'protocol/reuse-pins.json').read_bytes())['files'];missing=[rel for rel in references if str((R.parent/rel).resolve()) not in pins]
results.append(dict(case='protocol_dependency_pins',missing=missing,mutable_ready_pinned=any(Path(name).name=='READY.json' for name in pins)))
with tempfile.TemporaryDirectory() as temporary:
 root=Path(temporary);data=c.fixture(root);calls=[];original=r.validate_observation
 def unavailable(value):raise ValueError('simulated unavailable protocol validator')
 r.validate_observation=unavailable
 try:
  with contextlib.redirect_stdout(io.StringIO()):c.execute(root,data,calls)
 except ValueError:results.append(dict(case='unavailable_observation_validator',synthetic_calls_before_failure=calls))
 finally:r.validate_observation=original
print(json.dumps(dict(scope='early review; owner not finished',results=results,reviewed_hashes=before,files_changed_during_reproduction=[name for name,want in before.items() if digest(R/name)!=want],provider_calls=0,fresh_sources_read=False,credential_values_read=False),indent=2))
