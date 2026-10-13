"""Unsigned zero-cost smoke proposals only. No signing/native build/credential access."""
import argparse,hashlib,json,re,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
PYTHON=Path('/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12')
LIB=PYTHON.parent.parent/'lib';STD=LIB/'python3.12'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def put(path,value):
    with path.open('xb') as f:f.write((json.dumps(value,indent=2,sort_keys=True)+'\n').encode())
def prepare(*,scope_id,expires_unix,review):
    if not isinstance(scope_id,str) or not re.fullmatch('[a-z][a-z0-9-]{0,63}',scope_id) or type(expires_unix) is not int or not int(time.time())<expires_unix<=int(time.time())+86400:raise ValueError('bounded delegated scope/expiry required')
    review=Path(review).resolve()
    if not review.is_file():raise ValueError('final smoke review required')
    common={PYTHON.resolve(),review}
    common.update(p.resolve() for p in STD.rglob('*') if p.is_file() and 'site-packages' not in p.parts)
    common.update(p.resolve() for p in LIB.glob('*.dylib') if p.is_file())
    proposals=[]
    for job_id in ('job-alpha','job-beta'):
        folder=ROOT/job_id;adapter=(folder/'adapter.py').resolve();files={str(p):sha(p) for p in sorted(common|{adapter})}
        proposal={'schema_version':'yokel.research-job.v1','job_id':job_id,'scope_id':scope_id,'project':'yokel.docketclock.research','expires_unix':expires_unix,'provider_variables':['OPENROUTER_API_KEY'],'job':{'argv':[str(PYTHON),'-I','-S','-B',str(adapter),'--live-initial'],'files':files,'timeout_seconds':30},'budget':{'prior_nanousd':0,'reservation_nanousd':0,'ceiling_nanousd':2000000000},'review':{'path':str(review),'sha256':sha(review)}}
        put(folder/'UNSIGNED-ZERO-COST-PROPOSAL.json',proposal);proposals.append({'job_id':job_id,'adapter_sha256':sha(adapter),'dependency_files':len(files)})
    return {'approval_status':'unapproved_pending_final_smoke_review_and_primary_signing','proposals':proposals,'provider_calls':0,'credentials_read':False,'signing_attempted':False,'benchmark_ledger_modified':False,'zero_native_reservation':True}
if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('--scope-id',required=True);cli.add_argument('--expires-unix',required=True,type=int);cli.add_argument('--review',required=True,type=Path);args=cli.parse_args();print(json.dumps(prepare(scope_id=args.scope_id,expires_unix=args.expires_unix,review=args.review),sort_keys=True))
