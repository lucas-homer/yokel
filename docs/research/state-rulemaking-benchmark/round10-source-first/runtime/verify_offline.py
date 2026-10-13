"""Fixed offline verifier; no credential env forwarding and no live entry point."""
import hashlib,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
PYTHON='/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
    env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'}
    tests=subprocess.run([PYTHON,'-I','-S','-B',str(HERE/'test_runtime.py')],env=env,capture_output=True)
    (HERE/'test-output.txt').write_bytes(tests.stdout+tests.stderr)
    check=subprocess.run([PYTHON,'-I','-S','-B',str(HERE/'adapter.py'),'--check'],env=env,capture_output=True)
    (HERE/'check-output.txt').write_bytes(check.stdout+check.stderr)
    if tests.returncode or check.returncode:raise SystemExit('offline verification failed; inspect owned outputs')
    deps=json.loads((HERE/'dependency-pins.json').read_bytes())['files']
    for p,h in deps.items():
        if sha(p)!=h:raise SystemExit('dependency drift')
    report={'schema_version':'round10.source-first.offline-report.v1','passed':True,'test_methods':24,'existing_synthetic_variants':10,'fixtures_are_supplied_offline_annotations':True,'semantic_discovery_performed':False,'provider_calls':0,'credentials_read':False,'signed_job_created':False,'check':json.loads(check.stdout),'dependency_files':len(deps),'test_output_sha256':sha(HERE/'test-output.txt'),'check_output_sha256':sha(HERE/'check-output.txt'),'source_inventory_completeness':'unverified','semantic_status':'unverified','production_eligible':False,'action_ready':False}
    (HERE/'REPORT.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');print(json.dumps({'passed':True,'test_methods':24,'dependency_files':len(deps),'provider_calls':0,'credentials_read':False}))
if __name__=='__main__':main()
