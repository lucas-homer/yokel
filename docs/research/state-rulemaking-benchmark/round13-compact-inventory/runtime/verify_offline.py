"""Read-only reproduction by default; author evidence recording stops at READY."""
import hashlib,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
PYTHON='/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    if sys.argv[1:] not in ([],['--record']):raise SystemExit('use --record only before READY')
    record=sys.argv[1:]==['--record']
    if record and (HERE/'READY.json').exists():raise SystemExit('frozen owner evidence is immutable')
    env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'}
    tests=subprocess.run([PYTHON,'-I','-S','-B',str(HERE/'test_runtime.py')],env=env,capture_output=True)
    check=subprocess.run([PYTHON,'-I','-S','-B',str(HERE/'adapter.py'),'--check'],env=env,capture_output=True)
    if record:
        (HERE/'test-output.txt').write_bytes(tests.stdout+tests.stderr);(HERE/'check-output.txt').write_bytes(check.stdout+check.stderr)
    if tests.returncode or check.returncode:
        sys.stderr.buffer.write(tests.stdout+tests.stderr+check.stdout+check.stderr);raise SystemExit('offline verification failed')
    deps=json.loads((HERE/'dependency-pins.json').read_bytes())['files']
    for p,h in deps.items():
        if sha(p)!=h:raise SystemExit('dependency drift')
    report={'schema_version':'round13.compact.offline-report.v1','passed':True,'runtime_test_methods':18,'fixtures':'complete supplied synthetic protocol controls, not R12 prefix salvage or model discovery','check':json.loads(check.stdout),'dependency_files':len(deps),'runtime_drift_entries':len(json.loads((HERE/'dependency-runtime-transition.json').read_bytes())['changed_files']),'imported_protocol':'exact pinned protocol/compact.py; validate_response + expand + contract','ledger_semantics':'charge_recorded; completed.json or stop.json is the separate outcome attestation; no hash cycle','pure_unsigned_proposal_validation_passed':True,'native_executor_check':'pending_primary','provider_calls':0,'credentials_read':False,'signer_executor_invoked':False,'candidate_or_reference_input':False,'semantic_status':'unverified','source_inventory_completeness':'unverified','provider_compatibility':'unverified','production_eligible':False,'action_ready':False}
    if record:
        report.update(test_output_sha256=sha(HERE/'test-output.txt'),check_output_sha256=sha(HERE/'check-output.txt'));(HERE/'REPORT.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'passed':True,'runtime_test_methods':18,'dependency_files':len(deps),'provider_calls':0,'credentials_read':False}))
if __name__=='__main__':main()
