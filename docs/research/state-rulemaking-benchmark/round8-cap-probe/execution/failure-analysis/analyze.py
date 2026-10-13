"""Read-only frozen assembly diagnosis; derived copies are development diagnostics only."""
import copy,hashlib,importlib.util,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def emit(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def guard(event,args):
    if event in ('socket.connect','socket.connect_ex','subprocess.Popen','os.system'):raise RuntimeError('offline diagnostic forbids network/process dispatch')
sys.addaudithook(guard)
spec=importlib.util.spec_from_file_location('probe_diagnostic_runtime',ROOT/'runtime/run_pipeline.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
freeze=ROOT/'execution/freeze-E.json';assert digest(freeze)=='415b294f83b3c093bd623da4cd4369a3c84cf385e6402ad190794e5681b30fb6'
frozen=json.loads(freeze.read_bytes())['files']
for row in frozen:
    path=(ROOT/row['path']).resolve();assert path.is_relative_to(ROOT.resolve()) and digest(path)==row['sha256'] and path.stat().st_size==row['bytes']
r.verify_implementation(ROOT/'runtime/implementation.json')
op=ROOT/'execution/run/operations/inventory-8f69eccb0e19f2d6e43cc72d';doc=ROOT/'execution/run/documents/doc-92211b8c7ba0'
source=json.loads((doc/'source.json').read_bytes());parsed=r.a.parse_or((op/'response.body').read_bytes());assert parsed==json.loads((op/'result.json').read_bytes())
inv=parsed['structured'];assembled=r.p.assemble(source,inv);assert assembled==json.loads((doc/'assembled.json').read_bytes())
expected=['t-access-request: dependency ids require a relation','t-access-request: relative/conditional timing requires dependency association or explicit uncertainty'];assert assembled['validation']['errors']==expected
schema_errors=r.p.schema_errors(inv,r.p.INVENTORY_SCHEMA);assert schema_errors==[]
def timing(value):return next(t for e in value['events'] for t in e['timing'] if t['id']=='t-access-request')
variants={}
for relation in ('other','uncertain'):
    diagnostic=copy.deepcopy(inv);timing(diagnostic)['dependency_relation']=relation;record=r.p.assemble(source,diagnostic);assert record['validation']['valid']
    plans=r.requests(source,record);assert plans['jev']['body']['state']==r.j.loads(plans['stronger']['body']['messages'][1]['content'])['payload']
    measures={stage:{**plans[stage]['admission'],'body_codepoints':len(r.j.encode(plans[stage]['body']).decode()),'input_margin':plans[stage]['admission']['cap']-plans[stage]['admission']['estimate'],'state_longest_margin':plans[stage]['admission']['state_longest_cap']-plans[stage]['admission']['state_longest_estimate'] if stage=='jev' else None} for stage in ('jev','stronger')}
    variants[relation]={'change':{'id':'t-access-request','field':'dependency_relation','from':'none','to':relation},'valid_structurally':True,'semantic_acceptance':False,'validation':record['validation'],'admission':measures,'paired_admitted':all(v['admitted'] for v in measures.values()),'inventory_sha256':hashlib.sha256(r.j.encode(diagnostic)).hexdigest(),'assembled_sha256':hashlib.sha256(r.j.encode(record)).hexdigest()}
    emit(HERE/('DIAGNOSTIC-DEVELOPMENT-'+relation+'-assembled.json'),{'diagnostic_development_only':True,'observed':False,'semantic_acceptance':False,'production_eligible':False,'assembly':record})
controls=[]
for relation,anchors,conditions,valid in [('none',[],['q-accessibility'],False),('none',[],[],False),('before',[],[],False),('other',[],['q-accessibility'],True),('uncertain',[],[],True)]:
    diagnostic=copy.deepcopy(inv);item=timing(diagnostic);item.update(dependency_relation=relation,anchor_event_ids=anchors,condition_requirement_ids=conditions);check=r.p.assemble(source,diagnostic);assert check['validation']['valid']==valid
    controls.append({'relation':relation,'anchors':anchors,'conditions':conditions,'expected_valid':valid,'passed':True,'errors':check['validation']['errors']})
report={'schema_version':'round8-cap-probe.failure-diagnosis.v1','freeze_E_sha256':digest(freeze),'frozen_files_checked':len(frozen),'implementation_sha256':digest(ROOT/'runtime/implementation.json'),'input_hashes':{str(p.relative_to(ROOT)):digest(p) for p in [doc/'source.json',doc/'assembled.json',op/'request.json',op/'response.body',op/'result.json']},'reproduced_exactly':True,'schema_errors':schema_errors,'assembly_errors':expected,'offending_timing':timing(inv),'provider':{'finish_reason':'stop','usage':parsed['usage'],'cost_usd':parsed['observed_cost_usd']},'controls':controls,'diagnostic_development_variants':variants,'provider_calls':0,'credentials_read':False,'labels_read':False,'observed_artifacts_modified':False,'production_eligible':False}
emit(HERE/'diagnosis.json',report)
for row in frozen:assert digest(ROOT/row['path'])==row['sha256']
print(json.dumps({'reproduced':True,'controls':len(controls),'paired_admitted':{k:v['paired_admitted'] for k,v in variants.items()},'provider_calls':0}))
