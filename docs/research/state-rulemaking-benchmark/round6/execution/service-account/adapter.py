#!/usr/bin/env python3
"""Fixed reviewed Round6 entry; no op, enrollment, key lookup or caller overrides."""
import contextlib,datetime,hashlib,importlib.util,json,os,sys
from pathlib import Path
ROOT=Path('/Users/home/.codex/worktrees/e8f4/yokel/docs/research/state-rulemaking-benchmark/round6')
HERE=ROOT/'execution/service-account'
PYTHON=Path('/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12')
SITE=Path('/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/lib/python3.12/site-packages')
FREEZES={'freeze-A.json':'d2acd7aaed9d08298809aeda03f25ddecf5df28913b753512fdc7fe0edfabe9f','freeze-S.json':'205cec19e5fea83a88cc261f87b0cf0ef3e8c708538aac62dfabbd91ca8ff7bc','freeze-B.json':'7fd9379aa2e1f3f3b7fb8a7f3526fd4e9e311d6f96fa4640a083e6d8c17d78e3'}
AUTH_SHA='4c18cac33c531fd593dbfb5956c17bb37fe3fc0c2d36086bd8bd39d48849d7c3'
IMPL_SHA='b55e4e7807fb3b295ce6a5a79b8d672486c5dc8a4caa0e84c113e3491cfa56a7'
SOURCE_SHA='c8421edc673c9b327bff82b9cff10cb6945db7a79e9b23c59cd888c3f3ec4cd9'
MANIFEST=ROOT/'sources/source-inputs.READY.json'
IMPLEMENTATION=ROOT/'runtime/implementation.json'
AUTHORIZATION=ROOT/'execution/live-authorization.json'
RUN=ROOT/'execution/run'
class Denied(Exception):pass

def require(condition):
    if not condition:raise Denied()

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_bytes())

def verify_freeze(root,path,want):
    require(digest(path)==want);data=read(path);require(set(data)=={'created_utc','description','files'} and isinstance(data['files'],list));seen=set()
    for row in data['files']:
        require(set(row)=={'path','sha256','bytes'} and isinstance(row['path'],str) and not Path(row['path']).is_absolute())
        p=(root/row['path']).resolve();require(p.is_relative_to(root.resolve()) and p.is_file() and row['path'] not in seen);seen.add(row['path'])
        require(digest(p)==row['sha256'] and p.stat().st_size==row['bytes'])
    return len(seen)

def verify_dependencies(path):
    data=read(path);require(set(data)=={'schema_version','files','dependency_scope'} and data['schema_version']=='round6.service-dependencies.v1');require(isinstance(data['files'],dict) and data['files'])
    for name,want in data['files'].items():
        p=Path(name);require(p.is_absolute() and p.is_file() and p.resolve()==p and digest(p)==want)
    require(str(PYTHON) in data['files'] and str(HERE/'adapter.py') in data['files'])
    return len(data['files'])

def verify_inputs():
    require(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode and Path(sys.executable).resolve()==PYTHON)
    dependency_count=verify_dependencies(HERE/'dependencies.json')
    counts={name:verify_freeze(ROOT,ROOT/'execution'/name,want) for name,want in FREEZES.items()}
    require(digest(AUTHORIZATION)==AUTH_SHA and digest(IMPLEMENTATION)==IMPL_SHA and digest(MANIFEST)==SOURCE_SHA)
    expected={'schema_version':'round6.live-authorization.v1','implementation_sha256':IMPL_SHA,'manifest_sha256':SOURCE_SHA,'source_labels_frozen_before_outputs':True,'source_labels_freeze_sha256':FREEZES['freeze-B.json'],'nominal_budget_usd':2.0}
    require(read(AUTHORIZATION)==expected)
    return {'freeze_counts':counts,'dependency_files':dependency_count,'authorization_sha256':AUTH_SHA,'implementation_sha256':IMPL_SHA,'manifest_sha256':SOURCE_SHA,'budget_usd':2.0,'max_new_operations':24}

def runtime_module():
    # -S skips .pth/sitecustomize. Only reviewed fixed package/runtime roots added.
    sys.path[:0]=[str(ROOT/'runtime'),str(SITE)]
    spec=importlib.util.spec_from_file_location('round6_unchanged_runtime',ROOT/'runtime/run_pipeline.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def check():
    verified=verify_inputs();runtime=runtime_module()
    result=runtime.run(MANIFEST,ROOT/'sources',IMPLEMENTATION,RUN,live=False,max_new=24,budget=2.0)
    require(result['documents']==4 and result['PDF_pages']==14 and all(not d['errors'] for d in result['source_validation']))
    return {**verified,'mode':'check','state':'passed','documents':result['documents'],'PDF_pages':result['PDF_pages'],'collection_target_achieved':False,'provider_calls':0,'credentials_read':False}

class Silent:
    def write(self,value):return len(value)
    def flush(self):pass

def receipt(name,value):
    # Only fixed nonsecret metadata; never provider values/outputs or exception text.
    path=HERE/name;data=(json.dumps(value,sort_keys=True)+'\n').encode()
    with path.open('xb') as file:file.write(data);file.flush();os.fsync(file.fileno())
    fd=os.open(HERE,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)

def live_initial():
    verified=verify_inputs();require(not RUN.exists() and not (HERE/'live-intent.json').exists())
    runtime=runtime_module();runtime.run(MANIFEST,ROOT/'sources',IMPLEMENTATION,RUN,live=False,max_new=24,budget=2.0)
    # Credential access is confined to the approved live entry, after frozen checks.
    require('OP_SERVICE_ACCOUNT_TOKEN' not in os.environ)
    keys={'openrouter':os.environ.get('OPENROUTER_API_KEY'),'jev':os.environ.get('TYPESAFE_API_KEY')}
    require(all(isinstance(key,str) and bool(key.strip()) and not key.startswith('op://') for key in keys.values()))
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    receipt('live-intent.json',{'schema_version':'round6.service-live-intent.v1',**verified,'started_utc':started,'adapter_sha256':digest(HERE/'adapter.py'),'dependencies_sha256':digest(HERE/'dependencies.json'),'output_path':str(RUN),'automatic_retry':False,'production_eligible':False})
    try:
        with contextlib.redirect_stdout(Silent()),contextlib.redirect_stderr(Silent()):
            result=runtime.run(MANIFEST,ROOT/'sources',IMPLEMENTATION,RUN,live=True,authorization=AUTHORIZATION,source_labels_freeze_sha256=FREEZES['freeze-B.json'],max_new=24,budget=2.0,keys=keys)
        state=result.get('state');require(state in ('completed','paused_at_operation_boundary'))
        receipt('live-result.json',{'schema_version':'round6.service-live-result.v1','state':state,'budget_usd':2.0,'max_new_operations':24,'output_path':str(RUN),'provider_calls_may_have_occurred':True,'production_eligible':False})
        require(state=='completed')
    except BaseException:
        if not (HERE/'live-stop.json').exists():receipt('live-stop.json',{'state':'stopped','automatic_retry':False,'provider_calls_may_have_occurred':True,'exception_text_retained':False})
        raise Denied() from None
    return {'state':'completed'}

def main():
    try:
        require(len(sys.argv)==2 and sys.argv[1] in ('--check','--live-initial'))
        if sys.argv[1]=='--check':print(json.dumps(check(),sort_keys=True))
        else:live_initial();print('Round6 approved job completed.')
        return 0
    except BaseException:
        print('Round6 adapter stopped; inspect approved nonsecret receipts.',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
