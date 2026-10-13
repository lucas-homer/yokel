"""Primary-only offline late binding. No credentials, signing, dispatch or overwrite."""
import argparse, importlib.util, json, re, time
from pathlib import Path
HERE=Path(__file__).resolve().parent; ROOT=HERE.parent
PYTHON=Path('/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12')
import hashlib
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def put(path,value):
    with path.open('xb') as f:f.write((json.dumps(value,indent=2,sort_keys=True)+'\n').encode())
def prepare(scope_id,expires_unix,review):
    if not re.fullmatch('[a-z][a-z0-9-]{0,63}',scope_id) or type(expires_unix) is not int or not int(time.time())<expires_unix<=int(time.time())+86400:raise ValueError('bounded scope/expiry required')
    review=Path(review).resolve(); files=json.loads((HERE/'dependency-pins.json').read_bytes())['files']
    for path,want in files.items():
        p=Path(path)
        if not p.is_absolute() or p.resolve()!=p or digest(p)!=want:raise ValueError('dependency drift')
    paths=[ROOT/'scope.json',ROOT/'live-authorization.json',review]
    paths += [p for p in HERE.iterdir() if p.is_file() and p.name not in ('dependencies.json','binding.json','UNSIGNED-JOB-PROPOSAL.json')]
    files.update({str(p.resolve()):digest(p) for p in paths})
    put(HERE/'dependencies.json',{'schema_version':'round14.compact.dependencies.v1','files':files})
    binding={'schema_version':'round14.compact.binding.v1','dependencies_sha256':digest(HERE/'dependencies.json'),'authorization_sha256':digest(ROOT/'live-authorization.json'),'scope_sha256':digest(ROOT/'scope.json'),'input_pins_sha256':digest(HERE/'input-pins.json')}
    put(HERE/'binding.json',binding)
    files.update({str(HERE/name):digest(HERE/name) for name in ('dependencies.json','binding.json')})
    proposal={'schema_version':'yokel.research-job.v1','job_id':'round14-semantic-contract-initial','scope_id':scope_id,'project':'yokel.docketclock.research','expires_unix':expires_unix,'provider_variables':['OPENROUTER_API_KEY'],'job':{'argv':[str(PYTHON),'-I','-S','-B',str(HERE/'adapter.py'),'--live-initial'],'files':files,'timeout_seconds':1800},'budget':{'prior_nanousd':1705990718,'reservation_nanousd':200000000,'ceiling_nanousd':2000000000},'review':{'path':str(review),'sha256':digest(review)}}
    put(HERE/'UNSIGNED-JOB-PROPOSAL.json',proposal)
    return {'provider_calls':0,'credentials_read':False,'signed_job_created':False,'dependency_files':len(files)}
if __name__=='__main__':
    cli=argparse.ArgumentParser(); cli.add_argument('--scope-id',required=True); cli.add_argument('--expires-unix',required=True,type=int); cli.add_argument('--review',required=True,type=Path); args=cli.parse_args();print(json.dumps(prepare(args.scope_id,args.expires_unix,args.review),sort_keys=True))
