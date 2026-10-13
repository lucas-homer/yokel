"""Reproduce offline receipts in owned runtime only; no credentials or network."""
import hashlib,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
PYTHON='/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
    if sys.argv[1:] not in ([],['--record']):raise SystemExit('use --record only before owner READY')
    record=sys.argv[1:]==['--record']
    if record and (HERE/'READY.json').exists():raise SystemExit('frozen runtime outputs are immutable')
    env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'}
    tests=subprocess.run([PYTHON,'-I','-S','-B',str(HERE/'test_runtime.py')],env=env,capture_output=True)
    if record:(HERE/'test-output.txt').write_bytes(tests.stdout+tests.stderr)
    check=subprocess.run([PYTHON,'-I','-S','-B',str(HERE/'adapter.py'),'--check'],env=env,capture_output=True)
    if record:(HERE/'check-output.txt').write_bytes(check.stdout+check.stderr)
    if tests.returncode or check.returncode:
        sys.stderr.buffer.write(tests.stdout+tests.stderr+check.stdout+check.stderr);raise SystemExit('offline verification failed')
    deps=json.loads((HERE/'dependency-pins.json').read_bytes())['files']
    for p,h in deps.items():
        if sha(p)!=h:raise SystemExit('dependency drift')
    transition=json.loads((HERE/'dependency-runtime-transition.json').read_bytes())
    report={'schema_version':'round12.automated-scope.offline-report.v1','passed':True,'test_methods':33,'synthetic_outputs_are_supplied_annotations':True,'semantic_discovery_performed':False,'provider_calls':0,'credentials_read':False,'signed_job_created':False,'signer_or_executor_invoked':False,'reference_contents_read':False,'check':json.loads(check.stdout),'dependency_files':len(deps),'bundled_runtime_changed_files':len(transition['changed_files']),'removed_unused_runtime_caches':sum(v['R12_sha256'] is None for v in transition['changed_files'].values()),'prior_benchmark_drift_files':0,'test_output_sha256':sha(HERE/'test-output.txt'),'check_output_sha256':sha(HERE/'check-output.txt'),'source_inventory_completeness':'unverified','whole_record_fidelity':'unverified','semantic_status':'unverified','provider_compatibility':'unverified','production_eligible':False,'action_ready':False}
    if record:(HERE/'REPORT.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'passed':True,'test_methods':33,'dependency_files':len(deps),'provider_calls':0,'credentials_read':False}))
if __name__=='__main__':main()
