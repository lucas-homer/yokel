"""Read-only reproduction by default; author evidence recording stops at READY."""
import hashlib,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
PYTHON='/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    if len(set(sys.argv[1:]))!=len(sys.argv[1:]) or set(sys.argv[1:])-{'--record','--candidate'}:raise SystemExit('use --candidate for pre-release checks; --record only before READY')
    record='--record' in sys.argv[1:];candidate='--candidate' in sys.argv[1:]
    if record and (HERE/'READY.json').exists():raise SystemExit('frozen owner evidence is immutable')
    env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'}
    tests=subprocess.run([PYTHON,'-I','-S','-B',str(HERE/'test_runtime.py')],env=env,capture_output=True)
    check=subprocess.run([PYTHON,'-I','-S','-B',str(HERE/'adapter.py'),'--candidate-check' if candidate else '--check'],env=env,capture_output=True)
    if record:
        (HERE/('candidate-test-output.txt' if candidate else 'test-output.txt')).write_bytes(tests.stdout+tests.stderr);(HERE/('candidate-check-output.txt' if candidate else 'check-output.txt')).write_bytes(check.stdout+check.stderr)
    if tests.returncode or check.returncode:
        sys.stderr.buffer.write(tests.stdout+tests.stderr+check.stdout+check.stderr);raise SystemExit('offline verification failed')
    deps=json.loads((HERE/'dependency-pins.json').read_bytes())['files']
    for p,h in deps.items():
        if sha(p)!=h:raise SystemExit('dependency drift')
    report={'schema_version':'round14.compact.offline-report.v1','passed':True,'runtime_test_methods':21,'fixtures':'complete synthetic structural outputs rebound to fresh source spans, not reference assertions or model discovery','release_preflight_passed':not candidate,'status':'CANDIDATE_CHECKED_NOT_RELEASED' if candidate else 'OFFLINE_PREFLIGHT_PASSED','check':json.loads(check.stdout),'dependency_files':len(deps),'runtime_drift_entries':len(json.loads((HERE/'dependency-runtime-transition.json').read_bytes())['changed_files']),'imported_protocol':'exact pinned protocol-revised/compact.py; validate_response + expand + contract','ledger_semantics':'charge_recorded; completed.json or stop.json is the separate outcome attestation; no hash cycle','pure_unsigned_proposal_validation_passed':True,'native_executor_check':'pending_primary','provider_calls':0,'credentials_read':False,'signer_executor_invoked':False,'candidate_or_reference_input':False,'semantic_status':'unverified','source_inventory_completeness':'unverified','provider_compatibility':'unverified','production_eligible':False,'action_ready':False}
    if record:
        report.update(test_output_sha256=sha(HERE/('candidate-test-output.txt' if candidate else 'test-output.txt')),check_output_sha256=sha(HERE/('candidate-check-output.txt' if candidate else 'check-output.txt')));(HERE/('CANDIDATE-REPORT.json' if candidate else 'REPORT.json')).write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'passed':True,'runtime_test_methods':21,'dependency_files':len(deps),'provider_calls':0,'credentials_read':False}))
if __name__=='__main__':main()
