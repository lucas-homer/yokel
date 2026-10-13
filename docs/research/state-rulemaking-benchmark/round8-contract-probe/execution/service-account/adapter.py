#!/usr/bin/env python3
"""R8 fixed native service entry. No key lookup, caller override, enrollment or retry."""
import contextlib,datetime,hashlib,importlib.util,json,os,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PYTHON=Path('/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12')
SITE=PYTHON.parent.parent/'lib/python3.12/site-packages'
REFERENCE_FREEZE=ROOT.parent/'round8/execution/freeze-B.json'
MANIFEST=ROOT/'sources/source-inputs.READY.json';IMPLEMENTATION=ROOT/'runtime/implementation.json';AUTHORIZATION=ROOT/'execution/live-authorization.json';RUN=ROOT/'execution/run'
class Denied(Exception):pass
def require(condition):
    if not condition:raise Denied()
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_bytes())
def verify_freeze(path,want,base=None):
    base=ROOT if base is None else base
    require(digest(path)==want);value=read(path);require(set(value)=={'created_utc','description','files'} and isinstance(value['files'],list));seen=set()
    for row in value['files']:
        require(set(row)=={'path','sha256','bytes'} and isinstance(row['path'],str) and not Path(row['path']).is_absolute())
        source=(base/row['path']).resolve();require(source.is_relative_to(base.resolve()) and row['path'] not in seen and source.is_file());seen.add(row['path'])
        require(digest(source)==row['sha256'] and source.stat().st_size==row['bytes'])
    return len(seen)
def verify_inputs():
    require(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode and Path(sys.executable).resolve()==PYTHON.resolve())
    binding=read(HERE/'binding.json');fields={'schema_version','implementation_sha256','manifest_sha256','authorization_sha256','freeze_A_sha256','freeze_S_sha256','freeze_B_sha256','dependencies_sha256'}
    require(set(binding)==fields and binding['schema_version']=='round8-contract-probe.service-binding.v1')
    deps=read(HERE/'dependencies.json');require(digest(HERE/'dependencies.json')==binding['dependencies_sha256'] and set(deps)=={'schema_version','files','dependency_scope'} and deps['schema_version']=='round8-contract-probe.service-dependencies.v1' and isinstance(deps['files'],dict) and deps['files'])
    for name,want in deps['files'].items():
        path=Path(name);require(path.is_absolute() and path.resolve()==path and path.is_file() and digest(path)==want)
    require(str(PYTHON.resolve()) in deps['files'] and str((HERE/'adapter.py').resolve()) in deps['files'])
    counts={name:verify_freeze(ROOT/'execution'/('freeze-'+name+'.json'),binding['freeze_'+name+'_sha256']) for name in ('A','S')}
    counts['B']=verify_freeze(REFERENCE_FREEZE,binding['freeze_B_sha256'],base=ROOT.parent/'round8')
    require(digest(IMPLEMENTATION)==binding['implementation_sha256'] and digest(MANIFEST)==binding['manifest_sha256'] and digest(AUTHORIZATION)==binding['authorization_sha256'])
    expected=dict(schema_version='round8-contract-probe.live-authorization.v1',implementation_sha256=binding['implementation_sha256'],manifest_sha256=binding['manifest_sha256'],source_labels_frozen_before_outputs=True,source_labels_freeze_sha256=binding['freeze_B_sha256'],nominal_budget_usd=2.0,prior_budget_debit_usd=.261774,prior_debit_sha256=digest(ROOT/'runtime/prior-debit.json'),max_new_operations=3,calls_per_stage=1,inventory_completion=12288,stronger_completion=4096,inventory_input_guard=35000,stronger_input_guard=40000,jev_total_input_guard=64000,jev_state_longest_guard=32000,prompt_delta_sha256='90a6f51531f5e26c9e1530a9b7b6c9feebde3b0742e238303839b8c975bf70b6')
    require(read(AUTHORIZATION)==expected)
    return dict(freeze_counts=counts,dependency_files=len(deps['files']),implementation_sha256=binding['implementation_sha256'],manifest_sha256=binding['manifest_sha256'],source_labels_freeze_sha256=binding['freeze_B_sha256'],authorization_sha256=binding['authorization_sha256'],budget_usd=2.0,max_new_operations=3,prior_budget_debit_usd=.261774)
def runtime_module():
    # Isolated Python skips .pth and sitecustomize; only the reviewed site package root is added.
    sys.path.insert(0,str(SITE))
    spec=importlib.util.spec_from_file_location('round8_durable_live',ROOT/'runtime/run_pipeline.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def check():
    verified=verify_inputs();runtime=runtime_module();plan=runtime.run(MANIFEST,ROOT/'sources',IMPLEMENTATION,RUN,live=False,max_new=3,budget=2.0)
    require(plan['documents']==1 and plan['PDF_pages']==2)
    return {**verified,'mode':'check','state':'passed','documents':plan['documents'],'PDF_pages':plan['PDF_pages'],'source_validation':plan['source_validation'],'provider_calls':0,'credentials_read':False}
class Silent:
    def write(self,value):return len(value)
    def flush(self):pass
def receipt(name,value):
    path=HERE/name;raw=(json.dumps(value,sort_keys=True)+'\n').encode()
    with path.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    fd=os.open(HERE,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)
def live_initial():
    verified=verify_inputs();require(not RUN.exists() and not (HERE/'live-intent.json').exists())
    runtime=runtime_module();runtime.run(MANIFEST,ROOT/'sources',IMPLEMENTATION,RUN,live=False,max_new=3,budget=2.0)
    require('OP_SERVICE_ACCOUNT_TOKEN' not in os.environ)
    keys={'openrouter':os.environ.get('OPENROUTER_API_KEY'),'jev':os.environ.get('TYPESAFE_API_KEY')}
    require(all(isinstance(k,str) and k.strip() and not k.startswith('op://') for k in keys.values()))
    receipt('live-intent.json',dict(schema_version='round8-contract-probe.service-live-intent.v1',**verified,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),adapter_sha256=digest(HERE/'adapter.py'),dependencies_sha256=digest(HERE/'dependencies.json'),binding_sha256=digest(HERE/'binding.json'),output_path=str(RUN),automatic_retry=False,production_eligible=False))
    try:
        with contextlib.redirect_stdout(Silent()),contextlib.redirect_stderr(Silent()):
            result=runtime.run(MANIFEST,ROOT/'sources',IMPLEMENTATION,RUN,live=True,authorization=AUTHORIZATION,source_labels_freeze_sha256=verified['source_labels_freeze_sha256'],max_new=3,budget=2.0,keys=keys)
        state=result.get('state');require(state in ('completed','paused_at_operation_boundary','stopped_provider_operation','stopped_budget'))
        receipt('live-result.json',dict(schema_version='round8-contract-probe.service-live-result.v1',state=state,budget_usd=2.0,max_new_operations=3,prior_budget_debit_usd=.261774,output_path=str(RUN),provider_calls_may_have_occurred=True,production_eligible=False))
        require(state=='completed')
    except BaseException:
        if not (HERE/'live-stop.json').exists():receipt('live-stop.json',dict(state='stopped',automatic_retry=False,provider_calls_may_have_occurred=True,exception_text_retained=False))
        raise Denied() from None
    return dict(state='completed')
def main():
    try:
        require(len(sys.argv)==2 and sys.argv[1] in ('--check','--live-initial'))
        if sys.argv[1]=='--check':print(json.dumps(check(),sort_keys=True))
        else:live_initial();print('Contract-probe approved job completed.')
        return 0
    except BaseException:
        print('Contract-probe adapter stopped; inspect approved nonsecret receipts.',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
