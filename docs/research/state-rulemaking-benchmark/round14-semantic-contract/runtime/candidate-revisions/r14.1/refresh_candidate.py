"""Owner-only candidate pins before READY; no credentials, calls or reference reads."""
import hashlib,importlib.util,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROUND=HERE.parent;BENCH=ROUND.parent
if (HERE/'READY.json').exists():raise SystemExit('frozen owner evidence is immutable')
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def put(p,v):Path(p).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
spec=importlib.util.spec_from_file_location('r14_candidate_protocol',ROUND/'protocol/compact.py');k=importlib.util.module_from_spec(spec);spec.loader.exec_module(k)
source=(ROUND/'source/parsed-body.txt').read_bytes().decode('utf-8');plan=k.build(source)
for name,value in [('source-request.json',plan['body']),('source-span-table.json',plan['table']),('source-schema.json',plan['body']['response_format']['json_schema']['schema'])]:(HERE/name).write_bytes(k.canonical(value))
rows=read(ROUND/'prior-baseline.json')['files'];targets={r['path']:str((BENCH/r['path']).resolve()) for r in rows}
for row in rows:
 p=Path(targets[row['path']]);assert p.is_relative_to(BENCH) and h(p)==row['sha256']
put(HERE/'baseline-target-witness.json',targets)
files={str(ROUND/'protocol'/n):v for n,v in read(ROUND/'protocol/READY.json')['sha256'].items()}
files[str(ROUND/'protocol/READY.json')]=h(ROUND/'protocol/READY.json')
files.update({str(ROUND/'source'/n):v['sha256'] for n,v in read(ROUND/'source/READY.json')['artifacts'].items()})
for p in [ROUND/'source/READY.json',ROUND/'prior-baseline.json',ROUND/'scope.json',HERE/'source-request.json',HERE/'source-span-table.json',HERE/'source-schema.json',HERE/'baseline-target-witness.json']:files[str(p)]=h(p)
# The primary supplies the review/release barrier; include its closure only when present.
release_path=ROUND/'implementation-release.json'
if release_path.exists():
 files[str(release_path)]=h(release_path)
 for name,want in read(release_path)['files'].items():
  path=Path(name);assert path.is_absolute() and path.resolve()==path and path.is_relative_to(BENCH);assert h(path)==(want['sha256'] if isinstance(want,dict) else want);files[str(path)]=h(path)
 review_path=ROUND/'review/protocol/READY.json'
 for name,want in read(review_path)['files'].items():
  path=(review_path.parent/name).resolve();assert path.is_relative_to(review_path.parent);assert h(path)==(want['sha256'] if isinstance(want,dict) else want);files[str(path)]=h(path)
put(HERE/'input-pins.json',{'schema_version':'round14.compact.input-pins.v1','files':files,'source_case':'Prospectively selected unused source; no reference/candidate/provider output in request','source_sha256':k.source_hash(source),'source_ready_sha256':h(ROUND/'source/READY.json'),'span_table_sha256':k.digest(plan['table']),'request_sha256':plan['request_sha256'],'body_bytes':plan['body_bytes'],'guarded_bytes':plan['guarded_bytes'],'candidate_or_reference_input':False})
prior=read(BENCH/'round13-compact-inventory/runtime/dependency-pins.json')['files'];changed={p:{'prior_sha256':v,'current_sha256':h(p)} for p,v in prior.items() if h(p)!=v};assert not changed,'prior dependency drift'
deps=dict(prior);deps.update({targets[r['path']]:r['sha256'] for r in rows});deps.update(files)
# Candidate code pins are separate to avoid self-referential dependency hashes.
for p,v in deps.items():assert Path(p).resolve()==Path(p) and h(p)==v
assert len(deps)+100<10000
put(HERE/'dependency-pins.json',{'schema_version':'round14.compact.dependency-pins.v1','files':deps})
put(HERE/'dependency-runtime-transition.json',{'R13_inventory_sha256':h(BENCH/'round13-compact-inventory/runtime/dependency-pins.json'),'changed_files':changed,'prior_benchmark_drift_files':0,'notes':'Unchanged prior dependency pins plus full baseline and current approved inputs; no prior artifacts repinned.'})
put(HERE/'code-pins.json',{'files':{str(p):h(p) for p in sorted(HERE.glob('*.py'))}})
put(HERE/'CAPACITY.json',{'source_bytes':len(source.encode()),'source_chars':len(source),'source_spans':len(plan['table']['rows']),'full_request_bytes':plan['body_bytes'],'guarded_bytes':plan['guarded_bytes'],'max_guarded_bytes':40000,'request_sha256':plan['request_sha256'],'protocol_ready_sha256':h(ROUND/'protocol/READY.json'),'source_ready_sha256':h(ROUND/'source/READY.json'),'output_cap':8192,'tokenizer_matched':False,'output_headroom_established':False,'scope':'Capacity and semantic diagnostic only; fictional sizing is not source inventory count or output-fit guarantee. No units dropped or source altered.','provider_calls':0,'production_eligible':False,'action_ready':False})
print(json.dumps({'body_bytes':plan['body_bytes'],'guarded_bytes':plan['guarded_bytes'],'spans':len(plan['table']['rows']),'baseline_rows':len(rows),'dependency_files':len(deps),'provider_calls':0}))
